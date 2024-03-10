from telebot import types

menuUser = types.ReplyKeyboardMarkup(True)
menuUser.add("🚀 Задать вопрос").add("🖍 Создать картинку").add("🥷 Профиль").add("📝 Помощь", "🎯 Администрация")

showAdmin = types.InlineKeyboardMarkup()
showAdmin.add(
    types.InlineKeyboardButton(text="Саппорт", url="https://t.me/arFury")
).add(
    types.InlineKeyboardButton(text="Админ", url="https://t.me/arFury")
)

menuFaq = types.ReplyKeyboardMarkup(True)
menuFaq.add("Доступ к боту").add("Не работает бот", "Сменить тему разговора").add("Бот не рисует", "Бот ответил неправильно").add("Другое").add("Назад")

menuGpt = types.ReplyKeyboardMarkup(True)
menuGpt.add("Сбросить контекст").add("В меню")

backMenu = types.ReplyKeyboardMarkup(True)
backMenu.add("В меню")

cancel = types.ReplyKeyboardMarkup(True)
cancel.add("Отмена")
