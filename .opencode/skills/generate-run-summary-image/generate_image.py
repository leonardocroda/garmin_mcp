#!/usr/bin/env python3
"""
Generate Run Summary Image
Creates a beautiful 1080x1920 story-ready image from Garmin activity data.

Usage:
    python generate_image.py --data-file run_data.json [--output-dir DIR]

    Or import generate_summary_image(activity_data, ...) directly from the
    OpenCode skill context.
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


# De-para 1:1 do intensityType do Garmin (validado contra atividades reais).
# Workout estruturado: WARMUP, ACTIVE (passo "corrida"), RECOVERY, REST, WALK,
# COOLDOWN, OTHER. Corrida livre (auto-lap): INTERVAL em todas as voltas.
# Sem intensity (vazio): corrida livre -> "run" (Corrida).
INTENSITY_MAP = {
    "WARMUP": "warm",
    "ACTIVE": "run",
    "RUN": "run",        # defensivo: alguns endpoints usam RUN p/ passo corrida
    "INTERVAL": "run",   # auto-laps de corrida livre = corrida contínua
    "RECOVERY": "rec",
    "REST": "rest",
    "COOLDOWN": "cool",
    "WALK": "walk",
    "OTHER": "other",
}


def classify_split(split):
    """Classifica o split pelo intensityType do Garmin — de-para puro, nada inventado."""
    intensity = (split.get("intensity") or split.get("intensity_type") or "").upper()
    return INTENSITY_MAP.get(intensity, "run")


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
        # Clamp à escala do gráfico: passos mais lentos que 7:00/km
        # (recuperação, caminhada, descanso) ficam no fundo com altura mínima,
        # em vez de gerar barras negativas (invisíveis).
        pace_sec = min(max(pace_sec, min_pace), max_pace)
        normalized = (pace_sec - min_pace) / (max_pace - min_pace)
        s["y"] = y_top + normalized * (y_bottom - y_top)
        s["height"] = max(y_bottom - s["y"], 2.5)

    # HR line Y positions
    hr_min = 110
    hr_max = 190
    for s in splits:
        hr = s.get("avg_hr", 150)
        s["hr_y"] = 320 - ((hr - hr_min) / (hr_max - hr_min)) * 280

    return splits


# Cores por tipo de passo do Garmin (chaves do de-para em INTENSITY_MAP).
# Princípio: intensidade = energia da cor — o passo "Corrida" (bloco de
# trabalho) é o herói no indigo (acento do template, contraste máximo com a
# linha vermelha de FC); passivos (recuperação/descanso) em tons neutros de
# slate; bookends suaves: aquecimento azul céu, desaquecimento verde (calma /
# fim de sessão). Tipos raros ficam com o que sobra de bonito: caminhada
# violeta.
COLORS = {
    "warm": ("#38bdf8", "#0284c7"),   # Aquecimento — azul céu
    "run": ("#818cf8", "#4f46e5"),    # Corrida — indigo (herói)
    "rec": ("#cbd5e1", "#94a3b8"),    # Recuperação — slate claro (ainda em movimento)
    "rest": ("#64748b", "#475569"),   # Descanso — slate escuro (parado)
    "cool": ("#4ade80", "#16a34a"),   # Desaquecimento — verde
    "walk": ("#a78bfa", "#7c3aed"),   # Caminhada — violeta
    "other": ("#a8a29e", "#57534e"),  # Outros — stone neutro
}

# Rótulos idênticos aos do app do Garmin (criação de workout)
TYPE_LABELS = {
    "warm": "Aquecimento",
    "run": "Corrida",
    "rec": "Recuperação",
    "rest": "Descanso",
    "cool": "Desaquecimento",
    "walk": "Caminhada",
    "other": "Outros",
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
        c1, c2 = COLORS.get(s["type"], COLORS["run"])
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
        c1, c2 = COLORS.get(s["type"], COLORS["run"])
        svg_parts.append(f'<linearGradient id="grad{s["km"]}" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="{c1}"/><stop offset="100%" stop-color="{c2}"/></linearGradient>')

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


LEGEND_ORDER = ["warm", "run", "walk", "rec", "rest", "cool", "other"]


def generate_legend(splits):
    """Legenda com os tipos de passo do Garmin presentes nos dados (FC fica no template).

    As cores dos pontos vêm direto de COLORS — fonte única de verdade, sem
    risco de drift com classes CSS do template.
    """
    existing_types = set(s["type"] for s in splits)
    items = []
    for t in LEGEND_ORDER:
        if t not in existing_types:
            continue
        c1, c2 = COLORS[t]
        items.append(
            f'<div class="item"><div class="dot" style="background: linear-gradient(135deg, {c1}, {c2});"></div>{TYPE_LABELS[t]}</div>'
        )
    return "".join(items)


# NOTE: o workout_type afeta APENAS os textos (título, badge de estrutura,
# footer e análise de fallback). O gráfico — cores, barras, legenda — é 100%
# dirigido pelo intensityType do Garmin via de-para (INTENSITY_MAP). Nada de
# tipos inventados como "Tiro": os rótulos vêm do próprio app do Garmin.


def derive_structure(splits):
    """Deriva a estrutura do treino somando os passos reais do Garmin por tipo.

    Ex: "Aquecimento 2,0km + Corrida 7,1km + Desaquecimento 2,0km".
    Para estruturas mais ricas (ex: "8×800m"), o agente pode sobrescrever
    via activity_data["structure"].
    """
    if not splits:
        return "Corrida"
    totals = {}
    order = []
    for s in splits:
        t = s["type"]
        if t not in totals:
            totals[t] = {"distance_m": 0.0, "duration_seconds": 0.0}
            order.append(t)
        totals[t]["distance_m"] += s.get("distance_m", 0)
        totals[t]["duration_seconds"] += s.get("duration_seconds", 0)
    parts = []
    for t in order:
        label = TYPE_LABELS[t]
        dist = totals[t]["distance_m"]
        dur = totals[t]["duration_seconds"]
        if dist >= 100:
            parts.append(f"{label} {dist / 1000:.1f}km".replace(".", ","))
        elif dur >= 60:
            parts.append(f"{label} {int(round(dur / 60))}min")
        else:
            parts.append(label)
    return " + ".join(parts)


def get_dynamic_text(workout_type, splits, activity_data=None):
    """Texto dinâmico por tipo de treino (título/badge/footer — nunca o gráfico).

    O agente pode sobrescrever qualquer texto via activity_data: title,
    highlight, structure, result_label, footer, vdot_label.
    """
    activity_data = activity_data or {}

    total_km = sum(s.get("distance_m", 1000) for s in splits) / 1000 if splits else 0
    structure = derive_structure(splits)

    # Race label from actual distance (e.g. "10K", "21K"); agent can override
    if total_km >= 5:
        race_label = f"{total_km:.0f}K"
    elif total_km > 0:
        race_label = f"{total_km:.1f}km"
    else:
        race_label = "Prova"

    texts = {
        "tempo": {
            "title": "Treino de",
            "highlight": "Tempo",
            "structure": structure,
            "result_label": "Tempo Total",
            "footer": "Tempo é controle",
            "vdot_label": "VDOT",
        },
        "interval": {
            "title": "Treino de",
            "highlight": "Intervalado",
            "structure": structure,
            "result_label": "Tempo Total",
            "footer": "Tiros é velocidade",
            "vdot_label": "Consistência",
        },
        "race": {
            "title": "Teste de",
            "highlight": race_label,
            "structure": f"Prova de {race_label}",
            "result_label": "Tempo Final",
            "footer": "Correr é liberdade",
            "vdot_label": "VDOT",
        },
        "long": {
            "title": "Longão",
            "highlight": f"{total_km:.1f} km".replace(".", ","),
            "structure": structure,
            "result_label": "Tempo Total",
            "footer": "Correr é liberdade",
            "vdot_label": "VDOT",
        },
        "easy": {
            "title": "Corrida",
            "highlight": "Fácil",
            "structure": structure,
            "result_label": "Tempo Total",
            "footer": "Correr é liberdade",
            "vdot_label": "VDOT",
        },
    }
    # Tipo omitido -> texto neutro, sem inventar rótulo
    default = {
        "title": "Corrida",
        "highlight": f"{total_km:.1f} km".replace(".", ","),
        "structure": structure,
        "result_label": "Tempo Total",
        "footer": "Correr é liberdade",
        "vdot_label": "VDOT",
    }
    texts = dict(texts.get(workout_type, default))

    # Explicit overrides from the caller (agent) always win
    for key in ("title", "highlight", "structure", "result_label", "footer", "vdot_label"):
        if activity_data.get(key):
            texts[key] = str(activity_data[key])

    return texts


def _count_run_groups(splits):
    """Conta grupos consecutivos de passos 'corrida' (tiros em treinos intervalados)."""
    groups = []
    prev_was_run = False
    for s in splits:
        if s["type"] == "run":
            if not prev_was_run:
                groups.append({"distance_m": 0.0, "count": 0})
            groups[-1]["distance_m"] += s.get("distance_m", 0)
            groups[-1]["count"] += 1
            prev_was_run = True
        else:
            prev_was_run = False
    return groups


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
    run_groups = _count_run_groups(splits)
    
    if workout_type == "interval" and len(run_groups) >= 2:
        # Interval workout: grupos de 'corrida' separados por recuperação = tiros
        n_reps = len(run_groups)
        rep_distance = int(round(sum(g["distance_m"] for g in run_groups) / n_reps))
        
        # Paces/HR por grupo: primeira e última volta de cada grupo
        group_idx = -1
        prev_was_run = False
        group_laps = []
        for s in splits:
            if s["type"] == "run":
                if not prev_was_run:
                    group_laps.append([])
                    group_idx += 1
                group_laps[group_idx].append(s)
                prev_was_run = True
            else:
                prev_was_run = False
        
        first_laps = [g[0] for g in group_laps]
        last_laps = [g[-1] for g in group_laps]
        first_int_pace = first_laps[0]["pace_seconds"]
        last_int_pace = last_laps[-1]["pace_seconds"]
        pace_drop = last_int_pace - first_int_pace
        all_rep_laps = [s for g in group_laps for s in g]
        rep_pace_values = [s["pace_seconds"] for s in all_rep_laps]
        max_pace_var = max(rep_pace_values) - min(rep_pace_values)
        
        analysis_parts.append(f"Treino de {n_reps}×{rep_distance}m realizado em {format_duration(total_time)}.")
        
        if pace_drop > 10:
            analysis_parts.append(f"Houve uma perda de {int(pace_drop)}s/km entre o primeiro e último intervalo.")
        elif max_pace_var <= 8:
            analysis_parts.append(f"Consistência excelente entre os intervalos (variação de apenas {int(max_pace_var)}s).")
        else:
            analysis_parts.append(f"Boa consistência entre os intervalos (variação de {int(max_pace_var)}s).")
        
        # HR rise across reps
        hr_rise = last_laps[-1].get("avg_hr", 150) - first_laps[0].get("avg_hr", 150)
        if hr_rise > 10:
            analysis_parts.append(f"A FC subiu {int(hr_rise)} bpm entre o primeiro e último tiro.")
    
    elif workout_type in ("tempo", "interval"):
        # Bloco sustentado (tempo run ou intervalado sem recuperações marcadas)
        run_laps = [s for s in splits if s["type"] == "run"]
        if run_laps:
            run_dist = sum(s.get("distance_m", 0) for s in run_laps) / 1000
            run_time = sum(s.get("duration_seconds", 0) for s in run_laps)
            run_pace = run_time / run_dist if run_dist > 0 else 0
            analysis_parts.append(f"Bloco sustentado de {run_dist:.1f}km a {format_pace(run_pace)}/km.")
            
            if len(run_laps) >= 4:
                spread = max(s["pace_seconds"] for s in run_laps) - min(s["pace_seconds"] for s in run_laps)
                if spread <= 8:
                    analysis_parts.append(f"Ritmo muito consistente (variação de apenas {int(spread)}s/km entre os quilômetros).")
                else:
                    analysis_parts.append(f"Variação de {int(spread)}s/km entre os quilômetros do bloco.")
            
            hr_rise = run_laps[-1].get("avg_hr", 150) - run_laps[0].get("avg_hr", 150)
            if hr_rise > 12:
                analysis_parts.append(f"A FC subiu {int(hr_rise)} bpm ao longo do bloco no mesmo ritmo — drift cardíaco.")
        
        if not analysis_parts:
            analysis_parts.append(f"Treino de {total_distance:.1f}km realizado em {format_duration(total_time)}.")
    
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
    
    elif workout_type == "easy":
        # Easy run analysis
        analysis_parts.append(f"Corrida de {total_distance:.1f}km em {format_duration(total_time)}.")
        
        if avg_pace > 330:
            analysis_parts.append(f"Ritmo de {format_pace(avg_pace)}/km perfeito para recuperação ativa.")
        elif avg_pace > 270:
            analysis_parts.append(f"Ritmo de {format_pace(avg_pace)}/km bom para base aeróbica.")
        else:
            analysis_parts.append(f"Ritmo de {format_pace(avg_pace)}/km — considere desacelerar para melhor adaptação aeróbica.")
    
    else:
        # Tipo não especificado — texto neutro, sem inventar rótulo
        analysis_parts.append(f"Corrida de {total_distance:.1f}km em {format_duration(total_time)} a {format_pace(avg_pace)}/km.")
    
    # Add VDOT context if available
    vdot = activity_data.get("vdot")
    if vdot and workout_type in ["race", "long", "tempo"]:
        analysis_parts.append(f"VDOT atual: {vdot}")
    
    return " ".join(analysis_parts)


def generate_summary_image(activity_data, output_dir=None, workout_type=None, analysis_text=None):
    """
    Generate summary image from activity data.
    
    Args:
        activity_data: dict with activity data including splits. Optional keys:
            - workout_type: "race" | "interval" | "long" | "easy" (fallback if
              the workout_type arg is not given)
            - analysis_text: analysis verdict to show in the "Análise do Treino"
              card (fallback if the analysis_text arg is not given). Typically
              the distilled verdict handed off from analyze-garmin-run.
            - date, location, vdot, activity_id
            - text overrides: title, highlight, structure, result_label, footer,
              vdot_label
        workout_type: explicit workout type — decided by the agent (asking the
            user when not explicit, per SKILL.md). Never inferred from pace or
            intensity data here.
        analysis_text: explicit analysis verdict text. Takes precedence over
            activity_data["analysis_text"] and over the naive built-in
            generate_analysis_text fallback.
        
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

    # Process splits — classificação 100% pelo intensityType do Garmin (de-para)
    splits = activity_data.get("splits", [])
    
    for i, s in enumerate(splits):
        s["km"] = i + 1
        s["type"] = classify_split(s)
        s["pace"] = format_pace(s.get("pace_seconds", 240))

    # Calculate chart dimensions
    splits = calculate_chart_dimensions(splits)

    # Workout type: afeta APENAS os textos (título/badge/footer/análise).
    # None -> neutro. O gráfico nunca depende disso.
    workout_type = workout_type or activity_data.get("workout_type")

    # Analysis text: explicit handoff (e.g. verdict from analyze-garmin-run)
    # wins over the naive built-in fallback.
    if analysis_text is None:
        analysis_text = activity_data.get("analysis_text")
    if not analysis_text:
        analysis_text = generate_analysis_text(splits, workout_type, activity_data)

    # Get dynamic text (activity_data may carry explicit overrides)
    texts = get_dynamic_text(workout_type, splits, activity_data)

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
    vdot = activity_data.get("vdot")
    vdot_line = f" · VDOT <b>{vdot}</b>" if vdot else ""
    html = html.replace("{{ vdot_line }}", vdot_line)
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
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(1500)
        page.screenshot(path=str(png_path), full_page=False)
        browser.close()

    return png_path


def main():
    """CLI entry point: render the story image from a JSON data file.

    The JSON file is produced by the agent as part of the skill workflow: it
    contains the activity data fetched from Garmin (splits, date, location,
    vdot) plus, optionally, the confirmed `workout_type`, an `analysis_text`
    handed off from analyze-garmin-run, and text overrides (title, highlight,
    structure, result_label, footer, vdot_label).

    Usage:
        python generate_image.py --data-file run_data.json [--output-dir DIR]
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a run summary story image (1080x1920) from a JSON data file."
    )
    parser.add_argument(
        "--data-file",
        required=True,
        help="JSON file with activity data: activity_id, date, location, splits[], "
        "vdot?, workout_type?, analysis_text?, text overrides?",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: ~/.opencode/tmp)",
    )
    args = parser.parse_args()

    # utf-8-sig: tolera data files gravados com BOM (ex.: PowerShell
    # Set-Content -Encoding UTF8 no Windows adiciona BOM e o json.load
    # com "utf-8" puro falharia em "Expecting value: line 1 column 1").
    with open(args.data_file, "r", encoding="utf-8-sig") as f:
        activity_data = json.load(f)

    png_path = generate_summary_image(
        activity_data,
        output_dir=Path(args.output_dir) if args.output_dir else None,
    )
    print(png_path)


if __name__ == "__main__":
    main()
