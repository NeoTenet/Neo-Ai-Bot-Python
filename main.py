# -*- coding: utf-8 -*-
"""
Telegram AI Bot - Python + Upstash Redis (100% Safe, Bilingual & Instant)
Configured for: Wispbyte / bot-hosting.net (Docker / Linux Environment)
Architecture:
1. 💬 Q&A & Chat Mode (Pure conversational assistant)
2. 💻 Coding & Dev Mode (Software engineering with clean source file delivery)
3. 🎨 Image Generation Studio (Strict image prompts only)
Features:
- Instantaneous /start response (< 0.2s) with zero blocking database latency
- 100% Airtight Sponsor Join Verification (No bypass on verify click)
- Clean RTL Channel Link Generator (Auto sanitizes t.me, @ and full URLs)
- Native Bilingual UI: Full Persian (🇮🇷) & English (🇬🇧) Support
- Three 100% Independent & Isolated Operational Modes
- Auto-Routing Safety Guard: Coding requests NEVER trigger image generators
- Full Backup Suite: One-click JSON Chat Export + Direct JSON Restore Engine
- Smart Cache Cleaner: Purges temporary states/files without touching user data
- Ultra-Low CPU Engine: In-memory cancel tracking, smart activity throttling & precompiled regex
- Strict Thought Filter: Strips <think> and internal monologues completely
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
# ⚡ کش‌های سراسری درون‌حافظه‌ای جهت سرعت آنی و حداقل مصرف CPU
# ==========================================
_KNOWN_USERS_CACHE = set()
_LAST_ACTIVE_CACHE = {}
_CANCEL_REQS = set()

# کش‌های سرعت بالا برای پاسخ آنی
_BOT_STATUS_CACHE = None
_BOT_STATUS_TIME = 0
_SPONSORS_CACHE = None
_SPONSORS_CACHE_TIME = 0
_USER_MODES_CACHE = {}
_USER_LANG_CACHE = {}

# پیش‌کامپایل عبارات باقاعده
_THINK_TAG_REGEX = re.compile(r'<think>[\s\S]*?</think>', flags=re.IGNORECASE)
_CODE_BLOCK_REGEX = re.compile(r'```([a-zA-Z0-9_+-]*)[^\n]*\r?\n([\s\S]*?)```')
_ROBOT_PREFIX_REGEX = re.compile(r'^(ربات|روبات|بات)[\s:,،\n]+(.*)$', flags=re.IGNORECASE | re.DOTALL)
_CLEAN_WORDS_REGEX = re.compile(r'[^\w\s]')

# ==========================================
# 🌐 سیستم دو زبانه (فارسی و انگلیسی)
# ==========================================
I18N = {
    "fa": {
        "welcome": "🚀 **به ربات هوش مصنوعی خوش آمدید!**\n\n🎯 **بخش فعال:** `{mode}`\n\nیکی از گزینه‌های زیر را برای فعالیت انتخاب کنید:",
        "mode_chat_name": "💬 پرسش و پاسخ و گفتگو",
        "mode_code_name": "💻 کدنویسی و توسعه نرم‌افزار",
        "mode_image_name": "🎨 استودیوی ساخت عکس",
        "btn_chat": "💬 پرسش و پاسخ",
        "btn_code": "💻 بخش کدنویسی",
        "btn_img": "🎨 ساخت عکس",
        "btn_models": "🤖 انتخاب مدل هوش مصنوعی",
        "btn_history": "📜 تاریخچه گفتگوها",
        "btn_support": "📞 پیام به پشتیبانی و ادمین",
        "btn_new_chat": "➕ شروع گفتگوی جدید",
        "btn_admin": "⚙️ پنل مدیریت ادمین",
        "btn_lang": "🌐 تغییر زبان / Language",
        "sponsor_warn": "⚠️ **برای استفاده از امکانات ربات، ابتدا باید در کانال‌(های) اسپانسر زیر عضو شوید:**",
        "sponsor_btn": "📢 عضویت در کانال ({ch})",
        "sponsor_check_btn": "✅ عضو شدم / بررسی",
        "sponsor_not_joined": "⚠️ شما هنوز در تمام کانال‌های اسپانسر عضو نشده‌اید!\nلطفاً ابتدا عضو شوید و سپس دکمه بررسی را بزنید.",
        "sponsor_verified": "✅ عضویت شما با موفقیت تایید شد!",
        "lang_select_title": "🌐 **لطفاً زبان مورد نظر خود را انتخاب کنید / Please select your language:**",
        "lang_changed": "✅ زبان ربات با موفقیت روی **فارسی** تنظیم شد.",
        "chat_mode_msg": "💬 **بخش «پرسش و پاسخ و گفتگو» فعال شد.**\nاکنون هر سوال علمی، عمومی، ترجمه یا متنی دارید بنویسید.",
        "code_mode_msg": "💻 **بخش «کدنویسی و توسعه نرم‌افزار» فعال شد.**\nزبان یا اسکریپت مورد نظرتان را اعلام کنید تا کد کامل همراه با فایل برایتان آماده شود.",
        "image_mode_msg": "🎨 **بخش «استودیو ساخت عکس» فعال شد.**\nتوصیف تصویری که می‌خواهید ساخته شود را بفرستید.",
        "cancel_btn": "❌ لغو عملیات",
        "req_canceled": "❌ عملیات با موفقیت لغو شد.",
        "new_chat_msg": "✨ چت جدید ایجاد شد! پیام خود را بفرستید."
    },
    "en": {
        "welcome": "🚀 **Welcome to the AI Bot!**\n\n🎯 **Active Mode:** `{mode}`\n\nChoose an option below to begin:",
        "mode_chat_name": "💬 Q&A and Chat",
        "mode_code_name": "💻 Coding & Software Dev",
        "mode_image_name": "🎨 Image Generation Studio",
        "btn_chat": "💬 Q&A & Chat",
        "btn_code": "💻 Coding & Dev",
        "btn_img": "🎨 Image Studio",
        "btn_models": "🤖 Select AI Model",
        "btn_history": "📜 Chat History",
        "btn_support": "📞 Contact Support",
        "btn_new_chat": "➕ New Chat",
        "btn_admin": "⚙️ Admin Panel",
        "btn_lang": "🌐 Language / زبان",
        "sponsor_warn": "⚠️ **Please join our sponsor channel(s) below to use the bot:**",
        "sponsor_btn": "📢 Join Channel ({ch})",
        "sponsor_check_btn": "✅ Joined / Verify",
        "sponsor_not_joined": "⚠️ You have not joined all sponsor channels yet!\nPlease join and click verify again.",
        "sponsor_verified": "✅ Membership verified successfully!",
        "lang_select_title": "🌐 **Please select your language / لطفاً زبان مورد نظر را انتخاب کنید:**",
        "lang_changed": "✅ Language successfully set to **English**.",
        "chat_mode_msg": "💬 **Q&A & Chat mode activated.**\nYou can now ask questions, translate text, or converse.",
        "code_mode_msg": "💻 **Coding & Software Dev mode activated.**\nDescribe what you need, and code files will be prepared.",
        "image_mode_msg": "🎨 **Image Generation Studio activated.**\nSend the description of the image you want to generate.",
        "cancel_btn": "❌ Cancel",
        "req_canceled": "❌ Operation canceled successfully.",
        "new_chat_msg": "✨ New chat started! Send your message."
    }
}

def get_user_lang(user_id):
    u_str = str(user_id)
    if u_str in _USER_LANG_CACHE:
        return _USER_LANG_CACHE[u_str]
    lang = safe_kv_get(f"USER_LANG_{u_str}") or "fa"
    if lang not in ["fa", "en"]:
        lang = "fa"
    _USER_LANG_CACHE[u_str] = lang
    return lang

def tr(user_id, key, **kwargs):
    lang = get_user_lang(user_id)
    text = I18N.get(lang, I18N["fa"]).get(key, I18N["fa"].get(key, ""))
    if kwargs:
        text = text.format(**kwargs)
    return text

# ==========================================
# 🎨 تزریق دکمه‌های رنگی تلگرام (Monkey-Patch)
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
# 📅 تقویم جلالی (هجری شمسی)
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
BOT_TOKEN = os.getenv("BOT_TOKEN", "Token")
ADMIN_ID = str(os.getenv("ADMIN_ID", "Admin Id"))

UPSTASH_URL = os.getenv("UPSTASH_URL", "Base url")
UPSTASH_TOKEN = os.getenv("UPSTASH_TOKEN", "Token datebase")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# ==========================================
# 🌐 تنظیم سوکت شبکه با پکت‌های زنده نگه‌دارنده
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
        res = http_session.post(UPSTASH_URL, headers=headers, json=cmd, timeout=10)
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
# ⚡ کش‌های وضعیت سراسری ربات و اسپانسرها
# ==========================================
def is_bot_globally_active():
    global _BOT_STATUS_CACHE, _BOT_STATUS_TIME
    now = time.time()
    if _BOT_STATUS_CACHE is not None and (now - _BOT_STATUS_TIME) < 20:
        return _BOT_STATUS_CACHE
    res = safe_kv_get("BOT_GLOBAL_STATUS") != "off"
    _BOT_STATUS_CACHE = res
    _BOT_STATUS_TIME = now
    return res

def clean_channel_username(raw_ch):
    """پاکسازی هر نوع فرمت لینک و تبدیل آن به یوزرنیم خالص بدون خطای راست‌چین"""
    if not raw_ch:
        return ""
    clean = str(raw_ch).strip()
    clean = re.sub(r'^(https?://)?(www\.)?(t\.me/|telegram\.me/)', '', clean, flags=re.IGNORECASE)
    clean = clean.lstrip('@').strip().rstrip('/')
    return clean

def get_sponsor_channels_cached():
    global _SPONSORS_CACHE, _SPONSORS_CACHE_TIME
    now = time.time()
    if _SPONSORS_CACHE is not None and (now - _SPONSORS_CACHE_TIME) < 60:
        return _SPONSORS_CACHE
    channels_raw = safe_kv_get("SPONSOR_CHANNELS")
    channels = []
    if channels_raw:
        try:
            parsed = json.loads(channels_raw)
            channels = [clean_channel_username(c) for c in parsed if clean_channel_username(c)]
        except Exception:
            clean = clean_channel_username(channels_raw)
            if clean:
                channels = [clean]
    _SPONSORS_CACHE = channels
    _SPONSORS_CACHE_TIME = now
    return channels

# ==========================================
# 🧠 تشخیص هوشمند احوالپرسی و قصد کاربر
# ==========================================
def is_casual_greeting(text):
    if not text:
        return False
    clean = _CLEAN_WORDS_REGEX.sub('', text).strip().lower()
    greetings = {
        'سلام', 'سلان', 'درود', 'خوبی', 'چطوری', 'سلام عشقم', 'سلان عشقم', 
        'سلام داداش', 'سلام رفیق', 'سلام علیکم', 'چطوری عشقم', 'خوبی عشقم', 
        'صبح بخیر', 'شب بخیر', 'عصر بخیر', 'سلام خوبی', 'سلان خوبی', 'hi', 'hello', 'hey'
    }
    return clean in greetings or any(clean.startswith(g + " ") for g in ['سلام', 'سلان', 'درود'])

def is_coding_intent(text):
    if not text:
        return False
    lower = text.lower()
    coding_keywords = [
        'کد', 'برنامه', 'اسکریپت', 'بنویس', 'پایتون', 'جاوا', 'html', 'css', 'sql', 'خطا',
        'ارور', 'باگ', 'دیباگ', 'تابع', 'کلاس', 'کامپایل', 'الگوریتم', 'ریکوئست', 'api',
        'function', 'class', 'def ', 'import ', 'var ', 'const ', 'code', 'script', 'bug', 'developer'
    ]
    return any(k in lower for k in coding_keywords)

def detect_image_intent(text):
    if not text:
        return False, ""
    clean = text.strip()
    lower = clean.lower()

    explicit_prefixes = ["/image", "/draw", "/img", "/photo", "عکس:", "تصویر:"]
    for ep in explicit_prefixes:
        if lower.startswith(ep):
            return True, clean[len(ep):].strip()

    en_triggers = ["draw ", "generate image", "create image", "create photo", "create picture"]
    for et in en_triggers:
        if et in lower:
            prompt = re.sub(r'^(?:please\s+)?(?:make|draw|paint|generate|create)\s+(?:a|an|the)?\s*(?:image|photo|picture)?\s*(?:of)?\s*', '', clean, flags=re.IGNORECASE)
            return True, prompt.strip() or clean

    if is_coding_intent(clean) or any(g in lower for g in ['توضیح', 'چیست', 'کیست', 'چرا', 'چطور', 'چگونه', 'ترجمه', 'متن', 'مقاله', 'سلام']):
        return False, clean

    has_visual_noun = any(n in clean for n in ["عکس", "تصویر", "نقاشی", "والپیپر"])
    has_visual_verb = any(v in clean for v in ["بکش", "نقاشی کن", "تصویرسازی کن", "طراحی کن", "تولید کن", "بساز"])

    if has_visual_noun and has_visual_verb:
        prompt = re.sub(r'(?:لطفاً|لطفا|بی زحمت|برام|برای من|یه|یک)\s+', '', clean)
        prompt = re.sub(r'(?:عکس|تصویر|نقاشی)\s+(?:از|بکش\s+از|بساز\s+از|تولید\s+کن\s+از)?\s*', '', prompt)
        prompt = re.sub(r'\s+(?:عکس|تصویر|نقاشی)?\s*(?:بساز|بکش|طراحی کن|نقاشی کن|تولید کن)$', '', prompt)
        return True, prompt.strip() or clean

    return False, clean

# ==========================================
# ⚡ توابع امن و کم‌مصرف مدیریت کاربران
# ==========================================
def get_all_bot_users():
    set_users = upstash_command(["SMEMBERS", "BOT_USERS_SET"]) or []
    old_users = []
    old_raw = safe_kv_get("BOT_USERS")
    if old_raw:
        try:
            old_users = json.loads(old_raw)
        except Exception:
            pass
    all_u = list(set([str(u) for u in (set_users + old_users) if str(u).strip()]))
    _KNOWN_USERS_CACHE.update(all_u)
    return all_u

def track_user_activity(user_id):
    now = time.time()
    u_str = str(user_id)
    need_sadd = u_str not in _KNOWN_USERS_CACHE
    need_active = (now - _LAST_ACTIVE_CACHE.get(u_str, 0)) > 120

    if not need_sadd and not need_active:
        return

    def _worker():
        try:
            if need_sadd:
                upstash_command(["SADD", "BOT_USERS_SET", u_str])
                _KNOWN_USERS_CACHE.add(u_str)
            if need_active:
                safe_kv_put(f"LAST_ACTIVE_{u_str}", str(int(now * 1000)))
                _LAST_ACTIVE_CACHE[u_str] = now
        except Exception as e:
            print(f"[Track User Error]: {e}")

    threading.Thread(target=_worker, daemon=True).start()

def clear_user_state(user_id):
    """پاکسازی فوری تمام متغیرها در یک دستور تکی ردیس"""
    keys = [
        f"ADMIN_STEP_{user_id}", f"TEMP_MODEL_{user_id}",
        f"TEMP_IMG_{user_id}", f"ADMIN_EDIT_IDX_{user_id}",
        f"ADMIN_EDIT_IMG_IDX_{user_id}", f"USER_SUPPORT_STEP_{user_id}",
        f"AWAITING_IMG_{user_id}", f"USER_MODE_{user_id}"
    ]
    upstash_command(["DEL"] + keys)

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
    """بررسی زنده و تضمینی عضویت در کانال‌های اسپانسر بدون امکان دور زدن"""
    if str(user_id) == str(ADMIN_ID):
        return True, []
        
    channels = get_sponsor_channels_cached()
    if not channels:
        return True, []

    unjoined = []
    for ch in channels:
        clean_ch = clean_channel_username(ch)
        if not clean_ch:
            continue
        formatted_ch = f"@{clean_ch}"
        try:
            member = bot.get_chat_member(formatted_ch, int(user_id))
            if member.status not in ["creator", "administrator", "member"]:
                unjoined.append(clean_ch)
        except Exception:
            unjoined.append(clean_ch)

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
# 📁 سیستم استخراج امن کدهای طولانی
# ==========================================
def process_code_and_text(raw_text):
    matches = _CODE_BLOCK_REGEX.findall(raw_text)
    code_files = []

    ext_map = {
        'python': 'py', 'py': 'py', 'javascript': 'js', 'js': 'js',
        'typescript': 'ts', 'ts': 'ts', 'html': 'html', 'css': 'css',
        'cpp': 'cpp', 'c++': 'cpp', 'c': 'c', 'java': 'java', 'kotlin': 'kt',
        'php': 'php', 'sql': 'sql', 'json': 'json', 'xml': 'xml',
        'bash': 'sh', 'sh': 'sh', 'shell': 'sh', 'go': 'go', 'golang': 'go',
        'rust': 'rs', 'rs': 'rs', 'csharp': 'cs', 'cs': 'cs'
    }

    if matches:
        for idx, (lang, code_content) in enumerate(matches, 1):
            clean_code = code_content.strip()
            if len(clean_code) < 100 and clean_code.count('\n') < 5:
                continue

            lang_clean = lang.strip().lower()
            ext = ext_map.get(lang_clean, 'txt')
            if ext == 'py':
                filename = "main.py" if idx == 1 else f"script_{idx}.py"
            elif ext == 'js':
                filename = "app.js" if idx == 1 else f"script_{idx}.js"
            elif ext == 'html':
                filename = "index.html" if idx == 1 else f"page_{idx}.html"
            else:
                filename = f"code_{idx}.{ext}" if len(matches) > 1 else f"code.{ext}"

            code_files.append((filename, clean_code.encode('utf-8'), ext))

    return raw_text, code_files

def send_code_document_safe(chat_id, byte_data, filename, ext, reply_to_id=None, thread_id=None):
    caption = f"📁 سورس کد آماده دانلود ({ext.upper()}): {filename}"

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
    except Exception as e:
        print(f"[Document Send Error]: {e}")
        return False

# ==========================================
# ۱. رابط کاربری ۳ حالته و تفکیک‌شده دو زبانه
# ==========================================
def get_user_current_mode(target_key_id):
    if target_key_id in _USER_MODES_CACHE:
        return _USER_MODES_CACHE[target_key_id]
    mode = safe_kv_get(f"BOT_MODE_{target_key_id}")
    if mode not in ["CHAT", "CODE", "IMAGE"]:
        mode = "CHAT"
    _USER_MODES_CACHE[target_key_id] = mode
    return mode

def get_main_menu_markup(user_id, current_mode="CHAT"):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    chat_lbl = f"✅ {tr(user_id, 'btn_chat')}" if current_mode == "CHAT" else tr(user_id, 'btn_chat')
    code_lbl = f"✅ {tr(user_id, 'btn_code')}" if current_mode == "CODE" else tr(user_id, 'btn_code')
    img_lbl  = f"✅ {tr(user_id, 'btn_img')}" if current_mode == "IMAGE" else tr(user_id, 'btn_img')
    
    markup.add(
        types.InlineKeyboardButton(chat_lbl, callback_data="switch_mode_chat", style="primary"),
        types.InlineKeyboardButton(code_lbl, callback_data="switch_mode_code", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton(img_lbl, callback_data="switch_mode_image", style="success")
    )
    markup.add(
        types.InlineKeyboardButton(tr(user_id, 'btn_models'), callback_data="models_hub"),
        types.InlineKeyboardButton(tr(user_id, 'btn_history'), callback_data="history_menu")
    )
    markup.add(
        types.InlineKeyboardButton(tr(user_id, 'btn_support'), callback_data="contact_admin", style="primary"),
        types.InlineKeyboardButton(tr(user_id, 'btn_lang'), callback_data="open_lang_menu")
    )
    row_last = [types.InlineKeyboardButton(tr(user_id, 'btn_new_chat'), callback_data="new_chat", style="success")]
    if str(user_id) == str(ADMIN_ID):
        row_last.append(types.InlineKeyboardButton(tr(user_id, 'btn_admin'), callback_data="admin_panel", style="primary"))
    markup.add(*row_last)
    return markup

def send_main_menu(chat_id, user_id):
    current_mode = get_user_current_mode(user_id)
    mode_key_map = {"CHAT": "mode_chat_name", "CODE": "mode_code_name", "IMAGE": "mode_image_name"}
    mode_text = tr(user_id, mode_key_map.get(current_mode, "mode_chat_name"))
    welcome_text = tr(user_id, "welcome", mode=mode_text)
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=get_main_menu_markup(user_id, current_mode))

def send_lang_selection_menu(chat_id, user_id, message_id=None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_lang_fa", style="primary"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en", style="primary")
    )
    markup.add(types.InlineKeyboardButton("🔙 بازگشت / Back", callback_data="main_menu"))
    text = tr(user_id, "lang_select_title")
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def build_sponsor_markup(user_id, unjoined_channels):
    """ساخت کیبورد شیشه‌ای کانال‌های اسپانسر با لینک مستقیم و چیدمان بدون ایراد RTL"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in unjoined_channels:
        clean_ch = clean_channel_username(ch)
        btn_label = tr(user_id, "sponsor_btn", ch=clean_ch)
        btn_url = f"https://t.me/{clean_ch}"
        markup.add(types.InlineKeyboardButton(btn_label, url=btn_url))
    markup.add(types.InlineKeyboardButton(tr(user_id, "sponsor_check_btn"), callback_data="check_sponsor", style="success"))
    return markup

def send_history_menu(chat_id, user_id, message_id=None):
    sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
    active_sess = safe_kv_get(f"ACTIVE_SESSION_{user_id}")

    if not sessions:
        empty_text = "📜 هیچ تاریخچه گفتگویی در حافظه یافت نشد." if get_user_lang(user_id) == "fa" else "📜 No chat history found."
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
        types.InlineKeyboardButton("➕ ایجاد چت جدید" if get_user_lang(user_id) == "fa" else "➕ New Chat", callback_data="new_chat", style="success"),
        types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی" if get_user_lang(user_id) == "fa" else "🔙 Main Menu", callback_data="main_menu")
    )

    text = "📜 **لیست گفتگوهای ذخیره‌شده شما:**\nبرای انتخاب روی متن چت و برای حذف تکی روی دکمه سطل زباله (🗑) کلیک کنید:" if get_user_lang(user_id) == "fa" else "📜 **Your Saved Conversations:**"
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
        "✨ **منوی جامع انتخاب مدل‌های هوش مصنوعی**\n\n"
        f"💬 مدل فعال چت و کدنویسی: **{chat_name}**\n"
        f"🎨 مدل فعال ساخت عکس: **{img_name}**\n\n"
        "بخش مورد نظر را برای تغییر مدل انتخاب کنید:"
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
    is_active = is_bot_globally_active()
    power_btn_text = "🔴 خاموش کردن کل ربات" if is_active else "🟢 روشن کردن کل ربات"
    power_callback = "admin_toggle_off" if is_active else "admin_toggle_on"
    power_style = "danger" if is_active else "success"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(power_btn_text, callback_data=power_callback, style=power_style),
        types.InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_stats", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("💾 خروجی بکاپ چت‌ها", callback_data="admin_backup_chats", style="success"),
        types.InlineKeyboardButton("📥 بازگردانی بکاپ", callback_data="admin_restore_chats", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast", style="primary"),
        types.InlineKeyboardButton("🧹 پاکسازی کش موقت", callback_data="admin_clean_cache", style="danger")
    )
    markup.add(
        types.InlineKeyboardButton("🟡 لیست مدل‌ها", callback_data="admin_list_models", style="primary"),
        types.InlineKeyboardButton("✏️ ویرایش مدل‌ها", callback_data="admin_edit_models_menu", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("➕ افزودن مدل چت", callback_data="admin_add_model", style="success"),
        types.InlineKeyboardButton("🎨 افزودن مدل عکس", callback_data="admin_add_img_model", style="success")
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

    status_str = "🟢 روشن و فعال" if is_bot_globally_active() else "🔴 خاموش (متوقف)"
    text = (
        f"📊 **آمار جامع کاربران و وضعیت ربات:**\n\n"
        f"⚡ وضعیت ربات: **{status_str}**\n"
        f"👥 کل کاربران ثبت‌نامی در حافظه: **{total_users}**\n"
        f"🟢 کاربران فعال در ۲۴ ساعت اخیر: **{active_count}**"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin_panel", style="primary"))
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def export_all_chats_backup(admin_chat_id):
    status_msg = bot.send_message(admin_chat_id, "⏳ در حال ساخت فایل پشتیبان از تمام گفتگوها...")
    try:
        users = get_all_bot_users()
        backup_data = {
            "backup_date": get_jalali_date(),
            "timestamp": int(time.time()),
            "total_users": len(users),
            "users_chats": {}
        }

        for u in users:
            sessions = json.loads(safe_kv_get(f"SESSIONS_{u}") or "[]")
            user_sessions_data = []
            for s in sessions:
                sid = s.get("id")
                if sid:
                    hist = json.loads(safe_kv_get(f"HISTORY_{u}_{sid}") or "[]")
                    user_sessions_data.append({
                        "session_id": sid,
                        "title": s.get("title"),
                        "date": s.get("date"),
                        "messages": hist
                    })
            if user_sessions_data:
                backup_data["users_chats"][str(u)] = user_sessions_data

        json_bytes = json.dumps(backup_data, ensure_ascii=False, indent=2).encode('utf-8')
        bio = io.BytesIO(json_bytes)
        bio.name = f"chats_backup_{get_jalali_date().replace('/', '-')}.json"
        bio.seek(0)

        caption = (
            f"💾 **فایل پشتیبان کامل چت‌های ربات**\n\n"
            f"📅 تاریخ: `{get_jalali_date()}`\n"
            f"👥 تعداد کاربران: `{len(users)}`\n"
            f"📦 حجم فایل: `{len(json_bytes) / 1024:.1f} KB`"
        )
        bot.delete_message(admin_chat_id, status_msg.message_id)
        bot.send_document(admin_chat_id, bio, caption=caption, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ خطا در ایجاد فایل بکاپ: {e}", chat_id=admin_chat_id, message_id=status_msg.message_id)

def clean_system_cache(admin_chat_id):
    users = get_all_bot_users()
    cleaned_count = 0
    for u in users:
        for k in [f"ADMIN_STEP_{u}", f"TEMP_MODEL_{u}", f"TEMP_IMG_{u}", f"USER_SUPPORT_STEP_{u}", f"AWAITING_IMG_{u}", f"USER_MODE_{u}"]:
            if safe_kv_get(k):
                safe_kv_delete(k)
                cleaned_count += 1

    report = (
        "🧹 **عملیات پاکسازی کش موقت با موفقیت انجام شد!**\n\n"
        f"🔹 موارد کش و استیت‌های منقضی‌شده پاک شدند: **{cleaned_count}**\n"
        "🔒 **اطلاعات چت‌ها و کاربران دست‌نخورده باقی ماند.**"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin_panel", style="primary"))
    bot.send_message(admin_chat_id, report, parse_mode="Markdown", reply_markup=markup)

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
            time.sleep(0.04)
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
    channels = get_sponsor_channels_cached()
    list_text = "📢 هیچ کانال اسپانسری ثبت نشده است." if not channels else "📢 **لیست کانال‌های اسپانسری:**"
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for idx, ch in enumerate(channels):
        markup.add(types.InlineKeyboardButton(f"🗑 {ch}", callback_data=f"del_sponsor_{idx}", style="danger"))

    markup.add(types.InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin_panel"))
    if message_id:
        try:
            bot.edit_message_text(list_text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, list_text, reply_markup=markup)

# ==========================================
# ۳. پردازش چت و کدنویسی
# ==========================================
def worker_ai_process(chat_id, user_id, message, text_prompt, target_key_id, is_group, target_reply_id, thread_id=None, active_mode="CHAT"):
    models = json.loads(safe_kv_get("AI_MODELS") or "[]")
    active_session_id = get_or_create_active_session(user_id)
    lang = get_user_lang(user_id)

    user_selected = safe_kv_get(f"USER_MODEL_{target_key_id}") or safe_kv_get(f"USER_MODEL_{user_id}") or "0"
    try:
        model_idx = int(user_selected)
    except:
        model_idx = 0

    if not models or model_idx >= len(models):
        bot.send_message(chat_id, "⚠️ ابتدا یک مدل چت در ربات ثبت کنید." if lang == "fa" else "⚠️ Please add a chat model first.", message_thread_id=thread_id)
        return

    active_model = models[model_idx]
    if not text_prompt:
        text_prompt = "سلام" if lang == "fa" else "Hello"
        
    is_greeting = is_casual_greeting(text_prompt)

    req_id = f"{user_id}_{int(time.time()*1000)}"
    cancel_markup = types.InlineKeyboardMarkup()
    cancel_markup.add(types.InlineKeyboardButton(tr(user_id, "cancel_btn"), callback_data=f"cancel_req_{req_id}", style="danger"))

    reply_to = target_reply_id if target_reply_id else (message.message_id if is_group else None)
    mode_icon = "💻" if active_mode == "CODE" else "💬"
    initial_text = f"{mode_icon} در حال پردازش با {active_model.get('name')}... ⏱️ 00:00" if lang == "fa" else f"{mode_icon} Processing with {active_model.get('name')}... ⏱️ 00:00"

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
            time.sleep(1.2)
            if is_done or (req_id in _CANCEL_REQS):
                break

            now = time.time()
            elapsed = int(now - start_time)
            if elapsed >= 2100:
                break

            if now - last_edit_time >= 2.4:
                mins = elapsed // 60
                secs = elapsed % 60
                time_display = f"{mins:02d}:{secs:02d}"

                cur_txt = f"{mode_icon} در حال پردازش با {active_model.get('name')}... ⏱️ {time_display}" if lang == "fa" else f"{mode_icon} Processing with {active_model.get('name')}... ⏱️ {time_display}"
                try:
                    bot.edit_message_text(cur_txt, chat_id=chat_id, message_id=status_msg_id, reply_markup=cancel_markup)
                    last_edit_time = now
                except ApiTelegramException as te:
                    if te.error_code == 429:
                        wait_time = te.result_json.get('parameters', {}).get('retry_after', 3)
                        last_edit_time = now + wait_time
                except Exception:
                    pass

    threading.Thread(target=timer_loop, daemon=True).start()

    try:
        history = json.loads(safe_kv_get(f"HISTORY_{user_id}_{active_session_id}") or "[]")
        user_content = text_prompt

        if message.photo:
            if not active_model.get("supportsVision"):
                is_done = True
                bot.edit_message_text("❌ این مدل از تحلیل عکس پشتیبانی نمی‌کند." if lang == "fa" else "❌ This model does not support Vision.", chat_id=chat_id, message_id=status_msg_id)
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
                    txt_part = next((p.get("text") for p in item["content"] if p.get("type") == "text"), "image")
                    cleaned_messages.append({"role": item["role"], "content": f"[Image: {txt_part}]"})
                else:
                    cleaned_messages.append(item)

            while cleaned_messages and cleaned_messages[0].get("role") == "assistant":
                cleaned_messages.pop(0)

            if len(cleaned_messages) > 6:
                cleaned_messages = cleaned_messages[-6:]
                if cleaned_messages and cleaned_messages[0].get("role") == "assistant":
                    cleaned_messages.pop(0)

        base_url = active_model.get("baseUrl", "").strip().rstrip("/")
        endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"

        target_lang_str = "Persian (Farsi)" if lang == "fa" else "English"
        if active_mode == "CODE":
            system_prompt_content = (
                f"You are {active_model.get('name')}, an expert senior software engineer. "
                f"CRITICAL INSTRUCTIONS:\n"
                f"1. Focus strictly on programming, architecture, debugging, and clean code generation.\n"
                f"2. Provide explanations in natural {target_lang_str}, followed by complete, working code in proper markdown codeblocks.\n"
                f"3. NEVER output internal monologue, notes, or <think> tags."
            )
        else:
            system_prompt_content = (
                f"You are {active_model.get('name')}, an intelligent and friendly AI assistant. "
                f"CRITICAL INSTRUCTIONS:\n"
                f"1. Answer questions, chat, explain, and converse clearly in natural {target_lang_str}.\n"
                f"2. NEVER output internal monologue, notes, or <think> tags."
            )

        system_prompt = {"role": "system", "content": system_prompt_content}

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
                    if req_id in _CANCEL_REQS:
                        break
                    if not raw_line:
                        continue
                    
                    line = raw_line.decode('utf-8', errors='replace') if isinstance(raw_line, bytes) else raw_line

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

                clean_c = _THINK_TAG_REGEX.sub('', full_content).strip()
                if clean_c:
                    api_response_text = clean_c
                elif full_content.strip():
                    api_response_text = full_content.strip()
                else:
                    api_response_text = _THINK_TAG_REGEX.sub('', full_reasoning).strip()
            else:
                try:
                    data = res.json()
                except Exception:
                    data = json.loads(res.content.decode('utf-8', errors='replace'))
                
                msg_obj = data.get("choices", [{}])[0].get("message", {})
                c = msg_obj.get("content", "")
                r = msg_obj.get("reasoning_content", "")
                
                clean_c = _THINK_TAG_REGEX.sub('', c).strip()
                api_response_text = clean_c if clean_c else (c if c.strip() else r)
        else:
            api_response_text = f"❌ API Error ({res.status_code}):\n{res.text[:250]}"

        if api_response_text:
            api_response_text = _THINK_TAG_REGEX.sub('', api_response_text).strip()

        if api_response_text and not api_response_text.startswith("❌"):
            clean_text, code_files = process_code_and_text(api_response_text)

            history.append({"role": "assistant", "content": clean_text[:800]})
            hist_to_save = []
            for item in history[-6:]:
                if isinstance(item.get("content"), list):
                    txt_part = next((p.get("text") for p in item["content"] if p.get("type") == "text"), "image")
                    hist_to_save.append({"role": item["role"], "content": txt_part})
                else:
                    hist_to_save.append(item)

            safe_kv_put(f"HISTORY_{user_id}_{active_session_id}", hist_to_save)
            update_session_title_if_new(user_id, active_session_id, text_prompt)

    except requests.exceptions.Timeout:
        api_response_text = "❌ زمان پاسخ بیش از ۳۵ دقیقه شد و قطع گردید." if lang == "fa" else "❌ Request timed out."
    except requests.exceptions.ConnectionError:
        api_response_text = "❌ خطای قطع ارتباط با سرور هوش مصنوعی." if lang == "fa" else "❌ Connection error with AI server."
    except Exception as e:
        api_response_text = f"❌ Error: {type(e).__name__} - {str(e)[:100]}"
    finally:
        is_done = True
        _CANCEL_REQS.discard(req_id)
        safe_kv_delete(f"CANCEL_{req_id}")

    if api_response_text and not api_response_text.startswith("❌"):
        if is_group:
            sender_name = f"@{message.from_user.username}" if message.from_user.username else (message.from_user.first_name or "User")
            final_text = f"👤 **User:** {sender_name} | {mode_icon} **Model:** {active_model.get('name')}\n\n{clean_text}"
        else:
            final_text = clean_text

        send_safe_ai_response(chat_id, status_msg_id, final_text, reply_to, thread_id)
        
        if active_mode == "CODE":
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
        if req_id not in _CANCEL_REQS and safe_kv_get(f"CANCEL_{req_id}") != "true":
            try:
                bot.edit_message_text(api_response_text or "❌ Empty response.", chat_id=chat_id, message_id=status_msg_id)
            except Exception:
                pass

# ==========================================
# ۴. پردازش ساخت عکس (استودیوی مستقل تصویرسازی)
# ==========================================
def worker_image_process(chat_id, user_id, prompt_text, target_key_id, thread_id=None):
    img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
    img_idx_str = safe_kv_get(f"USER_IMG_MODEL_{target_key_id}") or safe_kv_get(f"USER_IMG_MODEL_{user_id}") or "0"
    lang = get_user_lang(user_id)
    try:
        img_idx = int(img_idx_str)
    except:
        img_idx = 0

    if not img_models or img_idx >= len(img_models):
        bot.send_message(chat_id, "⚠️ هیچ مدل تصویرسازی تعریف نشده است." if lang == "fa" else "⚠️ No image models defined.", message_thread_id=thread_id)
        return

    active_img_model = img_models[img_idx]

    req_id = f"{user_id}_img_{int(time.time()*1000)}"
    cancel_markup = types.InlineKeyboardMarkup()
    cancel_markup.add(types.InlineKeyboardButton(tr(user_id, "cancel_btn"), callback_data=f"cancel_req_{req_id}", style="danger"))

    loading_msg = f"🎨 در حال ساخت تصویر با {active_img_model.get('name')}... ⏱️ 00:00" if lang == "fa" else f"🎨 Generating image with {active_img_model.get('name')}... ⏱️ 00:00"
    status_msg = bot.send_message(
        chat_id,
        loading_msg,
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
            time.sleep(1.2)
            if is_done or (req_id in _CANCEL_REQS):
                break

            now = time.time()
            elapsed = int(now - start_time)
            if elapsed >= 2100:
                break

            if now - last_edit_time >= 2.4:
                mins = elapsed // 60
                secs = elapsed % 60
                time_display = f"{mins:02d}:{secs:02d}"
                cur_text = f"🎨 در حال ساخت تصویر با {active_img_model.get('name')}... ⏱️ {time_display}" if lang == "fa" else f"🎨 Generating image with {active_img_model.get('name')}... ⏱️ {time_display}"
                try:
                    bot.edit_message_text(
                        cur_text,
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
            headers = {"Authorization": f"Bearer {api_key}", "Accept": "image/*"}
            res = http_session.post(
                base_url,
                headers=headers,
                files={"none": ''},
                data={"prompt": prompt_text, "output_format": "webp"},
                timeout=(60, 2100)
            )
            if req_id in _CANCEL_REQS:
                return
            if res.status_code == 200:
                image_data = res.content
            else:
                error_msg = f"Code: {res.status_code}\n{res.text[:200]}"

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
            payload = {"model": model_name, "prompt": prompt_text, "n": 1, "size": "1024x1024"}
            res = http_session.post(endpoint, headers=headers, json=payload, timeout=(60, 2100))
            if req_id in _CANCEL_REQS:
                return
            if res.status_code == 200:
                data = res.json()
                if "data" in data and len(data["data"]) > 0:
                    image_data = data["data"][0].get("url")
            else:
                error_msg = f"Code: {res.status_code}\n{res.text[:200]}"

    except Exception as e:
        error_msg = str(e)
    finally:
        is_done = True

    if req_id in _CANCEL_REQS:
        _CANCEL_REQS.discard(req_id)
        safe_kv_delete(f"CANCEL_{req_id}")
        try:
            bot.edit_message_text("❌ ساخت تصویر لغو شد." if lang == "fa" else "❌ Image generation canceled.", chat_id=chat_id, message_id=status_msg_id)
        except Exception:
            pass
        return

    _CANCEL_REQS.discard(req_id)
    safe_kv_delete(f"CANCEL_{req_id}")

    if image_data:
        try:
            bot.delete_message(chat_id, status_msg_id)
        except Exception:
            pass
        caption = f"✨ **Image generated with {active_img_model.get('name')}**\n\n📝 **Prompt:** {prompt_text}" if lang == "en" else f"✨ **تصویر تولید شده با {active_img_model.get('name')}**\n\n📝 **پرامپت:** {prompt_text}"
        try:
            bot.send_photo(chat_id, image_data, caption=caption, parse_mode="Markdown", message_thread_id=thread_id)
        except Exception:
            bot.send_photo(chat_id, image_data, caption=caption, message_thread_id=thread_id)
    else:
        try:
            bot.edit_message_text(f"❌ ساخت تصویر با خطا مواجه شد.\n{error_msg or ''}" if lang == "fa" else f"❌ Image generation failed.\n{error_msg or ''}", chat_id=chat_id, message_id=status_msg_id)
        except Exception:
            pass

# ==========================================
# ⚡ هندلر اختصاصی دستور /start (پاسخ‌دهی آنی زیر ۰.۲ ثانیه)
# ==========================================
@bot.message_handler(commands=['start'])
def handle_start_command(msg):
    chat_id = msg.chat.id
    user_id = str(msg.from_user.id)
    is_group = msg.chat.type in ["group", "supergroup"]
    thread_id = getattr(msg, 'message_thread_id', None) if getattr(msg, 'is_topic_message', False) else None

    if not is_bot_globally_active() and user_id != ADMIN_ID:
        bot.send_message(
            chat_id,
            "⚠️ **ربات موقتاً توسط مدیریت خاموش و در دست به‌روزرسانی می‌باشد.**\nلطفاً ساعاتی دیگر مراجعه کنید. 🙏",
            parse_mode="Markdown",
            message_thread_id=thread_id
        )
        return

    track_user_activity(user_id)

    if is_group:
        if not is_group_admin(chat_id, user_id):
            return
        bot_info = bot.get_me()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🤖 ورود به پیوی ربات", url=f"https://t.me/{bot_info.username}?start=true", style="primary"))
        bot.reply_to(
            msg,
            "⚠️ **منوی تنظیمات فقط در پیوی ربات در دسترس است.**",
            parse_mode="Markdown",
            reply_markup=markup,
            allow_sending_without_reply=True
        )
        return

    # بررسی تضمینی عضویت در کانال‌های اسپانسر
    ok_sponsor, unjoined = check_sponsor_join(user_id)
    if not ok_sponsor and ADMIN_ID and user_id != ADMIN_ID:
        markup = build_sponsor_markup(user_id, unjoined)
        bot.send_message(chat_id, tr(user_id, "sponsor_warn"), parse_mode="Markdown", reply_markup=markup)
        return

    # پاکسازی وضعیت‌های موقت در پس‌زمینه
    threading.Thread(target=clear_user_state, args=(user_id,), daemon=True).start()
    
    # ارسال فوری منو
    send_main_menu(chat_id, user_id)

# ==========================================
# ۵. هندلر پیام‌ها و تفکیک صددرصدی ۳ حالت
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
    target_key_id = f"group_{chat_id}" if is_group else user_id

    if not is_bot_globally_active() and user_id != ADMIN_ID:
        bot.send_message(
            chat_id,
            "⚠️ **ربات موقتاً توسط مدیریت خاموش است.**",
            parse_mode="Markdown",
            message_thread_id=thread_id
        )
        return

    track_user_activity(user_id)

    # بازگردانی اطلاعات از فایل بکاپ توسط ادمین
    if not is_group and user_id == ADMIN_ID:
        admin_step = safe_kv_get(f"ADMIN_STEP_{user_id}")
        if admin_step == "AWAITING_BACKUP_FILE":
            if not msg.document or not msg.document.file_name.lower().endswith('.json'):
                bot.reply_to(msg, "❌ لطفاً فقط فایل بکاپ با پسوند `.json` ارسال نمایید.", parse_mode="Markdown")
                return

            clear_user_state(user_id)
            status_msg = bot.reply_to(msg, "⏳ در حال استخراج و بازگردانی اطلاعات از فایل پشتیبان...")
            try:
                f_info = bot.get_file(msg.document.file_id)
                f_bytes = bot.download_file(f_info.file_path)
                data = json.loads(f_bytes.decode('utf-8', errors='ignore'))

                users_chats = data.get("users_chats") or data.get("users") or {}
                if not isinstance(users_chats, dict) or not users_chats:
                    bot.edit_message_text("❌ ساختار فایل پشتیبان معتبر نیست یا داده‌ای در آن یافت نشد.", chat_id=chat_id, message_id=status_msg.message_id)
                    return

                restored_users = 0
                restored_sessions = 0

                for u_id, s_data in users_chats.items():
                    u_str = str(u_id)
                    upstash_command(["SADD", "BOT_USERS_SET", u_str])
                    _KNOWN_USERS_CACHE.add(u_str)

                    cur_sessions = json.loads(safe_kv_get(f"SESSIONS_{u_str}") or "[]")
                    existing_sids = {s.get("id") for s in cur_sessions if s.get("id")}

                    if isinstance(s_data, list):
                        for item in s_data:
                            sid = item.get("session_id") or item.get("id")
                            if not sid:
                                continue
                            if sid not in existing_sids:
                                cur_sessions.append({
                                    "id": sid,
                                    "title": item.get("title", "گفتگوی بازیابی‌شده"),
                                    "date": item.get("date", get_jalali_date())
                                })
                                existing_sids.add(sid)
                            msgs = item.get("messages", [])
                            if msgs:
                                safe_kv_put(f"HISTORY_{u_str}_{sid}", msgs)
                                restored_sessions += 1

                    safe_kv_put(f"SESSIONS_{u_str}", cur_sessions)
                    if cur_sessions and not safe_kv_get(f"ACTIVE_SESSION_{u_str}"):
                        safe_kv_put(f"ACTIVE_SESSION_{u_str}", cur_sessions[0]["id"])

                    restored_users += 1

                res_text = (
                    "✅ **اطلاعات با موفقیت بازگردانی شد!**\n\n"
                    f"👥 کاربران بازیابی‌شده: **{restored_users}**\n"
                    f"💬 گفتگوهای اضافه‌شده به دیتابیس: **{restored_sessions}**"
                )
                bot.edit_message_text(res_text, chat_id=chat_id, message_id=status_msg.message_id, parse_mode="Markdown")
            except Exception as e:
                bot.edit_message_text(f"❌ خطا در بازگردانی فایل: {e}", chat_id=chat_id, message_id=status_msg.message_id)
            return

    # خواندن فایل‌های متنی/کد ارسالی کاربر
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

    # پشتیبانی
    if not is_group and safe_kv_get(f"USER_SUPPORT_STEP_{user_id}") == "AWAITING_MSG":
        safe_kv_delete(f"USER_SUPPORT_STEP_{user_id}")
        sender_name = msg.from_user.first_name or "کاربر"
        sender_user = f"@{msg.from_user.username}" if msg.from_user.username else "بدون یوزرنیم"

        admin_notify = (
            f"📩 **پیام جدید به پشتیبانی:**\n\n"
            f"👤 **نام:** {sender_name}\n"
            f"🆔 **آیدی عددی:** `{user_id}`\n"
            f"🔗 **یوزرنیم:** {sender_user}\n\n"
            f"👇 پیام یا فایل:"
        )
        markup_reply = types.InlineKeyboardMarkup()
        markup_reply.add(types.InlineKeyboardButton("✍️ ارسال پاسخ", callback_data=f"admin_reply_{user_id}", style="primary"))
        
        try:
            bot.send_message(ADMIN_ID, admin_notify, parse_mode="Markdown")
            bot.copy_message(chat_id=ADMIN_ID, from_chat_id=chat_id, message_id=msg.message_id, reply_markup=markup_reply)
            bot.send_message(chat_id, "✅ پیام شما با موفقیت به پشتیبانی ارسال شد.")
        except Exception as e:
            bot.send_message(chat_id, f"❌ خطا در ارسال: {e}")
        return

    # پاسخ ادمین به کاربر
    if not is_group and user_id == ADMIN_ID:
        admin_step = safe_kv_get(f"ADMIN_STEP_{user_id}")
        if admin_step and admin_step.startswith("REPLY_TO_"):
            target_uid = admin_step.replace("REPLY_TO_", "")
            safe_kv_delete(f"ADMIN_STEP_{user_id}")
            try:
                bot.send_message(target_uid, "📩 **پاسخ پشتیبانی و مدیریت:**", parse_mode="Markdown")
                bot.copy_message(chat_id=target_uid, from_chat_id=chat_id, message_id=msg.message_id)
                bot.send_message(chat_id, f"✅ پاسخ شما برای کاربر `{target_uid}` ارسال گردید.", parse_mode="Markdown")
            except Exception as e:
                bot.send_message(chat_id, f"❌ خطا در ارسال: {e}")
            return

        if admin_step:
            if admin_step == "BROADCAST_MSG":
                clear_user_state(user_id)
                threading.Thread(target=broadcast_worker, args=(chat_id, msg.message_id), daemon=True).start()
                return
            else:
                handle_admin_steps(chat_id, user_id, text, admin_step)
                return

    # بررسی مجدد اسپانسر برای پیام‌های معمولی در پیوی
    if not is_group:
        ok_sponsor, unjoined = check_sponsor_join(user_id)
        if not ok_sponsor and ADMIN_ID and user_id != ADMIN_ID:
            markup = build_sponsor_markup(user_id, unjoined)
            bot.send_message(chat_id, tr(user_id, "sponsor_warn"), parse_mode="Markdown", reply_markup=markup)
            return

    if text.startswith("/models"):
        if is_group:
            if not is_group_admin(chat_id, user_id):
                bot.reply_to(msg, "⛔ تغییر مدل‌های ربات در گروه فقط توسط ادمین مجاز است.", allow_sending_without_reply=True)
                return
        elif ADMIN_ID and user_id != ADMIN_ID:
            bot.send_message(chat_id, "⛔ این دستور تنها برای ادمین ربات مجاز است.")
            return

        send_models_hub(chat_id, target_key_id, is_group)
        return

    target_reply_id = msg.message_id
    if is_group:
        bot_info = bot.get_me()
        bot_id = str(bot_info.id)
        lower_text = text.lower().strip()

        # ابزارهای مدیریتی ناظمی در گروه
        if is_group_admin(chat_id, user_id) and msg.reply_to_message:
            target_user = msg.reply_to_message.from_user
            target_uid = target_user.id
            target_name = target_user.first_name or "کاربر"

            if lower_text.startswith("سکوت") or lower_text.startswith("/mute"):
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
                    time_msg = f"به مدت **{minutes} دقیقه**" if minutes > 0 else "**دائم**"
                    bot.reply_to(msg, f"🔇 کاربر [{target_name}](tg://user?id={target_uid}) {time_msg} بی‌صدا شد.", parse_mode="Markdown")
                except Exception:
                    pass
                return

            elif lower_text in ["رفع سکوت", "ازاد", "آزاد", "/unmute"]:
                try:
                    bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=target_uid,
                        permissions=ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
                    )
                    bot.reply_to(msg, f"🔊 سکوت کاربر [{target_name}](tg://user?id={target_uid}) لغو شد.", parse_mode="Markdown")
                except Exception:
                    pass
                return

            elif lower_text in ["اخراج", "بن", "/ban"]:
                try:
                    bot.ban_chat_member(chat_id, target_uid)
                    bot.reply_to(msg, f"🚫 کاربر [{target_name}](tg://user?id={target_uid}) اخراج گردید.", parse_mode="Markdown")
                except Exception:
                    pass
                return

            elif lower_text in ["حذف", "پاک", "/del"]:
                try:
                    bot.delete_message(chat_id, msg.reply_to_message.message_id)
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
                return

        if safe_kv_get(f"GROUP_MUTED_{chat_id}") == "true":
            return

        is_reply_to_bot = msg.reply_to_message and str(msg.reply_to_message.from_user.id) == bot_id
        robot_match = _ROBOT_PREFIX_REGEX.match(text.strip())
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

    # ==============================================================
    # 🎯 تفکیک ۳ گانه و قطعی (پرسش و پاسخ | کدنویسی | ساخت عکس)
    # ==============================================================
    has_photo_attached = bool(msg.photo or (msg.reply_to_message and msg.reply_to_message.photo))
    active_mode = get_user_current_mode(target_key_id)
    
    # ۱. اولویت قطعی کدنویسی
    is_code = is_coding_intent(text)
    
    # ۲. قصد ساخت عکس
    is_img_prompt, clean_img_prompt = detect_image_intent(text) if not has_photo_attached else (False, text)

    # قانون ۱: اگر کدنویسی است، عکس اجرا نشود
    if is_code:
        _USER_MODES_CACHE[target_key_id] = "CODE"
        safe_kv_put(f"BOT_MODE_{target_key_id}", "CODE")
        threading.Thread(target=worker_ai_process, args=(chat_id, user_id, msg, text, target_key_id, is_group, target_reply_id, thread_id, "CODE"), daemon=True).start()
        return

    # قانون ۲: ساخت عکس تنها در صورت درخواست مستقیم یا حالت فعال عکس
    if (active_mode == "IMAGE" or is_img_prompt) and not has_photo_attached:
        img_prompt_to_use = clean_img_prompt if is_img_prompt else text
        threading.Thread(target=worker_image_process, args=(chat_id, user_id, img_prompt_to_use, target_key_id, thread_id), daemon=True).start()
        return

    # قانون ۳: پاسخ متنی هوشمند چت یا کد
    current_ai_mode = "CODE" if active_mode == "CODE" else "CHAT"
    threading.Thread(target=worker_ai_process, args=(chat_id, user_id, msg, text, target_key_id, is_group, target_reply_id, thread_id, current_ai_mode), daemon=True).start()

# ==========================================
# ۶. هندلر دکمه‌های شیشه‌ای و سوییچ لحظه‌ای ۳ حالت و تایید اسپانسر
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(query):
    chat_id = query.message.chat.id
    user_id = str(query.from_user.id)
    data = query.data
    is_group = query.message.chat.type in ["group", "supergroup"]
    target_key_id = f"group_{chat_id}" if is_group else user_id

    if not is_bot_globally_active() and user_id != ADMIN_ID:
        bot.answer_callback_query(query.id, "⚠️ ربات هم‌اکنون توسط ادمین موقتاً خاموش شده است.", show_alert=True)
        return

    # لغو لحظه‌ای درخواست
    if data.startswith("cancel_req_"):
        req_id = data.replace("cancel_req_", "")
        owner_id = req_id.split("_")[0]
        if user_id != owner_id:
            bot.answer_callback_query(query.id, "⛔ این درخواست متعلق به شما نیست!", show_alert=True)
            return

        bot.answer_callback_query(query.id, "✅ درخواست لغو شد.")
        _CANCEL_REQS.add(req_id)
        safe_kv_put(f"CANCEL_{req_id}", "true", 2100)
        try:
            bot.edit_message_text(tr(user_id, "req_canceled"), chat_id=chat_id, message_id=query.message.message_id)
        except Exception:
            pass
        return

    # ==========================================
    # 🔒 تایید عضویت اسپانسر بدون امکان دور زدن
    # ==========================================
    if data == "check_sponsor" and not is_group:
        ok_sponsor, unjoined = check_sponsor_join(user_id)
        if not ok_sponsor:
            bot.answer_callback_query(
                query.id,
                tr(user_id, "sponsor_not_joined"),
                show_alert=True
            )
            try:
                markup = build_sponsor_markup(user_id, unjoined)
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=markup)
            except Exception:
                pass
            return
        else:
            bot.answer_callback_query(query.id, tr(user_id, "sponsor_verified"))
            try:
                bot.delete_message(chat_id, query.message.message_id)
            except Exception:
                pass
            send_main_menu(chat_id, user_id)
            return

    if is_group:
        group_allowed_actions = ["models_hub", "models_cat_chat", "models_cat_image", "close_menu"]
        is_set_action = data.startswith("set_model_") or data.startswith("set_img_model_")

        if data in group_allowed_actions or is_set_action:
            if not is_group_admin(chat_id, user_id):
                bot.answer_callback_query(query.id, "⛔ تغییر مدل در گروه فقط توسط ادمین امکان‌پذیر است!", show_alert=True)
                return

        pv_only = ["main_menu", "history_menu", "new_chat", "switch_mode_chat", "switch_mode_code", "switch_mode_image", "contact_admin", "open_lang_menu"]
        if data in pv_only or data.startswith("switch_sess_") or data.startswith("del_single_sess_") or data.startswith("admin_"):
            bot.answer_callback_query(query.id, "⚠️ این منو فقط در چت خصوصی (پیوی) ربات قابل استفاده است.", show_alert=True)
            return

    try:
        bot.answer_callback_query(query.id)
    except Exception:
        pass

    if data in ["main_menu", "history_menu", "new_chat"]:
        clear_user_state(user_id)

    # تغییر زبان
    if data == "open_lang_menu" and not is_group:
        send_lang_selection_menu(chat_id, user_id, query.message.message_id)

    elif data == "set_lang_fa" and not is_group:
        _USER_LANG_CACHE[user_id] = "fa"
        safe_kv_put(f"USER_LANG_{user_id}", "fa")
        bot.answer_callback_query(query.id, "زبان روی فارسی تنظیم شد.")
        send_main_menu(chat_id, user_id)

    elif data == "set_lang_en" and not is_group:
        _USER_LANG_CACHE[user_id] = "en"
        safe_kv_put(f"USER_LANG_{user_id}", "en")
        bot.answer_callback_query(query.id, "Language set to English.")
        send_main_menu(chat_id, user_id)

    # سوئیچ بین ۳ بخش مستقل
    elif data == "switch_mode_chat":
        _USER_MODES_CACHE[target_key_id] = "CHAT"
        safe_kv_put(f"BOT_MODE_{target_key_id}", "CHAT")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=get_main_menu_markup(user_id, "CHAT"))
        except Exception:
            pass
        bot.send_message(chat_id, tr(user_id, "chat_mode_msg"), parse_mode="Markdown")

    elif data == "switch_mode_code":
        _USER_MODES_CACHE[target_key_id] = "CODE"
        safe_kv_put(f"BOT_MODE_{target_key_id}", "CODE")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=get_main_menu_markup(user_id, "CODE"))
        except Exception:
            pass
        bot.send_message(chat_id, tr(user_id, "code_mode_msg"), parse_mode="Markdown")

    elif data == "switch_mode_image":
        _USER_MODES_CACHE[target_key_id] = "IMAGE"
        safe_kv_put(f"BOT_MODE_{target_key_id}", "IMAGE")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=get_main_menu_markup(user_id, "IMAGE"))
        except Exception:
            pass
        bot.send_message(chat_id, tr(user_id, "image_mode_msg"), parse_mode="Markdown")

    # پیام به پشتیبانی
    elif data == "contact_admin" and not is_group:
        safe_kv_put(f"USER_SUPPORT_STEP_{user_id}", "AWAITING_MSG")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="main_menu", style="danger"))
        bot.send_message(
            chat_id,
            "📞 **بخش پشتیبانی و ارتباط با مدیریت:**\n\nلطفاً پیام، پیشنهاد یا گزارش خود را ارسال کنید:",
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
            f"✍️ **در حال پاسخ به کاربر:** `{target_uid}`\n\nپیام خود را بفرستید:",
            parse_mode="Markdown",
            reply_markup=markup
        )

    # کلید روشن/خاموش سراسری
    elif data == "admin_toggle_off" and user_id == ADMIN_ID:
        global _BOT_STATUS_CACHE, _BOT_STATUS_TIME
        _BOT_STATUS_CACHE = False
        _BOT_STATUS_TIME = time.time()
        safe_kv_put("BOT_GLOBAL_STATUS", "off")
        bot.send_message(chat_id, "🔴 **ربات با موفقیت خاموش شد.**")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=get_admin_panel_markup())
        except Exception:
            pass

    elif data == "admin_toggle_on" and user_id == ADMIN_ID:
        _BOT_STATUS_CACHE = True
        _BOT_STATUS_TIME = time.time()
        safe_kv_delete("BOT_GLOBAL_STATUS")
        bot.send_message(chat_id, "🟢 **ربات با موفقیت روشن شد.**")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=get_admin_panel_markup())
        except Exception:
            pass

    # پاکسازی کش موقت
    elif data == "admin_clean_cache" and user_id == ADMIN_ID:
        clean_system_cache(chat_id)

    # خروجی فایل پشتیبان
    elif data == "admin_backup_chats" and user_id == ADMIN_ID:
        threading.Thread(target=export_all_chats_backup, args=(chat_id,), daemon=True).start()

    # بازگردانی فایل پشتیبان
    elif data == "admin_restore_chats" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "AWAITING_BACKUP_FILE")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel", style="danger"))
        bot.send_message(
            chat_id,
            "📥 **بازگردانی اطلاعات از فایل پشتیبان (بکاپ):**\n\n"
            "لطفاً فایل پشتیبان `.json` را که قبلاً از ربات دریافت کرده‌اید همینجا ارسال (آپلود) کنید.\n\n"
            "⚠️ *نکته امنیتی:* داده‌های موجود در فایل با دیتابیس ترکیب می‌شوند و اطلاعات فعلی بدون تغییر حفظ خواهند شد.",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif data == "main_menu":
        if not is_group:
            send_main_menu(chat_id, user_id)

    elif data == "close_menu":
        try:
            bot.delete_message(chat_id, query.message.message_id)
        except Exception:
            pass

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

        bot.send_message(chat_id, f"✅ مدل چت و کدنویسی روی **{name}** تنظیم شد.", parse_mode="Markdown")

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

    elif data == "new_chat" and not is_group:
        new_sess = f"sess_{int(time.time())}"
        safe_kv_put(f"ACTIVE_SESSION_{user_id}", new_sess)
        sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
        sessions.insert(0, {"id": new_sess, "title": "گفتگوی جدید 💬", "date": get_jalali_date()})
        safe_kv_put(f"SESSIONS_{user_id}", sessions)
        bot.send_message(chat_id, tr(user_id, "new_chat_msg"), parse_mode="Markdown")

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
        bot.send_message(chat_id, "📢 **ارسال پیام همگانی:**\n\nپیام خود را بفرستید:", parse_mode="Markdown")

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
        bot.send_message(chat_id, "✏️ نام جدید مدل تصویر را وارد کنید (یا .):")

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
        bot.send_message(
            chat_id,
            "📢 **افزودن کانال اسپانسر:**\n\n"
            "می‌توانید یوزرنیم کانال را به هر یک از فرمت‌های زیر بفرستید:\n"
            "🔹 `neotenet`\n"
            "🔹 `@neotenet`\n"
            "🔹 `t.me/neotenet`\n"
            "🔹 `https://t.me/neotenet`\n\n"
            "*(ربات باید در کانال ادمین باشد)*",
            parse_mode="Markdown"
        )

    elif data == "admin_del_sponsor_menu" and user_id == ADMIN_ID:
        send_admin_sponsor_list(chat_id)

    elif data.startswith("del_sponsor_") and user_id == ADMIN_ID:
        idx = int(data.replace("del_sponsor_", ""))
        channels = get_sponsor_channels_cached()
        if 0 <= idx < len(channels):
            channels.pop(idx)
            safe_kv_put("SPONSOR_CHANNELS", channels)
            global _SPONSORS_CACHE
            _SPONSORS_CACHE = channels
        send_admin_sponsor_list(chat_id, query.message.message_id)

    elif data == "admin_ban_user" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "BAN_USER")
        bot.send_message(chat_id, "🚫 آیدی عددی کاربر برای مسدودسازی:")

    elif data == "admin_unban_user" and user_id == ADMIN_ID:
        safe_kv_delete(f"BANNED_{text.strip()}")
        clear_user_state(user_id)
        bot.send_message(chat_id, "✅ کاربر رفع مسدودی شد.")
        bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())

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
        bot.send_message(chat_id, "🌐 **URL BASE** تصویرساز را وارد کنید:", parse_mode="Markdown")

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
        bot.send_message(chat_id, "📌 **MODEL NAME** تصویرساز را وارد کنید:", parse_mode="Markdown")

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
        bot.send_message(chat_id, "👁 قابلیت Vision؟ (`yes` یا `no` یا .)", parse_mode="Markdown")

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
        bot.send_message(chat_id, "🌐 URL Base جدید تصویرساز (یا .):")

    elif step == "EDIT_IMG_URL":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IMG_IDX_{user_id}") or "0")
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if text != "." and idx < len(img_models):
            img_models[idx]["baseUrl"] = text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_IMG_KEY")
        bot.send_message(chat_id, "🔑 API Key جدید تصویرساز (یا .):")

    elif step == "EDIT_IMG_KEY":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IMG_IDX_{user_id}") or "0")
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if text != "." and idx < len(img_models):
            img_models[idx]["apiKey"] = "" if text.strip() == "." else text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_IMG_ID")
        bot.send_message(chat_id, "📌 Model Name جدید تصویرساز (یا .):")

    elif step == "EDIT_IMG_ID":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IMG_IDX_{user_id}") or "0")
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if text != "." and idx < len(img_models):
            img_models[idx]["modelName"] = text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
        clear_user_state(user_id)
        bot.send_message(chat_id, "✅ مدل ساخت عکس ویرایش شد!")
        bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())

    elif step == "ADD_SPONSOR":
        clean_ch = clean_channel_username(text)
        if clean_ch:
            channels = get_sponsor_channels_cached()
            if clean_ch not in channels:
                channels.append(clean_ch)
                safe_kv_put("SPONSOR_CHANNELS", channels)
                global _SPONSORS_CACHE
                _SPONSORS_CACHE = channels
            clear_user_state(user_id)
            bot.send_message(chat_id, f"📢 کانال اسپانسر `{clean_ch}` با موفقیت اضافه شد.", parse_mode="Markdown")
            bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())
        else:
            bot.send_message(chat_id, "❌ یوزرنیم کانال نامعتبر است.")

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
    print("🚀 Instant /start Enabled (< 0.2s)")
    print("🌐 Bilingual Support Active (FA / EN)")
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
