import yfinance as yf, telebot, os, time, json
from flask import Flask
import threading
from datetime import datetime
import pytz

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") # لو عامل قناة حط الاي دي هنا
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
RIYADH = pytz.timezone('Asia/Riyadh')

FILE = "subs.json"

def load_subs():
    try:
        with open(FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_subs(subs):
    try:
        with open(FILE, "w") as f:
            json.dump(list(subs), f)
    except: pass

SUBSCRIBERS = load_subs()

@app.route('/')
def home(): 
    return f"Bot Live - Subs: {len(SUBSCRIBERS)}"

def get_rsi(p):
    d=p.diff(); g=(d.where(d>0,0)).rolling(14).mean(); l=(-d.where(d<0,0)).rolling(14).mean(); rs=g/l; return 100-(100/(1+rs))

def get_signal():
    try:
        spx=yf.Ticker("^GSPC"); d=spx.history(period="1d",interval="5m")
        if d.empty: return None
        last=float(d['Close'].iloc[-1]); open_p=float(d['Open'].iloc[0])
        d['Typ']=(d['High']+d['Low']+d['Close'])/3; d['PV']=d['Typ']*d['Volume']
        vwap=float(d['PV'].sum()/d['Volume'].sum()); e20=float(d['Close'].ewm(20).mean().iloc[-1]); e50=float(d['Close'].ewm(50).mean().iloc[-1])
        rsi=float(get_rsi(d['Close']).iloc[-1]); vix=float(yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1])
        call_pts=0; put_pts=0; reasons=[]
        if last>vwap: call_pts+=2; reasons.append(f"✅ فوق VWAP {vwap:.0f}")
        else: put_pts+=2; reasons.append(f"❌ تحت VWAP {vwap:.0f}")
        if last>open_p: call_pts+=2; reasons.append(f"✅ فوق الافتتاح {open_p:.0f}")
        else: put_pts+=2; reasons.append(f"❌ تحت الافتتاح {open_p:.0f}")
        if e20>e50: call_pts+=1
        else: put_pts+=1
        if rsi>55: call_pts+=1
        elif rsi<45: put_pts+=1
        
        if call_pts>=4: dec="🟢 CALL"; conf=int(call_pts/(call_pts+put_pts)*100)
        elif put_pts>=4: dec="🔴 PUT"; conf=int(put_pts/(call_pts+put_pts)*100)
        else: dec="🟡 لا تدخل"; conf=50
        
        txt="\n".join(reasons)
        return f"🔔 SPX {last:.2f}\n\n{txt}\n\n💡 {dec} {conf}%\n😨 VIX: {vix:.1f}\n⏰ {datetime.now(RIYADH).strftime('%H:%M')} الرياض"
    except Exception as e:
        return f"خطأ: {e}"

@bot.message_handler(commands=['start','market','spx'])
def handle(m):
    global SUBSCRIBERS
    SUBSCRIBERS.add(m.chat.id)
    save_subs(SUBSCRIBERS)
    s=get_signal()
    if s:
        bot.send_message(m.chat.id, s, parse_mode="Markdown")
        if CHANNEL_ID:
            try: bot.send_message(CHANNEL_ID, s)
            except: pass

@bot.message_handler(commands=['stop'])
def stop(m):
    global SUBSCRIBERS
    SUBSCRIBERS.discard(m.chat.id)
    save_subs(SUBSCRIBERS)
    bot.send_message(m.chat.id, "🔕 وقفت الإشعارات")

def auto_loop():
    sent=set()
    while True:
        try:
            now=datetime.now(RIYADH); key=f"{now.day}-{now.hour}-{now.minute}"
            is_market=now.weekday()<5 and 16<=now.hour<=23
            # يبعت 4:25 و كل 30 دقيقة
            if is_market and now.minute in [25,0,30] and key not in sent:
                s=get_signal()
                print(f"Auto check {now} - subs {len(SUBSCRIBERS)}")
                if s:
                    # يبعت للقناة لو موجودة
                    if CHANNEL_ID:
                        try: bot.send_message(CHANNEL_ID, "🔔 تنبيه أوتوماتيك\n\n"+s)
                        except Exception as e: print(e)
                    # يبعت للمشتركين
                    for cid in list(SUBSCRIBERS):
                        try: bot.send_message(cid, "🔔 تنبيه أوتوماتيك\n\n"+s)
                        except: pass
                sent.add(key)
                if len(sent)>200: sent.clear()
            time.sleep(20)
        except Exception as e:
            print(f"Loop error {e}")
            time.sleep(60)

def run_flask(): app.run(host='0.0.0.0',port=int(os.environ.get("PORT",5000)))

if __name__=="__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=auto_loop,daemon=True).start()
    bot.infinity_polling()
