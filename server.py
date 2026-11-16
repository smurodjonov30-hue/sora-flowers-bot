import os, json, hmac, hashlib, time, sqlite3
from urllib.parse import parse_qsl
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import httpx
load_dotenv()

BASE=Path(__file__).parent
BOT_TOKEN=os.getenv('BOT_TOKEN','')
ADMIN_CHAT_ID=os.getenv('ADMIN_CHAT_ID','')
BOT_USERNAME=os.getenv('BOT_USERNAME','')
WEBAPP_URL=os.getenv('WEBAPP_URL','')
WEBHOOK_SECRET=os.getenv('WEBHOOK_SECRET','')
DB=BASE/'orders.sqlite3'
app=FastAPI(title='Sora Flowers Mini App')

class Customer(BaseModel):
    name:str=Field(min_length=2,max_length=100)
    phone:str=Field(min_length=9,max_length=25)
    address:str=Field(min_length=5,max_length=500)
    delivery_time:str=''
class Item(BaseModel):
    name:str
    qty:int=Field(ge=1,le=30)
    price:int=Field(ge=0)
class Order(BaseModel):
    customer:Customer
    payment_method:str='cash'
    items:list[Item]
    total:int=Field(ge=0)

def init_db():
    with sqlite3.connect(DB) as c:
        c.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, telegram_user_id TEXT, customer_name TEXT, phone TEXT, address TEXT, delivery_time TEXT, payment_method TEXT, items_json TEXT, total INTEGER, status TEXT DEFAULT 'new')")
init_db()

def verify_init_data(raw:str):
    if not BOT_TOKEN or not raw: return None
    pairs=dict(parse_qsl(raw,keep_blank_values=True))
    their_hash=pairs.pop('hash',None)
    if not their_hash: return None
    auth_date=int(pairs.get('auth_date','0') or 0)
    if abs(time.time()-auth_date)>86400: return None
    data_check='\n'.join(f'{k}={v}' for k,v in sorted(pairs.items()))
    secret=hmac.new(b'WebAppData',BOT_TOKEN.encode(),hashlib.sha256).digest()
    ours=hmac.new(secret,data_check.encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(ours,their_hash): return None
    try: return json.loads(pairs.get('user','{}'))
    except Exception: return None

async def notify_admin(text):
    if not BOT_TOKEN or not ADMIN_CHAT_ID: return
    async with httpx.AsyncClient(timeout=12) as client:
        await client.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',json={'chat_id':ADMIN_CHAT_ID,'text':text})

@app.get('/api/health')
def health(): return {'ok':True,'service':'Sora Flowers'}

START_TEXT = (
    "🌿 <b>SORA FLOWERS</b> ga xush kelibsiz!\n\n"
    "Assalomu alaykum! 💚\n\n"
    "Biz sizga uyingiz va ofisingiz uchun turli xil chiroyli xona gullarini taklif qilamiz.\n\n"
    "🌱 Sifatli va saralangan gullar\n"
    "🎁 Sovg‘a uchun ajoyib tanlov\n"
    "🚚 Yetkazib berish xizmati mavjud\n\n"
    "📍 <b>Manzil:</b> Toshkent shahri, Chorsu bozori\n\n"
    "📞 <b>Aloqa:</b> <a href=\"tel:+998946282004\">+998 94 628 20 04</a>\n\n"
    "🛍 Katalogimizni ko‘ring, o‘zingizga yoqqan gulni tanlang va buyurtma bering!\n\n"
    "<b>SORA FLOWERS — Tabiat go‘zalligi sizning uyingizda!</b>"
)

async def telegram_call(method, payload):
    if not BOT_TOKEN:
        raise HTTPException(503, 'BOT_TOKEN serverda sozlanmagan')
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f'https://api.telegram.org/bot{BOT_TOKEN}/{method}', json=payload)
        r.raise_for_status()
        data = r.json()
        if not data.get('ok'):
            raise RuntimeError(data.get('description','Telegram API xatosi'))
        return data.get('result')

@app.on_event('startup')
async def register_telegram_webhook():
    # Render'dagi xizmat ishga tushganda Telegram webhook manzilini avtomatik sozlaydi.
    if not BOT_TOKEN:
        print('BOT_TOKEN sozlanmagan: Telegram webhook ulanmaydi')
        return
    base_url = os.getenv('RENDER_EXTERNAL_URL', 'https://sora-flowers-bot.onrender.com').rstrip('/')
    payload = {'url': base_url + '/telegram/webhook'}
    if WEBHOOK_SECRET:
        payload['secret_token'] = WEBHOOK_SECRET
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/setWebhook',
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            if result.get('ok'):
                print('Telegram webhook muvaffaqiyatli sozlandi:', payload['url'])
            else:
                print('Telegram webhook xatosi:', result.get('description', 'Noma’lum xato'))
    except Exception as exc:
        print('Telegram webhook sozlashda xato:', str(exc))


@app.post('/telegram/webhook')
async def telegram_webhook(update: dict, x_telegram_bot_api_secret_token: str = Header(default='')):
    if WEBHOOK_SECRET and not hmac.compare_digest(WEBHOOK_SECRET, x_telegram_bot_api_secret_token):
        raise HTTPException(403, 'Webhook secret noto‘g‘ri')
    message = update.get('message') or update.get('edited_message')
    if not message or not message.get('text','').split():
        return {'ok': True}
    text_in = message.get('text','').strip()
    if text_in.startswith('/start'):
        chat_id = message['chat']['id']
        keyboard = {'inline_keyboard': [[{'text':'🛍 Katalogni ko‘rish','web_app':{'url':WEBAPP_URL}}]]}
        await telegram_call('sendMessage', {'chat_id':chat_id,'text':START_TEXT,'parse_mode':'HTML','reply_markup':keyboard})
    return {'ok': True}

@app.post('/api/orders')
async def create_order(order:Order, x_telegram_init_data:str=Header(default='')):
    user=verify_init_data(x_telegram_init_data)
    if not user: raise HTTPException(401,'Telegram foydalanuvchisi tasdiqlanmadi. Mini App ichidan qayta kiring.')
    if order.payment_method!='cash': raise HTTPException(400,'Hozircha faqat yetkazilganda naqd toʻlov ishlaydi.')
    catalog=json.loads((BASE/'catalog.json').read_text('utf-8'))
    by_name={p.get('name'):int(p.get('price') or 0) for p in catalog.get('items',[])}
    calc=0
    safe_items=[]
    for it in order.items:
        if it.name not in by_name: raise HTTPException(400,'Katalogda topilmagan mahsulot: '+it.name)
        price=by_name[it.name]
        if price<=0: raise HTTPException(400,'Mahsulot narxi hali belgilanmagan: '+it.name)
        calc+=price*it.qty
        safe_items.append({'name':it.name,'qty':it.qty,'price':price})
    if calc!=order.total: raise HTTPException(400,'Buyurtma summasi mos kelmadi. Sahifani yangilang.')
    with sqlite3.connect(DB) as c:
        cur=c.execute('INSERT INTO orders(telegram_user_id,customer_name,phone,address,delivery_time,payment_method,items_json,total) VALUES(?,?,?,?,?,?,?,?)',
            (str(user.get('id','')),order.customer.name,order.customer.phone,order.customer.address,order.customer.delivery_time,'cash',json.dumps(safe_items,ensure_ascii=False),calc))
        oid=cur.lastrowid
    msg=(f'🌿 SORA FLOWERS — YANGI BUYURTMA №{oid}\n\n'+ '\n'.join(f"• {x['name']} × {x['qty']} — {x['price']*x['qty']:,} soʻm" for x in safe_items)+
         f"\n\nJami: {calc:,} soʻm\nToʻlov: Yetkazilganda naqd\n\nIsm: {order.customer.name}\nTelefon: {order.customer.phone}\nManzil: {order.customer.address}\nYetkazish: {order.customer.delivery_time or 'Kelishiladi'}\nTelegram ID: {user.get('id','')} ")
    try: await notify_admin(msg)
    except Exception: pass
    return {'ok':True,'order_id':oid,'message':'Buyurtma qabul qilindi'}

@app.get('/api/my-orders')
def my_orders(x_telegram_init_data:str=Header(default='')):
    user=verify_init_data(x_telegram_init_data)
    if not user: raise HTTPException(401,'Telegram foydalanuvchisi tasdiqlanmadi. Mini App ichidan qayta kiring.')
    uid=str(user.get('id',''))
    with sqlite3.connect(DB) as c:
        c.row_factory=sqlite3.Row
        rows=c.execute('SELECT id, created_at, items_json, total, status FROM orders WHERE telegram_user_id=? ORDER BY id DESC LIMIT 100',(uid,)).fetchall()
    return [{'id':r['id'],'created_at':r['created_at'],'items':json.loads(r['items_json'] or '[]'),'total':r['total'],'status':r['status']} for r in rows]

@app.get('/api/admin/orders')
def list_orders(x_admin_key:str=Header(default='')):
    key=os.getenv('ADMIN_API_KEY','')
    if not key or not hmac.compare_digest(key,x_admin_key): raise HTTPException(403,'Ruxsat yoʻq')
    with sqlite3.connect(DB) as c:
        c.row_factory=sqlite3.Row
        rows=c.execute('SELECT * FROM orders ORDER BY id DESC LIMIT 100').fetchall()
    return [dict(r) for r in rows]

app.mount('/',StaticFiles(directory=BASE/'static',html=True),name='static')
