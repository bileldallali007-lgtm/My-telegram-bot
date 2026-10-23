import yfinance as yf, telebot, os, time, json
from flask import Flask
import threading
from datetime import datetime
import pytz

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")  # ID بتاعك اختياري
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
RIYADH = pytz.timezone('Asia/Riyadh')

FILE = "/tmp/subs.json"  # Render بيمسح /tmp بس هنرجعك بـ OWNER_ID

def load_subs():
    try:
        with open(FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_subs(s):
    try:
        with open(FILE, "w") as f:
            json.dump(list(s), f)
    except: pass

SUBSCRIBERS = load_subs()

@app.route('/')
def home():
    return f"OK - Live - Subs: {len(SUBSCRIBERS)} - {datetime.now(RIYADH).strftime('%H:%M')} KSA"

def get_rsi(p):
    d=p.diff(); g=(d.where(d>0,0)).rolling(14).mean(); l=(-d.where(d<0,0)).rolling(14).mean(); rs=g/l; return 100-(100/(1+rs))

def get_signal():
    try:
        spx=yf.Ticker("^GSPC"); d=spx.history(period="1d",interval="5m")
        if d.empty: return "⛔ السوق مقفل - هيفتح 4:30 عصراً الرياض"
        last=float(d['Close'].iloc[-1]); open_p=float(d['Open'].iloc[0])
        d['Typ']=(d['High']+d['Low']+d['Close'])/3; d['PV']=d['Typ']*d['Volume']
        vwap=float(d['PV'].sum()/d['Volume'].sum())
        e20=float(d['Close'].ewm(20).mean().iloc[-1]); e50=float(d['Close'].ewm(50).mean().iloc[-1])
        rsi=float(get_rsi(d['Close']).iloc[-1])
        vix=float(yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1])

        call_pts=0; put_pts=0; reasons=[]
        if last>vwap: call_pts+=2; reasons.append(f"✅ فوق VWAP {vwap:.0f}")
        else: put_pts+=2; reasons.append(f"❌ تحت VWAP {vwap:.0f}")
        if last>open_p: call_pts+=2; reasons.append(f"✅ فوق الافتتاح {open_p:.0f}")
        else: put_pts+=2; reasons.append(f"❌ تحت الافتتاح {open_p:.0f}")
        if e20>e50: call_pts+=1; reasons.append("✅ EMA20>EMA50")
        else: put_pts+=1; reasons.append("❌ EMA20<EMA50")
        if rsi>55: call_pts+=1
        elif rsi<45: put_pts+=1

        total=call_pts+put_pts
        if call_pts>=4: dec="🟢 CALL"; conf=int(call_pts/total*100); strike=f"CALL {round(last+10)}"
        elif put_pts>=4: dec="🔴 PUT"; conf=int(put_pts/total*100); strike=f"PUT {round(last-10)}"
        else: dec="🟡 لا تدخل"; conf=50; strike="انتظر"

        txt="\n".join(reasons)
        return f"🔔 SPX {last:.2f}\n\n{txt}\n\n💡 {dec} {conf}%\n🎯 {strike}\n😨 VIX: {vix:.1f}\n⏰ {datetime.now(RIYADH).strftime('%H:%M')} الرياض"
    except Exception as e:
        return f"خطأ: {e}"

@bot.message_handler(commands=['start'])
def start(m):
    global SUBSCRIBERS
    SUBSCRIBERS.add(m.chat.id)
    save_subs(SUBSCRIBERS)
    bot.send_message(m.chat.id, "✅ اشتغل! اشتركت في الإشعارات\nالساعة 4:25 عصراً هيبعتلك أوتوماتيك")
    s=get_signal()
    if s: bot.send_message(m.chat.id, s)

@bot.message_handler(commands=['market','spx'])
def market(m):
    global SUBSCRIBERS
    SUBSCRIBERS.add(m.chat.id)
    save_subs(SUBSCRIBERS)
    s=get_signal()
    if s: bot.send_message(m.chat.id, s)

def auto_loop():
    sent=set()
    while True:
        try:
            now=datetime.now(RIYADH)
            key=f"{now.day}-{now.hour}-{now.minute}"
            is_weekday=now.weekday()<5
            is_market=is_weekday and 16 <= now.hour <= 23
            # يبعت 4:25 و كل 30 دقيقة
            if is_market and now.minute in [25,0,30] and key not in sent:
                s=get_signal()
                if s:
                    targets = set(SUBSCRIBERS)
                    if OWNER_ID:
                        try: targets.add(int(OWNER_ID))
                        except: pass
                    print(f"Sending to {len(targets)} at {now}")
                    for cid in list(targets):
                        try: bot.send_message(cid, f"🔔 تنبيه أوتوماتيك\n\n{s}")
                        except: pass
                sent.add(key)
                if len(sent)>200: sent.clear()
            time.sleep(20)
        except Exception as e:
            print(f"Loop err {e}")
            time.sleep(60)

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=auto_loop, daemon=True).start()
    bot.infinity_polling()
