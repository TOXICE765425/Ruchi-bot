# Ruchi - AI Girlfriend Telegram Bot

Groq AI + group moderation + /start menu (photo + 5 buttons, ek hi message edit hota hai).

## Env variables
`.env.example` dekho. Zaroori: `BOT_TOKEN`, `GROQ_API_KEY`, `WEBHOOK_SECRET`.
Baaki: `SUPPORT_URL`, `UPDATES_URL`, `DEVELOPER_URL`, `START_IMG`, `GF_NAME`, `OWNER_NAME`.

## Deploy (webhook): Render / Railway / Heroku / Vercel
1. Repo GitHub pe daalo, platform pe connect karo, env variables set karo
   - Render: `render.yaml` ya Web Service (start: `gunicorn app:app --workers 1 --threads 8 --timeout 120`)
   - Railway / Heroku: `Procfile` apne aap use hota hai
   - Vercel: `vercel.json` ready hai
2. Deploy hone ke baad browser mein ye kholo (ek baar):
   `https://TUMHARA-URL/setwebhook?key=WEBHOOK_SECRET_WALI_VALUE`
3. Telegram mein /start bhejo

## VPS / local (polling, webhook nahi chahiye)
```
pip install -r requirements.txt
export BOT_TOKEN=... GROQ_API_KEY=...
python bot.py
```
Background mein: `nohup python bot.py &` ya pm2 / systemd.

## BotFather setup
- `/setprivacy` -> Disable (group mein messages dikhne ke liye)
- Group mein bot ko admin banao (ban/mute/promote ke liye rights do)

## Firebase Realtime Database (permanent memory, Vercel ke liye zaroori)
1. console.firebase.google.com -> project banao -> Build -> Realtime Database -> Create database
2. Rules tab mein: `{ "rules": { ".read": false, ".write": false } }` -> Publish
3. Database ka URL copy karo (jaise `https://xxxx-default-rtdb.firebaseio.com`) -> `FIREBASE_DB_URL`
4. Project settings -> Service accounts -> Database secrets -> secret copy karo -> `FIREBASE_SECRET`
5. Dono env variables Vercel/Render mein daalo aur Redeploy karo

Firebase set na ho to memory local `data/db.json` mein save hoti hai (Vercel pe reset ho jayegi).

## /tempadmin auto-demote (Vercel)
Vercel pe background thread nahi chalta. cron-job.org (free) pe ek job banao jo har minute
`https://TUMHARA-URL/cron?key=WEBHOOK_SECRET` hit kare. Render/Railway/VPS pe iski zaroorat nahi.
