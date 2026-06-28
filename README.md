# Telegram Auto Poster — Vercel Python

Bu loyiha Telegram user akkaunti orqali tanlangan guruh yoki kanalga jadval bo‘yicha xabar yuborish uchun tayyorlangan.

## Funksiyalar

- Telegram bot `/start`
- Web App tugmasi
- Telefon raqam orqali Telegram login
- Telegram kod tasdiqlash
- 2 bosqichli Telegram parolni qo‘llash
- Guruh va kanallar ro‘yxatini olish
- Xabar va interval belgilash
- Cron orqali vaqti kelgan xabarlarni yuborish
- PostgreSQL bilan ishlash

## Muhim ogohlantirish

Bu appni faqat o‘zingizga tegishli akkauntlarda va ruxsatga ega bo‘lgan guruh/kanallarda ishlating. Spam yoki ruxsatsiz avtomatik xabar yuborish Telegram cheklovlariga olib kelishi mumkin.

## Vercel Environment Variables

Vercel → Project → Settings → Environment Variables ichiga qo‘shing:

```text
API_ID
API_HASH
BOT_TOKEN
SECRET_KEY
WEBAPP_URL
DATABASE_URL
CRON_SECRET
```

`WEBAPP_URL` misol:

```text
https://autoxabar.vercel.app
```

## Telegram API_ID va API_HASH

Telegram API_ID va API_HASH olish uchun Telegram developer portalidan app yarating.

## Database

Vercel uchun PostgreSQL kerak. SQLite Vercel’da doimiy saqlanmaydi. `DATABASE_URL` PostgreSQL connection string bo‘lishi kerak.

Misol:

```text
postgresql://user:password@host:5432/dbname
```

## Deploy

```bash
git add .
git commit -m "deploy telegram autoposter"
git push
npx vercel@latest --prod
```

## Bot webhook

Deploydan keyin browserda oching:

```text
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://autoxabar.vercel.app/api/bot
```

`<BOT_TOKEN>` o‘rniga bot tokenni qo‘ying.

## Cron

Har 1 daqiqada quyidagi URL chaqirilishi kerak:

```text
https://autoxabar.vercel.app/api/cron?secret=YOUR_CRON_SECRET
```

Buni `cron-job.org` orqali sozlash mumkin.

## Test endpointlar

```text
https://autoxabar.vercel.app/health
https://autoxabar.vercel.app/api/bot
https://autoxabar.vercel.app/api/cron?secret=YOUR_CRON_SECRET
```

## File structure

```text
api/
  index.py
  bot.py
  cron.py
utils/
  database.py
templates/
  login.html
  dashboard.html
static/
  css/style.css
  js/app.js
scripts/
  set_webhook.py
vercel.json
requirements.txt
.env.example
README.md
```
