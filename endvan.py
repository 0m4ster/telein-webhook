from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json
from datetime import datetime

app = FastAPI(title="Telein Webhook API", description="API para receber webhooks do Telein")

# Modelo para dados do Telein
class TeleinWebhook(BaseModel):
    event_type: Optional[str] = None
    lead_data: Optional[Dict[str, Any]] = None
    campaign_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    source: Optional[str] = None

# Modelo de entrada original (mantido para compatibilidade)
class Lead(BaseModel):
    nome: str
    telefone: str
    mailing: str
    campanha: str
    opcao: str
    email: str
    endereco: str

# Endpoint GET para testar
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
    
    return {
        "status": "success",
        "message": "Lead processado com sucesso",
        "event_type": "lead_created",
        "lead_id": lead_data.get("id"),
        "timestamp": datetime.now().isoformat()
    }

# Processa atualização de campanha
async def process_campaign_updated(data: Dict[str, Any]):
    campaign_data = data.get("campaign_data", {})
    
    print(f"Processando atualização de campanha: {campaign_data}")
    
    return {
        "status": "success",
        "message": "Campanha atualizada processada",
        "event_type": "campaign_updated",
        "campaign_id": campaign_data.get("id"),
        "timestamp": datetime.now().isoformat()
    }

# Processa formulário de contato
async def process_contact_form(data: Dict[str, Any]):
    form_data = data.get("form_data", {})
    
    print(f"Processando formulário de contato: {form_data}")
    
    return {
        "status": "success",
        "message": "Formulário de contato processado",
        "event_type": "contact_form_submitted",
        "timestamp": datetime.now().isoformat()
    }

# Processa webhook genérico
async def process_generic_webhook(data: Dict[str, Any]):
    print(f"Processando webhook genérico: {data}")
    
    return {
        "status": "success",
        "message": "Webhook processado com sucesso",
        "received_data": data,
        "timestamp": datetime.now().isoformat()
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

# Para executar com uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
