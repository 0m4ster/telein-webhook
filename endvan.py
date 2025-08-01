from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from datetime import datetime
import httpx
import asyncio

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
        "api_key": "SUA_API_KEY_AQUI",
        "token": "SEU_TOKEN_AQUI"
    }
}

# Função para enviar dados para outros endpoints
async def forward_to_endpoint(endpoint_url: str, data: Dict[str, Any], event_type: str = "unknown"):
    """Envia dados para outro endpoint"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            
            # Formata dados para a API da IPLUC
            if "api.ipluc.com" in endpoint_url:
                # Extrai dados do lead do Telein
                lead_data = data.get("lead_data", {})
                
                # Formata payload para IPLUC
                payload = {
                    "nome": lead_data.get("nome", ""),
                    "telefone": lead_data.get("telefone", ""),
                    "email": lead_data.get("email", ""),
                    "campanha": lead_data.get("campanha", ""),
                    "fonte": "telein_webhook",
                    "event_type": event_type,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Headers com autenticação
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEYS['ipluc']['token']}",
                    "X-API-Key": API_KEYS['ipluc']['api_key']
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
            
            if response.status_code in [200, 201, 202]:
                print(f"Dados enviados com sucesso para {endpoint_url}")
                return {
                    "status": "success",
                    "forwarded_to": endpoint_url,
                    "response_status": response.status_code,
                    "response_data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                }
            else:
                print(f"Erro ao enviar dados para {endpoint_url}: {response.status_code}")
                return {
                    "status": "error",
                    "forwarded_to": endpoint_url,
                    "response_status": response.status_code,
                    "error": response.text
                }
                
    except Exception as e:
        print(f"Erro ao enviar dados para {endpoint_url}: {str(e)}")
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
    timestamp: Optional[str] = None
    source: Optional[str] = None

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
        data = await request.json()
        
        # Log dos dados recebidos
        print(f"Webhook recebido do Telein: {json.dumps(data, indent=2)}")
        
        # Processa diferentes tipos de eventos
        event_type = data.get("event_type", "unknown")
        
        if event_type == "lead_created":
            return await process_lead_created(data)
        elif event_type == "campaign_updated":
            return await process_campaign_updated(data)
        elif event_type == "contact_form_submitted":
            return await process_contact_form(data)
        else:
            # Processa dados genéricos
            return await process_generic_webhook(data)
            
    except Exception as e:
        print(f"Erro no webhook: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Erro ao processar webhook: {str(e)}")

# Processa criação de lead
async def process_lead_created(data: Dict[str, Any]):
    lead_data = data.get("lead_data", {})
    
    # Aqui você pode salvar no banco, enviar para CRM, etc.
    print(f"Processando lead criado: {lead_data}")
    
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

# Processa atualização de campanha
async def process_campaign_updated(data: Dict[str, Any]):
    campaign_data = data.get("campaign_data", {})
    
    print(f"Processando atualização de campanha: {campaign_data}")
    
    # Envia dados para outro endpoint
    endpoint_url = DESTINATION_ENDPOINTS.get("campaign_updated", DESTINATION_ENDPOINTS["default"])
    forward_result = await forward_to_endpoint(endpoint_url, data, "campaign_updated")
    
    return {
        "status": "success",
        "message": "Campanha atualizada processada",
        "event_type": "campaign_updated",
        "campaign_id": campaign_data.get("id"),
        "timestamp": datetime.now().isoformat(),
        "forward_result": forward_result
    }

# Processa formulário de contato
async def process_contact_form(data: Dict[str, Any]):
    form_data = data.get("form_data", {})
    
    print(f"Processando formulário de contato: {form_data}")
    
    # Envia dados para outro endpoint
    endpoint_url = DESTINATION_ENDPOINTS.get("contact_form_submitted", DESTINATION_ENDPOINTS["default"])
    forward_result = await forward_to_endpoint(endpoint_url, data, "contact_form_submitted")
    
    return {
        "status": "success",
        "message": "Formulário de contato processado",
        "event_type": "contact_form_submitted",
        "timestamp": datetime.now().isoformat(),
        "forward_result": forward_result
    }

# Processa webhook genérico
async def process_generic_webhook(data: Dict[str, Any]):
    print(f"Processando webhook genérico: {data}")
    
    # Envia dados para outro endpoint
    endpoint_url = DESTINATION_ENDPOINTS["default"]
    forward_result = await forward_to_endpoint(endpoint_url, data, "generic")
    
    return {
        "status": "success",
        "message": "Webhook processado com sucesso",
        "received_data": data,
        "timestamp": datetime.now().isoformat(),
        "forward_result": forward_result
    }

# Endpoint POST original (mantido para compatibilidade)
@app.post("/receber_lead")
async def receber_lead(lead: Lead):
    # Aqui você pode salvar em banco, processar, etc.
    print(f"Lead recebido: {lead.dict()}")
    
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

# Endpoint para visualizar chaves de API (sem mostrar os valores)
@app.get("/config/api-keys")
async def get_api_keys_config():
    """Retorna a configuração atual das chaves de API (sem valores)"""
    config_info = {}
    for service, keys in API_KEYS.items():
        config_info[service] = {
            "configured_keys": list(keys.keys()),
            "has_api_key": "api_key" in keys and keys["api_key"] != "SUA_API_KEY_AQUI",
            "has_token": "token" in keys and keys["token"] != "SEU_TOKEN_AQUI"
        }
    
    return {
        "api_keys_config": config_info,
        "timestamp": datetime.now().isoformat()
    }

# Para executar com uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
