import os
import re
import logging
from datetime import datetime, timedelta
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import sqlite3
import spacy
import pandas as pd
import locale
import uuid  # Adicionado aqui para corrigir o erro
from unidecode import unidecode  # Adicione isso

# Configurações
NGROK_URL = "https://631d-2804-1b1c-200a-d300-3ca7-3ea0-6b3d-1305.ngrok-free.app"

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
ADMIN_NUMERO = os.getenv("ADMIN_NUMERO", "whatsapp:+555198995077")

MENSAGEM_BOAS_VINDAS = """
🎉 Olá! Bem-vindo(a) ao Aprima Controle Financeiro! 🎉

Eu sou seu ajudante para organizar gastos e receitas pelo WhatsApp. Veja como usar:

📌 Registrar Gastos : "Gastei 50 em mercado" ou "50 no cinema ontem"
📌 Registrar Receitas: "Recebi 100 de salário" ou "Ganhei 30 de freela"
📌 Ver Relatórios : "Resumo do Dia", "Relatório Semanal" ou "Relatório Mensal"
📌 Excluir lançamentos : "Excluir #abcd" (use o ID mostrado ao registrar)

💡 Dica: Você pode registrar várias coisas de uma vez, como "Gastei 20 em mercado e 30 em gasolina".

Qualquer dúvida, é só perguntar! Como posso te ajudar agora? 😊
"""

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração de locale e SpaCy
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')  # Usa o locale padrão do sistema
    
nlp = spacy.load("pt_core_news_sm")

# Categorias e Subcategorias
CATEGORIAS_DESPESA = {
    "Moradia": [
        "aluguel", "prestação do imóvel", "móveis", "mobilia", "eletrodomésticos", "eletros", "decoração", "decor", 
        "reparos", "consertos", "jardinagem", "jardim", "condomínio", "condo", "IPTU", "segurança residencial", 
        "mudança", "despachante imobiliário", "porteiro", "zelador", "taxas de manutenção", "financiamento casa", 
        "hipoteca", "limpeza", "faxina", "alugar", "casa própria", "quarto", "kitnet", "apartamento", "chácara", 
        "sítio", "luz da casa", "água da casa", "gás da casa"
    ],
    "Alimentação": [
        "supermercado", "mercado", "feira", "feirinha", "padaria", "pão", "açougue", "carne", "hortifruti", "verdura", 
        "bebidas", "bebida", "comida orgânica", "orgânicos", "suplementos", "vitaminas", "utensílios de cozinha", 
        "panelas", "produtos naturais", "delivery de supermercado", "ração para pets", "comida", "mantimento", 
        "lanche", "guloseimas", "doces", "salgados", "leite", "frutas", "verduras", "cereais", "enlatados", "congelados"
    ],
    "Comer fora": [
        "restaurante", "restaurantes", "lanchonete", "lanche", "pizza", "pizzaria", "delivery", "entrega", "café", 
        "cafeteria", "fast food", "sorveteria", "barzinho", "bar", "self-service", "comida japonesa", "sushi", 
        "rodízios", "food trucks", "jantar fora", "almoço fora", "comida pronta", "churrasco fora", "pastelaria", 
        "temaki", "hamburgueria", "creperia", "padoca"
    ],
    "Transporte": [
        "gasolina", "combustível", "etanol", "álcool", "diesel", "Uber", "táxi", "taxi", "ônibus","carro" , "busão", "metrô", 
        "metro", "pedágio", "pedagio", "bicicleta", "bike", "aluguel de carro", "carro alugado", "manutenção de bicicleta", 
        "transporte escolar", "van escolar", "bilhete de transporte público", "passagem", "passagem rodoviária", 
        "estacionamento", "carona", "aplicativo", "corrida", "transporte público", "trânsito", "vale transporte", 
        "trem", "barco", "ferry"  ],
    "Saúde": [
        "farmácia", "farmacia", "remédio", "medicamento", "médico", "consulta", "dentista", "dente", "exames", "exame", 
        "plano de saúde", "plano", "fisioterapia", "fisio", "psicólogo", "psi", "nutricionista", "nutri", "óculos", 
        "lentes", "cirurgias", "operação", "homeopatia", "acupuntura", "suplementos vitamínicos", "vitaminas", "hospital", 
        "internação", "terapia", "psicoterapia", "ortodontia", "aparelho dental", "prótese", "check-up", "vacina", 
        "medicina alternativa", "massoterapia"
    ],
    "Educação": [
        "escola", "colégio", "faculdade", "universidade", "curso", "aula", "livros", "livro", "material escolar", 
        "material", "pós-graduação", "pós", "tutoria particular", "professor particular", "plataformas de ensino", 
        "EAD", "workshops", "workshop", "congressos", "seminário", "certificações", "certificado", "aulas online", 
        "idiomas", "inglês", "espanhol", "caderno", "mochila", "caneta", "treinamento", "palestra", "escola técnica", 
        "uniforme", "matrícula"
    ],
    "Lazer": [
        "cinema", "filme", "teatro", "show", "shows", "jogos", "game", "bar", "boteco", "passeios", "passeio", "parques", 
        "parque", "museus", "museu", "esportes radicais", "aventura", "clube", "viagens curtas", "bate-volta", "festivais", 
        "festival", "boliche", "escape room", "camping", "rolê", "balada", "festa", "praia", "academia", "esporte", 
        "trilha", "pescaria", "churrasco", "kart", "paintball"
    ],
    "Shopping": [
        "compras gerais", "compras", "eletrônicos", "eletronico", "souvenirs", "lembrancinha", "presentes", "presente", 
        "lojas de departamento", "loja", "artesanato", "livraria", "games", "jogo", "brinquedos", "brinquedo", "vitrine", 
        "promoção", "black friday", "shop", "galeria", "feira de rua", "bazar", "outlet", "roupas de marca", "perfumaria"
    ],
    "Vestuário": [
        "roupas", "roupa", "sapatos", "sapato", "acessórios", "acessorio", "roupas de academia", "roupa esportiva", 
        "roupas de festa", "roupa social", "joias", "bijuteria", "moda praia", "biquíni", "roupas infantis", "roupa de bebê", 
        "tênis", "chinelo", "bolsa", "mochila", "cinto", "óculos de sol", "roupa íntima", "lingerie", "meia", "calça", 
        "camiseta", "jaqueta", "uniforme", "costureira", "roupa sob medida"
    ],
    "Beleza e cuidados pessoais": [
        "cabeleireiro", "salão", "manicure", "unha", "cosméticos", "maquiagem", "barbearia", "barba", "spa", "tratamentos estéticos", 
        "estética", "perfumes", "perfume", "dermatologista", "dermato", "massagem", "depilação", "creme", "hidratante", 
        "shampoo", "tratamento", "bronzeamento", "tatuagem", "piercing", "esteticista", "podologia", "corte de cabelo", 
        "unhas postiças", "maquiador"
    ],
    "Contas e utilidades": [
        "internet", "wifi", "energia", "luz", "água", "gás", "gas", "telefone", "celular", "TV a cabo", "tv", "manutenção elétrica", 
        "eletricidade", "coleta de lixo", "lixo", "desentupimento", "encanamento", "serviço de esgoto", "esgoto", "segurança privada", 
        "alarme", "assinatura de tv", "netflix", "conta", "boleto", "fatura", "recarga", "telefonia", "conserto de conta"
    ],
    "Seguro": [
        "seguro viagem", "seguro de vida", "vida", "seguro residencial", "seguro casa", "seguro de carro", "seguro auto", 
        "seguro saúde", "seguro para celular", "seguro de bicicleta", "seguro bike", "seguro contra acidentes", "apólice", 
        "proteção", "seguro odontológico", "seguro empresarial", "seguro de viagem internacional", "seguro de equipamentos"
    ],
    "Viagens": [
        "hotel", "hospedagem", "passagem aérea", "avião", "passagem de ônibus", "ônibus", "aluguel de carro", "carro alugado", 
        "passeios turísticos", "turismo", "seguro viagem", "transporte local", "souvenirs", "lembrancinha", "alimentação em viagem", 
        "comida de viagem", "pacote", "excursão", "camping", "resort", "cruzeiro", "hostel", "pousada", "airbnb", "guia turístico", 
        "ingresso de atração"
    ],
    "Impostos e taxas": [
        "impostos", "imposto", "taxas", "taxa", "multas", "multa", "contribuição sindical", "sindicato", "licenciamento de veículo", 
        "licenciamento", "taxas bancárias", "tarifa bancária", "IPVA", "taxa de cartório", "cartório", "tarifas de documentos", 
        "darf", "irpf", "juros", "tarifa", "taxa de serviço", "pedágio extra", "taxa de administração", "tributo"
    ],
    "Investimentos": [
        "aplicação", "investimento", "compra de ações", "ações", "fundos", "fundo", "criptomoedas", "cripto", "tesouro direto", 
        "tesouro", "investimento imobiliário", "imóvel", "CDB", "LCI", "LCA", "fundos multimercado", "previdência privada", 
        "previdência", "poupança", "renda fixa", "corretora", "trade", "bitcoin", "ethereum", "day trade", "swing trade"
    ],
    "Dívidas e financiamentos": [
        "empréstimo", "financiamento", "cartão de crédito", "cartão", "parcelamentos", "parcela", "cheque especial", "juros", 
        "dívidas pessoais", "dívida", "consórcio", "crediário", "boleto", "pagamento atrasado", "financiamento de carro", 
        "financiamento de casa", "empréstimo pessoal", "agiotagem", "penhor", "refinanciamento"
    ],
    "Presentes e doações": [
        "aniversário", "natal", "casamento", "doação", "caridade", "doação para ONGs", "ONG", "vaquinhas", "presentes corporativos", 
        "brindes", "presente", "mimo", "lembrança", "ajuda", "doação religiosa", "dízimo", "oferta", "presente de amigo secreto", 
        "caixinha", "donativo"
    ],
    "Pets": [
        "ração", "comida", "veterinário", "vet", "acessórios", "coleira", "banho e tosa", "banho", "tosa", "hospedagem", 
        "brinquedos para pet", "brinquedo", "adestramento", "vacinas", "vacina", "consulta veterinária", "medicação para pets", 
        "remédio", "pet shop", "gato", "cachorro", "pássaro", "aquário", "ração especial", "tratamento pet", "hotel pet"
    ],
    "Assinaturas e serviços": [
        "streaming", "netflix", "revistas", "revista", "aplicativos", "app", "serviços online", "clubes de assinatura", 
        "assinatura", "assinatura de cursos", "curso online", "software licenciado", "software", "cloud storage", "nuvem", 
        "Spotify", "música", "Amazon Prime", "Disney+", "HBO", "YouTube Premium", "jornal online", "assinatura de academia"
    ],
    "Manutenção da casa": [
        "reparos", "conserto", "pintura", "tinta", "limpeza", "produtos de limpeza", "encanador", "encanamento", "eletricista", 
        "elétrica", "troca de móveis", "móvel novo", "dedetização", "controle de pragas", "construção e reforma", "reforma", 
        "telhado", "telha", "cortinas e persianas", "persiana", "janela", "vidro", "marceneiro", "carpintaria", "gesso", 
        "piso", "azulejo"
    ],
    "Educação dos filhos": [
        "escola", "colégio", "uniforme", "material escolar", "caderno", "mochila", "atividades extracurriculares", "esporte", 
        "música", "reforço escolar", "aula particular", "transporte escolar", "van", "excursões", "passeio escolar", "creche", 
        "berçário", "babá", "idiomas infantil", "acampamento escolar", "livros infantis", "tablets escolares"
    ],
    "Festas e eventos": [
        "festa", "aniversário", "casamento", "formatura", "aluguel de salão", "salão", "decoração", "decor", "buffet", 
        "comida", "fotografia", "foto", "DJ", "banda", "convites", "convite", "bebida", "bolo", "show", "ingresso", 
        "festa infantil", "open bar", "cerimonialista", "aluguel de equipamentos", "som e luz"
    ],
    "Emergências": [
        "reserva", "conserto urgente", "médico emergencial", "hospital", "ajuda financeira inesperada", "socorro", "reboque", 
        "chaveiro", "remédio urgente", "despesa imprevista", "urgência", "emergência", "conserto de carro", "queda de energia", 
        "vazamento", "incêndio", "pronto-socorro"
    ],
    "Tecnologia": [
        "celular", "smartphone", "computador", "notebook", "acessórios tech", "carregador", "software", "programa", "impressora", 
        "cartucho", "upgrade de hardware", "upgrade", "console de videogame", "console", "smartwatch", "relógio inteligente", 
        "tablet", "games", "jogo", "internet", "roteador", "cabo", "TV smart", "caixa de som", "fones de ouvido"
    ],
    "Equipamentos e ferramentas": [
        "ferramentas", "ferramenta", "equipamentos", "equipamento", "manutenção", "conserto", "compra de maquinário", "máquina", 
        "itens de construção", "material de obra", "equipamentos de segurança", "capacete", "serra", "furadeira", "parafusadeira", 
        "trena", "escada", "gerador", "solda", "equipamento de jardinagem"
    ],
    "Serviços domésticos": [
        "faxineira", "diarista", "jardineiro", "jardinagem", "babá", "cuidador", "cozinheira", "cozinha", "lavanderia", 
        "passadeira", "limpeza", "serviço", "limpeza de piscina", "piscineiro", "caseiro", "zelador doméstico", "motorista", 
        "entregador doméstico", "serviços gerais", "lavagem de tapete"
    ],
    "Manutenção do carro": [
        "revisão", "revisao", "peças", "peça", "lavagem", "lava jato", "seguro auto", "troca de óleo", "óleo", 
        "alinhamento e balanceamento", "alinhamento", "troca de pneus", "pneu", "mecânico", "funilaria", "pintura", 
        "bateria", "farol", "limpador de para-brisa", "calibragem", "conserto de ar condicionado", "vidro do carro"
    ],
    "Reservas financeiras": [
        "poupança", "fundo de emergência", "reserva", "reserva para viagens", "reserva para aposentadoria", "economia", 
        "dinheiro guardado", "poupar", "fundo reserva", "caixinha", "cofrinho", "reserva para imprevistos", "pote de dinheiro"
    ],
    "Mesada e ajuda financeira": [
        "mesada para filhos", "mesada", "mesada para familiares", "ajuda para amigos", "transferência financeira", 
        "ajuda a terceiros", "dinheiro para família", "grana emprestada", "auxílio financeiro", "presente em dinheiro", 
        "caixinha para alguém", "pix para amigo"
    ],
    "Outros": [
        "serviços gerais", "despesas avulsas", "gorjetas", "gorjeta", "despesas bancárias", "perda financeira", "outro", 
        "gastos extras", "miscelânea", "diversos", "não categorizado", "compras aleatórias", "despesa pequena", 
        "dinheiro perdido", "taxa extra", "serviço avulso"
    ]
}

CATEGORIAS_RECEITA = {
    "Salário e Trabalho Formal": [
        "salário", "salario", "proventos", "pagamento", "ordenado", "renda fixa", "mensal", "holerite", "contracheque", 
        "remuneração", "folha de pagamento", "renda CLT", "adicional noturno", "hora extra", "bônus salarial", "comissão fixa", 
        "salário mensal", "vencimento", "renda de emprego", "carteira assinada", "salário base", "adicional de periculosidade", 
        "adicional de insalubridade", "gratificação", "prêmio de desempenho"
    ],
    "Freelance e Trabalho Autônomo": [
        "freelance", "bico", "trabalho extra", "freela", "serviço avulso", "job", "trampo", "ganho extra", "autônomo", 
        "consultoria", "projeto", "prestação de serviço", "design gráfico", "tradução", "programação", "aulas particulares", 
        "manutenção", "serviço técnico", "fotografia", "filmagem", "edição de vídeo", "redação", "locução", "produção musical", 
        "artesanato", "costura", "reparos", "pintura", "trabalho manual", "serviço de limpeza", "babysitting", "dog walker", 
        "entrega", "motorista de aplicativo"
    ],
    "Investimentos e Aplicações Financeiras": [
        "juros", "dividendos", "renda fixa", "lucro de ações", "ações", "tesouro direto", "CDB", "poupança", "lucro", "retorno", 
        "ganho financeiro", "rendimento", "trade", "invest", "criptomoedas", "cripto", "fundos imobiliários", "renda passiva", 
        "ganho com forex", "staking de criptomoedas", "NFTs", "royalties", "bitcoin", "ethereum", "lucro de trade", "day trade", 
        "swing trade", "LCI", "LCA", "fundos multimercado", "previdência privada", "tesouro selic", "renda de investimento", 
        "ganho de capital", "lucro de fundos"
    ],
    "Aluguel e Locação": [
        "aluguel recebido", "locação", "subarrendamento", "renda de imóvel", "aluguéis", "ganho com imóvel", "repasse de aluguel", 
        "hospedagem curta", "Airbnb", "inquilino", "locação de carro", "locação de equipamentos", "locação de terrenos", 
        "locação de espaço comercial", "aluguel de casa", "aluguel de apartamento", "renda de temporada", "locação de máquinas", 
        "aluguel de ferramentas", "renda de garagem", "aluguel de quarto", "coworking"
    ],
    "Venda de Produtos e Serviços": [
        "venda de produto", "venda de serviço", "venda pessoal", "venda", "revenda", "lucro de venda", "comércio", "negócio", 
        "brechó", "usado", "artesanato", "feira", "dropshipping", "e-commerce", "marketplace", "mercado livre", "OLX", "Shopee", 
        "Etsy", "importação", "venda de comida", "venda de roupas", "venda de eletrônicos", "venda de móveis", "venda de carro", 
        "venda de moto", "lucro de revenda", "venda de cosméticos", "venda de bijuterias", "venda online"
    ],
    "Prêmios e Recompensas": [
        "prêmio", "herança", "bônus", "loteria", "ganho", "achado", "recompensa", "cashback", "sorteio", "concursos", "bolão", 
        "campanhas de incentivo", "jogos de azar", "casino", "bet", "premiação esportiva", "programa de fidelidade", "prêmio em dinheiro", 
        "ganho de rifa", "sorteio online", "recompensa de aplicativo", "prêmio de competição", "dinheiro encontrado", "recompensa de trabalho"
    ],
    "Comissões e Programas de Afiliados": [
        "comissão", "afiliado", "renda de afiliado", "propaganda", "publicidade", "comissão de venda", "indicação", "link de afiliado", 
        "patrocínio", "marketing de afiliados", "renda de parcerias", "dropshipping afiliado", "lucro de indicação", "comissão variável", 
        "ganho por clique", "CPC", "CPA", "lucro de campanha", "afiliação online", "renda de influencer"
    ],
    "Presente e Doação Recebida": [
        "presente", "doação recebida", "mimo", "dinheiro de presente", "ajuda", "grana", "caixinha", "gorjeta", "herança", 
        "mesada recebida", "doação de empresa", "financiamento coletivo", "apoio financeiro", "dinheiro de família", "presente de aniversário", 
        "presente de natal", "vaquinha online", "pix de amigo", "doação religiosa", "ajuda de custo", "donativo"
    ],
    "Reembolso e Restituições": [
        "reembolso", "devolução", "restituição", "volta", "dinheiro de volta", "acerto", "ressarcimento", "indenização", 
        "seguro recebido", "acerto trabalhista", "plano de saúde reembolso", "seguro de viagem", "devolução de compra", 
        "reembolso de passagem", "restituição de imposto", "IRPF devolvido", "dinheiro retornado", "acerto de conta", 
        "reembolso de aplicativo", "devolução de produto"
    ],
    "Direitos e Benefícios": [
        "auxílio", "aposentadoria", "pensão", "seguro-desemprego", "benefício social", "auxílio emergencial", "BPC", "bolsa família", 
        "FGTS", "décimo terceiro", "participação nos lucros", "abono salarial", "rescisão", "benefícios previdenciários", 
        "pensões alimentícias", "reajuste salarial", "benefício de servidor público", "auxílio transporte", "vale alimentação convertido em dinheiro", 
        "vale refeição em dinheiro", "auxílio doença", "licença remunerada", "férias remuneradas", "indenização trabalhista"
    ],
    "Reservas Financeiras e Aportes": [
        "saque de poupança", "uso de fundo", "reserva", "dinheiro guardado", "economia", "fundo emergencial", "retirada", 
        "aporte pessoal", "resgate de aplicação", "empréstimo recebido", "resgate de previdência privada", "saque de investimento", 
        "dinheiro do cofrinho", "reserva usada", "fundo de reserva", "retirada de CDB", "resgate de tesouro", "saque de ações"
    ],
    "Criação de Conteúdo e Redes Sociais": [
        "monetização", "YouTube", "TikTok", "Twitch", "Facebook Ads", "Instagram Ads", "blog", "produção de conteúdo", "assinantes", 
        "OnlyFans", "apoio financeiro", "crowdfunding", "doação de seguidores", "Patreon", "streaming", "live paga", "subscribers", 
        "super chat", "cursos online vendidos", "publicidade no blog", "anúncios", "renda de canal", "views monetizadas", "lives"
    ],
    "Educação e Pesquisa": [
        "bolsa de estudos", "bolsa pesquisa", "iniciação científica", "bolsa CAPES", "bolsa CNPq", "fundo de pesquisa", 
        "palestras remuneradas", "consultoria acadêmica", "produção de artigos científicos pagos", "mentoria acadêmica", 
        "auxílio acadêmico", "renda de professor", "bolsa de mestrado", "bolsa de doutorado", "financiamento de pesquisa", 
        "workshop pago", "curso ministrado"
    ],
    "Transações e Benefícios Bancários": [
        "cashback", "recompensa bancária", "pontos convertidos em dinheiro", "recompensa de cartão de crédito", "juros sobre saldo", 
        "incentivos financeiros", "abono bancário", "programa de milhas convertido em dinheiro", "bônus de conta", "reembolso bancário", 
        "lucro de conta remunerada", "cashback de compras", "desconto convertido em dinheiro", "promoção bancária"
    ],
    "Empreendedorismo e Startups": [
        "investimento recebido", "capital de risco", "rodada de investimento", "investidor-anjo", "fundo de venture capital", 
        "seed money", "financiamento coletivo", "subvenção para startup", "subvenção para inovação", "lucro de startup", 
        "venda de participação", "aporte de sócio", "investimento externo", "renda de pitch", "fundo de aceleração"
    ],
    "Outros": [
        "renda extra", "dinheiro inesperado", "renda ocasional", "outros ganhos", "devolução de imposto", "crédito bancário", 
        "pagamento atrasado", "troco recebido", "valor ressarcido", "lucro por arbitragem", "compensação por erro bancário", 
        "benefício inesperado", "dinheiro achado", "reembolso avulso", "ganho pequeno", "lucro não categorizado"
    ]
}

# Flask
app = Flask(__name__)
exclusoes_pendentes = {}

# Banco de Dados
sqlite3.register_adapter(datetime, lambda val: val.isoformat())

def get_db_connection():
    conn = sqlite3.connect("gastos.db")
    conn.row_factory = sqlite3.Row
    return conn

def criar_banco():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Dropar tabelas existentes para recriar com subcategoria
        cursor.execute("DROP TABLE IF EXISTS gastos")
        cursor.execute("DROP TABLE IF EXISTS receitas")
        cursor.execute("DROP TABLE IF EXISTS usuarios_boas_vindas")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id TEXT PRIMARY KEY,
            usuario TEXT NOT NULL,
            valor REAL NOT NULL,
            categoria TEXT NOT NULL,
            subcategoria TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mensagem TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS receitas (
            id TEXT PRIMARY KEY,
            usuario TEXT NOT NULL,
            valor REAL NOT NULL,
            categoria TEXT NOT NULL,
            subcategoria TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mensagem TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_autorizados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios_boas_vindas (
            numero TEXT PRIMARY KEY,
            recebeu_boas_vindas INTEGER DEFAULT 0
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gastos_usuario_data ON gastos (usuario, data)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receitas_usuario_data ON receitas (usuario, data)")
        numeros_iniciais = ["whatsapp:+555198995077"]
        for numero in numeros_iniciais:
            cursor.execute("INSERT OR IGNORE INTO usuarios_autorizados (numero) VALUES (?)", (numero,))
            cursor.execute("INSERT OR IGNORE INTO usuarios_boas_vindas (numero, recebeu_boas_vindas) VALUES (?, 1)", (numero,))
        conn.commit()

# Autenticação
def usuario_autorizado(numero):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT numero FROM usuarios_autorizados WHERE numero = ?", (numero,))
        return cursor.fetchone() is not None

def adicionar_usuario(numero):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO usuarios_autorizados (numero) VALUES (?)", (numero,))
        conn.commit()
    logger.info(f"✅ Usuário autorizado: {numero}")

def remover_usuario(numero):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM usuarios_autorizados WHERE numero = ?", (numero,))
        conn.commit()
    logger.info(f"✅ Usuário removido: {numero}")

def listar_usuarios_autorizados():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT numero FROM usuarios_autorizados")
        usuarios = cursor.fetchall()
    return [usuario["numero"].replace("whatsapp:", "") for usuario in usuarios]

def usuario_recebeu_boas_vindas(numero):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT recebeu_boas_vindas FROM usuarios_boas_vindas WHERE numero = ?", (numero,))
        resultado = cursor.fetchone()
        if resultado and resultado["recebeu_boas_vindas"] == 1:
            return True
        return False

def marcar_boas_vindas_enviada(numero):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO usuarios_boas_vindas (numero, recebeu_boas_vindas) VALUES (?, 1)", (numero,))
        conn.commit()
    logger.info(f"✅ Boas-vindas marcadas como enviadas para {numero}")

# Funções Auxiliares
def formatar_valor(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_date(texto):
    texto = texto.lower()
    hoje = datetime.now()
    if "ontem" in texto:
        return hoje - timedelta(days=1)
    elif "semana passada" in texto:
        return hoje - timedelta(days=7)
    elif "dia" in texto:
        match = re.search(r"dia (\d{1,2})", texto)
        if match:
            dia = int(match.group(1))
            mes = hoje.month
            ano = hoje.year
            if dia > hoje.day:
                if mes > 1:
                    mes -= 1
                else:
                    mes = 12
                    ano -= 1
            try:
                return datetime(ano, mes, dia)
            except ValueError:
                return hoje
    return hoje

def processar_mensagem(mensagem):
    doc = nlp(mensagem.lower())
    mensagem_sem_acento = unidecode(mensagem.lower())  # Normaliza a mensagem inteira
    logger.info(f"Processando mensagem completa: {mensagem} (sem acento: {mensagem_sem_acento})")
    
    tipo = "gasto"  # Padrão
    if any(token.lemma_ in ["receber", "ganhar", "recebi"] for token in doc):
        tipo = "receita"
    categorias = CATEGORIAS_RECEITA if tipo == "receita" else CATEGORIAS_DESPESA
    
    data_atual = parse_date(mensagem)
    
    valores = []
    for token in doc:
        if token.like_num:
            try:
                valor = float(token.text.replace(",", ".").strip())
                if 0 < valor <= 10000:
                    valores.append(valor)
                    logger.info(f"Valor encontrado: {valor}")
            except ValueError:
                pass
    
    if not valores:
        logger.info("Nenhum valor válido encontrado na mensagem")
        return []
    
    itens = []
    for valor in valores:
        categoria_atual = "Outros"
        subcategoria_atual = None
        
        # Busca por correspondência em subcategorias na mensagem inteira
        melhor_correspondencia = None
        maior_tamanho = 0
        for cat, subs in categorias.items():
            for sub in subs:
                sub_sem_acento = unidecode(sub.lower())
                if sub_sem_acento in mensagem_sem_acento:
                    if sub_sem_acento == "gas" and "gastei" in mensagem_sem_acento:
                        continue
                    if len(sub_sem_acento) > maior_tamanho:
                        melhor_correspondencia = (cat, sub.capitalize())
                        maior_tamanho = len(sub_sem_acento)
                        logger.info(f"Match encontrado: {cat}/{sub} (normalizado: {sub_sem_acento})")
        
        if melhor_correspondencia:
            categoria_atual, subcategoria_atual = melhor_correspondencia
        else:
            logger.info(f"Nenhuma subcategoria encontrada, usando categoria padrão: {categoria_atual}")
        
        itens.append((valor, categoria_atual, subcategoria_atual, data_atual, tipo))
    
    return itens
def gerar_id_unico():
    return f"#{uuid.uuid4().hex[:4]}"

def salvar_gasto(usuario, valor, categoria, subcategoria=None, data=None, mensagem=None):
    try:
        id_registro = gerar_id_unico()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if data is None:
                cursor.execute("INSERT INTO gastos (id, usuario, valor, categoria, subcategoria, mensagem) VALUES (?, ?, ?, ?, ?, ?)", 
                               (id_registro, usuario, valor, categoria, subcategoria, mensagem))
            else:
                cursor.execute("INSERT INTO gastos (id, usuario, valor, categoria, subcategoria, data, mensagem) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                               (id_registro, usuario, valor, categoria, subcategoria, data, mensagem))
            conn.commit()
            logger.info(f"✅ Gasto salvo: id={id_registro}, usuario={usuario}, valor={valor}, categoria={categoria}, subcategoria={subcategoria}, data={data or 'hoje'}")
            return id_registro
    except Exception as e:
        logger.error(f"Erro ao salvar gasto: {str(e)}")
        return None

def salvar_receita(usuario, valor, categoria, subcategoria=None, data=None, mensagem=None):
    try:
        id_registro = gerar_id_unico()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if data is None:
                cursor.execute("INSERT INTO receitas (id, usuario, valor, categoria, subcategoria, mensagem) VALUES (?, ?, ?, ?, ?, ?)", 
                               (id_registro, usuario, valor, categoria, subcategoria, mensagem))
            else:
                cursor.execute("INSERT INTO receitas (id, usuario, valor, categoria, subcategoria, data, mensagem) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                               (id_registro, usuario, valor, categoria, subcategoria, data, mensagem))
            conn.commit()
            logger.info(f"✅ Receita salva: id={id_registro}, usuario={usuario}, valor={valor}, categoria={categoria}, subcategoria={subcategoria}, data={data or 'hoje'}")
            return id_registro
    except Exception as e:
        logger.error(f"Erro ao salvar receita: {str(e)}")
        return None

def excluir_registro(usuario, id_registro, tipo="gasto"):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            tabela = "gastos" if tipo == "gasto" else "receitas"
            cursor.execute(f"DELETE FROM {tabela} WHERE usuario = ? AND id = ?", (usuario, id_registro))
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"✅ Registro excluído: usuario={usuario}, id={id_registro}, tipo={tipo}")
                return True
            else:
                logger.info(f"⚠️ Registro não encontrado: usuario={usuario}, id={id_registro}, tipo={tipo}")
                return False
    except Exception as e:
        logger.error(f"Erro ao excluir registro: {str(e)}")
        return False

# Análise
def calcular_gastos_hoje(usuario):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        hoje = datetime.now()
        inicio_hoje = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        fim_hoje = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
        cursor.execute("SELECT SUM(valor) FROM gastos WHERE usuario = ? AND data BETWEEN ? AND ?", 
                       (usuario, inicio_hoje, fim_hoje))
        total = cursor.fetchone()[0] or 0.0
    return total

def calcular_receitas_hoje(usuario):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        hoje = datetime.now()
        inicio_hoje = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        fim_hoje = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
        cursor.execute("SELECT SUM(valor) FROM receitas WHERE usuario = ? AND data BETWEEN ? AND ?", 
                       (usuario, inicio_hoje, fim_hoje))
        total = cursor.fetchone()[0] or 0.0
    return total

def gerar_relatorio_diario(usuario):
    hoje = datetime.now()
    inicio_hoje = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_hoje = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)

    with get_db_connection() as conn:
        query_gastos = """
        SELECT categoria, subcategoria, SUM(valor) as valor 
        FROM gastos 
        WHERE usuario = ? AND data BETWEEN ? AND ? 
        GROUP BY categoria, subcategoria
        """
        df_gastos = pd.read_sql_query(query_gastos, conn, params=(usuario, inicio_hoje, fim_hoje))
        
        query_receitas = """
        SELECT categoria, subcategoria, SUM(valor) as valor 
        FROM receitas 
        WHERE usuario = ? AND data BETWEEN ? AND ? 
        GROUP BY categoria, subcategoria
        """
        df_receitas = pd.read_sql_query(query_receitas, conn, params=(usuario, inicio_hoje, fim_hoje))

    total_gastos = df_gastos['valor'].sum() if not df_gastos.empty else 0.0
    total_receitas = df_receitas['valor'].sum() if not df_receitas.empty else 0.0
    
    if df_gastos.empty and df_receitas.empty:
        raise ValueError("Nenhum dado disponível para hoje.")
    
    df_gastos["valor_formatted"] = df_gastos["valor"].apply(formatar_valor) if not df_gastos.empty else None
    df_receitas["valor_formatted"] = df_receitas["valor"].apply(formatar_valor) if not df_receitas.empty else None
    
    logger.info(f"Dados para relatório diário: Gastos={df_gastos.to_dict()}, Receitas={df_receitas.to_dict()}")
    return df_gastos, df_receitas, total_gastos, total_receitas, hoje, hoje

def gerar_relatorio_semanal(usuario):
    hoje = datetime.now()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    inicio_semana = inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_semana = fim_semana.replace(hour=23, minute=59, second=59, microsecond=999999)

    with get_db_connection() as conn:
        query_gastos = """
        SELECT categoria, subcategoria, SUM(valor) as valor 
        FROM gastos 
        WHERE usuario = ? AND data BETWEEN ? AND ? 
        GROUP BY categoria, subcategoria
        """
        df_gastos = pd.read_sql_query(query_gastos, conn, params=(usuario, inicio_semana, fim_semana))
        
        query_receitas = """
        SELECT categoria, subcategoria, SUM(valor) as valor 
        FROM receitas 
        WHERE usuario = ? AND data BETWEEN ? AND ? 
        GROUP BY categoria, subcategoria
        """
        df_receitas = pd.read_sql_query(query_receitas, conn, params=(usuario, inicio_semana, fim_semana))

    total_gastos = df_gastos['valor'].sum() if not df_gastos.empty else 0.0
    total_receitas = df_receitas['valor'].sum() if not df_receitas.empty else 0.0
    
    if df_gastos.empty and df_receitas.empty:
        raise ValueError("Nenhum dado disponível para a semana atual.")
    
    df_gastos["valor_formatted"] = df_gastos["valor"].apply(formatar_valor) if not df_gastos.empty else None
    df_receitas["valor_formatted"] = df_receitas["valor"].apply(formatar_valor) if not df_receitas.empty else None
    
    logger.info(f"Dados para relatório semanal: Gastos={df_gastos.to_dict()}, Receitas={df_receitas.to_dict()}")
    return df_gastos, df_receitas, total_gastos, total_receitas, inicio_semana, fim_semana

def gerar_relatorio_mensal(usuario, mes=None):
    hoje = datetime.now()
    if mes:
        meses = {
            "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6,
            "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12
        }
        mes_num = meses.get(mes.lower())
        if not mes_num:
            raise ValueError("Mês inválido. Use: janeiro, fevereiro, etc.")
        ano = hoje.year if mes_num <= hoje.month else hoje.year - 1
        inicio_mes = datetime(ano, mes_num, 1)
    else:
        inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ano = hoje.year
        mes_num = hoje.month
    
    ultimo_dia = (inicio_mes.replace(month=mes_num % 12 + 1, day=1) - timedelta(days=1) if mes_num < 12 else 
                  datetime(ano + 1, 1, 1) - timedelta(days=1))
    fim_mes = ultimo_dia.replace(hour=23, minute=59, second=59, microsecond=999999)

    with get_db_connection() as conn:
        query_gastos = """
        SELECT categoria, subcategoria, SUM(valor) as valor 
        FROM gastos 
        WHERE usuario = ? AND data BETWEEN ? AND ? 
        GROUP BY categoria, subcategoria
        """
        df_gastos = pd.read_sql_query(query_gastos, conn, params=(usuario, inicio_mes, fim_mes))
        
        query_receitas = """
        SELECT categoria, subcategoria, SUM(valor) as valor 
        FROM receitas 
        WHERE usuario = ? AND data BETWEEN ? AND ? 
        GROUP BY categoria, subcategoria
        """
        df_receitas = pd.read_sql_query(query_receitas, conn, params=(usuario, inicio_mes, fim_mes))

    total_gastos = df_gastos['valor'].sum() if not df_gastos.empty else 0.0
    total_receitas = df_receitas['valor'].sum() if not df_receitas.empty else 0.0
    
    if df_gastos.empty and df_receitas.empty:
        mes_str = mes or hoje.strftime('%B').lower()
        raise ValueError(f"Nenhum dado disponível para o mês de {mes_str}.")
    
    df_gastos["valor_formatted"] = df_gastos["valor"].apply(formatar_valor) if not df_gastos.empty else None
    df_receitas["valor_formatted"] = df_receitas["valor"].apply(formatar_valor) if not df_receitas.empty else None
    
    logger.info(f"Dados para relatório mensal: Gastos={df_gastos.to_dict()}, Receitas={df_receitas.to_dict()}")
    return df_gastos, df_receitas, total_gastos, total_receitas, inicio_mes, fim_mes

# Rota Principal
@app.route("/webhook", methods=["POST"])
def webhook():
    if not request.form or "Body" not in request.form or "From" not in request.form:
        logger.error("Requisição inválida: campos obrigatórios ausentes")
        resp = MessagingResponse()
        resp.message("⚠️ Erro interno: requisição inválida. Contate o suporte.")
        return str(resp), 400

    mensagem = request.form["Body"].strip().lower()
    numero = request.form["From"]

    if not mensagem:
        logger.info(f"Usuário {numero} enviou mensagem vazia")
        resp = MessagingResponse()
        resp.message("⚠️ Mensagem vazia. Tente algo como 'Gastei 50 no mercado'.")
        return str(resp)
    if len(mensagem) > 1000:
        logger.warning(f"Mensagem de {numero} excedeu limite: {len(mensagem)} caracteres")
        resp = MessagingResponse()
        resp.message("⚠️ Mensagem muito longa. Limite: 1000 caracteres.")
        return str(resp)

    logger.info(f"Mensagem recebida: '{mensagem}' de {numero}")

    if not usuario_autorizado(numero):
        logger.info(f"Usuário não autorizado: {numero}")
        resp = MessagingResponse()
        resp.message("⚠️ Você não está autorizado a usar este serviço. Contate o administrador.")
        return str(resp)

    resp = MessagingResponse()

    # Verificar e enviar mensagem de boas-vindas
    if not usuario_recebeu_boas_vindas(numero):
        resp.message(MENSAGEM_BOAS_VINDAS)
        marcar_boas_vindas_enviada(numero)
        return str(resp)

    # Comandos Admin
    if numero == ADMIN_NUMERO:
        if mensagem.startswith("add "):
            novo_numero = mensagem.split(" ")[1].strip()
            if not re.match(r"^\+?\d{10,15}$", novo_numero):
                resp.message("⚠️ Número inválido. Use formato: +551234567890")
                return str(resp)
            novo_numero = "whatsapp:" + novo_numero if not novo_numero.startswith("whatsapp:") else novo_numero
            adicionar_usuario(novo_numero)
            resp.message(f"✅ Usuário {novo_numero} autorizado.")
            return str(resp)
        elif mensagem.startswith("remove "):
            numero_remover = mensagem.split(" ")[1].strip()
            if not re.match(r"^\+?\d{10,15}$", numero_remover):
                resp.message("⚠️ Número inválido. Use formato: +551234567890")
                return str(resp)
            numero_remover = "whatsapp:" + numero_remover if not numero_remover.startswith("whatsapp:") else numero_remover
            remover_usuario(numero_remover)
            resp.message(f"✅ Usuário {numero_remover} removido.")
            return str(resp)
        elif mensagem == "listar":
            usuarios = listar_usuarios_autorizados()
            resp.message(f"📋 Usuários autorizados:\n" + "\n".join(usuarios) if usuarios else "⚠️ Nenhum usuário autorizado.")
            return str(resp)

    # Exclusão de Registros
    if numero in exclusoes_pendentes:
        id_registro, tipo = exclusoes_pendentes[numero]
        if mensagem == "sim":
            with get_db_connection() as conn:
                cursor = conn.cursor()
                tabela = "gastos" if tipo == "gasto" else "receitas"
                cursor.execute(f"SELECT * FROM {tabela} WHERE usuario = ? AND id = ?", (numero, id_registro))
                registro = cursor.fetchone()
                if registro and excluir_registro(numero, id_registro, tipo):
                    valor = formatar_valor(registro['valor'])
                    categoria = registro['categoria']
                    subcategoria = registro['subcategoria'] or "Geral"
                    tipo_str = "Gasto" if tipo == "gasto" else "Receita"
                    resp.message(f"✅ {tipo_str} ID {id_registro} excluído com sucesso ({valor} em {categoria}/{subcategoria}).")
                else:
                    resp.message(f"⚠️ Registro ID {id_registro} não encontrado ou já excluído.")
            del exclusoes_pendentes[numero]
        elif mensagem == "não":
            resp.message(f"❌ Exclusão do ID {id_registro} cancelada.")
            del exclusoes_pendentes[numero]
        else:
            resp.message("⚠️ Responda apenas 'Sim' ou 'Não'.")
        return str(resp)
    
    if mensagem.startswith("excluir id ") or mensagem.startswith("excluir "):
        try:
            id_registro = mensagem.split("excluir ")[1].split()[0] if "excluir id " not in mensagem else mensagem.split("excluir id ")[1].split()[0]
            if not re.match(r"^#\w{4}$", id_registro):
                resp.message("⚠️ ID inválido. Ex.: 'excluir #60fc'")
                return str(resp)
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM gastos WHERE usuario = ? AND id = ?", (numero, id_registro))
                registro_gasto = cursor.fetchone()
                cursor.execute("SELECT * FROM receitas WHERE usuario = ? AND id = ?", (numero, id_registro))
                registro_receita = cursor.fetchone()
                
                if registro_gasto:
                    tipo = "gasto"
                    registro = registro_gasto
                elif registro_receita:
                    tipo = "receita"
                    registro = registro_receita
                else:
                    resp.message(f"⚠️ Registro ID {id_registro} não encontrado.")
                    return str(resp)
                
                exclusoes_pendentes[numero] = (id_registro, tipo)
                valor = formatar_valor(registro['valor'])
                categoria = registro['categoria']
                subcategoria = registro['subcategoria'] or "Geral"
                tipo_str = "Gasto" if tipo == "gasto" else "Receita"
                resp.message(f"Confirmar exclusão de {tipo_str} ID {id_registro} ({valor} em {categoria}/{subcategoria})?\nResponda 'Sim' ou 'Não'")
            return str(resp)
        except IndexError:
            resp.message("⚠️ ID inválido. Ex.: 'excluir #60fc'")
            return str(resp)

    # Relatórios
    if ("relatório" in mensagem or "resumo" in mensagem) and ("semanal" in mensagem or "semana" in mensagem):
        try:
            df_gastos, df_receitas, total_gastos, total_receitas, inicio_semana, fim_semana = gerar_relatorio_semanal(numero)
            inicio_str = inicio_semana.strftime("%d/%m/%Y")
            fim_str = fim_semana.strftime("%d/%m/%Y")
            
            report_text = f"📊 Relatório Semanal ({inicio_str} a {fim_str})\n\n"
            
            report_text += "🟢 Entradas\n\n"
            if not df_receitas.empty:
                categorias = df_receitas.groupby("categoria")
                for cat, grupo in categorias:
                    report_text += f"    💰 {cat}\n"
                    for _, row in grupo.iterrows():
                        subcat = row['subcategoria'] if row['subcategoria'] else "Geral"
                        report_text += f"        {subcat}: {row['valor_formatted']}\n"
            else:
                report_text += "    Nenhuma entrada registrada.\n"
            
            report_text += "\n🔴 Saídas\n\n"
            if not df_gastos.empty:
                categorias = df_gastos.groupby("categoria")
                for cat, grupo in categorias:
                    report_text += f"    💸 {cat}\n"
                    for _, row in grupo.iterrows():
                        subcat = row['subcategoria'] if row['subcategoria'] else "Geral"
                        report_text += f"        {subcat}: {row['valor_formatted']}\n"
            else:
                report_text += "    Nenhuma saída registrada.\n"
            
            saldo = total_receitas - total_gastos
            report_text += (f"\n       Total de Despesas: {formatar_valor(total_gastos)}\n"
                           f"       Total de Entradas: {formatar_valor(total_receitas)}\n"
                           f" 🏦 Saldo: {'-' if saldo < 0 else ''}{formatar_valor(abs(saldo))}")
            
            resp.message(report_text)
        except ValueError as e:
            resp.message(f"⚠️ {str(e)}")
        return str(resp)
    
    elif ("relatório" in mensagem or "resumo" in mensagem) and ("diário" in mensagem or "diario" in mensagem or "hoje" in mensagem or "do dia" in mensagem or mensagem == "resumo do dia"):
        try:
            logger.info(f"Gerando relatório diário para {numero}")
            df_gastos, df_receitas, total_gastos, total_receitas, inicio_dia, fim_dia = gerar_relatorio_diario(numero)
            data_str = inicio_dia.strftime("%d/%m/%Y")
            
            report_text = f"📊 Relatório Diário ({data_str})\n\n"
            
            report_text += "🟢 Entradas\n\n"
            if not df_receitas.empty:
                categorias = df_receitas.groupby("categoria")
                for cat, grupo in categorias:
                    report_text += f"    💰 {cat}\n"
                    for _, row in grupo.iterrows():
                        subcat = row['subcategoria'] if row['subcategoria'] else "Geral"
                        report_text += f"        {subcat}: {row['valor_formatted']}\n"
            else:
                report_text += "    Nenhuma entrada registrada.\n"
            
            report_text += "\n🔴 Saídas\n\n"
            if not df_gastos.empty:
                categorias = df_gastos.groupby("categoria")
                for cat, grupo in categorias:
                    report_text += f"    💸 {cat}\n"
                    for _, row in grupo.iterrows():
                        subcat = row['subcategoria'] if row['subcategoria'] else "Geral"
                        report_text += f"        {subcat}: {row['valor_formatted']}\n"
            else:
                report_text += "    Nenhuma saída registrada.\n"
            
            saldo = total_receitas - total_gastos
            report_text += (f"\n       Total de Despesas: {formatar_valor(total_gastos)}\n"
                           f"       Total de Entradas: {formatar_valor(total_receitas)}\n"
                           f" 🏦 Saldo: {'-' if saldo < 0 else ''}{formatar_valor(abs(saldo))}")
            
            logger.info(f"Enviando resposta ao WhatsApp: {report_text}")
            resp.message(report_text)
            logger.info(f"Resposta enviada com sucesso para {numero}")
        except ValueError as e:
            logger.error(f"Erro ao gerar relatório diário: {str(e)}")
            resp.message(f"⚠️ {str(e)}")
        except Exception as e:
            logger.error(f"Erro inesperado no relatório diário: {str(e)}")
            resp.message("⚠️ Erro interno ao gerar o relatório. Tente novamente.")
        return str(resp)
    
    elif "relatório" in mensagem or "resumo" in mensagem:
        try:
            mes = None
            for m in ["janeiro", "fevereiro", "março", "abril", "maio", "junho", 
                      "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]:
                if m in mensagem:
                    mes = m
                    break
            df_gastos, df_receitas, total_gastos, total_receitas, inicio_mes, fim_mes = gerar_relatorio_mensal(numero, mes=mes)
            inicio_str = inicio_mes.strftime("%d/%m/%Y")
            fim_str = fim_mes.strftime("%d/%m/%Y")
            mes_str = mes.capitalize() if mes else datetime.now().strftime("%B").capitalize()
            
            report_text = f"📊 Relatório Mensal de {mes_str} ({inicio_str} a {fim_str})\n\n"
            
            report_text += "🟢 Entradas\n\n"
            if not df_receitas.empty:
                categorias = df_receitas.groupby("categoria")
                for cat, grupo in categorias:
                    report_text += f"    💰 {cat}\n"
                    for _, row in grupo.iterrows():
                        subcat = row['subcategoria'] if row['subcategoria'] else "Geral"
                        report_text += f"        {subcat}: {row['valor_formatted']}\n"
            else:
                report_text += "    Nenhuma entrada registrada.\n"
            
            report_text += "\n🔴 Saídas\n\n"
            if not df_gastos.empty:
                categorias = df_gastos.groupby("categoria")
                for cat, grupo in categorias:
                    report_text += f"    💸 {cat}\n"
                    for _, row in grupo.iterrows():
                        subcat = row['subcategoria'] if row['subcategoria'] else "Geral"
                        report_text += f"        {subcat}: { row['valor_formatted']}\n"
            else:
                report_text += "    Nenhuma saída registrada.\n"
            
            saldo = total_receitas - total_gastos
            report_text += (f"\n       Total de Despesas: {formatar_valor(total_gastos)}\n"
                           f"       Total de Entradas: {formatar_valor(total_receitas)}\n"
                           f" 🏦 Saldo: {'-' if saldo < 0 else ''}{formatar_valor(abs(saldo))}")
            
            resp.message(report_text)
        except ValueError as e:
            resp.message(f"⚠️ {str(e)}")
        return str(resp)
    
    # Registro de Gastos e Receitas
    else:
        itens = processar_mensagem(mensagem)
        if itens:
            respostas = []
            for valor, categoria, subcategoria, data, tipo in itens:
                if tipo == "gasto":
                    id_registro = salvar_gasto(numero, valor, categoria, subcategoria, data, mensagem)
                    if id_registro:
                        total_gastos_hoje = calcular_gastos_hoje(numero)
                        subcat_str = f"/{subcategoria}" if subcategoria else ""
                        respostas.append(
                            f"📌 Gasto Registrado!\n"
                            f"🔹 Categoria: {categoria}{subcat_str}\n"
                            f"💰 Valor: {formatar_valor(valor)}\n"
                            f"📅 Data: {data.strftime('%d/%m/%Y')}\n"
                            f"📊 Total gasto hoje: {formatar_valor(total_gastos_hoje)}\n"
                            f"🆔 ID: {id_registro}\n\n"
                            f"📢 Para mais detalhes, digite \"Resumo do Dia\"."
                        )
                    else:
                        respostas.append("⚠️ Erro ao registrar gasto.")
                else:
                    id_registro = salvar_receita(numero, valor, categoria, subcategoria, data, mensagem)
                    if id_registro:
                        total_receitas_hoje = calcular_receitas_hoje(numero)
                        subcat_str = f"/{subcategoria}" if subcategoria else ""
                        respostas.append(
                            f"📌 Receita Registrada!\n"
                            f"🔹 Categoria: {categoria}{subcat_str}\n"
                            f"💰 Valor: {formatar_valor(valor)}\n"
                            f"📅 Data: {data.strftime('%d/%m/%Y')}\n"
                            f"📊 Total recebido hoje: {formatar_valor(total_receitas_hoje)}\n"
                            f"🆔 ID: {id_registro}\n\n"
                            f"📢 Para mais detalhes, digite \"Resumo do Dia\"."
                        )
                    else:
                        respostas.append("⚠️ Erro ao registrar receita.")
            resp.message("\n\n".join(respostas))
        else:
            resp.message("⚠️ Não entendi. Ex.: 'Gastei 50 em gasolina', 'Recebi 100 de salário', 'Excluir #60fc', 'Resumo semana'")
        return str(resp)

if __name__ == "__main__":
    criar_banco()
   app.run(host='0.0.0.0', port=5000, debug=True)
