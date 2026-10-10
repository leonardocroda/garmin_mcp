#!/usr/bin/env python3
"""
Generate Run Summary Image
Creates a beautiful 1080x1920 story-ready image from Garmin activity data.

Usage:
    Called from OpenCode skill context with activity data.
"""

import json
import re
from pathlib import Path


def format_pace(seconds_per_km):
    """Format seconds per km as MM:SS"""
    m = int(seconds_per_km // 60)
    s = int(seconds_per_km % 60)
    return f"{m}:{s:02d}"


def format_duration(seconds):
    """Format seconds as HH:MM:SS or MM:SS"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def classify_split(split, threshold_pace=260, is_continuous_run=True):
    """Classify a split by type based on intensity and pace.
    
    For continuous runs (tests, races, long runs), all splits are 'race'.
    Only interval workouts with explicit warmup/active/recovery/cooldown get typed.
    """
    intensity = split.get("intensity", "").upper()
    
    # For continuous runs, always return 'race' regardless of intensity field
    if is_continuous_run:
        return "race"
    
    # Only for actual interval workouts, classify by intensity
    if intensity == "WARMUP":
        return "warm"
    elif intensity == "ACTIVE":
        return "int"
    elif intensity == "RECOVERY":
        return "rec"
    elif intensity == "COOLDOWN":
        return "cool"
    elif intensity == "INTERVAL":
        return "race"
    else:
        return "race"


def calculate_chart_dimensions(splits):
    """Calculate X positions and bar heights for the chart."""
    total_time = sum(s["duration_seconds"] for s in splits)
    available_width = 860
    scale = available_width / total_time if total_time > 0 else 1

    x = 70
    for s in splits:
        s["width"] = s["duration_seconds"] * scale
        s["x"] = x
        x += s["width"]

    # Y-axis: pace -> height (faster = taller)
    min_pace = 180  # 3:00/km
    max_pace = 420  # 7:00/km
    y_top = 40
    y_bottom = 320

    for s in splits:
        pace_sec = s.get("pace_seconds", 240)
        normalized = (pace_sec - min_pace) / (max_pace - min_pace)
        s["y"] = y_top + normalized * (y_bottom - y_top)
        s["height"] = y_bottom - s["y"]

    # HR line Y positions
    hr_min = 110
    hr_max = 190
    for s in splits:
        hr = s.get("avg_hr", 150)
        s["hr_y"] = 320 - ((hr - hr_min) / (hr_max - hr_min)) * 280

    return splits


# Colors by split type
COLORS = {
    "warm": ("#60a5fa", "#3b82f6"),   # Blue
    "int": ("#fb923c", "#ea580c"),    # Orange
    "rec": ("#4ade80", "#16a34a"),    # Green
    "cool": ("#94a3b8", "#64748b"),   # Gray
    "race": ("#818cf8", "#4f46e5"),   # Indigo
}

TYPE_LABELS = {
    "warm": "Aquecimento",
    "int": "Tiro",
    "rec": "Recuperação",
    "cool": "Desaquecimento",
    "race": "Corrida",
}


def generate_svg(splits):
    """Generate the combined pace+HR SVG chart."""
    svg_parts = []
    svg_parts.append('<svg width="100%" height="100%" viewBox="0 0 980 400" preserveAspectRatio="xMidYMid meet">')

    # Grid
    svg_parts.append('<line x1="70" y1="30" x2="70" y2="320" stroke="rgba(255,255,255,0.08)" stroke-width="1"/>')
    svg_parts.append('<line x1="70" y1="320" x2="930" y2="320" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>')

    # Y-axis labels (pace)
    for pace, y in [("3:00", 40), ("4:00", 110), ("5:00", 180), ("6:00", 250), ("7:00", 325)]:
        svg_parts.append(f'<text x="60" y="{y}" text-anchor="end" fill="#8b8b9e" font-size="14" font-family="JetBrains Mono">{pace}</text>')

    # Y-axis labels (HR)
    for hr, y in [(190, 40), (170, 110), (150, 180), (130, 250), (110, 325)]:
        svg_parts.append(f'<text x="950" y="{y}" text-anchor="start" fill="#ef4444" font-size="14" font-family="JetBrains Mono">{hr}</text>')

    # Horizontal grid lines
    for y in [40, 110, 180, 250]:
        svg_parts.append(f'<line x1="70" y1="{y}" x2="930" y2="{y}" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>')

    # Bars
    for s in splits:
        c1, c2 = COLORS.get(s["type"], COLORS["race"])
        svg_parts.append(f'<rect x="{s["x"]:.1f}" y="{s["y"]:.1f}" width="{s["width"]:.1f}" height="{s["height"]:.1f}" rx="5" fill="url(#grad{s["km"]})"/>')
        svg_parts.append(f'<text x="{s["x"] + s["width"]/2:.1f}" y="{s["y"] - 10:.1f}" text-anchor="middle" fill="{c1}" font-size="14" font-family="JetBrains Mono" font-weight="700">{s["pace"]}</text>')

    # HR line
    points = " ".join(f'{s["x"] + s["width"]/2:.1f},{s["hr_y"]:.1f}' for s in splits)
    svg_parts.append(f'<polyline fill="none" stroke="#ef4444" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="{points}"/>')

    # HR dots
    for s in splits:
        cx = s["x"] + s["width"] / 2
        svg_parts.append(f'<circle cx="{cx:.1f}" cy="{s["hr_y"]:.1f}" r="6" fill="#ef4444"/>')

    # Gradients
    for s in splits:
        c1, c2 = COLORS.get(s["type"], COLORS["race"])
        svg_parts.append(f'<linearGradient id="grad{s["km"]}" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/></linearGradient>')

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def generate_legend(splits):
    """Generate legend HTML showing only existing split types."""
    existing_types = set(s["type"] for s in splits)
    legend_items = []

    if "warm" in existing_types:
        legend_items.append('<div class="item"><div class="dot d1"></div>Aquecimento</div>')
    if "race" in existing_types:
        legend_items.append('<div class="item"><div class="dot d2"></div>Corrida</div>')
    if "rec" in existing_types:
        legend_items.append('<div class="item"><div class="dot d3"></div>Recuperação</div>')
    if "cool" in existing_types:
        legend_items.append('<div class="item"><div class="dot d4"></div>Desaquecimento</div>')
    # Note: "int" type is only used for actual interval workouts, not continuous runs

    return "".join(legend_items)


def detect_workout_type_from_message(message):
    """Detect workout type from user's message. Returns None if not explicit."""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["teste", "test", "prova"]):
        return "race"
    elif any(word in message_lower for word in ["tiros", "intervalado", "8x800", "4x400", "repeticion"]):
        return "interval"
    elif any(word in message_lower for word in ["longão", "longo", "long run"]):
        return "long"
    elif any(word in message_lower for word in ["fácil", "facil", "easy", "recuperação", "leve"]):
        return "easy"
    
    return None


def classify_all_splits_as_race(splits):
    """For continuous runs, classify all splits as 'race'."""
    for s in splits:
        s["type"] = "race"
    return splits


def get_dynamic_text(workout_type, splits):
    """Get dynamic text content based on workout type."""
    texts = {
        "interval": {
            "title": "Treino de",
            "highlight": f"{len([s for s in splits if s['type'] == 'int'])}×800m",
            "structure": f"Aquecimento + {len([s for s in splits if s['type'] == 'int'])}×800m + Desaquecimento",
            "result_label": "Tempo Total",
            "footer": "Tiros é velocidade",
            "vdot_label": "Consistência",
        },
        "race": {
            "title": "Teste de",
            "highlight": "10K",
            "structure": "Prova de 10K",
            "result_label": "Tempo Final",
            "footer": "Correr é liberdade",
            "vdot_label": "VDOT",
        },
        "long": {
            "title": "Longão",
            "highlight": f"{sum(s['distance_m'] for s in splits)/1000:.1f} km",
            "structure": f"Longão de {sum(s['distance_m'] for s in splits)/1000:.1f} km",
            "result_label": "Tempo Total",
            "footer": "Correr é liberdade",
            "vdot_label": "VDOT",
        },
        "easy": {
            "title": "Corrida",
            "highlight": "Fácil",
            "structure": "Corrida fácil",
            "result_label": "Tempo Total",
            "footer": "Correr é liberdade",
            "vdot_label": "VDOT",
        },
    }
    return texts.get(workout_type, texts["easy"])


def generate_analysis_text(splits, workout_type, activity_data):
    """Generate automatic analysis text based on workout data."""
    if not splits:
        return "Treino realizado com sucesso."
    
    total_distance = sum(s.get("distance_m", 1000) for s in splits) / 1000
    total_time = sum(s.get("duration_seconds", 0) for s in splits)
    avg_pace = total_time / total_distance if total_distance > 0 else 0
    avg_hr = sum(s.get("avg_hr", 150) for s in splits) / len(splits)
    
    # Calculate split statistics
    paces = [s.get("pace_seconds", 240) for s in splits]
    first_half_pace = sum(paces[:len(paces)//2]) / max(len(paces)//2, 1)
    second_half_pace = sum(paces[len(paces)//2:]) / max(len(paces) - len(paces)//2, 1)
    
    analysis_parts = []
    
    if workout_type == "interval":
        # Interval workout analysis
        int_splits = [s for s in splits if s["type"] == "int"]
        if len(int_splits) >= 2:
            first_int_pace = int_splits[0]["pace_seconds"]
            last_int_pace = int_splits[-1]["pace_seconds"]
            pace_drop = last_int_pace - first_int_pace
            
            int_paces = [s["pace_seconds"] for s in int_splits]
            max_pace_var = max(int_paces) - min(int_paces)
            
            analysis_parts.append(f"Treino de {len(int_splits)}×800m realizado em {format_duration(total_time)}.")
            
            if pace_drop > 10:
                analysis_parts.append(f"Houve uma perda de {int(pace_drop)}s/km entre o primeiro e último intervalo.")
            elif max_pace_var <= 8:
                analysis_parts.append(f"Consistência excelente entre os intervalos (variação de apenas {int(max_pace_var)}s).")
            else:
                analysis_parts.append(f"Boa consistência entre os intervalos (variação de {int(max_pace_var)}s).")
            
            # HR recovery analysis
            int_hrs = [s.get("avg_hr", 150) for s in int_splits]
            hr_rise = int_hrs[-1] - int_hrs[0] if len(int_hrs) >= 2 else 0
            if hr_rise > 10:
                analysis_parts.append(f"A FC subiu {int(hr_rise)} bpm entre o primeiro e último tiro.")
    
    elif workout_type == "race":
        # Race/test analysis
        analysis_parts.append(f"Teste de {total_distance:.1f}km realizado em {format_duration(total_time)}.")
        
        if len(splits) >= 4:
            if second_half_pace > first_half_pace + 5:
                drop = int(second_half_pace - first_half_pace)
                analysis_parts.append(f"O ritmo caiu {drop}s/km na segunda metade. Começar 5-10s/km mais lento pode melhorar a distribuição de esforço.")
            elif second_half_pace < first_half_pace - 5:
                gain = int(first_half_pace - second_half_pace)
                analysis_parts.append(f"Excelente negative split! O ritmo melhorou {gain}s/km na segunda metade.")
            else:
                analysis_parts.append(f"Pace muito consistente entre as metades (diferença de apenas {int(abs(second_half_pace - first_half_pace))}s/km).")
        
        if avg_hr > 170:
            analysis_parts.append(f"FC média de {int(avg_hr)} bpm indica esforço intenso.")
    
    elif workout_type == "long":
        # Long run analysis
        analysis_parts.append(f"Longão de {total_distance:.1f}km realizado em {format_duration(total_time)}.")
        
        if avg_pace > 300:
            analysis_parts.append(f"Ritmo de {format_pace(avg_pace)}/km é ideal para desenvolvimento aeróbico.")
        elif avg_pace > 240:
            analysis_parts.append(f"Ritmo de {format_pace(avg_pace)}/km bom para base aeróbica.")
        else:
            analysis_parts.append(f"Ritmo de {format_pace(avg_pace)}/km um pouco rápido para longão.")
        
        if avg_hr > 155:
            analysis_parts.append(f"FC média de {int(avg_hr)} bpm sugere intensidade moderada.")
    
    else:
        # Easy run analysis
        analysis_parts.append(f"Corrida de {total_distance:.1f}km em {format_duration(total_time)}.")
        
        if avg_pace > 330:
            analysis_parts.append(f"Ritmo de {format_pace(avg_pace)}/km perfeito para recuperação ativa.")
        elif avg_pace > 270:
            analysis_parts.append(f"Ritmo de {format_pace(avg_pace)}/km bom para base aeróbica.")
        else:
            analysis_parts.append(f"Ritmo de {format_pace(avg_pace)}/km — considere desacelerar para melhor adaptação aeróbica.")
    
    # Add VDOT context if available
    vdot = activity_data.get("vdot")
    if vdot and workout_type in ["race", "long"]:
        analysis_parts.append(f"VDOT atual: {vdot}")
    
    return " ".join(analysis_parts)


def generate_summary_image(activity_data, output_dir=None):
    """
    Generate summary image from activity data.
    
    Args:
        activity_data: dict with activity data including splits
        
    Returns:
        Path to generated image
    """
    if output_dir is None:
        output_dir = Path.home() / ".opencode" / "tmp"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    activity_id = activity_data.get("activity_id", "unknown")
    html_path = output_dir / f"run_summary_{activity_id}.html"
    png_path = output_dir / f"run_summary_{activity_id}.png"

    # Process splits
    splits = activity_data.get("splits", [])
    
    # Detect if this is a continuous run (not an interval workout)
    # Interval workouts have explicit warmup/active/recovery/cooldown types
    has_explicit_interval_types = any(
        s.get("intensity", "").upper() in ["WARMUP", "RECOVERY", "COOLDOWN"]
        for s in splits
    )
    is_continuous_run = not has_explicit_interval_types
    
    for i, s in enumerate(splits):
        s["km"] = i + 1
        s["type"] = classify_split(s, is_continuous_run=is_continuous_run)
        s["pace"] = format_pace(s.get("pace_seconds", 240))

    # Calculate chart dimensions
    splits = calculate_chart_dimensions(splits)

    # Detect workout type
    workout_type = detect_workout_type(splits, activity_data)

    # Get dynamic text
    texts = get_dynamic_text(workout_type, splits)

    # Generate analysis text
    analysis_text = generate_analysis_text(splits, workout_type, activity_data)

    # Generate SVG chart
    chart_svg = generate_svg(splits)

    # Generate legend
    legend_items = generate_legend(splits)

    # Calculate totals
    total_distance = sum(s.get("distance_m", 1000) for s in splits) / 1000
    total_time = sum(s.get("duration_seconds", 0) for s in splits)
    avg_pace = total_time / total_distance if total_distance > 0 else 0
    avg_hr = sum(s.get("avg_hr", 150) for s in splits) / len(splits) if splits else 150
    max_hr = max((s.get("avg_hr", 150) for s in splits), default=150)
    elevation = sum(s.get("elevation_gain", 0) for s in splits)

    # Read template with explicit UTF-8 encoding
    template_path = Path(__file__).parent / "templates" / "story_template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Replace placeholders
    html = html.replace("{{ date }}", activity_data.get("date", ""))
    html = html.replace("{{ location }}", activity_data.get("location", ""))
    html = html.replace("{{ title }}", texts["title"])
    html = html.replace("{{ highlight }}", texts["highlight"])
    html = html.replace("{{ workout_structure }}", texts["structure"])
    html = html.replace("{{ result_label }}", texts["result_label"])
    html = html.replace("{{ duration }}", format_duration(total_time))
    html = html.replace("{{ distance }}", f"{total_distance:.2f} km")
    html = html.replace("{{ avg_pace }}", format_pace(avg_pace))
    html = html.replace("{{ avg_hr }}", str(int(avg_hr)))
    html = html.replace("{{ max_hr }}", str(int(max_hr)))
    html = html.replace("{{ elevation }}", f"{int(elevation)}m")
    html = html.replace("{{ chart_svg }}", chart_svg)
    html = html.replace("{{ legend_items }}", legend_items)
    html = html.replace("{{ footer_text }}", texts["footer"])
    html = html.replace("{{ analysis_text }}", analysis_text)

    # Save HTML with explicit UTF-8 encoding
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Take screenshot
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1080, "height": 1920},
            device_scale_factor=2,
        )
        page = context.new_page()
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(png_path), full_page=False)
        browser.close()

    return png_path
