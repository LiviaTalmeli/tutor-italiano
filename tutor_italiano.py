import os
from flask import Flask
import threading
# ... (os outros imports do seu bot, como telebot, openai, etc.)
import telebot
from openai import OpenAI
import schedule
import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 1. Cria o aplicativo do Flask aqui em cima
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot está rodando!"

# ==========================================
# CONFIGURAÇÕES DE CHAVES E IDs
# ==========================================
# Lembre-se: use chaves NOVAS e nunca as compartilhe publicamente!
TELEGRAM_TOKEN = '8913417725:AAHK9QH9Qke6h6BrU3cFwAa5yx5qlvHo-XY'
OPENAI_API_KEY = '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'

# ID do seu grupo (Para o bot mandar a mensagem diária)
GRUPO_ID = '-1004415878695' 

# Link de convite do seu grupo
LINK_DO_GRUPO = 'https://t.me/+_9bCJB4D8PBiODBk'

# Se o grupo usar Tópicos, coloque o ID do tópico aqui (ex: 1234). Se não usar, deixe None.
TOPICO_DESAFIOS_ID = None 

bot = telebot.TeleBot(TELEGRAM_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================================
# CÉREBRO DA IA (Ajustado para HTML seguro)
# ==========================================
SYSTEM_PROMPT = """
Você é um professor de italiano. Analise a mensagem enviada.
- Se a mensagem estiver em italiano correto OU se for apenas uma saudação/conversa que não precisa de correção, responda APENAS: OK
- Se houver erros em italiano, aponte-os usando EXATAMENTE a estrutura HTML abaixo:

❌ <b>Erro:</b> [trecho errado]
✅ <b>Correção:</b> [forma correta]
💡 <b>Dica:</b> [explicação curta de 1 linha]
"""

# ==========================================
# OUVINTE DE MENSAGENS NO GRUPO COM LOGS DETALHADOS
# ==========================================
@bot.message_handler(content_types=['text'], func=lambda message: message.chat.type in ['group', 'supergroup'])
def monitorar_mensagens_grupo(message):
    nome = message.from_user.first_name if message.from_user else "Desconhecido"
    texto = message.text

    print(f"\n📩 [NOVA MENSAGEM NO GRUPO] De: {nome} | Texto: '{texto}'")

    # 1. Verifica se é bot
    if message.from_user and message.from_user.is_bot:
        print("⏩ Ignorado: Enviado por um bot.")
        return

    # 2. Verifica se é admin anônimo
    if message.sender_chat is not None:
        print("⚠️ Ignorado: Enviado como Admin Anônimo ou Canal. Desative 'Permanecer Anônimo' para testar.")
        return
        
    user_id = message.from_user.id
    
    # 3. Ignora comandos
    if texto.startswith('/'):
        print("⏩ Ignorado: É um comando com /.")
        return

    print("🤖 Consultando a OpenAI...")
    correcao = checar_gramatica(texto)
    print(f"🔍 Resposta da OpenAI: {repr(correcao)}")

    # 4. Verifica se a IA encontrou erro
    if correcao.strip().upper() not in ["OK", "OK.", "OK!"]:
        print(f"📤 Tentando enviar correção no privado para {nome} (ID: {user_id})...")
        try:
            bot.send_message(
                chat_id=user_id,
                text=f"📌 <b>Ajuste na sua mensagem enviada no grupo:</b>\n\n{correcao}",
                parse_mode="HTML"
            )
            print(f"✅ SUCESSO: Correção entregue no privado de {nome}!")
        except Exception as e:
            print(f"❌ ERRO ao enviar mensagem no privado: {e}")
    else:
        print("ℹ️ Nenhuma correção necessária (IA respondeu OK).")

# ==========================================
# TAREFAS AGENDADAS (MENSAGEM DIÁRIA)
# ==========================================
def enviar_frase_diaria():
    """Função que envia o desafio do dia no grupo."""
    frase_do_dia = (
        "🇮🇹 **Desafio do Dia!** 🇮🇹\n\n"
        "Como você diria: *'Eu gostaria de um café, por favor'* em italiano?\n\n"
        "Responda aqui para praticar!"
    )
    
    try:
        if TOPICO_DESAFIOS_ID:
            bot.send_message(GRUPO_ID, frase_do_dia, message_thread_id=TOPICO_DESAFIOS_ID, parse_mode="Markdown")
        else:
            bot.send_message(GRUPO_ID, frase_do_dia, parse_mode="Markdown")
        print("[LOG] Mensagem diária enviada com sucesso!")
    except Exception as e:
        print(f"[ERRO] Não foi possível enviar a mensagem diária: {e}")

# Configura os horários que o bot vai mandar a mensagem (formato 24h)
schedule.every().day.at("09:00").do(enviar_frase_diaria)
schedule.every().day.at("18:00").do(enviar_frase_diaria)

def rodar_agendador():
    """Roda em segundo plano para o schedule funcionar sem travar o bot."""
    while True:
        schedule.run_pending()
        time.sleep(1)

# ==========================================
# INICIAR O BOT, O AGENDADOR E O FLASK
# ==========================================
def run_bot():
    print("⏳ Aguardando 15 segundos antes de iniciar o bot para evitar Erro 409 no Render...")
    time.sleep(15) # Dá tempo para a instância antiga ser desligada
    
    print("🤖 Bot do Telegram iniciando!")
    try:
        # Força a remoção de qualquer webhook travado que esteja causando o erro 409
        bot.remove_webhook()
    except Exception as e:
        print(f"[AVISO] Não foi possível remover o webhook: {e}")
    
    # Inicia o polling. Se houver erro de conexão, ele aguarda e tenta de novo
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"[ERRO] A conexão caiu ou houve conflito: {e}")
            print("🔄 Tentando reconectar em 10 segundos...")
            time.sleep(10)

if __name__ == '__main__':
    # 1. Inicia o agendador em uma thread paralela
    thread_agendador = threading.Thread(target=rodar_agendador, daemon=True)
    thread_agendador.start()

    # 2. Inicia o bot do Telegram em outra thread paralela
    thread_bot = threading.Thread(target=run_bot, daemon=True)
    thread_bot.start()

    print("🌐 Servidor web do Flask iniciando para o Render...")
    # 3. O Flask roda no fluxo principal pegando a porta do Render
    porta_render = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=porta_render)
