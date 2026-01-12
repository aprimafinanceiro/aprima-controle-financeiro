# Guia de Deployment na VPS Hostinger

Este guia mostra como fazer deploy completo do sistema na sua VPS da Hostinger.

## Pré-requisitos

- VPS da Hostinger com Ubuntu/Debian
- Acesso SSH root ou sudo
- Domínio apontando para o IP da VPS (opcional, mas recomendado)

## Passo 1: Conectar na VPS

```bash
ssh root@seu-ip-da-vps
# ou
ssh seu-usuario@seu-ip-da-vps
```

## Passo 2: Atualizar o Sistema

```bash
sudo apt update
sudo apt upgrade -y
```

## Passo 3: Instalar Dependências

```bash
# Python 3 e pip
sudo apt install python3 python3-pip python3-venv -y

# Git
sudo apt install git -y

# Nginx (servidor web)
sudo apt install nginx -y

# Supervisor ou systemd (já vem instalado no Ubuntu)
sudo apt install supervisor -y
```

## Passo 4: Criar Usuário para a Aplicação

```bash
# Criar usuário dedicado (mais seguro)
sudo adduser --system --group --home /home/aprimabot aprimabot
```

## Passo 5: Clonar o Repositório

```bash
# Mudar para o usuário da aplicação
sudo su - aprimabot

# Clonar o repositório
cd /home/aprimabot
git clone https://github.com/aprimafinanceiro/aprima-controle-financeiro.git
cd aprima-controle-financeiro
```

## Passo 6: Criar Ambiente Virtual Python

```bash
# Ainda como usuário aprimabot
python3 -m venv venv
source venv/bin/activate
```

## Passo 7: Instalar Dependências Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn  # Servidor WSGI para produção
```

## Passo 8: Configurar Variáveis de Ambiente

```bash
# Criar arquivo .env
nano .env
```

Cole as configurações:
```bash
# Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-anon-key-aqui

# Facebook
FACEBOOK_PAGE_ID=sua-page-id
FACEBOOK_ACCESS_TOKEN=seu-token

# Evolution API
EVOLUTION_API_URL=https://sua-evolution-api.com
EVOLUTION_API_KEY=sua-chave
```

Salve com `Ctrl+O`, `Enter`, `Ctrl+X`

## Passo 9: Testar a Aplicação

```bash
# Testar se funciona
source venv/bin/activate
python app.py
```

Se aparecer "Running on http://0.0.0.0:5000", está funcionando! Pressione `Ctrl+C` para parar.

Volte para o usuário root:
```bash
exit
```

## Passo 10: Configurar Systemd (Processo em Background)

```bash
# Como root
sudo nano /etc/systemd/system/aprima-imoveis.service
```

Cole o conteúdo do arquivo `aprima-imoveis.service` (veja o arquivo neste repositório).

Depois:
```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Iniciar o serviço
sudo systemctl start aprima-imoveis

# Verificar status
sudo systemctl status aprima-imoveis

# Habilitar para iniciar automaticamente no boot
sudo systemctl enable aprima-imoveis
```

## Passo 11: Configurar Nginx (Reverse Proxy)

```bash
sudo nano /etc/nginx/sites-available/aprima-imoveis
```

Cole o conteúdo do arquivo `nginx.conf` (veja o arquivo neste repositório).

**Importante:** Substitua `seu-dominio.com` pelo seu domínio real.

Depois:
```bash
# Criar link simbólico
sudo ln -s /etc/nginx/sites-available/aprima-imoveis /etc/nginx/sites-enabled/

# Testar configuração
sudo nginx -t

# Recarregar Nginx
sudo systemctl reload nginx
```

## Passo 12: Configurar Firewall

```bash
# Permitir HTTP e HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH (importante!)

# Habilitar firewall
sudo ufw enable
```

## Passo 13: Configurar SSL/HTTPS (Opcional mas Recomendado)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obter certificado SSL gratuito
sudo certbot --nginx -d seu-dominio.com

# Renovação automática já está configurada!
```

## Verificar se está Funcionando

```bash
# Ver logs em tempo real
sudo journalctl -u aprima-imoveis -f

# Ou se estiver usando supervisor
sudo tail -f /var/log/aprima-imoveis/*.log
```

Acesse no navegador: `http://seu-dominio.com` ou `http://seu-ip-da-vps`

Deve aparecer: "🏠 WhatsApp → Facebook Marketplace Integration está online!"

## Comandos Úteis

```bash
# Parar o serviço
sudo systemctl stop aprima-imoveis

# Reiniciar o serviço
sudo systemctl restart aprima-imoveis

# Ver status
sudo systemctl status aprima-imoveis

# Ver logs
sudo journalctl -u aprima-imoveis -n 100

# Ver logs em tempo real
sudo journalctl -u aprima-imoveis -f

# Atualizar código
sudo su - aprimabot
cd /home/aprimabot/aprima-controle-financeiro
git pull
source venv/bin/activate
pip install -r requirements.txt
exit
sudo systemctl restart aprima-imoveis
```

## Troubleshooting

### Serviço não inicia

```bash
# Ver erro detalhado
sudo journalctl -u aprima-imoveis -n 50

# Verificar se as variáveis de ambiente estão corretas
sudo cat /home/aprimabot/aprima-controle-financeiro/.env
```

### Nginx retorna 502 Bad Gateway

```bash
# Verificar se o serviço está rodando
sudo systemctl status aprima-imoveis

# Ver logs do Nginx
sudo tail -f /var/log/nginx/error.log
```

### Porta já em uso

```bash
# Ver o que está usando a porta 5000
sudo lsof -i :5000

# Matar processo se necessário
sudo kill -9 <PID>
```

### Atualizar o código

```bash
cd /home/aprimabot/aprima-controle-financeiro
sudo -u aprimabot git pull
sudo systemctl restart aprima-imoveis
```

## Monitoramento

### Ver uso de recursos

```bash
# CPU e memória
htop

# Espaço em disco
df -h

# Processos Python
ps aux | grep python
```

### Logs

```bash
# Logs da aplicação
sudo journalctl -u aprima-imoveis --since "1 hour ago"

# Logs do Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Backup

```bash
# Backup do código e configurações
sudo tar -czf backup-aprima-$(date +%Y%m%d).tar.gz \
  /home/aprimabot/aprima-controle-financeiro \
  /etc/nginx/sites-available/aprima-imoveis \
  /etc/systemd/system/aprima-imoveis.service

# Dados do Supabase já têm backup automático
```

## Configurar Domínio

Se você tem um domínio (ex: imoveis.suaempresa.com):

1. No painel DNS do seu domínio (Registro.br, GoDaddy, etc):
   - Tipo: A
   - Nome: @ (ou imoveis)
   - Valor: IP-DA-SUA-VPS
   - TTL: 3600

2. Aguarde propagação DNS (5-30 minutos)

3. Configure SSL:
```bash
sudo certbot --nginx -d imoveis.suaempresa.com
```

## Otimizações

### Aumentar workers do Gunicorn

Edite o arquivo `/etc/systemd/system/aprima-imoveis.service`:
```
--workers 4  # Para 4 cores de CPU
```

### Adicionar compressão no Nginx

No arquivo `/etc/nginx/sites-available/aprima-imoveis`, adicione:
```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

### Rate limiting (proteção contra abuso)

No arquivo Nginx:
```nginx
limit_req_zone $binary_remote_addr zone=webhook:10m rate=10r/s;

location /webhook {
    limit_req zone=webhook burst=20;
    ...
}
```

## Segurança

1. **Firewall configurado** ✓
2. **SSL/HTTPS** ✓
3. **Usuário dedicado** ✓
4. **Variáveis de ambiente seguras** ✓
5. **Atualizar regularmente:**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## Custo Estimado

- **VPS Hostinger:** R$ 30-60/mês (dependendo do plano)
- **Supabase:** Grátis (até 500MB)
- **Domínio:** R$ 40/ano (opcional)
- **SSL:** Grátis (Let's Encrypt)

**Total:** ~R$ 30-60/mês

## Suporte

Se tiver problemas:
1. Verifique os logs: `sudo journalctl -u aprima-imoveis -f`
2. Verifique o Nginx: `sudo nginx -t`
3. Teste conexão Supabase no dashboard
4. Verifique firewall: `sudo ufw status`
