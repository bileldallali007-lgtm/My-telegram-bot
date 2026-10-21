import yfinance as yf
import telebot
import os
from flask import Flask
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "Bilel 0DTE Bot Live"

def get_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_0dte_analysis():
    try:
        spx = yf.Ticker("^GSPC")
        data = spx.history(period="2d", interval="5m")
        if data.empty:
            return "⛔ السوق مقفل - جرب وقت الافتتاح 4:30 عصراً بتوقيت الرياض"
        last_price = float(data['Close'].iloc[-1])
        data['Typical'] = (data['High'] + data['Low'] + data['Close']) / 3
        data['PV'] = data['Typical'] * data['Volume']
        vwap = float(data['PV'].tail(78).sum() / data['Volume'].tail(78).sum())
        ema20 = float(data['Close'].ewm(span=20).mean().iloc[-1])
        rsi = float(get_rsi(data['Close']).iloc[-1])
        vix = float(yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1])

        score = 0
        if last_price > vwap: score += 1
        else: score -= 1
        if last_price > ema20: score += 1
        else: score -= 1
        if rsi > 52: score += 1
        elif rsi < 48: score -= 1
        if vix < 16: score += 1
        else: score -= 1

        if score >= 2:
            trend = "📈 صاعد قوي - يوم CALL فقط"
            suggestion = f"CALL {round(last_price+10)} الى {round(last_price+25)}"
            plan = f"استنى هبوط لـ {vwap:.0f} وادخل CALL"
            color = "🟢"
        elif score <= -2:
            trend = "📉 هابط قوي - يوم PUT فقط"
            suggestion = f"PUT {round(last_price-25)} الى {round(last_price-10)}"
            plan = f"استنى صعود لـ {vwap:.0f} وادخل PUT"
            color = "🔴"
        else:
            trend = "⚖️ متذبذب - لا تدخل 0DTE"
            suggestion = "انتظر كسر واضح"
            plan = "احفظ فلوسك"
            color = "🟡"

        return f"""{color} **تقرير 0DTE - SPX**
📊 السعر: {last_price:.2f}
📍 VWAP: {vwap:.2f}
📈 EMA20: {ema20:.2f}
📊 RSI: {rsi:.1f}
😨 VIX: {vix:.2f}

💡 {trend}
🎯 العقد: {suggestion}
📝 الخطة: {plan}
⏰ 0DTE اليوم فقط
⚠️ 1-2% فقط
"""
    except Exception as e:
        return f"خطأ: {e}"

@bot.message_handler(commands=['start'])
def start_cmd(m):
    bot.send_message(m.chat.id, "أهلا بلال! 🔥\nبوت 0DTE جاهز\n\n/market - تحليل السوق الآن")

@bot.message_handler(commands=['market'])
def market_cmd(m):
    bot.send_message(m.chat.id, "⏳ بحلل السوق...")
    bot.send_message(m.chat.id, get_0dte_analysis(), parse_mode="Markdown")

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
