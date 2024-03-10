import os
import random
import time
import requests
from database import *
from config import *
from telebot import TeleBot
from keyboards import *
import threading
import schedule
import openai

bot = TeleBot(token, disable_web_page_preview=True, parse_mode="html")
connect()
openai.api_key = openaiToken
model = "gpt-4-1106-preview"


def checkSub(channel_id, user_id):
    try:
        x = bot.get_chat_member(channel_id, user_id)
        if x.status in ["member", "administrator", "creator"]:
            return True
        return False
    except:
        return False


def ask_chat_thread(message):
    if message.chat.id > 0:
        return bot.send_message(message.chat.id, "Эта команда используется только в чатах!")
    if len(message.text.split()) == 1:
        return bot.send_message(message.chat.id, "Вы забыли указать вопрос!")
    question = message.text.split(" ", 1)[1]
    user_id = message.from_user.id
    username = "" if not message.from_user.username else message.from_user.username
    if not Users.select().where(Users.user_id == user_id).exists():
        Users.create(user_id=user_id, username=username)
    userInfo = Users.select().where(Users.user_id == user_id)[0]
    if userInfo.qLeft + userInfo.qReferal <= 0:
        return bot.send_message(message.chat.id, "К сожалению, у вас закончились бесплатные запросы.",
                                reply_markup=menuUser)
    if userInfo.qLeft > 0:
        Users.update(qLeft=userInfo.qLeft - 1).where(Users.user_id == userInfo.user_id).execute()
    else:
        Users.update(qReferal=userInfo.qReferal - 1).where(Users.user_id == userInfo.user_id).execute()
    history = [{"role": "user", "content": question}]
    msg = bot.reply_to(message, "Пожалуйста, подождите...")
    response = openai.chat.completions.create(
        model=model,
        messages=history
    )
    text = response.choices[0].message.content.strip()
    if Ads.select():
        ad = random.choice(Ads.select())
        Ads.update(views=ad.views+1).where(Ads.name == ad.name).execute()
        text += f"\n\n{ad.text}"
    bot.edit_message_text(text, msg.chat.id, msg.message_id, parse_mode="")


def generate_chat(message):
    if message.chat.id > 0:
        return bot.send_message(message.chat.id, "Эта команда используется только в чате!")
    if len(message.text.split()) == 1:
        return bot.send_message(message.chat.id, "Вы забыли указать вопрос!")
    question = message.text.split(" ", 1)[1]
    user_id = message.from_user.id
    username = "" if not message.from_user.username else message.from_user.username
    if not Users.select().where(Users.user_id == user_id).exists():
        Users.create(user_id=user_id, username=username)
    userInfo = Users.select().where(Users.user_id == user_id)[0]
    if userInfo.qLeft + userInfo.qReferal <= 2:
        return bot.send_message(message.chat.id, "К сожалению, у вас закончились бесплатные запросы.")
    if userInfo.qLeft > 2:
        Users.update(qLeft=userInfo.qLeft - 3).where(Users.user_id == message.from_user.id).execute()
    elif userInfo.qLeft == 2:
        Users.update(qLeft=0, qReferal=userInfo.qReferal - 1).where(Users.user_id == message.from_user.id).execute()
    elif userInfo.qLeft == 1:
        Users.update(qLeft=0, qReferal=userInfo.qReferal - 2).where(Users.user_id == message.from_user.id).execute()
    else:
        Users.update(qReferal=userInfo.qReferal - 3).where(Users.user_id == message.from_user.id).execute()
    msg = bot.send_message(message.chat.id, """Пожалуйста, подождите, это может занять некоторое время...
<i>(Приблизительно 10-45 сек)</i>""")
    response = openai.images.generate(
        model="dall-e-3",
        prompt=question,
        size="1024x1024",
        quality="standard"
    )
    image_url = response.data[0].url
    response = requests.get(image_url)
    with open(f"{message.message_id}.jpg", "wb") as f:
        f.write(response.content)
    text = "Вот ваша фотография!"
    if Ads.select():
        ad = random.choice(Ads.select())
        Ads.update(views=ad.views + 1).where(Ads.name == ad.name).execute()
        text += f"\n\n{ad.text}"
    with open(f"{message.message_id}.jpg", "rb") as f:
        bot.send_photo(message.chat.id, f, text, reply_to_message_id=message.message_id)
    bot.delete_message(msg.chat.id, msg.message_id)
    os.remove(f"{message.message_id}.jpg")


def menuAdmin(user_id):
    userInfo = Users.select().where(Users.user == user_id)[0]
    menuAdmin = types.ReplyKeyboardMarkup(True)
    menuAdmin.add("Рассылка").add("Пользователи").add("Статистика").add("Изменить сообщение старт").add("Реклама").add("Каналы")
    if userInfo.status == "owner":
        menuAdmin.add("Добавить менеджера").add("Передать права")
    return menuAdmin


@bot.message_handler(commands=['admin'])
def admin(message: types.Message):
    userInfo = Users.select().where(Users.user_id == message.chat.id)[0]
    if not userInfo.status:
        return start(message)
    bot.send_message(message.chat.id, "Открываю админку", reply_markup=menuAdmin(message.chat.id))


@bot.message_handler(commands=['ask'])
def ask_question(message: types.Message):
    threading.Thread(target=ask_chat_thread, args=(message, )).start()


@bot.message_handler(commands=['generate'])
def generate_photo(message: types.Message):
    threading.Thread(target=generate_chat, args=(message, )).start()


@bot.message_handler(commands=['restart'])
def restart_conversations(message: types.Message):
    if message.chat.id < 0:
        return
    Conversations.update(status=False).where(Conversations.owner_id == Users.select().where(Users.user_id == message.chat.id)[0]).execute()
    bot.send_message(message.chat.id, "Отлично! Ваш контекст очищен.")


@bot.message_handler(content_types=['new_chat_members'])
def added_chat(message: types.Message):
    bot.send_message(message.chat.id, "Спасибо, что добавили в чат! Для работы выдайте права администратора.")
    Chats.create(chat_id=message.chat.id)


@bot.message_handler(commands=['start'])
def start(message: types.Message):
    if message.chat.id < 0:
        return
    if not message.chat.username:
        return bot.send_message(message.chat.id, "Для пользования ботом установите username.")
    if not Users.select().where(Users.user_id == message.chat.id).exists():
        referal = 0
        if len(message.text.split()) == 2:
            if message.text.split()[1].isdigit() and Users.select().where(Users.user_id == int(message.text.split()[1])).exists():
                referal = int(message.text.split()[1])
                refInfo = Users.select().where(Users.user_id == referal)[0]
                Users.update(qReferal=refInfo.qReferal+5).where(Users.user_id == referal).execute()
                try:
                    bot.send_message(referal, "<b>Вам начислено 5 бонусных запросов!</b>")
                except:
                    pass
        Users.create(user_id=message.chat.id, referal=referal)
    Users.update(username=message.chat.username).where(Users.user_id == message.chat.id).execute()
    userInfo = Users.select().where(Users.user_id == message.chat.id)[0]
    if userInfo.blocked:
        return bot.send_message(message.chat.id, "Вы заблокированы!")
    channels = Channels.select()
    flag = True
    for channel in channels:
        if not checkSub(channel.channel_id, message.chat.id):
            flag = False
    if not flag:
        kb = types.InlineKeyboardMarkup()
        for channel in channels:
            kb.add(
                types.InlineKeyboardButton(text="Подписаться", url=channel.link)
            )
        return bot.send_message(message.chat.id, "Подпишитесь на все каналы ниже, затем заново напишите /start.", reply_markup=kb)
    with open("mainText.txt", "r", encoding="utf-8") as file:
        photo, text = file.read().split("\n", 1)
    addChat = types.InlineKeyboardMarkup()
    addChat.add(
        types.InlineKeyboardButton(text="Добавить бота в чат", url=f"https://t.me/{bot.get_me().username}?startgroup=start")
    )
    bot.send_message(message.chat.id, "✏️", reply_markup=menuUser)
    if photo and os.path.exists(photo):
        with open(photo, "rb") as file:
            bot.send_photo(message.chat.id, file, caption=text, reply_markup=addChat)
    else:
        bot.send_message(message.chat.id, text, reply_markup=addChat)


@bot.message_handler(content_types=['text'])
def dialogue(message: types.Message):
    if message.chat.id < 0:
        return
    if not message.chat.username:
        return bot.send_message(message.chat.id, "Для пользования ботом установите username.")
    if not Users.select().where((Users.user_id == message.chat.id) & (Users.username == message.chat.username)).exists():
        return bot.send_message(message.chat.id, "Напишите /start.")
    userInfo = Users.select().where(Users.user_id == message.chat.id)[0]
    if userInfo.blocked:
        return bot.send_message(message.chat.id, "Вы заблокированы!")
    channels = Channels.select()
    flag = True
    for channel in channels:
        if not checkSub(channel.channel_id, message.chat.id):
            flag = False
    if not flag:
        kb = types.InlineKeyboardMarkup()
        for channel in channels:
            kb.add(
                types.InlineKeyboardButton(text="Подписаться", url=channel.link)
            )
        return bot.send_message(message.chat.id, "Подпишитесь на все каналы ниже, затем повторите действие.",
                                reply_markup=kb)
    if message.text == "🚀 Задать вопрос":
        bot.send_message(message.chat.id, "Пожалуйста, напишите свой запрос одним сообщением 📍", reply_markup=menuGpt)
        bot.register_next_step_handler(message, talkGpt)
    elif message.text == "🖍 Создать картинку":
        bot.send_message(message.chat.id, "Опишите желаемую картинку одним предложением 📍", reply_markup=backMenu)
        bot.register_next_step_handler(message, createImage)
    elif message.text == "🥷 Профиль":
        bot.send_message(message.chat.id, f'''⚡️ Привет, <code>{message.chat.first_name}</code>!

<b>ID:</b> <code>{message.chat.id}</code>
<b>Осталось запросов:</b> <code>{userInfo.qLeft + userInfo.qReferal}</code>
<i>{userInfo.qLeft} ежедневных запросов, {userInfo.qReferal} бонусных</i>

<b>Твоя реферальная ссылка:https://t.me/{bot.get_me().username}?start={message.chat.id}
Количество активных рефералов:</b> {len(Users.select().where(Users.referal == message.chat.id))}

<i>"Каждый приглашённый человек даёт 5 бонусных запросов"</i>''')
    elif message.text == "📝 Помощь":
        bot.send_message(message.chat.id, "Выберите интересующий вас вопрос", reply_markup=menuFaq)
        bot.register_next_step_handler(message, openFaq)
    elif message.text == "🎯 Администрация":
        bot.send_message(message.chat.id, "По важным вопросам", reply_markup=showAdmin)
    elif message.text == "Рассылка" and (userInfo.status or message.chat.id in admins):
        kb = types.ReplyKeyboardMarkup(True)
        kb.add("Пользователи", "Чаты").add("Отмена")
        bot.send_message(message.chat.id, "Кому отправить сообщение", reply_markup=kb)
        bot.register_next_step_handler(message, selectSendAll)
    elif message.text == "Пользователи" and (userInfo.status or message.chat.id in admins):
        bot.send_message(message.chat.id, "Введите ID или username пользователя.", reply_markup=cancel)
        bot.register_next_step_handler(message, searchUser)
    elif message.text == "Статистика" and (userInfo.status or message.chat.id in admins):
        countChatsUsers = 0
        for chat in Chats.select():
            try:
                chat_info = bot.get_chat_member_count(chat.chat_id)
                countChatsUsers += chat_info
            except:
                pass
        text = f"""Статистика:

Пользователей в боте: {len(Users.select())}

Всего {len(Chats.select())} чатов
В сумме {countChatsUsers} людей в чатах

Всего пользователей: {len(Users.select()) + countChatsUsers}"""
        bot.send_message(message.chat.id, text)
    elif message.text == "Изменить сообщение старт" and (userInfo.status or message.chat.id in admins):
        bot.send_message(message.chat.id, "Введите новое сообщение для старта (можно с фото)", reply_markup=cancel)
        bot.register_next_step_handler(message, changeStart)
    elif message.text == "Реклама" and (userInfo.status or message.chat.id in admins):
        ads = Ads.select()
        kb = types.ReplyKeyboardMarkup(True)
        text = "Все рекламы на данный момент:\n"
        for ad in ads:
            kb.add(ad.name)
            text += f"\n{ad.name} - {ad.views} просмотров"
        text += "\nДля удаления рекламы нажмите на её название ниже"
        kb.add("Добавить рекламу").add("Отмена")
        bot.send_message(message.chat.id, text, reply_markup=kb)
        bot.register_next_step_handler(message, viewAds)
    elif message.text == "Каналы" and (userInfo.status or message.chat.id in admins):
        channels = Channels.select()
        kb = types.ReplyKeyboardMarkup(True)
        for channel in channels:
            name = bot.get_chat(channel.channel_id).first_name
            kb.add(f"{channel.channel_id} | | {name}")
        kb.add("Добавить канал").add("Отмена")
        bot.send_message(message.chat.id, "Для удаления канала нажмите на него.", reply_markup=kb)
        bot.register_next_step_handler(message, viewChannels)
    elif message.text == "Менеджеры" and message.chat.id in admins:
        bot.send_message(message.chat.id, "Введите ID пользователя кого сделать менеджером/убрать.", reply_markup=cancel)
        bot.register_next_step_handler(message, addManager)
    else:
        bot.send_message(message.chat.id, "Я тебя не понимаю. Выбери функцию из меню ниже.", reply_markup=menuUser)


def viewChannels(message):
    if not message.text or message.text == "Отмена":
        return admin(message)
    if message.text == "Добавить канал":
        bot.send_message(message.chat.id, "Введите айди канала", reply_markup=cancel)
        bot.register_next_step_handler(message, addChannel)
    elif " | | " in message.text:
        channel_id = message.text.split(" | | ", 1)[0]
        try:
            channel_id = int(channel_id)
        except:
            return admin(message)
        channel = Channels.select().where(Channels.channel_id == channel_id)
        if channel:
            channel[0].delete_instance()
        bot.send_message(message.chat.id, "Канал успешно удалён.")
    else:
        admin(message)


def addChannel(message):
    if not message.text or message.text == "Отмена":
        return admin(message)
    try:
        channel_id = int(message.text)
    except:
        return admin(message)
    if Channels.select().where(Channels.channel_id == channel_id).exists():
        return bot.send_message(message.chat.id, "Такой канал уже добавлен.", reply_markup=menuAdmin(message.chat.id))
    bot.send_message(message.chat.id, "Введите ссылку на канал", reply_markup=cancel)
    bot.register_next_step_handler(message, addChannelFinish, channel_id)


def addChannelFinish(message, channel_id):
    if not message.text or message.text == "Отмена":
        return admin(message)
    Channels.create(channel_id=channel_id, link=message.text)
    bot.send_message(message.chat.id, "Канал успешно добавлен.", reply_markup=menuAdmin(message.chat.id))


def addManager(message: types.Message):
    if not message.text or not message.text.isdigit():
        return admin(message)
    if not Users.select().where(Users.user_id == int(message.text)).exists():
        return bot.send_message(message.chat.id, "Не могу найти такого пользователя.", reply_markup=menuAdmin(message.chat.id))
    userInfo = Users.select().where(Users.user_id == int(message.text))[0]
    if userInfo.status == "manager":
        Users.update(status="").where(Users.user_id == int(message.text)).execute()
        return bot.send_message(message.chat.id, "Пользователь успешно снят с должности менеджера.", reply_markup=menuAdmin(message.chat.id))
    Users.update(status="manager").where(Users.user_id == int(message.text)).execute()
    bot.send_message(message.chat.id, "Пользователь успешно добавлен в менеджеры.", reply_markup=menuAdmin(message.chat.id))


def viewAds(message: types.Message):
    if not message.text or message.text == "Отмена":
        return admin(message)
    if Ads.select().where(Ads.name == message.text):
        Ads.select().where(Ads.name == message.text).delete_instance()
        bot.send_message(message.chat.id, "Реклама успешно удалена.", reply_markup=menuAdmin(message.chat.id))
    elif message.text == "Добавить рекламу":
        bot.send_message(message.chat.id, "Введите название рекламы (для понимания в админке)", reply_markup=cancel)
        bot.register_next_step_handler(message, addAd)
    else:
        admin(message)


def addAd(message):
    if not message.text or message.text == "Отмена":
        return admin(message)
    if Ads.select().where(Ads.name == message.text).exists():
        return bot.send_message(message.chat.id, "Такая реклама уже существует.", reply_markup=menuAdmin(message.chat.id))
    bot.send_message(message.chat.id, "Введите текст, который будет показывать.", reply_markup=cancel)
    bot.register_next_step_handler(message, addAdFinal, message.text)


def addAdFinal(message: types.Message, name):
    if not message.text or message.text == "Отмена":
        return admin(message)
    Ads.create(name=name, text=message.html_text)
    bot.send_message(message.chat.id, "Реклама успешно создана.", reply_markup=menuAdmin(message.chat.id))


def selectSendAll(message):
    if not message.text or message.text not in ["Пользователи", "Чаты"]:
        return admin(message)
    bot.send_message(message.chat.id, "Введите текст для рассылки", reply_markup=cancel)
    bot.register_next_step_handler(message, startSendAll, message.text.replace("Пользователи", "users").replace("Чаты", "chats"))


def changeStart(message: types.Message):
    if not (message.text or message.caption) or message.text == "Отмена":
        return admin(message)
    photo = ""
    with open("mainText.txt", "r", encoding="utf-8") as file:
        oldPhoto, oldText = file.read().split("\n", 1)
    if oldPhoto and os.path.exists(oldPhoto):
        os.remove(oldPhoto)
    if message.content_type == "photo":
        file = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file.file_path)
        with open(f"{message.message_id}.jpg", "wb") as wFile:
            wFile.write(downloaded_file)
        photo = f"{message.message_id}.jpg"
        text = message.html_caption
    else:
        text = message.html_text
    with open("mainText.txt", "w", encoding="utf-8") as file:
        file.write(f"{photo}\n{text}")
    bot.send_message(message.chat.id, "Текст успешно изменён.", reply_markup=menuAdmin(message.chat.id))


def searchUser(message: types.Message):
    if not message.text or message.text == "Отмена":
        return admin(message)
    if message.text.isdigit():
        users = Users.select().where(Users.user_id == int(message.text))
    else:
        username = message.text.replace("@", "")
        users = Users.select().where(Users.username == username)
    if not users.exists():
        return bot.send_message(message.chat.id, "К сожалению, не могу найти такого пользователя.", reply_markup=menuAdmin(message.chat.id))
    userInfo = users[0]
    text = f"""Профиль @{userInfo.username}

<b>ID:</b> <code>{userInfo.user_id}</code>
<b>Осталось запросов:</b> <code>{userInfo.qLeft + userInfo.qReferal}</code>
<i>{userInfo.qLeft} ежедневных запросов, {userInfo.qReferal} бонусных</i>
Выберите действие:"""
    kb = types.ReplyKeyboardMarkup(True)
    kb.add("Изменить кол-во запросов")
    if userInfo.blocked:
        kb.add("Разблокировать")
    else:
        kb.add("Заблокировать")
    kb.add("Отмена")
    bot.send_message(message.chat.id, text, reply_markup=kb)
    bot.register_next_step_handler(message, doUser, userInfo)


def doUser(message, userInfo):
    if not message.text or message.text == "Отмена":
        return admin(message)
    if message.text == "Заблокировать":
        Users.update(blocked=True).where(Users.id == userInfo.id).execute()
        return bot.send_message(message.chat.id, "Пользователь заблокирован.", reply_markup=menuAdmin(message.chat.id))
    elif message.text == "Разблокировать":
        Users.update(blocked=False).where(Users.id == userInfo.id).execute()
        return bot.send_message(message.chat.id, "Пользователь разблокирован.", reply_markup=menuAdmin(message.chat.id))
    if message.text == "Изменить кол-во запросов":
        bot.send_message(message.chat.id, "Введите новое кол-во запросов (изменятся только дневные)", reply_markup=cancel)
        bot.register_next_step_handler(message, changeQLeft, userInfo)
    else:
        admin(message)


def changeQLeft(message, userInfo):
    if not message.text or not message.text.isdigit():
        return admin(message)
    Users.update(qLeft=int(message.text)).where(Users.id == userInfo.id).execute()
    bot.send_message(message.chat.id, "Кол-во запросов успешно изменено.", reply_markup=menuAdmin(message.chat.id))


def sendAll(message, name, url, who="users"):
    if name and url:
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton(text=name, url=url)
        )
    else:
        kb = None
    bot.send_message(message.chat.id, "Рассылка началась.", reply_markup=menuAdmin(message.chat.id))
    count = [0, 0]
    if message.content_type == "text":
        if who == "users":
            for userInfo in Users.select():
                try:
                    bot.send_message(userInfo.user_id, message.html_text, reply_markup=kb)
                    count[0] += 1
                    time.sleep(0.3)
                except:
                    count[1] += 1
        else:
            for chatInfo in Chats.select():
                try:
                    bot.send_message(chatInfo.chat_id, message.html_text, reply_markup=kb)
                except:
                    pass
            time.sleep(0.3)
    elif message.content_type == "photo":
        file = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file.file_path)
        with open(f"{message.message_id}.jpg", "wb") as photo:
            photo.write(downloaded_file)
        if who == "users":
                for userInfo in Users.select():
                    try:
                        with open(f"{message.message_id}.jpg", "rb") as photo:
                            bot.send_photo(userInfo.user_id, photo, caption=message.html_caption or "", reply_markup=kb)
                        count[0] += 0
                        time.sleep(0.3)
                    except:
                        count[1] += 0
        else:
            for chatInfo in Chats.select():
                try:
                    with open(f"{message.message_id}.jpg", "rb") as photo:
                        bot.send_photo(chatInfo.chat_id, photo, caption=message.html_caption or "", reply_markup=kb)
                except:
                    pass
                time.sleep(0.3)
        os.remove(f"{message.message_id}.jpg")
    elif message.content_type == "video":
        file = bot.get_file(message.video.file_id)
        downloaded_file = bot.download_file(file.file_path)
        with open(message.video.file_name, "wb") as video:
            video.write(downloaded_file)
        if who == "users":
            for userInfo in Users.select():
                try:
                    with open(message.video.file_name, "rb") as video:
                        bot.send_video(userInfo.user_id, video, caption=message.html_caption or "", reply_markup=kb)
                    count[0] += 0
                    time.sleep(0.3)
                except:
                    count[1] += 0
        else:
            for chatInfo in Chats.select():
                try:
                    with open(message.video.file_name, "rb") as video:
                        bot.send_video(chatInfo.chat_id, video, caption=message.html_caption or "", reply_markup=kb)
                except:
                    pass
                time.sleep(0.3)
        os.remove(message.video.file_name)
    bot.send_message(message.chat.id, f"Рассылка закончена.\nДоставлено: {count[0]}. Не доставлено: {count[1]}")


def startSendAll(message: types.Message, who):
    if not (message.text or message.caption) or message.text == "Отмена":
        return admin(message)
    kb = types.ReplyKeyboardMarkup(True)
    kb.add("Пропустить").add("Отмена")
    bot.send_message(message.chat.id, "Введите название ссылки для кнопки под сообщением", reply_markup=kb)
    bot.register_next_step_handler(message, startSendAll2, message, who)


def startSendAll2(message, msg, who):
    if not message.text or message.text == "Отмена":
        return admin(message)
    if message.text == "Пропустить":
        return threading.Thread(target=sendAll, args=(msg, "", "", who, )).start()
    bot.send_message(message.chat.id, "Введите ссылку и рассылка начнётся.", reply_markup=cancel)
    bot.register_next_step_handler(message, startSendAllFinish, msg, message.text, who)


def startSendAllFinish(message, msg, name, who):
    if not message.text or message.text == "Отмена":
        return admin(message)
    threading.Thread(target=sendAll, args=(msg, name, message.text, who, )).start()


def createImageThread(message):
    userInfo = Users.select().where(Users.user_id == message.chat.id)[0]
    if userInfo.blocked:
        return bot.send_message(message.chat.id, "Вы заблокированы!")
    if not message.text or message.text == "В меню":
        return bot.send_message(message.chat.id, "Возвращаюсь в меню.", reply_markup=menuUser)
    if userInfo.qLeft + userInfo.qReferal <= 2:
        return bot.send_message(message.chat.id, "К сожалению, у вас закончились бесплатные запросы.",
                                reply_markup=menuUser)
    if userInfo.qLeft > 2:
        Users.update(qLeft=userInfo.qLeft - 3).where(Users.user_id == message.chat.id).execute()
    elif userInfo.qLeft == 2:
        Users.update(qLeft=0, qReferal=userInfo.qReferal - 1).where(Users.user_id == message.chat.id).execute()
    elif userInfo.qLeft == 1:
        Users.update(qLeft=0, qReferal=userInfo.qReferal - 2).where(Users.user_id == message.chat.id).execute()
    else:
        Users.update(qReferal=userInfo.qReferal - 3).where(Users.user_id == message.chat.id).execute()
    msg = bot.send_message(message.chat.id, """Пожалуйста, подождите, это может занять некоторое время...
<i>(Приблизительно 10-45 сек)</i>""")
    response = openai.images.generate(
        model="dall-e-3",
        prompt=message.text,
        size="1024x1024",
        quality="standard"
    )
    image_url = response.data[0].url
    response = requests.get(image_url)
    with open(f"{message.message_id}.jpg", "wb") as f:
        f.write(response.content)
    with open(f"{message.message_id}.jpg", "rb") as f:
        bot.send_photo(message.chat.id, f, "Вот ваша фотография!", reply_markup=menuUser)
    if Ads.select():
        ad = random.choice(Ads.select())
        Ads.update(views=ad.views + 1).where(Ads.name == ad.name).execute()
        bot.send_message(message.chat.id, ad.text)
    bot.delete_message(msg.chat.id, msg.message_id)
    os.remove(f"{message.message_id}.jpg")


def createImage(message: types.Message):
    threading.Thread(target=createImageThread, args=(message, )).start()


def talkGptThread(message):
    userInfo = Users.select().where(Users.user_id == message.chat.id)[0]
    if userInfo.blocked:
        return bot.send_message(message.chat.id, "Вы заблокированы!")
    if not message.text or message.text == "В меню":
        return bot.send_message(message.chat.id, "Возвращаюсь в меню.", reply_markup=menuUser)
    if message.text == "Сбросить контекст":
        Conversations.update(status=False).where(Conversations.owner_id == userInfo).execute()
        bot.send_message(message.chat.id, "Отлично! Можете задать новый вопрос 🔍")
        return bot.register_next_step_handler(message, talkGpt)
    if userInfo.qLeft + userInfo.qReferal <= 0:
        return bot.send_message(message.chat.id, "К сожалению, у вас закончились бесплатные запросы.",
                                reply_markup=menuUser)
    if userInfo.qLeft > 0:
        Users.update(qLeft=userInfo.qLeft - 1).where(Users.user_id == message.chat.id).execute()
    else:
        Users.update(qReferal=userInfo.qReferal - 1).where(Users.user_id == message.chat.id).execute()
    conversations = Conversations.select().where((Conversations.owner_id == userInfo) & (Conversations.status == True))
    if not conversations.exists():
        conversation = Conversations.create(owner_id=userInfo)
    else:
        conversation = conversations[0]
    messages = Messages.select().where(Messages.conversation == conversation)
    history = []
    Messages.create(conversation=conversation, text=message.text)
    for msg in messages:
        history.append({"role": msg.role, "content": msg.text})
    msg = bot.send_message(message.chat.id, "Пожалуйста, подождите...")
    response = openai.chat.completions.create(
        model=model,
        messages=history
    )
    Messages.create(conversation=conversation, role=response.choices[0].message.role,
                    text=response.choices[0].message.content.strip())
    bot.edit_message_text(response.choices[0].message.content.strip(), msg.chat.id, msg.message_id, parse_mode="")
    if Ads.select():
        ad = random.choice(Ads.select())
        Ads.update(views=ad.views + 1).where(Ads.name == ad.name).execute()
        bot.send_message(message.chat.id, ad.text)
    bot.register_next_step_handler(message, talkGpt)


def talkGpt(message: types.Message):
    threading.Thread(target=talkGptThread, args=(message, )).start()


def openFaq(message: types.Message):
    if not message.text or message.text == "Назад":
        return bot.send_message(message.chat.id, "Возвращаюсь в меню.", reply_markup=menuUser)
    if message.text == "Доступ к боту":
        bot.send_message(message.chat.id, f"""Бот доступен в Телеграм - @{bot.get_me().username}

Меня можно добавить в группу и получать быстрые ответы прям там! Для этого нужно: добавить бота как администратора и воспользоваться командами /ask и /generate. Для того, чтобы добавить в группу - воспользуйтесь командой /chat""", reply_markup=menuFaq)
    elif message.text == "Не работает бот":
        bot.send_message(message.chat.id, f"""Вероятно, сейчас много пользователей одновременно делают запросы. Попробуйте, пожалуйста, воспользоваться *бот* немного позже, минут через 5-10🙏

А также можете воспользоваться командой /restart.""", reply_markup=menuFaq)
    elif message.text == "Сменить тему разговора" or message.text == "Бот не рисует":
        bot.send_message(message.chat.id, "Воспользуйтесь командой /restart.", reply_markup=menuFaq)
    elif message.text == "Бот ответил неправильно":
        bot.send_message(message.chat.id, """Создайте новый запрос, иногда я могу ошибаться""", reply_markup=menuFaq)
    elif message.text == "Другое":
        bot.send_message(message.chat.id, f"Если у вас возникли какие-то сложности, напишите @. Поможем со всем разобраться.", reply_markup=menuFaq)
    else:
        return bot.send_message(message.chat.id, "Возвращаюсь в меню.", reply_markup=menuUser)
    bot.register_next_step_handler(message, openFaq)


def updateQuestions():
    Users.update(qLeft=10).where(Users.qLeft < 10).execute()


def checkTime():
    schedule.every().day.at("00:00").do(updateQuestions)
    while True:
        schedule.run_pending()
        time.sleep(1)


threading.Thread(target=checkTime).start()
bot.infinity_polling()
