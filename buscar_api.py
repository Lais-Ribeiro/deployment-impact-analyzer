"""
ARQUIVO: buscar_api.py

Consulta no Elasticsearch o volume de requisições de uma API
dentro de um período informado.
"""

import os
from datetime import datetime

from dotenv import load_dotenv
from elastic_transport import ConnectionTimeout

from conexao_elastic import conectar_elasticsearch

load_dotenv()

NOME_INDICE = os.getenv("ELASTIC_INDICE")


def formatar_data(data_informada):
    """
    Converte:
    09/08/2026 13:00

    Para:
    2026-08-09T13:00:00
    """

    data = datetime.strptime(data_informada, "%d/%m/%Y %H:%M")

    return data.strftime("%Y-%m-%dT%H:%M:%S")


def validar_periodo(data_inicio, data_fim):
    """Confere se o período informado faz sentido."""

    inicio = datetime.strptime(data_inicio, "%d/%m/%Y %H:%M")
    fim = datetime.strptime(data_fim, "%d/%m/%Y %H:%M")

    if fim <= inicio:
        raise ValueError(
            "A data final precisa ser maior que a data inicial."
        )

    duracao_segundos = (fim - inicio).total_seconds()

    if duracao_segundos > 3600:
        raise ValueError(
            "O período máximo permitido por consulta é de 1 hora."
        )


def consultar_volume_por_api(url, data_inicio, data_fim):
    """
    Consulta quantas requisições existem para uma API no período.

    Devolve o total e as URLs distintas encontradas.
    """

    conexao = conectar_elasticsearch()

    if url.startswith("http"):
        filtro_api = {
            "term": {
                "labels.http_request_url": url
            }
        }
    else:
        filtro_api = {
            "wildcard": {
                "labels.http_request_url": {"value": f"*{url}*"}
            }
        }

    resposta = conexao.search(
        index=NOME_INDICE,
        size=0,
        track_total_hits=False,
        request_timeout=60,
        timeout="30s",
        query={
            "bool": {
                "filter": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": data_inicio,
                                "lte": data_fim
                            }
                        }
                    },
                    filtro_api
                ]
            }
        },
        aggs={
            "total_requisicoes": {
                "filter": {
                    "match_all": {}
                }
            },
            "urls": {
                "terms": {
                    "field": "labels.http_request_url",
                    "size": 20
                }
            }
        }
    )

    if resposta.get("timed_out"):
        raise TimeoutError(
            "A consulta excedeu o tempo permitido. "
            "Reduza o intervalo de análise."
        )

    total_requisicoes = resposta[
        "aggregations"
    ]["total_requisicoes"]["doc_count"]

    urls_encontradas = {
        grupo["key"]: grupo["doc_count"]
        for grupo in resposta["aggregations"]["urls"]["buckets"]
    }

    return total_requisicoes, urls_encontradas


def exibir_resultado(
    url,
    data_inicio,
    data_fim,
    total_requisicoes,
    urls_encontradas
):
    """Mostra na tela o resultado da consulta."""

    print()
    print(f"URL consultada: {url}")
    print(f"Período: {data_inicio} até {data_fim}")
    print(f"Total de requisições: {total_requisicoes}")
    print()

    if not urls_encontradas:
        print("Nenhum dado encontrado.")
        return

    print("URLs encontradas:")

    for endereco, quantidade in urls_encontradas.items():
        print(f"{endereco} -> {quantidade}")


if __name__ == "__main__":

    try:
        url_informada = input(
            "Informe a URL da API: "
        ).strip()

        data_inicio_informada = input(
            "Informe a data inicial (exemplo: 09/08/2026 13:00): "
        ).strip()

        data_fim_informada = input(
            "Informe a data final (exemplo: 09/08/2026 14:00): "
        ).strip()

        validar_periodo(
            data_inicio_informada,
            data_fim_informada
        )

        data_inicio_elastic = formatar_data(
            data_inicio_informada
        )

        data_fim_elastic = formatar_data(
            data_fim_informada
        )

        total, urls = consultar_volume_por_api(
            url_informada,
            data_inicio_elastic,
            data_fim_elastic
        )

        exibir_resultado(
            url_informada,
            data_inicio_informada,
            data_fim_informada,
            total,
            urls
        )

    except ValueError as erro:
        print()
        print(f"Dados inválidos: {erro}")

    except ConnectionTimeout:
        print()
        print(
            "O Elasticsearch demorou para responder. "
            "Tente novamente com um período menor."
        )

    except TimeoutError as erro:
        print()
        print(erro)

    except Exception as erro:
        print()
        print(f"Erro ao consultar o Elasticsearch: {erro}")