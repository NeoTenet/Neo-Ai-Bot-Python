# -*- coding: utf-8 -*-
"""
Telegram AI Bot - Python + Upstash Redis (100% Safe & Stable)
Configured for: Wispbyte / bot-hosting.net (Docker / Linux Environment)
Features:
- Fixed Unicode SyntaxError (Replaced non-standard bullet characters with safe ASCII)
- Native Persian/Jalali Calendar Engine (Automatic conversion to Iranian dates)
- History Purge Suite: One-click individual session delete (🗑) + Full Database Purge
- Instant Casual Greeting Engine (Fixes 6-min thinking bug on 'سلام عشقم' etc.)
- Strict Thought Filter: Strips <think> and internal monologues completely
- Smart Group Photo Reply (Strict Vision analysis when replying to photos)
- Structured Code Delivery: Concise explanation first, then code file attached as a direct reply
- Real-Time Glitch-Free Stopwatch (Accurate wall-clock time)
- Unified /models Hub: Independent Chat & Image Model Switcher with Live Status
- Ultra-Fast MGET Admin Stats (< 0.2s for 50+ users)
- Native Stability AI v2beta Support (Ultra, Core, SD3)
- Colored Buttons (Primary Blue, Success Green, Danger Red)
- Group Moderation Suite (Mute, Timed-Mute, Unmute, Ban, Delete) for Admins
- Anti-Clutter: No long code dumps in group or private chats
- Strict UTF-8 Streaming Engine (No Mojibake)
- [جدید] دکمه لغو زنده ساخت تصویر هوش مصنوعی
- [جدید] حل باگ تداخل مدل متن و عکس و ریست خودکار وضعیت
- [جدید] آمارگیری اتمیک بدون خطا با Redis Sets (جلوگیری قطعی از پریدن آمار کاربران)
Timeout: 35 Minutes (2100s)
Developer Channel: T.me/Neotenet
"""

import os
import io
import re
import json
import time
import base64
import socket
import threading
import urllib.parse
import requests
from requests.adapters import HTTPAdapter
import telebot
from telebot import types
from telebot.types import ChatPermissions
from telebot.apihelper import ApiTelegramException

# ==========================================
# 🎨 تزریق مستقیم دکمه‌های رنگی به تل‌بات (Monkey-Patch)
# ==========================================
_orig_btn_init = types.InlineKeyboardButton.__init__
def _custom_btn_init(self, *args, **kwargs):
    self.style = kwargs.pop('style', None)
    self.icon_custom_emoji_id = kwargs.pop('icon_custom_emoji_id', None)
    _orig_btn_init(self, *args, **kwargs)
types.InlineKeyboardButton.__init__ = _custom_btn_init

_orig_btn_to_dict = types.InlineKeyboardButton.to_dict
def _custom_btn_to_dict(self):
    d = _orig_btn_to_dict(self)
    if hasattr(self, 'style') and self.style:
        d['style'] = self.style
    if hasattr(self, 'icon_custom_emoji_id') and self.icon_custom_emoji_id:
        d['icon_custom_emoji_id'] = self.icon_custom_emoji_id
    return d
types.InlineKeyboardButton.to_dict = _custom_btn_to_dict

# ==========================================
# 📅 موتور تبدیل تاریخ میلادی به هجری شمسی (ایران)
# ==========================================
def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy if gm > 2 else gy - 1
    days = (365 * gy) + ((gy2 + 4) // 4) - ((gy2 + 100) // 100) + ((gy2 + 400) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd

def get_jalali_date():
    t = time.localtime()
    jy, jm, jd = gregorian_to_jalali(t.tm_year, t.tm_mon, t.tm_mday)
    return f"{jy}/{jm:02d}/{jd:02d}"

def format_session_date(d_str):
    if not d_str:
        return get_jalali_date()
    d_str = str(d_str).strip()
    parts = re.split(r'[-/]', d_str)
    if len(parts) == 3 and parts[0].isdigit() and int(parts[0]) > 1600:
        try:
            jy, jm, jd = gregorian_to_jalali(int(parts[0]), int(parts[1]), int(parts[2]))
            return f"{jy}/{jm:02d}/{jd:02d}"
        except Exception:
            pass
    return d_str

# ==========================================
# ⚙️ تنظیمات اصلی و اطلاعات دیتابیس Upstash
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT TOKEN")
ADMIN_ID = str(os.getenv("ADMIN_ID", "ID ADMIN"))

UPSTASH_URL = os.getenv("UPSTASH_URL", "https://precious.upstash.io")
UPSTASH_TOKEN = os.getenv("UPSTASH_TOKEN", "DATE BASE TOKEN")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ==========================================
# 🌐 تنظیم سوکت شبکه با پکت‌های زنده نگه‌دارنده (TCP Keep-Alive)
# ==========================================
class TCPKeepAliveAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        socket_options = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
        if hasattr(socket, "TCP_KEEPIDLE"):
            socket_options.append((socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 5))
        elif hasattr(socket, "TCP_KEEPALIVE"):
            socket_options.append((socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, 5))
            
        if hasattr(socket, "TCP_KEEPINTVL"):
            socket_options.append((socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5))
        if hasattr(socket, "TCP_KEEPCNT"):
            socket_options.append((socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 10))

        pool_kwargs["socket_options"] = socket_options
        super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)

http_session = requests.Session()
adapter = TCPKeepAliveAdapter(pool_connections=20, pool_maxsize=50)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

# ==========================================
# ۰. توابع کمکی دیتابیس Upstash Redis
# ==========================================
def upstash_command(cmd):
    try:
        headers = {
            "Authorization": f"Bearer {UPSTASH_TOKEN}",
            "Content-Type": "application/json"
        }
        res = http_session.post(UPSTASH_URL, headers=headers, json=cmd, timeout=15)
        if res.status_code == 200:
            return res.json().get("result")
    except Exception as e:
        print(f"[Upstash Error]: {e}")
    return None

def safe_kv_put(key, value, expiration_ttl=None):
    try:
        str_val = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        if expiration_ttl:
            upstash_command(["SET", key, str_val, "EX", int(expiration_ttl)])
        else:
            upstash_command(["SET", key, str_val])
        return True
    except Exception as e:
        print(f"[Upstash Put Error {key}]: {e}")
        return False

def safe_kv_get(key):
    try:
        res = upstash_command(["GET", key])
        return str(res) if res is not None else None
    except Exception as e:
        print(f"[Upstash Get Error {key}]: {e}")
        return None

def safe_kv_delete(key):
    try:
        upstash_command(["DEL", key])
        return True
    except Exception as e:
        print(f"[Upstash Del Error {key}]: {e}")
        return False

# ==========================================
# 🧠 تشخیص دقیق و هوشمند احوالپرسی و تصویرسازی (بدون قاطی شدن)
# ==========================================
def is_casual_greeting(text):
    if not text:
        return False
    clean = re.sub(r'[^\w\s]', '', text).strip().lower()
    greetings = [
        'سلام', 'سلان', 'درود', 'خوبی', 'چطوری', 'سلام عشقم', 'سلان عشقم', 
        'سلام داداش', 'سلام رفیق', 'سلام علیکم', 'چطوری عشقم', 'خوبی عشقم', 
        'صبح بخیر', 'شب بخیر', 'عصر بخیر', 'سلام خوبی', 'سلان خوبی', 'hi', 'hello', 'hey'
    ]
    return clean in greetings or any(clean.startswith(g + " ") for g in ['سلام', 'سلان', 'درود'])

def detect_image_intent(text):
    if not text:
        return False, ""
    clean = text.strip()
    lower = clean.lower()

    # کلماتی که نشان‌دهنده سوال متنی، گفتگو یا درباره مدل‌ها هستند نه ساخت عکس
    text_code_guards = [
        'کد', 'برنامه', 'اسکریپت', 'تابع', 'متغیر', 'پایتون', 'جاوا', 'html', 'css', 'sql',
        'دیباگ', 'ارور', 'خطا', 'حل کن', 'توضیح بده', 'توضیح بدید', 'توضیح دهید',
        'چیست', 'کیست', 'چرا', 'چطور', 'چگونه', 'راهنمایی', 'بنویس', 'ترجمه', 'متن', 'مقاله',
        'مدل', 'هوش مصنوعی', 'ربات', 'بات', 'تنظیمات', 'قابلیت', 'سوال', 'سلام', 'درود'
    ]
    has_text_guard = any(guard in lower for guard in text_code_guards)

    # اگر کاربر کلماتی مانند کد یا سوال یا صحبت درباره مدل پرسیده، به هیچ وجه به عنوان عکس پردازش نشود
    if has_text_guard:
        return False, clean

    # تشخیص انگلیسی
    en_triggers = ["draw ", "paint ", "generate image", "create image", "create photo", "create picture", "image of ", "photo of ", "picture of "]
    for et in en_triggers:
        if et in lower:
            prompt = re.sub(r'^(?:please\s+)?(?:make|draw|paint|generate|create|imagine)\s+(?:a|an|the)?\s*(?:image|photo|picture)?\s*(?:of)?\s*', '', clean, flags=re.IGNORECASE)
            return True, prompt.strip() or clean

    # افعال و کلمات صریح ساخت عکس در زبان فارسی
    fa_visual_verbs = ["بکش", "نقاشی کن", "تولید کن", "طراحی کن", "بساز", "خلق کن", "ایجاد کن", "درست کن", "تصویرسازی کن"]
    has_visual_verb = any(v in clean for v in fa_visual_verbs)

    fa_visual_nouns = ["عکس", "تصویر", "نقاشی", "پوستر", "والپیپر"]
    has_visual_noun = any(n in clean for n in fa_visual_nouns)

    if has_visual_noun and has_visual_verb:
        prompt = clean
        prompt = re.sub(r'(?:لطفاً|لطفا|بی زحمت|برام|برای من|یه|یک)\s+', '', prompt)
        prompt = re.sub(r'(?:عکس|تصویر|نقاشی|پوستر|والپیپر)\s+(?:از|بکش\s+از|بساز\s+از|تولید\s+کن\s+از)?\s*', '', prompt)
        prompt = re.sub(r'\s+(?:عکس|تصویر|نقاشی)?\s*(?:بساز|بکش|تولید کن|طراحی کن|بده|درست کن|خلق کن|ایجاد کن|تصویرسازی کن)$', '', prompt)
        prompt = re.sub(r'^(?:از)\s+', '', prompt)
        return True, prompt.strip() or clean

    # الگوهای ساختاریافته مانند "عکس از ..." یا "یک عکس از ..."
    prefix_pattern = r'^(?:یک\s+|یه\s+)?(?:عکس|تصویر|نقاشی|پوستر|والپیپر)\s+از\s+(.+)$'
    m = re.match(prefix_pattern, clean, flags=re.IGNORECASE)
    if m:
        return True, m.group(1).strip()

    return False, clean

# ==========================================
# توابع بررسی دسترسی و مدیریت کاربر (اتمیک و ضد افت آمار)
# ==========================================
def get_all_bot_users():
    """دریافت لیست تمام کاربران بدون خطر پریدن یا بازنویسی دیتابیس"""
    set_users = upstash_command(["SMEMBERS", "BOT_USERS_SET"]) or []
    old_users = []
    old_raw = safe_kv_get("BOT_USERS")
    if old_raw:
        try:
            old_users = json.loads(old_raw)
        except Exception:
            pass
    # ترکیب ایمن دو منبع برای حفظ تمامی کاربران قبلی و جدید
    all_users = list(set([str(u) for u in (set_users + old_users) if str(u).strip()]))
    return all_users

def track_user_activity(user_id):
    """ثبت اتمیک کاربر با SADD برای جلوگیری کامل از حذف شدن تصادفی کاربران"""
    try:
        upstash_command(["SADD", "BOT_USERS_SET", str(user_id)])
        safe_kv_put(f"LAST_ACTIVE_{user_id}", str(int(time.time() * 1000)))
    except Exception as e:
        print(f"[Track User Error]: {e}")

def clear_user_state(user_id):
    for key in [
        f"ADMIN_STEP_{user_id}", f"TEMP_MODEL_{user_id}",
        f"TEMP_IMG_{user_id}", f"ADMIN_EDIT_IDX_{user_id}",
        f"ADMIN_EDIT_IMG_IDX_{user_id}", f"USER_SUPPORT_STEP_{user_id}"
    ]:
        safe_kv_delete(key)

def is_group_admin(chat_id, user_id):
    if str(user_id) == str(ADMIN_ID):
        return True
    try:
        member = bot.get_chat_member(chat_id, int(user_id))
        return member.status in ["creator", "administrator"]
    except Exception as e:
        print(f"[is_group_admin Error]: {e}")
        return False

def check_sponsor_join(user_id):
    channels_raw = safe_kv_get("SPONSOR_CHANNELS")
    channels = []
    if channels_raw:
        try:
            channels = json.loads(channels_raw)
        except:
            channels = [channels_raw]

    if not channels:
        return True, []

    unjoined = []
    for ch in channels:
        formatted_ch = ch if ch.startswith("@") else f"@{ch}"
        try:
            member = bot.get_chat_member(formatted_ch, int(user_id))
            if member.status not in ["creator", "administrator", "member"]:
                unjoined.append(formatted_ch)
        except Exception:
            unjoined.append(formatted_ch)

    return len(unjoined) == 0, unjoined

def get_or_create_active_session(user_id):
    active_id = safe_kv_get(f"ACTIVE_SESSION_{user_id}")
    if not active_id:
        active_id = f"sess_{int(time.time())}"
        safe_kv_put(f"ACTIVE_SESSION_{user_id}", active_id)
        sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
        sessions.insert(0, {"id": active_id, "title": "گفتگوی جدید 💬", "date": get_jalali_date()})
        safe_kv_put(f"SESSIONS_{user_id}", sessions)
    return active_id

def update_session_title_if_new(user_id, session_id, first_msg):
    sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
    for s in sessions:
        if s.get("id") == session_id and s.get("title") == "گفتگوی جدید 💬":
            s["title"] = (first_msg[:22] + "...") if len(first_msg) > 22 else first_msg
            safe_kv_put(f"SESSIONS_{user_id}", sessions)
            break

def is_code_request(text):
    if not text or is_casual_greeting(text):
        return False
    lower = text.lower()
    code_keywords = [
        'code', 'script', 'bug', 'error', 'function', 'const', 'let', 'var', 
        'import', 'export', 'def', 'class', 'html', 'css', 'js', 'python', 
        'c++', 'java', 'sql', 'json', 'async', 'await', 'return', 'if', 'else',
        'کد', 'برنامه', 'اسکریپت', 'باگ', 'خطا', 'دیباگ', 'توابع', 'متغیر', 'ارور'
    ]
    return any(k in lower for k in code_keywords)

def chunk_string(s, size=4000):
    return [s[i:i + size] for i in range(0, len(s), size)]

def send_safe_ai_response(chat_id, message_id, text, reply_to_id=None, thread_id=None):
    if len(text) <= 4000:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown")
        except Exception:
            try:
                bot.edit_message_text(text, chat_id=chat_id, message_id=message_id)
            except Exception:
                pass
    else:
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass

        chunks = chunk_string(text, 4000)
        for chunk in chunks:
            try:
                bot.send_message(
                    chat_id, chunk, parse_mode="Markdown",
                    reply_to_message_id=reply_to_id,
                    allow_sending_without_reply=True,
                    message_thread_id=thread_id
                )
            except Exception:
                bot.send_message(
                    chat_id, chunk,
                    reply_to_message_id=reply_to_id,
                    allow_sending_without_reply=True,
                    message_thread_id=thread_id
                )

# ==========================================
# 📁 سیستم تفکیک کد از متن و فیلتر تمیز
# ==========================================
def process_code_and_text(raw_text, is_code_prompt):
    pattern = r'```([a-zA-Z0-9_+-]*)[^\n]*\r?\n([\s\S]*?)```'
    matches = re.findall(pattern, raw_text)
    code_files = []

    ext_map = {
        'python': 'py', 'py': 'py', 'javascript': 'js', 'js': 'js',
        'typescript': 'ts', 'ts': 'ts', 'html': 'html', 'css': 'css',
        'cpp': 'cpp', 'c++': 'cpp', 'c': 'c', 'java': 'java', 'kotlin': 'kt',
        'php': 'php', 'sql': 'sql', 'json': 'json', 'xml': 'xml',
        'bash': 'sh', 'sh': 'sh', 'shell': 'sh', 'go': 'go', 'golang': 'go',
        'rust': 'rs', 'rs': 'rs', 'lua': 'lua', 'csharp': 'cs', 'cs': 'cs',
        'ruby': 'rb', 'rb': 'rb', 'swift': 'swift', 'dart': 'dart', 'txt': 'txt'
    }

    if matches:
        detected_lang_name = "کد"
        for idx, (lang, code_content) in enumerate(matches, 1):
            clean_code = code_content.strip()
            if len(clean_code) < 10:
                continue

            lang_clean = lang.strip().lower()
            if lang_clean in ext_map:
                ext = ext_map[lang_clean]
            elif 'def ' in clean_code or 'import ' in clean_code:
                ext = 'py'
            elif 'console.log' in clean_code or 'const ' in clean_code:
                ext = 'js'
            elif '<html' in clean_code:
                ext = 'html'
            else:
                ext = 'txt'

            detected_lang_name = ext.upper()
            if ext == 'py':
                filename = "main.py" if idx == 1 else f"script_{idx}.py"
            elif ext == 'js':
                filename = "app.js" if idx == 1 else f"script_{idx}.js"
            elif ext == 'html':
                filename = "index.html" if idx == 1 else f"page_{idx}.html"
            elif ext == 'cpp':
                filename = "main.cpp" if idx == 1 else f"file_{idx}.cpp"
            else:
                filename = f"code_{idx}.{ext}" if len(matches) > 1 else f"code.{ext}"

            code_files.append((filename, clean_code.encode('utf-8'), ext))

        cleaned_text = re.sub(pattern, '', raw_text).strip()
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text).strip()

        if len(cleaned_text) > 10:
            cleaned_text += f"\n\n📦 **سورس کد {detected_lang_name} در فایل زیر ضمیمه و ریپلای شد 👇**"
        else:
            cleaned_text = f"✅ **توضیحات و سورس کد {detected_lang_name} آماده شد و در فایل زیر ضمیمه گردید 👇**"

        return cleaned_text, code_files

    code_indicators = ['def ', 'import ', 'class ', 'const ', 'function ', 'console.log', '<!DOCTYPE', '<html', '#include', 'public class']
    has_code_syntax = any(ind in raw_text for ind in code_indicators)

    if (is_code_prompt or has_code_syntax) and len(raw_text) > 40:
        if 'def ' in raw_text or 'import ' in raw_text:
            ext = 'py'
            filename = "main.py"
        elif 'console.log' in raw_text or 'const ' in raw_text:
            ext = 'js'
            filename = "app.js"
        elif '<html' in raw_text:
            ext = 'html'
            filename = "index.html"
        else:
            ext = 'txt'
            filename = "script.txt"

        code_files.append((filename, raw_text.encode('utf-8'), ext))
        cleaned_text = "✅ **سورس کد برنامه با موفقیت آماده شد و در فایل زیر ضمیمه گردید 👇**"
        return cleaned_text, code_files

    return raw_text, []

# ==========================================
# 📤 تابع ارسال فایل سورس کد
# ==========================================
def send_code_document_safe(chat_id, byte_data, filename, ext, reply_to_id=None, thread_id=None):
    caption = f"📁 فایل سورس کد ({ext.upper()}): {filename}"

    def make_bio():
        b = io.BytesIO(byte_data)
        b.name = filename
        b.seek(0)
        return b

    try:
        kwargs = {"caption": caption}
        if reply_to_id:
            kwargs["reply_to_message_id"] = reply_to_id
            kwargs["allow_sending_without_reply"] = True
        if thread_id:
            kwargs["message_thread_id"] = thread_id

        bot.send_document(chat_id, make_bio(), **kwargs)
        return True
    except TypeError:
        try:
            bot.send_document(chat_id, make_bio(), caption=caption, reply_to_message_id=reply_to_id)
            return True
        except Exception:
            pass
    except Exception as e1:
        print(f"[Document Send Error 1]: {e1}")

    try:
        kwargs2 = {"caption": caption}
        if thread_id:
            kwargs2["message_thread_id"] = thread_id
        bot.send_document(chat_id, make_bio(), **kwargs2)
        return True
    except Exception as e2:
        print(f"[Document Send Error 2]: {e2}")
        return False

# ==========================================
# ۱. رابط کاربری و هاب جامع انتخاب مدل‌ها (/models)
# ==========================================
def get_main_menu_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💬 گفتگو و کدنویسی", callback_data="mode_chat", style="primary"),
        types.InlineKeyboardButton("🎨 تصویرسازی هوش مصنوعی", callback_data="mode_image", style="success")
    )
    markup.add(
        types.InlineKeyboardButton("🤖 انتخاب مدل هوش مصنوعی", callback_data="models_hub"),
        types.InlineKeyboardButton("📜 تاریخچه گفتگوها", callback_data="history_menu")
    )
    markup.add(
        types.InlineKeyboardButton("📞 پیام به پشتیبانی و ادمین", callback_data="contact_admin", style="primary")
    )
    row_last = [types.InlineKeyboardButton("➕ شروع گفتگوی جدید", callback_data="new_chat", style="success")]
    if str(user_id) == str(ADMIN_ID):
        row_last.append(types.InlineKeyboardButton("⚙️ پنل مدیریت ادمین", callback_data="admin_panel", style="primary"))
    markup.add(*row_last)
    return markup

def send_main_menu(chat_id, user_id):
    bot.send_message(
        chat_id,
        "🚀 سلام دوست خوبم به ربات هوش مصنوعی خودت خوش امدی از منو پایین گزینه مورد نظرت رو انتخاب کن 🫡!",
        reply_markup=get_main_menu_markup(user_id)
    )

def send_history_menu(chat_id, user_id, message_id=None):
    sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
    active_sess = safe_kv_get(f"ACTIVE_SESSION_{user_id}")

    if not sessions:
        empty_text = "📜 هیچ تاریخچه گفتگویی در حافظه یافت نشد."
        if message_id:
            try:
                bot.edit_message_text(empty_text, chat_id=chat_id, message_id=message_id)
                return
            except Exception:
                pass
        bot.send_message(chat_id, empty_text)
        return

    markup = types.InlineKeyboardMarkup()
    for s in sessions[:12]:
        sid = s.get("id")
        is_cur = "🟢 " if sid == active_sess else "💬 "
        date_str = format_session_date(s.get("date"))
        title = f"{is_cur}{s.get('title')} [{date_str}]"
        
        markup.row(
            types.InlineKeyboardButton(title, callback_data=f"switch_sess_{sid}"),
            types.InlineKeyboardButton("🗑", callback_data=f"del_single_sess_{sid}", style="danger")
        )

    markup.add(
        types.InlineKeyboardButton("➕ ایجاد چت جدید", callback_data="new_chat", style="success"),
        types.InlineKeyboardButton("🗑 پاکسازی کامل همه چت‌ها", callback_data="clear_all_history", style="danger")
    )
    markup.add(
        types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")
    )

    text = "📜 **لیست گفتگوهای ذخیره‌شده شما:**\nبرای انتخاب روی متن چت و برای حذف تکی روی دکمه سطل زباله (🗑) کلیک کنید:"
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def send_models_hub(chat_id, target_key_id, is_group=False, message_id=None):
    keys = ["AI_MODELS", "IMAGE_MODELS", f"USER_MODEL_{target_key_id}", f"USER_IMG_MODEL_{target_key_id}"]
    res = upstash_command(["MGET"] + keys) or [None, None, None, None]

    chat_models = json.loads(res[0] or "[]")
    img_models = json.loads(res[1] or "[]")
    cur_chat_idx = int(res[2] or "0")
    cur_img_idx = int(res[3] or "0")

    chat_name = chat_models[cur_chat_idx].get("name") if cur_chat_idx < len(chat_models) else "تعریف نشده"
    img_name = img_models[cur_img_idx].get("name") if cur_img_idx < len(img_models) else "تعریف نشده"

    text = (
        "✨ **منوی جامع مدیریت مدل‌های هوش مصنوعی**\n\n"
        f"💬 مدل فعال چت: **{chat_name}**\n"
        f"🎨 مدل فعال عکس: **{img_name}**\n\n"
        "بخش مورد نظر را برای انتخاب یا تغییر انتخاب کنید:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💬 مدل‌های چت و کدنویسی", callback_data="models_cat_chat", style="primary"),
        types.InlineKeyboardButton("🎨 مدل‌های ساخت عکس", callback_data="models_cat_image", style="success")
    )
    if is_group:
        markup.add(types.InlineKeyboardButton("❌ بستن منو", callback_data="close_menu", style="danger"))
    else:
        markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu"))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def build_model_selection_markup(target_key_id, is_group=False, models=None, current_idx=None):
    if models is None or current_idx is None:
        keys = ["AI_MODELS", f"USER_MODEL_{target_key_id}"]
        res = upstash_command(["MGET"] + keys) or [None, None]
        models = json.loads(res[0] or "[]")
        current_idx = res[1] or "0"

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for idx, m in enumerate(models):
        chk = "✅ " if str(idx) == str(current_idx) else "🤖 "
        vis = " 👁️" if m.get("supportsVision") else ""
        btn_text = f"{chk}{m.get('name')}{vis}"
        buttons.append(types.InlineKeyboardButton(btn_text, callback_data=f"set_model_{idx}"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی مدل‌ها", callback_data="models_hub"))
    return markup

def build_image_model_selection_markup(target_key_id, is_group=False, img_models=None, current_idx=None):
    if img_models is None or current_idx is None:
        keys = ["IMAGE_MODELS", f"USER_IMG_MODEL_{target_key_id}"]
        res = upstash_command(["MGET"] + keys) or [None, None]
        img_models = json.loads(res[0] or "[]")
        current_idx = res[1] or "0"

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for idx, m in enumerate(img_models):
        chk = "✅ " if str(idx) == str(current_idx) else "🎨 "
        buttons.append(types.InlineKeyboardButton(f"{chk}{m.get('name')}", callback_data=f"set_img_model_{idx}"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی مدل‌ها", callback_data="models_hub"))
    return markup

def send_image_model_selection_menu(chat_id, user_id, is_group=False):
    target_key = f"group_{chat_id}" if is_group else user_id
    keys = ["IMAGE_MODELS", f"USER_IMG_MODEL_{target_key}"]
    res = upstash_command(["MGET"] + keys) or [None, None]
    img_models = json.loads(res[0] or "[]")

    if not img_models:
        bot.send_message(chat_id, "⚠️ هیچ مدل تصویرسازی تعریف نشده است.")
        return

    current_idx = res[1] or "0"
    markup = build_image_model_selection_markup(target_key, is_group, img_models, current_idx)
    bot.send_message(chat_id, "🎨 **مدل ساخت عکس را انتخاب کنید:**", parse_mode="Markdown", reply_markup=markup)

# ==========================================
# ۲. پنل مدیریت ادمین
# ==========================================
def get_admin_panel_markup():
    is_active = safe_kv_get("BOT_GLOBAL_STATUS") != "off"
    power_btn_text = "🔴 خاموش کردن کل ربات" if is_active else "🟢 روشن کردن کل ربات"
    power_callback = "admin_toggle_off" if is_active else "admin_toggle_on"
    power_style = "danger" if is_active else "success"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(power_btn_text, callback_data=power_callback, style=power_style),
        types.InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_stats", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast", style="primary"),
        types.InlineKeyboardButton("🗑 پاکسازی کل تاریخچه‌ها", callback_data="admin_purge_all_hist", style="danger")
    )
    markup.add(
        types.InlineKeyboardButton("➕ افزودن مدل چت", callback_data="admin_add_model", style="success"),
        types.InlineKeyboardButton("🎨 افزودن مدل عکس", callback_data="admin_add_img_model", style="success")
    )
    markup.add(
        types.InlineKeyboardButton("📋 لیست مدل‌ها", callback_data="admin_list_models"),
        types.InlineKeyboardButton("✏️ ویرایش مدل‌ها", callback_data="admin_edit_models_menu", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("📢 افزودن اسپانسر", callback_data="admin_add_sponsor", style="primary"),
        types.InlineKeyboardButton("🗑 حذف اسپانسر", callback_data="admin_del_sponsor_menu", style="danger")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 مسدودسازی کاربر", callback_data="admin_ban_user", style="danger"),
        types.InlineKeyboardButton("✅ رفع مسدودی", callback_data="admin_unban_user", style="success")
    )
    markup.add(
        types.InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")
    )
    return markup

def send_bot_stats(chat_id):
    users = get_all_bot_users()
    total_users = len(users)

    now_ms = int(time.time() * 1000)
    day_ms = 24 * 60 * 60 * 1000
    active_count = 0

    if users:
        keys = [f"LAST_ACTIVE_{u}" for u in users]
        for i in range(0, len(keys), 100):
            batch_keys = keys[i:i+100]
            res = upstash_command(["MGET"] + batch_keys)
            if res and isinstance(res, list):
                for val in res:
                    if val and str(val).isdigit() and (now_ms - int(val)) < day_ms:
                        active_count += 1

    status_str = "🟢 روشن و فعال" if safe_kv_get("BOT_GLOBAL_STATUS") != "off" else "🔴 خاموش (متوقف)"
    text = (
        f"📊 **آمار جامع کاربران و وضعیت ربات:**\n\n"
        f"⚡ وضعیت ربات: **{status_str}**\n"
        f"👥 کل کاربران ثبت‌نامی در حافظه: **{total_users}**\n"
        f"🟢 کاربران فعال در ۲۴ ساعت اخیر: **{active_count}**"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin_panel", style="primary"))
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def broadcast_worker(admin_chat_id, message_id):
    users = get_all_bot_users()
    if not users:
        bot.send_message(admin_chat_id, "⚠️ هیچ کاربری در دیتابیس ربات ثبت نشده است.")
        return

    status_msg = bot.send_message(admin_chat_id, f"⏳ ارسال پیام همگانی به {len(users)} کاربر آغاز شد...")
    success = 0
    failed = 0

    for u in users:
        try:
            bot.copy_message(chat_id=int(u), from_chat_id=admin_chat_id, message_id=message_id)
            success += 1
            time.sleep(0.05)
        except ApiTelegramException as te:
            failed += 1
            if te.error_code == 429:
                time.sleep(te.result_json.get('parameters', {}).get('retry_after', 3))
        except Exception:
            failed += 1

    report = (
        f"✅ **ارسال پیام همگانی به پایان رسید!**\n\n"
        f"👥 کل کاربران: **{len(users)}**\n"
        f"🟢 ارسال موفق: **{success}**\n"
        f"🔴 ناموفق / بلاک: **{failed}**"
    )
    try:
        bot.edit_message_text(report, chat_id=admin_chat_id, message_id=status_msg.message_id, parse_mode="Markdown")
    except Exception:
        bot.send_message(admin_chat_id, report, parse_mode="Markdown")

def send_admin_models_list(chat_id, message_id=None):
    chat_models = json.loads(safe_kv_get("AI_MODELS") or "[]")
    img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for idx, m in enumerate(chat_models):
        buttons.append(types.InlineKeyboardButton(f"🗑 چت: {m.get('name')}", callback_data=f"del_model_{idx}", style="danger"))
    for idx, m in enumerate(img_models):
        buttons.append(types.InlineKeyboardButton(f"🗑 عکس: {m.get('name')}", callback_data=f"del_img_model_{idx}", style="danger"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    markup.add(types.InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin_panel"))
    text = "📋 **لیست و حذف مدل‌ها:**"
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

def send_admin_edit_models_list(chat_id):
    chat_models = json.loads(safe_kv_get("AI_MODELS") or "[]")
    img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for idx, m in enumerate(chat_models):
        buttons.append(types.InlineKeyboardButton(f"✏️ چت: {m.get('name')}", callback_data=f"edit_model_{idx}", style="primary"))
    for idx, m in enumerate(img_models):
        buttons.append(types.InlineKeyboardButton(f"✏️ عکس: {m.get('name')}", callback_data=f"edit_img_model_{idx}", style="primary"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    markup.add(types.InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin_panel"))
    bot.send_message(chat_id, "✏️ **مدلی که قصد ویرایش آن را دارید انتخاب کنید:**", reply_markup=markup)

def send_admin_sponsor_list(chat_id, message_id=None):
    channels = json.loads(safe_kv_get("SPONSOR_CHANNELS") or "[]")
    list_text = "📢 هیچ کانال اسپانسری ثبت نشده است." if not channels else "📢 **لیست کانال‌های اسپانسری:**"
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for idx, ch in enumerate(channels):
        buttons.append(types.InlineKeyboardButton(f"🗑 {ch}", callback_data=f"del_sponsor_{idx}", style="danger"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    markup.add(types.InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin_panel"))
    if message_id:
        try:
            bot.edit_message_text(list_text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, list_text, reply_markup=markup)

# ==========================================
# ۳. پردازش چت هوش مصنوعی
# ==========================================
def worker_ai_process(chat_id, user_id, message, text_prompt, target_key_id, is_group, target_reply_id, thread_id=None):
    models = json.loads(safe_kv_get("AI_MODELS") or "[]")
    active_session_id = get_or_create_active_session(user_id)

    user_selected = safe_kv_get(f"USER_MODEL_{target_key_id}") or safe_kv_get(f"USER_MODEL_{user_id}") or "0"
    try:
        model_idx = int(user_selected)
    except:
        model_idx = 0

    if not models or model_idx >= len(models):
        bot.send_message(chat_id, "⚠️ ابتدا یک مدل چت اضافه کنید.", message_thread_id=thread_id)
        return

    active_model = models[model_idx]
    if not text_prompt:
        text_prompt = "سلام"
        
    is_code = is_code_request(text_prompt)
    is_greeting = is_casual_greeting(text_prompt)

    req_id = f"{user_id}_{int(time.time()*1000)}"
    cancel_markup = types.InlineKeyboardMarkup()
    cancel_markup.add(types.InlineKeyboardButton("❌ لغو و توقف فکر کردن", callback_data=f"cancel_req_{req_id}", style="danger"))

    reply_to = target_reply_id if target_reply_id else (message.message_id if is_group else None)
    initial_text = "💻 در حال آماده‌سازی کد... ⏱️ 00:00" if is_code else "🧠 در حال پردازش و پاسخ... ⏱️ 00:00"

    try:
        status_msg = bot.send_message(
            chat_id, initial_text,
            reply_markup=cancel_markup,
            reply_to_message_id=reply_to,
            allow_sending_without_reply=True,
            message_thread_id=thread_id
        )
    except Exception:
        status_msg = bot.send_message(chat_id, initial_text, reply_markup=cancel_markup, message_thread_id=thread_id)

    status_msg_id = status_msg.message_id
    is_done = False
    api_response_text = None
    start_time = time.time()

    def timer_loop():
        last_edit_time = 0
        while not is_done:
            time.sleep(0.5)
            if is_done or safe_kv_get(f"CANCEL_{req_id}") == "true":
                break

            now = time.time()
            elapsed = int(now - start_time)
            if elapsed >= 2100:
                break

            if now - last_edit_time >= 2:
                mins = elapsed // 60
                secs = elapsed % 60
                time_display = f"{mins:02d}:{secs:02d}"

                cur_txt = f"💻 در حال آماده‌سازی کد... ⏱️ {time_display}" if is_code else f"🧠 در حال پردازش و پاسخ... ⏱️ {time_display}"
                try:
                    bot.edit_message_text(cur_txt, chat_id=chat_id, message_id=status_msg_id, reply_markup=cancel_markup)
                    last_edit_time = now
                except ApiTelegramException as te:
                    if te.error_code == 429:
                        wait_time = te.result_json.get('parameters', {}).get('retry_after', 3)
                        last_edit_time = now + wait_time
                except Exception:
                    pass

    t_thread = threading.Thread(target=timer_loop, daemon=True)
    t_thread.start()

    try:
        history = json.loads(safe_kv_get(f"HISTORY_{user_id}_{active_session_id}") or "[]")
        user_content = text_prompt

        if message.photo:
            if not active_model.get("supportsVision"):
                is_done = True
                bot.edit_message_text("❌ این مدل از تحلیل عکس پشتیبانی نمی‌کند.", chat_id=chat_id, message_id=status_msg_id)
                return

            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            img_bytes = bot.download_file(file_info.file_path)
            b64_img = base64.b64encode(img_bytes).decode('utf-8')
            user_content = [
                {"type": "text", "text": text_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
            ]

        history.append({"role": "user", "content": user_content})

        if is_greeting:
            cleaned_messages = [{"role": "user", "content": text_prompt}]
        else:
            cleaned_messages = []
            for idx, item in enumerate(history):
                if idx < len(history) - 1 and isinstance(item.get("content"), list):
                    txt_part = next((p.get("text") for p in item["content"] if p.get("type") == "text"), "تصویر قبلی")
                    cleaned_messages.append({"role": item["role"], "content": f"[تصویر ارسال شده: {txt_part}]"})
                else:
                    cleaned_messages.append(item)

            while cleaned_messages and cleaned_messages[0].get("role") == "assistant":
                cleaned_messages.pop(0)

            if len(cleaned_messages) > 4:
                cleaned_messages = cleaned_messages[-4:]
                if cleaned_messages and cleaned_messages[0].get("role") == "assistant":
                    cleaned_messages.pop(0)

        base_url = active_model.get("baseUrl", "").strip().rstrip("/")
        endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"

        system_prompt = {
            "role": "system",
            "content": (
                f"You are {active_model.get('name')}, a smart and friendly AI assistant. "
                "CRITICAL RULES:\n"
                "1. Always reply in clean, natural Persian directly to the user.\n"
                "2. NEVER output English internal monologue, notes, or meta-analysis. Never reveal your chain of thought.\n"
                "3. If the user greets you, reply with an affectionate, natural, friendly Persian greeting immediately. Do NOT write code unless explicitly requested in the CURRENT message.\n"
                "4. When code is explicitly requested, provide a brief, concise Persian explanation first, then the complete code inside markdown codeblocks."
            )
        }

        payload = {
            "model": active_model.get("modelName"),
            "messages": [system_prompt] + cleaned_messages,
            "max_tokens": 8192,
            "stream": True
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {active_model.get('apiKey', '')}",
            "Accept": "text/event-stream"
        }

        res = http_session.post(endpoint, headers=headers, json=payload, timeout=(60, 2100), stream=True)
        res.encoding = 'utf-8'

        if res.status_code == 200:
            full_content = ""
            full_reasoning = ""
            content_type = res.headers.get("Content-Type", "").lower()
            is_stream_response = "text/event-stream" in content_type

            if is_stream_response:
                for raw_line in res.iter_lines():
                    if safe_kv_get(f"CANCEL_{req_id}") == "true":
                        break
                    if not raw_line:
                        continue
                    
                    if isinstance(raw_line, bytes):
                        line = raw_line.decode('utf-8', errors='replace')
                    else:
                        line = raw_line

                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            c = delta.get("content")
                            r = delta.get("reasoning_content")
                            if c:
                                full_content += c
                            if r:
                                full_reasoning += r
                        except Exception:
                            continue

                clean_c = re.sub(r'<think>[\s\S]*?</think>', '', full_content, flags=re.IGNORECASE).strip()
                if clean_c:
                    api_response_text = clean_c
                elif full_content.strip():
                    api_response_text = full_content.strip()
                else:
                    api_response_text = re.sub(r'<think>[\s\S]*?</think>', '', full_reasoning, flags=re.IGNORECASE).strip()
            else:
                try:
                    data = res.json()
                except Exception:
                    data = json.loads(res.content.decode('utf-8', errors='replace'))
                
                msg_obj = data.get("choices", [{}])[0].get("message", {})
                c = msg_obj.get("content", "")
                r = msg_obj.get("reasoning_content", "")
                
                clean_c = re.sub(r'<think>[\s\S]*?</think>', '', c, flags=re.IGNORECASE).strip()
                api_response_text = clean_c if clean_c else (c if c.strip() else r)
        else:
            api_response_text = f"❌ خطای سرور API (کد {res.status_code}):\n{res.text[:250]}"

        if api_response_text:
            api_response_text = re.sub(r'<think>[\s\S]*?</think>', '', api_response_text, flags=re.IGNORECASE).strip()

        if api_response_text and not api_response_text.startswith("❌"):
            clean_text, code_files = process_code_and_text(api_response_text, is_code)

            history.append({"role": "assistant", "content": clean_text[:800]})
            hist_to_save = []
            for item in history[-6:]:
                if isinstance(item.get("content"), list):
                    txt_part = next((p.get("text") for p in item["content"] if p.get("type") == "text"), "تصویر")
                    hist_to_save.append({"role": item["role"], "content": txt_part})
                else:
                    hist_to_save.append(item)

            safe_kv_put(f"HISTORY_{user_id}_{active_session_id}", hist_to_save)
            update_session_title_if_new(user_id, active_session_id, text_prompt)

    except requests.exceptions.Timeout:
        api_response_text = "❌ زمان ارسال درخواست به بیش از ۳۵ دقیقه رسید و ارتباط قطع شد."
    except requests.exceptions.ConnectionError:
        api_response_text = "❌ خطای قطع ارتباط با سرور هوش مصنوعی (ارتباط بسته شد)."
    except Exception as e:
        api_response_text = f"❌ خطای ارتباطی: {type(e).__name__} - {str(e)[:100]}"
    finally:
        is_done = True
        safe_kv_delete(f"CANCEL_{req_id}")

    if api_response_text and not api_response_text.startswith("❌"):
        if is_group:
            sender_name = f"@{message.from_user.username}" if message.from_user.username else (message.from_user.first_name or "کاربر")
            final_text = f"👤 **کاربر:** {sender_name} | 🤖 **مدل:** {active_model.get('name')}\n\n{clean_text}"
        else:
            final_text = clean_text

        send_safe_ai_response(chat_id, status_msg_id, final_text, reply_to, thread_id)
        
        for filename, byte_data, ext in code_files:
            send_code_document_safe(
                chat_id=chat_id,
                byte_data=byte_data,
                filename=filename,
                ext=ext,
                reply_to_id=status_msg_id,
                thread_id=thread_id
            )
    else:
        if safe_kv_get(f"CANCEL_{req_id}") != "true":
            try:
                bot.edit_message_text(api_response_text or "❌ سرور پاسخی ارسال نکرد (پاسخ خالی بود).", chat_id=chat_id, message_id=status_msg_id)
            except Exception:
                pass

# ==========================================
# ۴. پردازش ساخت عکس (کرنومتر زنده + دکمه لغو فعال)
# ==========================================
def worker_image_process(chat_id, user_id, prompt_text, target_key_id, thread_id=None):
    img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
    img_idx_str = safe_kv_get(f"USER_IMG_MODEL_{target_key_id}") or safe_kv_get(f"USER_IMG_MODEL_{user_id}") or "0"
    try:
        img_idx = int(img_idx_str)
    except:
        img_idx = 0

    if not img_models or img_idx >= len(img_models):
        bot.send_message(chat_id, "⚠️ هیچ مدل تصویرسازی تعریف نشده است.", message_thread_id=thread_id)
        return

    active_img_model = img_models[img_idx]

    # تنظیم دکمه لغو ساخت تصویر
    req_id = f"{user_id}_img_{int(time.time()*1000)}"
    cancel_markup = types.InlineKeyboardMarkup()
    cancel_markup.add(types.InlineKeyboardButton("❌ لغو ساخت تصویر", callback_data=f"cancel_req_{req_id}", style="danger"))

    status_msg = bot.send_message(
        chat_id,
        f"🎨 در حال ساخت تصویر با {active_img_model.get('name')}... ⏱️ 00:00",
        reply_markup=cancel_markup,
        message_thread_id=thread_id
    )
    status_msg_id = status_msg.message_id
    is_done = False
    image_data = None
    error_msg = None
    start_time = time.time()

    def timer_loop():
        last_edit_time = 0
        while not is_done:
            time.sleep(0.5)
            if is_done or safe_kv_get(f"CANCEL_{req_id}") == "true":
                break

            now = time.time()
            elapsed = int(now - start_time)
            if elapsed >= 2100:
                break

            if now - last_edit_time >= 2:
                mins = elapsed // 60
                secs = elapsed % 60
                time_display = f"{mins:02d}:{secs:02d}"
                try:
                    bot.edit_message_text(
                        f"🎨 در حال ساخت تصویر با {active_img_model.get('name')}... ⏱️ {time_display}",
                        chat_id=chat_id,
                        message_id=status_msg_id,
                        reply_markup=cancel_markup
                    )
                    last_edit_time = now
                except ApiTelegramException as te:
                    if te.error_code == 429:
                        wait_time = te.result_json.get('parameters', {}).get('retry_after', 3)
                        last_edit_time = now + wait_time
                except Exception:
                    pass

    threading.Thread(target=timer_loop, daemon=True).start()

    try:
        base_url = active_img_model.get("baseUrl", "").strip().rstrip("/")
        api_key = active_img_model.get("apiKey", "").strip()
        model_name = active_img_model.get("modelName", "").strip()

        if "stability.ai" in base_url:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Accept": "image/*"
            }
            res = http_session.post(
                base_url,
                headers=headers,
                files={"none": ''},
                data={"prompt": prompt_text, "output_format": "webp"},
                timeout=(60, 2100)
            )
            if safe_kv_get(f"CANCEL_{req_id}") == "true":
                return
            if res.status_code == 200:
                image_data = res.content
            else:
                error_msg = f"کد خطا: {res.status_code}\n{res.text[:200]}"

        elif "pollinations.ai" in base_url:
            encoded_prompt = urllib.parse.quote(prompt_text)
            image_data = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            if model_name and model_name.lower() != "flux":
                image_data += f"?model={model_name}"

        else:
            endpoint = base_url if base_url.endswith("/images/generations") else f"{base_url}/images/generations"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Connection": "keep-alive"
            }
            payload = {
                "model": model_name,
                "prompt": prompt_text,
                "n": 1,
                "size": "1024x1024"
            }
            res = http_session.post(endpoint, headers=headers, json=payload, timeout=(60, 2100))
            if safe_kv_get(f"CANCEL_{req_id}") == "true":
                return
            if res.status_code == 200:
                data = res.json()
                if "data" in data and len(data["data"]) > 0:
                    image_data = data["data"][0].get("url")
            else:
                error_msg = f"کد خطا: {res.status_code}\n{res.text[:200]}"

    except Exception as e:
        error_msg = str(e)
    finally:
        is_done = True

    # بررسی لغو شدن توسط کاربر
    if safe_kv_get(f"CANCEL_{req_id}") == "true":
        safe_kv_delete(f"CANCEL_{req_id}")
        try:
            bot.edit_message_text("❌ عملیات ساخت تصویر توسط کاربر لغو گردید.", chat_id=chat_id, message_id=status_msg_id)
        except Exception:
            pass
        return

    safe_kv_delete(f"CANCEL_{req_id}")

    if image_data:
        try:
            bot.delete_message(chat_id, status_msg_id)
        except Exception:
            pass
        caption = f"✨ **تصویر تولید شده با {active_img_model.get('name')}**\n\n📝 **پرامپت:** {prompt_text}"
        try:
            bot.send_photo(chat_id, image_data, caption=caption, parse_mode="Markdown", message_thread_id=thread_id)
        except Exception:
            bot.send_photo(chat_id, image_data, caption=caption, message_thread_id=thread_id)
    else:
        try:
            bot.edit_message_text(f"❌ ساخت تصویر با خطا مواجه شد.\n{error_msg or ''}", chat_id=chat_id, message_id=status_msg_id)
        except Exception:
            pass

# ==========================================
# ۵. هندلر پیام‌ها و رویدادهای تلگرام
# ==========================================
@bot.message_handler(content_types=['text', 'photo', 'document', 'video', 'audio', 'voice', 'sticker'])
def handle_all_messages(msg):
    if not msg.from_user:
        return

    chat_id = msg.chat.id
    user_id = str(msg.from_user.id)
    text = msg.text or msg.caption or ""
    is_group = msg.chat.type in ["group", "supergroup"]
    thread_id = getattr(msg, 'message_thread_id', None) if getattr(msg, 'is_topic_message', False) else None

    # بررسی وضعیت خاموش بودن ربات
    is_bot_active = safe_kv_get("BOT_GLOBAL_STATUS") != "off"
    if not is_bot_active and user_id != ADMIN_ID:
        bot.send_message(
            chat_id,
            "⚠️ **ربات موقتاً توسط مدیریت خاموش و در دست به‌روزرسانی می‌باشد.**\nلطفاً شکیبا باشید و ساعاتی دیگر مجدداً مراجعه کنید. 🙏",
            parse_mode="Markdown",
            message_thread_id=thread_id
        )
        return

    # ثبت امن کاربر در دیتابیس (بدون ریسک حذف دیتابیس)
    threading.Thread(target=track_user_activity, args=(user_id,), daemon=True).start()

    # محتوای فایل‌های متنی/کد
    if msg.document:
        doc = msg.document
        exts = ('.js', '.py', '.txt', '.json', '.html', '.css', '.cpp', '.java')
        if doc.file_name and doc.file_name.lower().endswith(exts):
            try:
                f_info = bot.get_file(doc.file_id)
                f_bytes = bot.download_file(f_info.file_path)
                f_text = f_bytes.decode('utf-8', errors='ignore')
                text = f"{text}\n\n محتوای فایل ارسال شده ({doc.file_name}):\n```\n{f_text}\n```"
            except Exception as e:
                print(f"[Doc Error]: {e}")

    if safe_kv_get(f"BANNED_{user_id}") == "true":
        bot.send_message(chat_id, "⛔ حساب شما توسط مدیریت مسدود شده است.", message_thread_id=thread_id)
        return

    # ارسال پیام کاربر به پشتیبانی
    if not is_group and safe_kv_get(f"USER_SUPPORT_STEP_{user_id}") == "AWAITING_MSG":
        safe_kv_delete(f"USER_SUPPORT_STEP_{user_id}")
        sender_name = msg.from_user.first_name or "کاربر"
        sender_user = f"@{msg.from_user.username}" if msg.from_user.username else "بدون یوزرنیم"

        admin_notify = (
            f"📩 **پیام جدید از کاربر به پشتیبانی:**\n\n"
            f"👤 **نام:** {sender_name}\n"
            f"🆔 **آیدی عددی:** `{user_id}`\n"
            f"🔗 **یوزرنیم:** {sender_user}\n\n"
            f"👇 متن یا فایل ارسال شده کاربر در زیر فوروارد شد:"
        )
        markup_reply = types.InlineKeyboardMarkup()
        markup_reply.add(types.InlineKeyboardButton("✍️ ارسال پاسخ به این کاربر", callback_data=f"admin_reply_{user_id}", style="primary"))
        
        try:
            bot.send_message(ADMIN_ID, admin_notify, parse_mode="Markdown")
            bot.copy_message(chat_id=ADMIN_ID, from_chat_id=chat_id, message_id=msg.message_id, reply_markup=markup_reply)
            bot.send_message(chat_id, "✅ پیام شما با موفقیت به مدیریت و پشتیبانی ربات ارسال شد. به زودی پاسخ شما داده خواهد شد.")
        except Exception as e:
            bot.send_message(chat_id, f"❌ خطا در ارسال پیام به پشتیبانی: {e}")
        return

    # ارسال پاسخ ادمین به کاربر
    if not is_group and user_id == ADMIN_ID:
        admin_step = safe_kv_get(f"ADMIN_STEP_{user_id}")
        if admin_step and admin_step.startswith("REPLY_TO_"):
            target_uid = admin_step.replace("REPLY_TO_", "")
            safe_kv_delete(f"ADMIN_STEP_{user_id}")
            try:
                bot.send_message(target_uid, "📩 **پاسخ پشتیبانی و مدیریت به پیام شما:**", parse_mode="Markdown")
                bot.copy_message(chat_id=target_uid, from_chat_id=chat_id, message_id=msg.message_id)
                bot.send_message(chat_id, f"✅ پاسخ شما با موفقیت برای کاربر `{target_uid}` ارسال گردید.", parse_mode="Markdown")
            except Exception as e:
                bot.send_message(chat_id, f"❌ خطا در ارسال پیام به کاربر: {e}")
            return

        if admin_step:
            if admin_step == "BROADCAST_MSG":
                clear_user_state(user_id)
                threading.Thread(target=broadcast_worker, args=(chat_id, msg.message_id), daemon=True).start()
                return
            else:
                handle_admin_steps(chat_id, user_id, text, admin_step)
                return

    if not is_group:
        ok_sponsor, unjoined = check_sponsor_join(user_id)
        if not ok_sponsor and ADMIN_ID and user_id != ADMIN_ID:
            markup = types.InlineKeyboardMarkup(row_width=2)
            buttons = [types.InlineKeyboardButton(f"📢 ورود به کانال {ch}", url=f"https://t.me/{ch.replace('@', '')}") for ch in unjoined]
            for i in range(0, len(buttons), 2):
                markup.row(*buttons[i:i+2])
            markup.add(types.InlineKeyboardButton("✅ عضو شدم / بررسی", callback_data="check_sponsor", style="success"))
            bot.send_message(chat_id, "⚠️ برای استفاده از ربات ابتدا باید در کانال(های) اسپانسر زیر عضو شوید:", reply_markup=markup)
            return

    if text.startswith("/start"):
        if is_group:
            if not is_group_admin(chat_id, user_id):
                return
            bot_info = bot.get_me()
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🤖 ورود به پیوی ربات", url=f"https://t.me/{bot_info.username}?start=true", style="primary"))
            bot.reply_to(
                msg,
                "⚠️ **منوی تنظیمات و مدیریت ربات فقط در چت خصوصی (پیوی) قابل استفاده است.**\n\nجهت استفاده از امکانات ربات روی دکمه زیر کلیک کنید:",
                parse_mode="Markdown",
                reply_markup=markup,
                allow_sending_without_reply=True
            )
            return
        clear_user_state(user_id)
        safe_kv_delete(f"USER_MODE_{user_id}")
        send_main_menu(chat_id, user_id)
        return

    if text.startswith("/models"):
        if is_group:
            if not is_group_admin(chat_id, user_id):
                bot.reply_to(msg, "⛔ تغییر مدل‌های ربات در گروه فقط توسط ادمین‌های گروه مجاز است.", allow_sending_without_reply=True)
                return
        elif ADMIN_ID and user_id != ADMIN_ID:
            bot.send_message(chat_id, "⛔ این دستور تنها برای ادمین ربات مجاز است.")
            return

        target_key = f"group_{chat_id}" if is_group else user_id
        send_models_hub(chat_id, target_key, is_group)
        return

    target_reply_id = msg.message_id
    if is_group:
        bot_info = bot.get_me()
        bot_id = str(bot_info.id)
        lower_text = text.lower().strip()

        if is_group_admin(chat_id, user_id) and msg.reply_to_message:
            target_user = msg.reply_to_message.from_user
            target_uid = target_user.id
            target_name = target_user.first_name or "کاربر"

            if lower_text.startswith("سکوت") or lower_text.startswith("بی صدا") or lower_text.startswith("/mute"):
                minutes = 0
                match_num = re.search(r'\d+', lower_text)
                if match_num:
                    minutes = int(match_num.group())

                until_date = int(time.time() + minutes * 60) if minutes > 0 else 0

                try:
                    bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=target_uid,
                        permissions=ChatPermissions(can_send_messages=False),
                        until_date=until_date
                    )
                    time_msg = f"به مدت **{minutes} دقیقه**" if minutes > 0 else "**به صورت دائم**"
                    bot.reply_to(msg, f"🔇 کاربر [{target_name}](tg://user?id={target_uid}) {time_msg} در گروه بی‌صدا شد.", parse_mode="Markdown")
                except Exception:
                    bot.reply_to(msg, "❌ خطای محدودسازی: دسترسی ادمینی ربات را در گروه بررسی کنید.")
                return

            elif lower_text in ["رفع سکوت", "ازاد", "آزاد", "/unmute"]:
                try:
                    bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=target_uid,
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True
                        )
                    )
                    bot.reply_to(msg, f"🔊 سکوت کاربر [{target_name}](tg://user?id={target_uid}) برداشته شد و می‌تواند پیام بفرستد.", parse_mode="Markdown")
                except Exception:
                    bot.reply_to(msg, "❌ خطا در رفع محدودیت.")
                return

            elif lower_text in ["اخراج", "بن", "بلاک", "/ban", "/kick"]:
                try:
                    bot.ban_chat_member(chat_id, target_uid)
                    bot.reply_to(msg, f"🚫 کاربر [{target_name}](tg://user?id={target_uid}) از گروه اخراج شد.", parse_mode="Markdown")
                except Exception:
                    bot.reply_to(msg, "❌ خطا در اخراج کاربر (ربات نمی‌تواند ادمین‌ها را اخراج کند).")
                return

            elif lower_text in ["حذف", "پاک", "دلیت", "/del"]:
                try:
                    bot.delete_message(chat_id, msg.reply_to_message.message_id)
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
                return

        admin_cmds = ["/bot", "bot", "/bot test", "bot test", "/bot سکوت", "bot سکوت", "/bot صحبت", "bot صحبت", "/bot راهنما", "bot راهنما"]
        if any(lower_text == c or lower_text.startswith(c + " ") for c in admin_cmds):
            if not is_group_admin(chat_id, user_id):
                return

            if "سکوت" in lower_text:
                safe_kv_put(f"GROUP_MUTED_{chat_id}", "true")
                bot.reply_to(msg, "🔇 **وضعیت ربات:** متوقف و در حالت سکوت قرار گرفت.", parse_mode="Markdown", allow_sending_without_reply=True)
                return
            elif "صحبت" in lower_text:
                safe_kv_put(f"GROUP_MUTED_{chat_id}", "false")
                bot.reply_to(msg, "🔊 **وضعیت ربات:** فعال و آماده پاسخگویی شد.", parse_mode="Markdown", allow_sending_without_reply=True)
                return
            elif "test" in lower_text:
                bot.reply_to(msg, "✅ **وضعیت ربات:** آنلاین، پایدار و متصل به هوش مصنوعی!", parse_mode="Markdown", allow_sending_without_reply=True)
                return
            else:
                help_text = (
                    "🛠 **پنل راهنمای مدیریت ربات در گروه**\n\n"
                    "🟢 وضعیت: `سیستم فعال و آماده به کار`\n\n"
                    "📌 **دستورات مدیریتی ویژه ادمین:**\n"
                    "🔹 `/bot test` ➔ بررسی وضعیت آنلاین بودن ربات\n"
                    "🔹 `/bot سکوت` ➔ متوقف کردن موقت پاسخگویی ربات\n"
                    "🔹 `/bot صحبت` ➔ فعال‌سازی مجدد ربات در گروه\n"
                    "🔹 `/models` ➔ انتخاب مدل چت و مدل عکس گروه\n\n"
                    "👮 **دستورات ناظمی (ریپلای روی پیام کاربر):**\n"
                    "🔸 `سکوت` یا `سکوت 10` ➔ بی‌صدا کردن کاربر\n"
                    "🔸 `رفع سکوت` یا `آزاد` ➔ لغو محدودیت کاربر\n"
                    "🔸 `اخراج` یا `بن` ➔ اخراج کاربر از گروه\n"
                    "🔸 `حذف` ➔ پاک کردن پیام متخلف"
                )
                bot.reply_to(msg, help_text, parse_mode="Markdown", allow_sending_without_reply=True)
                return

        if safe_kv_get(f"GROUP_MUTED_{chat_id}") == "true":
            return

        is_reply_to_bot = msg.reply_to_message and str(msg.reply_to_message.from_user.id) == bot_id

        robot_pattern = r'^(ربات|روبات|بات)[\s:,،\n]+(.*)$'
        robot_match = re.match(robot_pattern, text.strip(), flags=re.IGNORECASE | re.DOTALL)
        is_exact_robot_call = text.strip() in ["ربات", "روبات", "بات"]

        if not is_reply_to_bot and not robot_match and not is_exact_robot_call:
            return

        if robot_match:
            text = robot_match.group(2).strip()
        elif is_exact_robot_call:
            text = "سلام! در خدمتم، چطور می‌تونم کمکت کنم؟"

        if msg.reply_to_message and str(msg.reply_to_message.from_user.id) != bot_id:
            target_user = msg.reply_to_message.from_user
            target_name = target_user.first_name or "کاربر"
            target_reply_id = msg.reply_to_message.message_id
            replied_text = msg.reply_to_message.text or msg.reply_to_message.caption or ""

            if msg.reply_to_message.photo and not msg.photo:
                msg.photo = msg.reply_to_message.photo

            prompt_inst = text.strip() if text.strip() else "لطفاً بررسی کن و پاسخ کامل بده."
            
            if msg.reply_to_message.photo:
                text = f"پاسخ به عکس ارسالی ({target_name}): {prompt_inst}"
            else:
                text = f'[پیام ({target_name}): "{replied_text}"]\n\nدستور:\n{prompt_inst}'

    target_key_id = f"group_{chat_id}" if is_group else user_id
    has_photo_attached = bool(msg.photo or (msg.reply_to_message and msg.reply_to_message.photo))
    
    user_forced_mode = None if is_group else safe_kv_get(f"USER_MODE_{target_key_id}")
    
    is_img_prompt = False
    clean_img_prompt = text

    if not has_photo_attached:
        is_img_prompt, clean_img_prompt = detect_image_intent(text)

    # اگر کاربر در حالت عکس بود اما سوال متنی پرسید یا احوالپرسی کرد، اولویت با چت باشد
    if user_forced_mode == "IMAGE_GEN":
        if is_casual_greeting(text) or any(g in text.lower() for g in ['کد', 'برنامه', 'مدل', 'توضیح', 'چرا', 'چطور', 'چیست', 'سلام']):
            is_img_prompt = False
            user_forced_mode = None
            safe_kv_delete(f"USER_MODE_{target_key_id}")

    # فقط در صورت تشخیص قطعی عکس، به مدل عکس ارسال شود
    if is_img_prompt or (user_forced_mode == "IMAGE_GEN" and not has_photo_attached):
        img_prompt_to_use = clean_img_prompt if is_img_prompt else text
        threading.Thread(target=worker_image_process, args=(chat_id, user_id, img_prompt_to_use, target_key_id, thread_id), daemon=True).start()
    else:
        threading.Thread(target=worker_ai_process, args=(chat_id, user_id, msg, text, target_key_id, is_group, target_reply_id, thread_id), daemon=True).start()

# ==========================================
# ۶. هندلر دکمه‌های شیشه‌ای و سوییچ لحظه‌ای
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(query):
    chat_id = query.message.chat.id
    user_id = str(query.from_user.id)
    data = query.data
    is_group = query.message.chat.type in ["group", "supergroup"]
    target_key_id = f"group_{chat_id}" if is_group else user_id

    # بررسی وضعیت کلی ربات
    if safe_kv_get("BOT_GLOBAL_STATUS") == "off" and user_id != ADMIN_ID:
        bot.answer_callback_query(query.id, "⚠️ ربات هم‌اکنون توسط ادمین موقتاً خاموش شده است.", show_alert=True)
        return

    # هندلر مشترک لغو (هم برای چت و هم برای ساخت تصویر)
    if data.startswith("cancel_req_"):
        req_id = data.replace("cancel_req_", "")
        owner_id = req_id.split("_")[0]
        if user_id != owner_id:
            bot.answer_callback_query(query.id, "⛔ این درخواست متعلق به شما نیست!", show_alert=True)
            return

        bot.answer_callback_query(query.id, "✅ درخواست لغو شد.")
        safe_kv_put(f"CANCEL_{req_id}", "true", 2100)
        try:
            bot.edit_message_text("❌ عملیات با موفقیت لغو شد.", chat_id=chat_id, message_id=query.message.message_id)
        except Exception:
            pass
        return

    if is_group:
        group_allowed_actions = ["models_hub", "models_cat_chat", "models_cat_image", "close_menu"]
        is_set_action = data.startswith("set_model_") or data.startswith("set_img_model_")

        if data in group_allowed_actions or is_set_action:
            if not is_group_admin(chat_id, user_id):
                bot.answer_callback_query(query.id, "⛔ تغییر مدل‌های ربات در گروه فقط توسط ادمین امکان‌پذیر است!", show_alert=True)
                return

        pv_only = ["main_menu", "check_sponsor", "history_menu", "new_chat", "mode_chat", "mode_image", "clear_all_history", "contact_admin"]
        if data in pv_only or data.startswith("switch_sess_") or data.startswith("del_single_sess_") or data.startswith("admin_"):
            bot.answer_callback_query(query.id, "⚠️ این منو فقط در چت خصوصی (پیوی) ربات قابل استفاده است.", show_alert=True)
            return

    try:
        bot.answer_callback_query(query.id)
    except Exception:
        pass

    if data in ["check_sponsor", "main_menu", "mode_chat", "mode_image", "history_menu", "new_chat"]:
        clear_user_state(user_id)

    # ارتباط با پشتیبانی / ادمین
    if data == "contact_admin" and not is_group:
        safe_kv_put(f"USER_SUPPORT_STEP_{user_id}", "AWAITING_MSG")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="main_menu", style="danger"))
        bot.send_message(
            chat_id,
            "📞 **بخش پشتیبانی و ارتباط با مدیریت:**\n\nلطفاً پیام، پیشنهاد، گزارش یا سوال خود را ارسال کنید (متن، عکس، صدا و... پذیرفته می‌شود):",
            parse_mode="Markdown",
            reply_markup=markup
        )

    # پاسخ ادمین به پیام کاربر پشتیبانی
    elif data.startswith("admin_reply_") and user_id == ADMIN_ID:
        target_uid = data.replace("admin_reply_", "")
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"REPLY_TO_{target_uid}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel", style="danger"))
        bot.send_message(
            chat_id,
            f"✍️ **در حال پاسخ به کاربر با آیدی عددی:** `{target_uid}`\n\nلطفاً پیام پاسخ خود را ارسال کنید (متن، عکس، ویس و...):",
            parse_mode="Markdown",
            reply_markup=markup
        )

    # روشن / خاموش کردن کلی ربات
    elif data == "admin_toggle_off" and user_id == ADMIN_ID:
        safe_kv_put("BOT_GLOBAL_STATUS", "off")
        bot.send_message(chat_id, "🔴 **ربات با موفقیت خاموش شد.** (هیچ کاربری جز ادمین امکان استفاده ندارد)")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=get_admin_panel_markup())
        except Exception:
            pass

    elif data == "admin_toggle_on" and user_id == ADMIN_ID:
        safe_kv_delete("BOT_GLOBAL_STATUS")
        bot.send_message(chat_id, "🟢 **ربات با موفقیت روشن شد.** (همه کاربران به آن دسترسی دارند)")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=get_admin_panel_markup())
        except Exception:
            pass

    # پاکسازی تمام سوابق و تاریخچه‌ها توسط ادمین
    elif data == "admin_purge_all_hist" and user_id == ADMIN_ID:
        users = get_all_bot_users()
        count_purged = 0
        for u in users:
            sessions = json.loads(safe_kv_get(f"SESSIONS_{u}") or "[]")
            for s in sessions:
                sid = s.get("id")
                if sid:
                    safe_kv_delete(f"HISTORY_{u}_{sid}")
            safe_kv_delete(f"SESSIONS_{u}")
            safe_kv_delete(f"ACTIVE_SESSION_{u}")
            count_purged += 1

        bot.send_message(
            chat_id,
            f"🗑 **عملیات پاکسازی کامل انجام شد!**\n\nسوابق و تاریخچه مکالمات **{count_purged} کاربر** به طور کامل از دیتابیس حذف گردید.",
            parse_mode="Markdown"
        )

    elif data in ["check_sponsor", "main_menu"]:
        if not is_group:
            send_main_menu(chat_id, user_id)

    elif data == "close_menu":
        try:
            bot.delete_message(chat_id, query.message.message_id)
        except Exception:
            pass

    elif data == "mode_chat":
        safe_kv_delete(f"USER_MODE_{target_key_id}")
        bot.send_message(chat_id, "💬 حالت گفتگو و کدنویسی فعال شد.")

    elif data == "mode_image":
        safe_kv_put(f"USER_MODE_{target_key_id}", "IMAGE_GEN")
        if not is_group:
            send_image_model_selection_menu(chat_id, user_id, is_group=False)

    elif data == "models_hub":
        send_models_hub(chat_id, target_key_id, is_group, query.message.message_id)

    elif data == "models_cat_chat":
        new_markup = build_model_selection_markup(target_key_id, is_group)
        try:
            bot.edit_message_text("✨ **مدل هوش مصنوعی چت و کدنویسی را انتخاب کنید:**", chat_id=chat_id, message_id=query.message.message_id, parse_mode="Markdown", reply_markup=new_markup)
        except Exception:
            pass

    elif data == "models_cat_image":
        new_markup = build_image_model_selection_markup(target_key_id, is_group)
        try:
            bot.edit_message_text("🎨 **مدل ساخت عکس را انتخاب کنید:**", chat_id=chat_id, message_id=query.message.message_id, parse_mode="Markdown", reply_markup=new_markup)
        except Exception:
            pass

    elif data.startswith("set_model_"):
        idx = data.replace("set_model_", "")
        safe_kv_put(f"USER_MODEL_{target_key_id}", idx)
        
        # نکته کلیدی: با انتخاب مدل چت، وضعیت ساخت عکس فورس شده پاک می‌شود تا تداخلی رخ ندهد
        safe_kv_delete(f"USER_MODE_{target_key_id}")
        
        active_sess = safe_kv_get(f"ACTIVE_SESSION_{user_id}")
        if active_sess:
            safe_kv_delete(f"HISTORY_{user_id}_{active_sess}")

        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        name = models[int(idx)].get("name") if idx.isdigit() and int(idx) < len(models) else "انتخاب شده"

        try:
            new_markup = build_model_selection_markup(target_key_id, is_group)
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=new_markup)
        except Exception:
            pass

        bot.send_message(chat_id, f"✅ مدل چت بلافاصله روی **{name}** تنظیم شد.", parse_mode="Markdown")

    elif data.startswith("set_img_model_"):
        idx = data.replace("set_img_model_", "")
        safe_kv_put(f"USER_IMG_MODEL_{target_key_id}", idx)

        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        name = img_models[int(idx)].get("name") if idx.isdigit() and int(idx) < len(img_models) else "انتخاب شده"

        try:
            new_img_markup = build_image_model_selection_markup(target_key_id, is_group)
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=new_img_markup)
        except Exception:
            pass

        bot.send_message(chat_id, f"🎨 مدل ساخت عکس روی **{name}** تنظیم شد.", parse_mode="Markdown")

    elif data == "history_menu" and not is_group:
        send_history_menu(chat_id, user_id)

    elif data.startswith("del_single_sess_") and not is_group:
        del_id = data.replace("del_single_sess_", "")
        sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
        active_sess = safe_kv_get(f"ACTIVE_SESSION_{user_id}")

        safe_kv_delete(f"HISTORY_{user_id}_{del_id}")

        new_sessions = [s for s in sessions if s.get("id") != del_id]
        safe_kv_put(f"SESSIONS_{user_id}", new_sessions)

        if active_sess == del_id:
            if new_sessions:
                safe_kv_put(f"ACTIVE_SESSION_{user_id}", new_sessions[0]["id"])
            else:
                new_sess_id = f"sess_{int(time.time())}"
                safe_kv_put(f"ACTIVE_SESSION_{user_id}", new_sess_id)
                new_sessions = [{"id": new_sess_id, "title": "گفتگوی جدید 💬", "date": get_jalali_date()}]
                safe_kv_put(f"SESSIONS_{user_id}", new_sessions)

        try:
            bot.answer_callback_query(query.id, "🗑 این گفتگو با موفقیت حذف شد.")
        except Exception:
            pass

        send_history_menu(chat_id, user_id, message_id=query.message.message_id)

    elif data == "clear_all_history" and not is_group:
        sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
        for s in sessions:
            sid = s.get("id")
            if sid:
                safe_kv_delete(f"HISTORY_{user_id}_{sid}")
        safe_kv_delete(f"SESSIONS_{user_id}")
        safe_kv_delete(f"ACTIVE_SESSION_{user_id}")
        
        new_sess = f"sess_{int(time.time())}"
        safe_kv_put(f"ACTIVE_SESSION_{user_id}", new_sess)
        new_sessions = [{"id": new_sess, "title": "گفتگوی جدید 💬", "date": get_jalali_date()}]
        safe_kv_put(f"SESSIONS_{user_id}", new_sessions)

        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("➕ ایجاد چت جدید", callback_data="new_chat", style="success"),
                types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")
            )
            bot.edit_message_text(
                "🗑 **تمام تاریخچه و سوابق گفتگوهای قبلی شما با موفقیت پاک شدند!**\n\nاکنون می‌توانید گفتگوی جدیدی را آغاز کنید.",
                chat_id=chat_id,
                message_id=query.message.message_id,
                parse_mode="Markdown",
                reply_markup=markup
            )
        except Exception:
            bot.send_message(chat_id, "🗑 تمام تاریخچه گفتگوهای شما با موفقیت پاک شدند.")

    elif data == "new_chat" and not is_group:
        new_sess = f"sess_{int(time.time())}"
        safe_kv_put(f"ACTIVE_SESSION_{user_id}", new_sess)
        sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
        sessions.insert(0, {"id": new_sess, "title": "گفتگوی جدید 💬", "date": get_jalali_date()})
        safe_kv_put(f"SESSIONS_{user_id}", sessions)
        safe_kv_delete(f"USER_MODE_{user_id}")
        bot.send_message(chat_id, "✨ چت جدید ایجاد شد! پیام خود را بفرستید.")

    elif data.startswith("switch_sess_") and not is_group:
        sess_id = data.replace("switch_sess_", "")
        safe_kv_put(f"ACTIVE_SESSION_{user_id}", sess_id)
        bot.send_message(chat_id, "🔄 با موفقیت به این گفتگو منتقل شدید.")
        send_history_menu(chat_id, user_id, message_id=query.message.message_id)

    elif data == "admin_panel" and user_id == ADMIN_ID:
        clear_user_state(user_id)
        bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", parse_mode="Markdown", reply_markup=get_admin_panel_markup())

    elif data == "admin_stats" and user_id == ADMIN_ID:
        send_bot_stats(chat_id)

    elif data == "admin_broadcast" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "BROADCAST_MSG")
        bot.send_message(chat_id, "📢 **ارسال پیام همگانی:**\n\nلطفاً پیامی که می‌خواهید برای همه ارسال شود را بفرستید (متن، عکس، ویدیو، فایل صوتی یا فوروارد پیام):", parse_mode="Markdown")

    elif data == "admin_add_model" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_MODEL_NAME")
        bot.send_message(chat_id, "📝 نام عمومی مدل چت را وارد کنید:")

    elif data == "admin_add_img_model" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_IMG_NAME")
        bot.send_message(chat_id, "🎨 نام عمومی مدل ساخت عکس را وارد کنید:")

    elif data == "admin_list_models" and user_id == ADMIN_ID:
        send_admin_models_list(chat_id)

    elif data == "admin_edit_models_menu" and user_id == ADMIN_ID:
        send_admin_edit_models_list(chat_id)

    elif data.startswith("edit_model_") and user_id == ADMIN_ID:
        idx = data.replace("edit_model_", "")
        safe_kv_put(f"ADMIN_EDIT_IDX_{user_id}", idx)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_MODEL_NAME")
        bot.send_message(chat_id, "✏️ نام جدید مدل چت را وارد کنید (یا .):")

    elif data.startswith("edit_img_model_") and user_id == ADMIN_ID:
        idx = data.replace("edit_img_model_", "")
        safe_kv_put(f"ADMIN_EDIT_IMG_IDX_{user_id}", idx)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_IMG_NAME")
        bot.send_message(chat_id, "✏️ نام جدید مدل تصویر را وارد کنید (یا . برای عدم تغییر):")

    elif data.startswith("del_model_") and user_id == ADMIN_ID:
        idx = int(data.replace("del_model_", ""))
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if 0 <= idx < len(models):
            models.pop(idx)
            safe_kv_put("AI_MODELS", models)
        send_admin_models_list(chat_id, query.message.message_id)

    elif data.startswith("del_img_model_") and user_id == ADMIN_ID:
        idx = int(data.replace("del_img_model_", ""))
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if 0 <= idx < len(img_models):
            img_models.pop(idx)
            safe_kv_put("IMAGE_MODELS", img_models)
        send_admin_models_list(chat_id, query.message.message_id)

    elif data == "admin_add_sponsor" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_SPONSOR")
        bot.send_message(chat_id, "📢 آیدی کانال اسپانسری را وارد کنید:")

    elif data == "admin_del_sponsor_menu" and user_id == ADMIN_ID:
        send_admin_sponsor_list(chat_id)

    elif data.startswith("del_sponsor_") and user_id == ADMIN_ID:
        idx = int(data.replace("del_sponsor_", ""))
        channels = json.loads(safe_kv_get("SPONSOR_CHANNELS") or "[]")
        if 0 <= idx < len(channels):
            channels.pop(idx)
            safe_kv_put("SPONSOR_CHANNELS", channels)
        send_admin_sponsor_list(chat_id, query.message.message_id)

    elif data == "admin_ban_user" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "BAN_USER")
        bot.send_message(chat_id, "🚫 آیدی عددی کاربر برای مسدودسازی:")

    elif data == "admin_unban_user" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "UNBAN_USER")
        bot.send_message(chat_id, "✅ آیدی عددی کاربر برای رفع مسدودی:")

# ==========================================
# ۷. هندلر مراحل پنل مدیریت (Wizard Steps)
# ==========================================
def handle_admin_steps(chat_id, user_id, text, step):
    if step == "ADD_MODEL_NAME":
        safe_kv_put(f"TEMP_MODEL_{user_id}", {"name": text})
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_MODEL_URL")
        bot.send_message(chat_id, "🌐 **URL BASE** مربوط به API را وارد کنید:", parse_mode="Markdown")

    elif step == "ADD_MODEL_URL":
        temp = json.loads(safe_kv_get(f"TEMP_MODEL_{user_id}") or "{}")
        temp["baseUrl"] = text
        safe_kv_put(f"TEMP_MODEL_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_MODEL_KEY")
        bot.send_message(chat_id, "🔑 **API KEY** را وارد کنید:", parse_mode="Markdown")

    elif step == "ADD_MODEL_KEY":
        temp = json.loads(safe_kv_get(f"TEMP_MODEL_{user_id}") or "{}")
        temp["apiKey"] = text
        safe_kv_put(f"TEMP_MODEL_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_MODEL_ID")
        bot.send_message(chat_id, "📌 **MODEL NAME** اصلی را وارد کنید:", parse_mode="Markdown")

    elif step == "ADD_MODEL_ID":
        temp = json.loads(safe_kv_get(f"TEMP_MODEL_{user_id}") or "{}")
        temp["modelName"] = text
        safe_kv_put(f"TEMP_MODEL_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_MODEL_VISION")
        bot.send_message(chat_id, "👁 آیا این مدل **Vision** دارد؟ (`yes` یا `no`)", parse_mode="Markdown")

    elif step == "ADD_MODEL_VISION":
        temp = json.loads(safe_kv_get(f"TEMP_MODEL_{user_id}") or "{}")
        temp["supportsVision"] = (text.strip().lower() == "yes")
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        models.append(temp)
        safe_kv_put("AI_MODELS", models)
        clear_user_state(user_id)
        bot.send_message(chat_id, f"✅ مدل چت **{temp.get('name')}** اضافه شد!", parse_mode="Markdown")
        bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())

    elif step == "ADD_IMG_NAME":
        safe_kv_put(f"TEMP_IMG_{user_id}", {"name": text})
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_IMG_URL")
        bot.send_message(chat_id, "🌐 **URL BASE** تصویرساز را وارد کنید (مثلاً `https://api.siliconflow.cn/v1`):", parse_mode="Markdown")

    elif step == "ADD_IMG_URL":
        temp = json.loads(safe_kv_get(f"TEMP_IMG_{user_id}") or "{}")
        temp["baseUrl"] = text
        safe_kv_put(f"TEMP_IMG_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_IMG_KEY")
        bot.send_message(chat_id, "🔑 **API KEY** تصویرساز (اگر Pollinations است . بفرستید):", parse_mode="Markdown")

    elif step == "ADD_IMG_KEY":
        temp = json.loads(safe_kv_get(f"TEMP_IMG_{user_id}") or "{}")
        temp["apiKey"] = "" if text == "." else text
        safe_kv_put(f"TEMP_IMG_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_IMG_ID")
        bot.send_message(chat_id, "📌 **MODEL NAME** تصویرساز را وارد کنید (مثلاً `black-forest-labs/FLUX.1-schnell`):", parse_mode="Markdown")

    elif step == "ADD_IMG_ID":
        temp = json.loads(safe_kv_get(f"TEMP_IMG_{user_id}") or "{}")
        temp["modelName"] = text
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        img_models.append(temp)
        safe_kv_put("IMAGE_MODELS", img_models)
        clear_user_state(user_id)
        bot.send_message(chat_id, f"🎨 مدل عکس **{temp.get('name')}** اضافه شد!", parse_mode="Markdown")
        bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())

    elif step == "EDIT_MODEL_NAME":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IDX_{user_id}") or "0")
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if text != "." and idx < len(models):
            models[idx]["name"] = text
            safe_kv_put("AI_MODELS", models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_MODEL_URL")
        bot.send_message(chat_id, "🌐 URL Base جدید (یا . برای عدم تغییر):")

    elif step == "EDIT_MODEL_URL":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IDX_{user_id}") or "0")
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if text != "." and idx < len(models):
            models[idx]["baseUrl"] = text
            safe_kv_put("AI_MODELS", models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_MODEL_KEY")
        bot.send_message(chat_id, "🔑 API Key جدید (یا . برای عدم تغییر):")

    elif step == "EDIT_MODEL_KEY":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IDX_{user_id}") or "0")
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if text != "." and idx < len(models):
            models[idx]["apiKey"] = text
            safe_kv_put("AI_MODELS", models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_MODEL_ID")
        bot.send_message(chat_id, "📌 Model Name جدید (یا . برای عدم تغییر):")

    elif step == "EDIT_MODEL_ID":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IDX_{user_id}") or "0")
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if text != "." and idx < len(models):
            models[idx]["modelName"] = text
            safe_kv_put("AI_MODELS", models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_MODEL_VISION")
        bot.send_message(chat_id, "👁 قابلیت Vision؟ (`yes` یا `no` یا . برای عدم تغییر)", parse_mode="Markdown")

    elif step == "EDIT_MODEL_VISION":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IDX_{user_id}") or "0")
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if text != "." and idx < len(models):
            models[idx]["supportsVision"] = (text.strip().lower() == "yes")
            safe_kv_put("AI_MODELS", models)
        clear_user_state(user_id)
        bot.send_message(chat_id, "✅ مدل چت ویرایش شد!")
        bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())

    elif step == "EDIT_IMG_NAME":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IMG_IDX_{user_id}") or "0")
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if text != "." and idx < len(img_models):
            img_models[idx]["name"] = text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_IMG_URL")
        bot.send_message(chat_id, "🌐 URL Base جدید تصویرساز (یا . برای عدم تغییر):")

    elif step == "EDIT_IMG_URL":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IMG_IDX_{user_id}") or "0")
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if text != "." and idx < len(img_models):
            img_models[idx]["baseUrl"] = text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_IMG_KEY")
        bot.send_message(chat_id, "🔑 API Key جدید تصویرساز (یا . برای عدم تغییر):")

    elif step == "EDIT_IMG_KEY":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IMG_IDX_{user_id}") or "0")
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if text != "." and idx < len(img_models):
            img_models[idx]["apiKey"] = "" if text.strip() == "." else text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_IMG_ID")
        bot.send_message(chat_id, "📌 Model Name جدید تصویرساز (یا . برای عدم تغییر):")

    elif step == "EDIT_IMG_ID":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IMG_IDX_{user_id}") or "0")
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if text != "." and idx < len(img_models):
            img_models[idx]["modelName"] = text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
        clear_user_state(user_id)
        bot.send_message(chat_id, "✅ مدل ساخت عکس با موفقیت ویرایش شد!")
        bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())

    elif step == "ADD_SPONSOR":
        channels = json.loads(safe_kv_get("SPONSOR_CHANNELS") or "[]")
        ch_name = text.strip() if text.strip().startswith("@") else f"@{text.strip()}"
        if ch_name not in channels:
            channels.append(ch_name)
            safe_kv_put("SPONSOR_CHANNELS", channels)
        clear_user_state(user_id)
        bot.send_message(chat_id, f"📢 کانال اسپانسر {ch_name} اضافه شد.")
        bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())

    elif step == "BAN_USER":
        safe_kv_put(f"BANNED_{text.strip()}", "true")
        clear_user_state(user_id)
        bot.send_message(chat_id, f"🚫 کاربر {text.strip()} مسدود شد.")
        bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())

    elif step == "UNBAN_USER":
        safe_kv_delete(f"BANNED_{text.strip()}")
        clear_user_state(user_id)
        bot.send_message(chat_id, f"✅ کاربر {text.strip()} رفع مسدودی شد.")
        bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())

# ==========================================
# ۸. اجرای مداوم ربات (Long Polling بدون قطعی)
# ==========================================
if __name__ == "__main__":
    print("=" * 45)
    print("🤖 Neo-AI-Bot Started Successfully")
    print("⚡ Connected to Upstash Redis REST Database")
    print("⏱️ Max Timeout: 35 Minutes | SSE Streaming Active")
    print("=" * 45)

    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"[Webhook Removal]: {e}")

    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"[Polling Error]: {e}")
            time.sleep(5)
