#!/usr/bin/env python3
"""
Generate one or more standalone Meta ad creatives via KIE.ai's
POST /api/v1/jobs/createTask with the Nano Banana model family
(nano-banana-2 default, nano-banana-pro / nano-banana-edit / nano-banana
legacy opt-in).

Brand contract: this script refuses any model outside the Nano Banana family.
The sibling `chatgpt-image-ad/scripts/generate_image.py` handles ChatGPT Image
on KIE (model string is configurable since KIE's marketplace catalogue shifts).

Reference images must be hosted at PUBLIC URLs — KIE has no presigned-upload
flow. Pass URLs (https://...) via --image-url; local files are NOT accepted.

Modes:
  --mode image       (default) text-to-image, optionally with --image-url
                     URLs for style/subject/character grounding. Up to 14 URLs.
  --mode image_edit  edits a --source-url image (required) using --prompt;
                     --image-url is optional additional refs.

Output contract:
  stdout: one JSON object per successfully generated variant, one per line
  stderr: human-readable progress + errors
  exit:   0 if at least one variant succeeded; 1 if all failed; 2 on bad args.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

BASE_URL_DEFAULT = "https://api.kie.ai"
ALLOWED_RATIOS = {"1:1", "4:5", "5:4", "2:3", "3:2", "9:16", "16:9", "3:4", "4:3", "21:9"}
ALLOWED_MODES = {"image", "image_edit"}
ALLOWED_MODELS = {"nano-banana-2", "nano-banana-pro", "nano-banana", "nano-banana-edit"}
DEFAULT_MODEL = "nano-banana-2"
POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 240
MIN_DIMENSION = 1024
MAX_REFS = 14

NO_CHROME_SUFFIX = (
    "\n\n[NO PLATFORM CHROME] Render only the standalone ad creative (the static image uploaded to Meta), "
    "not a screenshot of how it displays in-feed. Exclude: iOS device chrome (status bar, home indicator); "
    "platform brand-row above the ad (avatar + handle + Sponsored / Saved label); post body / caption text; "
    "link-card footer (URL + headline + button); engagement rows (likes / comments / shares counts, "
    "Followed-by, View comments); action buttons (Like / Comment / Share / Save); comment input boxes; "
    "platform tab/nav bars (Instagram, Facebook, Twitter); Story chrome (progress bars, story header, "
    "swipe-up arrows). Just the standalone image."
)

SAFE_ZONE_SUFFIX = (
    "\n\n[EDGE-SAFE] All text, headlines, CTAs, table headers, sign/board content, product wordmarks, and "
    "key focal subjects must fit within the central 84% of the canvas (~8% padding from every edge). "
    "Backgrounds and divider lines may bleed; text and focal elements may NOT touch or extend off any edge. "
    "If a tall focal subject doesn't fit at the requested aspect ratio, scale it DOWN — never crop a "
    "headline, never let text run off-frame, never cut off the top/bottom of a sign, board, or product."
)

GLYPH_SAFETY_SUFFIX = (
    "\n\n[TEXT FIDELITY] Inside body-text blocks (chat bubbles, message threads, comment text, ChatGPT "
    "responses, dense paragraphs): plain words only — NO emoji, NO unicode glyphs, NO special characters "
    "mid-sentence. Emoji OK in headlines and short large-text positions where the prompt explicitly calls "
    "for them. Render the EXACT count of conversation elements the prompt specifies — do not invent "
    "additional comments, messages, replies, or responses."
)


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def load_env(env_path: Path) -> dict:
    if not env_path.exists():
        raise SystemExit(f"error: .env not found at {env_path}")
    out: dict[str, str] = {}
    for raw in env_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def auth_header(env: dict) -> str:
    key = env.get("KIE_API_KEY") or os.environ.get("KIE_API_KEY")
    if not key:
        raise SystemExit("error: KIE_API_KEY not set in .env or shell environment")
    return f"Bearer {key}"


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len] or "image"


def http_post_json(url: str, headers: dict, body: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {url}: {err_body}") from e


def http_get_json(url: str, headers: dict, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} on {url}: {err_body}") from e


def http_head_url(url: str, timeout: int = 10) -> int:
    """Return HTTP status code for a HEAD on the URL (or GET if HEAD unsupported)."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:  # noqa: BLE001
        return 0


def http_download(url: str, dest: Path, timeout: int = 120) -> None:
    # KIE result-URL CDN 403's the default Python urllib User-Agent; spoof a browser UA.
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as out:
        while chunk := resp.read(64 * 1024):
            out.write(chunk)


def probe_dimensions(path: Path) -> tuple[int, int]:
    """Return (width, height) for a PNG/JPEG/WebP using stdlib only — cross-platform."""
    try:
        with path.open("rb") as f:
            header = f.read(32)
        if len(header) < 24:
            return 0, 0
        if header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR":
            return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")
        if header[:2] == b"\xff\xd8":
            with path.open("rb") as f:
                data = f.read()
            i = 2
            while i < len(data) - 8:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xD8, 0xD9):
                    i += 2
                    continue
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    h = int.from_bytes(data[i + 5:i + 7], "big")
                    w = int.from_bytes(data[i + 7:i + 9], "big")
                    return w, h
                seg_len = int.from_bytes(data[i + 2:i + 4], "big")
                i += 2 + seg_len
            return 0, 0
        if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            chunk = header[12:16]
            if chunk == b"VP8X" and len(header) >= 30:
                return int.from_bytes(header[24:27], "little") + 1, int.from_bytes(header[27:30], "little") + 1
            if chunk == b"VP8 ":
                with path.open("rb") as f:
                    data = f.read(40)
                if len(data) >= 30:
                    return (int.from_bytes(data[26:28], "little") & 0x3FFF,
                            int.from_bytes(data[28:30], "little") & 0x3FFF)
            if chunk == b"VP8L":
                with path.open("rb") as f:
                    data = f.read(25)
                if len(data) >= 25 and data[20] == 0x2F:
                    b0, b1, b2, b3 = data[21], data[22], data[23], data[24]
                    w = ((b1 & 0x3F) << 8 | b0) + 1
                    h = ((b3 & 0x0F) << 10 | b2 << 2 | (b1 >> 6)) + 1
                    return w, h
        return 0, 0
    except Exception as e:  # noqa: BLE001
        log(f"warn: could not probe dimensions for {path}: {e}")
        return 0, 0


def submit(
    prompt: str,
    model: str,
    mode: str,
    aspect_ratio: str | None,
    source_url: str | None,
    ref_urls: list[str],
    base_url: str,
    auth_hdr: str,
    callback_url: str | None,
    allow_chrome: bool = False,
    no_safe_zone: bool = False,
) -> str:
    final_prompt = prompt
    if not allow_chrome:
        final_prompt += NO_CHROME_SUFFIX
    if not no_safe_zone:
        final_prompt += SAFE_ZONE_SUFFIX
    final_prompt += GLYPH_SAFETY_SUFFIX

    inputs: dict = {"prompt": final_prompt}
    if mode == "image":
        if not aspect_ratio:
            raise ValueError("aspect_ratio required for mode=image")
        inputs["aspect_ratio"] = aspect_ratio
    elif mode == "image_edit":
        if not source_url:
            raise ValueError("source_url required for mode=image_edit")
        # For nano-banana-edit on KIE the source URL goes in image_input[0]; refs follow.
        combined = [source_url] + ref_urls
        inputs["image_input"] = combined
    if mode == "image" and ref_urls:
        inputs["image_input"] = ref_urls

    body: dict = {"model": model, "input": inputs}
    if callback_url:
        body["callBackUrl"] = callback_url

    headers = {
        "Authorization": auth_hdr,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    resp = http_post_json(f"{base_url}/api/v1/jobs/createTask", headers, body)
    data = resp.get("data") or {}
    task_id = data.get("taskId") or resp.get("taskId")
    if not task_id:
        raise RuntimeError(f"submit returned no taskId: {resp}")
    code = resp.get("code")
    if code is not None and code != 200:
        raise RuntimeError(f"submit returned code={code}: {resp}")
    return task_id


def poll(task_id: str, base_url: str, auth_hdr: str) -> str:
    headers = {"Authorization": auth_hdr, "Accept": "application/json"}
    deadline = time.monotonic() + POLL_TIMEOUT_S
    last_state = None
    while time.monotonic() < deadline:
        resp = http_get_json(
            f"{base_url}/api/v1/jobs/recordInfo?taskId={task_id}", headers
        )
        data = resp.get("data") or {}
        state = data.get("state")
        if state != last_state:
            log(f"  [{task_id[:8]}] state={state}")
            last_state = state
        if state == "success":
            # resultJson is a JSON-encoded string per KIE convention.
            result_raw = data.get("resultJson")
            if isinstance(result_raw, str):
                try:
                    result = json.loads(result_raw)
                except json.JSONDecodeError:
                    raise RuntimeError(f"resultJson not parseable: {result_raw[:200]}")
            elif isinstance(result_raw, dict):
                result = result_raw
            else:
                raise RuntimeError(f"resultJson missing or unexpected shape: {data}")
            # Result may contain `resultUrls` (list) or `images` (list of objects with url).
            urls = result.get("resultUrls") or result.get("urls")
            if not urls:
                imgs = result.get("images") or result.get("output")
                if isinstance(imgs, list) and imgs:
                    urls = [
                        img.get("url") if isinstance(img, dict) else img
                        for img in imgs
                    ]
            if not urls:
                raise RuntimeError(f"success but no URLs in result: {result}")
            return urls[0]
        if state in {"fail", "failed"}:
            err = data.get("failMsg") or data.get("error") or resp.get("msg")
            raise RuntimeError(f"task failed: {err} (full: {resp})")
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"task {task_id} did not complete in {POLL_TIMEOUT_S}s")


def validate_url(url: str) -> None:
    if not url.startswith(("http://", "https://")):
        raise SystemExit(
            f"error: image references must be public URLs (http/https), got: {url[:120]}"
        )


def generate_one(
    variant: int,
    prompt: str,
    model: str,
    mode: str,
    aspect_ratio: str | None,
    source_url: str | None,
    ref_urls: list[str],
    out_dir: Path,
    slug: str,
    ts: str,
    base_url: str,
    auth_hdr: str,
    callback_url: str | None,
    allow_chrome: bool,
    no_safe_zone: bool,
) -> dict:
    log(f"variant {variant}: submitting (model={model}, mode={mode}, refs={len(ref_urls)})…")
    task_id = submit(
        prompt, model, mode, aspect_ratio, source_url, ref_urls,
        base_url, auth_hdr, callback_url,
        allow_chrome=allow_chrome, no_safe_zone=no_safe_zone,
    )
    log(f"variant {variant}: taskId={task_id}")
    url = poll(task_id, base_url, auth_hdr)
    dest = out_dir / f"{ts}-{slug}-v{variant}.png"
    log(f"variant {variant}: downloading -> {dest.name}")
    http_download(url, dest)
    w, h = probe_dimensions(dest)
    if w and h and (w < MIN_DIMENSION or h < MIN_DIMENSION):
        log(
            f"variant {variant}: WARNING image is {w}x{h}, below {MIN_DIMENSION}x{MIN_DIMENSION} "
            f"floor. Regenerate or upscale."
        )
    return {
        "variant": variant,
        "path": str(dest),
        "task_id": task_id,
        "width": w,
        "height": h,
        "prompt": prompt,
        "mode": mode,
        "aspect_ratio": aspect_ratio,
        "model": model,
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Generate Nano Banana image(s) via KIE.ai. Defaults to nano-banana-2.",
    )
    p.add_argument("--prompt", required=True, help="Image prompt (post-rewrite).")
    p.add_argument(
        "--mode", default="image", choices=sorted(ALLOWED_MODES),
        help="image (default) or image_edit (edit --source-url).",
    )
    p.add_argument(
        "--aspect-ratio", choices=sorted(ALLOWED_RATIOS),
        help="Required for --mode image.",
    )
    p.add_argument("--n", type=int, default=1, help="Variant count, 1-5.")
    p.add_argument(
        "--out", type=Path, default=Path("./generated"),
        help="Output directory for PNGs.",
    )
    p.add_argument(
        "--image-url", action="append", default=[], metavar="URL",
        help=(
            f"Public URL for a reference image. Repeatable, max {MAX_REFS}. "
            "KIE does NOT provide a presigned upload — host elsewhere first."
        ),
    )
    p.add_argument(
        "--source-url", metavar="URL",
        help="Public URL for the source image to edit. Required for --mode image_edit.",
    )
    p.add_argument(
        "--model", default=DEFAULT_MODEL, choices=sorted(ALLOWED_MODELS),
        help=(
            f"Nano Banana variant. Default {DEFAULT_MODEL}. "
            "nano-banana-pro is Gemini 3 Pro Image; "
            "nano-banana-edit for inpaint; nano-banana is legacy."
        ),
    )
    p.add_argument(
        "--env-file", type=Path, default=Path(".env"),
        help="Path to .env (default: ./.env).",
    )
    p.add_argument(
        "--base-url", default=None,
        help=f"KIE API base URL (default: {BASE_URL_DEFAULT} or KIE_BASE_URL).",
    )
    p.add_argument(
        "--callback-url", default=None,
        help="If set, KIE POSTs the result here instead of (or in addition to) polling. "
        "Polling still runs as a fallback.",
    )
    p.add_argument("--allow-chrome", action="store_true")
    p.add_argument("--no-safe-zone", action="store_true")
    p.add_argument(
        "--skip-url-check", action="store_true",
        help="Skip the HEAD probe on each --image-url / --source-url. "
        "Useful for hosts that block HEAD.",
    )
    args = p.parse_args()

    if args.model not in ALLOWED_MODELS:
        log(f"error: --model must be one of {sorted(ALLOWED_MODELS)}; got '{args.model}'")
        return 2

    if not (1 <= args.n <= 5):
        log(f"error: --n must be 1..5 (got {args.n})")
        return 2

    if len(args.image_url) > MAX_REFS:
        log(f"error: too many --image-url ({len(args.image_url)}); Nano Banana cap is {MAX_REFS}")
        return 2

    if args.mode == "image":
        if args.source_url:
            log("error: --source-url is not allowed with --mode image. "
                "Use --image-url for guidance, or switch to --mode image_edit.")
            return 2
        if not args.aspect_ratio:
            log("error: --aspect-ratio is required for --mode image. "
                f"Choose one of {sorted(ALLOWED_RATIOS)}.")
            return 2
    elif args.mode == "image_edit":
        if not args.source_url:
            log("error: --source-url is required for --mode image_edit.")
            return 2
        if args.aspect_ratio:
            log("warn: --aspect-ratio is ignored for --mode image_edit.")

    # Validate URL shapes + reachability.
    all_urls = list(args.image_url)
    if args.source_url:
        all_urls.append(args.source_url)
    for u in all_urls:
        validate_url(u)
        if not args.skip_url_check:
            code = http_head_url(u)
            if code and code >= 400:
                log(f"error: reference URL not reachable (HTTP {code}): {u}")
                return 2

    env = load_env(args.env_file)
    auth_hdr = auth_header(env)
    base_url = (
        args.base_url
        or env.get("KIE_BASE_URL")
        or os.environ.get("KIE_BASE_URL")
        or BASE_URL_DEFAULT
    )

    args.out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = slugify(args.prompt)

    aspect = args.aspect_ratio if args.mode == "image" else None
    chrome_state = "allowed" if args.allow_chrome else "stripped"
    log(
        f"generating {args.n} variant(s) model={args.model} mode={args.mode} "
        f"{'aspect=' + aspect if aspect else 'aspect=from-source'} "
        f"chrome={chrome_state} refs={len(args.image_url)} -> {args.out}/"
    )

    results: list[dict] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=args.n) as ex:
        futures = {
            ex.submit(
                generate_one, i, args.prompt, args.model, args.mode, aspect,
                args.source_url, list(args.image_url), args.out, slug, ts,
                base_url, auth_hdr, args.callback_url,
                args.allow_chrome, args.no_safe_zone,
            ): i
            for i in range(1, args.n + 1)
        }
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                results.append(fut.result())
            except Exception as e:  # noqa: BLE001
                errors.append(f"variant {i}: {e}")
                log(f"variant {i}: FAILED — {e}")

    results.sort(key=lambda r: r["variant"])
    for r in results:
        print(json.dumps(r), flush=True)

    if not results:
        log(f"all {args.n} variant(s) failed")
        return 1
    if errors:
        log(f"{len(results)}/{args.n} succeeded, {len(errors)} failed")
    else:
        log(f"all {args.n} variant(s) succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
