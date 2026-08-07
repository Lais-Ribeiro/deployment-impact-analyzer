# Cria conexão com o Elasticsearch

import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

def conectar_elasticsearch():

    elastic_url = os.getenv("ELASTIC_URL_SEARCH")

    conexao = Elasticsearch(
        elastic_url,
        request_timeout=60,   # espera até 60 segundos antes de desistir
    )

    return conexao