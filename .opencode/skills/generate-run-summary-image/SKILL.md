---
name: generate-run-summary-image
description: Generate a beautiful, story-ready image (1080x1920) summarizing a Garmin running activity. Fetches live data from Garmin MCP, renders an elegant HTML template with combined pace+HR chart, and converts to PNG via Playwright. Use whenever the user wants to create a visual summary of a run for social media — e.g. "gera uma imagem do meu treino", "faz um story do meu 10km", "cria imagem para postar da minha corrida", "gera um resumo visual do meu longo de sábado". Pairs with analyze-garmin-run: when an analysis already ran (or is requested together), reuse its data and inject its verdict as the analysis card.
---

# Generate Run Summary Image Skill

Generate a stunning, Instagram-stories-ready image (1080×1920) from any Garmin running activity with combined pace + heart rate chart.

## When to use

- User asks to create an image/story/post from a run
- User wants to share results visually
- User says "gera imagem", "faz um story", "cria um post", "resumo visual"

## Workflow

### Step 1 — Resolve the activity

Same resolution as `analyze-garmin-run`:
- "hoje" → today's date
- "ontem" → yesterday
- explicit date → that date
- "minha última corrida" → most recent running activity
- "meu 10km de sábado" → search by date + distance

### Step 2 — Fetch data (parallel)

```python
get_activity(activity_id)           → duration, distance, pace, HR, cadence, power
get_activity_splits(activity_id)    → per-split: pace, HR, elevation, time, intensity_type
get_weather(activity_id)            → temp, humidity, wind
get_vdot_zones()                    → read from calibrate-garmin-zones/vdot_zones.json
```

### Step 3 — Workout type (OPTIONAL — affects texts only)

The chart NEVER depends on the workout type: colors, bars and legend come 100% from Garmin's own `intensityType` data (see the de-para in "Rendering reference"). The type is only used for the story texts (title, structure badge, footer) and the fallback analysis.

If the user named the type in their message, pass it: `tempo` (sustentado), `interval` (tiros/intervalado), `race` (teste/prova), `long` (longão), `easy` (fácil/rodagem). If it is not explicit, either ask or **omit it** — omitted type renders neutral labels ("Corrida / X km") instead of inventing one.

### Step 4 — Build the data file

Write the fetched data to a JSON file, e.g. `~/.opencode/tmp/run_data_{activity_id}.json`:

```json
{
  "activity_id": "1234567890",
  "date": "Sáb, 10 Mai",
  "location": "Sua Cidade",
  "workout_type": "tempo",
  "analysis_text": "...",
  "vdot": 45.0,
  "splits": [
    {
      "distance_m": 1000,
      "duration_seconds": 308,
      "pace_seconds": 308,
      "avg_hr": 138,
      "elevation_gain": 11,
      "intensity": "WARMUP"
    }
  ]
}
```

- `workout_type`: **optional** — `tempo` | `interval` | `race` | `long` | `easy`. Affects ONLY the story texts; omit for neutral labels.
- `analysis_text`: **optional handoff** — the verdict distilled from `analyze-garmin-run` (see "Chaining" below). Without it, the script falls back to a naive built-in analysis.
- `vdot`: **optional** — from `.opencode/skills/calibrate-garmin-zones/vdot_zones.json`.
- `splits[]`: per-km data from `get_activity_splits`; `intensity` is Garmin's own `intensityType` — structured workouts use `WARMUP` / `ACTIVE` (passo "corrida") / `RECOVERY` / `REST` / `WALK` / `COOLDOWN` / `OTHER`; free runs (auto-lap) come as `INTERVAL`. Pass it through unchanged — never invent or reinterpret it.
- Optional text overrides (win over the type defaults): `title`, `highlight`, `structure`, `result_label`, `footer`, `vdot_label` — e.g. `structure: "8×800m"` when the real session structure is known.

### Step 5 — Generate the image

Run the script that lives next to this SKILL.md:

```bash
python generate_image.py --data-file run_data_{activity_id}.json [--output-dir DIR]
```

The script handles everything else (see "Rendering reference" below): split classification, chart proportions, SVG + legend, dynamic text, HTML render, and Playwright screenshot (1080×1920 @2x). Output: `run_summary_{activity_id}.png` — show it to the user with the file path.

## Rendering reference (what the script does internally)

- **Split classification — de-para 1:1 do `intensityType` do Garmin** (validado contra atividades reais; nada inventado):

  | Garmin `intensityType` | App Garmin (PT) | Cor | Legenda |
  |---|---|---|---|
  | `WARMUP` | Aquecimento | azul céu | Aquecimento |
  | `ACTIVE` / `RUN` | Corrida | indigo (herói) | Corrida |
  | `INTERVAL` | (auto-lap corrida livre) | indigo (herói) | Corrida |
  | `RECOVERY` | Recuperação | slate claro | Recuperação |
  | `REST` | Descanso | slate escuro | Descanso |
  | `COOLDOWN` | Desaquecimento | verde | Desaquecimento |
  | `WALK` | Caminhada | violeta | Caminhada |
  | `OTHER` | Outros | stone | Outros |
  | *(vazio)* | corrida livre | indigo (herói) | Corrida |

  Princípio da paleta: intensidade = energia da cor — o passo "Corrida" (bloco de trabalho) é o herói no indigo (acento do template, contraste máximo com a linha vermelha de FC); passivos (recuperação/descanso) em tons neutros de slate; bookends suaves (aquecimento azul céu, desaquecimento verde). As cores vivem em `COLORS` no script — fonte única: barras e pontos da legenda leem dali (a legenda injeta estilos inline).

  O tipo de treino (`workout_type`) NÃO participa da classificação — só dos textos.
- **Chart**: X-axis proportional to TIME (not distance); Y-axis inversely proportional to pace (3:00/km top → 7:00/km bottom, com clamp — passos mais lentos ficam no fundo com altura mínima); red HR line (#ef4444) scaled 110–190 bpm with dots at each split; pace labels on bars; gradient fills per step type. Details in "Chart specifications" below.
- **Dynamic legend**: only step types present in the data (labels do app do Garmin) + always "FC".
- **Structure badge (default)**: derived from the real steps, summing distance per type — e.g. "Aquecimento 2,0km + Corrida 7,1km + Desaquecimento 2,0km". Overridable via `structure`.
- **Dynamic text**: `workout_type` sets title/highlight/footer defaults (`tempo` → "Treino de Tempo"; omitted → neutral "Corrida / X km"); overrides win.
- **Analysis card**: uses `analysis_text` when present; otherwise the naive built-in fallback.
- **VDOT**: appended to the main card distance line when `vdot` is present in the JSON.

## Chart specifications

- **ViewBox**: 0 0 980 400
- **Chart area**: x=70 to x=930, y=30 to y=320
- **Grid**: Horizontal lines at each minute mark
- **Pace labels**: On top of bars
- **HR line**: Red (#ef4444), stroke-width=4, round caps
- **HR dots**: Red circles, r=6
- **Bar colors**: pelo tipo de passo do Garmin (de-para acima): aquecimento=azul céu, corrida=indigo, recuperação=slate claro, descanso=slate escuro, desaquecimento=verde, caminhada=violeta, outros=stone — todas definidas em `COLORS` (fonte única; a legenda injeta os gradientes inline)

## Chaining with analyze-garmin-run

Both skills share the activity resolution and core data fetch. When the user asks for analysis + image together, or asks for the image right after an analysis:

**Coming from `analyze-garmin-run` (preferred flow):**
- **Skip Steps 1–3** — the activity is already resolved, the data is already fetched, and the intent is already determined there. Reuse the fetched activity + splits + weather; do not re-call Garmin.
- **Pass the intent as `workout_type`** (texts only): sustentado/tempo → `tempo`, tiros/intervalado → `interval`, race/teste → `race`, longão → `long`, fácil/rodagem → `easy` — or omit for neutral labels. The chart needs nothing from the type: colors and legend come from Garmin's `intensityType` alone.
- **Inject the verdict**: the analysis skill distills its verdict into 2–3 plain-text sentences in Portuguese (≤ ~320 chars) passed as `analysis_text` — it replaces the naive built-in analysis in the card. The card inserts raw HTML: markdown does NOT render; `<b>` works (styled orange).
- Build the JSON (Step 4) from the already-fetched data and run Step 5 directly.

**No prior analysis:** proceed normally — the card uses the built-in fallback. Optionally suggest running `analyze-garmin-run` first for a richer analysis card.

## Edge cases

- **No splits**: Show only summary stats, skip chart
- **Very short run** (< 3 splits): Show simplified chart
- **No VDOT zones**: omit VDOT from the main card (all other metrics unaffected)
- **Non-running activity**: Adapt (cycling = power-based, etc.)
- **Missing HR data**: Show only pace bars without HR line

## Example triggers

- "gera uma imagem do meu treino de hoje"
- "faz um story do meu 10km de ontem"
- "cria um post da minha corrida de sábado"
- "resumo visual do meu longo"
- "quero compartilhar meu resultado de hoje"
