from flask import Flask, request, jsonify
import os
import json
import requests
import re
from datetime import datetime
import sqlite3

app = Flask(__name__)

# Configurações do Facebook
FACEBOOK_PAGE_ID = os.environ.get('FACEBOOK_PAGE_ID', '')
FACEBOOK_ACCESS_TOKEN = os.environ.get('FACEBOOK_ACCESS_TOKEN', '')

# Configurações da Evolution API
EVOLUTION_API_URL = os.environ.get('EVOLUTION_API_URL', '')
EVOLUTION_API_KEY = os.environ.get('EVOLUTION_API_KEY', '')

# Database setup
def init_db():
    conn = sqlite3.connect('imoveis.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS imoveis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whatsapp_message_id TEXT,
            whatsapp_from TEXT,
            titulo TEXT,
            descricao TEXT,
            preco TEXT,
            tipo_imovel TEXT,
            imagens_urls TEXT,
            facebook_listing_id TEXT,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pendente'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class FacebookMarketplaceIntegration:
    """Classe para gerenciar integração com Facebook Marketplace"""

    def __init__(self, page_id, access_token):
        self.page_id = page_id
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v18.0"

    def upload_image(self, image_url):
        """Faz upload de uma imagem para o Facebook"""
        try:
            # Baixa a imagem primeiro
            img_response = requests.get(image_url)
            if img_response.status_code != 200:
                print(f"❌ Erro ao baixar imagem: {image_url}")
                return None

            # Upload para Facebook
            files = {
                'file': ('image.jpg', img_response.content, 'image/jpeg')
            }
            data = {
                'access_token': self.access_token
            }

            url = f"{self.base_url}/{self.page_id}/photos"
            response = requests.post(url, files=files, data=data)

            if response.status_code == 200:
                photo_id = response.json().get('id')
                print(f"✅ Imagem enviada: {photo_id}")
                return photo_id
            else:
                print(f"❌ Erro ao enviar imagem: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Erro no upload de imagem: {str(e)}")
            return None

    def create_listing(self, property_data):
        """Cria um anúncio no Facebook Marketplace"""
        try:
            # Upload das imagens
            photo_ids = []
            for img_url in property_data.get('images', []):
                photo_id = self.upload_image(img_url)
                if photo_id:
                    photo_ids.append(photo_id)

            if not photo_ids:
                print("❌ Nenhuma imagem foi enviada com sucesso")
                return None

            # Monta o payload do anúncio
            listing_data = {
                'access_token': self.access_token,
                'name': property_data.get('titulo', 'Imóvel'),
                'description': property_data.get('descricao', ''),
                'price': property_data.get('preco', '0'),
                'currency': 'BRL',
                'availability': 'AVAILABLE',
                'condition': 'NEW',
                'category': 'property_for_rent' if 'aluguel' in property_data.get('tipo', '').lower() else 'property_for_sale',
            }

            # Adiciona as imagens
            if photo_ids:
                listing_data['images'] = json.dumps([{'id': pid} for pid in photo_ids])

            # Cria o anúncio
            url = f"{self.base_url}/{self.page_id}/marketplace_listings"
            response = requests.post(url, data=listing_data)

            if response.status_code == 200:
                listing_id = response.json().get('id')
                print(f"✅ Anúncio criado no Facebook: {listing_id}")
                return listing_id
            else:
                print(f"❌ Erro ao criar anúncio: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Erro ao criar listing: {str(e)}")
            return None


class WhatsAppPropertyProcessor:
    """Processa mensagens do WhatsApp e extrai informações de imóveis"""

    def __init__(self):
        self.keywords_imovel = [
            'casa', 'apartamento', 'apto', 'imóvel', 'imovel',
            'aluguel', 'venda', 'locação', 'locacao', 'r$',
            'quartos', 'quarto', 'banheiro', 'suite', 'suíte',
            'vaga', 'garagem', 'metragem', 'm²', 'm2'
        ]

    def is_property_message(self, message):
        """Verifica se a mensagem é sobre um imóvel"""
        if not message:
            return False

        message_lower = message.lower()
        return any(keyword in message_lower for keyword in self.keywords_imovel)

    def extract_price(self, text):
        """Extrai preço da mensagem"""
        patterns = [
            r'R\$\s*(\d+\.?\d*\.?\d*)',
            r'(\d+\.?\d*\.?\d*)\s*reais',
            r'valor:?\s*(\d+\.?\d*\.?\d*)',
            r'preço:?\s*R?\$?\s*(\d+\.?\d*\.?\d*)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace('.', '')
                return price_str

        return '0'

    def extract_property_type(self, text):
        """Identifica o tipo de imóvel"""
        text_lower = text.lower()

        if 'casa' in text_lower:
            return 'casa'
        elif 'apartamento' in text_lower or 'apto' in text_lower:
            return 'apartamento'
        elif 'kitnet' in text_lower or 'quitinete' in text_lower:
            return 'kitnet'
        elif 'sala comercial' in text_lower or 'comercial' in text_lower:
            return 'comercial'
        elif 'terreno' in text_lower:
            return 'terreno'
        else:
            return 'imóvel'

    def extract_transaction_type(self, text):
        """Identifica se é venda ou aluguel"""
        text_lower = text.lower()

        if 'aluguel' in text_lower or 'locação' in text_lower or 'locacao' in text_lower:
            return 'aluguel'
        elif 'venda' in text_lower or 'vende-se' in text_lower:
            return 'venda'
        else:
            return 'aluguel'  # padrão

    def create_title(self, text):
        """Gera um título para o anúncio"""
        tipo = self.extract_property_type(text)
        transacao = self.extract_transaction_type(text)
        preco = self.extract_price(text)

        if preco and preco != '0':
            return f"{tipo.capitalize()} para {transacao} - R$ {preco}"
        else:
            return f"{tipo.capitalize()} para {transacao}"

    def process_message(self, data):
        """Processa a mensagem e extrai dados do imóvel"""
        message = data.get('message', {})

        # Suporte para diferentes formatos de webhook da Evolution API
        if isinstance(message, str):
            text = message
            images = []
        else:
            text = message.get('conversation', '') or message.get('text', {}).get('body', '')

            # Extrai URLs das imagens
            images = []
            if message.get('imageMessage'):
                img_url = message['imageMessage'].get('url', '')
                if img_url:
                    images.append(img_url)
            elif message.get('images'):
                images = message.get('images', [])

        # Verifica se é mensagem sobre imóvel
        if not self.is_property_message(text):
            return None

        # Extrai informações
        property_data = {
            'titulo': self.create_title(text),
            'descricao': text[:500],  # Limita descrição
            'preco': self.extract_price(text),
            'tipo': self.extract_property_type(text),
            'transacao': self.extract_transaction_type(text),
            'images': images,
            'whatsapp_from': data.get('from', ''),
            'message_id': data.get('messageId', '')
        }

        return property_data


# Rota principal
@app.route('/', methods=['GET'])
def home():
    return "🏠 WhatsApp → Facebook Marketplace Integration está online!", 200


# Rota que recebe mensagens da Evolution API
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        print("📩 Mensagem recebida do WhatsApp:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        # Processa a mensagem
        processor = WhatsAppPropertyProcessor()
        property_data = processor.process_message(data)

        if not property_data:
            print("ℹ️ Mensagem não é sobre imóvel")
            return jsonify({"status": "ignorado", "motivo": "não é mensagem de imóvel"}), 200

        print(f"🏠 Imóvel detectado: {property_data['titulo']}")

        # Salva no banco de dados
        conn = sqlite3.connect('imoveis.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO imoveis (whatsapp_message_id, whatsapp_from, titulo, descricao,
                               preco, tipo_imovel, imagens_urls, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            property_data.get('message_id'),
            property_data.get('whatsapp_from'),
            property_data.get('titulo'),
            property_data.get('descricao'),
            property_data.get('preco'),
            property_data.get('tipo'),
            json.dumps(property_data.get('images', [])),
            'pendente'
        ))
        imovel_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"💾 Imóvel salvo no banco de dados (ID: {imovel_id})")

        # Publica no Facebook Marketplace (se configurado)
        if FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN and property_data.get('images'):
            print("📤 Publicando no Facebook Marketplace...")

            fb_integration = FacebookMarketplaceIntegration(FACEBOOK_PAGE_ID, FACEBOOK_ACCESS_TOKEN)
            listing_id = fb_integration.create_listing(property_data)

            if listing_id:
                # Atualiza o banco de dados
                conn = sqlite3.connect('imoveis.db')
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE imoveis SET facebook_listing_id = ?, status = ? WHERE id = ?
                ''', (listing_id, 'publicado', imovel_id))
                conn.commit()
                conn.close()

                return jsonify({
                    "status": "sucesso",
                    "imovel_id": imovel_id,
                    "facebook_listing_id": listing_id,
                    "titulo": property_data['titulo']
                }), 200
            else:
                return jsonify({
                    "status": "erro",
                    "motivo": "falha ao publicar no facebook",
                    "imovel_id": imovel_id
                }), 200
        else:
            motivo = []
            if not FACEBOOK_PAGE_ID or not FACEBOOK_ACCESS_TOKEN:
                motivo.append("credenciais do facebook não configuradas")
            if not property_data.get('images'):
                motivo.append("nenhuma imagem encontrada")

            return jsonify({
                "status": "salvo",
                "imovel_id": imovel_id,
                "motivo": " e ".join(motivo),
                "titulo": property_data['titulo']
            }), 200

    except Exception as e:
        print(f"❌ Erro ao processar webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


# Rota para listar imóveis cadastrados
@app.route('/imoveis', methods=['GET'])
def listar_imoveis():
    try:
        conn = sqlite3.connect('imoveis.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, titulo, preco, tipo_imovel, status, facebook_listing_id,
                   data_cadastro FROM imoveis ORDER BY data_cadastro DESC LIMIT 50
        ''')
        imoveis = cursor.fetchall()
        conn.close()

        resultado = []
        for imovel in imoveis:
            resultado.append({
                'id': imovel[0],
                'titulo': imovel[1],
                'preco': imovel[2],
                'tipo': imovel[3],
                'status': imovel[4],
                'facebook_listing_id': imovel[5],
                'data_cadastro': imovel[6]
            })

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


# Rota para detalhes de um imóvel
@app.route('/imoveis/<int:imovel_id>', methods=['GET'])
def detalhes_imovel(imovel_id):
    try:
        conn = sqlite3.connect('imoveis.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM imoveis WHERE id = ?', (imovel_id,))
        imovel = cursor.fetchone()
        conn.close()

        if not imovel:
            return jsonify({"erro": "Imóvel não encontrado"}), 404

        return jsonify({
            'id': imovel[0],
            'whatsapp_message_id': imovel[1],
            'whatsapp_from': imovel[2],
            'titulo': imovel[3],
            'descricao': imovel[4],
            'preco': imovel[5],
            'tipo': imovel[6],
            'imagens_urls': json.loads(imovel[7]) if imovel[7] else [],
            'facebook_listing_id': imovel[8],
            'data_cadastro': imovel[9],
            'status': imovel[10]
        }), 200

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
