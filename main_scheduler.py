import os
import threading
import time

from dotenv import load_dotenv

import subscribers
from bot import bot, send_alert
from webook_monitor import compare_events, fetch_event

load_dotenv()

POLL_SECONDS = max(
    30,
    int(os.getenv("POLL_SECONDS", "60"))
)


def format_event(data):
    remaining = data.get("remaining_public")

    if remaining is None:
        remaining_text = "غير معلن"
    else:
        remaining_text = str(remaining)

    return (
        f"🎟️ *{data.get('title') or 'فعالية Webook'}*\n\n"
        f"📅 الموعد: {data.get('start_date') or 'غير معلن'}\n"
        f"📍 المكان: {data.get('location') or 'غير معلن'}\n"
        f"💰 السعر: {data.get('price') or 'غير معلن'}\n"
        f"🟢 التوفر: {data.get('availability') or 'غير معلن'}\n"
        f"🎫 المتبقي المعلن: {remaining_text}\n\n"
        f"🔗 {data.get('url')}"
    )


def monitor_once():
    events = subscribers.list_watches()

    for event_id, url, label in events:
        try:
            data, fingerprint = fetch_event(url)

            previous = subscribers.get_last_snapshot(event_id)

            if previous is None:
                subscribers.save_snapshot(
                    event_id,
                    fingerprint,
                    data,
                )

                send_alert(
                    "✅ *بدأت مراقبة فعالية جديدة*\n\n"
                    + format_event(data)
                )

                continue

            if previous["fingerprint"] == fingerprint:
                continue

            changes = compare_events(
                previous["data"],
                data,
            )

            subscribers.save_snapshot(
                event_id,
                fingerprint,
                data,
            )

            if changes:
                send_alert(
                    "🚨 *تغيير جديد في الفعالية*\n\n"
                    + "\n".join(changes)
                    + "\n\n"
                    + format_event(data)
                )

        except Exception as exc:
            print(f"⚠️ فشل فحص {url}: {exc}")


def monitor_loop():
    while True:
        monitor_once()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    watcher = threading.Thread(
        target=monitor_loop,
        daemon=True,
    )

    watcher.start()

    me = bot.get_me()

    print(
        f"✅ HYHY Ticket Radar يعمل الآن: "
        f"@{me.username}"
    )

    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30,
    )