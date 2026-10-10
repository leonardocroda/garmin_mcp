# Generate Run Summary Image

Gera uma imagem elegante em formato story (1080×1920) a partir de dados de atividades do Garmin.

## Instalação

```bash
pip install playwright
playwright install chromium
```

## Uso via OpenCode

Basta pedir:
- "gera uma imagem do meu treino de hoje"
- "faz um story do meu 10km de ontem"
- "cria um post da minha corrida de sábado"

O agente busca os dados no Garmin MCP, monta o JSON de dados e roda o script. O gráfico (cores e legenda) é 100% derivado do `intensityType` de cada volta — os mesmos tipos de passo que você usa ao criar um workout no app (Aquecimento, Corrida, Recuperação, Descanso, Caminhada, Desaquecimento, Outros). O `workout_type` no JSON é opcional e afeta apenas os textos (título/badge/footer).

## Encadeamento com analyze-garmin-run

Se o usuário pedir análise + imagem (ou a imagem logo após uma análise), as skills se encadeiam:
- A skill de análise reutiliza os dados já buscados (não re-chama o Garmin) e destila o verdict em 2–3 frases.
- O verdict entra no card "Análise do Treino" via `analysis_text` no JSON, substituindo a análise ingênua gerada automaticamente.
- Sem análise prévia, o card usa o fallback embutido.

## Uso standalone

O script não fala com o Garmin diretamente — ele consome um JSON de dados (produzido pelo agente no fluxo da skill):

```bash
python generate_image.py --data-file run_data.json [--output-dir DIR]
```

Formato esperado (veja o SKILL.md para o schema completo):

```json
{
  "activity_id": "24588181266",
  "date": "Sáb, 10 Out",
  "location": "São Paulo",
  "workout_type": "race",
  "analysis_text": "Excelente execução: 92% do tempo na zona alvo...",
  "vdot": 51,
  "splits": [
    {"distance_m": 1000, "duration_seconds": 258, "pace_seconds": 258,
     "avg_hr": 152, "elevation_gain": 12, "intensity": "ACTIVE"}
  ]
}
```

## Personalização

Edite `templates/story_template.html` para alterar:
- Cores e gradientes
- Layout e espaçamento
- Fontes e tamanhos
- Elementos visuais

## Estrutura

```
generate-run-summary-image/
├── SKILL.md              # Definição da skill (workflow + chaining)
├── README.md             # Este arquivo
├── generate_image.py     # Script principal (CLI via --data-file)
└── templates/
    └── story_template.html  # Template HTML
```
