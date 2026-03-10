import telebot
from telebot import types
import sqlite3
import os
from flask import Flask, request

TOKEN = os.getenv("8210579716:AAGtgHEAz3IDcB2mQH9T92Cg7zpSKG1zPj8")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

SUPER_ADMIN = 1331356868

conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS channels(username TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS categories(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,cat_id INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS apks(id INTEGER PRIMARY KEY AUTOINCREMENT,item_id INTEGER,file_id TEXT,photo_id TEXT,caption TEXT)")
conn.commit()

state = {}

def is_admin(uid):
    if uid == SUPER_ADMIN:
        return True
    cursor.execute("SELECT id FROM admins WHERE id=?", (uid,))
    return cursor.fetchone()

def check_sub(uid):

    cursor.execute("SELECT username FROM channels")
    ch = cursor.fetchall()

    for c in ch:

        try:

            m = bot.get_chat_member(c[0], uid)

            if m.status not in ["member","administrator","creator"]:
                return False

        except:
            return False

    return True
    @bot.message_handler(commands=["start"])
def start(m):

    uid = m.from_user.id

    cursor.execute("INSERT OR IGNORE INTO users VALUES(?)",(uid,))
    conn.commit()

    if not check_sub(uid):

        cursor.execute("SELECT username FROM channels")
        ch = cursor.fetchall()

        text = "❌ Avval kanallarga obuna bo‘ling\n\n"

        for i in ch:
            text += f"{i[0]}\n"

        bot.send_message(m.chat.id,text)
        return

    show_categories(m.chat.id)

def show_categories(chat):

    markup = types.InlineKeyboardMarkup()

    cursor.execute("SELECT * FROM categories")
    cats = cursor.fetchall()

    for c in cats:

        markup.add(types.InlineKeyboardButton(
            c[1],
            callback_data=f"cat_{c[0]}"
        ))

    bot.send_message(chat,"📂 Kategoriya tanlang",reply_markup=markup)

@bot.callback_query_handler(func=lambda c:c.data.startswith("cat_"))
def category(c):

    cid = c.data.split("_")[1]

    markup = types.InlineKeyboardMarkup()

    cursor.execute("SELECT * FROM items WHERE cat_id=?",(cid,))
    items = cursor.fetchall()

    for i in items:

        markup.add(types.InlineKeyboardButton(
            i[1],
            callback_data=f"item_{i[0]}"
        ))

    bot.send_message(c.message.chat.id,"📦 Tanlang",reply_markup=markup)

@bot.callback_query_handler(func=lambda c:c.data.startswith("item_"))
def item(c):

    iid = c.data.split("_")[1]

    cursor.execute("SELECT * FROM apks WHERE item_id=?",(iid,))
    f = cursor.fetchone()

    if not f:
        bot.send_message(c.message.chat.id,"❌ APK yo‘q")
        return

    bot.send_photo(c.message.chat.id,f[3],caption=f[4])
    bot.send_document(c.message.chat.id,f[2])
    @bot.message_handler(commands=["admin"])
def admin(m):

    if not is_admin(m.from_user.id):
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row("➕ Kategoriya","🗑 Kategoriya")
    markup.row("➕ Element","➕ APK")
    markup.row("📡 Kanallar","📢 Broadcast")
    markup.row("📊 Statistika","👥 Adminlar")

    bot.send_message(m.chat.id,"👑 Admin panel",reply_markup=markup)


@bot.message_handler(func=lambda m:m.text=="📊 Statistika")
def stats(m):

    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM categories")
    cats = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM items")
    items = cursor.fetchone()[0]

    bot.send_message(m.chat.id,f"""
👥 Userlar: {users}
📂 Kategoriya: {cats}
📦 Element: {items}
""")


@bot.message_handler(func=lambda m:m.text=="📢 Broadcast")
def bc(m):

    if not is_admin(m.from_user.id):
        return

    state[m.from_user.id] = "broadcast"

    bot.send_message(m.chat.id,"Xabar yuboring")


@bot.message_handler(func=lambda m:m.from_user.id in state)
def states(m):

    if state[m.from_user.id] == "broadcast":

        cursor.execute("SELECT id FROM users")
        users = cursor.fetchall()

        sent = 0

        for u in users:

            try:
                bot.send_message(u[0],m.text)
                sent += 1
            except:
                pass

        bot.send_message(m.chat.id,f"Yuborildi {sent}")

        del state[m.from_user.id]
        @bot.message_handler(func=lambda m:m.text=="👥 Adminlar")
def admin_menu(m):

    if m.from_user.id != SUPER_ADMIN:
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row("➕ Admin","🗑 Admin")
    markup.row("📋 Adminlar")

    bot.send_message(m.chat.id,"Admin boshqaruvi",reply_markup=markup)


@bot.message_handler(func=lambda m:m.text=="➕ Admin")
def add_admin(m):

    state[m.from_user.id] = "add_admin"

    bot.send_message(m.chat.id,"Admin ID yubor")


@bot.message_handler(func=lambda m:m.from_user.id in state and state[m.from_user.id]=="add_admin")
def save_admin(m):

    cursor.execute("INSERT INTO admins VALUES(?)",(m.text,))
    conn.commit()

    bot.send_message(m.chat.id,"Admin qo‘shildi")

    del state[m.from_user.id]


app = Flask(__name__)

@app.route(f"/{TOKEN}",methods=["POST"])
def webhook():

    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)

    bot.process_new_updates([update])

    return "ok",200


@app.route("/")
def index():
    return "Bot ishlayapti"


if __name__ == "__main__":

    bot.remove_webhook()

    bot.set_webhook(
        url="https://minecraft-mod-cgix.onrender.com" + TOKEN
    )

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT",10000))
    )
    
