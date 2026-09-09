import os
import sys
import threading
import time
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI
import schedule

# Força o Python a mostrar os logs no Render em tempo real
sys.stdout.reconfigure(line_buffering=True)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot de Italiano rodando com sucesso!"

# ==========================================
# CONFIGURAÇÕES DE CHAVES E IDs
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

GRUPO_ID = '-1004415878695' 
LINK_DO_GRUPO = 'https://t.me/+_9bCJB4D8PBiODBk' # Seu link de convite
TOPICO_DESAFIOS_ID = 4 # ID do tópico Giornale

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# CÉREBRO 1: TUTOR DE CORREÇÃO EXAUSTIVA
# ==========================================
SYSTEM_PROMPT = """
Você é um professor e linguista nativo especialista em ensinar italiano para brasileiros.
Sua missão é analisar minuciosamente a mensagem do aluno e identificar TODOS os erros existentes.

REGRAS OBRIGATÓRIAS:
1. NÃO PARE NO PRIMEIRO ERRO: Analise a frase inteira de ponta a ponta. Se houver 2 ou mais erros na mesma mensagem (ex: "grazi mili" -> corrija "grazie" E "mille"; "io volere un pizza" -> corrija "vorrei" E "una"), liste TODOS os erros.
2. ANÁLISE CONTEXTUAL: Não avalie palavras soltas no dicionário. Analise o sentido da frase (ex: "Come estate" está errado para saudação -> o correto é "Come state?").
3. ERROS DE GRAFIA E PORTUNHOL: Corrija qualquer falso amigo ou erro de letra (ex: "grazi" -> "grazie", "mili" -> "mille", "funsiona" -> "funziona", "ciau" -> "ciao").
4. QUANDO RESPONDER APENAS "OK":
   - Se o italiano estiver 100% correto.
   - Se a mensagem for 100% uma conversa em português entre alunos (ex: "Gente, que horas é a aula?").
   - Mas se houver qualquer tentativa de italiano com erro, CORRIJA.

FORMATO DE RESPOSTA (Use estritamente este formato HTML):

❌ <b>Erro:</b> [trecho errado]
✅ <b>Correção:</b> [forma correta]
💡 <b>Dica:</b> [explicação curta de 1 linha em português]

(Se houver múltiplos erros, repita o bloco acima para cada erro individual).
"""

def checar_gramatica(texto_aluno):
    """Envia o texto para a OpenAI corrigir todos os erros."""
    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": texto_aluno}
            ],
            max_tokens=350, # Espaço para múltiplos erros sem cortar
            temperature=0.1
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERRO OpenAI Correção] {e}", flush=True)
        return "OK"

# ==========================================
# CÉREBRO 2: CRIADOR DE DESAFIOS DINÂMICOS
# ==========================================
ARQUIVO_HISTORICO = "historico_desafios.json"
# 1. Banco massivo de temas do cotidiano real (foge do clichê de pizza/gelato)
TEMAS_COTIDIANO = [
    # --- 🛒 COMPRAS E COMÉRCIO LOCAL ---
    "No supermercado (pesar frutas/legumes na balança, pegar sacola, passar no caixa)",
    "Na padaria / Forno italiano (pedir pão fresco por peso, fatias de focaccia, troco)",
    "Na salumeria / frios (pedir 'etti' de presunto, queijo ralado na hora, pedir para fatiar fino)",
    "Na feira de rua / Mercato rionale (perguntar se a fruta está madura, negociar quantidade)",
    "No açougue ou peixaria (pedir carne moída, pedir para limpar o peixe)",
    "Em lojas de roupas e calçados (perguntar se tem outro tamanho, provar no vestiário, liquidação 'saldi')",
    "Em lojas de eletrônicos ou bricolagem (comprar adaptador de tomada italiano, pilhas, lâmpada)",
    "Na tabaccheria (comprar bilhete de ônibus, recarga de celular, selo 'marca da bollo')",
    # --- 🏥 SAÚDE E CUIDADOS ---
    "Na farmácia (pedir remédio para dor de cabeça, curativo, pastilha de garganta, termômetro)",
    "No médico de família ou consulta (descrever sintomas simples, dor de estômago, febre)",
    "No dentista (descrever dor de dente, marcar uma limpeza ou retorno)",
    "No cabeleireiro ou barbearia (pedir para cortar só as pontas, aparar a barba, lavar o cabelo)",
    "Na ótica (ajustar óculos tortos, pedir líquido para lentes de contato)",
    # --- 🚆 TRANSPORTE E DESLOCAMENTO ---
    "Na estação de trem (usar a máquina de bilhetes, validar o bilhete 'convalidare', achar a plataforma)",
    "No ônibus ou bonde (perguntar se passa em determinado ponto, avisar que vai descer)",
    "No metrô (comprar passe diário, catraca que travou, qual linha pegar)",
    "No táxi ou transfer (dar o endereço com ponto de referência, perguntar quanto vai custar aproximadamente)",
    "No aeroporto (despacho de mala de mão, achar o portão de embarque, esteira de bagagens)",
    "No posto de gasolina (pedir 'self' ou 'servito', calibrar pneus, abastecer diesel ou gasolina)",
    "Aluguel de carro ou bicicleta (pedir cadeirinha de bebê, perguntar sobre o seguro e franquia)",
    "Estacionamento na rua (entender as faixas azuis/brancas, pagar no parquímetro)",
    # --- 🏠 CASA, CONDOMÍNIO E VIZINHANÇA ---
    "Com o vizinho de condomínio (cumprimentar no elevador, pedir para receber uma encomenda)",
    "Lixo e reciclagem (entender os dias da 'raccolta differenziata', onde jogar cada material)",
    "Problemas domésticos (chamar o encanador para vazamento, eletricista para queda de luz)",
    "Na lavanderia 'self-service' a moeda (comprar ficha 'gettone', escolher programa da secadora)",
    "Cozinhando em casa (pedir ajuda para cortar ingredientes, esquecer a panela no fogo)",
    "Faxina e organização (procurar a vassoura, pedir para tirar os sapatos ao entrar)",
    # --- ☕ COMIDA E SOCIAL (MUITO ALÉM DA PIZZA) ---
    "No bar italiano tomando café (pedir café 'al banco' vs 'al tavolo', pedir água com ou sem gás)",
    "Na trattoria tradicional (pedir mesa do lado de fora, pedir sugestão do dia, pedir a conta)",
    "Pizzaria 'al taglio' por pedaço (pedir para aquecer o pedaço 'me la scaldi?', escolher sabores)",
    "Restrições e preferências (avisar que não pode glúten, lactose ou pedir prato vegetariano)",
    "Aperitivo de fim de tarde (pedir petiscos, escolher a bebida, brindar 'Cin cin!')",
    # --- 💼 TRABALHO, ESTUDO E TECNOLOGIA ---
    "No escritório ou home office (avisar que a internet caiu, convidar colega para uma pausa pro café)",
    "E-mail profissional rápido (pedir desculpas pelo atraso em responder, anexar um documento)",
    "Na universidade ou curso (pedir anotações emprestadas, perguntar data de uma prova)",
    "Wi-Fi e tecnologia (pedir a senha do Wi-Fi, reclamar de celular descarregado, cabo emprestado)",
    # --- 🧳 VIAGENS, LAZER E HOTELARIA ---
    "No hotel ou Airbnb (avisar horário de chegada tarde, pedir toalha extra, senha da portaria)",
    "Na praia italiana / Stabilimento balneare (alugar guarda-sol e espreguiçadeira, perguntar da praia livre)",
    "Na montanha ou trilha (perguntar se o caminho é fácil, pedir um chocolate quente no refúgio)",
    "No museu ou atração turística (comprar ingresso com desconto de estudante/idoso, fila prioritária)",
    "No cinema ou teatro (escolher assento na plateia, perguntar se o filme é legendado)",
    # --- 📬 BUROCRACIA E SERVIÇOS DO DIA A DIA ---
    "Nos correios / Poste Italiane (retirar uma encomenda com aviso de chegada, mandar carta registrada)",
    "No banco ou caixa eletrônico / Bancomat (sacar dinheiro, cartão engolido pela máquina)",
    "Pedindo informações na rua (pedir para indicar onde fica a farmácia ou praça mais próxima)",
    # --- 🌦️ PERRENGUES, EMOÇÕES E CONVERSA FIADA ---
    "Falando sobre o clima (reclamar do calor abafado 'afa', chuva repentina sem guarda-chuva)",
    "Perrengues do dia (esquecer a chave dentro de casa, perder o ônibus)",
    "Desculpas sinceras e atrasos (trânsito pesado, despertador que não tocou, imprevisto)",
    "Marcando encontro com amigos (combinar horário na praça, decidir quem vai de carona)",
    "Fazendo elogios sinceros (elogiar a roupa de alguém, o corte de cabelo, uma comida gostosa)",
    "Expressões de surpresa, alívio e pressa ('Che peccato!', 'Meno male!', 'Ho una fretta tremenda!')"
]
# 2. Formatos variados de atividades
FORMATOS_ATIVIDADE = [
    {
        "tipo": "Tradução prática (PT -> IT)",
        "instrucao": "Dê uma frase útil e curta em português e peça aos alunos para traduzirem para o italiano."
    },
    {
        "tipo": "Crie sua frase (Palavra-chave)",
        "instrucao": "Dê 1 ou 2 palavras italianas muito úteis e desafie os alunos a criarem uma frase simples usando-as."
    },
    {
        "tipo": "Pergunta aberta de conversação",
        "instrucao": "Faça uma pergunta em italiano direta e curiosa sobre a vida/rotina deles para responderem no grupo."
    },
    {
        "tipo": "Como você diria? (Situação rápida)",
        "instrucao": "Apresente uma micro-situação real do dia a dia e pergunte como eles falariam aquilo em italiano."
    },
    {
        "tipo": "Caça ao erro ou complete a frase",
        "instrucao": "Apresente uma frase em italiano com um espaço pontilhado '_____' ou um erro comum simples para os alunos completarem ou corrigirem."
    },
    {
        "tipo": "Expressão idiomática ou gíria cotidiana",
        "instrucao": "Apresente uma expressão muito usada pelos italianos nativos e pergunte se sabem o que significa ou peça para usarem num exemplo."
    }
]
# 3. Níveis de dificuldade com pesos (70% Fácil, 25% Médio, 5% Desafio Curioso)
NIVEIS_DIFICULDADE = [
    {"nivel": "Fácil / Iniciante (A1-A2)", "peso": 70, "dica": "Frases curtas, vocabulário essencial, verbos comuns no presente."},
    {"nivel": "Médio / Intermediário (B1)", "peso": 25, "dica": "Conectar duas ideias curtas, passado recente (passato prossimo) ou dar uma opinião simples."},
    {"nivel": "Curiosidade / Expressão do Dia", "peso": 5, "dica": "Uma expressão do dia a dia ou falso amigo interessante, mas explicada de forma simples e acessível."}
]
FALLBACKS_VARIADOS = [
    "🇮🇹 <b>Desafio Relâmpago!</b> 🇮🇹\n\nComo você diria em italiano para o atendente do supermercado: <i>'Poderia me dar uma sacola, por favor?'</i>\n\n💬 <i>Mande sua resposta aqui no grupo!</i>",
    "☕ <b>Momento Prática!</b> 🍕\n\nQual destas opções significa <i>'Estou com pressa'</i>?\n1️⃣ Ho fame\n2️⃣ Ho fretta\n3️⃣ Ho freddo\n\n💬 <i>Responda com o número correto!</i>",
    "🇮🇹 <b>Pergunta do Dia!</b> 🇮🇹\n\n<i>Cosa fai di bello oggi?</i> (O que você vai fazer de bom hoje?)\n\n💬 <i>Escreva pelo menos uma frase simples em italiano aqui!</i>",
    "🎯 <b>Desafio de Vocabulário!</b> 🎯\n\nCrie uma frase simples em italiano usando a palavra <b>'Subito'</b> (imediatamente / logo)!\n\n💬 <i>Mostre sua frase aqui no grupo!</i>"
]
def carregar_historico():
    """Carrega os últimos tópicos abordados para evitar repetições."""
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []
def salvar_no_historico(resumo):
    """Guarda até 15 tópicos recentes."""
    historico = carregar_historico()
    historico.append(resumo)
    if len(historico) > 15:
        historico = historico[-15:]
    try:
        with open(ARQUIVO_HISTORICO, "w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AVISO] Não foi possível salvar histórico: {e}", flush=True)
def sortear_parametros():
    """Sorteia a combinação única do desafio de hoje."""
    # Sorteio ponderado para priorizar o nível mais fácil
    nivel_escolhido = random.choices(
        NIVEIS_DIFICULDADE,
        weights=[n["peso"] for n in NIVEIS_DIFICULDADE],
        k=1
    )[0]
    
    atividade_escolhida = random.choice(FORMATOS_ATIVIDADE)
    tema_escolhido = random.choice(TEMAS_COTIDIANO)
    
    return nivel_escolhido, atividade_escolhida, tema_escolhido
PROMPT_SISTEMA = """
Você é um professor de italiano dinâmico, moderno e muito carismático da comunidade "Método Viare / Italiano na Prática".
Seu objetivo é gerar micropílulas de prática diária que motivem até os alunos mais tímidos a participarem.
REGRAS DE FORMATAÇÃO E ESTILO:
1. FORMATO: Use EXCLUSIVAMENTE tags HTML (<b>, <i>, <code>). NUNCA use markdown (*, **, #).
2. TAMANHO: Curto e direto (máximo 4 a 6 linhas).
3. TOM: Encorajador, amigável e descontraído.
4. ESTRUTURA:
   - Título impactante com emojis (ex: 🇮🇹 <b>Desafio Prático!</b> 🇮🇹)
   - O desafio ou pergunta claramente explicada.
   - Chamada para ação final motivando todos a mandarem suas respostas no grupo.
5. ANTI-CLICHÊ: EVITE ficar sempre em pedir pizza ou pedir sorvete na gelateria. Use a vida real autêntica!
"""
def gerar_desafio_ia():
    """Gera um desafio inédito com parâmetros dinâmicos e controle de repetição."""
    nivel, atividade, tema = sortear_parametros()
    historico_recente = carregar_historico()
    evitar_texto = f"Evite temas parecidos com os recentes: {', '.join(historico_recente[-5:])}." if historico_recente else ""
    prompt_usuario = f"""
Crie um desafio inédito hoje seguindo estes parâmetros sorteados:
- Nível de Dificuldade: {nivel['nivel']} ({nivel['dica']})
- Tipo de Atividade: {atividade['tipo']} -> {atividade['instrucao']}
- Cenário do Cotidiano: {tema}
- {evitar_texto}
Garanta que seja fácil e convidativo para que iniciantes não tenham medo de tentar responder!
"""
    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": prompt_usuario}
            ],
            max_tokens=350,
            temperature=0.95  # Alta criatividade combinada com parâmetros dinâmicos
        )
        conteudo = resposta.choices[0].message.content.strip()
        
        # Salva o tema sorteado no histórico para nunca repetir em sequência
        salvar_no_historico(f"{atividade['tipo']} sobre {tema}")
        return conteudo
    except Exception as e:
        print(f"[ERRO OpenAI Desafio] {e}", flush=True)
        # Fallback randômico entre várias opções
        return random.choice(FALLBACKS_VARIADOS)
        
# ==========================================
# TAREFAS AGENDADAS (DESAFIOS DINÂMICOS)
# ==========================================
def enviar_frase_diaria():
    print("⏰ [AGENDADOR] Gerando novo desafio inédito com IA...", flush=True)
    frase_do_dia = gerar_desafio_ia()
    
    try:
        if TOPICO_DESAFIOS_ID:
            bot.send_message(GRUPO_ID, frase_do_dia, message_thread_id=TOPICO_DESAFIOS_ID, parse_mode="HTML")
        else:
            bot.send_message(GRUPO_ID, frase_do_dia, parse_mode="HTML")
        print("[LOG] Desafio dinâmico enviado com sucesso!", flush=True)
    except Exception as e:
        print(f"[ERRO] Falha ao enviar mensagem diária: {e}", flush=True)
# Horários configurados (09:00 e 18:00 de Brasília = 12:00 e 21:00 UTC)
schedule.every().day.at("12:00").do(enviar_frase_diaria)
schedule.every().day.at("21:00").do(enviar_frase_diaria)
def rodar_agendador():
    while True:
        schedule.run_pending()
        time.sleep(1)

# ==========================================
# OUVINTES NO PRIVADO
# ==========================================
@bot.message_handler(commands=['start'], func=lambda message: message.chat.type == 'private')
def dar_boas_vindas(message):
    markup = InlineKeyboardMarkup()
    botao_grupo = InlineKeyboardButton("Entrar na Comunidade 🇮🇹", url=LINK_DO_GRUPO)
    markup.add(botao_grupo)

    texto = (
        "Ciao! 👋 Eu sou o assistente do Método Italiano.\n\n"
        "Para começar a praticar e receber minhas correções, entre no nosso grupo oficial!\n\n"
        "👇 Clique no botão abaixo para entrar:"
    )
    bot.send_message(message.chat.id, texto, reply_markup=markup)

# Comando para você testar a geração do desafio a qualquer momento
@bot.message_handler(commands=['gerar_desafio'], func=lambda message: message.chat.type == 'private')
def testar_desafio_manual(message):
    bot.send_message(message.chat.id, "🤖 Gerando um desafio inédito com a IA e enviando no tópico Giornale...")
    enviar_frase_diaria()
    bot.send_message(message.chat.id, "✅ Desafio enviado!")

@bot.message_handler(func=lambda message: message.chat.type == 'private' and not message.text.startswith('/'))
def conversa_privada(message):
    bot.send_message(
        message.chat.id, 
        "💬 Eu fico observando as mensagens lá no <b>grupo da comunidade</b>! Vá lá interagir e, se tiver algum errinho de italiano na sua mensagem, eu te aviso aqui no privado. 😉",
        parse_mode="HTML"
    )

# ==========================================
# OUVINTE NO GRUPO (CORREÇÃO DE MENSAGENS)
# ==========================================
@bot.message_handler(content_types=['text'], func=lambda message: message.chat.type in ['group', 'supergroup'])
def monitorar_mensagens_grupo(message):
    nome = message.from_user.first_name if message.from_user else "Desconhecido"
    texto = message.text
    user_id = message.from_user.id if message.from_user else None

    print(f"\n🔔 [GRUPO] De: {nome} (ID: {user_id}) | Mensagem: '{texto}'", flush=True)

    if (message.from_user and message.from_user.is_bot) or message.sender_chat is not None:
        return
        
    if texto.startswith('/'):
        return

    correcao = checar_gramatica(texto)
    print(f"🔍 [IA] Resposta:\n{correcao}", flush=True)

    if correcao.strip().upper() not in ["OK", "OK.", "OK!"]:
        try:
            bot.send_message(
                chat_id=user_id,
                text=f"📌 <b>Ajuste na sua mensagem enviada no grupo:</b>\n\n{correcao}",
                parse_mode="HTML"
            )
            print(f"✅ [SUCESSO] Correção enviada para {nome}!", flush=True)
        except Exception as e:
            print(f"❌ [ERRO] Falha ao enviar no privado: {e}", flush=True)

# ==========================================
# INICIAR O SERVIÇO
# ==========================================
def run_bot():
    print("⏳ Aguardando 10 segundos para iniciar...", flush=True)
    time.sleep(10)
    try:
        bot.remove_webhook()
    except Exception:
        pass
    
    print("🤖 Bot conectado e escutando!", flush=True)
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60, allowed_updates=['message', 'edited_message'])
        except Exception as e:
            print(f"⚠️ [Reconectando]: {e}", flush=True)
            time.sleep(10)

if __name__ == '__main__':
    thread_agendador = threading.Thread(target=rodar_agendador, daemon=True)
    thread_agendador.start()

    thread_bot = threading.Thread(target=run_bot, daemon=True)
    thread_bot.start()

    porta_render = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=porta_render)


