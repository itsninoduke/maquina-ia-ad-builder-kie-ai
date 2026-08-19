#!/usr/bin/env python3
"""
Generate one or more standalone Meta ad creatives via KIE.ai's dedicated
ChatGPT-Image-class endpoint:

  POST   /api/v1/gpt4o-image/generate         submit
  GET    /api/v1/gpt4o-image/record-info      poll (data.successFlag: 0/1/2)
  POST   /api/v1/gpt4o-image/download-url     get fresh download URL (result URLs expire ~20 min)

Brand contract: this skill hits KIE's OpenAI 4o-image / GPT-Image endpoint. It
does NOT use /api/v1/jobs/createTask — that's for Nano Banana and other
marketplace models. For Nano Banana, use the sibling nano-banana-image-ad skill.

Reference images must be public URLs (KIE does not provide presigned upload).

Modes:
  --mode image       (default) text-to-image, optionally with --image-url
                     URLs in filesUrl[]. Up to 5 URLs.
  --mode image_edit  edits a --source-url image (required) using --prompt and
                     optional --mask-url for inpainting. --image-url URLs in
                     filesUrl[] are still supported as additional refs.

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
ALLOWED_RATIOS = {"1:1", "3:2", "2:3"}  # /api/v1/gpt4o-image/generate cap
ALLOWED_MODES = {"image", "image_edit"}
# Per the docs nVariants enum is {1, 2, 4}, but in practice KIE silently downgrades
# any nVariants > 1 to 1 on this account/plan tier. To give the user the variants
# they asked for, the script fires N parallel single-variant requests instead of
# relying on nVariants batching — matches the other 3 image-ad scripts' pattern.
N_VARIANTS_PER_REQUEST = 1  # hard-locked
POLL_INTERVAL_S = 5
POLL_TIMEOUT_S = 300
MIN_DIMENSION = 1024
MAX_REFS = 5  # filesUrl cap

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

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
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": USER_AGENT})
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
    size: str,
    files_url: list[str],
    mask_url: str | None,
    n_variants: int,
    base_url: str,
    auth_hdr: str,
    callback_url: str | None,
    is_enhance: bool,
    enable_fallback: bool,
    allow_chrome: bool = False,
    no_safe_zone: bool = False,
) -> str:
    final_prompt = prompt
    if not allow_chrome:
        final_prompt += NO_CHROME_SUFFIX
    if not no_safe_zone:
        final_prompt += SAFE_ZONE_SUFFIX
    final_prompt += GLYPH_SAFETY_SUFFIX

    body: dict = {
        "prompt": final_prompt,
        "size": size,
        "nVariants": n_variants,
        "isEnhance": is_enhance,
        "enableFallback": enable_fallback,
    }
    if files_url:
        body["filesUrl"] = files_url
    if mask_url:
        body["maskUrl"] = mask_url
    if callback_url:
        body["callBackUrl"] = callback_url

    headers = {
        "Authorization": auth_hdr,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    resp = http_post_json(f"{base_url}/api/v1/gpt4o-image/generate", headers, body)
    code = resp.get("code")
    if code != 200:
        raise RuntimeError(f"submit returned code={code}: {resp}")
    data = resp.get("data") or {}
    task_id = data.get("taskId")
    if not task_id:
        raise RuntimeError(f"submit returned no taskId: {resp}")
    return task_id


def poll(task_id: str, base_url: str, auth_hdr: str) -> list[str]:
    """Poll record-info until successFlag transitions out of 0. Returns result URLs."""
    headers = {"Authorization": auth_hdr, "Accept": "application/json"}
    deadline = time.monotonic() + POLL_TIMEOUT_S
    last_progress = None
    while time.monotonic() < deadline:
        resp = http_get_json(
            f"{base_url}/api/v1/gpt4o-image/record-info?taskId={task_id}", headers
        )
        data = resp.get("data") or {}
        flag = data.get("successFlag")
        progress = data.get("progress")
        if progress != last_progress:
            log(f"  [{task_id[:8]}] flag={flag} progress={progress}")
            last_progress = progress
        if flag == 1:
            response = data.get("response") or {}
            urls = response.get("result_urls") or response.get("resultUrls")
            if not urls:
                raise RuntimeError(f"success but no result_urls: {data}")
            return urls
        if flag == 2:
            err = data.get("errorMessage") or data.get("error") or resp.get("msg")
            raise RuntimeError(f"task failed: {err} (full: {resp})")
        time.sleep(POLL_INTERVAL_S)
    raise TimeoutError(f"task {task_id} did not complete in {POLL_TIMEOUT_S}s")


def validate_url(url: str) -> None:
    if not url.startswith(("http://", "https://")):
        raise SystemExit(
            f"error: image references must be public URLs (http/https), got: {url[:120]}"
        )


def generate_one(
    request_index: int,
    prompt: str,
    size: str,
    files_url: list[str],
    mask_url: str | None,
    n_variants: int,
    out_dir: Path,
    slug: str,
    ts: str,
    base_url: str,
    auth_hdr: str,
    callback_url: str | None,
    is_enhance: bool,
    enable_fallback: bool,
    allow_chrome: bool,
    no_safe_zone: bool,
) -> list[dict]:
    """Submit one request and return one result dict per variant the API produced."""
    log(f"request {request_index}: submitting (size={size}, nVariants={n_variants}, refs={len(files_url)})…")
    task_id = submit(
        prompt, size, files_url, mask_url, n_variants,
        base_url, auth_hdr, callback_url, is_enhance, enable_fallback,
        allow_chrome=allow_chrome, no_safe_zone=no_safe_zone,
    )
    log(f"request {request_index}: taskId={task_id}")
    result_urls = poll(task_id, base_url, auth_hdr)
    log(f"request {request_index}: got {len(result_urls)} result URL(s)")

    results: list[dict] = []
    for vi, url in enumerate(result_urls, start=1):
        dest = out_dir / f"{ts}-{slug}-r{request_index}-v{vi}.png"
        log(f"  variant {vi}: downloading -> {dest.name}")
        http_download(url, dest)
        w, h = probe_dimensions(dest)
        if w and h and (w < MIN_DIMENSION or h < MIN_DIMENSION):
            log(
                f"  variant {vi}: WARNING image is {w}x{h}, below {MIN_DIMENSION}x{MIN_DIMENSION} "
                f"floor. Regenerate or upscale."
            )
        results.append({
            "variant": vi,
            "request_index": request_index,
            "path": str(dest),
            "task_id": task_id,
            "result_url": url,
            "width": w,
            "height": h,
            "prompt": prompt,
            "size": size,
            "model": "gpt-image-2",  # KIE's branding label; underlying model is OpenAI 4o-image
        })
    return results


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Generate ChatGPT Image 2 (OpenAI 4o-image) image(s) via KIE.ai. "
            "Hits the dedicated /api/v1/gpt4o-image/generate endpoint."
        ),
    )
    p.add_argument("--prompt", required=True, help="Image prompt (post-rewrite).")
    p.add_argument(
        "--mode", default="image", choices=sorted(ALLOWED_MODES),
        help="image (default) or image_edit (use --source-url + optional --mask-url).",
    )
    p.add_argument(
        "--aspect-ratio", choices=sorted(ALLOWED_RATIOS),
        help=f"Required. Maps to 'size' in the API request. One of {sorted(ALLOWED_RATIOS)}.",
    )
    p.add_argument(
        "--n", type=int, default=1,
        help=(
            "Variant count (1-5). Fired as N parallel single-variant requests. "
            "(The API has an nVariants param but silently downgrades to 1 in practice — "
            "we work around by parallelizing instead.)"
        ),
    )
    p.add_argument(
        "--out", type=Path, default=Path("./generated"),
        help="Output directory for PNGs.",
    )
    p.add_argument(
        "--image-url", action="append", default=[], metavar="URL",
        help=(
            f"Public URL for a reference image. Repeatable, max {MAX_REFS} (filesUrl cap). "
            "KIE does NOT provide a presigned upload — host elsewhere first."
        ),
    )
    p.add_argument(
        "--source-url", metavar="URL",
        help="Public URL for the source image to edit. Required for --mode image_edit.",
    )
    p.add_argument(
        "--mask-url", metavar="URL",
        help="Public URL for an inpainting mask (image_edit mode only).",
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
        help="If set, KIE POSTs the result here when done (in addition to polling).",
    )
    p.add_argument(
        "--is-enhance", action="store_true",
        help="Set isEnhance=true on the API (prompt-enhancement pass).",
    )
    p.add_argument(
        "--enable-fallback", action="store_true",
        help="Set enableFallback=true (KIE may swap models if primary fails).",
    )
    p.add_argument("--allow-chrome", action="store_true")
    p.add_argument("--no-safe-zone", action="store_true")
    p.add_argument(
        "--skip-url-check", action="store_true",
        help="Skip the HEAD probe on each --image-url / --source-url / --mask-url.",
    )
    args = p.parse_args()

    if not (1 <= args.n <= 5):
        log(f"error: --n must be 1..5; got {args.n}")
        return 2

    if len(args.image_url) > MAX_REFS:
        log(f"error: too many --image-url ({len(args.image_url)}); filesUrl cap is {MAX_REFS}")
        return 2

    if args.mode == "image":
        if args.source_url:
            log("error: --source-url is not allowed with --mode image. Use --mode image_edit.")
            return 2
        if args.mask_url:
            log("error: --mask-url is image_edit only.")
            return 2
        if not args.aspect_ratio:
            log("error: --aspect-ratio required. " f"Choose one of {sorted(ALLOWED_RATIOS)}.")
            return 2
    elif args.mode == "image_edit":
        if not args.source_url:
            log("error: --source-url is required for --mode image_edit.")
            return 2
        if not args.aspect_ratio:
            log("error: --aspect-ratio required even for image_edit (server enforces size). "
                f"Choose one of {sorted(ALLOWED_RATIOS)}.")
            return 2

    # In image_edit mode, source-url is also passed as the first filesUrl entry.
    files_url = list(args.image_url)
    if args.mode == "image_edit" and args.source_url:
        files_url = [args.source_url] + files_url
        if len(files_url) > MAX_REFS:
            log(f"error: source-url + image-urls exceeds filesUrl cap of {MAX_REFS}")
            return 2

    all_urls = list(files_url)
    if args.mask_url:
        all_urls.append(args.mask_url)
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

    chrome_state = "allowed" if args.allow_chrome else "stripped"
    log(
        f"generating {args.n} variant(s) (parallel requests, nVariants=1 each) "
        f"size={args.aspect_ratio} mode={args.mode} "
        f"chrome={chrome_state} refs={len(files_url)} mask={'yes' if args.mask_url else 'no'} -> {args.out}/"
    )

    # Fire N parallel single-variant requests. Matches the other 3 image-ad scripts.
    results: list[dict] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=args.n) as ex:
        futures = {
            ex.submit(
                generate_one, i, args.prompt, args.aspect_ratio, files_url, args.mask_url,
                N_VARIANTS_PER_REQUEST, args.out, slug, ts, base_url, auth_hdr,
                args.callback_url, args.is_enhance, args.enable_fallback,
                args.allow_chrome, args.no_safe_zone,
            ): i
            for i in range(1, args.n + 1)
        }
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                results.extend(fut.result())
            except Exception as e:  # noqa: BLE001
                errors.append(f"request {i}: {e}")
                log(f"request {i}: FAILED — {e}")

    results.sort(key=lambda r: r["request_index"])
    for r in results:
        print(json.dumps(r), flush=True)

    if not results:
        log(f"all {args.n} request(s) failed")
        return 1
    if errors:
        log(f"{len(results)}/{args.n} succeeded, {len(errors)} failed")
    else:
        log(f"all {args.n} variant(s) succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
