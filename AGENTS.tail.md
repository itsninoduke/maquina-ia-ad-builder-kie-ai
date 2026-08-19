## This repo specifically

- **API:** KIE.ai (`https://api.kie.ai`).
- **Auth:** Bearer token via `KIE_API_KEY` (single token, no pre-encoded header).
- **Skills:**
  - `kie-external-api` — main API reference (Veo/Sora/Nano Banana endpoints, auth, polling, jobs vs first-party paths).
  - `generate-youtube-thumbnail` — YouTube thumbnail batch workflow on top of Nano Banana 2.
  - **Image-ad ecosystem** (3 skills + shared 37-template library) — see [shared/skills/image-ad-prompting/OVERVIEW.md](shared/skills/image-ad-prompting/OVERVIEW.md):
    - `chatgpt-image-ad` — generate via KIE's dedicated `/api/v1/gpt4o-image/generate` endpoint (typography / UI-mimicry creatives).
    - `nano-banana-image-ad` — generate via KIE `nano-banana-2`/`-pro`/`-edit` (photoreal / lifestyle creatives).
    - `image-ad-clone` — single backend-agnostic skill that reverse-engineers existing ads into reusable templates (asks which backend to validate against at Phase 1; optionally cross-validates at Phase 8).
- **Setup check:** `./scripts/check-kie-env.sh`.
- **Reference images:** KIE has no presigned-upload flow. Hosted public URLs only — see *Image hosting* in MASTER_CONTEXT.md.
- **Logging:** Log every generation call to `logs/kie-api.jsonl` (schema in `logs/README.md`).
- **Dashboards:** [kie.ai/logs](https://kie.ai/logs) · [kie.ai/api-key](https://kie.ai/api-key) · [kie.ai/pricing](https://kie.ai/pricing) · [kie.ai/market](https://kie.ai/market).
