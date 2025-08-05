from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from datetime import datetime
import httpx
import asyncio
import os
import uuid
import logging

# Configurar logging para debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telein Webhook API", description="API para receber webhooks do Telein")

# Configurações dos endpoints de destino
DESTINATION_ENDPOINTS = {
    "lead_created": "https://api.ipluc.com/api/salvar-lead",
    "campaign_updated": "https://api.ipluc.com/api/salvar-lead", 
    "contact_form_submitted": "https://api.ipluc.com/api/salvar-lead",
    "default": "https://api.ipluc.com/api/salvar-lead"
}

# Configurações de autenticação (você precisa configurar essas chaves)
API_KEYS = {
    "ipluc": {
        "api_key": os.getenv("IPLUC_API_KEY", "SUA_API_KEY_AQUI")
    }
}

# Função para enviar dados para outros endpoints
async def forward_to_endpoint(endpoint_url: str, data: Dict[str, Any], event_type: str = "unknown"):
    """Envia dados para outro endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            # Formata dados para a API da IPLUC
            if "api.ipluc.com" in endpoint_url:
                # Log completo dos dados recebidos
                logger.info(f"=== DADOS RECEBIDOS DO TELEIN ===")
                logger.info(f"Event type: {event_type}")
                logger.info(f"Data completo: {json.dumps(data, indent=2)}")
                
                # Extrai dados do lead do Telein - tenta diferentes estruturas
                lead_data = data.get("lead_data", {})
                client_data = data.get("client_data", {})
                call_data = data.get("call_data", {})
                
                # Se não encontrar lead_data ou client_data, usa o próprio data
                if not lead_data and not client_data and not call_data:
                    lead_data = data
                    client_data = data
                    call_data = data
                
                # Tenta extrair nome de diferentes campos possíveis
                nome = (
                    lead_data.get("nome") or 
                    client_data.get("nome") or 
                    call_data.get("nome") or
                    lead_data.get("name") or 
                    client_data.get("name") or 
                    call_data.get("name") or
                    lead_data.get("nome_completo") or 
                    client_data.get("nome_completo") or 
                    call_data.get("nome_completo") or
                    lead_data.get("cliente_nome") or 
                    client_data.get("cliente_nome") or 
                    call_data.get("cliente_nome") or
                    ""
                )
                
                # Tenta extrair telefone de diferentes campos possíveis
                telefone = (
                    str(lead_data.get("telefone") or "") or
                    str(client_data.get("telefone") or "") or
                    str(call_data.get("telefone") or "") or
                    str(lead_data.get("phone") or "") or
                    str(client_data.get("phone") or "") or
                    str(call_data.get("phone") or "") or
                    str(lead_data.get("telefone_1") or "") or
                    str(client_data.get("telefone_1") or "") or
                    str(call_data.get("telefone_1") or "") or
                    str(lead_data.get("cliente_telefone") or "") or
                    str(client_data.get("cliente_telefone") or "") or
                    str(call_data.get("cliente_telefone") or "") or
                    str(data.get("telefone") or "") or
                    str(data.get("phone") or "") or
                    ""
                )
                
                # Tenta extrair CPF de diferentes campos possíveis
                cpf = (
                    lead_data.get("cpf") or 
                    client_data.get("cpf") or 
                    call_data.get("cpf") or
                    lead_data.get("documento") or 
                    client_data.get("documento") or 
                    call_data.get("documento") or
                    lead_data.get("cliente_cpf") or 
                    client_data.get("cliente_cpf") or 
                    call_data.get("cliente_cpf") or
                    data.get("cpf") or
                    data.get("documento") or
                    ""
                )
                
                logger.info(f"=== DADOS EXTRAÍDOS ===")
                logger.info(f"Nome: '{nome}'")
                logger.info(f"Telefone: '{telefone}'")
                logger.info(f"CPF: '{cpf}'")
                
                # Verifica se tem dados mínimos - agora aceita apenas telefone
                if not telefone:
                    logger.error("ERRO: Nenhum telefone encontrado nos dados!")
                    return {
                        "status": "error",
                        "forwarded_to": endpoint_url,
                        "error": "Dados insuficientes: telefone não encontrado"
                    }
                
                # Se não tem nome, usa um nome padrão
                if not nome:
                    nome = "Cliente Telein"
                    logger.warning(f"Nome não encontrado, usando padrão: {nome}")
                
                # Formata payload para IPLUC conforme documentação
                payload = {
                    "id": int(str(uuid.uuid4().int)[:10]),  # ID único 
                    "status_id": 15135,  
                    "nome": nome,
                    "telefone_1": telefone,
                    "cpf": cpf,
                    "utm_source": "URA",
                    "codigo_convenio": "INSS"
                }
                
                # Headers conforme documentação da IPLUC
                headers = {
                    "Content-Type": "application/json",
                    "apikey": API_KEYS['ipluc']['api_key']
                }
                
                # Debug: log da chave sendo enviada (sem mostrar completa)
                api_key = API_KEYS['ipluc']['api_key']
                logger.info(f"=== ENVIANDO PARA IPLUC ===")
                logger.info(f"URL: {endpoint_url}")
                logger.info(f"API Key: {api_key[:10]}...{api_key[-10:] if len(api_key) > 20 else '***'}")
                logger.info(f"Payload: {json.dumps(payload, indent=2)}")
                
                # Verifica se a API key está configurada
                if api_key == "SUA_API_KEY_AQUI":
                    logger.error("ERRO: API Key da IPLUC não está configurada!")
                    return {
                        "status": "error",
                        "forwarded_to": endpoint_url,
                        "error": "API Key da IPLUC não configurada"
                    }
                
            else:
                # Formato padrão para outros endpoints
                payload = {
                    "source": "telein_webhook",
                    "event_type": event_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
                headers = {"Content-Type": "application/json"}
            
            response = await client.post(endpoint_url, json=payload, headers=headers)
            
            logger.info(f"=== RESPOSTA DA IPLUC ===")
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            logger.info(f"Response Body: {response.text}")
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"✅ Dados enviados com sucesso para {endpoint_url}")
                return {
                    "status": "success",
                    "forwarded_to": endpoint_url,
                    "response_status": response.status_code,
                    "response_data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                }
            else:
                logger.error(f"❌ Erro ao enviar dados para {endpoint_url}: {response.status_code}")
                return {
                    "status": "error",
                    "forwarded_to": endpoint_url,
                    "response_status": response.status_code,
                    "error": response.text
                }
                
    except Exception as e:
        logger.error(f"❌ Erro ao enviar dados para {endpoint_url}: {str(e)}")
        return {
            "status": "error",
            "forwarded_to": endpoint_url,
            "error": str(e)
        }

# Modelo para dados do Telein
class TeleinWebhook(BaseModel):
    event_type: Optional[str] = None
    lead_data: Optional[Dict[str, Any]] = None
    campaign_data: Optional[Dict[str, Any]] = None
    client_data: Optional[Dict[str, Any]] = None
    call_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    source: Optional[str] = None
    key: Optional[str] = None

#entradas
class Lead(BaseModel):
    nome: str
    telefone: str
    mailing: str
    campanha: str
    opcao: str
    email: str
    endereco: str

@app.get("/")
async def root():
    return {
        "mensagem": "Telein Webhook API está funcionando!",
        "status": "online",
        "endpoints": {
            "webhook": "/webhook/telein",
            "lead": "/receber_lead",
            "health": "/health"
        }
    }

# Endpoint de saúde da API
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Telein Webhook API"
    }

# Webhook principal para Telein
@app.post("/webhook/telein")
async def telein_webhook(request: Request):
    try:
        # Recebe dados brutos do request
        body = await request.body()
        
        logger.info(f"=== WEBHOOK RECEBIDO ===")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Body raw: {body}")
        
        # Tenta fazer parse do JSON
        try:
            data = await request.json()
            logger.info(f"Data parsed: {json.dumps(data, indent=2)}")
        except Exception as json_error:
            logger.error(f"Erro ao fazer parse do JSON: {json_error}")
            # Se não conseguir fazer parse, usa o body como string
            data = {"raw_body": body.decode('utf-8', errors='ignore')}
            logger.info(f"Usando body como string: {data}")
        
        # Log dos dados recebidos
        logger.info(f"Webhook recebido do Telein: {json.dumps(data, indent=2)}")
        
        # Processa diferentes tipos de eventos
        event_type = data.get("event_type", "unknown")
        key_pressed = data.get("key")
        
        logger.info(f"Event type detectado: {event_type}")
        logger.info(f"Key pressed: {key_pressed}")
        
        # Processa diferentes tipos de eventos que podem gerar leads
        if event_type == "key_pressed" and key_pressed == "2":
            logger.info(f"✅ Processando tecla 2 - Criando lead")
            return await process_key_pressed_2(data)
        elif event_type == "lead_created":
            logger.info(f"✅ Processando lead criado")
            return await process_lead_created(data)
        elif event_type == "call_answered":
            logger.info(f"✅ Processando chamada atendida")
            return await process_call_answered(data)
        elif event_type == "contact_form_submitted":
            logger.info(f"✅ Processando formulário de contato")
            return await process_contact_form(data)
        else:
            # Para todos os outros casos, apenas loga mas não processa
            logger.info(f"❌ Ignorando evento: {event_type} (key: {key_pressed})")
            return {
                "status": "ignored",
                "message": f"Evento ignorado: {event_type}",
                "event_type": event_type,
                "key": key_pressed,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Erro no webhook: {str(e)}")
        # Retorna erro mas não falha completamente
        return {
            "status": "error",
            "message": f"Erro ao processar webhook: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }

# Webhook GET para Telein (compatibilidade)
@app.get("/webhook/telein")
async def telein_webhook_get():
    """Endpoint GET para compatibilidade com Telein"""
    return {
        "status": "success",
        "message": "Webhook GET funcionando",
        "endpoint": "/webhook/telein",
        "method": "GET",
        "timestamp": datetime.now().isoformat()
    }

# Processa criação de lead
async def process_lead_created(data: Dict[str, Any]):
    lead_data = data.get("lead_data", {})
    
    # Aqui você pode salvar no banco, enviar para CRM, etc.
    logger.info(f"Processando lead criado: {lead_data}")
    
    # Envia dados para outro endpoint
    endpoint_url = DESTINATION_ENDPOINTS.get("lead_created", DESTINATION_ENDPOINTS["default"])
    forward_result = await forward_to_endpoint(endpoint_url, data, "lead_created")
    
    return {
        "status": "success",
        "message": "Lead processado com sucesso",
        "event_type": "lead_created",
        "lead_id": lead_data.get("id"),
        "timestamp": datetime.now().isoformat(),
        "forward_result": forward_result
    }

# Processa quando tecla "2" for pressionada
async def process_key_pressed_2(data: Dict[str, Any]):
    logger.info(f"Cliente pressionou tecla 2: {data}")
    
    # Extrai dados do cliente que pressionou "2"
    client_data = data.get("client_data", {})
    
    # Envia dados para IPLUC
    endpoint_url = DESTINATION_ENDPOINTS["default"]
    forward_result = await forward_to_endpoint(endpoint_url, data, "key_pressed_2")
    
    return {
        "status": "success",
        "message": "Lead criado por pressionar tecla 2",
        "event_type": "key_pressed_2",
        "client_data": client_data,
        "timestamp": datetime.now().isoformat(),
        "forward_result": forward_result
    }

# Processa quando chamada for atendida
async def process_call_answered(data: Dict[str, Any]):
    logger.info(f"Chamada atendida: {data}")
    
    # Extrai dados da chamada
    call_data = data.get("call_data", {})
    
    # Envia dados para IPLUC
    endpoint_url = DESTINATION_ENDPOINTS["default"]
    forward_result = await forward_to_endpoint(endpoint_url, data, "call_answered")
    
    return {
        "status": "success",
        "message": "Lead criado por chamada atendida",
        "event_type": "call_answered",
        "call_data": call_data,
        "timestamp": datetime.now().isoformat(),
        "forward_result": forward_result
    }

# Processa formulário de contato
async def process_contact_form(data: Dict[str, Any]):
    logger.info(f"Formulário de contato: {data}")
    
    # Extrai dados do formulário
    form_data = data.get("form_data", {})
    
    # Envia dados para IPLUC
    endpoint_url = DESTINATION_ENDPOINTS["default"]
    forward_result = await forward_to_endpoint(endpoint_url, data, "contact_form_submitted")
    
    return {
        "status": "success",
        "message": "Lead criado por formulário de contato",
        "event_type": "contact_form_submitted",
        "form_data": form_data,
        "timestamp": datetime.now().isoformat(),
        "forward_result": forward_result
    }

# Endpoint POST original (mantido para compatibilidade)
@app.post("/receber_lead")
async def receber_lead(lead: Lead):
    # Aqui você pode salvar em banco, processar, etc.
    logger.info(f"Lead recebido: {lead.dict()}")
    
    return {
        "mensagem": "Lead recebido com sucesso!",
        "dados": lead,
        "timestamp": datetime.now().isoformat()
    }

# Endpoint para testar webhook
@app.post("/test/webhook")
async def test_webhook():
    """Endpoint para testar se o webhook está funcionando"""
    test_data = {
        "event_type": "test",
        "message": "Teste de webhook",
        "timestamp": datetime.now().isoformat()
    }
    
    return {
        "status": "success",
        "message": "Webhook testado com sucesso",
        "test_data": test_data
    }

# Endpoint para testar dados do Telein
@app.post("/test/telein-data")
async def test_telein_data():
    """Testa com dados simulados do Telein"""
    # Simula dados que o Telein pode enviar
    test_data = {
        "event_type": "key_pressed",
        "key": "2",
        "client_data": {
            "nome": "João Silva Teste",
            "telefone": "11999999999",
            "cpf": "12345678901"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Processa como se fosse um webhook real
    result = await process_key_pressed_2(test_data)
    
    return {
        "status": "success",
        "message": "Teste de dados do Telein",
        "test_data": test_data,
        "process_result": result
    }

# Endpoint para configurar endpoints de destino
@app.post("/config/endpoints")
async def configure_endpoints(endpoints: Dict[str, str]):
    """Configura os endpoints de destino"""
    global DESTINATION_ENDPOINTS
    
    # Atualiza apenas os endpoints fornecidos
    for event_type, url in endpoints.items():
        DESTINATION_ENDPOINTS[event_type] = url
    
    return {
        "status": "success",
        "message": "Endpoints configurados com sucesso",
        "current_endpoints": DESTINATION_ENDPOINTS
    }

# Endpoint para visualizar configuração atual
@app.get("/config/endpoints")
async def get_endpoints_config():
    """Retorna a configuração atual dos endpoints"""
    return {
        "endpoints": DESTINATION_ENDPOINTS,
        "timestamp": datetime.now().isoformat()
    }

# Endpoint para configurar chaves de API
@app.post("/config/api-keys")
async def configure_api_keys(api_keys: Dict[str, Dict[str, str]]):
    """Configura as chaves de API"""
    global API_KEYS
    
    # Atualiza as chaves fornecidas
    for service, keys in api_keys.items():
        if service not in API_KEYS:
            API_KEYS[service] = {}
        API_KEYS[service].update(keys)
    
    return {
        "status": "success",
        "message": "Chaves de API configuradas com sucesso",
        "configured_services": list(api_keys.keys())
    }

# Endpoint específico para configurar API key da IPLUC
@app.post("/config/ipluc-api-key")
async def configure_ipluc_api_key(api_key: str):
    """Configura especificamente a API key da IPLUC"""
    global API_KEYS
    
    if "ipluc" not in API_KEYS:
        API_KEYS["ipluc"] = {}
    
    API_KEYS["ipluc"]["api_key"] = api_key
    
    return {
        "status": "success",
        "message": "API Key da IPLUC configurada com sucesso",
        "api_key_length": len(api_key),
        "api_key_preview": f"{api_key[:10]}...{api_key[-10:]}" if len(api_key) > 20 else "***"
    }

# Endpoint para testar conexão com IPLUC
@app.post("/test/ipluc-connection")
async def test_ipluc_connection():
    """Testa a conexão com a API da IPLUC"""
    try:
        api_key = API_KEYS['ipluc']['api_key']
        
        if api_key == "SUA_API_KEY_AQUI":
            return {
                "status": "error",
                "message": "API Key da IPLUC não está configurada",
                "solution": "Use o endpoint /config/ipluc-api-key para configurar"
            }
        
        # Testa com dados fictícios
        test_payload = {
            "id": 123456789,
            "status_id": 15135,
            "nome": "TESTE CONEXÃO",
            "telefone_1": "11999999999",
            "cpf": "12345678901",
            "utm_source": "URA",
            "codigo_convenio": "INSS"
        }
        
        headers = {
            "Content-Type": "application/json",
            "apikey": api_key
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.ipluc.com/api/salvar-lead",
                json=test_payload,
                headers=headers
            )
            
            return {
                "status": "success" if response.status_code in [200, 201, 202] else "error",
                "message": "Teste de conexão com IPLUC",
                "response_status": response.status_code,
                "response_body": response.text,
                "api_key_configured": True
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Erro ao testar conexão com IPLUC: {str(e)}",
            "api_key_configured": API_KEYS['ipluc']['api_key'] != "SUA_API_KEY_AQUI"
        }

# Endpoint para visualizar chaves de API (sem mostrar os valores)
@app.get("/config/api-keys")
async def get_api_keys_config():
    """Retorna a configuração atual das chaves de API (sem valores)"""
    config_info = {}
    for service, keys in API_KEYS.items():
        config_info[service] = {
            "configured_keys": list(keys.keys()),
            "has_api_key": "api_key" in keys and keys["api_key"] != "SUA_API_KEY_AQUI"
        }
    
    return {
        "api_keys_config": config_info,
        "timestamp": datetime.now().isoformat()
    }

# Endpoint para verificar status da configuração
@app.get("/status")
async def get_status():
    """Retorna o status atual da configuração"""
    ipluc_api_key = API_KEYS['ipluc']['api_key']
    
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "ipluc_config": {
            "api_key_configured": ipluc_api_key != "SUA_API_KEY_AQUI",
            "api_key_length": len(ipluc_api_key),
            "api_key_preview": f"{ipluc_api_key[:10]}...{ipluc_api_key[-10:]}" if len(ipluc_api_key) > 20 and ipluc_api_key != "SUA_API_KEY_AQUI" else "***",
            "env_variable": "IPLUC_API_KEY",
            "env_value": os.getenv("IPLUC_API_KEY", "NÃO CONFIGURADO")
        },
        "endpoints": {
            "webhook": "/webhook/telein",
            "ipluc_config": "/config/ipluc-api-key",
            "ipluc_test": "/test/ipluc-connection",
            "status": "/status",
            "debug_env": "/debug/environment"
        },
        "next_steps": [
            "1. Configure a API key da IPLUC usando POST /config/ipluc-api-key",
            "2. Teste a conexão usando POST /test/ipluc-connection",
            "3. Configure o Telein para enviar webhooks para https://telein-webhook.onrender.com/webhook/telein"
        ]
    }

# Endpoint para debug do ambiente
@app.get("/debug/environment")
async def debug_environment():
    """Debug das variáveis de ambiente"""
    return {
        "ipluc_api_key_env": os.getenv("IPLUC_API_KEY", "NÃO CONFIGURADO"),
        "ipluc_api_key_length": len(os.getenv("IPLUC_API_KEY", "")),
        "current_api_key": API_KEYS['ipluc']['api_key'],
        "current_api_key_length": len(API_KEYS['ipluc']['api_key']),
        "environment_variables": {
            "IPLUC_API_KEY": "CONFIGURADO" if os.getenv("IPLUC_API_KEY") else "NÃO CONFIGURADO",
            "PORT": os.getenv("PORT", "NÃO CONFIGURADO"),
            "RENDER": os.getenv("RENDER", "NÃO CONFIGURADO")
        }
    }

# Endpoint de debug simples
@app.get("/debug/test")
async def debug_test():
    """Endpoint simples para testar se o código foi atualizado"""
    return {
        "status": "success",
        "message": "Código atualizado funcionando",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0"
    }

# Para executar com uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
