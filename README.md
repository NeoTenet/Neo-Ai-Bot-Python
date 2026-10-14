<div align="center">

# 🤖 Neo-AI-Bot

### ربات هوش مصنوعی چندمنظوره تلگرام

ربات تلگرامی هوش مصنوعی با پشتیبانی از ارائه‌دهندگان سازگار با API اوپن‌ای‌آی، پاسخ‌گویی استریم، ذخیره‌سازی ابری و ابزارهای مدیریتی.

**Developed with ❤️ by [NeoTenet](https://t.me/NeoTenet)**

[راهنمای فارسی](#-راهنمای-فارسی) · [English Guide](#-english-guide) · [استقرار](#-استقرار) · [پیکربندی](#-پیکربندی)

</div>

---

## 🌟 قابلیت‌ها در یک نگاه

- ⚡ **پاسخ‌گویی استریم (Streaming):** نمایش تدریجی پاسخ مدل به‌جای انتظار برای دریافت کل پاسخ.
- 🔌 **پشتیبانی از چند ارائه‌دهنده:** امکان اتصال به سرویس‌های هوش مصنوعی سازگار با API مورد استفاده پروژه.
- 🧠 **ذخیره‌سازی ابری با Upstash Redis:** نگهداری داده‌ها و تنظیمات موردنیاز بدون راه‌اندازی دیتابیس محلی.
- 📄 **ارسال خودکار کد در قالب فایل:** جداسازی قطعه‌کدها و ارسال آن‌ها به‌صورت فایل‌هایی مانند `.py`، `.js`، `.html`، `.cpp` و `.txt`.
- 🛠️ **ابزارهای مدیریتی:** مدیریت کاربران و ارسال پیام همگانی (Broadcast).
- 👥 **پشتیبانی از گروه‌های تلگرام:** امکان پاسخ‌گویی با منشن یا ریپلای و کنترل‌های مدیریتی مرتبط.
- 📣 **عضویت اجباری در کانال:** امکان تعیین کانال‌های موردنیاز برای استفاده از ربات.
- 🖥️ **قابلیت استقرار روی هاست پایتون یا Linux VPS:** اجرای پروژه روی محیط‌های میزبانی سازگار.

---

## 🌐 زبان‌ها / Languages

- [🇮🇷 راهنمای فارسی](#-راهنمای-فارسی)
- [🇬🇧 English Guide](#-english-guide)

---

# 🇮🇷 راهنمای فارسی

## 📋 معرفی

**Neo-AI-Bot** یک ربات هوش مصنوعی برای تلگرام است که با پایتون اجرا می‌شود و برای استقرار روی هاست‌های پایتونی، کانتینرها و سرورهای لینوکسی طراحی شده است. این پروژه از ذخیره‌سازی ابری Upstash Redis و قابلیت‌های استریم پاسخ استفاده می‌کند.

> **توجه:** امکانات نهایی ربات به پیاده‌سازی فعلی پروژه، سرویس‌دهنده هوش مصنوعی و محدودیت‌های هاست وابسته است.

## 🧰 پیش‌نیازها

- Python 3
- فایل‌های پروژه، از جمله `main.py` و `requirements.txt`
- ربات تلگرام و توکن دریافت‌شده از [@BotFather](https://t.me/BotFather)
- شناسه عددی تلگرام مدیر
- دیتابیس Upstash Redis با دسترسی REST
- کلید API سرویس هوش مصنوعی، در صورت نیاز به تنظیم در سورس پروژه

## ⚙️ پیکربندی

متغیرهای زیر را مطابق نام‌هایی که پروژه استفاده می‌کند تنظیم کنید:

| متغیر | توضیحات |
| --- | --- |
| `BOT_TOKEN` | توکن ربات تلگرام از `@BotFather` |
| `ADMIN_ID` | شناسه عددی مدیر ربات |
| `UPSTASH_URL` | نشانی REST دیتابیس Upstash Redis |
| `UPSTASH_TOKEN` | توکن دسترسی REST دیتابیس Upstash |

مقادیر را در بخش **Environment Variables** هاست وارد کنید، یا مطابق ساختار فعلی پروژه در فایل پیکربندی قرار دهید.

**نکته امنیتی:** توکن ربات، کلیدهای API و اطلاعات دیتابیس را در مخزن عمومی GitHub منتشر نکنید. اگر اطلاعات محرمانه ناخواسته منتشر شد، آن‌ها را از سرویس مربوطه باطل و جایگزین کنید.

## 🗄️ ساخت دیتابیس Upstash

1. وارد [Upstash](https://upstash.com) شوید و حساب کاربری ایجاد کنید.
2. گزینه ساخت دیتابیس (**Create Database**) را انتخاب کنید.
3. نام دیتابیس و منطقه جغرافیایی مناسب را انتخاب کنید.
4. صفحه دیتابیس را باز کرده و بخش **REST API** را پیدا کنید.
5. نشانی REST و توکن را در متغیرهای `UPSTASH_URL` و `UPSTASH_TOKEN` قرار دهید.

نام متغیرهای محیطی مورد استفاده در کد باید با نام‌هایی که در پروژه تعریف شده‌اند مطابقت داشته باشد.

## 🚀 اجرا روی هاست پایتونی

این روش برای هاست‌هایی مناسب است که از اجرای برنامه‌های پایتون پشتیبانی می‌کنند.

1. فایل‌های پروژه، از جمله `main.py` و `requirements.txt`، را در پوشه اصلی برنامه قرار دهید.
2. متغیرهای محیطی موردنیاز را در تنظیمات هاست وارد کنید.
3. وابستگی‌ها را با دستور زیر نصب کنید:

   ```bash
   pip install -r requirements.txt
   ```

4. دستور شروع برنامه را روی این مقدار قرار دهید:

   ```bash
   python main.py
   ```

5. برنامه را اجرا کنید و گزارش‌های اجرا را برای بررسی خطاها ببینید.

## 🖥️ استقرار روی Ubuntu / Debian VPS

### ۱. نصب پیش‌نیازها

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

### ۲. دریافت سورس و نصب وابستگی‌ها

```bash
git clone https://github.com/NeoTenet/Neo-Ai-Bot.git
cd Neo-Ai-Bot

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### ۳. آزمایش اجرای برنامه

پیش از ساخت سرویس دائمی، مطمئن شوید متغیرهای محیطی تنظیم شده‌اند و برنامه به‌صورت دستی اجرا می‌شود:

```bash
python main.py
```

پس از تأیید اجرای درست برنامه، آن را با `Ctrl+C` متوقف کنید تا برای اجرای سرویس آماده شوید.

### ۴. ساخت سرویس systemd

فایل سرویس را ایجاد کنید:

```bash
sudo nano /etc/systemd/system/neo-ai-bot.service
```

نمونه زیر را وارد کنید. مسیرها و نام کاربر را متناسب با محل واقعی نصب پروژه تغییر دهید:

```ini
[Unit]
Description=Neo AI Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_LINUX_USER
WorkingDirectory=/path/to/Neo-Ai-Bot
EnvironmentFile=/etc/neo-ai-bot.env
ExecStart=/path/to/Neo-Ai-Bot/.venv/bin/python /path/to/Neo-Ai-Bot/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

فایل محیطی جداگانه ایجاد کنید تا اطلاعات محرمانه داخل فایل سرویس قرار نگیرند:

```bash
sudo nano /etc/neo-ai-bot.env
```

نمونه محتوا؛ مقادیر واقعی خودتان را وارد کنید:

```dotenv
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ADMIN_ID=YOUR_NUMERIC_TELEGRAM_ID
UPSTASH_URL=https://your-database.upstash.io
UPSTASH_TOKEN=YOUR_UPSTASH_REST_TOKEN
```

دسترسی فایل حاوی اطلاعات محرمانه را محدود کنید:

```bash
sudo chmod 600 /etc/neo-ai-bot.env
```

سپس سرویس را فعال و اجرا کنید:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now neo-ai-bot
sudo systemctl status neo-ai-bot
```

برای مشاهده گزارش‌های زنده:

```bash
sudo journalctl -u neo-ai-bot -f
```

> **مهم:** `YOUR_LINUX_USER` و مسیرهای `/path/to/Neo-Ai-Bot` مقادیر نمونه هستند و باید با مسیر و کاربر واقعی سرور جایگزین شوند. همچنین برنامه باید از متغیرهای محیطی پشتیبانی کند؛ در غیر این صورت، بخش پیکربندی سورس را مطابق ساختار پروژه تنظیم کنید.

## 🧯 عیب‌یابی سریع

- **ربات اجرا نمی‌شود:** گزارش سرویس را با `sudo journalctl -u neo-ai-bot -n 100 --no-pager` بررسی کنید.
- **خطای وابستگی‌ها:** فعال بودن محیط مجازی و نصب موفق `requirements.txt` را بررسی کنید.
- **خطای اتصال به Redis:** نشانی REST و توکن Upstash را بررسی کنید.
- **ربات به پیام‌ها پاسخ نمی‌دهد:** توکن ربات، تنظیمات سرویس هوش مصنوعی و لاگ‌های برنامه را بررسی کنید.
- **سرویس بعد از ویرایش اجرا نمی‌شود:** پس از تغییر فایل سرویس، `sudo systemctl daemon-reload` را اجرا و سرویس را دوباره راه‌اندازی کنید.

---

# 🇬🇧 English Guide

## Overview

**Neo-AI-Bot** is a Python-based Telegram AI bot designed for Python hosting platforms, containers, and Linux VPS environments. It uses Upstash Redis for cloud persistence and supports streaming-style responses.

### Key Features

- **Streaming responses** for progressive output.
- **Multi-provider support** for compatible AI APIs, subject to the project implementation.
- **Upstash Redis integration** for cloud-based persistence.
- **Automatic code-to-file delivery** for supported file types such as `.py`, `.js`, `.html`, `.cpp`, and `.txt`.
- **Admin tools** including broadcast messaging and user management.
- **Telegram group support** with mention/reply workflows.
- **Mandatory channel membership** options.
- **Flexible deployment** on Python hosts or Linux VPS instances.

## Requirements

- Python 3
- Project files, including `main.py` and `requirements.txt`
- Telegram bot token from [@BotFather](https://t.me/BotFather)
- Numeric Telegram admin ID
- Upstash Redis REST URL and token
- AI provider credentials, if required by the project configuration

## Environment Variables

| Variable | Description |
| --- | --- |
| `BOT_TOKEN` | Telegram bot token |
| `ADMIN_ID` | Numeric Telegram admin ID |
| `UPSTASH_URL` | Upstash Redis REST endpoint |
| `UPSTASH_TOKEN` | Upstash Redis REST access token |

Keep credentials in your hosting provider's environment settings or a protected environment file. **Never commit secrets to a public repository.**

## Deploy on a Python Host

1. Upload `main.py`, `requirements.txt`, and the required project files.
2. Configure the required environment variables.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set the startup command:

   ```bash
   python main.py
   ```

5. Start the application and inspect the host logs if it fails.

## Deploy on Ubuntu / Debian

Install the required packages:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

Clone the repository and install dependencies in a virtual environment:

```bash
git clone https://github.com/NeoTenet/Neo-Ai-Bot.git
cd Neo-Ai-Bot

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Test the application before configuring the service:

```bash
python main.py
```

For persistent execution, create `/etc/systemd/system/neo-ai-bot.service` and adapt the paths and Linux user to your server:

```ini
[Unit]
Description=Neo AI Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_LINUX_USER
WorkingDirectory=/path/to/Neo-Ai-Bot
EnvironmentFile=/etc/neo-ai-bot.env
ExecStart=/path/to/Neo-Ai-Bot/.venv/bin/python /path/to/Neo-Ai-Bot/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Create `/etc/neo-ai-bot.env` with your actual values, restrict its permissions, then enable the service:

```bash
sudo chmod 600 /etc/neo-ai-bot.env
sudo systemctl daemon-reload
sudo systemctl enable --now neo-ai-bot
sudo systemctl status neo-ai-bot
sudo journalctl -u neo-ai-bot -f
```

Replace all example paths and placeholder values before starting the service. The application must read the configured environment variables for this setup to work as written.

---

## 👨‍💻 Creator & Support

- **Creator:** [NeoTenet](https://t.me/NeoTenet)
- **Repository:** [NeoTenet/Neo-Ai-Bot](https://github.com/NeoTenet/Neo-Ai-Bot)
- **License:** MIT *(as stated by the project; add the `LICENSE` file to the repository if it is not already present)*

---

<div align="center">

Made with ❤️ by **[NeoTenet](https://t.me/NeoTenet)**

</div>
