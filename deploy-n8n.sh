#!/bin/bash

# Script de Deploy n8n na VPS
# Execute como root: sudo bash deploy-n8n.sh

set -e

echo "=================================================="
echo "  Deploy n8n - Automação Visual"
echo "=================================================="
echo ""

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Por favor, execute como root: sudo bash deploy-n8n.sh"
    exit 1
fi

echo "✓ Executando como root"

# Solicitar informações
echo ""
read -p "Digite seu domínio para n8n (ex: n8n.seudominio.com): " N8N_DOMAIN
read -p "Digite FACEBOOK_PAGE_ID: " FACEBOOK_PAGE_ID
read -p "Digite FACEBOOK_ACCESS_TOKEN: " FACEBOOK_ACCESS_TOKEN
read -p "Digite SUPABASE_URL: " SUPABASE_URL
read -p "Digite SUPABASE_KEY: " SUPABASE_KEY

echo ""
echo "📦 Passo 1: Instalando Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo "✓ Docker instalado"
else
    echo "✓ Docker já instalado"
fi

echo ""
echo "📦 Passo 2: Instalando Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✓ Docker Compose instalado"
else
    echo "✓ Docker Compose já instalado"
fi

echo ""
echo "📁 Passo 3: Criando diretório n8n..."
mkdir -p /opt/n8n/workflows
cd /opt/n8n

echo ""
echo "⚙️  Passo 4: Criando docker-compose.yml..."
cat > docker-compose.yml <<EOF
version: '3.8'

services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_HOST=${N8N_DOMAIN}
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - NODE_ENV=production
      - WEBHOOK_URL=https://${N8N_DOMAIN}/
      - GENERIC_TIMEZONE=America/Sao_Paulo
      - N8N_METRICS=true

      # Credenciais do projeto
      - FACEBOOK_PAGE_ID=${FACEBOOK_PAGE_ID}
      - FACEBOOK_ACCESS_TOKEN=${FACEBOOK_ACCESS_TOKEN}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}

    volumes:
      - n8n_data:/home/node/.n8n
      - ./workflows:/home/node/.n8n/workflows

volumes:
  n8n_data:
    driver: local
EOF

echo "✓ docker-compose.yml criado"

echo ""
echo "🚀 Passo 5: Iniciando n8n..."
docker-compose up -d

# Aguardar n8n iniciar
echo "Aguardando n8n iniciar..."
sleep 10

if docker ps | grep -q n8n; then
    echo "✅ n8n iniciado com sucesso!"
else
    echo "❌ Erro ao iniciar n8n"
    docker logs n8n
    exit 1
fi

echo ""
echo "🌐 Passo 6: Configurando Nginx..."

# Instalar Nginx se não estiver instalado
if ! command -v nginx &> /dev/null; then
    apt install -y nginx
fi

cat > /etc/nginx/sites-available/n8n <<EOF
server {
    listen 80;
    server_name ${N8N_DOMAIN};

    client_max_body_size 50M;

    location / {
        proxy_pass http://localhost:5678;
        proxy_http_version 1.1;

        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_cache_bypass \$http_upgrade;

        # Timeouts para workflows longos
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
}
EOF

ln -sf /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/

nginx -t
systemctl reload nginx

echo "✓ Nginx configurado"

echo ""
echo "🔥 Passo 7: Configurando Firewall..."
ufw allow 80/tcp 2>/dev/null || true
ufw allow 443/tcp 2>/dev/null || true
echo "✓ Firewall configurado"

echo ""
read -p "Deseja configurar SSL com Let's Encrypt? (s/n): " SETUP_SSL

if [ "$SETUP_SSL" = "s" ]; then
    echo ""
    echo "🔒 Passo 8: Configurando SSL..."

    if ! command -v certbot &> /dev/null; then
        apt install -y certbot python3-certbot-nginx
    fi

    certbot --nginx -d ${N8N_DOMAIN} --non-interactive --agree-tos --register-unsafely-without-email || {
        echo "⚠️  Erro ao configurar SSL. Configure manualmente depois:"
        echo "   sudo certbot --nginx -d ${N8N_DOMAIN}"
    }
fi

echo ""
echo "📥 Passo 9: Baixando workflow..."
curl -o /opt/n8n/workflows/n8n-workflow.json \
  https://raw.githubusercontent.com/aprimafinanceiro/aprima-controle-financeiro/main/n8n-workflow.json || {
    echo "⚠️  Não foi possível baixar o workflow automaticamente"
    echo "   Você pode importar manualmente pelo dashboard do n8n"
}

echo ""
echo "=================================================="
echo "  ✅ n8n INSTALADO COM SUCESSO!"
echo "=================================================="
echo ""
echo "🌐 Acesse o n8n:"
if [ "$SETUP_SSL" = "s" ]; then
    echo "   https://${N8N_DOMAIN}"
else
    echo "   http://${N8N_DOMAIN}"
fi
echo ""
echo "📋 Primeiros passos:"
echo "   1. Acesse a URL acima"
echo "   2. Crie seu usuário e senha (primeira vez)"
echo "   3. Vá em Workflows → Import from File"
echo "   4. Importe: /opt/n8n/workflows/n8n-workflow.json"
echo "   5. Configure credenciais do Supabase"
echo "   6. Ative o workflow (toggle ON)"
echo "   7. Copie a URL do webhook"
echo "   8. Configure na Evolution API"
echo ""
echo "📝 Comandos úteis:"
echo "   Ver logs:        docker logs -f n8n"
echo "   Reiniciar:       docker-compose -f /opt/n8n/docker-compose.yml restart"
echo "   Parar:           docker-compose -f /opt/n8n/docker-compose.yml down"
echo "   Iniciar:         docker-compose -f /opt/n8n/docker-compose.yml up -d"
echo "   Atualizar:       docker-compose -f /opt/n8n/docker-compose.yml pull && docker-compose -f /opt/n8n/docker-compose.yml up -d"
echo ""
echo "📖 Documentação completa: N8N_SETUP.md"
echo "=================================================="
