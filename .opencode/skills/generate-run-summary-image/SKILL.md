---
name: generate-run-summary-image
description: Generate a beautiful, story-ready image (1080x1920) summarizing a Garmin running activity. Fetches live data from Garmin MCP, renders an elegant HTML template with combined pace+HR chart, and converts to PNG via Playwright. Use whenever the user wants to create a visual summary of a run for social media — e.g. "gera uma imagem do meu treino", "faz um story do meu 10km", "cria imagem para postar da minha corrida", "gera um resumo visual do meu longo de sábado".
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

### Step 3 — Determine workout type (ASK if not explicit)

**CRITICAL: Never infer the workout type automatically. Always ask the user if not explicit.**

Check if the user mentioned the workout type in their message:
- "teste" / "test" / "prova" → race
- "tiros" / "intervalado" / "8x800" → interval
- "longão" / "longo" → long
- "fácil" / "easy" / "recuperação" → easy

**If the type is NOT explicit in the message, ASK the user:**
> "Que tipo de treino foi esse? (teste, tiros, longão, corrida fácil)"

Only proceed after the user confirms the type.

### Step 4 — Classify splits by type

Based on the confirmed workout type:
- **interval**: Use `intensity_type` from Garmin (WARMUP/ACTIVE/RECOVERY/COOLDOWN)
- **race/long/easy**: All splits are "race" (Corrida) — Indigo

**Never infer split types from pace or intensity fields for continuous runs.**

### Step 4 — Calculate chart proportions

**X-axis: proportional to TIME (not distance)**
```
total_time = sum of all split durations (seconds)
available_width = 860px (from x=70 to x=930)
scale = available_width / total_time
each_split_width = split_duration * scale
```

**Y-axis: inversely proportional to pace, aligned to axis labels**
```
min_pace = 180 (3:00/km) → y=40 (top)
max_pace = 420 (7:00/km) → y=320 (bottom)
normalized = (pace_sec - min_pace) / (max_pace - min_pace)
y = 40 + normalized * 280
height = 320 - y
```

**HR line (red #ef4444):**
```
hr_min = 110 bpm, hr_max = 190 bpm
hr_y = 320 - ((hr - hr_min) / (hr_max - hr_min)) * 280
```

### Step 5 — Generate SVG chart

Build inline SVG with:
- Grid lines (horizontal at 3:00, 4:00, 5:00, 6:00, 7:00/km)
- Y-axis labels (left = pace, right = HR in red)
- Colored bars for each split (width ∝ time, height ∝ inverse pace)
- Red polyline (#ef4444, stroke-width=4) connecting HR values
- Red dots at each HR data point
- Pace labels on top of bars
- Gradient fills for each bar

### Step 6 — Dynamic legend

Show only legend items for split types that exist in the data:
- "warm" exists → show "Aquecimento" (blue)
- "race" exists → show "Corrida" (indigo)
- "rec" exists → show "Recuperação" (green)
- "cool" exists → show "Desaquecimento" (gray)
- Always show "FC" (red)

### Step 7 — Dynamic text content

**Title & Highlight:**
- Interval workout: "Treino de Tiros" / "8×800m"
- Race/test: "Teste de 10K" / "10K"
- Long run: "Longão" / distance
- Easy run: "Corrida" / "Fácil"
- Default: "Corrida" / date

**Workout structure badge:**
- Interval: "Aquecimento + 8×800m + Desaquecimento"
- Race: "Prova de 10K"
- Long: "Longão de X km"
- Easy: "Corrida fácil"

**Result label:**
- Race/test: "Tempo Final"
- Interval: "Tempo Total"
- Default: "Tempo Total"

**Footer text (dynamic by workout type):**
- Interval: "Tiros é velocidade"
- Race: "Correr é liberdade"
- Long: "Correr é liberdade"
- Easy: "Correr é liberdade"
- Default: "Correr é liberdade"

**VDOT card (if available):**
- Interval: "Consistência" / range of work rep paces
- Race: "VDOT" / value
- Long: "VDOT" / value
- Easy: "VDOT" / value

### Step 8 — Render and screenshot

1. Render HTML template (simple string replacement, no Jinja2 needed)
2. Save to `~/.opencode/tmp/run_summary_{activity_id}.html`
3. Screenshot with Playwright (viewport 1080×1920, deviceScaleFactor=2)
4. Save to `~/.opencode/tmp/run_summary_{activity_id}.png`
5. Show image to user with file path

## Chart specifications

- **ViewBox**: 0 0 980 400
- **Chart area**: x=70 to x=930, y=30 to y=320
- **Grid**: Horizontal lines at each minute mark
- **Pace labels**: On top of bars
- **HR line**: Red (#ef4444), stroke-width=4, round caps
- **HR dots**: Red circles, r=6
- **Bar colors**: By split type (warm=blue, race=indigo, rec=green, cool=gray, int=orange)

## Edge cases

- **No splits**: Show only summary stats, skip chart
- **Very short run** (< 3 splits): Show simplified chart
- **No VDOT zones**: Skip VDOT card, show only metrics
- **Non-running activity**: Adapt (cycling = power-based, etc.)
- **Missing HR data**: Show only pace bars without HR line

## Example triggers

- "gera uma imagem do meu treino de hoje"
- "faz um story do meu 10km de ontem"
- "cria um post da minha corrida de sábado"
- "resumo visual do meu longo"
- "quero compartilhar meu resultado de hoje"
