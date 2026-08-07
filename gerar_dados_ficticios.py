"""
ARQUIVO: gerar_dados_ficticios.py

Gera requisições fictícias de API e grava no Elasticsearch.

Os campos seguem o mesmo padrão do Elasticsearch da empresa
(@timestamp e labels.*), para que o código de análise sirva nos dois projetos.

Cada API devolve o erro num formato diferente, de propósito: é assim que
acontece na vida real e é o que torna a análise desafiadora.
"""

import json
import random
from datetime import datetime, timedelta

from elasticsearch import helpers
from conexao_elastic import conectar_elasticsearch


# ---------------------------------------------------------------
# CONFIGURAÇÕES — mude aqui se quiser outro cenário
# ---------------------------------------------------------------

NOME_INDICE = "logs-api"

DIAS_DE_DADOS = 3
REQUISICOES_POR_HORA = 60

# Há quantas horas atrás aconteceu o "deploy problemático"
HORAS_ATRAS_DO_DEPLOY = 30

# Qual API vai piorar depois do deploy
API_AFETADA = "api-pagamentos"


APIS = [
    {
        "nome": "api-clientes",
        "url": "https://api.exemplo.com.br/v1/clientes",
        "metodo": "GET",
        "formato_erro": "descritivo",
    },
    {
        "nome": "api-pedidos",
        "url": "https://api.exemplo.com.br/v1/pedidos",
        "metodo": "POST",
        "formato_erro": "spring",
    },
    {
        "nome": "api-pagamentos",
        "url": "https://api.exemplo.com.br/v1/pagamentos",
        "metodo": "POST",
        "formato_erro": "aninhado",
    },
]


# Erros de negócio (4xx) — cada API tem os seus
ERROS_NEGOCIO = {
    "api-clientes": [
        (404, "CLIENTE_NAO_ENCONTRADO", "Cliente não encontrado na base"),
        (422, "CPF_INVALIDO", "CPF informado é inválido"),
    ],
    "api-pedidos": [
        (422, "PEDIDO_SEM_ITENS", "Pedido não possui itens"),
        (409, "PEDIDO_DUPLICADO", "Já existe pedido igual em aberto"),
    ],
    "api-pagamentos": [
        (422, "SALDO_INSUFICIENTE", "Saldo insuficiente para a operação"),
        (403, "CLIENTE_COM_PENDENCIA", "Cliente com pendência financeira"),
    ],
}

# Erros técnicos (5xx) — valem para qualquer API
ERROS_TECNICOS = [
    (500, "ERRO_INTERNO", "Erro interno no processamento"),
    (503, "SERVICO_INDISPONIVEL", "Serviço temporariamente indisponível"),
    (504, "TEMPO_ESGOTADO", "Tempo de resposta excedido"),
]

# Texto que acompanha cada status HTTP
TEXTO_DO_STATUS = {
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Unprocessable Entity",
    500: "Internal Server Error",
    503: "Service Unavailable",
    504: "Gateway Timeout",
}


def gerar_identificador(prefixo=""):
    """Inventa um identificador único, como os sistemas reais fazem."""
    return prefixo + "".join(random.choices("abcdef0123456789", k=12))


def montar_corpo_erro(api, momento, status, codigo, mensagem):
    """
    Monta o corpo da resposta de erro no formato daquela API.
    Cada formato usa tags diferentes — igual acontece na vida real.
    """

    formato = api["formato_erro"]

    if formato == "descritivo":
        corpo = {
            "description": mensagem,
            "serviceName": api["nome"],
            "errorCode": codigo,
            "errorMessage": mensagem,
            "timestamp": momento.isoformat(),
        }

    elif formato == "spring":
        corpo = {
            "status": status,
            "error": TEXTO_DO_STATUS.get(status, "Error"),
            "message": mensagem,
            "internalCode": codigo.lower().replace("_", "."),
            "traceId": gerar_identificador(),
        }

    else:  # aninhado
        corpo = {
            "serviceName": api["nome"],
            "errorDetail": {
                "code": codigo,
                "message": mensagem,
            },
            "requestId": gerar_identificador("req-"),
        }

    return json.dumps(corpo, ensure_ascii=False)


def montar_corpo_requisicao(api):
    """
    Monta o corpo enviado na requisição.
    GET normalmente não tem corpo; POST tem.
    """

    if api["metodo"] == "GET":
        return ""

    if api["nome"] == "api-pedidos":
        corpo = {
            "clienteId": random.randint(1000, 9999),
            "itens": random.randint(1, 5),
        }
    else:
        corpo = {
            "clienteId": random.randint(1000, 9999),
            "valor": round(random.uniform(10, 2000), 2),
        }

    return json.dumps(corpo, ensure_ascii=False)


def sortear_resultado(nome_api, momento, momento_deploy):
    """
    Decide se a requisição deu certo ou errado.
    Depois do deploy, a API afetada passa a errar muito mais.
    """

    chance_erro_tecnico = 1     # 1%
    chance_erro_negocio = 5     # 5%

    if nome_api == API_AFETADA and momento >= momento_deploy:
        chance_erro_tecnico = 25    # 25%
        chance_erro_negocio = 8     # 8%

    sorteio = random.randint(1, 100)

    if sorteio <= chance_erro_tecnico:
        return random.choice(ERROS_TECNICOS)

    if sorteio <= chance_erro_tecnico + chance_erro_negocio:
        return random.choice(ERROS_NEGOCIO[nome_api])

    return (200, None, None)


def montar_documento(api, momento, momento_deploy):
    """Monta uma requisição completa, no padrão de campos da empresa."""

    status, codigo, mensagem = sortear_resultado(
        api["nome"], momento, momento_deploy
    )

    # Requisições com sucesso não têm corpo de erro
    if codigo:
        corpo_resposta = montar_corpo_erro(api, momento, status, codigo, mensagem)
    else:
        corpo_resposta = ""

    return {
        "@timestamp": momento.isoformat(),
        "labels": {
            "http_request_url": api["url"],
            "http_response_status": str(status),
            "http_request_body_full": montar_corpo_requisicao(api),
            "http_response_body_full": corpo_resposta,
        },
    }


def gerar_todos_os_documentos():
    """Percorre hora a hora do período e gera as requisições."""

    agora = datetime.now()
    inicio = agora - timedelta(days=DIAS_DE_DADOS)
    momento_deploy = agora - timedelta(hours=HORAS_ATRAS_DO_DEPLOY)

    documentos = []
    momento = inicio

    while momento < agora:
        for api in APIS:
            for _ in range(REQUISICOES_POR_HORA):
                instante = momento + timedelta(seconds=random.randint(0, 3599))
                documentos.append(montar_documento(api, instante, momento_deploy))

        momento += timedelta(hours=1)

    return documentos, momento_deploy


MAPEAMENTO = {
    "properties": {
        "@timestamp": {"type": "date"},
        "labels": {
            "properties": {
                "http_request_url": {"type": "keyword"},
                "http_response_status": {"type": "keyword"},
                "http_request_body_full": {"type": "text"},
                "http_response_body_full": {"type": "text"},
            }
        },
    }
}


def enviar_para_elasticsearch(documentos):
    """Apaga o índice antigo e grava os documentos novos, em lotes."""

    conexao = conectar_elasticsearch()

    if conexao.indices.exists(index=NOME_INDICE):
        conexao.indices.delete(index=NOME_INDICE)

    conexao.indices.create(index=NOME_INDICE, mappings=MAPEAMENTO)

    acoes = [{"_index": NOME_INDICE, "_source": doc} for doc in documentos]

    # chunk_size = quantos documentos vão por vez
    helpers.bulk(conexao, acoes, chunk_size=500, request_timeout=60)


if __name__ == "__main__":
    print("Gerando dados fictícios...")
    documentos, momento_deploy = gerar_todos_os_documentos()
    print(f"{len(documentos)} requisições geradas.")

    print("Gravando no Elasticsearch...")
    enviar_para_elasticsearch(documentos)

    print()
    print("Pronto!")
    print(f"Índice: {NOME_INDICE}")
    print(f"Deploy simulado em: {momento_deploy.strftime('%d/%m/%Y %H:%M')}")
    print(f"API afetada: {API_AFETADA}")