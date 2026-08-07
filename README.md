# Deployment Impact Analyzer

Ferramenta que mede o impacto de mudanças em APIs, comparando métricas de erro antes e depois de um deploy.

---

## O problema

Quando um deploy vai para produção e algo começa a falhar, a pergunta é sempre a mesma: **foi a mudança que causou isso?**

Responder na mão significa abrir o Kibana, montar um gráfico para o período anterior, outro para o posterior, e comparar no olho — repetindo para cada tipo de erro. É demorado, e o resultado depende de quem está olhando.

Este projeto automatiza essa comparação.

---

## Como funciona

Você informa a API e o horário do deploy. A ferramenta consulta o Elasticsearch em duas janelas — antes e depois — e compara:

- Volume de requisições
- Taxa de sucesso
- Erros de negócio (4xx) versus erros técnicos (5xx)
- Mensagens de erro que apareceram pela primeira vez ou aumentaram

---

## Stack

| Ferramenta | Papel |
|---|---|
| Python | Consulta, normalização e comparação |
| Elasticsearch 8.11 | Armazenamento e agregação dos logs |
| Grafana | Visualização |
| Docker Compose | Sobe o ambiente inteiro |

---

## Rodando localmente

**1. Suba o ambiente**

```bash
docker compose up -d
```

Elasticsearch responde em `http://localhost:9200` e o Grafana em `http://localhost:3000` (usuário e senha: `admin`).

**2. Instale as dependências**

```bash
python -m pip install -r requirements.txt
```

**3. Configure o `.env`**

```bash
ELASTIC_URL_SEARCH=http://localhost:9200
```

**4. Gere os dados fictícios**

```bash
python gerar_dados_ficticios.py
```

O script imprime o horário do deploy simulado ao final. Guarde esse horário — é ele que você vai informar na análise.

**5. Rode a análise**

```bash
python buscar_metricas.py
```

---

## Os dados

Os dados são fictícios, gerados por script. O gerador simula três APIs ao longo de alguns dias, com um "deploy problemático" no meio do período que degrada uma delas.

Cada requisição é gravada assim:

```json
{
  "@timestamp": "2026-08-06T16:16:12",
  "labels": {
    "http_request_url": "https://api.exemplo.com.br/v1/pagamentos",
    "http_response_status": "500",
    "http_request_body_full": "{\"clienteId\": 5686, \"valor\": 1073.54}",
    "http_response_body_full": "{\"serviceName\": \"api-pagamentos\", ...}"
  }
}
```

---

## Decisões técnicas

### Os campos seguem o padrão de um Elasticsearch corporativo

Os nomes de campo (`@timestamp`, `labels.http_request_url`, `labels.http_response_status`, `labels.http_request_body_full`, `labels.http_response_body_full`) não foram escolhidos por conveniência — reproduzem o formato de índices de log corporativos reais.

O motivo é prático: o mesmo código de análise roda sobre dados fictícios e sobre dados de produção, sem adaptação de nomes.

### Cada API devolve o erro num formato diferente

Este é o ponto central do projeto. As três APIs simuladas usam estruturas de resposta distintas:

```json
// Formato descritivo
{ "description": "...", "serviceName": "...", "errorCode": "...", "errorMessage": "..." }

// Formato Spring Boot
{ "status": 500, "error": "Internal Server Error", "message": "...", "internalCode": "..." }

// Formato aninhado
{ "serviceName": "...", "errorDetail": { "code": "...", "message": "..." } }
```

Em um ambiente real, APIs construídas por times diferentes, em épocas diferentes, raramente convergem para um contrato de erro único. Simular essa diversidade força a normalização a ser genérica — a busca pelas tags de erro precisa percorrer a estrutura em profundidade, em vez de assumir um caminho fixo.

### O corpo do erro carrega ruído de propósito

Cada resposta de erro inclui campos que mudam a cada requisição: `timestamp`, `traceId`, `requestId`.

Isso importa porque o objetivo da análise é **agrupar erros iguais e contar ocorrências**. Duas respostas idênticas em conteúdo, mas com identificadores diferentes, precisam ser reconhecidas como o mesmo padrão — e não como dois erros distintos. Sem esse ruído nos dados de teste, a normalização passaria em um cenário mais fácil do que o real.

### A contagem acontece no Elasticsearch, não em Python

As consultas usam `size: 0` com agregação por termos. O Elasticsearch devolve apenas o resumo — quantas requisições em cada status — em vez dos documentos.

Trazer milhares de registros para contar em Python funcionaria com dados de teste e quebraria em produção. Aqui a diferença é entre transferir um punhado de números e transferir megabytes de log.

### O status HTTP é armazenado como texto

`"500"` e não `500`. É o formato mais comum em índices de log corporativos, onde o campo costuma chegar como string do agente de coleta. A conversão para número acontece no Python, no momento de classificar entre 4xx e 5xx.

### As janelas de tempo usam `gte` e `lt`

O intervalo inclui o início e exclui o fim. Quando as janelas "antes" e "depois" se encostam no horário do deploy, nenhuma requisição é contada duas vezes.

### O índice é recriado a cada execução do gerador

O script apaga o índice antes de gravar. Isso mantém o cenário reproduzível: quem clonar o repositório e rodar obtém uma base limpa, sem resíduo de execuções anteriores.

### Ajustes para ambiente com pouca memória

O contêiner do Elasticsearch roda com limite de memória baixo, para caber em uma máquina modesta. Duas consequências foram tratadas:

- `request_timeout=60` na conexão — a resposta demora mais do que o padrão de 10 segundos permite
- `chunk_size=500` na gravação em lote — enviar 13 mil documentos de uma vez causava timeout

---

## Roadmap

- [x] Ambiente com Elasticsearch e Grafana em Docker
- [x] Conexão com o Elasticsearch
- [x] Gerador de dados fictícios com cenário de deploy
- [ ] Consulta de métricas por período
- [ ] Comparação antes x depois
- [ ] Normalização e agrupamento de padrões de erro
- [ ] Dashboards no Grafana

---

## Dashboards

_Em construção — última etapa do roadmap._

---

## Contexto

Este projeto nasceu de uma necessidade real do meu trabalho: medir se uma mudança em produção causou impacto nos serviços. A versão que roda na empresa consome dados reais e se integra ao ITSM; esta versão pública reproduz a mesma lógica sobre dados fictícios, com a stack idêntica.
