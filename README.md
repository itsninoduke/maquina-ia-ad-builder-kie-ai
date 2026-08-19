# KIE.ai Video + Image — Agent Skill Pack

<sub>Parte del ecosistema **[MÁQUINA IA](https://www.skool.com/maquinadeleads/about)** · la comunidad LATAM donde dueños de negocio automatizan su operación con Claude</sub>

Create AI marketing videos and images using your [KIE.ai](https://kie.ai) account, powered by AI agents in **Claude Code** or **Cursor**. Supports the full KIE creative stack — **Seedance 2.0** (flagship video, plus Fast and 1.5 Pro variants), **Sora 2** + **Sora 2 Pro**, **Veo 3.1** (with all three generation modes), **Kling 3.0**, **Nano Banana 2 / Pro / Edit**, and **ChatGPT Image 2** via KIE's dedicated `/gpt4o-image` endpoint — plus a 37-template static Meta image-ad library and pipelines for **Pixar-style** and **claymation** animated ads.

**Key KIE characteristics to know upfront:**
- **Async by design.** Every generation call returns a `taskId`; results arrive via polling (`record-info` endpoints) or webhooks (`callBackUrl`).
- **URL-only references.** KIE has no presigned-upload flow — reference images must be publicly reachable URLs (your bucket, CDN, image host).
- **Marketplace catalogue evolves.** Model strings change as KIE adds/renames models. Verify on [kie.ai/market](https://kie.ai/market) on first use; the agent records confirmed strings in `MASTER_CONTEXT.md`.

## Prerequisites

The agent and the basic KIE workflows (image generation, video generation, polling) work with just **Python 3.10+** and the API key from setup. Some multi-step pipelines need a few extra CLI tools:

| Tool | Required for | Install (macOS) |
|---|---|---|
| **Python 3.10+** | Everything (the image-ad generators are stdlib-only — no pip install) | preinstalled or `brew install python@3.12` |
| **`ffmpeg`** | Pixar-style ad, claymation ad, caption-video (stitching + chroma-key overlay) | `brew install ffmpeg` |
| **`jq`** | Several bash scripts (pixar-style-ad, etc.) | `brew install jq` |
| **Node.js + `npx hyperframes`** | Caption burn-in workflow | `brew install node` (the skill runs `npx` on demand) |
| **`whisper`** Python package | Caption transcription | `pip install openai-whisper` (or `pip3`) |
| **`meta-ad-builder` deps** | Publishing to Meta Marketing API | `pip install -r shared/skills/meta-ad-builder/scripts/requirements.txt` |
| **Image hosting** | KIE reference images need public URLs (no presigned upload on KIE) | Your own R2 / S3 / Cloudinary, or a temp host like `0x0.st` or imgur |

The image-ad generator scripts (`chatgpt-image-ad`, `nano-banana-image-ad`, `image-ad-clone`) are intentionally stdlib-only — no extra installs needed. The deps above are only required when you invoke the matching multi-step workflow.

Linux users: `apt install ffmpeg jq nodejs python3`. Windows users: WSL2 recommended; the shell scripts assume bash.

## Get started (5 minutes)

### 1. Clone this repo

```bash
git clone https://github.com/itsninoduke/maquina-ia-ad-builder-kie-ai.git
cd maquina-ia-ad-builder-kie-ai
```

### 2. Run setup

```bash
./scripts/setup.sh
```

This will:
- Ask for your **KIE API key** (find it at [kie.ai/api-key](https://kie.ai/api-key))
- Save it securely in `.env` (never committed to git)
- Verify your connection to KIE
- Create your personal `MASTER_CONTEXT.md` workspace file
- Sync skills to `.claude/skills/` and `.cursor/skills/`

### 3. Open in your AI editor

**Claude Code:** Open the folder. A `SessionStart` hook runs and prints an orientation banner showing which skills are installed, whether your `.env` and `MASTER_CONTEXT.md` are set up, and where the docs live.

**Cursor:** Open the folder. Skills are exposed at `.cursor/skills/`.

### 4. Start creating

The agent handles API calls, async polling, prompt engineering, file organization, and cost confirmation. Workflows are grouped by what you want to make.

---

### 🎬 Seedance 2.0 videos (the flagship — start here)

Seedance 2.0 is the most flexible video model — 4–15s clips, native audio, image-to-video or video-to-video, reference images, multiple shot styles. Five prompt formulas ship with the skill, each tuned for a different ad shape:

#### UGC selfie-style product review

> "Make a 12-second Seedance UGC video — woman in a kitchen, holding the product, says she stopped buying [competitor]"

The 9-layer UGC formula tuned for Seedance 2.0 (iPhone-shot aesthetic, natural eye-contact breaks, casual delivery). See `skills/kie-external-api/prompting/prompt-library/seedance-2-ugc.md`.

#### Premium product reveal (no person)

> "Premium reveal of [product] — dark void, text narrative, hero rotation"

Dark-void aesthetic, text overlays narrating positioning, no person on screen. See `skills/kie-external-api/prompting/prompt-library/seedance-2-premium-reveal.md`.

#### Product hero with elemental effects

> "Seedance product hero — water splash, mist, slow rotation"

Splash, mist, light rays, slow rotation. See `skills/kie-external-api/prompting/prompt-library/seedance-2-product-hero.md`.

#### Studio lookbook with voiceover

> "Studio lookbook of [product] — multi-look, polished, with voiceover script"

Polished editorial / lookbook style, multi-shot, with embedded dialogue. See `skills/kie-external-api/prompting/prompt-library/seedance-2-studio-lookbook.md`.

#### Feature walkthrough demo

> "Seedance feature walkthrough — fast-paced, show off [features]"

Fast-paced product-demo cuts. See `skills/kie-external-api/prompting/prompt-library/seedance-2-feature-walkthrough.md`.

**Seedance variants on KIE:** `bytedance/seedance-2` (flagship), `bytedance/seedance-2-fast` (cheaper / faster), `bytedance/seedance-1.5-pro` (legacy). Always verify current strings on the marketplace.

---

### 🎬 Other video models

#### Veo 3.1 — three generation modes

> "Animate this Nano Banana still into a Veo video with dialogue" (REFERENCE_2_VIDEO)
> "Transition from this still to this still" (FIRST_AND_LAST_FRAMES_2_VIDEO)
> "Generate a pure Veo video of [scene]" (TEXT_2_VIDEO)

Veo 3.1 supports three mutually exclusive `generationType` modes:

- **`TEXT_2_VIDEO`** — pure prompt, no image anchor
- **`FIRST_AND_LAST_FRAMES_2_VIDEO`** — 2 URLs in `imageUrls` (start + end), Veo transitions between them
- **`REFERENCE_2_VIDEO`** — 1 URL in `imageUrls`, video unfolds from a single reference. **`REFERENCE_2_VIDEO` only supports `veo3_fast`.**

Model strings: `veo3_fast` (default), `veo3`, `veo3_lite`. Endpoint: `POST /api/v1/veo/generate`. The agent confirms dialogue separately before generating (the MANDATORY dialogue gate).

#### Sora 2 (text-to-video, up to 20s)

> "Generate a 16-second Sora video of [scene]"

Sora 2 handles longer durations than Veo. Duration enum: `[4, 8, 12, 16, 20]`. Auto-selected from script word count (~2.5 words/sec).

- **`sora-2-text-to-video`** — text-only
- **`sora-2-pro-text-to-video`** — Pro tier, premium quality
- **`sora-2-image-to-video`** — start from an image URL

#### Kling 3.0 (b-roll / scene)

> "Make a 5-second Kling b-roll clip of [scene]"

Kling 3.0 for cinematic b-roll and scene generation. Confirm exact marketplace string for your account.

---

### 🖼️ Image generation (Nano Banana + ChatGPT Image 2)

#### Create a new AI influencer (10-image character sheet)

> "Create a new AI influencer — 22-year-old college student with freckles, golden-hour kitchen lighting"

Two-pass workflow: (1) generate a hero front portrait via Nano Banana 2, get your approval, (2) generate 9 additional angles with the hero URL as the reference. All 10 saved to `references/influencers/` for future reuse.

#### UGC product selfie still

> "Generate a UGC selfie of Sofia holding [product] in her bedroom"

Combines your character hero URL + product photo URL + style references from `references/aesthetics/ugc-selfie/` into an authentic-looking iPhone selfie frame grab via Nano Banana 2. Includes skin realism and camera imperfections to fight AI's polished default.

#### Product showcase still → video

> "AI person holding [product] talking about [feature]"

Two-step: Nano Banana 2 with product reference URL → starting frame of the AI person with the product → user approves → starting-frame URL into Veo 3.1 `REFERENCE_2_VIDEO` or Sora 2 image-to-video.

#### Recreate an influencer from a reference photo

> "Recreate this influencer's look from this reference photo URL"

Two-step: Nano Banana 2 generates a still from the reference URL → user approves → still URL → Veo 3.1 `REFERENCE_2_VIDEO`.

#### Nano Banana model choice on KIE

KIE exposes multiple Nano Banana variants — pick per workflow:

- **`nano-banana-2`** (default) — current standard image model
- **`nano-banana-pro`** — Gemini 3 Pro Image, premium quality, locks character identity tighter across batches
- **`nano-banana-edit`** — inpaint / edit an existing image
- **`nano-banana`** — original / legacy variant (rarely needed)

---

### 📸 Static Meta image ad creative (37-template library)

> "Make me an Apple Notes-style ad for my product" / "Generate a Forbes editorial ad" / "Clone this comparison-table ad as a template"

A four-skill family for static Meta image ads with a shared library of **37 validated prompt templates** (Apple Notes lists, editorial hero, fake Google search, comparison tables, sticky-note flatlays, fake Slack threads, ChatGPT-conversation ads, iMessage screenshots, magazine cover, billboard, museum exhibit, weather forecast UI, scratch-off ticket, founder letter, dating-app card, more).

- **`chatgpt-image-ad`** — typography-heavy / UI-mimicry creatives. Hits KIE's **dedicated `/api/v1/gpt4o-image/generate` endpoint** (not `/jobs/createTask`). Sizes: `1:1`, `3:2`, `2:3`.
- **`nano-banana-image-ad`** — photoreal / lifestyle / multi-reference creatives via `/jobs/createTask`. Full Meta ratio set including `4:5` (the native Meta feed-portrait ratio).
- **`image-ad-clone`** — single backend-agnostic skill that reverse-engineers any existing ad URL into a new library entry (asks which generator to validate against at Phase 1; optionally cross-validates against the other at Phase 8).

Reference images are **public URLs** (KIE has no presigned upload). Output is image files; pair with the `meta-ad-builder` skill to publish as paused Meta ads. **Read `shared/skills/image-ad-prompting/OVERVIEW.md` first** — it has the decision tree, the aspect-ratio compatibility matrix per backend, and the standard generate / clone workflows. Live-validated end-to-end against the KIE API.

---

### 🎞️ Multi-step animated ad pipelines

#### Pixar-style 3D animated ad

> "Make a Pixar-style ad for [product] — anthropomorphized mascot, 8-beat story arc"

Lock cast sheet → ChatGPT Image 2 storyboard stills (sequential, prior frame as reference for identity lock) → Seedance 2.0 image-to-video per beat (`bytedance/seedance-2`) → ffmpeg stitch + burn captions. See `shared/skills/pixar-style-ad/prompting/guide.md`.

#### Claymation / Aardman-style ad

> "Make a claymation ad — sculpted plasticine characters, narrator-driven, 60–115s"

Same backbone as Pixar with an 8-beat narrator-driven story arc and clay textures. ChatGPT Image 2 storyboard (sequential for identity, parallel for beat 5 chart; falls back to `nano-banana-pro` for close-ups if clay texture flattens) → Seedance 2.0 i2v per beat → ffmpeg stitch with optional `fps=12,fps=24` stop-motion judder. VO is generated externally (ElevenLabs) and mixed in post. See `shared/skills/claymation-ad/prompting/guide.md`.

#### YouTube thumbnails (5 CTR formulas)

> "Generate 10 thumbnail variants for this video about prompt engineering"

Specialized `generate-youtube-thumbnail` skill: peace-sign/branding, real-vs-AI comparison, terminal flow, reaction shock, before/after split. Likeness lockdown via 5+ face URLs. Parallel batch firing against Nano Banana 2. See `skills/generate-youtube-thumbnail/`.

#### Burn captions onto a finished video

> "Add captions to this MP4"

Out-of-band post-step (no KIE call) that works on any source — Pixar, claymation, UGC, B-roll. HyperFrames + Whisper `medium.en` for transcription → group word-level transcript into reading phrases → render captions-only HTML over `#ff00ff` magenta → ffmpeg chroma-key overlay. See `shared/skills/caption-video/prompting/guide.md`.

---

### 🔄 Reverse-engineer existing creative

#### Analyze a reference video into a Seedance template

> "Reverse-engineer this video URL into a reusable Seedance template"

The `analyze-video` workflow under `skills/kie-external-api/prompting/analyze-video/` extracts the structure of a reference video into a parameterizable Seedance 2.0 prompt template.

#### Clone an existing video ad for a different product

> "Clone this video ad for our new product"

`skills/kie-external-api/prompting/clone-ad/` — end-to-end: analyze the reference → adapt to the new product → generate. The companion to `analyze-video` when you want to ship the cloned version directly.

#### Clone a static image ad into the prompt library

> "Reverse-engineer this image ad URL as a reusable template"

The `image-ad-clone` skill produces parameterizable entries for the 37-template library (see above).

---

### 📤 Publish creatives as paused Meta ads

> "Publish this approved creative as a paused Meta ad in my account"

The cross-API `meta-ad-builder` skill (in `shared/skills/`) takes a finished creative path and uploads it via the Meta Marketing API. Every ad is created PAUSED — you review and launch manually in Ads Manager. Also has a research path to pull top-spending ads and competitor ads. Auth via `META_*` keys in `.env`.

## What's in the box

| Path | What it does |
|------|-------------|
| `skills/kie-external-api/` | **The core skill.** API reference, prompting guide, per-model prompt libraries (Seedance / Sora / Veo / Kling / Nano Banana), analyze-video + clone-ad sub-workflows. |
| `skills/generate-youtube-thumbnail/` | 5 CTR-tested YouTube thumbnail formulas with parallel batch firing against Nano Banana 2. |
| `skills/chatgpt-image-ad/` | Static Meta image-ad creatives via `/api/v1/gpt4o-image/generate` (typography / UI mimicry). Live-validated. |
| `skills/nano-banana-image-ad/` | Static Meta image-ad creatives via Nano Banana 2 / Pro / Edit (photoreal / lifestyle). Live-validated. |
| `skills/image-ad-clone/` | Reverse-engineer an existing ad URL into a reusable library entry. Backend-agnostic — asks at Phase 1 whether to validate via gpt-image-2 (via `/gpt4o-image`) or Nano Banana, optionally cross-validates against the other at Phase 8. |
| `shared/skills/image-ad-prompting/` | Shared brain for the image-ad ecosystem: 37 validated templates, safety suffixes, entry format, `OVERVIEW.md`. |
| `shared/skills/pixar-style-ad/` | Cross-API recipe: 8-beat anthropomorphized mascot ad via GPT Image 2 storyboard + Seedance 2.0 i2v. |
| `shared/skills/claymation-ad/` | Cross-API recipe: Aardman-style 8-beat clay narrative ad; same backbone as Pixar with stop-motion judder option. |
| `shared/skills/caption-video/` | Out-of-band post step: HyperFrames + Whisper + ffmpeg chroma-key to burn captions onto any finished MP4. |
| `shared/skills/meta-ad-builder/` | Publish finished creatives as paused Meta ads via the Meta Marketing API. |
| `shared/scripts/check-context.sh` | SessionStart banner — lists installed skills, checks `.env` / `MASTER_CONTEXT.md` status, surfaces ecosystem pointers. Hooked into `.claude/settings.json`. |
| `MASTER_CONTEXT.template.md` | Template for your workspace context (credit costs, brand voice, image hosting, learnings). |
| `MASTER_CONTEXT.md` | Your personalized copy (created by setup, not committed to git). |
| `.env` | Your API key (created by setup, never committed). |
| `scripts/setup.sh` | One-time setup. |
| `scripts/sync-skill.sh` | Copies skill edits to `.claude/` and `.cursor/` directories. |
| `scripts/check-kie-env.sh` | Tests API connectivity. |
| `logs/kie-api.jsonl` | Append-only log of every generation call — model, duration, reference counts, taskId, status, credits charged. Powers cost estimates. See `logs/README.md`. **Committed** (historical cost data is valuable; no keys or full prompts logged.) |
| `references/` | Drop reference images here (influencers, products, aesthetics) — gitignored. |
| `outputs/` | Per-session download folders (`outputs/{YYYY-MM-DD}-{slug}/`) — gitignored. |

## Your API key

Your key authenticates with the KIE API. During setup you paste it once and the agent uses it from `.env` automatically. You never need to paste it into chat.

Need a KIE.ai account first? Create one here: **https://kie.ai**

Find your key: **[KIE Dashboard → API Key](https://kie.ai/api-key)**

For Meta-ad publishing (the `meta-ad-builder` skill), you'll also need `META_ACCESS_TOKEN` and `META_AD_ACCOUNT_ID` in `.env` — the `.env.example` has placeholder rows.

## Reference images must be hosted

KIE accepts reference images as **publicly reachable URLs** (`imageUrls` for Veo, `input.image_input` for marketplace models, `filesUrl` for `/gpt4o-image`). There is **no presigned-upload flow**. Plan your hosting strategy up front and record it in `MASTER_CONTEXT.md` under *Image hosting*:

- Your own R2 / S3 / Cloudinary bucket
- A temp host like `0x0.st` or imgur
- Anything that returns a public URL the KIE backend can fetch

The agent will **stop and ask** how to host a file if you pass a local path and no hosting is configured. The new image-ad scripts also HEAD-probe each URL before submitting (pass `--skip-url-check` if your host blocks HEAD).

## Async pattern and webhooks

Every KIE generation call is async. Two ways to get results:

- **Polling (default)** — agent polls the matching `record-info` endpoint every ~30 seconds:
  - Veo: `GET /api/v1/veo/record-info?taskId=…` (`successFlag` 0/1/2)
  - ChatGPT Image 2: `GET /api/v1/gpt4o-image/record-info?taskId=…` (`successFlag` 0/1/2)
  - Jobs (Sora / Kling / Nano Banana / Seedance / etc.): `GET /api/v1/jobs/recordInfo?taskId=…` (`state` waiting/queuing/generating/success/fail)
- **Webhook** — pass `callBackUrl` in the request body; KIE POSTs the final payload when done. Use for production / long-running jobs if you have an endpoint up.

Typical durations: Veo ~2–5 min, Sora 2 ~2–5 min, Seedance 2 ~3–4 min, Nano Banana / ChatGPT Image ~20–60 sec. KIE rate-limits at 20 req per 10s with up to 100 concurrent tasks — back off with jitter on 429.

## Project memory

`MASTER_CONTEXT.md` is your workspace's living memory. The agent reads it at the start of every session and writes learnings back. It stores:

- **Image hosting** — how you convert `references/` files to public URLs (write this once and the agent stops asking)
- **Credit costs** — per-model rates, filled in once
- **Confirmed model strings** — the exact `model` values the KIE marketplace exposes to your account (the marketplace catalogue evolves)
- **Default model variant** — e.g. Nano Banana 2 vs Pro for image generation
- **Brand voice** — optional tone, audience, and word preferences
- **API learnings** — universal KIE quirks that help the agent work better
- **Changelog** — dated notes from each session

## Supported models

| Model | Type | `model` string | Best for | Notes |
|-------|------|----------------|----------|-------|
| **Seedance 2.0** | Video (4–15s) | `bytedance/seedance-2` | Flagship video. UGC, premium reveal, product hero, lookbook, feature walkthrough. Native audio. | 5 prompt formulas ship. Endpoint: `POST /api/v1/jobs/createTask`. |
| **Seedance 2.0 Fast** | Video | `bytedance/seedance-2-fast` | Cheaper / faster Seedance for iteration. | Same endpoint. |
| **Seedance 1.5 Pro** | Video | `bytedance/seedance-1.5-pro` | Legacy Seedance Pro. | Same endpoint. |
| **Veo 3.1** | Video (~8s) | `veo3_fast` (default), `veo3`, `veo3_lite` | Animating starting frames (REFERENCE_2_VIDEO), text-to-video, first+last frame transitions. UGC stills → video path. | Endpoint: `POST /api/v1/veo/generate`. Mutually exclusive `generationType` modes; `REFERENCE_2_VIDEO` only supports `veo3_fast`. |
| **Sora 2** | Video (up to 20s) | `sora-2-text-to-video` | Long-duration text-to-video. | Endpoint: `POST /api/v1/jobs/createTask`. Duration auto-selected from script word count. |
| **Sora 2 Pro** | Video | `sora-2-pro-text-to-video` | Premium-tier Sora 2 for hero pieces. | Same endpoint. |
| **Sora 2 image-to-video** | Video | `sora-2-image-to-video` | Start a Sora video from a public image URL. | Same endpoint. |
| **Kling 3.0** | Video | per marketplace (`kling-3`, `kling-3-pro`, etc.) | B-roll, cinematic clips. | Confirm string on [kie.ai/market](https://kie.ai/market) for your account. |
| **Nano Banana 2** (default) | Image | `nano-banana-2` | UGC stills, character sheets, product shots, influencer recreation, image-ad creatives. | Endpoint: `POST /api/v1/jobs/createTask`. |
| **Nano Banana Pro** | Image | `nano-banana-pro` | Premium image quality (Gemini 3 Pro Image). Locks character identity tighter across batches. | Same endpoint. |
| **Nano Banana Edit** | Image | `nano-banana-edit` | Inpaint / edit an existing image. | Same endpoint. |
| **Nano Banana** (legacy) | Image | `nano-banana` | Original variant, rarely needed. | Same endpoint. |
| **ChatGPT Image 2** | Image | (no model param — endpoint selects model) | Typography-heavy / UI-mimicry static ad creatives. Used by `chatgpt-image-ad` skill + the Pixar / Claymation storyboard pipelines. | **Dedicated endpoint:** `POST /api/v1/gpt4o-image/generate`. Sizes: `1:1`, `3:2`, `2:3`. Up to 5 reference URLs in `filesUrl[]`. |

Cost is presented as an **estimate** before every generation; the agent reads `logs/kie-api.jsonl` for historical credit values matching your config. **Always verify exact `model` strings on the marketplace page for your account** — KIE adds and renames models as vendors update. Confirmed strings get written into `MASTER_CONTEXT.md` automatically.

## Reference images

Drop images into the `references/` folder and the agent will use them automatically (once you've set up hosting):

- **`references/influencers/`** — Photos of people to recreate as AI-generated content
- **`references/products/`** — Product photos for showcase videos and hero images
- **`references/aesthetics/`** — Style references organized by vibe (`ugc-selfie/`, `cinematic/`, etc.)

Images stay local — the folder contents are gitignored. The agent auto-upscales any reference below 1024px (the API's min-size floor) using Lanczos before uploading to your host.

## Editing skills

Each skill's canonical source lives in `skills/<name>/`. After editing any file there, run:

```bash
./scripts/sync-skill.sh
```

This copies your changes to `.claude/skills/` and `.cursor/skills/` (which are gitignored — they're generated copies). The `SessionStart` hook in `.claude/settings.json` also runs this automatically when Claude Code opens.

## Staying current

This repo updates regularly — new templates land in the prompt library, new workflows get added, bugs get fixed. To stay in sync with upstream:

- **At every Claude Code session start**, the `check-context.sh` hook automatically runs `git fetch origin` (with a 10s timeout, never blocks). If your local clone is behind, the SessionStart banner will list the pending commits and tell you to run `git pull`. No surprise pulls — it just notifies.
- **To pull updates manually:** `git pull origin main` from the repo root. If you've made local changes to tracked files, stash them first: `git stash && git pull && git stash pop`.
- **If you've forked the repo on GitHub:** click the "Sync fork" button on your fork's page to bring it in line with this upstream, then `git pull` locally.
- **Customizations:** your `.env`, `MASTER_CONTEXT.md`, `references/`, `outputs/`, and `logs/` are all gitignored — they survive every update. If you customize a core skill file (e.g. tune a SKILL.md for your brand), expect potential merge conflicts on `git pull` — keep custom versions under a non-tracked path (e.g. `local-skills/`) if you don't want them affected by upstream updates.

## Security

- `.env` is gitignored — never committed
- `MASTER_CONTEXT.md` is gitignored — contains your cost tables, hosting paths, and confirmed model strings
- `logs/kie-api.jsonl` IS committed (historical cost data is valuable), but never logs keys, headers, or full prompt text — see `logs/README.md`
- Never paste API keys in GitHub issues or public chats
- Every Meta ad created via `meta-ad-builder` is created **PAUSED** — nothing goes live without you launching it manually in Ads Manager

## Vendor prompting guides

| Model | Guide |
|-------|--------|
| Seedance 2.0 | Aligned to ByteDance's published Seedance prompting platform (the skill summarizes this in `skills/kie-external-api/prompting/prompt-library/seedance-2.md`) |
| Veo 3.1 | [Google Cloud — Veo 3.1](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1) |
| Sora 2 | [OpenAI — Sora 2 prompting guide](https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide) |
| Kling 3.0 | [Kling — user guide](https://kling.ai/quickstart/klingai-video-3-model-user-guide) |
| Nano Banana | [Google Cloud — Nano Banana](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana) |
| ChatGPT Image 2 | OpenAI image-generation guidance (summarized in `shared/skills/chatgpt-image-ad/prompting/guide.md` with model-specific strengths and limits) |

## API docs

- **KIE docs:** [docs.kie.ai](https://docs.kie.ai)
- **Model marketplace:** [kie.ai/market](https://kie.ai/market) — verify current `model` strings
- **Pricing:** [kie.ai/pricing](https://kie.ai/pricing)
- **Task logs UI:** [kie.ai/logs](https://kie.ai/logs) — server-side task history, status, credit consumption

## Comunidad · MÁQUINA IA 🚀

Este repo es una pieza del **Sistema 1 — el Marketero IA**: la parte que produce el creativo. El resto del sistema (cómo lo distribuís, cómo capturás el lead y cómo lo cerrás) vive en la comunidad.

**[skool.com/maquinadeleads](https://www.skool.com/maquinadeleads/about)** — en español, para LATAM:

- **Q&A en vivo cada semana** — te ayudamos con tu caso, en pantalla compartida
- **Bases de Claude** — desde cero, si nunca usaste IA
- **Los 5 Sistemas** — Marketero · Setter · Closer · Analista · Asistente, con sus bots y workflows ya armados
- **Snapshots de GHL y templates de n8n / Make** — importables, listos para producción
- **Facebook Ads Mastery · Video Editing Mastery · Planes de contenido** — qué hacer con el creativo una vez que lo generaste
- **El Drop del Mes** — un recurso nuevo cada mes, más una masterclass mensual

Si te trabás con este repo, ahí es donde se resuelve.

## Other AI assistants (Manus, Copilot, etc.)

Point your assistant at [AGENTS.md](AGENTS.md) and `MASTER_CONTEXT.md` + the skill paths in `skills/` and `shared/skills/`. See [AGENTS.md](AGENTS.md) for details.
