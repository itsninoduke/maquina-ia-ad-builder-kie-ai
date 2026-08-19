# KIE.ai Video + Imagen — Pack de Skills para Agentes

<sub>Parte del ecosistema **[MÁQUINA IA](https://www.skool.com/maquinadeleads/about)** · la comunidad LATAM donde dueños de negocio automatizan su operación con Claude</sub>

<sub>🇺🇸 [English version](README.en.md)</sub>

Crea videos e imágenes publicitarias con IA usando tu cuenta de [KIE.ai](https://kie.ai), manejada por agentes en **Claude Code** o **Cursor**. Soporta todo el stack creativo de KIE — **Seedance 2.0** (el modelo estrella de video, más las variantes Fast y 1.5 Pro), **Sora 2** + **Sora 2 Pro**, **Veo 3.1** (con sus tres modos de generación), **Kling 3.0**, **Nano Banana 2 / Pro / Edit**, y **ChatGPT Image 2** vía el endpoint dedicado `/gpt4o-image` de KIE — más una librería de 37 plantillas de anuncios estáticos para Meta y pipelines para anuncios animados **estilo Pixar** y **claymation**.

**Tres cosas de KIE que conviene saber desde el arranque:**
- **Todo es asíncrono.** Cada llamada de generación devuelve un `taskId`; los resultados llegan por polling (endpoints `record-info`) o por webhook (`callBackUrl`).
- **Las referencias son solo por URL.** KIE no tiene subida de archivos — las imágenes de referencia tienen que estar en URLs públicas y alcanzables (tu bucket, CDN o servicio de hosting).
- **El catálogo cambia.** Los nombres de los modelos cambian a medida que KIE agrega o renombra. Verifica en [kie.ai/market](https://kie.ai/market) la primera vez; el agente guarda los nombres confirmados en `MASTER_CONTEXT.md`.

## Requisitos

El agente y los flujos básicos de KIE (generar imágenes, generar videos, polling) funcionan solo con **Python 3.10+** y la API key del setup. Algunos pipelines de varios pasos necesitan herramientas extra:

| Herramienta | Necesaria para | Instalación (macOS) |
|---|---|---|
| **Python 3.10+** | Todo (los generadores de anuncios usan solo la librería estándar — no hace falta pip install) | ya viene instalado, o `brew install python@3.12` |
| **`ffmpeg`** | Anuncio estilo Pixar, claymation, subtítulos quemados (unir clips + overlay con chroma) | `brew install ffmpeg` |
| **`jq`** | Varios scripts de bash (pixar-style-ad, etc.) | `brew install jq` |
| **Node.js + `npx hyperframes`** | Flujo de subtítulos quemados | `brew install node` (la skill corre `npx` cuando lo necesita) |
| **Paquete `whisper` de Python** | Transcripción para subtítulos | `pip install openai-whisper` (o `pip3`) |
| **Dependencias de `meta-ad-builder`** | Publicar en la Meta Marketing API | `pip install -r shared/skills/meta-ad-builder/scripts/requirements.txt` |
| **Hosting de imágenes** | Las referencias de KIE necesitan URLs públicas (KIE no permite subir archivos) | Tu propio R2 / S3 / Cloudinary, o un host temporal como `0x0.st` o imgur |

Los scripts generadores de anuncios (`chatgpt-image-ad`, `nano-banana-image-ad`, `image-ad-clone`) usan a propósito solo la librería estándar — no requieren instalar nada. Las dependencias de arriba solo hacen falta cuando invocas el flujo correspondiente.

En Linux: `apt install ffmpeg jq nodejs python3`. En Windows: se recomienda WSL2; los scripts asumen bash.

## Arranca en 5 minutos

### 1. Clona el repo

```bash
git clone https://github.com/itsninoduke/maquina-ia-ad-builder-kie-ai.git
cd maquina-ia-ad-builder-kie-ai
```

### 2. Corre el setup

```bash
./scripts/setup.sh
```

Esto va a:
- Pedirte tu **API key de KIE** (la encuentras en [kie.ai/api-key](https://kie.ai/api-key))
- Guardarla de forma segura en `.env` (nunca se sube a git)
- Verificar tu conexión con KIE
- Crear tu archivo personal `MASTER_CONTEXT.md`
- Sincronizar las skills a `.claude/skills/` y `.cursor/skills/`

### 3. Ábrelo en tu editor con IA

**Claude Code:** abre la carpeta. Un hook de `SessionStart` imprime un banner de orientación con las skills instaladas, si tu `.env` y tu `MASTER_CONTEXT.md` están listos, y dónde está la documentación.

**Cursor:** abre la carpeta. Las skills quedan expuestas en `.cursor/skills/`.

### 4. Empieza a crear

El agente se encarga de las llamadas a la API, el polling asíncrono, la ingeniería de prompts, la organización de archivos y la confirmación de costos. Los flujos están agrupados por lo que quieres producir.

---

### 🎬 Videos con Seedance 2.0 (el modelo estrella — empieza aquí)

Seedance 2.0 es el modelo de video más flexible — clips de 4 a 15 segundos, audio nativo, imagen-a-video o video-a-video, imágenes de referencia y varios estilos de toma. La skill trae cinco fórmulas de prompt, cada una afinada para un formato de anuncio distinto:

#### Reseña de producto estilo selfie UGC

> "Haz un video UGC de 12 segundos con Seedance — una mujer en la cocina sosteniendo el producto, dice que dejó de comprar [competidor]"

La fórmula UGC de 9 capas afinada para Seedance 2.0 (estética de iPhone, cortes naturales de contacto visual, tono casual). Ver `skills/kie-external-api/prompting/prompt-library/seedance-2-ugc.md`.

#### Revelación premium del producto (sin persona)

> "Revelación premium de [producto] — fondo negro, texto narrativo, rotación del producto"

Estética de vacío oscuro, textos que narran el posicionamiento, sin ninguna persona en pantalla. Ver `skills/kie-external-api/prompting/prompt-library/seedance-2-premium-reveal.md`.

#### Producto como héroe con efectos

> "Producto héroe con Seedance — salpicadura de agua, neblina, rotación lenta"

Salpicaduras, neblina, rayos de luz, rotación lenta. Ver `skills/kie-external-api/prompting/prompt-library/seedance-2-product-hero.md`.

#### Lookbook de estudio con voz en off

> "Lookbook de estudio de [producto] — varios looks, pulido, con guion de voz en off"

Estilo editorial pulido, varias tomas, con diálogo incorporado. Ver `skills/kie-external-api/prompting/prompt-library/seedance-2-studio-lookbook.md`.

#### Demo de funcionalidades

> "Recorrido de funcionalidades con Seedance — ritmo rápido, muestra [funcionalidades]"

Cortes rápidos de demo de producto. Ver `skills/kie-external-api/prompting/prompt-library/seedance-2-feature-walkthrough.md`.

**Variantes de Seedance en KIE:** `bytedance/seedance-2` (la principal), `bytedance/seedance-2-fast` (más barata / más rápida), `bytedance/seedance-1.5-pro` (legacy). Verifica siempre los nombres actuales en el marketplace.

---

### 🎬 Otros modelos de video

#### Veo 3.1 — tres modos de generación

> "Anima esta imagen de Nano Banana en un video de Veo con diálogo" (REFERENCE_2_VIDEO)
> "Haz la transición de esta imagen a esta otra" (FIRST_AND_LAST_FRAMES_2_VIDEO)
> "Genera un video de Veo puro de [escena]" (TEXT_2_VIDEO)

Veo 3.1 soporta tres modos de `generationType`, mutuamente excluyentes:

- **`TEXT_2_VIDEO`** — solo prompt, sin imagen de anclaje
- **`FIRST_AND_LAST_FRAMES_2_VIDEO`** — 2 URLs en `imageUrls` (inicio + fin), Veo hace la transición entre ambas
- **`REFERENCE_2_VIDEO`** — 1 URL en `imageUrls`, el video se desarrolla desde una sola referencia. **`REFERENCE_2_VIDEO` solo funciona con `veo3_fast`.**

Nombres de modelo: `veo3_fast` (por defecto), `veo3`, `veo3_lite`. Endpoint: `POST /api/v1/veo/generate`. El agente confirma el diálogo por separado antes de generar (el gate obligatorio de diálogo).

#### Sora 2 (texto a video, hasta 20s)

> "Genera un video de Sora de 16 segundos de [escena]"

Sora 2 maneja duraciones más largas que Veo. Duraciones válidas: `[4, 8, 12, 16, 20]`. Se elige automáticamente según la cantidad de palabras del guion (~2,5 palabras por segundo).

- **`sora-2-text-to-video`** — solo texto
- **`sora-2-pro-text-to-video`** — tier Pro, calidad premium
- **`sora-2-image-to-video`** — arranca desde una URL de imagen

#### Kling 3.0 (b-roll / escenas)

> "Haz un clip de b-roll de 5 segundos con Kling de [escena]"

Kling 3.0 para b-roll cinematográfico y generación de escenas. Confirma el nombre exacto del modelo en el marketplace de tu cuenta.

---

### 🖼️ Generación de imágenes (Nano Banana + ChatGPT Image 2)

#### Crear un influencer IA nuevo (character sheet de 10 imágenes)

> "Crea un influencer IA nuevo — estudiante de 22 años con pecas, luz de cocina al atardecer"

Flujo de dos pasadas: (1) genera un retrato frontal principal con Nano Banana 2 y te pide aprobación, (2) genera 9 ángulos más usando la URL del retrato como referencia. Las 10 quedan guardadas en `references/influencers/` para reutilizarlas.

#### Selfie UGC con producto

> "Genera un selfie UGC de Sofía sosteniendo [producto] en su habitación"

Combina la URL de tu personaje + la foto del producto + las referencias de estilo de `references/aesthetics/ugc-selfie/` en un frame de selfie de iPhone que parece real, vía Nano Banana 2. Incluye realismo de piel e imperfecciones de cámara para contrarrestar el acabado demasiado pulido de la IA.

#### Imagen de producto → video

> "Persona IA sosteniendo [producto] hablando de [beneficio]"

Dos pasos: Nano Banana 2 con la URL del producto → frame inicial de la persona IA con el producto → apruebas → esa URL entra a Veo 3.1 `REFERENCE_2_VIDEO` o a Sora 2 imagen-a-video.

#### Recrear un influencer desde una foto de referencia

> "Recrea el look de este influencer desde esta URL de referencia"

Dos pasos: Nano Banana 2 genera una imagen desde la URL de referencia → apruebas → esa URL entra a Veo 3.1 `REFERENCE_2_VIDEO`.

#### Qué variante de Nano Banana usar en KIE

KIE expone varias variantes de Nano Banana — elige según el flujo:

- **`nano-banana-2`** (por defecto) — el modelo de imagen estándar actual
- **`nano-banana-pro`** — Gemini 3 Pro Image, calidad premium, mantiene la identidad del personaje más firme entre lotes
- **`nano-banana-edit`** — retocar / editar una imagen existente
- **`nano-banana`** — variante original / legacy (rara vez hace falta)

---

### 📸 Anuncios estáticos para Meta (librería de 37 plantillas)

> "Hacéme un anuncio estilo Apple Notes para mi producto" / "Genera un anuncio editorial estilo Forbes" / "Clona este anuncio de tabla comparativa como plantilla"

Una familia de cuatro skills para anuncios estáticos de Meta con una librería compartida de **37 plantillas de prompt validadas** (listas estilo Apple Notes, editorial, búsqueda falsa de Google, tablas comparativas, flatlays de notas adhesivas, hilos falsos de Slack, anuncios con formato de conversación de ChatGPT, capturas de iMessage, tapa de revista, cartel de vía pública, exhibición de museo, interfaz de pronóstico del clima, raspadita, carta del fundador, tarjeta de app de citas, y más).

- **`chatgpt-image-ad`** — creativos cargados de tipografía / imitación de interfaces. Usa el **endpoint dedicado `/api/v1/gpt4o-image/generate`** (no `/jobs/createTask`). Tamaños: `1:1`, `3:2`, `2:3`.
- **`nano-banana-image-ad`** — creativos fotorrealistas / lifestyle / con múltiples referencias, vía `/jobs/createTask`. Todos los ratios de Meta, incluido `4:5` (el vertical nativo del feed).
- **`image-ad-clone`** — una sola skill agnóstica del backend que hace ingeniería inversa de cualquier URL de anuncio existente y la convierte en una entrada nueva de la librería (te pregunta con qué generador validar en la Fase 1; opcionalmente valida contra el otro en la Fase 8).

Las imágenes de referencia van por **URL pública** (KIE no permite subir archivos). La salida son archivos de imagen; combínalo con la skill `meta-ad-builder` para publicarlos como anuncios pausados en Meta. **Lee primero `shared/skills/image-ad-prompting/OVERVIEW.md`** — ahí está el árbol de decisión, la matriz de compatibilidad de ratios por backend y los flujos estándar de generar / clonar. Validado en vivo de punta a punta contra la API de KIE.

---

### 🎞️ Pipelines de anuncios animados (varios pasos)

#### Anuncio 3D estilo Pixar

> "Haz un anuncio estilo Pixar para [producto] — mascota antropomorfizada, arco narrativo de 8 beats"

Fijar el cast → imágenes de storyboard con ChatGPT Image 2 (secuenciales, cada frame usa el anterior como referencia para mantener la identidad) → Seedance 2.0 imagen-a-video por beat (`bytedance/seedance-2`) → unir con ffmpeg + quemar subtítulos. Ver `shared/skills/pixar-style-ad/prompting/guide.md`.

#### Anuncio claymation / estilo Aardman

> "Haz un anuncio claymation — personajes de plastilina, narrado, de 60 a 115 segundos"

La misma columna vertebral que Pixar, con un arco narrado de 8 beats y texturas de plastilina. Storyboard con ChatGPT Image 2 (secuencial para la identidad, en paralelo para el gráfico del beat 5; si la textura de plastilina se aplana en los primeros planos, cae a `nano-banana-pro`) → Seedance 2.0 i2v por beat → unir con ffmpeg y la opción de trepidación stop-motion `fps=12,fps=24`. La voz en off se genera aparte (ElevenLabs) y se mezcla en la post. Ver `shared/skills/claymation-ad/prompting/guide.md`.

#### Miniaturas de YouTube (5 fórmulas de CTR)

> "Genera 10 variantes de miniatura para este video sobre ingeniería de prompts"

La skill `generate-youtube-thumbnail`: seña de paz/branding, comparación real vs IA, flujo de terminal, cara de sorpresa, split de antes/después. La identidad facial se fija con 5 o más URLs de referencia. Dispara el lote en paralelo contra Nano Banana 2. Ver `skills/generate-youtube-thumbnail/`.

#### Quemar subtítulos en un video terminado

> "Ponle subtítulos a este MP4"

Paso posterior que no usa KIE y funciona sobre cualquier fuente — Pixar, claymation, UGC o b-roll. HyperFrames + Whisper `medium.en` para transcribir → agrupa la transcripción palabra por palabra en frases legibles → renderiza solo los subtítulos en HTML sobre magenta `#ff00ff` → overlay con chroma-key de ffmpeg. Ver `shared/skills/caption-video/prompting/guide.md`.

---

### 🔄 Ingeniería inversa de creativos existentes

#### Analizar un video de referencia y convertirlo en plantilla de Seedance

> "Haz ingeniería inversa de esta URL de video y convertila en una plantilla reusable de Seedance"

El flujo `analyze-video` en `skills/kie-external-api/prompting/analyze-video/` extrae la estructura de un video de referencia y la convierte en una plantilla de prompt parametrizable para Seedance 2.0.

#### Clonar un anuncio de video para otro producto

> "Clona este anuncio de video para nuestro producto nuevo"

`skills/kie-external-api/prompting/clone-ad/` — de punta a punta: analiza la referencia → la adapta al producto nuevo → genera. El complemento de `analyze-video` cuando quieres publicar la versión clonada directamente.

#### Clonar un anuncio estático hacia la librería de prompts

> "Haz ingeniería inversa de esta URL de anuncio como plantilla reusable"

La skill `image-ad-clone` produce entradas parametrizables para la librería de 37 plantillas (ver arriba).

---

### 📤 Publicar creativos como anuncios pausados en Meta

> "Publica este creativo aprobado como anuncio pausado en mi cuenta"

La skill `meta-ad-builder` (en `shared/skills/`) toma la ruta de un creativo terminado y lo sube por la Meta Marketing API. Todos los anuncios se crean PAUSADOS — tú los revisas y los activas a mano en el Administrador de Anuncios. También tiene un camino de investigación para traer los anuncios de mayor inversión y los de la competencia. La autenticación va con las claves `META_*` en `.env`.

## Qué trae el pack

| Ruta | Qué hace |
|------|-------------|
| `skills/kie-external-api/` | **La skill principal.** Referencia de la API, guía de prompting, librerías de prompts por modelo (Seedance / Sora / Veo / Kling / Nano Banana) y los sub-flujos analyze-video y clone-ad. |
| `skills/generate-youtube-thumbnail/` | 5 fórmulas de miniatura de YouTube probadas por CTR, con disparo de lotes en paralelo contra Nano Banana 2. |
| `skills/chatgpt-image-ad/` | Anuncios estáticos de Meta vía `/api/v1/gpt4o-image/generate` (tipografía / imitación de interfaces). Validado en vivo. |
| `skills/nano-banana-image-ad/` | Anuncios estáticos de Meta vía Nano Banana 2 / Pro / Edit (fotorrealista / lifestyle). Validado en vivo. |
| `skills/image-ad-clone/` | Ingeniería inversa de una URL de anuncio existente hacia una entrada reusable de la librería. Agnóstico del backend — pregunta en la Fase 1 si validar con gpt-image-2 (vía `/gpt4o-image`) o con Nano Banana, y opcionalmente valida contra el otro en la Fase 8. |
| `shared/skills/image-ad-prompting/` | El cerebro compartido del ecosistema de anuncios: 37 plantillas validadas, sufijos de seguridad, formato de entrada y `OVERVIEW.md`. |
| `shared/skills/pixar-style-ad/` | Receta cruzada: anuncio de 8 beats con mascota antropomorfizada, storyboard con GPT Image 2 + Seedance 2.0 i2v. |
| `shared/skills/claymation-ad/` | Receta cruzada: anuncio narrado de 8 beats estilo Aardman; misma base que Pixar con opción de trepidación stop-motion. |
| `shared/skills/caption-video/` | Paso posterior: HyperFrames + Whisper + chroma-key de ffmpeg para quemar subtítulos en cualquier MP4 terminado. |
| `shared/skills/meta-ad-builder/` | Publica creativos terminados como anuncios pausados vía la Meta Marketing API. |
| `shared/scripts/check-context.sh` | Banner de `SessionStart` — lista las skills instaladas, chequea el estado de `.env` y `MASTER_CONTEXT.md`, y muestra los punteros del ecosistema. Está enganchado en `.claude/settings.json`. |
| `MASTER_CONTEXT.template.md` | Plantilla del contexto de tu espacio de trabajo (costos en créditos, voz de marca, hosting de imágenes, aprendizajes). |
| `MASTER_CONTEXT.md` | Tu copia personalizada (la crea el setup, no se sube a git). |
| `.env` | Tu API key (la crea el setup, nunca se sube). |
| `scripts/setup.sh` | Configuración inicial, una sola vez. |
| `scripts/sync-skill.sh` | Copia los cambios de las skills a `.claude/` y `.cursor/`. |
| `scripts/check-kie-env.sh` | Prueba la conectividad con la API. |
| `logs/kie-api.jsonl` | Log de solo-agregado de cada llamada de generación — modelo, duración, cantidad de referencias, taskId, estado y créditos cobrados. Es lo que alimenta las estimaciones de costo. Ver `logs/README.md`. **Se sube a git** (el historial de costos vale la pena; no se loguean claves ni prompts completos). |
| `references/` | Deja aquí tus imágenes de referencia (influencers, productos, estéticas) — está en gitignore. |
| `outputs/` | Carpetas de descarga por sesión (`outputs/{AAAA-MM-DD}-{slug}/`) — está en gitignore. |

## Tu API key

Tu key te autentica contra la API de KIE. Durante el setup la pegas una sola vez y el agente la usa desde `.env` automáticamente. Nunca hace falta que la pegues en el chat.

¿Todavía no tienes cuenta de KIE.ai? Créala aquí: **https://kie.ai**

Dónde está tu key: **[Dashboard de KIE → API Key](https://kie.ai/api-key)**

Para publicar en Meta (la skill `meta-ad-builder`) también vas a necesitar `META_ACCESS_TOKEN` y `META_AD_ACCOUNT_ID` en `.env` — el archivo `.env.example` ya tiene las filas de ejemplo.

## Las imágenes de referencia tienen que estar hosteadas

KIE acepta las referencias como **URLs públicas y alcanzables** (`imageUrls` para Veo, `input.image_input` para los modelos del marketplace, `filesUrl` para `/gpt4o-image`). **No hay subida de archivos.** Define tu estrategia de hosting desde el arranque y anótala en `MASTER_CONTEXT.md`, en la sección *Image hosting*:

- Tu propio bucket de R2 / S3 / Cloudinary
- Un host temporal como `0x0.st` o imgur
- Cualquier cosa que devuelva una URL pública que el backend de KIE pueda descargar

Si le pasas una ruta local y no hay hosting configurado, el agente **se detiene y te pregunta** cómo hostear el archivo. Los scripts de anuncios además hacen un HEAD a cada URL antes de enviarla (pasa `--skip-url-check` si tu host bloquea HEAD).

## Patrón asíncrono y webhooks

Toda generación en KIE es asíncrona. Hay dos formas de obtener el resultado:

- **Polling (por defecto)** — el agente consulta el endpoint `record-info` correspondiente cada ~30 segundos:
  - Veo: `GET /api/v1/veo/record-info?taskId=…` (`successFlag` 0/1/2)
  - ChatGPT Image 2: `GET /api/v1/gpt4o-image/record-info?taskId=…` (`successFlag` 0/1/2)
  - Jobs (Sora / Kling / Nano Banana / Seedance / etc.): `GET /api/v1/jobs/recordInfo?taskId=…` (`state` waiting/queuing/generating/success/fail)
- **Webhook** — pasa `callBackUrl` en el cuerpo del request y KIE te hace un POST con el resultado final. Úsalo en producción o para trabajos largos, si tienes un endpoint levantado.

Duraciones típicas: Veo ~2–5 min, Sora 2 ~2–5 min, Seedance 2 ~3–4 min, Nano Banana / ChatGPT Image ~20–60 seg. KIE limita a 20 requests cada 10 segundos, con hasta 100 tareas concurrentes — ante un 429, espera con jitter.

## Memoria del proyecto

`MASTER_CONTEXT.md` es la memoria viva de tu espacio de trabajo. El agente lo lee al inicio de cada sesión y escribe ahí lo que va aprendiendo. Guarda:

- **Hosting de imágenes** — cómo conviertes los archivos de `references/` en URLs públicas (escríbelo una vez y el agente deja de preguntar)
- **Costos en créditos** — las tarifas por modelo, cargadas una sola vez
- **Nombres de modelo confirmados** — los valores exactos de `model` que el marketplace de KIE expone en tu cuenta (el catálogo cambia)
- **Variante por defecto** — por ejemplo, Nano Banana 2 vs Pro para generar imágenes
- **Voz de marca** — opcional: tono, audiencia y preferencias de vocabulario
- **Aprendizajes de la API** — las mañas de KIE que le sirven al agente para trabajar mejor
- **Changelog** — notas fechadas de cada sesión

## Modelos soportados

| Modelo | Tipo | String de `model` | Ideal para | Notas |
|-------|------|----------------|----------|-------|
| **Seedance 2.0** | Video (4–15s) | `bytedance/seedance-2` | El modelo estrella. UGC, revelación premium, producto héroe, lookbook, demo de funcionalidades. Audio nativo. | Trae 5 fórmulas de prompt. Endpoint: `POST /api/v1/jobs/createTask`. |
| **Seedance 2.0 Fast** | Video | `bytedance/seedance-2-fast` | Seedance más barato y rápido, para iterar. | Mismo endpoint. |
| **Seedance 1.5 Pro** | Video | `bytedance/seedance-1.5-pro` | Seedance Pro legacy. | Mismo endpoint. |
| **Veo 3.1** | Video (~8s) | `veo3_fast` (por defecto), `veo3`, `veo3_lite` | Animar frames iniciales (REFERENCE_2_VIDEO), texto a video, transiciones entre primer y último frame. El camino de imagen UGC → video. | Endpoint: `POST /api/v1/veo/generate`. Los modos de `generationType` son mutuamente excluyentes; `REFERENCE_2_VIDEO` solo funciona con `veo3_fast`. |
| **Sora 2** | Video (hasta 20s) | `sora-2-text-to-video` | Texto a video de larga duración. | Endpoint: `POST /api/v1/jobs/createTask`. La duración se elige según las palabras del guion. |
| **Sora 2 Pro** | Video | `sora-2-pro-text-to-video` | Sora 2 tier premium para piezas principales. | Mismo endpoint. |
| **Sora 2 imagen a video** | Video | `sora-2-image-to-video` | Arrancar un video de Sora desde una URL pública de imagen. | Mismo endpoint. |
| **Kling 3.0** | Video | según marketplace (`kling-3`, `kling-3-pro`, etc.) | B-roll, clips cinematográficos. | Confirma el string en [kie.ai/market](https://kie.ai/market) para tu cuenta. |
| **Nano Banana 2** (por defecto) | Imagen | `nano-banana-2` | Imágenes UGC, character sheets, fotos de producto, recreación de influencers, creativos de anuncios. | Endpoint: `POST /api/v1/jobs/createTask`. |
| **Nano Banana Pro** | Imagen | `nano-banana-pro` | Calidad premium (Gemini 3 Pro Image). Mantiene la identidad del personaje más firme entre lotes. | Mismo endpoint. |
| **Nano Banana Edit** | Imagen | `nano-banana-edit` | Retocar / editar una imagen existente. | Mismo endpoint. |
| **Nano Banana** (legacy) | Imagen | `nano-banana` | Variante original, rara vez necesaria. | Mismo endpoint. |
| **ChatGPT Image 2** | Imagen | (sin parámetro de modelo — lo elige el endpoint) | Creativos estáticos cargados de tipografía / imitación de interfaces. Lo usan la skill `chatgpt-image-ad` y los pipelines de storyboard de Pixar y claymation. | **Endpoint dedicado:** `POST /api/v1/gpt4o-image/generate`. Tamaños: `1:1`, `3:2`, `2:3`. Hasta 5 URLs de referencia en `filesUrl[]`. |

El costo se presenta siempre como **estimación** antes de cada generación; el agente lee `logs/kie-api.jsonl` para sacar los valores históricos que coinciden con tu configuración. **Verifica siempre los strings exactos de `model` en la página del marketplace de tu cuenta** — KIE agrega y renombra modelos a medida que los proveedores actualizan. Los strings confirmados se escriben solos en `MASTER_CONTEXT.md`.

## Imágenes de referencia

Deja tus imágenes en la carpeta `references/` y el agente las va a usar automáticamente (una vez que tengas el hosting configurado):

- **`references/influencers/`** — Fotos de personas para recrear como contenido generado con IA
- **`references/products/`** — Fotos de producto para videos de showcase e imágenes principales
- **`references/aesthetics/`** — Referencias de estilo organizadas por vibe (`ugc-selfie/`, `cinematic/`, etc.)

Las imágenes quedan en tu máquina — el contenido de la carpeta está en gitignore. El agente escala automáticamente con Lanczos cualquier referencia por debajo de 1024px (el mínimo que pide la API) antes de subirla a tu host.

## Editar las skills

La fuente canónica de cada skill vive en `skills/<nombre>/`. Después de editar cualquier archivo ahí, corre:

```bash
./scripts/sync-skill.sh
```

Esto copia tus cambios a `.claude/skills/` y `.cursor/skills/` (que están en gitignore — son copias generadas). El hook `SessionStart` de `.claude/settings.json` también lo corre solo cuando abres Claude Code.

## Mantenerte al día

Este repo se actualiza seguido — entran plantillas nuevas a la librería de prompts, se agregan flujos y se corrigen errores. Para mantenerte sincronizado:

- **Al inicio de cada sesión de Claude Code**, el hook `check-context.sh` corre `git fetch origin` automáticamente (con timeout de 10 segundos, nunca te bloquea). Si tu copia local está atrasada, el banner te lista los commits pendientes y te dice que corras `git pull`. No hay pulls sorpresa — solo te avisa.
- **Para traer actualizaciones a mano:** `git pull origin main` desde la raíz del repo. Si hiciste cambios locales en archivos versionados, guárdalos primero: `git stash && git pull && git stash pop`.
- **Si hiciste un fork en GitHub:** toca el botón "Sync fork" en la página de tu fork para alinearlo con este repo, y después haz `git pull` en tu máquina.
- **Tus personalizaciones:** `.env`, `MASTER_CONTEXT.md`, `references/`, `outputs/` y `logs/` están todos en gitignore — sobreviven a cada actualización. Si personalizas un archivo de una skill (por ejemplo, ajustas un SKILL.md para tu marca), espera posibles conflictos al hacer `git pull` — si no quieres que las actualizaciones los toquen, guarda tus versiones en una ruta no versionada (por ejemplo `local-skills/`).

## Seguridad

- `.env` está en gitignore — nunca se sube
- `MASTER_CONTEXT.md` está en gitignore — contiene tus tablas de costos, rutas de hosting y strings de modelo confirmados
- `logs/kie-api.jsonl` SÍ se sube (el historial de costos vale la pena), pero nunca loguea claves, headers ni el texto completo de los prompts — ver `logs/README.md`
- Nunca pegues API keys en issues de GitHub ni en chats públicos
- Todo anuncio creado por `meta-ad-builder` se crea **PAUSADO** — nada sale al aire sin que tú lo actives a mano en el Administrador de Anuncios

## Guías de prompting de cada proveedor

| Modelo | Guía |
|-------|--------|
| Seedance 2.0 | Alineado a la guía oficial de prompting de Seedance de ByteDance (la skill lo resume en `skills/kie-external-api/prompting/prompt-library/seedance-2.md`) |
| Veo 3.1 | [Google Cloud — Veo 3.1](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1) |
| Sora 2 | [OpenAI — guía de prompting de Sora 2](https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide) |
| Kling 3.0 | [Kling — guía de uso](https://kling.ai/quickstart/klingai-video-3-model-user-guide) |
| Nano Banana | [Google Cloud — Nano Banana](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-nano-banana) |
| ChatGPT Image 2 | Guía de generación de imágenes de OpenAI (resumida en `shared/skills/chatgpt-image-ad/prompting/guide.md`, con las fortalezas y los límites del modelo) |

## Documentación de la API

- **Docs de KIE:** [docs.kie.ai](https://docs.kie.ai)
- **Marketplace de modelos:** [kie.ai/market](https://kie.ai/market) — verifica los strings de `model` actuales
- **Precios:** [kie.ai/pricing](https://kie.ai/pricing)
- **Historial de tareas:** [kie.ai/logs](https://kie.ai/logs) — historial del lado del servidor, estado y consumo de créditos

## Comunidad · MÁQUINA IA 🚀

Este repo es una pieza del **Sistema 1 — el Marketero IA**: la parte que produce el creativo. El resto del sistema (cómo lo distribuyes, cómo capturas el lead y cómo lo cierras) vive en la comunidad.

**[skool.com/maquinadeleads](https://www.skool.com/maquinadeleads/about)** — en español, para LATAM:

- **Q&A en vivo cada semana** — te ayudamos con tu caso, en pantalla compartida
- **Bases de Claude** — desde cero, si nunca usaste IA
- **Los 5 Sistemas** — Marketero · Setter · Closer · Analista · Asistente, con sus bots y workflows ya armados
- **Snapshots de GHL y templates de n8n / Make** — importables, listos para producción
- **Facebook Ads Mastery · Video Editing Mastery · Planes de contenido** — qué hacer con el creativo una vez que lo generaste
- **El Drop del Mes** — un recurso nuevo cada mes, más una masterclass mensual

Si te trabas con este repo, ahí es donde se resuelve.

## Otros asistentes de IA (Manus, Copilot, etc.)

Apunta tu asistente a [AGENTS.md](AGENTS.md) y a `MASTER_CONTEXT.md`, más las rutas de skills en `skills/` y `shared/skills/`. Los detalles están en [AGENTS.md](AGENTS.md).
