import telebot
from telebot import types
import subscribers

# ضع توكن البوت الحقيقي المأخوذ من BotFather هنا بدلاً من المكتوب
API_TOKEN = '8896802101:AAH3IUWNVR44ACtfZwf1MotEw3PhPLQEYS0'
# ضع اسم معرف قناة التلغرام (قناة الدفعات) الخاصة بك هنا مع علامة @
CHANNEL_ID = '@MishraqChannel'
bot = telebot.TeleBot(API_TOKEN)

def build_keyboard(user_id):
    keyboard = types.InlineKeyboardMarkup()
    active_sections = subscribers.get_user_categories(user_id)
    
    # بناء وتحديث لوحة الأزرار الخارجية الحقيقية ديناميكياً لتعديل قاعدة البيانات فوراً
    for key, name in subscribers.CATEGORIES.items():
        status_icon = '✅' if key in active_sections else '❌'
        button_text = f"{status_icon} {name}"
        keyboard.add(types.InlineKeyboardButton(text=button_text, callback_data=f"toggle_{key}"))
        
    keyboard.add(types.InlineKeyboardButton(text='🏢 طلب اقتناص جماعي وتجميد تذاكر للعملاء', callback_data='corporate_request'))
    return keyboard

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or 'عزيزي العميل'
    
    subscribers.add_subscriber(user_id)
    
    welcome_text = (
        f"⚡ *مرحبا بك يا {user_name}!* \n\n"
        f"* منظومة الاقتناص والتأمين الفائق لشركتنا وعملائنا! *\n\n"
        f"⚡ *هذا البوت يعمل بنظام التوربو (Turbo Stream) لاكتساح زحام التذاكر: *\n\n"
        f"🎛️ *لوحة التحكم بالاهتمامات الحالية لقنوات الفحص:* \n"
        f"اضغط لتفعيل الفحص (✅) أو إيقافه (❌):\n"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown', reply_markup=build_keyboard(user_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def handle_toggle(call):
    user_id = call.from_user.id
    section_key = call.data.replace('toggle_', '')
    
    subscribers.toggle_category(user_id, section_key)
    
    # تحديث حالة الأزرار في الواجهة فوراً ومزامنتها مع الداتا ستور دون اهتزاز الشاشة
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=build_keyboard(user_id))
    bot.answer_callback_query(call.id, "🔄 تم التحديث في داتا ستور النظام الحقيقي!")

@bot.callback_query_handler(func=lambda call: call.data == 'corporate_request')
def handle_corporate(call):
    req_msg = (
        f"🏢 *بوابة الاحتجاز الفوري الممتد (VIP Hold System):*\n\n"
        f"• لتأمين المقاعد في الصفوف الأولى وتجميد الوقت لـ (ساعات أو أيام)، يرجى تزويد الدعم بـ:\n"
        f"• *اسم الفعالية / المباراة:*\n"
        f"• *العدد المطلوب:*\n"
        f"• *الفئة المفضلة (VVIP / أولى):*\n\n"
        f"🚀 *المحرك شغال الآن وجاهز للانقضاض فور الطرح!*"
    )
    bot.send_message(call.message.chat.id, req_msg, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

if __name__ == '__main__':
    bot.infinity_polling()
