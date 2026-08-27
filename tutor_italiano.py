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
PROMPT_CRIAR_DESAFIO = """
Você é um professor de italiano carismático e engajador da comunidade "Método Viare / Italiano na Prática".
Crie um desafio interativo, variado e envolvente para os alunos praticarem no grupo.

VARIE OS TIPOS DE DESAFIO (Escolha 1 estilo aleatoriamente a cada execução):
1. Situação do cotidiano na Itália (pedir algo no restaurante, farmácia, aeroporto, hotel, pedir informações).
2. Pergunta de conversação aberta (ex: "Raccontaci: qual è la tua città italiana preferita e perché?").
3. Desafio de tradução ou completar a frase (ex: frases úteis do dia a dia).
4. Falso amigo ou dica cultural com pergunta no final.

ESTRUTURA DA MENSAGEM:
- Título chamativo com emojis (ex: 🇮🇹 <b>Desafio do Dia!</b> 🇮🇹 ou ☕ <b>Momento Prática!</b> 🍕).
- O desafio ou pergunta bem explicada.
- Chamada para ação amigável convidando todos a responderem no grupo.
- FORMATO: Use EXCLUSIVAMENTE tags HTML (<b>, <i>). NUNCA use markdown com asteriscos.
- Máximo 5 a 6 linhas, direto ao ponto e motivador.
"""

def gerar_desafio_ia():
    """Gera um desafio inédito e criativo usando a IA."""
    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PROMPT_CRIAR_DESAFIO},
                {"role": "user", "content": "Crie um desafio inédito e criativo de italiano para a comunidade hoje."}
            ],
            max_tokens=300,
            temperature=0.9 # Alta criatividade para nunca repetir mensagens
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERRO OpenAI Desafio] {e}", flush=True)
        return (
            "🇮🇹 <b>Desafio do Dia!</b> 🇮🇹\n\n"
            "Como você diria em italiano: <i>'Muito prazer em conhecê-lo'</i>?\n\n"
            "💬 <i>Responda aqui no grupo para praticar!</i>"
        )

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
        print("[LOG] Desafio dinâmico enviado no tópico com sucesso!", flush=True)
    except Exception as e:
        print(f"[ERRO] Falha ao enviar mensagem diária: {e}", flush=True)

# 09:00, 13:00 e 18:00 de Brasília (12:00, 16:00 e 21:00 UTC)
schedule.every().day.at("12:00").do(enviar_frase_diaria)
schedule.every().day.at("16:00").do(enviar_frase_diaria)
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


