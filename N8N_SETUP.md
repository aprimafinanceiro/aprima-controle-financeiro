# Setup n8n - Automação Visual WhatsApp → Facebook Marketplace

Este guia mostra como usar **n8n** (alternativa open-source ao Zapier) para criar a integração de forma visual, sem precisar de código Python.

## Por que usar n8n?

✅ **Interface Visual** - Arrastar e soltar nodes
✅ **Fácil de Modificar** - Sem precisar editar código
✅ **Self-hosted** - Roda na sua VPS
✅ **Open-source** - Gratuito
✅ **Integrações Prontas** - 400+ nodes (Supabase, HTTP, etc)
✅ **Execuções Ilimitadas** - Sem limites de workflows

## Opções de Deployment

### Opção 1: n8n Cloud (Mais Fácil)

1. Acesse: https://n8n.io/
2. Clique em "Start Free"
3. Crie uma conta
4. Importe o workflow (veja abaixo)

**Custo:** Grátis até 5.000 execuções/mês

### Opção 2: Self-hosted na VPS (Recomendado)

Rodar n8n na mesma VPS Hostinger junto com o sistema Python.

## Instalação n8n na VPS

### Passo 1: Instalar n8n com Docker

```bash
# Conecte na VPS
ssh root@seu-ip-da-vps

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Criar diretório para n8n
mkdir -p /opt/n8n
cd /opt/n8n

# Criar arquivo de configuração
nano docker-compose.yml
```

Cole o seguinte:

```yaml
version: '3.8'

services:
  n8n:
    image: n8nio/n8n
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=seu-dominio.com
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - NODE_ENV=production
      - WEBHOOK_URL=https://seu-dominio.com/
      - GENERIC_TIMEZONE=America/Sao_Paulo

      # Variáveis de ambiente do projeto
      - FACEBOOK_PAGE_ID=sua-page-id
      - FACEBOOK_ACCESS_TOKEN=seu-token
      - SUPABASE_URL=https://seu-projeto.supabase.co
      - SUPABASE_KEY=sua-key

    volumes:
      - n8n_data:/home/node/.n8n
      - /opt/n8n/workflows:/home/node/.n8n/workflows

volumes:
  n8n_data:
```

Salve: `Ctrl+O`, `Enter`, `Ctrl+X`

### Passo 2: Iniciar n8n

```bash
docker-compose up -d

# Ver logs
docker logs -f n8n
```

### Passo 3: Configurar Nginx para n8n

```bash
nano /etc/nginx/sites-available/n8n
```

Cole:

```nginx
server {
    listen 80;
    server_name n8n.seu-dominio.com;  # Subdomínio para n8n

    location / {
        proxy_pass http://localhost:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts para workflows longos
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
}
```

Ative:

```bash
ln -s /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Passo 4: Configurar SSL

```bash
certbot --nginx -d n8n.seu-dominio.com
```

### Passo 5: Acessar n8n

Acesse: `https://n8n.seu-dominio.com`

Primeira vez:
- Crie usuário e senha
- Configure email (opcional)

## Importar Workflow

### No n8n:

1. Clique em "Workflows" (menu lateral)
2. Clique em "Import from File"
3. Selecione o arquivo `n8n-workflow.json` deste repositório
4. O workflow será importado com todos os nodes

## Configurar Credenciais

### 1. Supabase

No workflow:
1. Clique no node "Salvar no Supabase"
2. Clique em "Create New Credential"
3. Preencha:
   - **Host:** `seu-projeto.supabase.co`
   - **Service Role Secret:** Sua service role key do Supabase
4. Clique em "Save"

Repita para o node "Atualizar Supabase"

### 2. Variáveis de Ambiente (Facebook)

As variáveis já são lidas do `docker-compose.yml`:
- `FACEBOOK_PAGE_ID`
- `FACEBOOK_ACCESS_TOKEN`

Ou configure manualmente:
1. Settings → Variables
2. Adicione:
   - `FACEBOOK_PAGE_ID`
   - `FACEBOOK_ACCESS_TOKEN`

## Ativar Workflow

1. Abra o workflow importado
2. Clique no node "Webhook WhatsApp"
3. Copie a URL do webhook (ex: `https://n8n.seu-dominio.com/webhook/whatsapp-imoveis`)
4. Clique no toggle "Active" no canto superior direito
5. O workflow está ativo!

## Configurar Evolution API

Na Evolution API, configure o webhook para apontar para o n8n:

```bash
# URL do webhook
https://n8n.seu-dominio.com/webhook/whatsapp-imoveis
```

## Como Funciona o Workflow

### Fluxo Completo:

```
Webhook WhatsApp
    ↓
Processar Mensagem (Function)
    ↓
É Imóvel? (IF)
    ↓ SIM
Salvar no Supabase
    ↓
Tem Imagens? (IF)
    ↓ SIM
Preparar para Facebook
    ↓
Baixar Imagem (HTTP Request)
    ↓
Upload Foto Facebook (HTTP Request)
    ↓
Agrupar Fotos (Merge)
    ↓
Agrupar IDs das Fotos (Function)
    ↓
Criar Anúncio Facebook (HTTP Request)
    ↓
Atualizar Supabase
    ↓
Responder Sucesso
```

### Nodes Principais:

1. **Webhook WhatsApp**: Recebe mensagens da Evolution API
2. **Processar Mensagem**: Extrai tipo, preço, descrição usando JavaScript
3. **É Imóvel?**: Verifica se contém keywords de imóveis
4. **Salvar no Supabase**: Insere no banco de dados
5. **Tem Imagens?**: Verifica se tem fotos
6. **Baixar Imagem**: Faz download das imagens do WhatsApp
7. **Upload Foto Facebook**: Envia para Facebook
8. **Criar Anúncio Facebook**: Publica no Marketplace
9. **Atualizar Supabase**: Marca como publicado

## Testar Workflow

### Teste Manual:

1. No n8n, abra o workflow
2. Clique em "Execute Workflow"
3. Clique no node "Webhook WhatsApp"
4. Clique em "Listen for Test Event"
5. Envie uma mensagem de teste no WhatsApp
6. Veja a execução em tempo real no n8n

### Teste via API:

```bash
curl -X POST https://n8n.seu-dominio.com/webhook/whatsapp-imoveis \
  -H "Content-Type: application/json" \
  -d '{
    "from": "5511999999999",
    "messageId": "ABC123",
    "message": {
      "conversation": "Casa para aluguel 3 quartos R$ 1500",
      "imageMessage": {
        "url": "https://example.com/image.jpg"
      }
    }
  }'
```

## Monitorar Execuções

### Ver Execuções:

1. Menu "Executions"
2. Veja todas execuções do workflow
3. Clique em uma para ver detalhes
4. Veja dados de entrada/saída de cada node

### Logs:

```bash
# Logs do Docker
docker logs -f n8n

# Ver workflows ativos
docker exec n8n n8n list:workflow --active=true
```

## Personalizar Workflow

### Adicionar Notificações:

1. Arraste um node "Telegram" ou "Email"
2. Conecte após "Responder Sucesso"
3. Configure para enviar notificação

### Adicionar Mais Validações:

1. Adicione node "IF" após "Processar Mensagem"
2. Adicione condições (ex: preço mínimo, tipo específico)

### Integrar com Outras Plataformas:

n8n tem nodes prontos para:
- OLX
- Telegram
- WhatsApp Business API
- Google Sheets
- Airtable
- Notion
- E mais 400+ integrações

## Vantagens n8n vs Python

| Aspecto | n8n | Python (app.py) |
|---------|-----|-----------------|
| **Interface** | Visual, drag & drop | Código |
| **Modificar** | Clique e edita | Editar arquivo + restart |
| **Debugging** | Ver dados em cada step | Logs no terminal |
| **Integrações** | 400+ nodes prontos | Precisa programar |
| **Monitoramento** | Dashboard visual | journalctl logs |
| **Curva Aprendizado** | Baixa | Média-Alta |
| **Flexibilidade** | Alta (com Function node) | Muito Alta |
| **Performance** | Boa | Excelente |

## Abordagem Híbrida (Recomendada)

Você pode usar os **dois** juntos:

### Cenário 1: n8n para workflows simples
- Receber webhooks
- Processar dados básicos
- Salvar no Supabase
- Notificações

### Cenário 2: Python para lógica complexa
- Processamento avançado de imagens
- IA/ML para classificação
- Validações complexas
- APIs personalizadas

**Comunicação:**
```
WhatsApp → n8n → (webhook) → Python API → n8n → Facebook
```

## Custos

### Self-hosted na VPS:

- VPS Hostinger: R$ 30-60/mês (mesma VPS do Python)
- n8n: Gratuito (open-source)
- Docker: Gratuito
- Supabase: Gratuito (500MB)

**Total: R$ 30-60/mês** (mesmo custo, mas com n8n incluso)

### n8n Cloud:

- Starter: Grátis (5.000 execuções/mês)
- Pro: $20/mês (50.000 execuções)

## Backup n8n

### Exportar Workflows:

1. Settings → Workflows
2. Clique em "Export"
3. Baixe JSON
4. Salve no Git

### Backup Docker Volume:

```bash
# Backup
docker run --rm \
  -v n8n_data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/n8n-backup.tar.gz /data

# Restore
docker run --rm \
  -v n8n_data:/data \
  -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/n8n-backup.tar.gz --strip 1"
```

## Comandos Úteis

```bash
# Parar n8n
docker-compose down

# Reiniciar n8n
docker-compose restart

# Ver logs
docker logs -f n8n

# Atualizar n8n
docker-compose pull
docker-compose up -d

# Backup
docker exec n8n n8n export:workflow --backup --output=/backup/

# Importar workflow via CLI
docker exec n8n n8n import:workflow --input=/workflows/n8n-workflow.json
```

## Troubleshooting

### Webhook não recebe dados

Verifique:
- Workflow está ativo (toggle ON)
- URL do webhook está correta na Evolution API
- Firewall permite porta 5678 ou Nginx está configurado

### Erro ao conectar no Supabase

- Verifique se a credencial do Supabase está correta
- Use a Service Role Key (não a anon key)
- Verifique se a tabela existe

### Imagens não carregam

- Verifique se as URLs das imagens são públicas
- Aumente timeout no node HTTP Request (Settings → Timeout)

### Workflow muito lento

- Reduza o número de imagens processadas
- Use node "Split In Batches" para processar em lotes
- Aumente recursos do Docker (CPU/RAM)

## Recursos Adicionais

- Documentação n8n: https://docs.n8n.io/
- Comunidade: https://community.n8n.io/
- Templates: https://n8n.io/workflows
- YouTube: https://www.youtube.com/@n8n-io

## Suporte

Para dúvidas:
1. Verifique execuções no dashboard n8n
2. Veja logs: `docker logs n8n`
3. Teste cada node individualmente
4. Use node "Sticky Note" para documentar
