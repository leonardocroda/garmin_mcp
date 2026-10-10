# Generate Run Summary Image

Gera uma imagem elegante em formato story (1080×1920) a partir de dados de atividades do Garmin.

## Instalação

```bash
pip install jinja2 playwright
playwright install chromium
```

## Uso via OpenCode

Basta pedir:
- "gera uma imagem do meu treino de hoje"
- "faz um story do meu 10km de ontem"
- "cria um post da minha corrida de sábado"

## Uso standalone

```bash
python generate_image.py --activity-id 24588181266
python generate_image.py --date 2026-10-03
python generate_image.py --last
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
├── SKILL.md              # Definição da skill
├── README.md             # Este arquivo
├── generate_image.py     # Script principal
└── templates/
    └── story_template.html  # Template HTML
```
