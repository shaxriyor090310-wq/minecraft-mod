import telebot
from telebot import types
import sqlite3
import time

TOKEN = "8210579716:AAGtgHEAz3IDcB2mQH9T92Cg7zpSKG1zPj8"
OWNER_ID = 1331356868

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, join_time INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS mods(code INTEGER PRIMARY KEY, photo TEXT, text TEXT, file TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS channels(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT)")

cur.execute("INSERT OR IGNORE INTO admins VALUES(?)",(OWNER_ID,))

cur.execute("CREATE INDEX IF NOT EXISTS idx_users ON users(id)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_mods ON mods(code)")

db.commit()


def is_admin(uid):
    cur.execute("SELECT 1 FROM admins WHERE id=?",(uid,))
    return cur.fetchone()


def add_user(uid):
    cur.execute("INSERT OR IGNORE INTO users VALUES(?,?)",(uid,int(time.time())))
    db.commit()


def get_channels():
    cur.execute("SELECT username FROM channels")
    return [x[0] for x in cur.fetchall()]


def check_sub(user_id):

    channels = get_channels()

    for ch in channels:
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
        kb.add(types.InlineKeyboardButton("🔗 "+ch,url="https://t.me/"+ch.replace("@","")))

    kb.add(types.InlineKeyboardButton("✅ Tekshirish",callback_data="check_sub"))

    return kb


@bot.callback_query_handler(func=lambda c:c.data=="check_sub")
def check_sub_callback(call):

    if check_sub(call.from_user.id):
        bot.answer_callback_query(call.id,"✅ Obuna tasdiqlandi")
        bot.send_message(call.message.chat.id,"Mod kodini yuboring")
    else:
        bot.answer_callback_query(call.id,"❌ Hali obuna bo‘lmagansiz")


@bot.message_handler(commands=['start'])
def start(message):

    add_user(message.from_user.id)

    if not check_sub(message.from_user.id):

        bot.send_message(
            message.chat.id,
            "🔒 Botdan foydalanish uchun kanallarga obuna bo‘ling",
            reply_markup=sub_keyboard()
        )
        return

    bot.send_message(message.chat.id,"🎮 Minecraft mod bot\n\nMod kodini yuboring")


@bot.message_handler(commands=['admin'])
def admin_panel(message):

    if not is_admin(message.from_user.id):
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("➕ Mod qo'shish","🗑 Mod o'chirish")
    kb.row("📊 Statistika","👥 Foydalanuvchilar")
    kb.row("📢 Broadcast")
    kb.row("➕ Kanal qo'shish","🗑 Kanal o'chirish")
    kb.row("➕ Admin qo'shish","🗑 Admin o'chirish")

    bot.send_message(message.chat.id,"👑 Admin panel",reply_markup=kb)


@bot.message_handler(func=lambda m:m.text=="📊 Statistika")
def stats(message):

    if not is_admin(message.from_user.id):
        return

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM mods")
    mods = cur.fetchone()[0]

    bot.send_message(message.chat.id,f"👥 Userlar: {users}\n📦 Modlar: {mods}")


@bot.message_handler(func=lambda m:m.text=="👥 Foydalanuvchilar")
def users_list(message):

    if not is_admin(message.from_user.id):
        return

    cur.execute("SELECT id FROM users LIMIT 50")
    users = cur.fetchall()

    text="👥 Oxirgi foydalanuvchilar:\n\n"

    for u in users:
        text+=str(u[0])+"\n"

    bot.send_message(message.chat.id,text)


@bot.message_handler(func=lambda m:m.text=="➕ Kanal qo'shish")
def add_channel(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(message.chat.id,"@kanal username yuboring")
    bot.register_next_step_handler(msg,save_channel)


def save_channel(message):

    username = message.text

    cur.execute("INSERT INTO channels(username) VALUES(?)",(username,))
    db.commit()

    bot.send_message(message.chat.id,"✅ Kanal qo'shildi")


@bot.message_handler(func=lambda m:m.text=="🗑 Kanal o'chirish")
def del_channel(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(message.chat.id,"O'chiriladigan kanal username yuboring")
    bot.register_next_step_handler(msg,delete_channel)


def delete_channel(message):

    username = message.text

    cur.execute("DELETE FROM channels WHERE username=?",(username,))
    db.commit()

    bot.send_message(message.chat.id,"🗑 Kanal o'chirildi")


@bot.message_handler(func=lambda m:m.text=="➕ Admin qo'shish")
def add_admin(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(message.chat.id,"Admin ID yuboring")
    bot.register_next_step_handler(msg,save_admin)


def save_admin(message):

    admin_id = int(message.text)

    cur.execute("INSERT OR IGNORE INTO admins VALUES(?)",(admin_id,))
    db.commit()

    bot.send_message(message.chat.id,"✅ Admin qo'shildi")


@bot.message_handler(func=lambda m:m.text=="🗑 Admin o'chirish")
def del_admin(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(message.chat.id,"O'chiriladigan admin ID yuboring")
    bot.register_next_step_handler(msg,delete_admin)


def delete_admin(message):

    admin_id = int(message.text)

    cur.execute("DELETE FROM admins WHERE id=?",(admin_id,))
    db.commit()

    bot.send_message(message.chat.id,"🗑 Admin o'chirildi")


@bot.message_handler(func=lambda m:m.text=="➕ Mod qo'shish")
def add_mod(message):

    if not is_admin(message.from_user.id):
        return

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

    cur.execute("INSERT OR REPLACE INTO mods VALUES(?,?,?,?)",(code,photo,text,file_id))
    db.commit()

    bot.send_message(message.chat.id,"✅ Mod qo'shildi")


@bot.message_handler(func=lambda m:m.text=="🗑 Mod o'chirish")
def del_mod(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(message.chat.id,"Mod kodini yuboring")
    bot.register_next_step_handler(msg,delete_mod)


def delete_mod(message):

    code=int(message.text)

    cur.execute("DELETE FROM mods WHERE code=?",(code,))
    db.commit()

    bot.send_message(message.chat.id,"🗑 Mod o'chirildi")


@bot.message_handler(func=lambda m:m.text=="📢 Broadcast")
def broadcast(message):

    if not is_admin(message.from_user.id):
        return

    msg = bot.send_message(message.chat.id,"Xabar yuboring")
    bot.register_next_step_handler(msg,send_all)


def send_all(message):

    cur.execute("SELECT id FROM users")
    users = cur.fetchall()

    for u in users:
        try:
            bot.send_message(u[0],message.text)
        except:
            pass

    bot.send_message(message.chat.id,"✅ Yuborildi")


@bot.message_handler(func=lambda m:m.text.isdigit())
def send_mod(message):

    if not check_sub(message.from_user.id):

        bot.send_message(
            message.chat.id,
            "🔒 Kanallarga obuna bo‘ling",
            reply_markup=sub_keyboard()
        )
        return

    code=int(message.text)

    cur.execute("SELECT photo,text,file FROM mods WHERE code=?",(code,))
    mod=cur.fetchone()

    if not mod:
        bot.send_message(message.chat.id,"❌ Mod topilmadi")
        return

    photo,text,file_id = mod

    bot.send_photo(message.chat.id,photo,caption=text)
    bot.send_document(message.chat.id,file_id)


bot.infinity_polling()
