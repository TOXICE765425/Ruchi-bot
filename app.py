import os, threading
from flask import Flask, request, jsonify
import bot

app = Flask(__name__)
SECRET = os.getenv("WEBHOOK_SECRET", "change-me-secret")

if not os.getenv("VERCEL"):  # tempadmin auto-demote ke liye (Vercel pe background thread nahi chalta)
    threading.Thread(target=bot.job_loop, daemon=True).start()

@app.get("/")
def home():
    return "Bot is running 💖"

@app.get("/setwebhook")
def setwebhook():
    if request.args.get("key") != SECRET:
        return "forbidden", 403
    base = (os.getenv("WEBHOOK_URL") or request.url_root).rstrip("/").replace("http://", "https://")
    r = bot.tg("setWebhook", url=f"{base}/webhook", secret_token=SECRET,
               allowed_updates=["message", "callback_query"], drop_pending_updates=True)
    return jsonify(r)

@app.post("/webhook")
def webhook():
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != SECRET:
        return "forbidden", 403
    try:
        bot.process_update(request.get_json(force=True))
    except Exception as e:
        print("ERR:", e)
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
