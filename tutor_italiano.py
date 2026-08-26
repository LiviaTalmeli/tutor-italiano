import os
import sys
import threading
import time
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from openai import OpenAI
import schedule

# Força o Python a mostrar TODOS os prints imediatamente no Render (sem travar em buffer)
sys.stdout.reconfigure(line_buffering=True)

# 1. Cria o aplicativo do Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot está rodando com sucesso!"

# ==========================================
# CONFIGURAÇÕES DE CHAVES E IDs
# ==========================================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '8913417725:AAHK9QH9Qke6h6BrU3cFwAa5yx5qlvHo-XY')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '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')

GRUPO_ID = '-1004415878695' 
LINK_DO_GRUPO = 'https://t.me/+_9bCJB4D8PBiODBk'
TOPICO_DESAFIOS_ID = None 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# CÉREBRO DA IA (HTML)
# ==========================================
SYSTEM_PROMPT = """
Você é um tutor de italiano. Analise o texto enviado.
- Se o texto estiver correto em italiano, ou se for apenas uma conversa em português que não precisa de correção, responda APENAS: OK
- Se houver erros em italiano, aponte-os usando EXATAMENTE a estrutura HTML abaixo:

❌ <b>Erro:</b> [trecho errado]
✅ <b>Correção:</b> [forma correta]
💡 <b>Dica:</b> [regra curta em 1 linha]
"""

def checar_gramatica(texto_aluno):
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
        print(f"[ERRO OpenAI] Falha na API: {e}", flush=True)
        return "OK"

# ==========================================
# TAREFAS AGENDADAS
# ==========================================
def enviar_frase_diaria():
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
        print("[LOG] Mensagem diária enviada com sucesso!", flush=True)
    except Exception as e:
        print(f"[ERRO] Falha ao enviar mensagem diária: {e}", flush=True)

schedule.every().day.at("09:00").do(enviar_frase_diaria)
schedule.every().day.at("18:00").do(enviar_frase_diaria)

def rodar_agendador():
    while True:
        schedule.run_pending()
        time.sleep(1)

# ==========================================
# OUVINTE NO PRIVADO
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
        "💬 Eu fico observando as mensagens lá no <b>grupo da comunidade</b>! Vá lá interagir e, se tiver algum errinho de italiano na sua mensagem, eu te aviso aqui no privado. 😉",
        parse_mode="HTML"
    )

# ==========================================
# OUVINTE GLOBAL NO GRUPO (COM LOGS IMEDIATOS)
# ==========================================
@bot.message_handler(content_types=['text'], func=lambda message: message.chat.type in ['group', 'supergroup'])
def monitorar_mensagens_grupo(message):
    nome = message.from_user.first_name if message.from_user else "Desconhecido"
    texto = message.text
    user_id = message.from_user.id if message.from_user else None

    # ESTE PRINT VAI APARECER NO RENDER NO MESMO SEGUNDO
    print(f"\n🔔 [CHEGOU NO GRUPO] De: {nome} (ID: {user_id}) | Chat: {message.chat.title} ({message.chat.id}) | Texto: '{texto}'", flush=True)

    # 1. Ignora bots
    if message.from_user and message.from_user.is_bot:
        print("⏩ [IGNORADO] Mensagem enviada por bot.", flush=True)
        return

    # 2. Verifica se é admin anônimo
    if message.sender_chat is not None and user_id is None:
        print("⚠️ [AVISO] Mensagem enviada como Anônimo/Canal. O bot não tem o ID privado para responder.", flush=True)
        return
        
    # 3. Ignora comandos
    if texto.startswith('/'):
        print("⏩ [IGNORADO] Comando de barra.", flush=True)
        return

    print("🤖 [IA] Enviando para OpenAI analisar...", flush=True)
    correcao = checar_gramatica(texto)
    print(f"🔍 [IA] Resposta da OpenAI: {repr(correcao)}", flush=True)

    # 4. Envia no privado se houver correção
    if correcao.strip().upper() not in ["OK", "OK.", "OK!"]:
        print(f"📤 [TELEGRAM] Enviando correção para o privado de {nome} (ID: {user_id})...", flush=True)
        try:
            bot.send_message(
                chat_id=user_id,
                text=f"📌 <b>Ajuste na sua mensagem enviada no grupo:</b>\n\n{correcao}",
                parse_mode="HTML"
            )
            print(f"✅ [SUCESSO] Correção entregue no privado de {nome}!", flush=True)
        except Exception as e:
            print(f"❌ [ERRO AO ENVIAR NO PRIVADO] Motivo: {e}", flush=True)
    else:
        print("ℹ️ [IA] Nenhuma correção necessária (resposta foi OK).", flush=True)

# ==========================================
# INICIAR O BOT
# ==========================================
def run_bot():
    print("⏳ Aguardando 5 segundos para limpar conexões antigas...", flush=True)
    time.sleep(5)
    try:
        bot.remove_webhook()
    except Exception:
        pass
    
    print("🤖 Bot conectado via Polling e pronto para escutar o grupo!", flush=True)
    while True:
        try:
            # allowed_updates garante que o Telegram mande mensagens de grupos
            bot.infinity_polling(timeout=60, long_polling_timeout=60, allowed_updates=['message', 'edited_message'])
        except Exception as e:
            print(f"[ERRO Polling] {e}", flush=True)
            time.sleep(10)

if __name__ == '__main__':
    thread_agendador = threading.Thread(target=rodar_agendador, daemon=True)
    thread_agendador.start()

    thread_bot = threading.Thread(target=run_bot, daemon=True)
    thread_bot.start()

    porta_render = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=porta_render)


    # 3. Servidor Web Flask (para o Render manter o serviço ativo)
    porta_render = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=porta_render)
