import os
import threading
import time
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI
import schedule

# 1. Cria o aplicativo do Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot está rodando com sucesso!"

# ==========================================
# CONFIGURAÇÕES DE CHAVES E IDs
# ==========================================
# Substitua pelas suas chaves ou use as variáveis de ambiente do Render
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8913417725:AAHK9QH9Qke6h6BrU3cFwAa5yx5qlvHo-XY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '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')

# ID do seu grupo e link de convite
GRUPO_ID = '-1004415878695' 
LINK_DO_GRUPO = 'https://t.me/+_9bCJB4D8PBiODBk'
TOPICO_DESAFIOS_ID = None 

# Inicializa o Bot e a OpenAI
bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# CÉREBRO DA IA - PROMPT E FUNÇÃO DE CHECAGEM
# ==========================================
SYSTEM_PROMPT = """
Você é um tutor de italiano. Analise o texto enviado.
- Se o texto estiver correto em italiano, ou se for apenas uma conversa em português que não precisa de correção, responda APENAS: OK
- Se houver erros em italiano, aponte-os de forma concisa usando estritamente o formato HTML abaixo:

❌ <b>Erro:</b> [palavra ou trecho curto errado]
✅ <b>Correção:</b> [forma correta]
💡 <b>Dica:</b> [regra explicada em no máximo 1 linha]

(Se houver mais de um erro, repita o formato acima. Sem textos extras).
"""

def checar_gramatica(texto_aluno):
    """Envia o texto para a OpenAI e retorna a correção."""
    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": texto_aluno}
            ],
            max_tokens=150,
            temperature=0.1
        )
        return resposta.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERRO OpenAI] Falha ao consultar a API: {e}")
        return "OK"

# ==========================================
# TAREFAS AGENDADAS (MENSAGEM DIÁRIA)
# ==========================================
def enviar_frase_diaria():
    """Função que envia o desafio do dia no grupo."""
    frase_do_dia = (
        "🇮🇹 <b>Desafio do Dia!</b> 🇮🇹\n\n"
        "Como você diria: <i>'Eu gostaria de um café, por favor'</i> em italiano?\n\n"
        "Responda aqui para praticar!"
    )
    
    try:
        if TOPICO_DESAFIOS_ID:
            bot.send_message(GRUPO_ID, frase_do_dia, message_thread_id=TOPICO_DESAFIOS_ID, parse_mode="HTML")
        else:
            bot.send_message(GRUPO_ID, frase_do_dia, parse_mode="HTML")
        print("[LOG] Mensagem diária enviada com sucesso!")
    except Exception as e:
        print(f"[ERRO] Não foi possível enviar a mensagem diária: {e}")

# Horários das mensagens diárias
schedule.every().day.at("09:00").do(enviar_frase_diaria)
schedule.every().day.at("18:00").do(enviar_frase_diaria)

def rodar_agendador():
    """Roda em segundo plano para o schedule funcionar."""
    while True:
        schedule.run_pending()
        time.sleep(1)

# ==========================================
# OUVINTE DE MENSAGENS NO PRIVADO (ONBOARDING)
# ==========================================
@bot.message_handler(commands=['start'], func=lambda message: message.chat.type == 'private')
def dar_boas_vindas(message):
    markup = InlineKeyboardMarkup()
    botao_grupo = InlineKeyboardButton("Entrar na Comunidade 🇮🇹", url=LINK_DO_GRUPO)
    markup.add(botao_grupo)

    texto = (
        "Ciao! 👋 Eu sou o assistente do Método Italiano.\n\n"
        "Para começar a praticar e receber minhas correções, você precisa entrar no nosso grupo oficial!\n\n"
        "👇 Clique no botão abaixo para entrar:"
    )
    bot.send_message(message.chat.id, texto, reply_markup=markup)

@bot.message_handler(func=lambda message: message.chat.type == 'private' and not message.text.startswith('/'))
def conversa_privada(message):
    bot.send_message(
        message.chat.id, 
        "💬 Eu fico observando as mensagens lá no <b>grupo da comunidade</b>! Vá lá praticar e, se tiver algum errinho de italiano, eu te aviso aqui no privado. 😉",
        parse_mode="HTML"
    )

# ==========================================
# OUVINTE DE MENSAGENS NO GRUPO (CORREÇÃO)
# ==========================================
@bot.message_handler(content_types=['text'], func=lambda message: message.chat.type in ['group', 'supergroup'])
def monitorar_mensagens_grupo(message):
    # 1. Ignora bots e admins anônimos
    if (message.from_user and message.from_user.is_bot) or message.sender_chat is not None:
        return
        
    texto = message.text
    user_id = message.from_user.id
    nome = message.from_user.first_name
    
    # 2. Ignora comandos de barra (ex: /start, /help)
    if texto.startswith('/'):
        return

    print(f"📩 [GRUPO] Mensagem de {nome}: '{texto}'")

    # 3. Chama a IA para checar o texto
    correcao = checar_gramatica(texto)
    print(f"🔍 [IA] Resposta: {repr(correcao)}")

    # 4. Se houver correção necessária, envia no privado do aluno
    if correcao.strip().upper() not in ["OK", "OK.", "OK!"]:
        try:
            bot.send_message(
                chat_id=user_id,
                text=f"📌 <b>Ajuste na sua mensagem enviada no grupo:</b>\n\n{correcao}",
                parse_mode="HTML"
            )
            print(f"✅ [SUCESSO] Correção enviada para {nome} (ID: {user_id})")
        except Exception as e:
            print(f"❌ [ERRO] Falha ao enviar para {nome}: {e}")

# ==========================================
# INICIALIZAÇÃO DO BOT
# ==========================================
def run_bot():
    print("⏳ Aguardando 5 segundos antes de iniciar o bot...")
    time.sleep(5)
    
    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"[AVISO] Webhook: {e}")
    
    print("🤖 Bot do Telegram iniciado e escutando mensagens!")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"[ERRO] Polling caiu: {e}")
            time.sleep(10)

if __name__ == '__main__':
    # 1. Thread do agendador
    thread_agendador = threading.Thread(target=rodar_agendador, daemon=True)
    thread_agendador.start()

    # 2. Thread do Telegram Bot
    thread_bot = threading.Thread(target=run_bot, daemon=True)
    thread_bot.start()

    # 3. Servidor Web Flask (para o Render manter o serviço ativo)
    porta_render = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=porta_render)
