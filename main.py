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
    return "Bilel Accurate Bot - Fixed"

def get_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_accurate():
    try:
        spx = yf.Ticker("^GSPC")
        data = spx.history(period="1d", interval="5m")
        if data.empty:
            return "⛔ السوق مقفل"
        last = float(data['Close'].iloc[-1])
        open_p = float(data['Open'].iloc[0])
        data['Typical'] = (data['High']+data['Low']+data['Close'])/3
        data['PV'] = data['Typical']*data['Volume']
        vwap = float(data['PV'].sum()/data['Volume'].sum())
        ema20 = float(data['Close'].ewm(span=20).mean().iloc[-1])
        ema50 = float(data['Close'].ewm(span=50).mean().iloc[-1])
        rsi = float(get_rsi(data['Close']).iloc[-1])
        vix = float(yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1])

        call_pts=0
        put_pts=0
        reasons=[]

        if last > vwap:
            call_pts+=2
            reasons.append(f"✅ فوق VWAP {vwap:.0f}")
        else:
            put_pts+=2
            reasons.append(f"❌ تحت VWAP {vwap:.0f}")

        if last > open_p:
            call_pts+=2
            reasons.append(f"✅ فوق الافتتاح {open_p:.0f}")
        else:
            put_pts+=2
            reasons.append(f"❌ تحت الافتتاح {open_p:.0f}")

        if ema20 > ema50: 
            call_pts+=1
            reasons.append("✅ EMA20>EMA50")
        else:
            put_pts+=1
            reasons.append("❌ EMA20<EMA50")

        if rsi>55:
            call_pts+=1
            reasons.append(f"✅ RSI {rsi:.0f} قوي")
        elif rsi<45:
            put_pts+=1
            reasons.append(f"❌ RSI {rsi:.0f} ضعيف")

        if call_pts>=4:
            dec="🟢 CALL فقط - شراء"
            conf=f"{int(call_pts/(call_pts+put_pts)*100)}% CALL"
            strike=f"CALL {round(last+5)} الى {round(last+20)}"
        elif put_pts>=4:
            dec="🔴 PUT فقط - بيع"
            conf=f"{int(put_pts/(call_pts+put_pts)*100)}% PUT"
            strike=f"PUT {round(last-20)} الى {round(last-5)}"
        else:
            dec="🟡 لا تدخل - متذبذب"
            conf="50/50"
            strike="انتظر"

        txt="\n".join(reasons)
        return f"""🔥 **قراءة دقيقة SPX {last:.2f}**

{txt}

━━━━━━━━
💡 القرار: {dec}
📊 الثقة: {conf}
🎯 العقد: {strike}
😨 VIX: {vix:.1f}
⚠️ 1-2% فقط
"""
    except Exception as e:
        return f"خطأ: {e}"

@bot.message_handler(commands=['start','market','spx'])
def handle(m):
    bot.send_message(m.chat.id, "⏳ بحلل بدقة عالية...")
    bot.send_message(m.chat.id, get_accurate(), parse_mode="Markdown")

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.infinity_polling()
