import time
import threading
import os
import subscribers
from bot import bot, CHANNEL_ID

def run_background_tasks():
    while True:
        try:
            # 1. إطلاق رادار الاستكشاف الذكي للبحث التلقائي عن الفعاليات والمباريات القادمة
            subscribers.auto_discover_events(bot, CHANNEL_ID)
            
            # 2. إطلاق محرك تجميد السلة واقتناص الخريطة المالي المؤمّن
            subscribers.run_cart_rolling_engine()
        except Exception as e:
            print(f"⚠️ تنبيه في العمليات الخلفية: {e}")
        time.sleep(30) # تكرار الفحص الشامل التلقائي والمكثف كل 30 ثانية لسرعة الطرح

if __name__ == '__main__':
    # إطلاق رادار فحص المقاعد المصرفي والاستكشاف في مسار مستقل (Thread) لعمل متوازي وفائق السرعة
    watcher_thread = threading.Thread(target=run_background_tasks, daemon=True)
    watcher_thread.start()
    
    # تشغيل ملف واجهة التلغرام ليعمل المشروع كاملاً ككتلة واحدة مستقرة
    print("🔥 جاري تشغيل الواجهة الخارجية للمشروع والمزامنة مع داتا ستور بايثون...")
    bot.infinity_polling()
