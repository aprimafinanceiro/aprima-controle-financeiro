from flask import Flask, request, jsonify

app = Flask(__name__)

# Rota principal (opcional, só pra saber se está no ar)
@app.route('/', methods=['GET'])
def home():
    return "🚀 ZapSaaS Webhook está online!", 200

# Rota que recebe mensagens da Evolution API
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json

    print("📩 Mensagem recebida do WhatsApp:")
    print(data)

    # Exemplo: extrair mensagem e número
    mensagem = data.get("message", "")
    numero = data.get("from", "")

    # Aqui você pode adicionar lógica de resposta, categorização, etc.
    print(f"Número: {numero} | Mensagem: {mensagem}")

    return jsonify({"status": "recebido"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
