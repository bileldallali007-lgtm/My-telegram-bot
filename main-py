import telebot
import threading
import os
from flask import Flask

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "البوت شغال على Render 24/24 ✅")

@bot.message_handler(commands=['myid'])
def myid(message):
    bot.reply_to(message, f"ID: {message.from_user.id}")

@app.route('/')
def home():
    return "Bot is running!"

def run_bot():
    bot.infinity_polling()

threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
