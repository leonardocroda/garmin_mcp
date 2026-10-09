# Skill: calibrate-garmin-zones

# Calibração de Zonas VDOT para Garmin MCP

Entrevista interativa que calcula zonas de ritmo personalizadas baseadas no resultado do último teste do corredor, usando as equações clássicas de Jack Daniels' Running Formula. Salva as zonas em `vdot_zones.json` para uso pelas outras skills.

## Quando usar

- **Primeira execução** de qualquer skill do Garmin (analyze-garmin-run ou create-garmin-training) — se não existir `vdot_zones.json`, rodar esta skill primeiro
- **Atualização solicitada** — quando o usuário diz "atualiza meus ritmos", "fiz um novo teste", "recalcula minhas zonas"
- **Verificação** — para ver as zonas atuais sem alterar

## Como funciona

1. **Pergunta** a distância do último teste (1500m, 3K, 5K, 10K, meia, maratona, ou outra)
2. **Pergunta** o tempo total (formato HH:MM:SS)
3. **Calcula** o VDOT usando as equações clássicas de Jack Daniels:
   - VDOT = VO2 / %VO2max
   - Onde VO2 = -4.60 + 0.182258 × vel + 0.000104 × vel²
   - E %VO2max = 0.8 + 0.1894393 × e^(-0.012778 × t) + 0.2989558 × e^(-0.1932605 × t)
4. **Gera** as 5 zonas de ritmo
5. **Salva** em `vdot_zones.json` na mesma pasta

## Zonas geradas

| Zona | Cálculo | Uso |
|------|---------|-----|
| **Easy** | 59–74% do VDOT | Recuperação, base aeróbica, aquecimento/desaquecimento |
| **Marathon** | Derivado do ritmo equivalente de maratona | Ritmo de maratona, longões |
| **Threshold** | 83–88% do VDOT | Limiar de lactato, tempo runs |
| **Interval** | 95–100% do VDOT | VO2max, esforços de 2-4 min |
| **Repetition** | ~105% do VDOT | Repetições curtas, 800m-1km |

## Execução

```bash
# Modo interativo (entrevista)
python .opencode/skills/calibrate-garmin-zones/calibrate_vdot.py

# Verificar configuração existente
python .opencode/skills/calibrate-garmin-zones/calibrate_vdot.py --check

# Forçar nova entrevita
python .opencode/skills/calibrate-garmin-zones/calibrate_vdot.py --force
```

## Integração com outras skills

As skills `analyze-garmin-run` e `create-garmin-training` leem as zonas do arquivo `vdot_zones.json`. Se o arquivo não existir, elas instruem o usuário a rodar esta skill primeiro.

## Exemplo de saída (vdot_zones.json)

```json
{
  "vdot": 50.1,
  "source": "10K em 41:14",
  "test_date": "2026-10-09",
  "distancia_metros": 10000,
  "tempo_segundos": 2474,
  "zones": {
    "easy": {
      "pace_range": "4:53-5:51/km",
      "ms_min": 2.817,
      "ms_max": 3.373,
      "description": "Recuperação, base aeróbica, aquecimento/desaquecimento"
    },
    "marathon": {
      "pace": "4:31/km",
      "ms": 3.691,
      "description": "Ritmo de maratona, longões"
    },
    "threshold": {
      "pace_range": "4:15-4:27/km",
      "ms_min": 3.546,
      "ms_max": 3.716,
      "description": "Limiar de lactato, tempo runs"
    },
    "interval": {
      "pace_range": "3:50-3:59/km",
      "ms_min": 4.184,
      "ms_max": 4.359,
      "description": "VO2max, esforços de 2-4 min"
    },
    "repetition": {
      "pace": "3:41/km",
      "ms": 4.587,
      "description": "Repetições curtas, 800m-1km"
    }
  },
  "equivalencias": {
    "5K": "19:53/km",
    "10K": "41:14/km",
    "Meia Maratona": "1:31:19/km",
    "Maratona": "3:10:14/km"
  }
}
```

## Triggers (exemplos)

- "calibra minhas zonas de ritmo"
- "atualiza meus ritmos"
- "fiz um novo teste, recalcula"
- "quero atualizar minhas zonas VDOT"
- "mostra minhas zonas atuais"
