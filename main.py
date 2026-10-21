import yfinance as yf
import telebot
import os
from flask import Flask
import threading
import time
from datetime import datetime
import pytz

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

SUBSCRIBERS = set()
RIYADH_TZ = pytz.timezone('Asia/Riyadh')

@app.route('/')
def home():
    return "Bilel Accurate 0DTE Bot"

def get_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_accurate_analysis():
    try:
        # نفس مؤشرك SPX 7712
        spx = yf.Ticker("^GSPC")
        data_5m = spx.history(period="1d", interval="5m")
        data_15m = spx.history(period="5d", interval="15m")
        
        if data_5m.empty:
            return "⛔ السوق مقفل - اكتب /market وقت الافتتاح 4:30 عصراً"
        
        last = float(data_5m['Close'].iloc[-1])
        open_price = float(data_5m['Open'].iloc[0])
        
        # 1. VWAP اليوم
        data_5m['Typical'] = (data_5m['High']+data_5m['Low']+data_5m['Close'])/3
        data_5m['PV'] = data_5m['Typical']*data_5m['Volume']
        vwap = float(data_5m['PV'].sum()/data_5m['Volume'].sum())
        
        # 2. EMA 20 و 50 على 5 دقايق
        ema20 = float(data_5m['Close'].ewm(span=20).mean().iloc[-1])
        ema50 = float(data_5m['Close'].ewm(span=50).mean().iloc[-1])
        
        # 3. EMA 20 على 15 دقيقة (الترند الكبير)
        ema20_15m = float(data_15m['Close'].ewm(span=20).mean().iloc[-1])
        
        # 4. RSI
        rsi = float(get_rsi(data_5m['Close']).iloc[-1])
        
        # 5. VIX
        vix = float(yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1])

        # === نظام النقاط المحترف ===
        call_points = 0
        put_points = 0
        reasons = []

        # VWAP (أهم حاجة في 0DTE)
        if last > vwap:
            call_points += 2
            reasons.append("✅ فوق VWAP")
        else:
            put_points += 2
            reasons.append("❌ تحت VWAP")

        # سعر الافتتاح
        if last > open_price:
            call_points += 2
            reasons.append(f"✅ فوق الافتتاح {open_price:.0f}")
        else:
            put_points += 2
            reasons.append(f"❌ تحت الافتتاح {open_price:.0f}")

        # EMA 20/50
        if ema20 > ema50 and last > ema20:
            call_points += 1
            reasons.append("✅ EMA20 فوق EMA50")
        elif ema20 < ema50 and last < ema20:
            put_points += 1
            reasons.append("❌ EMA20 تحت EMA50")

        # الترند الكبير 15م
        if last > ema20_15m:
            call_points += 1
            reasons.append("✅ ترند 15د صاعد")
        else:
            put_points += 1
            reasons.append("❌ ترند 15د هابط")

        # RSI
        if rsi > 55:
            call_points += 1
            reasons.append(f"✅ RSI قوي {rsi:.0f}")
        elif rsi < 45:
            put_points += 1
            reasons.append(f"❌ RSI ضعيف {rsi:.0f}")
        else:
            reasons.append(f"⚠️ RSI متذبذب {rsi:.0f}")

        # VIX
        if vix > 20:
            reasons.append(f"⚠️ VIX عالي {vix:.1f} - خطر")
        elif vix < 16:
            reasons.append(f"✅ VIX آمن {vix:.1f}")

        # === القرار النهائي ===
        total = call_points + put_points
        if call_points >= 4:
            decision = "🟢 CALL - ادخل CALL فقط"
            confidence = f"{int(call_points/total*100)}% CALL"
            strike = f"CALL {round(last+5)} الى {round(last+20)} - OTM خفيف"
            plan = f"اشتري عند {vwap:.0f} - {ema20:.0f}"
        elif put_points >= 4:
            decision = "🔴 PUT - ادخل PUT فقط"
            confidence = f"{int(put_points/total*100)}% PUT"
            strike = f"PUT {round(last-20)} الى {round(last-5)} - OTM خفيف"
            plan = f"اشتري عند {vwap:.0f} - {ema20:.0f}"
        else:
            decision = "🟡 لا تدخل - السوق متذبذب"
            confidence = "50/50 خطر"
            strike = "لا تدخل 0DTE"
            plan = "احفظ فلوسك"

        reason_text = "\n".join(reasons)

        return f"""🔥 **قراءة دقيقة - SPX {last:.2f}**

{reason_text}

━━━━━━━━━━━━━━
💡 **القرار: {decision}**
📊 **الثقة: {confidence}**
🎯 **العقد: {strike}**
📝 **الخطة: {plan}**

⏰ {datetime.now(RIYADH_TZ).strftime('%H:%M')} الرياض
⚠️ 0DTE خطر - 1% فقط

/market للتحديث
"""

    except Exception as e:
        return f"خطأ: {e}"

@bot.message_handler(commands=['start'])
def start_cmd(m):
    SUBSCRIBERS.add(m.chat.id)
    bot.send_message(m.chat.id, "🔥 بوت القراءة الصحيحة اشتغل!\n\nهيبعتلك:\n✅ 4:25 عصراً قبل الافتتاح\n✅ /market في أي وقت\n\nاكتب /market الآن")
    a = get_accurate_analysis()
    if a: bot.send_message(m.chat.id, a, parse_mode="Markdown")

@bot.message_handler(commands=['market','spx'])
def market_cmd(m):
    SUBSCRIBERS.add(m.chat.id)
    bot.send_message(m.chat.id, "⏳ بحلل بدقة...")
    a = get_accurate_analysis()
    bot.send_message(m.chat.id, a, parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def stop_cmd(m):
    SUBSCRIBERS.discard(m.chat.id)
    bot.send_message(m.chat.id, "🔕 وقفت الإشعارات")

def auto_sender():
    while True:
        try:
            now = datetime.now(RIYADH_TZ)
            # 4:25 عصراً و كل 30 دقيقة
            if now.weekday()<5 and 16<=now.hour<=23 and now.minute in [25,0,30]:
                if SUBSCRIBERS:
                    a = get_accurate_analysis()
                    if a:
                        for cid in list(SUBSCRIBERS):
                            try: bot.send_message(cid, "🔔 تنبيه أوتوماتيك\n\n"+a, parse_mode="Markdown")
                            except: pass
                time.sleep(60)
            time.sleep(30)
        except:
            time.sleep(60)

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=auto_sender, daemon=True).start()
    bot.infinity_polling()
