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
TELEGRAM_TOKEN = '8913417725:AAHahvz5btb2Oyl1Pt_bjlDadQKnLhubX_w'
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
# CÉREBRO DA IA - PROMPT DO PROFESSOR (ULTRA OTIMIZADO)
# ==========================================
SYSTEM_PROMPT = """
Corrija o italiano da mensagem. Se estiver correta, responda APENAS "OK".
Se houver erros, liste-os de forma EXTREMAMENTE concisa usando EXATAMENTE o formato abaixo.

❌ **Erro:** [Apenas a palavra ou trecho curto errado]
✅ **Correção:** [Apenas a forma correta correspondente]
💡 **Dica:** [Explicação da regra em no máximo 1 linha]

(Se houver mais de um erro na mesma frase, repita o bloco acima para cada erro. Não adicione saudações ou textos extras).
"""

def checar_gramatica(texto_aluno):
    """Envia o texto para a OpenAI com foco total em economia de tokens."""
    try:
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": texto_aluno}
            ],
            max_tokens=150, # Reduzido ainda mais, pois agora a saída é curtíssima
            temperature=0.1 # Mantém a IA focada e sem enrolação
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
# OUVINTE DE MENSAGENS NO PRIVADO (ONBOARDING)
# ==========================================
@bot.message_handler(commands=['start'], func=lambda message: message.chat.type == 'private')
def dar_boas_vindas(message):
    # Cria o botão de acesso ao grupo
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
        "💬 Eu fico apenas observando as conversas lá no **grupo da comunidade**! Vá lá interagir com o pessoal e, se tiver algum errinho de italiano na sua mensagem, eu te dou um toque por aqui. 😉",
        parse_mode="Markdown"
    )

# ==========================================
# OUVINTE DE MENSAGENS NO GRUPO (CORREÇÃO)
# ==========================================
@bot.message_handler(content_types=['text'], func=lambda message: message.chat.type in ['group', 'supergroup'])
def monitorar_mensagens_grupo(message):
    # 🛡️ Ignora bots (inclusive ele mesmo) e admins que enviam mensagens anonimamente
    if message.from_user.is_bot or message.sender_chat is not None:
        return
        
    texto = message.text
    user_id = message.from_user.id
    
    # Ignora comandos de barra (ex: /start, /help) enviados no grupo
    if texto.startswith('/'):
        return

    # Manda a mensagem do aluno para a IA analisar
    correcao = checar_gramatica(texto)

    # Se a IA não responder "OK", significa que ela encontrou erros e gerou o texto de correção
    if correcao != "OK":
        try:
            bot.send_message(
                chat_id=user_id,
                text=f"📌 **Ajuste na sua mensagem enviada no grupo:**\n\n{correcao}",
                parse_mode="Markdown"
            )
            print(f"[LOG] Correção enviada para {message.from_user.first_name}.")
        except Exception as e:
            print(f"[ERRO] Falha ao enviar para {message.from_user.first_name}. O usuário possivelmente não iniciou o bot. Erro: {e}")

# ==========================================
# INICIAR O BOT, O AGENDADOR E O FLASK
# ==========================================
def run_bot():
    print("🤖 Bot do Telegram iniciado!")
    bot.infinity_polling()

if __name__ == '__main__':
    # 1. Inicia o agendador em uma thread paralela
    thread_agendador = threading.Thread(target=rodar_agendador, daemon=True)
    thread_agendador.start()

    # 2. Inicia o bot do Telegram em outra thread paralela
    thread_bot = threading.Thread(target=run_bot, daemon=True)
    thread_bot.start()

    print("🌐 Servidor web do Flask iniciando para o Render...")
    # 3. O Flask roda no fluxo principal (mantendo a porta 10000 aberta para o Render)
    app.run(host='0.0.0.0', port=10000)