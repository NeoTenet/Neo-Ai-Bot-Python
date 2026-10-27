# راه‌اندازی سریع — Neo-AI-Bot

۱. Python 3.10 یا بالاتر نصب کنید.
۲. یک دیتابیس Upstash Redis بسازید و REST URL و REST Token را دریافت کنید.
۳. در Environment Variables هاست، چهار مقدار `BOT_TOKEN`، `ADMIN_ID`، `UPSTASH_URL` و `UPSTASH_TOKEN` را تنظیم کنید.
۴. وابستگی‌ها را نصب کنید: `python -m pip install -r requirements.txt`
۵. برنامه را با `python main.py` اجرا کنید.
۶. در خصوصی ربات `/start` بفرستید و از پنل ادمین مدل‌ها را اضافه کنید.

نکته: `.env.example` صرفاً نمونه است؛ فایل فعلی به‌طور خودکار `.env` را نمی‌خواند. توکن‌ها را در مخزن GitHub قرار ندهید.
