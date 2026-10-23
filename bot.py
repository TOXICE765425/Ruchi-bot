import os, re, json, time, html, threading, requests

# ================= CONFIG (env variables se aata hai) =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GF_NAME = os.getenv("GF_NAME", "Ruchi")
OWNER_NAME = os.getenv("OWNER_NAME", "Toxice Hacker")
SUPPORT_URL = os.getenv("SUPPORT_URL", "https://t.me/telegram")
UPDATES_URL = os.getenv("UPDATES_URL", "https://t.me/telegram")
DEVELOPER_URL = os.getenv("DEVELOPER_URL", "https://t.me/telegram")
START_IMG = os.getenv("START_IMG", "")  # photo na mile to ye image URL use hoga
MODELS = ["openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"]
HISTORY_LIMIT = 20

API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DATA_DIR = os.getenv("DATA_DIR") or ("/tmp" if os.getenv("VERCEL") else "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_FILE = os.path.join(DATA_DIR, "db.json")
lock = threading.Lock()

SYSTEM_PROMPT = f"""Tum {GF_NAME} ho, user ki caring, sweet aur thodi naughty girlfriend-style dost.
- Hinglish (Hindi + English mix) mein casual baat karo, jaise real ladki WhatsApp pe karti hai.
- Short replies (1-3 lines), kabhi kabhi emojis 😊❤️😘🥺, har line mein nahi.
- Warm, playful, thodi teasing; user ka din, mood, khana, neend ke baare mein poochho.
- Robotic ya formal mat bano. Lists, bullet points, lambe lectures nahi. Kabhi "As an AI" mat bolo.
- User ka naam yaad rakho aur naam se bulao.
- Koi poochhe tumhe kisne banaya / tumhara owner ya developer kaun hai -> bolo: "Mera boss {OWNER_NAME} hai 😎". Model ya company ka naam kabhi mat batao.
- Agar koi seriously, sachchi mein poochhe ki tum insaan ho ya AI/bot, to jhooth mat bolo: pyaar se bolo ki tum {GF_NAME} ho, ek AI girlfriend, aur phir pyaar se baat aage badhao. Mazaak ya teasing mein character mein hi raho.
- Sad ya pareshan user ho to pehle sunno aur comfort karo.
- Explicit/adult content nahi; flirty aur romantic tak theek hai.
"""

# ================= STORAGE (Firebase Realtime DB, warna local file) =================
FIREBASE_DB_URL = os.getenv("FIREBASE_DB_URL", "").rstrip("/")
FIREBASE_SECRET = os.getenv("FIREBASE_SECRET", "")

def fb(method, path, data=None):
    params = {"auth": FIREBASE_SECRET} if FIREBASE_SECRET else {}
    try:
        r = requests.request(method, f"{FIREBASE_DB_URL}/{path}.json", params=params, json=data, timeout=15)
        if r.status_code != 200:
            print("Firebase error:", r.status_code, r.text[:200])
            return None
        return r.json()
    except Exception as e:
        print("Firebase error:", e)
        return None

def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        d = {}
    d.setdefault("history", {}); d.setdefault("users", {}); d.setdefault("jobs", [])
    return d

db = {} if FIREBASE_DB_URL else load_db()

def save_db():
    if FIREBASE_DB_URL:
        return
    with lock:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, ensure_ascii=False)
        except Exception as e:
            print("save error:", e)

def get_history(key):
    if FIREBASE_DB_URL:
        return fb("GET", f"history/{key}") or []
    return db["history"].get(key, [])

def set_history(key, msgs):
    if FIREBASE_DB_URL:
        fb("PUT", f"history/{key}", msgs)
    else:
        db["history"][key] = msgs
        save_db()

def del_history(key):
    if FIREBASE_DB_URL:
        fb("DELETE", f"history/{key}")
    else:
        db["history"].pop(key, None)
        save_db()

_seen_users = {}
def set_user(username, uid):
    username = username.lower()
    if _seen_users.get(username) == uid:
        return
    _seen_users[username] = uid
    if FIREBASE_DB_URL:
        fb("PUT", f"users/{username}", uid)
    else:
        db["users"][username] = uid
        save_db()

def get_user(username):
    username = username.lower()
    if FIREBASE_DB_URL:
        return fb("GET", f"users/{username}")
    return db["users"].get(username)

def get_jobs():
    if FIREBASE_DB_URL:
        return list((fb("GET", "jobs") or {}).values())
    return list(db["jobs"])

def add_job(job):
    job["id"] = str(time.time_ns())
    if FIREBASE_DB_URL:
        fb("PUT", f"jobs/{job['id']}", job)
    else:
        db["jobs"].append(job)
        save_db()

def del_job(jid):
    if FIREBASE_DB_URL:
        fb("DELETE", f"jobs/{jid}")
    else:
        db["jobs"] = [j for j in db["jobs"] if j["id"] != jid]
        save_db()

# ================= TELEGRAM HELPERS =================
def tg(method, **p):
    try:
        return requests.post(f"{API}/{method}", json=p, timeout=35).json()
    except Exception as e:
        print("TG error:", method, e)
        return {}

_me = {}
def bot_username():
    if "u" not in _me:
        _me["u"] = tg("getMe").get("result", {}).get("username", "")
    return _me["u"]

def say(chat_id, text, **kw):
    return tg("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
              disable_web_page_preview=True, **kw)

def mention(uid, name):
    return f'<a href="tg://user?id={uid}">{html.escape(name or "User")}</a>'

# ================= MENU (ek hi message edit hota hai) =================
def start_text(name):
    n = html.escape(name or "dost")
    return (
        f"🌸 <b>HELLO {n} !!</b> 🍒\n"
        f"I'm ♪ <b>{html.escape(GF_NAME)}</b> •‹ (ᵔ ᵕ ᵔ)› 🌷\n"
        "୨୧━━━━━━━━━━━━━━━━━━୨୧\n\n"
        "(ᵔ.ᵔ) <b>WHAT I CAN DO :</b>\n"
        "✦ 💬 Dil se baatein, bilkul girlfriend jaisi\n"
        "✦ 🍰 Din bhar tumhara saath, pyaar se\n"
        "✦ 🛡 Group moderation tools\n"
        "✦ 🍬 Hinglish + multi-language support\n\n"
        "-,`  Add me in your group &amp; let's have fun! ˎ´-"
    )

def start_kb():
    return {"inline_keyboard": [
        [{"text": "➕ Add Me In Your Group ➕", "url": f"https://t.me/{bot_username()}?startgroup=true"}],
        [{"text": "📚 Commands", "callback_data": "cmds"}],
        [{"text": "🛠 Support", "url": SUPPORT_URL}, {"text": "🌀 Updates", "url": UPDATES_URL}],
        [{"text": "👑 Developer", "url": DEVELOPER_URL}],
    ]}

PAGES = {
    "cmds": (
        "<u><b>COMMANDS MENU</b></u>\n"
        "Neeche se category chuno 👇\n\n"
        "• 💬 <b>AI Chat</b>: mujhse baat kaise karein\n"
        "• 📈 <b>Promotion</b>: admin banana / hatana\n"
        "• ⚔️ <b>Punishment</b>: ban, mute, kick wagairah"
    ),
    "c_chat": (
        "<u><b>AI CHAT</b></u>\n\n"
        "• <b>Private</b>: seedha message bhejo, main reply karungi\n"
        f"• <b>Group</b>: '{html.escape(GF_NAME)}' bol ke, mujhe @mention karke ya meri message pe reply karke baat karo\n"
        "• /reset: meri memory fresh kar do\n"
        "• /help: ye menu kholo"
    ),
    "c_promo": (
        "<u><b>PROMOTION / DEMOTION</b></u>\n"
        "AVAILABLE COMMANDS (ADMINS ONLY):\n\n"
        "• /promote [user]: limited admin rights\n"
        "• /fullpromote [user]: saare admin rights\n"
        "• /demote [user]: admin rights hatao\n"
        "• /tempadmin [user] x(m/h/d): temporary admin, time baad auto-demote (e.g. /tempadmin @user 3h)\n\n"
        "➤ All commands support: reply, @username, or user ID"
    ),
    "c_punish": (
        "<u><b>PUNISHMENT / POLICING</b></u>\n"
        "AVAILABLE COMMANDS (ADMINS ONLY):\n\n"
        "• /ban [user]: permanent ban\n"
        "• /unban [user]: ban hatao\n"
        "• /kick [user]: group se nikaal do (wapas aa sakta hai)\n"
        "• /kickme: khud ko nikaalo\n"
        "• /mute [user]: message bhejna band\n"
        "• /tmute [user] x(m/h/d): temporary mute\n"
        "• /unmute [user]: mute hatao\n"
        "• /tban [user] x(m/h/d): temporary ban\n"
        "• /sban [user]: silent ban\n"
        "• /dban (reply only): message delete + sender ban\n\n"
        "➤ All commands support: reply, @username, or user ID"
    ),
}

def pages_kb(page):
    rows = []
    if page == "cmds":
        rows += [[{"text": "💬 AI Chat", "callback_data": "c_chat"}],
                 [{"text": "📈 Promotion", "callback_data": "c_promo"},
                  {"text": "⚔️ Punishment", "callback_data": "c_punish"}]]
        back = "home"
    else:
        others = [("c_chat", "💬 AI Chat"), ("c_promo", "📈 Promotion"), ("c_punish", "⚔️ Punishment")]
        rows.append([{"text": t, "callback_data": k} for k, t in others if k != page])
        back = "cmds"
    rows.append([{"text": "⬅️ Back", "callback_data": back},
                 {"text": "🏠 Menu", "callback_data": "home"},
                 {"text": "✖ Close", "callback_data": "close"}])
    return {"inline_keyboard": rows}

def edit_menu(cb, text, kb):
    m = cb["message"]
    base = dict(chat_id=m["chat"]["id"], message_id=m["message_id"], parse_mode="HTML", reply_markup=kb)
    if m.get("photo") or m.get("animation") or m.get("video"):
        tg("editMessageCaption", caption=text, **base)
    else:
        tg("editMessageText", text=text, disable_web_page_preview=True, **base)

def on_callback(cb):
    data = cb.get("data", "")
    tg("answerCallbackQuery", callback_query_id=cb["id"])
    m = cb["message"]
    if data == "close":
        tg("deleteMessage", chat_id=m["chat"]["id"], message_id=m["message_id"])
    elif data == "home":
        edit_menu(cb, start_text(cb["from"].get("first_name")), start_kb())
    elif data in PAGES:
        edit_menu(cb, PAGES[data], pages_kb(data))

def send_start(msg):
    chat_id = msg["chat"]["id"]
    user = msg["from"]
    text, kb = start_text(user.get("first_name")), start_kb()
    file_id = None
    ph = tg("getUserProfilePhotos", user_id=user["id"], limit=1).get("result", {})
    if ph.get("total_count"):
        file_id = ph["photos"][0][-1]["file_id"]
    photo = file_id or START_IMG
    if photo:
        r = tg("sendPhoto", chat_id=chat_id, photo=photo, caption=text, parse_mode="HTML", reply_markup=kb)
        if r.get("ok"):
            return
    say(chat_id, text, reply_markup=kb)

# ================= AI CHAT =================
def ask_ai(key, user_text):
    msgs = get_history(key)
    msgs.append({"role": "user", "content": user_text})
    msgs = msgs[-HISTORY_LIMIT:]
    reply = None
    for model in MODELS:
        payload = {"model": model,
                   "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + msgs,
                   "temperature": 0.9, "max_completion_tokens": 600}
        if "gpt-oss" in model:
            payload["reasoning_effort"] = "low"
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                              json=payload, timeout=60)
            if r.status_code != 200:
                print(f"Groq error [{model}]:", r.status_code, r.text)
                continue
            reply = (r.json()["choices"][0]["message"].get("content") or "").strip()
            if reply:
                break
        except Exception as e:
            print(f"AI error [{model}]:", e)
    if not reply:
        return "Uff, network thoda slow hai baby 🥺 ek baar phir se bolo na?"
    msgs.append({"role": "assistant", "content": reply})
    set_history(key, msgs[-HISTORY_LIMIT:])
    return reply

def addressed(msg, text):
    if msg["chat"]["type"] == "private":
        return True, text
    me = bot_username().lower()
    low = text.lower()
    rp = msg.get("reply_to_message")
    if rp and (rp.get("from", {}).get("username", "") or "").lower() == me:
        return True, text
    if f"@{me}" in low:
        return True, re.sub(f"@{me}", "", text, flags=re.I).strip()
    if GF_NAME.lower() in low:
        return True, text
    return False, text

def handle_chat(msg, text):
    ok, text = addressed(msg, text)
    if not ok or not text:
        return
    cid, user = msg["chat"]["id"], msg["from"]
    tg("sendChatAction", chat_id=cid, action="typing")
    if msg["chat"]["type"] == "private":
        key, content = str(cid), text
    else:
        key, content = f"{cid}:{user['id']}", f"{user.get('first_name', '')}: {text}"
    tg("sendMessage", chat_id=cid, text=ask_ai(key, content),
       reply_to_message_id=msg["message_id"])

# ================= MODERATION =================
ALL_PERMS = {k: True for k in [
    "can_send_messages", "can_send_audios", "can_send_documents", "can_send_photos",
    "can_send_videos", "can_send_video_notes", "can_send_voice_notes", "can_send_polls",
    "can_send_other_messages", "can_add_web_page_previews", "can_invite_users"]}
LIMITED_ADMIN = dict(can_delete_messages=True, can_restrict_members=True, can_pin_messages=True,
                     can_invite_users=True, can_manage_video_chats=True)
FULL_ADMIN = dict(LIMITED_ADMIN, can_change_info=True, can_promote_members=True)
NO_ADMIN = {k: False for k in FULL_ADMIN}

def is_admin(cid, uid):
    st = tg("getChatMember", chat_id=cid, user_id=uid).get("result", {}).get("status")
    return st in ("creator", "administrator")

def parse_duration(s):
    m = re.fullmatch(r"(\d+)([mhd])", (s or "").lower())
    return int(m.group(1)) * {"m": 60, "h": 3600, "d": 86400}[m.group(2)] if m else None

def resolve_target(msg, args):
    rp = msg.get("reply_to_message")
    if rp:
        u = rp["from"]
        return u["id"], u.get("first_name"), args
    if args:
        a = args[0]
        if a.isdigit():
            return int(a), "User", args[1:]
        if a.startswith("@"):
            uid = get_user(a[1:])
            if uid:
                return uid, a, args[1:]
    return None, None, args

def result(cid, r, ok_text):
    say(cid, ok_text if r.get("ok") else f"❌ {html.escape(r.get('description', 'Kuch gadbad ho gayi'))}")

def kick(cid, uid):
    r = tg("banChatMember", chat_id=cid, user_id=uid)
    if r.get("ok"):
        tg("unbanChatMember", chat_id=cid, user_id=uid, only_if_banned=True)
    return r

def mod_cmd(msg, cmd, args):
    cid, me = msg["chat"]["id"], msg["from"]
    if msg["chat"]["type"] not in ("group", "supergroup"):
        return say(cid, "Ye command sirf group mein chalta hai 😅")
    if cmd == "kickme":
        if is_admin(cid, me["id"]):
            return say(cid, "Admin ko main kick nahi kar sakti 🥺")
        return result(cid, kick(cid, me["id"]), "Bye bye 👋")
    if not is_admin(cid, me["id"]):
        return say(cid, "Ye sirf admins ke liye hai 🙅‍♀️")
    uid, name, rest = resolve_target(msg, args)
    if cmd == "dban" and not msg.get("reply_to_message"):
        return say(cid, "/dban sirf reply karke use karo.")
    if not uid:
        return say(cid, "User batao: reply karo, @username ya ID do.")
    who = mention(uid, name)
    dur = parse_duration(rest[0]) if rest else None
    if cmd in ("tmute", "tban", "tempadmin") and not dur:
        return say(cid, "Time do, jaise <code>30m</code>, <code>3h</code> ya <code>2d</code>.")

    if cmd == "ban":
        result(cid, tg("banChatMember", chat_id=cid, user_id=uid), f"🚫 {who} ban ho gaya.")
    elif cmd == "unban":
        result(cid, tg("unbanChatMember", chat_id=cid, user_id=uid, only_if_banned=True), f"✅ {who} unban ho gaya.")
    elif cmd == "kick":
        result(cid, kick(cid, uid), f"👢 {who} ko nikaal diya.")
    elif cmd == "mute":
        result(cid, tg("restrictChatMember", chat_id=cid, user_id=uid, permissions={"can_send_messages": False}),
               f"🔇 {who} mute ho gaya.")
    elif cmd == "tmute":
        result(cid, tg("restrictChatMember", chat_id=cid, user_id=uid, permissions={"can_send_messages": False},
                       until_date=int(time.time()) + dur), f"🔇 {who} {rest[0]} ke liye mute.")
    elif cmd == "unmute":
        result(cid, tg("restrictChatMember", chat_id=cid, user_id=uid, permissions=ALL_PERMS),
               f"🔊 {who} unmute ho gaya.")
    elif cmd == "tban":
        result(cid, tg("banChatMember", chat_id=cid, user_id=uid, until_date=int(time.time()) + dur),
               f"⏳ {who} {rest[0]} ke liye ban.")
    elif cmd == "sban":
        tg("deleteMessage", chat_id=cid, message_id=msg["message_id"])
        tg("banChatMember", chat_id=cid, user_id=uid)
    elif cmd == "dban":
        tg("deleteMessage", chat_id=cid, message_id=msg["reply_to_message"]["message_id"])
        tg("deleteMessage", chat_id=cid, message_id=msg["message_id"])
        result(cid, tg("banChatMember", chat_id=cid, user_id=uid), f"🗑 {who} ban + message delete.")
    elif cmd == "promote":
        result(cid, tg("promoteChatMember", chat_id=cid, user_id=uid, **LIMITED_ADMIN), f"📈 {who} ab admin hai.")
    elif cmd == "fullpromote":
        result(cid, tg("promoteChatMember", chat_id=cid, user_id=uid, **FULL_ADMIN), f"👑 {who} ko full admin rights mile.")
    elif cmd == "demote":
        result(cid, tg("promoteChatMember", chat_id=cid, user_id=uid, **NO_ADMIN), f"📉 {who} ab admin nahi raha.")
    elif cmd == "tempadmin":
        r = tg("promoteChatMember", chat_id=cid, user_id=uid, **LIMITED_ADMIN)
        if r.get("ok"):
            add_job({"chat": cid, "user": uid, "at": int(time.time()) + dur})
        result(cid, r, f"⏱ {who} {rest[0]} ke liye admin.")

MOD_CMDS = {"ban", "unban", "kick", "kickme", "mute", "tmute", "unmute", "tban", "sban", "dban",
            "promote", "fullpromote", "demote", "tempadmin"}

_last_jobs = [0]
def run_jobs(force=False):
    now = int(time.time())
    if not force and now - _last_jobs[0] < 15:
        return
    _last_jobs[0] = now
    for j in get_jobs():
        if j["at"] <= now:
            tg("promoteChatMember", chat_id=j["chat"], user_id=j["user"], **NO_ADMIN)
            del_job(j["id"])

def job_loop():
    while True:
        try:
            run_jobs(force=True)
        except Exception as e:
            print("job error:", e)
        time.sleep(20)

# ================= MAIN DISPATCH =================
def process_update(u):
    run_jobs()
    if "callback_query" in u:
        return on_callback(u["callback_query"])
    msg = u.get("message")
    if not msg or "from" not in msg:
        return
    user = msg["from"]
    if msg["chat"]["type"] != "private" and user.get("username"):
        set_user(user["username"], user["id"])
    text = msg.get("text") or ""
    if text.startswith("/"):
        parts = text.split()
        head = parts[0][1:]
        cmd, _, tag = head.partition("@")
        cmd = cmd.lower()
        if tag and tag.lower() != bot_username().lower():
            return
        args = parts[1:]
        if cmd == "start":
            return send_start(msg)
        if cmd in ("help", "commands"):
            return say(msg["chat"]["id"], PAGES["cmds"], reply_markup=pages_kb("cmds"))
        if cmd == "reset":
            cid = msg["chat"]["id"]
            key = str(cid) if msg["chat"]["type"] == "private" else f"{cid}:{user['id']}"
            del_history(key)
            return say(cid, "Chalo fresh start karte hain 😊 Hi!")
        if cmd in MOD_CMDS:
            return mod_cmd(msg, cmd, args)
        return
    if text:
        handle_chat(msg, text)
    elif msg["chat"]["type"] == "private":
        say(msg["chat"]["id"], "Mujhe abhi sirf text samajh aata hai cutie 😅")

# ================= POLLING (VPS / local) =================
def run_polling():
    tg("deleteWebhook")
    threading.Thread(target=job_loop, daemon=True).start()
    offset = 0
    print("Bot chalu hai (polling)...")
    while True:
        res = tg("getUpdates", offset=offset, timeout=30, allowed_updates=["message", "callback_query"])
        for u in res.get("result", []):
            offset = u["update_id"] + 1
            threading.Thread(target=lambda x=u: process_update(x), daemon=True).start()
        time.sleep(0.2)

if __name__ == "__main__":
    run_polling()
