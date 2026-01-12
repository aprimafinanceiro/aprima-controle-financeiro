# WhatsApp → Facebook Marketplace - Integração para Imobiliárias

Sistema automatizado que monitora mensagens de um grupo do WhatsApp, identifica anúncios de imóveis (com fotos e descrições) e publica automaticamente no Facebook Marketplace usando Supabase como banco de dados.

## Escolha Sua Abordagem

Este projeto oferece **duas formas** de implementação:

### 1️⃣ Python (app.py) - Código Tradicional
- ✅ Código Python Flask
- ✅ Mais controle e flexibilidade
- ✅ Performance otimizada
- 📖 Deploy: Veja seção "Instalação" abaixo

### 2️⃣ n8n - Automação Visual (Recomendado para iniciantes)
- ✅ Interface visual (arrastar e soltar)
- ✅ Fácil de modificar sem código
- ✅ 400+ integrações prontas
- ✅ Self-hosted ou cloud
- 📖 Setup: Leia [N8N_SETUP.md](N8N_SETUP.md)
- 🚀 Deploy rápido: `bash deploy-n8n.sh`

**💡 Escolha n8n se:** você prefere interface visual e quer modificar facilmente
**💡 Escolha Python se:** você precisa de performance máxima e controle total

---

## Funcionalidades

- Recebe mensagens via webhook da Evolution API (WhatsApp)
- Detecta automaticamente mensagens sobre imóveis usando keywords
- Extrai informações importantes: tipo de imóvel, preço, descrição
- Faz download de imagens enviadas no WhatsApp
- Publica automaticamente no Facebook Marketplace
- Armazena histórico em banco de dados Supabase (PostgreSQL)
- API REST para consultar imóveis cadastrados

## Requisitos

### 1. Supabase (Banco de Dados)

Supabase é uma alternativa open-source ao Firebase usando PostgreSQL:

1. Acesse: https://supabase.com/
2. Crie uma conta e um novo projeto
3. Aguarde a criação do banco de dados
4. Vá em "Project Settings" → "API"
5. Copie:
   - **Project URL** (SUPABASE_URL)
   - **anon/public key** (SUPABASE_KEY)
6. Vá em "SQL Editor" e execute o script `setup_supabase.sql` deste repositório

### 2. Evolution API (WhatsApp)

Você precisa de uma instância da Evolution API configurada:
- Site: https://evolution-api.com/
- Configure uma instância com seu número de WhatsApp Business
- Anote a URL da API e a chave de acesso

### 3. Facebook Developer Account

Para publicar no Facebook Marketplace, você precisa:
- Uma Página no Facebook
- Acesso à Graph API do Facebook
- Um Access Token com permissões de Marketplace

#### Como obter o Access Token do Facebook:

1. Acesse: https://developers.facebook.com/
2. Crie um App (tipo "Business")
3. Adicione o produto "Marketing API"
4. Vá em "Tools" → "Graph API Explorer"
5. Selecione sua página
6. Adicione as permissões:
   - `pages_manage_metadata`
   - `pages_read_engagement`
   - `pages_show_list`
   - `commerce_manage_catalog`
7. Gere o token de longa duração
8. Copie o Page ID da sua página

## Instalação

### Local

```bash
# Clone o repositório
git clone <seu-repositorio>
cd aprima-controle-financeiro

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
export SUPABASE_URL="https://seu-projeto.supabase.co"
export SUPABASE_KEY="sua-anon-key"
export FACEBOOK_PAGE_ID="sua-page-id"
export FACEBOOK_ACCESS_TOKEN="seu-token"
export EVOLUTION_API_URL="https://sua-evolution-api.com"
export EVOLUTION_API_KEY="sua-chave"

# Execute o servidor
python app.py
```

### Deploy (Render.com)

O projeto já está configurado para deploy no Render.com:

1. Faça push do código para o GitHub
2. Conecte seu repositório no Render.com
3. Configure as variáveis de ambiente no painel do Render:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `FACEBOOK_PAGE_ID`
   - `FACEBOOK_ACCESS_TOKEN`
   - `EVOLUTION_API_URL`
   - `EVOLUTION_API_KEY`
4. O Render detectará automaticamente o `render.yaml`

### Deploy em VPS (Hostinger, DigitalOcean, etc)

**Opção 1: Deploy Automatizado (Recomendado)**

```bash
# Conecte na VPS via SSH
ssh root@seu-ip-da-vps

# Baixe e execute o script de deploy
curl -O https://raw.githubusercontent.com/aprimafinanceiro/aprima-controle-financeiro/main/deploy.sh
sudo bash deploy.sh
```

O script fará tudo automaticamente:
- Instalar dependências (Python, Nginx, etc)
- Criar usuário da aplicação
- Clonar repositório
- Configurar ambiente virtual
- Configurar systemd (processo em background)
- Configurar Nginx (servidor web)
- Configurar firewall
- Opcionalmente configurar SSL/HTTPS

**Opção 2: Deploy Manual**

Consulte o guia completo: [DEPLOY_VPS.md](DEPLOY_VPS.md)

**Após o deploy:**

1. Edite as variáveis de ambiente:
```bash
sudo nano /home/aprimabot/aprima-controle-financeiro/.env
```

2. Reinicie o serviço:
```bash
sudo systemctl restart aprima-imoveis
```

3. Acesse: `http://seu-ip-ou-dominio`

**Comandos úteis VPS:**
```bash
# Ver logs em tempo real
sudo journalctl -u aprima-imoveis -f

# Reiniciar serviço
sudo systemctl restart aprima-imoveis

# Ver status
sudo systemctl status aprima-imoveis
```

## Configuração do Banco de Dados

### Setup do Supabase

1. Acesse seu projeto no Supabase
2. Vá em "SQL Editor"
3. Crie uma nova query
4. Copie e cole o conteúdo do arquivo `setup_supabase.sql`
5. Execute o script (Run)

Este script criará:
- Tabela `imoveis` com todos os campos necessários
- Índices para melhorar performance
- Triggers para atualizar `updated_at` automaticamente
- Políticas de segurança (Row Level Security)

### Estrutura da Tabela

```sql
CREATE TABLE imoveis (
    id BIGSERIAL PRIMARY KEY,
    whatsapp_message_id TEXT,
    whatsapp_from TEXT,
    titulo TEXT NOT NULL,
    descricao TEXT,
    preco TEXT,
    tipo_imovel TEXT,
    imagens_urls JSONB,
    facebook_listing_id TEXT,
    status TEXT DEFAULT 'pendente',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Configuração do Webhook

### Na Evolution API:

Configure o webhook para apontar para seu servidor:

```json
{
  "webhook": "https://seu-servidor.com/webhook",
  "events": ["messages.upsert"]
}
```

### Formato esperado do webhook:

```json
{
  "from": "5511999999999@s.whatsapp.net",
  "messageId": "ABC123",
  "message": {
    "conversation": "Casa para aluguel 3 quartos R$ 1500",
    "imageMessage": {
      "url": "https://url-da-imagem.jpg"
    }
  }
}
```

## Como Funciona

### 1. Detecção Automática de Imóveis

O sistema detecta mensagens sobre imóveis procurando por palavras-chave:
- Tipo: casa, apartamento, kitnet, terreno, comercial
- Transação: aluguel, venda, locação
- Características: quartos, banheiro, suite, vaga, garagem, m²
- Preço: R$, reais, valor

### 2. Extração de Informações

Quando uma mensagem é detectada como sendo sobre imóvel:
- Extrai o tipo do imóvel (casa, apartamento, etc)
- Identifica se é venda ou aluguel
- Captura o preço usando regex
- Gera um título automático
- Armazena as URLs das imagens

### 3. Publicação no Facebook

Se as credenciais do Facebook estiverem configuradas:
- Faz upload de cada imagem para o Facebook
- Cria o anúncio no Marketplace com:
  - Título gerado automaticamente
  - Descrição completa
  - Preço em BRL
  - Categoria (venda ou aluguel)
  - Todas as imagens

### 4. Armazenamento

Todos os imóveis são salvos no Supabase (PostgreSQL):
- ID do WhatsApp
- Número do remetente
- Título e descrição
- URLs das imagens (JSON)
- ID do anúncio no Facebook
- Status (pendente/publicado)
- Data de cadastro e atualização

## API Endpoints

### GET /

Health check do servidor

```bash
curl https://seu-servidor.com/
```

Resposta: "🏠 WhatsApp → Facebook Marketplace Integration está online!"

### POST /webhook

Recebe mensagens da Evolution API (configurado automaticamente)

### GET /imoveis

Lista os últimos 50 imóveis cadastrados

```bash
curl https://seu-servidor.com/imoveis
```

Resposta:
```json
[
  {
    "id": 1,
    "titulo": "Casa para aluguel - R$ 1500",
    "preco": "1500",
    "tipo": "casa",
    "status": "publicado",
    "facebook_listing_id": "123456789",
    "data_cadastro": "2026-01-12T10:30:00Z"
  }
]
```

### GET /imoveis/{id}

Detalhes completos de um imóvel específico

```bash
curl https://seu-servidor.com/imoveis/1
```

Resposta:
```json
{
  "id": 1,
  "whatsapp_message_id": "ABC123",
  "whatsapp_from": "5511999999999",
  "titulo": "Casa para aluguel - R$ 1500",
  "descricao": "Casa para aluguel 3 quartos R$ 1500...",
  "preco": "1500",
  "tipo": "casa",
  "imagens_urls": ["https://url1.jpg", "https://url2.jpg"],
  "facebook_listing_id": "123456789",
  "data_cadastro": "2026-01-12T10:30:00Z",
  "status": "publicado"
}
```

## Exemplos de Mensagens que Funcionam

### Exemplo 1: Casa para Aluguel
```
Casa para aluguel
3 quartos, 2 banheiros
Garagem para 2 carros
R$ 1.500/mês
```

### Exemplo 2: Apartamento à Venda
```
Apartamento à venda
2 quartos, 1 suíte
60m², 1 vaga
R$ 250.000
```

### Exemplo 3: Kitnet
```
Kitnet para alugar
R$ 800
Próximo ao metrô
```

## Estrutura do Projeto

```
aprima-controle-financeiro/
├── app.py                    # Aplicação Flask principal (Python)
├── requirements.txt          # Dependências Python
├── setup_supabase.sql        # Script SQL para criar tabelas no Supabase
├── render.yaml              # Configuração de deployment (Render.com)
├── .env.example             # Template de variáveis de ambiente
├── .gitignore               # Arquivos ignorados pelo Git
│
├── deploy.sh                # Script deploy automatizado Python (VPS)
├── deploy-n8n.sh            # Script deploy automatizado n8n (VPS)
├── aprima-imoveis.service   # Configuração systemd (Python)
├── nginx.conf               # Configuração Nginx (Python)
│
├── n8n-workflow.json        # Workflow n8n (importar no n8n)
├── N8N_SETUP.md             # Guia completo setup n8n
├── DEPLOY_VPS.md            # Guia deploy manual VPS
└── README.md                # Esta documentação
```

## Classes Principais

### FacebookMarketplaceIntegration

Gerencia a comunicação com a API do Facebook:
- `upload_image(image_url)`: Faz upload de uma imagem
- `create_listing(property_data)`: Cria um anúncio no Marketplace

### WhatsAppPropertyProcessor

Processa mensagens e extrai informações de imóveis:
- `is_property_message(message)`: Detecta se é mensagem sobre imóvel
- `extract_price(text)`: Extrai o preço usando regex
- `extract_property_type(text)`: Identifica o tipo de imóvel
- `extract_transaction_type(text)`: Identifica venda ou aluguel
- `create_title(text)`: Gera título automático
- `process_message(data)`: Processa mensagem completa

## Troubleshooting

### Erro ao conectar ao Supabase

Verifique se:
- URL do Supabase está correta (https://seu-projeto.supabase.co)
- Chave anon/public está correta
- O script `setup_supabase.sql` foi executado
- As políticas RLS permitem acesso

### Imóveis não estão sendo detectados

Verifique se a mensagem contém palavras-chave como:
- casa, apartamento, aluguel, venda, R$, quartos, etc

### Imagens não aparecem no Facebook

Certifique-se de que:
- As URLs das imagens são públicas e acessíveis
- O Facebook consegue baixar as imagens
- As credenciais do Facebook estão corretas

### Erro ao publicar no Facebook

Possíveis causas:
- Access Token expirado (gere um novo)
- Página do Facebook sem permissões de Marketplace
- Falta de permissões na API do Facebook

### Webhook não recebe mensagens

Verifique:
- URL do webhook configurada corretamente na Evolution API
- Servidor está acessível publicamente (não localhost)
- Evolution API está conectada ao WhatsApp

## Vantagens do Supabase

- **PostgreSQL**: Banco de dados robusto e escalável
- **Gratuito**: 500MB de database + 1GB de storage grátis
- **Real-time**: Suporte a subscriptions em tempo real
- **Dashboard**: Interface visual para gerenciar dados
- **Backups**: Backup automático dos dados
- **Segurança**: Row Level Security (RLS) integrado
- **API REST**: API REST gerada automaticamente
- **Webhooks**: Suporte a webhooks para eventos do banco

## Limitações

- As imagens precisam estar acessíveis via URL pública
- Preços devem estar no formato: "R$ 1.500" ou similar
- Descrições são limitadas a 500 caracteres
- Facebook Marketplace pode ter restrições por região

## Próximas Melhorias

- [ ] Suporte a múltiplas imagens por anúncio
- [ ] Integração com IA para melhor extração de dados
- [ ] Painel web para gerenciar imóveis (usando Supabase Auth)
- [ ] Edição de anúncios já publicados
- [ ] Notificações de sucesso/erro no WhatsApp
- [ ] Suporte a vídeos
- [ ] Integração com outros marketplaces (OLX, ZAP, etc)
- [ ] Analytics e relatórios via Supabase

## Monitoramento

### Via Supabase Dashboard

1. Acesse seu projeto no Supabase
2. Vá em "Table Editor" → "imoveis"
3. Visualize todos os imóveis cadastrados
4. Filtre por status, data, tipo, etc
5. Edite ou delete registros manualmente

### Logs da Aplicação

O sistema imprime logs detalhados:
- ✅ Sucesso em operações
- ❌ Erros e falhas
- ℹ️ Informações gerais
- 📩 Mensagens recebidas
- 🏠 Imóveis detectados
- 💾 Salvamento no banco
- 📤 Publicação no Facebook

## Suporte

Para dúvidas ou problemas:
1. Verifique os logs do servidor
2. Consulte o dashboard do Supabase
3. Teste os endpoints manualmente
4. Valide as credenciais do Facebook
5. Confira a configuração do webhook

## Licença

MIT License

## Autor

Sistema desenvolvido para automação de anúncios de imóveis usando Supabase, WhatsApp e Facebook Marketplace.
