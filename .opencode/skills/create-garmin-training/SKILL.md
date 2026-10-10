---
name: create-garmin-training
description: Create and schedule running workouts on Garmin Connect with personalized VDOT paces (loaded from vdot_zones.json), multi-segment workouts, and repeat intervals built as true Garmin repeat blocks (RepeatGroupDTO). Use this skill whenever the user wants to create any structured run: sustentado, tempo, threshold, intervals with recovery, repeats (2x3km, 5x800m, 10x(100m run + 100m recovery)), or complex multi-segment sessions. Automatically handles VDOT pace conversion, min/km to m/s conversion, builds the proper Garmin JSON, and schedules it on the calendar.
---

# Garmin Sustentado + Repeats Skill

Create and schedule running workouts with personalized VDOT paces, multiple segments, and repeats on Garmin Connect. 

Supports: simple sustained runs, tempo/threshold efforts, repeats built as true Garmin repeat blocks (e.g., 2x3km a threshold com 5min recovery, 10x(100m run + 100m recovery)), complex multi-segment workouts with warm-up/cool-down, and custom pace naming.

## Pace Zones (from vdot_zones.json)

**First execution:** Check if `.opencode/skills/calibrate-garmin-zones/vdot_zones.json` exists. If not, instruct the user to run the `calibrate-garmin-zones` skill first to calculate their personal zones.

**Loading zones:** Read the JSON file and use the zones defined there. The file contains:
- `vdot`: the calculated VDOT value
- `source`: description of the test used (e.g., "10K em 43:16")
- `test_date`: when the test was performed
- `zones`: the 5 pace zones (easy, marathon, threshold, interval, repetition) with pace ranges and m/s values

**How to use:** Say "threshold", "interval", "easy", etc. instead of min/km, and the skill converts automatically using the loaded zones. Alternatively, still use min/km (e.g., "4:15/km").

**Recalibration rule:** if the user reports a new test result (any distance), offer to run the `calibrate-garmin-zones` skill again to recalculate the zones. Never silently change the zones.

## When to Use

Use this skill whenever the user wants to create ANY structured running workout:
- Simple: **sustentado**, tempo, threshold efforts
- **Repeats**: 2x3km, 5x800m, 10x100m (with recovery between) — built as real repeat blocks in Garmin Connect
- Complex: **warm-up + main set + cool-down**, race-paced build-ups
- Multi-segment: Different pace zones using VDOT or manual min/km

Example phrases that should trigger this skill:
- "Cria um sustentado de 30min a threshold pro sábado"
- "Quero um treino: 1km easy, 2x3km threshold com 5min recovery, 1km easy — sexta"
- "Faz 6x800m a repetition com 2min recovery (ou 800m easy entre eles) próxima terça"
- "Treino: aquecimento 1km easy + 3x2km interval com 3min recovery + desaq 1km easy"
- "8km aquec easy + 10km threshold pro dia 17"
- "5x1km a 3:50/km com 2min recovery, plus 1km warm-up e 1km cool-down"
- "10x(100m run + 100m recovery) pro sábado"

## What It Does

1. **Parse inputs**: Extract all segments (distance/time + pace range) and date from natural language
2. **Convert paces**: Transform min/km to meters-per-second (m/s) for Garmin's API
3. **Build workout**: Create proper Garmin JSON with multiple segments, each with its own pace target
4. **Upload & schedule**: Send to Garmin Connect and add to calendar
5. **Confirm**: Return the workout ID, segments, and details

## Input Format

The user provides segments in natural language. Each can specify:

### Single segment
- **Distance OR Duration**: "8km", "30min", "2 miles"
- **Pace**: Either VDOT name (`easy`, `threshold`, `interval`, `repetition`, `marathon`) OR min/km (e.g., "4:15/km")
  - VDOT names auto-convert using the loaded zones from vdot_zones.json
  - Min/km still work (e.g., "4:10-4:20/km", single value like "4:15/km")

### Repeats
- **Format**: `Nx[distance/time] a [pace] com [recovery duration] [recovery pace]` or `Nx(work + recovery)`
- Example: `2x3km a threshold com 5min easy`, `6x800m a 3:50/km com 2min recovery`, `10x(100m run + 100m recovery)`
- All repeats become ONE `RepeatGroupDTO` block (see Repeat Group rules below) — never expanded into individual steps
- **Recovery**: Can be distance ("400m"), time ("3min"), or pace ("easy", "marathon")
  - If just "5min" → assume easy/recovery pace
  - If "5min no.target" → no specific pace target during recovery
  - If "800m easy" → 800m at easy pace

Overall inputs:
- **Segments/Repeats**: List in order, separated by "+" or commas
- **Date**: When to schedule
- **Name** (optional): Auto-generated from segments

### Examples of Different Formats

**VDOT-named paces (recommended):**
- "1km easy + 3km threshold + 1km easy — sexta"
- "2x3km threshold com 5min easy"
- "Warm-up 1km easy + 5x800m repetition com 2min + Cool-down 1km easy — próximo sábado"

**Mixed VDOT + manual min/km:**
- "1km easy + 2x3km a 4:10/km com 5min recovery + 1km easy"
- "Threshold 30min (4:15/km is your VDOT pace)"

**Repeats variations:**
- `2x3km threshold com 5min easy` — 2 reps, 5min easy recovery between
- `6x800m repetition com 2min no.target` — 6 reps, 2min unstructured recovery
- `3x2km interval com 2km easy` — 3 reps, 2km easy-pace recovery
- `5x1km a 3:50/km com 90sec recovery` — 5 reps, 90sec at default easy pace
- `10x(100m run + 100m recovery)` — 10 reps of 100m fast + 100m recovery, as ONE repeat block

## Conversions

### VDOT Name → Pace (from vdot_zones.json)

When user says "threshold", "easy", etc., use the zones loaded from `vdot_zones.json`:

| Zone | Pace | m/s |
|------|------|-----|
| Easy | From JSON (e.g., 5:07–5:38) | From JSON (e.g., 3.205–3.279) |
| Marathon | From JSON (e.g., 4:31) | From JSON (e.g., 3.684) |
| Threshold | From JSON (e.g., 4:15) | From JSON (e.g., 3.922) |
| Interval | From JSON (e.g., 3:54) | From JSON (e.g., 4.301) |
| Repetition | From JSON (e.g., 3:39) | From JSON (e.g., 4.567) |

**Important:** Always read the actual values from the JSON file. The values above are just examples from a VDOT 52 athlete.

For ranges (easy: 5:07–5:38):
- Slower end (5:38/km) = 3.205 m/s → targetValueOne
- Faster end (5:07/km) = 3.279 m/s → targetValueTwo

For single paces (threshold: 4:15):
- Use 4:15/km = 3.922 m/s for both targetValueOne and targetValueTwo

### min/km → m/s (Manual Paces)

Garmin API expects **meters per second**:

```
seconds_per_km = minutes × 60 + seconds
m/s = 1000 / seconds_per_km
```

Examples:
- 4:10/km = 250 sec/km → 1000÷250 = **4.0 m/s**
- 4:15/km = 255 sec/km → 1000÷255 = **3.922 m/s**
- 3:50/km = 230 sec/km → 1000÷230 = **4.348 m/s**
- 5:00/km = 300 sec/km → 1000÷300 = **3.333 m/s**

When a range is given (e.g., "4:10-4:20/km"):
- Slower (4:20/km = 260 sec) = 3.846 m/s → targetValueOne
- Faster (4:10/km = 250 sec) = 4.0 m/s → targetValueTwo

## Garmin Workout Structure

The skill creates a workout with multiple `workoutSteps`. Key points:

- **One step per segment**; each step can be **distance-based** (e.g., 3km) or **time-based** (e.g., 30min)
- **Repeats** are built as a `RepeatGroupDTO` block — a real repeat group in Garmin Connect, NOT expanded individual steps. `10x(100m + 100m rec)` = ONE group with 2 child steps iterated 10 times
- **Recovery steps** (inside the group) use `stepTypeId 4` (recovery) with `no.target` or optional pace

### Simple Example (Single Segment)

```json
{
  "workoutName": "Sustentado 30min",
  "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
    "workoutSteps": [
      {
        "stepOrder": 1,
        "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
        "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
        "endConditionValue": 1800,
        "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
        "targetValueOne": 3.846,
        "targetValueTwo": 4.0,
        "type": "ExecutableStepDTO"
      }
    ]
  }]
}
```

### Complex Example (Multiple Segments)

```json
{
  "workoutName": "Aquec + Prova · 18km",
  "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
    "workoutSteps": [
      {
        "stepOrder": 1,
        "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
        "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
        "endConditionValue": 8000,
        "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
        "targetValueOne": 3.03,
        "targetValueTwo": 3.279,
        "type": "ExecutableStepDTO"
      },
      {
        "stepOrder": 2,
        "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
        "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
        "endConditionValue": 10000,
        "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
        "targetValueOne": 3.846,
        "targetValueTwo": 4.0,
        "type": "ExecutableStepDTO"
      }
    ]
  }]
}
```

### Repeats Example (Repeat Group — RepeatGroupDTO)

Repeats are built as **one `RepeatGroupDTO` block**, not expanded steps. This renders as a collapsible repeat group in Garmin Connect and on the watch, just like workouts built in the Garmin Connect UI:

```json
{
  "workoutName": "1km easy + 2x3km threshold + 1km easy",
  "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
    "workoutSteps": [
      {
        "stepOrder": 1,
        "stepType": {"stepTypeId": 1, "stepTypeKey": "warmup"},
        "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
        "endConditionValue": 1000,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
        "type": "ExecutableStepDTO"
      },
      {
        "type": "RepeatGroupDTO",
        "stepOrder": 2,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat"},
        "numberOfIterations": 2,
        "smartRepeat": false,
        "endCondition": {"conditionTypeId": 7, "conditionTypeKey": "iterations"},
        "endConditionValue": 2,
        "workoutSteps": [
          {
            "stepOrder": 1,
            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
            "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
            "endConditionValue": 3000,
            "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
            "targetValueOne": 3.922,
            "targetValueTwo": 3.922,
            "type": "ExecutableStepDTO"
          },
          {
            "stepOrder": 2,
            "stepType": {"stepTypeId": 4, "stepTypeKey": "recovery"},
            "endCondition": {"conditionTypeId": 2, "conditionTypeKey": "time"},
            "endConditionValue": 300,
            "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
            "type": "ExecutableStepDTO"
          }
        ]
      },
      {
        "stepOrder": 3,
        "stepType": {"stepTypeId": 2, "stepTypeKey": "cooldown"},
        "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
        "endConditionValue": 1000,
        "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
        "type": "ExecutableStepDTO"
      }
    ]
  }]
}
```

**Repeat group rules (critical):**
- The group MUST include `endCondition: {"conditionTypeId": 7, "conditionTypeKey": "iterations"}` with `endConditionValue` = N — omitting `conditionTypeId: 7` makes the Garmin API **silently corrupt the repeat count**
- Also include `numberOfIterations: N`, `stepType: {"stepTypeId": 6, "stepTypeKey": "repeat"}`, and `"smartRepeat": false`
- **stepOrder**: top-level steps are sequential (warmup=1, group=2, cooldown=3). The group occupies ONE stepOrder; its **child steps restart numbering at 1** (1=work, 2=recovery)
- The recovery step runs after **every** rep, including the last one (same behavior as Garmin Connect's own UI) — account for it in total distance/time estimates
- Work and recovery child steps CAN use different end conditions (e.g., 800m distance work + 2min time recovery)

### Short Intervals Example: 10x(100m run + 100m recovery)

Short repeats use the same structure — distance-based child steps inside one repeat block:

```json
{
  "workoutName": "10x(100m run + 100m rec)",
  "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
  "workoutSegments": [{
    "segmentOrder": 1,
    "sportType": {"sportTypeId": 1, "sportTypeKey": "running"},
    "workoutSteps": [
      {
        "type": "RepeatGroupDTO",
        "stepOrder": 1,
        "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat"},
        "numberOfIterations": 10,
        "smartRepeat": false,
        "endCondition": {"conditionTypeId": 7, "conditionTypeKey": "iterations"},
        "endConditionValue": 10,
        "workoutSteps": [
          {
            "stepOrder": 1,
            "stepType": {"stepTypeId": 3, "stepTypeKey": "interval"},
            "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
            "endConditionValue": 100,
            "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
            "targetValueOne": 4.567,
            "targetValueTwo": 4.567,
            "type": "ExecutableStepDTO"
          },
          {
            "stepOrder": 2,
            "stepType": {"stepTypeId": 4, "stepTypeKey": "recovery"},
            "endCondition": {"conditionTypeId": 3, "conditionTypeKey": "distance"},
            "endConditionValue": 100,
            "targetType": {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"},
            "type": "ExecutableStepDTO"
          }
        ]
      }
    ]
  }]
}
```

For very short reps (<200m), GPS pace lags too much for a pace target to be useful — you can use `no.target` on the work step instead and let the athlete run by effort.

**Key fields:**
- `stepTypeId 1` = warmup (easy pace, no target)
- `stepTypeId 2` = cooldown (easy pace, no target)
- `stepTypeId 3` = interval/sustained (main effort with pace target)
- `stepTypeId 4` = recovery (inside repeat blocks, usually no pace target)
- `stepTypeId 6` = repeat (RepeatGroupDTO only)
- `endConditionId 2` = time-based (duration in **seconds**: 5min = 300s, 30min = 1800s)
- `endConditionId 3` = distance-based (in **meters**: 1km = 1000m, 3km = 3000m, 100m = 100)
- `endConditionId 7` = iterations (repeat count — REQUIRED on RepeatGroupDTO)
- `targetValueOne` = slower pace (lower m/s)
- `targetValueTwo` = faster pace (higher m/s)
- Top-level `workoutSteps` = sequential; a repeat group occupies ONE stepOrder and its children restart numbering at 1

## How to Use This Skill

When the user asks to create a sustentado:

1. **Extract the details** from their request (pace, duration, date, etc.)
2. **Convert paces** from min/km to m/s
3. **Determine the date** — if they say "sábado" or "Saturday", find the next Saturday; if they say "próxima terça", find next Tuesday, etc.
4. **Call `mcp__garmin__schedule_workouts`** with the JSON structure and `calendar_date` in YYYY-MM-DD format
5. **Report back** with workout ID, date, and details

## Example Workflows

### Simple Sustentado
**User:** "Cria um sustentado de 30min a 4:10-4:20/km pro sábado"

1. Parse: pace 4:10-4:20/km, duration 30min, date: next Saturday
2. Convert: 4:10/km = 4.0 m/s, 4:20/km = 3.846 m/s
3. Date: 2026-10-07 (Wed) → Saturday = 2026-10-10
4. Build JSON with single interval step (1800s)
5. Schedule: calendar_date="2026-10-10"
6. Result: "✅ Sustentado 30min agendado para sábado 10/10 (4:10-4:20/km). Workout ID: 1722836512"

### With VDOT Paces
**User:** "Treino: 1km easy, 2x3km threshold com 5min easy, 1km easy — sexta"

1. Parse: 1km easy, then 2 reps of 3km threshold, recovery 5min easy, 1km easy
2. Load zones from vdot_zones.json and convert paces:
   - Easy: from JSON (e.g., 5:07–5:38/km = 3.205–3.279 m/s)
   - Threshold: from JSON (e.g., 4:15/km = 3.922 m/s)
3. Date: Friday = 2026-10-11 (next Friday)
4. Build JSON with steps:
   - Step 1: 1km warmup (no target)
   - Step 2: RepeatGroupDTO with 2 iterations → child 1: 3km threshold (3.922 m/s), child 2: 5min recovery (no target)
   - Step 3: 1km cooldown (no target)
5. Schedule: calendar_date="2026-10-11"
6. Result: "✅ Treino de repeats agendado para sexta 11/10 (1km easy + 2x3km threshold + 1km easy). Total: 7km. Workout ID: XXXXX"

### Short Interval Repeats (Repeat Block)
**User:** "10x(100m run + 100m recovery) pro sábado"

1. Parse: 10 reps of 100m fast + 100m recovery, date: next Saturday
2. Build ONE RepeatGroupDTO with `numberOfIterations: 10`:
   - Child 1: 100m interval (distance: conditionTypeId 3, endConditionValue 100) — repetition pace from JSON (e.g., 4.567 m/s) or `no.target`
   - Child 2: 100m recovery (distance: conditionTypeId 3, endConditionValue 100, `no.target`)
3. Schedule: calendar_date="2026-10-10"
4. Result: "✅ 10x(100m + 100m rec) agendado para sábado 10/10. Bloco de repetição com 10 iterações. Workout ID: XXXXX"

## Pace Conversion Reference

Common paces used in running workouts:

| Min/km | Seconds | m/s | Use Case |
|--------|---------|-----|----------|
| 3:30/km | 210 | 4.762 | Race pace / VO2max efforts |
| 3:45/km | 225 | 4.444 | Tempo / threshold runs |
| 3:50/km | 230 | 4.348 | Fast tempo / FTP zone |
| 4:00/km | 240 | 4.167 | Sustentado / base pace |
| 4:10/km | 250 | 4.0 | Sustentado (moderate) |
| 4:15/km | 255 | 3.922 | Sustentado |
| 4:20/km | 260 | 3.846 | Sustentado (conservative) |
| 4:30/km | 270 | 3.704 | Build-up / progression |
| 4:45/km | 285 | 3.509 | Steady run |
| 4:50/km | 290 | 3.448 | Steady run |
| 5:00/km | 300 | 3.333 | Easy / recovery run |
| 5:05/km | 305 | 3.279 | Warm-up / easy |
| 5:30/km | 330 | 3.030 | Recovery / very easy |
| 6:00/km | 360 | 2.778 | Long slow distance |

**When you see a range like "4:10-4:20/km":**
- Slower end (4:20/km = 3.846 m/s) → `targetValueOne`
- Faster end (4:10/km = 4.0 m/s) → `targetValueTwo`
- (Counter-intuitive: higher m/s = faster pace)

## Edge Cases

- **Single pace** (not a range, e.g., "4:15/km"): Use the same value for both targetValueOne and targetValueTwo
- **Very short duration** (< 10min): Warn the user that this is quite short for a sustentado
- **Very long duration** (> 60min): Confirm they meant that duration
- **Date in past**: Assume next occurrence (e.g., if it's Wednesday and they say "terça", schedule for next Tuesday, not yesterday)
- **No date given**: Ask which day, or suggest "próximo sábado"

## Limitations

- Only creates **running** workouts (sportTypeId 1)
- **Repeats** are built as real Garmin repeat blocks (RepeatGroupDTO): one work step + one recovery step, iterated N times
- The recovery step inside a repeat block also runs after the LAST rep (same as Garmin Connect's UI)
- Each segment/repeat has a single pace target (no intra-segment variation)
- Cannot modify existing workouts — only create new ones
- All segments must be either **distance-based** OR **time-based** (cannot mix in one step); the work and recovery steps inside a repeat block CAN differ (e.g., 800m work + 2min recovery)
- Segments are executed sequentially (cannot do parallel/simultaneous efforts)
- **Not supported**: Repeat blocks with 3+ child steps or varying paces across reps, e.g. "2x(3km @ threshold + 2min easy + 1km @ interval)" — no nested repeat groups

## Tips for Best Results

### General
- **Segments**: Be explicit about what changes (distance/time + pace)
- **Pace**: VDOT names (easy, threshold, etc.) OR min/km values (e.g., "4:15/km", "4:10-4:20/km")
- **Date**: Clear format ("sábado", "Friday", "próxima terça", "11/10", "2026-10-12")
- **Names**: Auto-generated — customize if preferred

### Repeats
- **Format**: `Nx[distance] a [pace] com [recovery]` or `Nx(work + recovery)`
  - Good: "2x3km threshold com 5min easy"
  - Good: "6x800m repetition com 2min"
  - Good: "5x1km a 3:50/km com 90sec recovery"
  - Good: "10x(100m run + 100m recovery)"
- **Always build repeats as ONE RepeatGroupDTO** (repeat block) — never expand into N×2 individual steps
- **Recovery can be:**
  - Time: "5min" (assumes easy/recovery pace)
  - Time + pace: "5min threshold", "2min easy"
  - Distance: "800m easy", "400m recovery", "100m recovery"
- **Ambiguity**: If unclear, ask before building

### Examples Formatted Properly

**Multi-segment:**
"Treino: 3km easy + 10km threshold + 2km easy — sexta"
→ Parsed as: 3km (easy) + 10km (4:15/km threshold) + 2km (easy)

**With repeats:**
"1km easy, 2x3km threshold com 5min easy, 1km easy — sábado"
→ Parsed as:
  - Warm-up: 1km easy
  - Repeat block (2 iterations): [3km threshold (4:15/km) + 5min easy recovery]
  - Cool-down: 1km easy
→ Auto-generated name: "Easy + 2x3km Threshold + Easy · 8km"

**Short intervals:**
"10x(100m run + 100m recovery) pro sábado"
→ Parsed as: ONE repeat block (10 iterations): [100m interval @ repetition + 100m recovery no.target]
→ Auto-generated name: "10x(100m + 100m rec)"

**VDOT vs manual:**
"1km easy + 6x800m repetition com 2min + 1km easy" ← uses VDOT paces from JSON
"1km a 5:30/km + 6x800m a 3:50/km com 2min recovery + 1km a 5:30/km" ← manual paces
