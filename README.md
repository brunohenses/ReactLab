# Simulador Web de Reações Químicas

**Versão:** 0.1-alpha  
**Stack:** Python 3 + Django, Django REST Framework, SQLite (dev) / PostgreSQL (prod), Chart.js, NumPy/SciPy

## Sobre o Projeto

Aplicação web educativa para simular reações químicas simples (cinética de ordem 0, 1 e 2). Permite criar templates de reação, gerir espécies químicas, executar simulações server-side e visualizar resultados interativos.

## Objetivos do MVP

- Autenticação com roles (admin / professor / aluno)
- CRUD de ReactionTemplate e Species
- Motor de simulação server-side (leis 0ª/1ª/2ª ordem)
- Criar SimulationRun, persistir resultados e plotar com Chart.js
- Export CSV/PDF, histórico de runs e validações básicas

## Estrutura do Projeto

```
simulador_reacoes/
├── simulador/          # Django project (settings, urls, wsgi)
├── accounts/           # Autenticação e gestão de utilizadores
├── simulator/          # App principal: models, views, engine, api
├── templates/          # Templates HTML
├── requirements.txt    # Dependências Python
├── manage.py          # Django management
└── README.md          # Este ficheiro
```

## Setup Local

**Requisitos:** Python 3.10+, pip, virtualenv

```bash
# Clonar repositório
git clone https://github.com/brunohenses/ReactLab

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Configurar base de dados
python manage.py migrate
python manage.py createsuperuser

# Iniciar servidor
python manage.py runserver
```

## Configuração

Criar `.env` baseado em `.env.example`:

```ini
SECRET_KEY=trocar-em-produção
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
```

## API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/templates/` | Listar templates de reação |
| GET | `/api/templates/<id>/` | Detalhes do template |
| POST | `/api/runs/` | Criar simulação |
| GET | `/api/runs/<id>/` | Obter resultados |

*Autenticação requerida para criação de runs*

## Comandos Úteis

```bash
# Demo do motor (standalone)
python run_engine_demo.py

# Executar testes
python manage.py test
```

## Workflow de Desenvolvimento

- **Branch main:** produção
- **Branch develop:** integração
- **Feature branches:** `feature/<descrição>`
- **Commits:** `feat: descrição`, `fix: descrição`
- Pull requests para `develop` com revisão

## Deployment

Sugestão: Render/Heroku com PostgreSQL
Configurar: `Procfile`, `DATABASE_URL`, `SECRET_KEY`

## Licença

MIT (definir antes do deploy público)