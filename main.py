import telebot
from telebot import types
import sqlite3
import time
from flask import Flask, request

TOKEN = "8638161881:AAHRFk9sVr7c8f7xtnUyJF38sg0ODrbWW94"
OWNER_ID = 1331356868

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
username TEXT,
name TEXT,
join_time INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS admins(
id INTEGER PRIMARY KEY
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS mods(
code INTEGER PRIMARY KEY,
photo TEXT,
text TEXT,
file TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS channels(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT
)
""")

cur.execute("INSERT OR IGNORE INTO admins VALUES(?)",(OWNER_ID,))

db.commit()

def is_admin(uid):
    cur.execute("SELECT 1 FROM admins WHERE id=?",(uid,))
    return cur.fetchone()

def add_user(user):
    cur.execute(
        "INSERT OR IGNORE INTO users VALUES(?,?,?,?)",
        (user.id,user.username,user.first_name,int(time.time()))
    )
    db.commit()

def get_channels():
    cur.execute("SELECT username FROM channels")
    return [x[0] for x in cur.fetchall()]

def check_sub(user_id):
    for ch in get_channels():
        try:
            member = bot.get_chat_member(ch,user_id)
            if member.status in ["left","kicked"]:
                return False
        except:
            return False
    return True

def sub_keyboard():
    kb = types.InlineKeyboardMarkup()
    for ch in get_channels():
        kb.add(types.InlineKeyboardButton(ch,url="https://t.me/"+ch.replace("@","")))
    kb.add(types.InlineKeyboardButton("✅ Tekshirish",callback_data="check_sub"))
    return kb

@bot.callback_query_handler(func=lambda c:c.data=="check_sub")
def check_sub_callback(call):
    if check_sub(call.from_user.id):
        bot.answer_callback_query(call.id,"Tasdiqlandi")
        bot.send_message(call.message.chat.id,"Mod kodini yuboring")
    else:
        bot.answer_callback_query(call.id,"Avval obuna bo‘ling")

@bot.message_handler(commands=['start'])
def start(message):

    add_user(message.from_user)

    if not check_sub(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "Botdan foydalanish uchun kanallarga obuna bo‘ling",
            reply_markup=sub_keyboard()
        )
        return

    bot.send_message(message.chat.id,"Minecraft mod bot\n\nMod kodini yuboring")

@bot.message_handler(commands=['admin'])
def admin_panel(message):

    if not is_admin(message.from_user.id):
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("➕ Mod qo'shish","🗑 Mod o'chirish")
    kb.row("📊 Statistika","👥 Foydalanuvchilar")
    kb.row("📢 Broadcast","👑 Adminlar")
    kb.row("➕ Kanal qo'shish","🗑 Kanal o'chirish")
    kb.row("➕ Admin qo'shish","🗑 Admin o'chirish")

    bot.send_message(message.chat.id,"Admin panel",reply_markup=kb)

@bot.message_handler(func=lambda m:m.text=="📊 Statistika")
def stats(message):

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM mods")
    mods = cur.fetchone()[0]

    bot.send_message(message.chat.id,f"Userlar: {users}\nModlar: {mods}")

@bot.message_handler(func=lambda m:m.text=="👥 Foydalanuvchilar")
def users_list(message):

    cur.execute("SELECT id,username,name FROM users")

    users = cur.fetchall()

    text="Foydalanuvchilar:\n\n"

    for u in users:

        text += f"{u[2]} | @{u[1]} | {u[0]}\n"

    bot.send_message(message.chat.id,text)

@bot.message_handler(func=lambda m:m.text=="👑 Adminlar")
def admins(message):

    cur.execute("SELECT id FROM admins")

    a = cur.fetchall()

    text="Adminlar:\n\n"

    for i in a:
        text+=str(i[0])+"\n"

    bot.send_message(message.chat.id,text)

@bot.message_handler(func=lambda m:m.text=="➕ Admin qo'shish")
def add_admin(message):

    msg = bot.send_message(message.chat.id,"Admin ID yuboring")

    bot.register_next_step_handler(msg,save_admin)

def save_admin(message):

    cur.execute("INSERT OR IGNORE INTO admins VALUES(?)",(int(message.text),))
    db.commit()

    bot.send_message(message.chat.id,"Admin qo'shildi")

@bot.message_handler(func=lambda m:m.text=="➕ Kanal qo'shish")
def add_channel(message):

    msg = bot.send_message(message.chat.id,"@kanal yuboring")

    bot.register_next_step_handler(msg,save_channel)

def save_channel(message):

    cur.execute("INSERT INTO channels(username) VALUES(?)",(message.text,))
    db.commit()

    bot.send_message(message.chat.id,"Kanal qo'shildi")

@bot.message_handler(func=lambda m:m.text=="➕ Mod qo'shish")
def add_mod(message):

    msg = bot.send_message(message.chat.id,"Mod kodini yuboring")

    bot.register_next_step_handler(msg,mod_code)

def mod_code(message):

    code=int(message.text)

    msg = bot.send_message(message.chat.id,"Rasm yuboring")

    bot.register_next_step_handler(msg,mod_photo,code)

def mod_photo(message,code):

    photo=message.photo[-1].file_id

    msg = bot.send_message(message.chat.id,"Tavsif yuboring")

    bot.register_next_step_handler(msg,mod_text,code,photo)

def mod_text(message,code,photo):

    text=message.text

    msg = bot.send_message(message.chat.id,"Mod fayl yuboring")

    bot.register_next_step_handler(msg,mod_file,code,photo,text)

def mod_file(message,code,photo,text):

    file_id=message.document.file_id

    cur.execute(
        "INSERT OR REPLACE INTO mods VALUES(?,?,?,?)",
        (code,photo,text,file_id)
    )

    db.commit()

    bot.send_message(message.chat.id,"Mod qo'shildi")

@bot.message_handler(func=lambda m:m.text=="🗑 Mod o'chirish")
def del_mod(message):

    msg = bot.send_message(message.chat.id,"Mod kodini yuboring")

    bot.register_next_step_handler(msg,delete_mod)

def delete_mod(message):

    cur.execute(
        "DELETE FROM mods WHERE code=?",
        (int(message.text),)
    )

    db.commit()

    bot.send_message(message.chat.id,"Mod o'chirildi")

@bot.message_handler(func=lambda m:m.text=="📢 Broadcast")
def broadcast(message):

    msg = bot.send_message(message.chat.id,"Xabar yuboring")

    bot.register_next_step_handler(msg,send_all)

def send_all(message):

    cur.execute("SELECT id FROM users")

    users=cur.fetchall()

    for u in users:

        try:
            bot.send_message(u[0],message.text)
        except:
            pass

    bot.send_message(message.chat.id,"Yuborildi")

@bot.message_handler(func=lambda m:m.text.isdigit())
def send_mod(message):

    code=int(message.text)

    cur.execute("SELECT photo,text,file FROM mods WHERE code=?",(code,))

    mod = cur.fetchone()

    if not mod:

        bot.send_message(message.chat.id,"Mod topilmadi")
        return

    photo,text,file_id=mod

    bot.send_photo(message.chat.id,photo,caption=text)

    bot.send_document(message.chat.id,file_id)

@app.route('/'+TOKEN, methods=['POST'])
def webhook():

    json_str = request.get_data().decode('UTF-8')

    update = telebot.types.Update.de_json(json_str)

    bot.process_new_updates([update])

    return "ok", 200

@app.route('/')
def index():
    return "Bot ishlayapti"

bot.remove_webhook()

bot.set_webhook(url="https://minecraft-mod-3.onrender.com/"+TOKEN)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


@app.route('/')
def index():
    return "Bot ishlayapti", 200
    if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
