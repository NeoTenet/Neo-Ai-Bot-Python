<div align="center">

<img src="banner.png" alt="Neo AI Bot — Python Telegram AI Bot" width="100%">

# 🤖 Neo-AI-Bot

### ربات هوش مصنوعی چندمنظوره تلگرام

ربات تلگرامی هوش مصنوعی با پشتیبانی از ارائه‌دهندگان سازگار با API اوپن‌ای‌آی، پاسخ‌گویی استریم، ذخیره‌سازی ابری و ابزارهای مدیریتی.

**Developed with ❤️ by [NeoTenet](https://t.me/NeoTenet)**

[راهنمای فارسی](#-راهنمای-فارسی) · [English Guide](#-english-guide) · [استقرار](#-استقرار) · [پیکربندی](#-پیکربندی) · [راهنمای دستورات گروه](#-راهنمای-دستورات-و-نکات-مهم-ربات)

</div>

---

## 🌟 قابلیت‌ها در یک نگاه

- ⚡ **پاسخ‌گویی استریم (Streaming):** نمایش تدریجی پاسخ مدل به‌جای انتظار برای دریافت کل پاسخ.
- 🔌 **پشتیبانی از چند ارائه‌دهنده:** امکان اتصال به سرویس‌های هوش مصنوعی سازگار با API مورد استفاده پروژه.
- 🧠 **ذخیره‌سازی ابری با Upstash Redis:** نگهداری داده‌ها و تنظیمات موردنیاز بدون راه‌اندازی دیتابیس محلی.
- 📄 **ارسال خودکار کد در قالب فایل:** جداسازی قطعه‌کدها و ارسال آن‌ها به‌صورت فایل‌هایی مانند `.py`، `.js`، `.html`، `.cpp` و `.txt`.
- 🛠️ **ابزارهای مدیریتی:** مدیریت کاربران و ارسال پیام همگانی (Broadcast).
- 👥 **پشتیبانی از گروه‌های تلگرام:** امکان پاسخ‌گویی با منشن یا ریپلای و کنترل‌های مدیریتی مرتبط.
- 🛡️ **مدیریت گروه با ریپلای:** ادمین‌های گروه می‌توانند با ریپلای روی پیام کاربر، او را بی‌صدا یا آزاد کنند، از گروه اخراج و بن کنند یا پیامش را حذف کنند.
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

## 🛡️ مدیریت کاربران گروه با ریپلای

برای آموزش قدم‌به‌قدم و مثال‌های قابل کپی، بخش [راهنمای کامل دستورات ربات در تلگرام](#-راهنمای-کامل-دستورات-ربات-در-تلگرام) را ببینید.

ادمین‌های گروه می‌توانند با ریپلای روی پیام کاربر موردنظر و ارسال یکی از فرمان‌های زیر، اقدامات مدیریتی را انجام دهند:

| فرمان | نتیجه |
| --- | --- |
| `سکوت` یا `بی صدا` | بی‌صدا کردن دائمی کاربر؛ کاربر تا زمان رفع محدودیت نمی‌تواند در گروه پیام بفرستد. |
| `سکوت 10` یا `سکوت 60` | بی‌صدا کردن زمان‌دار بر حسب دقیقه؛ پس از پایان مدت تعیین‌شده، محدودیت به‌صورت خودکار برداشته می‌شود. |
| `رفع سکوت` یا `آزاد` | برداشتن محدودیت سکوت و اجازه ارسال پیام به کاربر. |
| `اخراج` یا `بن` | اخراج کاربر از گروه و مسدود کردن او از حضور مجدد در گروه. |
| `حذف` یا `پاک` | حذف پیامی که ادمین روی آن ریپلای کرده است. |

**نکته:** برای اجرای این فرمان‌ها، فرستنده باید ادمین گروه باشد و ربات نیز مجوزهای مدیریتی لازم، از جمله محدود کردن کاربران و حذف پیام‌ها را داشته باشد.

### تشخیص شکل‌های مختلف کلمهٔ ربات

برای فراخوانی هوش مصنوعی در گروه، ربات شکل‌های مختلف نوشتاری را نیز تشخیص می‌دهد؛ از جمله **ربات**، **روبات** (با واو)، **ربات:**، **ربات،** و **بات**. با استفاده از این شکل‌ها، پیام کاربر برای پاسخ‌گویی به هوش مصنوعی تحویل داده می‌شود.

**خروج از حالت سکوت آزمایشی:** اگر قبلاً برای آزمایش، دستور `/bot سکوت` را در گروه فرستاده‌اید، یک‌بار دستور `/bot صحبت` را در گروه ارسال کنید تا ربات از حالت سکوت خارج شود.

## 📌 راهنمای کامل دستورات ربات در تلگرام

این قسمت را به‌ترتیب بخوانید و مثال‌ها را دقیقاً همان‌طور که نوشته شده‌اند در گروه امتحان کنید. برای دستورهایی که روی یک کاربر اجرا می‌شوند، **حتماً پیام همان کاربر را Reply (پاسخ) کنید**؛ در غیر این صورت ربات ممکن است متوجه نشود منظورتان کدام عضو است.

<details open>
<summary><b>📣 ۱. عضویت اجباری در کانال اسپانسری</b></summary>

اگر ربات از شما می‌خواهد اول عضو یک کانال شوید، مراحل زیر را انجام دهید:

1. پیامی را که ربات درباره عضویت در کانال نشان داده است باز کنید.
2. روی لینک کانال بزنید و وارد کانال شوید.
3. دکمه **Join / عضویت** را بزنید.
4. به ربات برگردید و دوباره دستور یا درخواست قبلی‌تان را ارسال کنید.

**برای مدیر ربات:** ربات را در کانال موردنظر ادمین کنید تا بتواند عضویت کاربران را بررسی کند. اگر ربات ادمین نباشد، ممکن است نتواند تشخیص دهد کاربر عضو کانال هست یا نه.

</details>

<details open>
<summary><b>🤖 ۲. چطور در گروه ربات را صدا بزنیم و از هوش مصنوعی سؤال کنیم؟</b></summary>

برای صدا زدن ربات لازم نیست دستور پیچیده‌ای بلد باشید. **اول پیام، کلمه «ربات» یا «بات» را بنویسید؛ بعد از آن یک فاصله بگذارید و درخواست خود را تایپ کنید.** سپس پیام را ارسال کنید.

**فرمول ساده:**

`ربات + درخواست شما`

**مثال‌های آماده برای کپی‌کردن:**

| اگر می‌خواهید… | این پیام را در گروه بفرستید |
| --- | --- |
| متن بگیرید | `ربات یک متن کوتاه درباره هوش مصنوعی بنویس` |
| سؤال بپرسید | `بات تفاوت پایتون و جاوااسکریپت چیه؟` |
| کد بخواهید | `ربات یک کد پایتون بنویس که اعداد زوج را جدا کنه` |
| متن ترجمه کنید | `ربات این جمله رو به انگلیسی ترجمه کن: سلام، حالت چطوره؟` |
| موضوعی را ساده یاد بگیرید | `بات مفهوم سرور VPS رو خیلی ساده توضیح بده` |
| متن را خلاصه کنید | `ربات متن زیر رو در سه خط خلاصه کن: ...` |

**قدم‌به‌قدم، برای کسی که اولین بار استفاده می‌کند:**

1. وارد گروهی شوید که ربات داخل آن است.
2. پایین صفحه روی کادر نوشتن پیام بزنید.
3. مثلاً بنویسید: `ربات درباره سیاره مریخ توضیح بده`.
4. دکمه ارسال را بزنید.
5. کمی صبر کنید تا ربات پاسخ را در گروه بفرستد.

**اگر پاسخ نگرفتید:** کلمه «ربات» یا «بات» را ابتدای پیام قرار دهید؛ مطمئن شوید ربات داخل گروه است و اجازه دسترسی به پیام‌های گروه را دارد. ممکن است تنظیمات حریم خصوصی ربات، محدودیت‌های گروه یا خطای سرویس هوش مصنوعی هم مانع پاسخ شود.

</details>

<details>
<summary><b>🔇 ۳. چطور یک کاربر را بی‌صدا (Mute) کنیم؟</b></summary>

این دستور برای مدیران گروه است و باید روی پیام همان کاربر اجرا شود.

1. پیام کاربری را که می‌خواهید بی‌صدا کنید در گروه پیدا کنید.
2. روی پیام او بزنید یا آن را نگه دارید.
3. گزینه **Reply / پاسخ** را انتخاب کنید.
4. در کادر پاسخ فقط یکی از این عبارت‌ها را بنویسید و ارسال کنید:
   - `سکوت`
   - `بی صدا`

**مثال:** پیام کاربر را Reply کنید و بنویسید `سکوت`.

این دستور برای بی‌صداکردن کاربر تا زمان برداشتن محدودیت استفاده می‌شود، مطابق رفتار پیاده‌سازی‌شده در ربات.

> **اشتباه رایج:** فقط نوشتن «سکوت» بدون Reply کردن پیام کاربر ممکن است کافی نباشد؛ ربات باید بداند کدام کاربر را هدف گرفته‌اید.

</details>

<details>
<summary><b>⏱️ ۴. چطور کاربر را برای چند دقیقه بی‌صدا کنیم؟</b></summary>

اگر می‌خواهید محدودیت بعد از مدت مشخصی تمام شود، پیام کاربر را Reply کنید و بعد از کلمه «سکوت» تعداد دقیقه را بنویسید.

**فرمت دستور:** `سکوت تعداد-دقیقه`

| دستور | مدت زمان |
| --- | --- |
| `سکوت 10` | ۱۰ دقیقه |
| `سکوت 30` | ۳۰ دقیقه |
| `سکوت 60` | ۶۰ دقیقه (یک ساعت) |
| `سکوت 120` | ۱۲۰ دقیقه (دو ساعت) |

**مثال واقعی:**

1. پیام کاربر را Reply کنید.
2. بنویسید `سکوت 10`.
3. پیام را ارسال کنید.

عدد باید مدت زمان را **برحسب دقیقه** نشان دهد؛ بنابراین `سکوت 60` یعنی ۶۰ دقیقه، نه ۶۰ ثانیه. پایان خودکار محدودیت به پشتیبانی نسخه ربات از سکوت زمان‌دار و اجرای درست آن بستگی دارد.

</details>

<details>
<summary><b>🔊 ۵. چطور سکوت کاربر را برداریم؟</b></summary>

برای اینکه کاربر دوباره اجازه ارسال پیام داشته باشد:

1. پیام همان کاربر را پیدا کنید.
2. پیامش را **Reply / پاسخ** کنید.
3. یکی از دستورهای زیر را ارسال کنید:
   - `رفع سکوت`
   - `آزاد`

**مثال:** روی پیام کاربر Reply کنید، عبارت `رفع سکوت` را بفرستید و منتظر نتیجه بمانید.

اگر کاربر هنوز نمی‌تواند پیام بدهد، بررسی کنید دستور برای همان کاربر اجرا شده باشد و محدودیت دیگری در گروه وجود نداشته باشد.

</details>

<details>
<summary><b>🚫 ۶. چطور کاربر را اخراج یا بن کنیم؟</b></summary>

**هشدار:** این دستورات روی عضویت افراد در گروه اثر می‌گذارند؛ پیش از ارسال، مطمئن شوید کاربر درست را انتخاب کرده‌اید.

1. پیام کاربر موردنظر را پیدا کنید.
2. آن پیام را **Reply / پاسخ** کنید.
3. یکی از دستورهای زیر را ارسال کنید:
   - `اخراج`
   - `بن`

طبق پیاده‌سازی ربات، این فرمان‌ها برای اخراج یا مسدودکردن کاربر در نظر گرفته شده‌اند. رفتار دقیق هرکدام را با نسخه فعال ربات بررسی کنید؛ در بسیاری از ربات‌ها «اخراج» و «بن» یکسان نیستند.

اگر دستور اجرا نشد، بررسی کنید فرستنده مدیر گروه باشد و ربات اجازه مدیریتی لازم برای اخراج یا مسدودکردن اعضا را داشته باشد.

</details>

<details>
<summary><b>🧹 ۷. چطور پیام را حذف کنیم؟</b></summary>

اگر نسخه ربات از فرمان حذف پشتیبانی می‌کند:

1. پیام موردنظر را پیدا کنید.
2. روی همان پیام Reply کنید.
3. یکی از عبارت‌های `حذف` یا `پاک` را ارسال کنید.

ربات برای حذف پیام باید دسترسی لازم را در گروه داشته باشد. اگر این فرمان در نسخه نصب‌شده فعال نباشد، اجرا نخواهد شد.

</details>

<details>
<summary><b>🧠 ۸. چطور مدل هوش مصنوعی گروه را ببینیم یا تغییر دهیم؟</b></summary>

برای دیدن فهرست مدل‌های در دسترس، در همان گروه این دستور را ارسال کنید:

`/models`

**مراحل:**

1. وارد گروهی شوید که ربات در آن فعال است.
2. دستور `/models` را بدون تغییر تایپ کنید و بفرستید.
3. اگر ربات فهرست مدل‌ها یا گزینه‌های انتخاب را نمایش داد، مدل موردنظرتان را طبق راهنمای همان پیام انتخاب کنید.

اگر چیزی نمایش داده نشد، ممکن است دستور در نسخه نصب‌شده فعال نباشد یا تنظیمات سرویس هوش مصنوعی نیاز به بررسی داشته باشد. فهرست مدل‌ها به پیکربندی و ارائه‌دهنده‌های متصل‌شده بستگی دارد.

</details>

<details>
<summary><b>⏸️ ۹. چطور پاسخ‌گویی ربات را در گروه متوقف و دوباره فعال کنیم؟</b></summary>

این دستورها برای کنترل پاسخ‌گویی خود ربات در گروه هستند؛ با سکوت‌کردن یک کاربر فرق دارند.

**توقف پاسخ‌گویی ربات:**

`/bot سکوت`

**فعال‌کردن دوباره پاسخ‌گویی ربات:**

`/bot صحبت`

**مراحل استفاده:**

1. وارد گروه شوید.
2. یکی از دستورهای بالا را دقیقاً تایپ کنید.
3. پیام را ارسال کنید.
4. برای فعال‌کردن مجدد، دستور `/bot صحبت` را بفرستید.

اگر قبلاً ربات را برای آزمایش ساکت کرده‌اید و دیگر به درخواست‌ها پاسخ نمی‌دهد، ابتدا `/bot صحبت` را امتحان کنید.

</details>

<details>
<summary><b>👮 ۱۰. چرا دستور مدیریتی من کار نمی‌کند؟ (ادمین ناشناس و دسترسی‌ها)</b></summary>

اگر دستورهای سکوت، آزادسازی، اخراج یا بن کار نمی‌کنند، این موارد را یکی‌یکی بررسی کنید:

- **ادمین گروه باشید:** حسابی که دستور را می‌فرستد باید مجوز مدیریتی لازم را داشته باشد.
- **از حالت ادمین ناشناس خارج شوید:** وقتی پیام به‌صورت ناشناس و از طرف گروه ارسال شود، ربات ممکن است نتواند حساب شخصی شما را با `ADMIN_ID` تطبیق دهد.
- **`ADMIN_ID` را درست تنظیم کنید:** این مقدار باید شناسه عددی حساب اصلی مدیر ربات باشد، نه نام کاربری و نه شناسه گروه.
- **به ربات دسترسی لازم بدهید:** بسته به دستور، ممکن است ربات به مجوز محدودکردن کاربران، حذف پیام‌ها یا مسدودکردن اعضا نیاز داشته باشد.
- **پیام درست را Reply کنید:** برای دستورات مربوط به کاربران، حتماً پیام همان فرد را پاسخ دهید.

**نکته:** مدیر بودن شما به‌تنهایی کافی نیست؛ خود ربات هم باید مجوز لازم برای انجام آن عمل را داشته باشد.

</details>

---

## 🧭 راهنمای سریع دستورات

| کار موردنظر | چه کاری انجام دهید؟ |
| --- | --- |
| پرسیدن سؤال از هوش مصنوعی | پیام را با `ربات` یا `بات` شروع کنید. |
| بی‌صدا کردن کاربر | Reply به پیام کاربر + `سکوت` یا `بی صدا` |
| بی‌صدا کردن زمان‌دار | Reply + `سکوت 10` یا `سکوت 60` |
| برداشتن سکوت | Reply + `رفع سکوت` یا `آزاد` |
| اخراج یا بن | Reply + `اخراج` یا `بن` |
| حذف پیام | Reply + `حذف` یا `پاک` |
| دیدن مدل‌های هوش مصنوعی | `/models` |
| توقف پاسخ‌گویی ربات | `/bot سکوت` |
| فعال‌کردن دوباره پاسخ‌گویی | `/bot صحبت` |

> **یادآوری:** دستورات و رفتار دقیق آن‌ها به نسخه نصب‌شده ربات بستگی دارد. برای فرمان‌های مدیریتی، هم فرستنده باید مجوز مناسب داشته باشد و هم ربات باید دسترسی لازم را در گروه دریافت کرده باشد.

---

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
- **Reply-based group moderation:** admins can mute users permanently or for a specified number of minutes, unmute them, ban them, or delete the replied-to message using Persian commands.
- **Mandatory channel membership** options.
- **Flexible deployment** on Python hosts or Linux VPS instances.

### Reply-Based Group Moderation

Group admins can reply to a user's message and send one of these Persian commands:

| Command | Action |
| --- | --- |
| `سکوت` or `بی صدا` | Mute the user until manually unmuted. |
| `سکوت 10` or `سکوت 60` | Mute the user for the specified number of minutes; the restriction is removed automatically when the time expires. |
| `رفع سکوت` or `آزاد` | Remove the user's mute restriction. |
| `اخراج` or `بن` | Remove and ban the user from the group. |
| `حذف` or `پاک` | Delete the message being replied to. |

**Note:** The sender must be a group admin, and the bot must have the required admin permissions, including restricting members and deleting messages.

### Recognizing Different Forms of “Bot”

When addressing the AI in a group, the bot also recognizes common variations, including **ربات**, **روبات**, **ربات:**, **ربات،**, and **بات**. Messages using these forms are forwarded to the AI for a response.

**Exit test silence mode:** If you previously sent `/bot سکوت` while testing, send `/bot صحبت` once in the group to bring the bot out of silence mode.

### Group Commands and Important Notes

1. **Sponsored channel membership:** Add the bot as an administrator in the required channel so it can check whether a user has joined.
2. **Call the bot:** Start your group message with `ربات` or `بات`, followed by your request.
3. **Mute a user:** Reply to the user's message with `سکوت` or `بی صدا`.
4. **Unmute a user:** Reply with `رفع سکوت` or `آزاد`.
5. **Kick/ban a user:** Reply with `اخراج` or `بن`.
6. **Timed mute:** Reply with `سکوت 10` or `سکوت 60`; the number represents minutes.
7. **Choose a group model:** Send `/models` to view the available models.
8. **Pause/resume bot replies:** Send `/bot سکوت` to pause replies and `/bot صحبت` to resume.
9. **Anonymous admin mode:** Leave anonymous-admin mode when issuing admin commands so the bot can identify the account configured as `ADMIN_ID`.

The sender must be a group administrator, and the bot must have the required Telegram admin permissions for moderation actions.

---

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
