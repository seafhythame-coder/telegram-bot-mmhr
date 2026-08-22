from flask import Flask, request
import telebot
import os

app = Flask(__name__)

API_TOKEN = '8896802101:AAH3IUWNVR44ACtfZwf1MotEw3PhPLQEYS0'
bot = telebot.TeleBot(API_TOKEN, threaded=False)

@app.route('/' + API_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    # استبدل الرابط أدناه برابط مشروعك على فيرسيل بعد النشر
    bot.set_webhook(url='https://' + os.environ.get('VERCEL_URL', '') + '/' + API_TOKEN)
    return "منظومة التوربو حية وتعمل بنجاح", 200