# Deployment Impact Analyzer

Ferramenta para análise de impacto de deployments em APIs usando Elasticsearch e Grafana.

## Objetivo

Medir o impacto de mudanças em serviços através de:
- Taxa de erro
- Latência da API
- Quantidade de requisições
- Disponibilidade do serviço

## Stack

- Elasticsearch 8.11.0
- Grafana
- Docker Compose
- Python

## Como Usar

### Iniciar

docker-compose up -d

### Acessar Grafana

http://localhost:3000
Usuário: admin
Senha: admin

### Parar

docker-compose down

## Arquitetura

Python Scripts → Elasticsearch → Grafana → Dashboards

## Próximos Passos

1. Gerar dados fictícios
2. Criar dashboards
3. Análise antes/depois

## Estrutura

deployment-impact-analyzer/
├── docker-compose.yml
├── README.md
├── data/
├── dashboards/
└── docs/

## Status

Infraestrutura base ✅
Dados 🔄
Dashboards 🔄