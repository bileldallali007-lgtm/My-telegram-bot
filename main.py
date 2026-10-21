import yfinance as yf, telebot, os, time
from flask import Flask
import threading
from datetime import datetime
import pytz

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
SUBSCRIBERS = set()
RIYADH = pytz.timezone('Asia/Riyadh')

@app.route('/')
def home(): return "Bilel Auto + Accurate"

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
        if call_pts>=4: dec="🟢 CALL"; conf=int(call_pts/(call_pts+put_pts)*100); strike=f"{round(last+10)}"
        elif put_pts>=4: dec="🔴 PUT"; conf=int(put_pts/(call_pts+put_pts)*100); strike=f"{round(last-10)}"
        else: dec="🟡 لا تدخل"; conf=50; strike="انتظر"
        txt="\n".join(reasons)
        return f"🔔 **تنبيه SPX {last:.2f}**\n\n{txt}\n\n💡 **القرار: {dec} {conf}%**\n🎯 Strike: {strike}\n😨 VIX: {vix:.1f}\n⏰ {datetime.now(RIYADH).strftime('%H:%M')} الرياض\n\n⚠️ 1% فقط - 0DTE خطر"
    except: return None

@bot.message_handler(commands=['start','market','spx'])
def handle(m):
    SUBSCRIBERS.add(m.chat.id)
    bot.send_message(m.chat.id, "✅ اشتركت في الإشعارات الأوتوماتيك\nهيبعتلك 4:25 عصراً + كل 30 دقيقة")
    s=get_signal()
    if s: bot.send_message(m.chat.id, s, parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def stop(m):
    SUBSCRIBERS.discard(m.chat.id)
    bot.send_message(m.chat.id, "🔕 وقفت الإشعارات")

def auto_loop():
    sent_times=set()
    while True:
        try:
            now=datetime.now(RIYADH)
            key=f"{now.day}-{now.hour}-{now.minute}"
            is_weekday=now.weekday()<5
            is_market=is_weekday and 16<=now.hour<=23
            is_alert=now.minute in [25,0,30]
            if is_market and is_alert and key not in sent_times:
                s=get_signal()
                if s and SUBSCRIBERS:
                    for cid in list(SUBSCRIBERS):
                        try: bot.send_message(cid, s, parse_mode="Markdown")
                        except: pass
                sent_times.add(key)
                if len(sent_times)>100: sent_times.clear()
            time.sleep(20)
        except: time.sleep(60)

def run_flask(): app.run(host='0.0.0.0',port=int(os.environ.get("PORT",5000)))
if __name__=="__main__":
    threading.Thread(target=run_flask).start()
    threading.Thread(target=auto_loop,daemon=True).start()
    bot.infinity_polling()
