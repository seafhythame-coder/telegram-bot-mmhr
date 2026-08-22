import os

import telebot
from telebot import types
from dotenv import load_dotenv

import subscribers

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ALERT_CHAT_ID = os.getenv("ALERT_CHAT_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN غير موجود في .env")

bot = telebot.TeleBot(BOT_TOKEN)


def get_admin_ids():
    raw = os.getenv("ADMIN_USER_IDS", "")
    result = set()

    for value in raw.split(","):
        value = value.strip()
        if value.lstrip("-").isdigit():
            result.add(int(value))

    return result


def is_admin(user_id):
    return user_id in get_admin_ids()


def build_keyboard(user_id):
    keyboard = types.InlineKeyboardMarkup()
    active = subscribers.get_user_categories(user_id)

    for key, name in subscribers.CATEGORIES.items():
        icon = "✅" if key in active else "❌"

        keyboard.add(
            types.InlineKeyboardButton(
                f"{icon} {name}",
                callback_data=f"toggle_{key}",
            )
        )

    keyboard.add(
        types.InlineKeyboardButton(
            "🏨 طلب تذاكر لضيوف الفندق",
            callback_data="guest_help",
        )
    )

    return keyboard


@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    subscribers.add_subscriber(user_id)

    name = message.from_user.first_name or "عزيزي العميل"

    text = (
        f"⚡ *مرحبًا {name}*\n\n"
        "🎟️ منظومة HYHY لمتابعة الفعاليات "
        "وخدمة ضيوف الفنادق.\n\n"
        "اختر اهتماماتك من القائمة:"
    )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown",
        reply_markup=build_keyboard(user_id),
    )


@bot.message_handler(commands=["whoami"])
def whoami(message):
    bot.reply_to(
        message,
        f"Telegram User ID:\n`{message.from_user.id}`",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["watch"])
def watch(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "هذا الأمر مخصص للإدارة.")
        return

    parts = message.text.split(maxsplit=1)

    if len(parts) != 2:
        bot.reply_to(
            message,
            "الاستخدام:\n/watch https://webook.com/..."
        )
        return

    url = parts[1].strip()

    if "webook.com/" not in url:
        bot.reply_to(message, "أرسل رابط فعالية Webook صحيح.")
        return

    event_id = subscribers.add_watch(url)

    bot.reply_to(
        message,
        f"✅ بدأت مراقبة الفعالية.\nID: {event_id}"
    )


@bot.message_handler(commands=["events"])
def events(message):
    if not is_admin(message.from_user.id):
        return

    rows = subscribers.list_watches()

    if not rows:
        bot.reply_to(message, "لا توجد فعاليات تحت المراقبة.")
        return

    lines = ["🎯 *الفعاليات تحت المراقبة:*"]

    for event_id, url, label in rows:
        lines.append(
            f"\n{event_id}. {label or 'Webook Event'}\n{url}"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(lines),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("toggle_")
)
def toggle(call):
    section = call.data.replace("toggle_", "", 1)

    subscribers.toggle_category(
        call.from_user.id,
        section,
    )

    bot.edit_message_reply_markup(
        call.message.chat.id,
        call.message.message_id,
        reply_markup=build_keyboard(call.from_user.id),
    )

    bot.answer_callback_query(
        call.id,
        "تم تحديث الاهتمامات ✅"
    )


@bot.callback_query_handler(
    func=lambda call: call.data == "guest_help"
)
def guest_help(call):
    bot.send_message(
        call.message.chat.id,
        "🏨 لتسجيل طلب ضيف اكتب:\n\n"
        "/request الفندق | اسم الضيف | "
        "الفعالية | العدد | الفئة"
    )

    bot.answer_callback_query(call.id)


def send_alert(text):
    targets = []

    if ALERT_CHAT_ID:
        targets.append(ALERT_CHAT_ID)

    targets.extend(get_admin_ids())

    for target in dict.fromkeys(targets):
        try:
            bot.send_message(
                target,
                text,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except Exception as exc:
            print(f"تعذر إرسال التنبيه إلى {target}: {exc}")


if __name__ == "__main__":
    print("✅ تم تشغيل بوت التذاكر")
    print(f"🤖 البوت: @{bot.get_me().username}")

    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30,
    )