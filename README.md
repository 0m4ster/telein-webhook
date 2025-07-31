# Telein Webhook API

API webhook para integração com o Telein.

## 🚀 Endpoints Disponíveis

### Webhook Principal
- **POST** `/webhook/telein` - Recebe webhooks do Telein

### Endpoints de Teste
- **GET** `/` - Status da API
- **GET** `/health` - Verificação de saúde
- **POST** `/test/webhook` - Teste do webhook
- **POST** `/receber_lead` - Endpoint original para leads

## 📋 Como Configurar no Telein

### 1. URL do Webhook
```
https://seu-dominio.com/webhook/telein
```

### 2. Eventos Suportados
- `lead_created` - Quando um lead é criado
- `campaign_updated` - Quando uma campanha é atualizada
- `contact_form_submitted` - Quando um formulário é enviado

### 3. Formato dos Dados
```json
{
  "event_type": "lead_created",
  "lead_data": {
    "id": "123",
    "nome": "João Silva",
    "email": "joao@exemplo.com",
    "telefone": "(11) 99999-9999"
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "source": "telein"
}
```

## 🛠️ Deploy em Servidor

### Opção 1: Deploy Local
```bash
# Instalar dependências
pip install -r requirements.txt

# Executar
python endvan.py
```

### Opção 2: Com Uvicorn
```bash
uvicorn endvan:app --host 0.0.0.0 --port 8000
```

### Opção 3: Deploy em Produção
```bash
# Com gunicorn (recomendado para produção)
pip install gunicorn
gunicorn endvan:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🔧 Variáveis de Ambiente

Crie um arquivo `.env`:
```env
HOST=0.0.0.0
PORT=8000
WEBHOOK_SECRET=seu_secret_aqui
LOG_LEVEL=INFO
ENABLE_LOGGING=true
```

## 📊 Monitoramento

### Logs
A API gera logs automáticos de todos os webhooks recebidos.

### Health Check
```bash
curl https://seu-dominio.com/health
```

## 🔒 Segurança

- Configure `WEBHOOK_SECRET` para autenticação
- Use HTTPS em produção
- Configure CORS adequadamente

## 📝 Exemplo de Uso

### Teste com curl:
```bash
curl -X POST https://seu-dominio.com/webhook/telein \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "lead_created",
    "lead_data": {
      "nome": "João Silva",
      "email": "joao@exemplo.com"
    }
  }'
```

## 🚀 Próximos Passos

1. Deploy em servidor (Heroku, VPS, etc.)
2. Configurar domínio HTTPS
3. Adicionar autenticação
4. Implementar banco de dados
5. Configurar notificações por email 