#!/bin/bash

# Script de Deploy Automatizado para VPS
# Execute como root: sudo bash deploy.sh

set -e  # Parar em caso de erro

echo "=================================================="
echo "  Deploy Aprima Imoveis - WhatsApp to Facebook"
echo "=================================================="
echo ""

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Por favor, execute como root: sudo bash deploy.sh"
    exit 1
fi

echo "✓ Executando como root"

# Variáveis
APP_USER="aprimabot"
APP_DIR="/home/$APP_USER/aprima-controle-financeiro"
REPO_URL="https://github.com/aprimafinanceiro/aprima-controle-financeiro.git"
SERVICE_NAME="aprima-imoveis"

echo ""
echo "📦 Passo 1: Atualizando sistema..."
apt update -qq
apt upgrade -y -qq

echo ""
echo "📦 Passo 2: Instalando dependências..."
apt install -y -qq python3 python3-pip python3-venv git nginx supervisor

echo ""
echo "👤 Passo 3: Criando usuário da aplicação..."
if id "$APP_USER" &>/dev/null; then
    echo "✓ Usuário $APP_USER já existe"
else
    adduser --system --group --home /home/$APP_USER $APP_USER
    echo "✓ Usuário $APP_USER criado"
fi

echo ""
echo "📥 Passo 4: Clonando/Atualizando repositório..."
if [ -d "$APP_DIR" ]; then
    echo "Atualizando repositório existente..."
    cd $APP_DIR
    sudo -u $APP_USER git pull
else
    echo "Clonando repositório..."
    sudo -u $APP_USER git clone $REPO_URL $APP_DIR
    cd $APP_DIR
fi

echo ""
echo "🐍 Passo 5: Configurando ambiente Python..."
if [ ! -d "$APP_DIR/venv" ]; then
    sudo -u $APP_USER python3 -m venv venv
    echo "✓ Ambiente virtual criado"
else
    echo "✓ Ambiente virtual já existe"
fi

sudo -u $APP_USER $APP_DIR/venv/bin/pip install --upgrade pip -q
sudo -u $APP_USER $APP_DIR/venv/bin/pip install -r requirements.txt -q
sudo -u $APP_USER $APP_DIR/venv/bin/pip install gunicorn -q
echo "✓ Dependências instaladas"

echo ""
echo "⚙️  Passo 6: Configurando variáveis de ambiente..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo "❗ Arquivo .env não encontrado!"
    echo "Criando .env de exemplo..."
    cp $APP_DIR/.env.example $APP_DIR/.env
    chown $APP_USER:$APP_USER $APP_DIR/.env
    echo ""
    echo "⚠️  IMPORTANTE: Edite o arquivo .env com suas credenciais:"
    echo "   nano $APP_DIR/.env"
    echo ""
    read -p "Pressione ENTER após configurar o .env, ou Ctrl+C para sair e configurar depois..."
else
    echo "✓ Arquivo .env encontrado"
fi

echo ""
echo "📁 Passo 7: Criando diretórios de log..."
mkdir -p /var/log/$SERVICE_NAME
chown $APP_USER:$APP_USER /var/log/$SERVICE_NAME
echo "✓ Diretórios criados"

echo ""
echo "🔧 Passo 8: Configurando systemd..."
cp $APP_DIR/$SERVICE_NAME.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable $SERVICE_NAME
echo "✓ Serviço systemd configurado"

echo ""
echo "🌐 Passo 9: Configurando Nginx..."
if [ ! -f "/etc/nginx/sites-available/$SERVICE_NAME" ]; then
    cp $APP_DIR/nginx.conf /etc/nginx/sites-available/$SERVICE_NAME

    echo ""
    read -p "Digite seu domínio (ou pressione ENTER para usar IP): " DOMAIN

    if [ -z "$DOMAIN" ]; then
        # Usar IP
        SERVER_IP=$(hostname -I | awk '{print $1}')
        sed -i "s/server_name seu-dominio.com;/server_name $SERVER_IP;/" /etc/nginx/sites-available/$SERVICE_NAME
        echo "✓ Configurado para usar IP: $SERVER_IP"
    else
        # Usar domínio
        sed -i "s/seu-dominio.com/$DOMAIN/g" /etc/nginx/sites-available/$SERVICE_NAME
        echo "✓ Configurado para usar domínio: $DOMAIN"

        echo ""
        read -p "Deseja configurar SSL com Let's Encrypt? (s/n): " SETUP_SSL
    fi

    ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default  # Remove site padrão

    nginx -t
    systemctl reload nginx
    echo "✓ Nginx configurado e recarregado"
else
    echo "✓ Nginx já configurado"
fi

echo ""
echo "🔥 Passo 10: Configurando Firewall..."
ufw allow 22/tcp  # SSH
ufw allow 80/tcp  # HTTP
ufw allow 443/tcp # HTTPS
echo "y" | ufw enable 2>/dev/null || true
echo "✓ Firewall configurado"

echo ""
echo "🚀 Passo 11: Iniciando serviço..."
systemctl restart $SERVICE_NAME
sleep 2

if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Serviço iniciado com sucesso!"
else
    echo "❌ Erro ao iniciar serviço. Verificando logs..."
    journalctl -u $SERVICE_NAME -n 20 --no-pager
    exit 1
fi

echo ""
echo "🔍 Testando aplicação..."
sleep 1
RESPONSE=$(curl -s http://localhost:5000/ || echo "ERRO")
if [[ $RESPONSE == *"online"* ]]; then
    echo "✅ Aplicação respondendo corretamente!"
else
    echo "⚠️  Aplicação pode não estar respondendo. Verifique os logs."
fi

# Configurar SSL se solicitado
if [ ! -z "$DOMAIN" ] && [ "$SETUP_SSL" = "s" ]; then
    echo ""
    echo "🔒 Configurando SSL com Let's Encrypt..."
    apt install -y certbot python3-certbot-nginx
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email || true
fi

echo ""
echo "=================================================="
echo "  ✅ DEPLOY CONCLUÍDO COM SUCESSO!"
echo "=================================================="
echo ""
echo "📊 Status do serviço:"
systemctl status $SERVICE_NAME --no-pager -l
echo ""
echo "🌐 Acesse:"
if [ -z "$DOMAIN" ]; then
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo "   http://$SERVER_IP"
else
    if [ "$SETUP_SSL" = "s" ]; then
        echo "   https://$DOMAIN"
    else
        echo "   http://$DOMAIN"
    fi
fi
echo ""
echo "📝 Comandos úteis:"
echo "   Ver logs:      sudo journalctl -u $SERVICE_NAME -f"
echo "   Reiniciar:     sudo systemctl restart $SERVICE_NAME"
echo "   Parar:         sudo systemctl stop $SERVICE_NAME"
echo "   Status:        sudo systemctl status $SERVICE_NAME"
echo ""
echo "⚙️  Configuração:"
echo "   Editar .env:   sudo nano $APP_DIR/.env"
echo "   Após editar:   sudo systemctl restart $SERVICE_NAME"
echo ""
echo "=================================================="
