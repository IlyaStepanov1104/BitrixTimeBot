import telebot
import requests
import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(TOKEN)
scheduler = BackgroundScheduler()

CHAT_ID_FILE = 'chat_id.json'


def load_chat_id():
    try:
        with open(CHAT_ID_FILE, 'r') as file:
            data = json.load(file)
            return data.get("chat_id")
    except FileNotFoundError:
        return None


def save_chat_id(chat_id):
    with open(CHAT_ID_FILE, 'w') as file:
        json.dump({"chat_id": chat_id}, file)


chat_id = load_chat_id()

menu_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
menu_keyboard.row("Начать рабочий день", "Завершить рабочий день")


def start_workday():
    if chat_id:
        response = requests.get(f"{WEBHOOK_URL}/timeman.open")
        if response.status_code == 200:
            bot.send_message(chat_id=chat_id, text="Рабочий день начат", reply_markup=menu_keyboard)
        else:
            bot.send_message(chat_id=chat_id, text="Ошибка при старте рабочего дня", reply_markup=menu_keyboard)


def end_workday():
    if chat_id:
        response = requests.get(f"{WEBHOOK_URL}/timeman.close")
        if response.status_code == 200:
            data = response.json().get('result')
            print(data)
            if data.get('DURATION'):
                elapsed_time = data.get('DURATION')
                bot.send_message(chat_id=chat_id, text=f"Рабочий день завершён. Общее время работы: {elapsed_time}",
                                 reply_markup=menu_keyboard)
            else:
                bot.send_message(chat_id=chat_id, text="Рабочий день завершён, но время работы не указано.",
                                 reply_markup=menu_keyboard)
        else:
            bot.send_message(chat_id=chat_id, text="Ошибка при завершении рабочего дня", reply_markup=menu_keyboard)


def check_start_reminder():
    if chat_id:
        response = requests.get(f"{WEBHOOK_URL}/timeman.status")
        data = response.json()
        if data["data"].get("status") != "Y":
            bot.send_message(chat_id=chat_id, text="Напоминание: Начните рабочий день", reply_markup=menu_keyboard)


def check_end_reminder():
    if chat_id:
        response = requests.get(f"{WEBHOOK_URL}/timeman.status")
        data = response.json()
        if data["data"].get("status") == "Y":
            bot.send_message(chat_id=chat_id, text="Напоминание: Завершите рабочий день", reply_markup=menu_keyboard)


@bot.message_handler(commands=['start'])
def handle_start_command(message):
    global chat_id
    chat_id = message.chat.id
    save_chat_id(chat_id)
    bot.send_message(chat_id, "Бот готов к работе. Вы можете начинать рабочий день.", reply_markup=menu_keyboard)


@bot.message_handler(func=lambda message: message.text.lower() == "начать рабочий день")
def handle_start(message):
    start_workday()


@bot.message_handler(func=lambda message: message.text.lower() == "завершить рабочий день")
def handle_end(message):
    end_workday()


# Настройка планировщика для напоминаний
scheduler.add_job(check_start_reminder, CronTrigger(day_of_week='mon-fri', hour='8-17', minute=0))
scheduler.add_job(check_end_reminder, CronTrigger(day_of_week='mon-fri', hour='18-21', minute=0))
scheduler.start()

# Запуск бота
bot.polling()
