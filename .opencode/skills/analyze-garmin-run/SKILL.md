---
name: analyze-garmin-run
description: Analyze and evaluate running workouts against personalized Jack Daniels VDOT pace zones (loaded from vdot_zones.json), Garmin's threshold-based HR zones, and full context from Garmin (elevation, weather, sleep, HRV, resting HR, training readiness, training load). Use this skill whenever the user asks to evaluate, review, critique, or analyze a run — e.g. "avalia meu treino de hoje", "como foi a corrida de ontem", "analisa minha série de treinos da semana", "avalie o longão de sábado". Can chain into generate-run-summary-image to attach the verdict to a shareable story image when the user also asks for a visual summary.
---

# Analyze Garmin Run Skill

Evaluate runs against their **intended training purpose**, combining two zone systems (pace + heart rate) with full physiological and environmental context. All analysis is done by fetching live data from the Garmin MCP — nothing is cached or assumed.

## Design principles

1. **Pace zones come from `vdot_zones.json`** — Garmin has no concept of pace zones, so they are calculated from the athlete's last test result using the Jack Daniels VDOT formula. The zones are stored in `.opencode/skills/calibrate-garmin-zones/vdot_zones.json`. Everything else (HR zones, thresholds, load, readiness) is fetched live from Garmin so it always reflects the current configured values.
2. **Intent matters more than numbers** — always ask or infer the intended workout type (easy / tempo / threshold / long run / progression / race) and judge execution against THAT, not against a generic ideal. An easy run run too fast is a failure even if the pace is "impressive".
3. **Context is an excuse or a confirmation, never decoration** — heat, humidity, elevation, poor sleep, low HRV, low readiness must explain deviations or reinforce that the session was well-executed. If context doesn't change the verdict, keep it to one line.
4. **Everything relative to personal baseline** — sleep/HRV/RHR are compared to the athlete's own recent trend (Garmin's own status labels: balanced/balanced/low etc.), never against generic population numbers.

## Pace Zones (from vdot_zones.json)

**First execution:** Check if `.opencode/skills/calibrate-garmin-zones/vdot_zones.json` exists. If not, instruct the user to run the `calibrate-garmin-zones` skill first to calculate their personal zones.

**Loading zones:** Read the JSON file and use the zones defined there. The file contains:
- `vdot`: the calculated VDOT value
- `source`: description of the test used (e.g., "10K em 43:16")
- `test_date`: when the test was performed
- `zones`: the 5 pace zones (easy, marathon, threshold, interval, repetition) with pace ranges and m/s values

**Recalibration rule:** if the user reports a new test result (any distance), offer to run the `calibrate-garmin-zones` skill again to recalculate the zones. Never silently change the zones.

**Heat adjustment:** in hot/humid conditions (>25°C or >70% humidity), easy runs should be judged by **effort (HR + perceived effort)**, not pace — a slow pace in heat is correct execution. Suggest the physiological drift allowance (roughly 2–4% slower per 5°C above ~18°C) rather than penalizing it.

## Data fetch protocol

### Step 1 — Resolve the activity
- "hoje"/"de hoje" → `get_activities_by_date` with today's date
- "ontem" → previous day
- explicit date → that date
- "minha última corrida" → `get_activities` (limit 5), first `running` type
- "essa semana" → `get_activities_by_date` over the week range
- Multiple activities in range → list them and ask which one (or analyze all if asked for a series/week review)

### Step 2 — Core activity data (parallel calls)
```
get_activity(activity_id)              → duration, distance, pace, HR, cadence, power,
                                          stride, GCT, vertical oscillation, TE, load,
                                          feel/RPE, recovery HR, body battery impact
get_activity_splits(activity_id)       → per-km laps: pace, HR, cadence, power, elevation
get_training_effect(activity_id)       → aerobic/anaerobic TE + label + load
get_activity_hr_in_timezones(activity_id) → time in each configured HR zone
```

### Step 3 — Context (parallel calls; same date as activity start)
```
get_activity_weather(activity_id)      → temp, humidity, wind (note: "tava bem calor"
                                          from user should be cross-checked here)
get_sleep_summary(date)                → sleep score, duration, deep/REM, interruptions
get_hrv_data(date) or get_hrv_trend(start,end) → HRV status vs personal baseline
get_rhr_day(date)                      → resting HR vs baseline
get_training_readiness(date)           → readiness score + contributing factors
get_stats(date)                        → Body Battery, stress, steps (partial-day caveats)
```
Skip gracefully if any call fails — analysis proceeds with available data, noting the gap.

### Step 4 — HR zone configuration (only if not yet fetched this session)
```
get_heart_rate_zones()                 → current threshold-based zone config
```
**Never hardcode HR zones.** Use what Garmin returns.

**IMPORTANT — Multiple zone configs:** The API may return multiple zone configurations (e.g., `DEFAULT` for general sports and `RUNNING` for running-specific). **Always use the `RUNNING` config when available** for running activities. Only fall back to `DEFAULT` if no `RUNNING` config exists.

### Step 5 — Deep dives (only when relevant)
- Strength work → `get_activity_exercise_sets`
- User asks about power/VI/NP details on rides → `get_activity_fit_data`
- User questions the data itself → `get_activity_fit_messages`
- Week/month review → `get_training_load_trend`, `get_training_status`, `get_training_load_balance`

## Analysis framework

Compute and evaluate in this order:

### A. Execution vs intent (the core verdict)
1. **Determine intent**: from activity name, user statement, or workout structure (even splits = steady; HR pattern = intervals). If unclear and it matters, ask.
2. **Pace zone classification**: classify overall AND each split into a VDOT zone.
   - % of time in intended zone vs wrong zones
   - For easy runs: was pace ≤5:38 (in-range) or too fast? Was HR capped instead?
   - For threshold: was pace ~4:15 with HR in LTHR zone?
   - For intervals: work reps within 3:54 ±2s/km, recoveries genuinely easy?
3. **HR zone cross-check**: time in Garmin's zones (from `get_activity_hr_in_timezones`) vs what the intent demands. Easy runs should be predominantly zone 1–2; threshold work in zone 3–4.

### B. Consistency & drift metrics
- **Negative/positive split**: compare first vs second half per-km paces
- **Cardiac drift**: HR at same pace early vs late; flag if HR rises >5–8 bpm at equal pace, or drift coefficient >10% per hour
- **Cadence fade**: avg cadence first vs last km (flag drop >3 spm)
- **Pace variability**: stddev of per-km pace for steady runs
- **HR vs pace decoupling**: % decoupling = (pace change % vs HR change %) over the run; >5% for runs ≥60min = meaningful aerobic inefficiency
- **Elevation impact per split**: When a split has significantly more elevation gain than others (>50% more than average), explicitly call it out as the reason for slower pace + higher HR. Show the correlation: "Split X: +YYm elevation → pace Z, HR W — explain the deviation rather than judging it." This is especially important for trail runs or hilly courses where elevation is the primary workout stressor.

### C. Context modifiers (each must change or confirm the verdict)
- **Weather**: temp/humidity → adjust expectations for easy pace; heat explains high HR at low pace
- **Elevation**: total gain, per-km gain on slow splits; grade-adjust the pace mentally (±~5–8s/km per 1% avg grade); explain pace drops on climbs
- **Sleep**: duration + score + efficiency vs their own baseline; poor sleep (<6h or score well below their norm) raises expected HR at given pace by a few bpm
- **HRV / RHR**: Garmin's own status (balanced / low / high) — low HRV + elevated RHR = fatigue flag, connects to readiness
- **Readiness / Body Battery**: if readiness is low, a hard session is risky; if the user ignored it and performed well, note it as resilience; if they blew up, note it as cause
- **Training load**: acute effect on load, TE interpretation (was the TE what the intent should produce? easy run → TE 1–2; tempo → 3–4; interval → 4–5)
- **Feel/RPE** (`workout_feel`, `workout_rpe`): mismatch analysis — felt hard (low feel score) but metrics say easy = accumulated fatigue

### D. Verdict rules
- **On-target**: execution matched intent within zone tolerances → reinforce, state what went right in 2–3 specifics
- **Off-target — too hard**: easy run in threshold zone, HR above cap → warn about aerobic benefit loss + fatigue cost + suggest corrective pacing for next run
- **Off-target — too easy**: intervals/threshold not reached → suggest adjustments
- **Context-explained**: deviation fully explained by heat/elevation/fatigue → verdict becomes "appropriate adjustment" with evidence
- **Fatigue signal**: poor HRV/readiness + high HR at easy pace + low feel score → recommend recovery day, cite the 2–3 converging signals

## Output format (respond in Portuguese — user's language)

Structure every single-activity analysis as:

```markdown
## 🏃 [Activity name] — [date]

**Resumo**: distance, time, avg pace, avg/max HR, TE + label (one line)

### Execução vs intenção
[intent] → [zone classification] → verdict ✅ / ⚠️ / ❌
- % tempo na zona alvo, splits fora da faixa

### Métricas de consistência
- splits, drift cardíaco, cadência, decoupling (table if ≥8km)

### Contexto
[weather, elevation, sleep, HRV, RHR, readiness — only what mattered]

### Verdict + recomendação
[2–3 bullet points: what worked, what to change next time]
```

For **series/week reviews**, use a comparison table (date, type, pace, zone match, TE, sleep, readiness, note) and call out trends: accumulating load, drifting easy paces, sleep degradation, repeated execution errors.

## Chaining with generate-run-summary-image (visual summary)

When the user asks for an image/story/post of the same run — either in the same request ("analisa meu treino e gera um story") or right after the analysis — chain into the `generate-run-summary-image` skill instead of restarting it from scratch:

1. **Skip its Steps 1–3**: the activity is already resolved, the data is fetched, and the intent is already determined here. Reuse the fetched activity + splits + weather; do not re-call Garmin.
2. **Distill the verdict** into 2–3 plain-text sentences in Portuguese (≤ ~320 chars) for the image's "Análise do Treino" card: lead with the verdict in words (e.g. "Excelente execução" / "Execução acima do alvo" / "Ajuste adequado ao contexto"), then the strongest 1–2 findings. This replaces the image skill's naive auto-generated analysis. The card inserts raw HTML: markdown does NOT render; `<b>` works (styled orange).
3. **Pass the intent as `workout_type`** (affects texts only — the image chart is driven 100% by Garmin's `intensityType` data): sustentado/tempo → `tempo`, tiros/intervalado → `interval`, race/teste → `race`, longão → `long`, fácil/rodagem → `easy`; omit for neutral labels.
4. Build the JSON data file from the already-fetched data (`activity_id`, `date`, `location`, `splits` with Garmin's `intensityType` passed through unchanged, `vdot`) plus `workout_type` and the distilled `analysis_text`, then run the image script (its Step 5). Write the data file via a small Python builder script (see the Step 4 pitfall note in the image skill) — raw JSON passed directly as file-write tool content can be parsed as an object and rejected.

Never fabricate splits or metrics in the handoff — if a field wasn't fetched, leave it out of the JSON.

## Triggers (examples)

- "avalia o treino de hoje" / "como foi meu treino?"
- "analisa a corrida de ontem"
- "avalie minha semana de treinos"
- "fiz 10km fácil, foi fácil mesmo?"
- "por que minha FC subiu tanto no final?"
- "compare meu último mês de treinos"

## Edge cases

- **No activity found**: say so and offer to analyze the most recent run instead
- **Activity is not a run** (cycling, strength, walk): adapt — swap pace zones for power/HR zones; for strength, use exercise sets and TE only
- **Race** (event_type == "race"): judge against race performance norms, not training zones; compare with PR history
- **User states intent contradicts data** ("era pra ser fácil" but pace was threshold): this is the most valuable finding — lead with it, use context to explain *why* it happened
- **Missing context data**: one line noting the gap, never block the analysis
- **Multiple runs same day**: analyze each separately, then a combined load note

## Limitations

- Pace zones are static until a new PR is reported (Garmin cannot define them)
- Garmin sleep/HRV/RHR data availability depends on the watch being worn overnight
- `get_stats` partial-day fields for "today" are elapsed-hours accumulators, not full-day totals
- Cardiac drift computed from split-level data (1km granularity), not per-second
