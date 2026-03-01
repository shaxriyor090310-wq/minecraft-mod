import telebot
from telebot import types
import sqlite3
import os
import time

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ====== SUPER ADMIN ======
SUPER_ADMIN = 123456789  # <-- O'ZINGNI ID yoz

# ====== DATABASE ======
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS admins(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS categories(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS items(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS files(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    caption TEXT,
    photo_id TEXT,
    file_id TEXT
)
""")

conn.commit()

admin_state = {}

# ====== ADMIN TEKSHIRISH ======
def is_admin(user_id):
    if user_id == SUPER_ADMIN:
        return True
    cursor.execute("SELECT user_id FROM admins WHERE user_id=?", (user_id,))
    return cursor.fetchone() is not None


# ====== OBUNA TEKSHIRISH ======
def check_subscription(user_id):
    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()

    for ch in channels:
        try:
            member = bot.get_chat_member(ch[0], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True
    @bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

    if not check_subscription(user_id):
        cursor.execute("SELECT username FROM channels")
        channels = cursor.fetchall()

        text = "❌ <b>Avval quyidagi kanallarga obuna bo‘ling:</b>\n\n"
        for ch in channels:
            text += f"{ch[0]}\n"

        return bot.send_message(message.chat.id, text)

    show_main_menu(message.chat.id)
    def show_main_menu(chat_id):
    markup = types.InlineKeyboardMarkup()

    cursor.execute("SELECT id,name FROM categories")
    cats = cursor.fetchall()

    for c in cats:
        markup.add(types.InlineKeyboardButton(c[1], callback_data=f"cat_{c[0]}"))

    bot.send_message(chat_id, "🎮 <b>Tanlang:</b>", reply_markup=markup)
    @bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def open_category(call):
    if not check_subscription(call.from_user.id):
        return bot.answer_callback_query(call.id, "❌ Avval obuna bo‘ling")

    cat_id = int(call.data.split("_")[1])

    markup = types.InlineKeyboardMarkup()
    cursor.execute("SELECT id,name FROM items WHERE category_id=?", (cat_id,))
    items = cursor.fetchall()

    for item in items:
        markup.add(types.InlineKeyboardButton(item[1], callback_data=f"item_{item[0]}"))

    bot.send_message(call.message.chat.id, "📦 Tanlang:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("item_"))
def open_item(call):
    if not check_subscription(call.from_user.id):
        return bot.answer_callback_query(call.id, "❌ Avval obuna bo‘ling")

    item_id = int(call.data.split("_")[1])

    cursor.execute("SELECT caption,photo_id,file_id FROM files WHERE item_id=?", (item_id,))
    data = cursor.fetchone()

    if not data:
        return bot.send_message(call.message.chat.id, "⚠️ APK topilmadi")

    bot.send_photo(call.message.chat.id, data[1], caption=data[0])
    bot.send_document(call.message.chat.id, data[2])
    @bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        return

    markup = types.InlineKeyboardMarkup(row_width=2)

    markup.add(
        types.InlineKeyboardButton("➕ Kategoriya", callback_data="add_category"),
        types.InlineKeyboardButton("➕ Element", callback_data="add_item")
    )

    markup.add(
        types.InlineKeyboardButton("➕ APK", callback_data="add_file"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")
    )

    markup.add(
        types.InlineKeyboardButton("📡 Kanallar", callback_data="manage_channels"),
        types.InlineKeyboardButton("📊 Statistika", callback_data="stats")
    )

    if message.from_user.id == SUPER_ADMIN:
        markup.add(types.InlineKeyboardButton("👥 Adminlar", callback_data="manage_admins"))

    bot.send_message(message.chat.id, "👑 <b>Admin Panel</b>", reply_markup=markup)
    @bot.callback_query_handler(func=lambda c: c.data == "add_category")
def add_category(call):
    if not is_admin(call.from_user.id):
        return
    admin_state[call.from_user.id] = {"step": "category_name"}
    bot.send_message(call.message.chat.id, "Kategoriya nomini yuboring:")


@bot.message_handler(func=lambda m: m.from_user.id in admin_state and admin_state[m.from_user.id]["step"] == "category_name")
def save_category(message):
    cursor.execute("INSERT INTO categories(name) VALUES(?)", (message.text,))
    conn.commit()
    del admin_state[message.from_user.id]
    bot.send_message(message.chat.id, "✅ Kategoriya qo‘shildi")
    @bot.callback_query_handler(func=lambda c: c.data == "add_item")
def choose_category_for_item(call):
    if not is_admin(call.from_user.id):
        return

    markup = types.InlineKeyboardMarkup()
    cursor.execute("SELECT id,name FROM categories")
    cats = cursor.fetchall()

    for c in cats:
        markup.add(types.InlineKeyboardButton(c[1], callback_data=f"itemcat_{c[0]}"))

    bot.send_message(call.message.chat.id, "Qaysi kategoriya?", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("itemcat_"))
def add_item_name(call):
    cat_id = int(call.data.split("_")[1])
    admin_state[call.from_user.id] = {"step": "item_name", "cat_id": cat_id}
    bot.send_message(call.message.chat.id, "Element nomini yuboring:")


@bot.message_handler(func=lambda m: m.from_user.id in admin_state and admin_state[m.from_user.id]["step"] == "item_name")
def save_item(message):
    data = admin_state[message.from_user.id]
    cursor.execute("INSERT INTO items(name,category_id) VALUES(?,?)",
                   (message.text, data["cat_id"]))
    conn.commit()
    del admin_state[message.from_user.id]
    bot.send_message(message.chat.id, "✅ Element qo‘shildi")
    @bot.callback_query_handler(func=lambda c: c.data == "add_file")
def choose_item_for_file(call):
    if not is_admin(call.from_user.id):
        return

    markup = types.InlineKeyboardMarkup()
    cursor.execute("SELECT id,name FROM items")
    items = cursor.fetchall()

    for item in items:
        markup.add(types.InlineKeyboardButton(item[1], callback_data=f"fileitem_{item[0]}"))

    bot.send_message(call.message.chat.id, "Qaysi elementga?", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("fileitem_"))
def ask_caption(call):
    item_id = int(call.data.split("_")[1])
    admin_state[call.from_user.id] = {"step": "file_caption", "item_id": item_id}
    bot.send_message(call.message.chat.id, "Caption yuboring:")


@bot.message_handler(func=lambda m: m.from_user.id in admin_state and admin_state[m.from_user.id]["step"] == "file_caption")
def save_caption(message):
    admin_state[message.from_user.id]["caption"] = message.text
    admin_state[message.from_user.id]["step"] = "file_photo"
    bot.send_message(message.chat.id, "Rasm yuboring:")


@bot.message_handler(content_types=['photo'])
def save_photo(message):
    if message.from_user.id not in admin_state:
        return
    if admin_state[message.from_user.id]["step"] != "file_photo":
        return

    admin_state[message.from_user.id]["photo_id"] = message.photo[-1].file_id
    admin_state[message.from_user.id]["step"] = "file_doc"
    bot.send_message(message.chat.id, "APK fayl yuboring:")


@bot.message_handler(content_types=['document'])
def save_file(message):
    if message.from_user.id not in admin_state:
        return
    if admin_state[message.from_user.id]["step"] != "file_doc":
        return

    data = admin_state[message.from_user.id]

    cursor.execute("""
    INSERT INTO files(item_id,caption,photo_id,file_id)
    VALUES(?,?,?,?)
    """, (data["item_id"], data["caption"],
          data["photo_id"], message.document.file_id))

    conn.commit()
    del admin_state[message.from_user.id]

    bot.send_message(message.chat.id, "✅ APK qo‘shildi")
    @bot.callback_query_handler(func=lambda c: c.data == "manage_channels")
def add_channel(call):
    if not is_admin(call.from_user.id):
        return
    admin_state[call.from_user.id] = {"step": "channel_add"}
    bot.send_message(call.message.chat.id, "Kanal username yuboring (@kanal):")


@bot.message_handler(func=lambda m: m.from_user.id in admin_state and admin_state[m.from_user.id]["step"] == "channel_add")
def save_channel(message):
    cursor.execute("INSERT INTO channels(username) VALUES(?)", (message.text,))
    conn.commit()
    del admin_state[message.from_user.id]
    bot.send_message(message.chat.id, "✅ Kanal qo‘shildi")
    @bot.callback_query_handler(func=lambda c: c.data == "stats")
def show_stats(call):
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM categories")
    cats = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM items")
    items = cursor.fetchone()[0]

    bot.send_message(call.message.chat.id,
                     f"👥 Userlar: {users}\n📂 Kategoriya: {cats}\n📦 Element: {items}")
                     @bot.callback_query_handler(func=lambda c: c.data == "manage_admins")
def ask_admin_id(call):
    if call.from_user.id != SUPER_ADMIN:
        return
    admin_state[call.from_user.id] = {"step": "add_admin"}
    bot.send_message(call.message.chat.id, "Yangi admin ID yuboring:")


@bot.message_handler(func=lambda m: m.from_user.id in admin_state and admin_state[m.from_user.id]["step"] == "add_admin")
def save_admin(message):
    cursor.execute("INSERT OR IGNORE INTO admins(user_id) VALUES(?)", (int(message.text),))
    conn.commit()
    del admin_state[message.from_user.id]
    bot.send_message(message.chat.id, "✅ Admin qo‘shildi")
    @bot.callback_query_handler(func=lambda c: c.data == "broadcast")
def ask_broadcast(call):
    if not is_admin(call.from_user.id):
        return

    admin_state[call.from_user.id] = {"step": "broadcast"}
    bot.send_message(call.message.chat.id, "Yuboriladigan postni yuboring")


@bot.message_handler(func=lambda m: m.from_user.id in admin_state and admin_state[m.from_user.id]["step"] == "broadcast",
                     content_types=['text','photo','document'])
def send_broadcast(message):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    success = 0
    failed = 0

    for user in users:
        try:
            if message.content_type == "text":
                bot.send_message(user[0], message.text)
            elif message.content_type == "photo":
                bot.send_photo(user[0], message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == "document":
                bot.send_document(user[0], message.document.file_id, caption=message.caption)

            success += 1
            time.sleep(0.05)  # 100k safe delay

        except:
            failed += 1
            cursor.execute("DELETE FROM users WHERE user_id=?", (user[0],))
            conn.commit()

    del admin_state[message.from_user.id]

    bot.send_message(message.chat.id,
                     f"✅ Yuborildi: {success}\n❌ Xato: {failed}")
                     @bot.callback_query_handler(func=lambda c: c.data == "delete_category")
def delete_category_menu(call):
    if not is_admin(call.from_user.id):
        return

    markup = types.InlineKeyboardMarkup()
    cursor.execute("SELECT id,name FROM categories")
    cats = cursor.fetchall()

    for c in cats:
        markup.add(types.InlineKeyboardButton(c[1], callback_data=f"delcat_{c[0]}"))

    bot.send_message(call.message.chat.id, "O‘chirish uchun tanlang:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("delcat_"))
def delete_category(call):
    cat_id = int(call.data.split("_")[1])

    cursor.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    cursor.execute("DELETE FROM items WHERE category_id=?", (cat_id,))
    conn.commit()

    bot.send_message(call.message.chat.id, "🗑 Kategoriya o‘chirildi")
    @bot.callback_query_handler(func=lambda c: c.data == "remove_admin")
def remove_admin_menu(call):
    if call.from_user.id != SUPER_ADMIN:
        return

    markup = types.InlineKeyboardMarkup()
    cursor.execute("SELECT user_id FROM admins")
    admins = cursor.fetchall()

    for a in admins:
        markup.add(types.InlineKeyboardButton(str(a[0]), callback_data=f"deladmin_{a[0]}"))

    bot.send_message(call.message.chat.id, "O‘chirish uchun admin:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("deladmin_"))
def delete_admin(call):
    if call.from_user.id != SUPER_ADMIN:
        return

    admin_id = int(call.data.split("_")[1])

    cursor.execute("DELETE FROM admins WHERE user_id=?", (admin_id,))
    conn.commit()

    bot.send_message(call.message.chat.id, "🗑 Admin o‘chirildi")
    print("🚀 Production Bot ishga tushdi...")
from flask import Flask, request

app = Flask(__name__)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "ok", 200

@app.route("/")
def index():
    return "Bot ishlayapti"

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://minecraft-mod-cgix.onrender.com{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
