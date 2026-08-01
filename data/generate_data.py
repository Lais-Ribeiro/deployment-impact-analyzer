import random
from datetime import datetime, timedelta

def lista_alaeatoria(campo):

    campo = random.choice(campo)
    
    return campo

def gerar_timestamp_aleatorio():
    agora = datetime.now()
    segundos_aleatorios = random.randint(0, 43200) 
    timestamp = agora - timedelta(seconds=segundos_aleatorios)

    return timestamp.isoformat()

def generate_logs(num_logs):

    lista_logs = []
    lista_status_codes = [200, 201, 204, 400, 412, 421, 500, 504, 550]
    lista_endpoints = ["/api/v1/users", "/api/v1/products", "/api/v1/orders"]
    lista_erros = ["Timeout", "Database error", "Connection refused", "Unauthorized"]

    for i in range(num_logs):
        status = lista_alaeatoria(lista_status_codes)
        tem_erro = status >= 500
        
        logs = {
            "timestamp": gerar_timestamp_aleatorio(),
            "endpoint": lista_alaeatoria(lista_endpoints),
            "status_code": status,
            "latencia_ms": random.randint(50, 2000),
            "tipo_erro": lista_alaeatoria(lista_erros) if tem_erro else None
        }
        lista_logs.append(logs)
    return lista_logs

print(generate_logs(10))
