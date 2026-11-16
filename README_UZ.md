# Sora Flowers — Telegram Mini App

## Hozir tayyorlangan qism
- Telegram WebApp SDK ulanishi, `ready()` va `expand()`
- Telegram `initData` HMAC tekshiruvi (serverda)
- Buyurtma serverga yuboriladi va SQLite bazaga yoziladi
- Buyurtma Telegram admin chatiga yuboriladi
- Narx serverdagi katalog bilan qayta tekshiriladi
- Hozircha toʻlov: yetkazilganda naqd

## Ishga tushirish
1. Python 3.11+ o‘rnating.
2. `python -m venv .venv` va aktivatsiya qiling.
3. `pip install -r requirements.txt`
4. `.env.example` nusxasini `.env` qiling va qiymatlarni to‘ldiring.
5. Muhit o‘zgaruvchilarini serverga kiriting (yoki `.env` yuklash uchun python-dotenv qo‘shing).
6. `uvicorn server:app --host 0.0.0.0 --port 8000`
7. Saytni HTTPS domen orqali oching. Telegram Mini App uchun HTTPS shart.

## /start xabarini ulash
- Backend HTTPS hostingga joylangandan so‘ng `WEBAPP_URL=https://sora-flower.netlify.app` bo‘lishi kerak.
- `.env` ichida `BOT_TOKEN` va tasodifiy uzun `WEBHOOK_SECRET` qiymatlarini kiriting.
- Webhookni bir marta Telegram API orqali o‘rnating: `https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://BACKEND-DOMEN/telegram/webhook&secret_token=<WEBHOOK_SECRET>`.
- Shundan keyin mijoz botga `/start` yuborsa, Sora Flowers tanishtiruv xabari va “Katalogni ko‘rish” hamda “Biz bilan bog‘lanish” tugmalari chiqadi.
- Bu webhook Netlify Drop’da emas, Python backend joylashtirilgan HTTPS serverda ishlaydi.

## Telegram sozlash
- Mavjud bot ishlatiladi: `@sora_flowers_bot`. Yangi bot yaratish shart emas.
- @BotFather ichida shu botni tanlab, tokenini oling va serverdagi `BOT_TOKEN` muhit o‘zgaruvchisiga kiriting. Tokenni chatga yoki ommaviy faylga yozmang.
- `BOT_USERNAME=sora_flowers_bot` qiymati oldindan sozlangan.
- Botni admin guruhga qo‘shing; `ADMIN_CHAT_ID` ga guruh ID sini kiriting.
- @BotFather orqali `/setmenubutton` buyrug‘ini tanlang, `@sora_flowers_bot` botini belgilang va Mini App URL sifatida quyidagi HTTPS manzilni kiriting.
- `WEBAPP_URL` ni haqiqiy HTTPS manzilga o‘zgartiring. Domen hostingga joylashtirilgandan keyin Telegram Mini App menyu tugmasi shu URL ga ochiladi.
- Admin guruhida botga xabar yuborish huquqi bo‘lsin.

## Mijozga beriladigan bot havolasi
- Bot: https://t.me/sora_flowers_bot
- Mini App to‘g‘ridan-to‘g‘ri ochish havolasi (Web App URL ulanganidan keyin): `https://t.me/sora_flowers_bot?startapp`

## To‘lovlar
Payme va Click hozir ulanmagan. Ularni yoqishdan oldin merchant shartnomasi, merchant ID/secret, callback URL va serverdagi payment status tekshiruvi kerak. Faqat to‘lov provayderining server callback’i tasdiqlagandan keyin buyurtma `paid` deb belgilanadi. Frontenddan kelgan `success` qiymatiga ishonilmaydi.

## Muhim
Bu loyiha deploy uchun boshlang‘ich backend bilan tayyorlandi, lekin bot tokeni, admin chat ID va HTTPS domen siz tomondan berilmaguncha real buyurtma oqimi internetda ishga tushmaydi. Admin buyurtmalar ro‘yxati `GET /api/admin/orders` orqali `X-Admin-Key` bilan himoyalangan.
