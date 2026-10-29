# -*- coding: utf-8 -*-
"""
Telegram AI Bot - Python + Upstash Redis (100% Safe, Autonomous Tech & Code AI Agent)
Configured for: Wispbyte / bot-hosting.net (Docker / Linux Environment)
Features:
- Complete Model Management Engine: Full Edit (Name, URL, API Key, Model ID, Toggle Vision) with Cancel
- Instant UI State Engine: Checkmarks move immediately upon model click
- Ultra-Fast Cache Cleaning: Instant RAM and Redis Temp Key Purge under 0.1s
- Native provider web search: uses only web-search tools exposed by the connected model API
- Provider-returned citations and source links are shown when the API supplies them
- Stable processing status text without repeated countdown edits
- Full Admin User CRM: Search by Numeric ID, View Profiles, One-Click Ban/Unban, Kick, DM & Manual Add
- Group Moderation: Bot Mute (/bot سکوت & /bot صحبت), Group Lock/Unlock (/lock & /unlock), User Mute/Ban/Del
- Dedicated Code Model Selector: Chat, Coding, and Image models are completely independent in groups & PV
- Universal Cancel Button in all Admin Wizard Prompts (Add/Edit Model, Sponsor, Ban, DM)
- Multi-Trigger Group Calls: Responds instantly to (نئو, نعو, neo, tenet) and (ربات:)
- Native Async Image Generation Support (Handles HTTP 202 Job Polling for xKiro / SenseNova)
- Separate Video Model Manager with job polling and downloadable output handling
- Independent standalone search engine removed; video tools retained
- Strict Thought Filter: Strips <think> and internal monologues completely with safe reasoning fallback
Timeout: 60 Minutes (3600s)
Developer Channel: T.me/Neotenet
"""

import os
import io
import ast
import inspect
import re
import json
import time
import html
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
    IRAN_TIMEZONE = ZoneInfo("Asia/Tehran")
except Exception:  # Compatibility fallback for older Python installations
    IRAN_TIMEZONE = timezone(timedelta(hours=3, minutes=30))
import base64
import socket
import threading
import urllib.parse
import traceback
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import requests
from requests.adapters import HTTPAdapter
import telebot
from telebot import types
from telebot.types import ChatPermissions
from telebot.apihelper import ApiTelegramException

# ==========================================
# ⚡ کش‌های سراسری درون‌حافظه‌ای جهت سرعت آنی
# ==========================================
_KNOWN_USERS_CACHE = set()
_LAST_ACTIVE_CACHE = {}
_CANCEL_REQS = set()
_BOT_STATUS_CACHE = None
_BOT_STATUS_TIME = 0
_SPONSORS_CACHE = None
_SPONSORS_CACHE_TIME = 0
_USER_MODES_CACHE = {}
_USER_LANG_CACHE = {}

# Prevent duplicate activity writes and no-op thread creation during traffic spikes.
_ACTIVITY_LOCK = threading.Lock()
_TRACKING_USERS = set()

# Cache getMe because doing a Telegram API round-trip for every group message adds latency.
_BOT_INFO_CACHE = None
_BOT_INFO_CACHE_TIME = 0.0
_BOT_INFO_LOCK = threading.Lock()

# Short-lived flags prevent repeated Redis round-trips on every group message.
_STATE_FLAG_CACHE = {}
_STATE_FLAG_LOCK = threading.Lock()
_STATE_FLAG_TTL = 30.0

# Cache successful sponsor checks briefly; re-check non-members immediately when they press Verify.
_SPONSOR_JOIN_VERIFIED_CACHE = {}
_SPONSOR_JOIN_VERIFIED_LOCK = threading.Lock()
_SPONSOR_JOIN_VERIFIED_TTL = 60.0

# Menu callbacks update local state immediately and persist it in a single background worker.
_MODEL_SELECTION_CACHE = {}
_MODEL_SELECTION_CACHE_LOCK = threading.Lock()
_MODEL_SELECTION_CACHE_TTL = 300.0
_SELECTED_MODEL_DISPLAY_CACHE = {}
_SELECTED_MODEL_DISPLAY_LOCK = threading.Lock()
_SELECTED_MODEL_DISPLAY_TTL = 120.0
_MAIN_MENU_MESSAGE_ID_CACHE = {}
_MAIN_MENU_MESSAGE_ID_LOCK = threading.Lock()

# Short TTL caches prevent serial Redis round-trips before every AI response.
_ACTIVE_SESSION_CACHE = {}
_ACTIVE_SESSION_CACHE_LOCK = threading.Lock()
_ACTIVE_SESSION_CACHE_TTL = 300.0
_CHAT_HISTORY_CACHE = {}
_CHAT_HISTORY_CACHE_LOCK = threading.Lock()
_CHAT_HISTORY_CACHE_TTL = 300.0
_CHAT_HISTORY_CACHE_MAX = 2048
_TEMP_STATE_CACHE = {}
_TEMP_STATE_CACHE_LOCK = threading.Lock()
_TEMP_STATE_CACHE_TTL = 45.0
_TEMP_STATE_CACHE_MAX = 4096

# When the bot is globally disabled, do not send a warning for every group message.
_INACTIVE_NOTICE_LAST_SENT = {}
_INACTIVE_NOTICE_LOCK = threading.Lock()
_INACTIVE_NOTICE_INTERVAL = 60.0

# کش‌های سرعت بالای مانیتورینگ ادمین
_ALL_USERS_CACHE = None
_ALL_USERS_CACHE_TIME = 0
_AI_MODELS_CACHE = None
_AI_MODELS_CACHE_TIME = 0
_CODE_MODELS_CACHE = None
_CODE_MODELS_CACHE_TIME = 0
_IMAGE_MODELS_CACHE = None
_IMAGE_MODELS_CACHE_TIME = 0
_VIDEO_MODELS_CACHE = None
_VIDEO_MODELS_CACHE_TIME = 0
_MODEL_REGISTRY_CACHE_TTL = 600.0

_THINK_TAG_REGEX = re.compile(r'<think>[\s\S]*?</think>', flags=re.IGNORECASE)
_CODE_BLOCK_REGEX = re.compile(r'```([a-zA-Z0-9_+-]*)[^\n]*\r?\n([\s\S]*?)```')
_CLEAN_WORDS_REGEX = re.compile(r'[^\w\s]')


def _safe_stream_preview(raw_content):
    """Remove complete and still-open <think> regions before showing partial model output."""
    raw = str(raw_content or "")
    tag_re = re.compile(r"</?think\b[^>]*>", flags=re.IGNORECASE)
    chunks = []
    pos = 0
    in_think = False
    for match in tag_re.finditer(raw):
        tag = match.group(0).lower()
        is_close = tag.startswith("</")
        if not in_think and not is_close:
            chunks.append(raw[pos:match.start()])
            in_think = True
        elif in_think and is_close:
            in_think = False
        pos = match.end()
    if not in_think:
        chunks.append(raw[pos:])
    visible = "".join(chunks)
    visible = re.sub(r"[ \t]{2,}", " ", visible)
    return visible.strip()

_ROBOT_PREFIX_REGEX = re.compile(
    r'^(نئو|نعو|neo|tenet|تننت|ربات|روبات|بات)(?=$|[\s:،,\-–—.!?؟])'
    r'[\s:،,\-–—.!?؟]*(.*)$',
    flags=re.IGNORECASE | re.DOTALL
)
_ROBOT_EXACT_CALLS = {'ربات', 'روبات', 'بات', 'نئو', 'نعو', 'neo', 'tenet', 'تننت'}


def _strip_bot_mention(text, bot_username):
    """Return (mention_found, text_without_our_bot_mention)."""
    raw = str(text or '')
    username = str(bot_username or '').strip().lstrip('@')
    if not username:
        return False, raw.strip()
    pattern = re.compile(r'(?<![\w])@' + re.escape(username) + r'(?![\w])', re.IGNORECASE)
    found = bool(pattern.search(raw))
    return found, pattern.sub(' ', raw).strip()


def extract_group_invocation(text, bot_username=''):
    """Recognize explicit group calls by Persian/English prefix or bot @mention.

    Examples: ``نئو سلام``, ``نعو - سلام``, ``neo-hello``, ``Neo: hello``,
    ``ربات سلام``, ``بات سلام`` and ``hello @botname``.
    Returns (is_invoked, prompt). The empty prompt means a bare bot call.
    """
    raw = str(text or '').strip()
    mentioned, without_mention = _strip_bot_mention(raw, bot_username)

    candidate = without_mention if mentioned else raw
    match = _ROBOT_PREFIX_REGEX.match(candidate)
    if match:
        return True, match.group(2).strip()

    exact = re.sub(r'[\s:،,\-–—.!?؟]+$', '', candidate).strip().lower()
    if exact in _ROBOT_EXACT_CALLS:
        return True, ''

    if mentioned:
        return True, candidate.strip()
    return False, raw

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

# ==========================================
# 🌐 سیستم دو زبانه
# ==========================================
I18N = {
    "fa": {
        "welcome": "🚀 **به ربات هوش مصنوعی خوش آمدید!**\n\n🎯 **بخش فعال:** `{mode}`\n🤖 **مدل انتخاب‌شده:** `{model_name}`\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
        "mode_chat_name": "💬 پرسش، تحقیق وب و حل مسائل",
        "mode_code_name": "💻 برنامه‌نویسی و توسعه نرم‌افزار",
        "mode_image_name": "🎨 استودیوی ساخت تصویر",
        "mode_video_name": "🎬 استودیوی ساخت ویدیو",
        "btn_chat": "💬 پرسش و پاسخ",
        "btn_code": "💻 بخش کدنویسی",
        "btn_img": "🎨 ساخت عکس",
        "btn_video": "🎬 ساخت ویدیو",
        "btn_video_model": "🎛 انتخاب مدل ساخت ویدیو",
        "btn_back_main": "🔙 بازگشت به منوی اصلی",
        "video_prompt_request": "🎬 توضیح ویدیویی را که می‌خواهی بسازم در پیام بعدی بفرست. برای انصراف، دکمهٔ بازگشت را بزن.",
        "btn_models": "🤖 انتخاب مدل هوش مصنوعی",
        "btn_history": "📜 تاریخچه گفتگوها",
        "btn_support": "📞 پیام به پشتیبانی و ادمین",
        "btn_new_chat": "➕ شروع گفتگوی جدید",
        "btn_admin": "⚙️ پنل مدیریت ادمین",
        "btn_lang": "🌐 تغییر زبان / Language",
        "sponsor_warn": "⚠️ **برای استفاده از امکانات ربات، ابتدا در کانال‌(های) اسپانسر زیر عضو شوید:**",
        "sponsor_btn": "📢 عضویت در کانال ({ch})",
        "sponsor_check_btn": "✅ عضو شدم / بررسی",
        "sponsor_not_joined": "⚠️ شما هنوز در تمام کانال‌های اسپانسر عضو نشده‌اید!\nلطفاً ابتدا عضو شوید و سپس دکمه بررسی را بزنید.",
        "sponsor_verified": "✅ عضویت شما با موفقیت تایید شد!",
        "lang_select_title": "🌐 **لطفاً زبان مورد نظر را انتخاب کنید / Please select language:**",
        "lang_changed": "✅ زبان ربات با موفقیت روی **فارسی** تنظیم شد.",
        "chat_mode_msg": "💬 **بخش «پرسش و پاسخ و تحقیق آنلاین» فعال شد.**\nاگر API مدل شما جست‌وجوی وب بومی داشته باشد، از همان ابزار خود سرویس استفاده می‌شود.",
        "code_mode_msg": "💻 **بخش «کدنویسی و مهندسی نرم‌افزار» فعال شد.**",
        "image_mode_msg": "🎨 **بخش «استودیو ساخت عکس» فعال شد.**",
        "video_mode_msg": "🎬 **بخش ساخت ویدیو فعال شد.** پرامپت ویدیو را ارسال کن.",
        "cancel_btn": "❌ لغو عملیات",
        "req_canceled": "❌ عملیات با موفقیت لغو شد.",
        "new_chat_msg": "✨ چت جدید ایجاد شد! پیام خود را بفرستید."
    },
    "en": {
        "welcome": "🚀 **Welcome to the AI Assistant Bot!**\n\n🎯 **Active section:** `{mode}`\n🤖 **Selected model:** `{model_name}`\n\nChoose an option below:",
        "mode_chat_name": "💬 Q&A, web research & problem solving",
        "mode_code_name": "💻 Programming & Software Development",
        "mode_image_name": "🎨 Image Generation Studio",
        "mode_video_name": "🎬 Video Generation Studio",
        "btn_chat": "💬 Q&A & Chat",
        "btn_code": "💻 Coding & Dev",
        "btn_img": "🎨 Image Studio",
        "btn_video": "🎬 Generate Video",
        "btn_video_model": "🎛 Select video model",
        "btn_back_main": "🔙 Back to main menu",
        "video_prompt_request": "🎬 Send a description of the video you want in your next message. Tap Back to cancel.",
        "btn_models": "🤖 Select AI Model",
        "btn_history": "📜 Chat History",
        "btn_support": "📞 Contact Support",
        "btn_new_chat": "➕ New Chat",
        "btn_admin": "⚙️ Admin Panel",
        "btn_lang": "🌐 Language / زبان",
        "sponsor_warn": "⚠️ **Please join our sponsor channel(s) below to use the bot:**",
        "sponsor_btn": "📢 Join Channel ({ch})",
        "sponsor_check_btn": "✅ Joined / Verify",
        "sponsor_not_joined": "⚠️ You have not joined all sponsor channels yet!",
        "sponsor_verified": "✅ Membership verified successfully!",
        "lang_select_title": "🌐 **Please select your language:**",
        "lang_changed": "✅ Language successfully set to **English**.",
        "chat_mode_msg": "💬 **Tech Q&A & Research Agent activated.** The bot uses only native web-search tools supported by the connected API.",
        "code_mode_msg": "💻 **Coding & Software Dev Agent activated.**",
        "image_mode_msg": "🎨 **Image Generation Studio activated.**",
        "video_mode_msg": "🎬 **Video generation mode activated.** Send a video prompt.",
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
# 🎨 دکمه‌های رنگی تلگرام
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
# 📅 تقویم جلالی و ثبت روز دقیق هفته
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

def get_iran_now():
    """Return current time in Iran, independent of the hosting server timezone."""
    return datetime.now(IRAN_TIMEZONE)

def format_jalali_datetime(dt=None):
    dt = dt or get_iran_now()
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return f"{jy}/{jm:02d}/{jd:02d} {dt.hour:02d}:{dt.minute:02d}"

def make_session_record(session_id, title="گفتگوی جدید 💬", dt=None):
    dt = dt or get_iran_now()
    return {
        "id": str(session_id),
        "title": title,
        "date": format_jalali_datetime(dt),
        "created_at": dt.isoformat(timespec="seconds"),
    }

def get_jalali_date():
    dt = get_iran_now()
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return f"{jy}/{jm:02d}/{jd:02d}"

def get_full_current_date_info():
    dt = get_iran_now()
    j_date = get_jalali_date()
    weekdays_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
    day_fa = weekdays_fa[dt.weekday()]
    g_date = f"{dt.year}-{dt.month:02d}-{dt.day:02d}"
    return f"{day_fa} {j_date} هجری شمسی (مطابق با {g_date} میلادی، ساعت ایران {dt:%H:%M})"

def format_session_date(d_str):
    if not d_str:
        return get_jalali_date()
    d_str = str(d_str).strip()
    # Old records may contain only a Gregorian date; convert those to Jalali.
    date_only = d_str.split()[0]
    parts = re.split(r'[-/]', date_only)
    if len(parts) == 3 and parts[0].isdigit() and int(parts[0]) > 1600:
        try:
            jy, jm, jd = gregorian_to_jalali(int(parts[0]), int(parts[1]), int(parts[2]))
            suffix = " " + " ".join(d_str.split()[1:]) if len(d_str.split()) > 1 else ""
            return f"{jy}/{jm:02d}/{jd:02d}{suffix}"
        except Exception:
            pass
    return d_str

def format_session_display(session, user_id):
    """Format saved chat timestamp in Iran local time; Persian users see Jalali date."""
    created_at = str((session or {}).get("created_at") or "").strip()
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=IRAN_TIMEZONE)
            else:
                dt = dt.astimezone(IRAN_TIMEZONE)
            if get_user_lang(user_id) == "fa":
                weekdays_fa = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یکشنبه"]
                jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
                return f"{jy}/{jm:02d}/{jd:02d} {dt:%H:%M}"
            return f"{dt:%Y-%m-%d %H:%M}"
        except Exception:
            pass
    # Older saved sessions did not retain an exact time; do not invent one.
    return format_session_date((session or {}).get("date"))

# ==========================================
# ⚙️ تنظیمات اصلی و اطلاعات دیتابیس Upstash
# ==========================================
# Keep credentials outside source control. Configure these in the hosting provider's environment.
BOT_TOKEN = os.getenv("BOT_TOKEN", "8970181549")
ADMIN_ID = str(os.getenv("ADMIN_ID", "1033000000"))

UPSTASH_URL = os.getenv("UPSTASH_URL", "https://precious-chimpupstash.io")
UPSTASH_TOKEN = os.getenv("UPSTASH_TOKEN", "gQAAAAAAA0eEEeeeeeee")

def _env_int(name, default, minimum, maximum):
    """Read a bounded integer setting without letting a bad environment value stop startup."""
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))


# Large-waiting-queue profile for a low-resource host. Only queue limits were increased;
# active worker counts and Telegram handler thread count are intentionally unchanged.
# Each pool can hold up to 1000 waiting jobs; this absorbs bursts, not 1000 simultaneous completions.
TELEGRAM_HANDLER_THREADS = _env_int("BOT_HANDLER_THREADS", 40, 4, 64)
AI_JOB_WORKERS = _env_int("AI_JOB_WORKERS", 10, 2, 32)
AI_JOB_QUEUE_LIMIT = _env_int("AI_JOB_QUEUE_LIMIT", 1000, 8, 2048)
GROUP_AI_JOB_WORKERS = _env_int("GROUP_AI_JOB_WORKERS", 6, 1, 12)
GROUP_AI_JOB_QUEUE_LIMIT = _env_int("GROUP_AI_JOB_QUEUE_LIMIT", 1000, 4, 2048)
CALLBACK_WORKERS = _env_int("BOT_CALLBACK_WORKERS", 16, 2, 32)
CALLBACK_QUEUE_LIMIT = _env_int("BOT_CALLBACK_QUEUE_LIMIT", 1000, 8, 2048)
# Image/video services often have slower jobs and different rate limits. Keep them
# out of the general chat/code queue so one type of workload cannot monopolize it.
IMAGE_JOB_WORKERS = _env_int("IMAGE_JOB_WORKERS", 2, 1, 8)
IMAGE_JOB_QUEUE_LIMIT = _env_int("IMAGE_JOB_QUEUE_LIMIT", 1000, 4, 2048)
VIDEO_JOB_WORKERS = _env_int("VIDEO_JOB_WORKERS", 1, 1, 4)
VIDEO_JOB_QUEUE_LIMIT = _env_int("VIDEO_JOB_QUEUE_LIMIT", 1000, 2, 2048)
API_TIMEOUT_SECONDS = _env_int("API_TIMEOUT_SECONDS", 3600, 60, 7200)
API_CONNECT_TIMEOUT_SECONDS = _env_int("API_CONNECT_TIMEOUT_SECONDS", 15, 3, 120)

# Keep small settings writes off interactive callback threads; one worker preserves write order.
_SETTINGS_PERSIST_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="neo-settings-persist")

bot = telebot.TeleBot(
    BOT_TOKEN or "0:REPLACE_WITH_BOT_TOKEN",
    parse_mode=None,
    threaded=True,
    num_threads=TELEGRAM_HANDLER_THREADS,
)

# Each executor has a bounded semaphore so excessive submissions are rejected cleanly.
# Chat/code, group text/code, callbacks, image generation, and video generation each
# have separate limits. These pools do not create unlimited background threads.
_AI_JOB_EXECUTOR = ThreadPoolExecutor(max_workers=AI_JOB_WORKERS, thread_name_prefix="neo-ai-job")
_AI_JOB_SLOTS = threading.BoundedSemaphore(AI_JOB_WORKERS + AI_JOB_QUEUE_LIMIT)
_GROUP_AI_JOB_EXECUTOR = ThreadPoolExecutor(max_workers=GROUP_AI_JOB_WORKERS, thread_name_prefix="neo-group-ai")
_GROUP_AI_JOB_SLOTS = threading.BoundedSemaphore(GROUP_AI_JOB_WORKERS + GROUP_AI_JOB_QUEUE_LIMIT)
_CALLBACK_EXECUTOR = ThreadPoolExecutor(max_workers=CALLBACK_WORKERS, thread_name_prefix="neo-callback")
_CALLBACK_SLOTS = threading.BoundedSemaphore(CALLBACK_WORKERS + CALLBACK_QUEUE_LIMIT)
_IMAGE_JOB_EXECUTOR = ThreadPoolExecutor(max_workers=IMAGE_JOB_WORKERS, thread_name_prefix="neo-image-job")
_IMAGE_JOB_SLOTS = threading.BoundedSemaphore(IMAGE_JOB_WORKERS + IMAGE_JOB_QUEUE_LIMIT)
_VIDEO_JOB_EXECUTOR = ThreadPoolExecutor(max_workers=VIDEO_JOB_WORKERS, thread_name_prefix="neo-video-job")
_VIDEO_JOB_SLOTS = threading.BoundedSemaphore(VIDEO_JOB_WORKERS + VIDEO_JOB_QUEUE_LIMIT)


def _submit_bounded(executor, slots, target, *args, **kwargs):
    """Submit a task only when there is capacity; return False rather than spawning unlimited threads."""
    if not slots.acquire(blocking=False):
        return False
    try:
        future = executor.submit(target, *args, **kwargs)
    except Exception:
        slots.release()
        raise
    future.add_done_callback(lambda _future: slots.release())
    return True


def get_bot_info_cached(force_refresh=False, max_age_seconds=600):
    """Thread-safe cache for Telegram getMe data; refresh at most every 10 minutes."""
    global _BOT_INFO_CACHE, _BOT_INFO_CACHE_TIME
    now = time.monotonic()
    if not force_refresh and _BOT_INFO_CACHE is not None and (now - _BOT_INFO_CACHE_TIME) < max_age_seconds:
        return _BOT_INFO_CACHE
    with _BOT_INFO_LOCK:
        now = time.monotonic()
        if not force_refresh and _BOT_INFO_CACHE is not None and (now - _BOT_INFO_CACHE_TIME) < max_age_seconds:
            return _BOT_INFO_CACHE
        try:
            info = bot.get_me()
            _BOT_INFO_CACHE = info
            _BOT_INFO_CACHE_TIME = time.monotonic()
            return info
        except Exception:
            # Normal message handling can fall back to the cache, but an explicit
            # health check must report a fresh API failure rather than a cached success.
            if _BOT_INFO_CACHE is not None and not force_refresh:
                return _BOT_INFO_CACHE
            raise


def _notify_job_queue_full(chat_id, thread_id=None, status_msg=None):
    message = "⚠️ تعداد درخواست‌های هم‌زمان زیاد است. لطفاً کمی بعد دوباره تلاش کن."
    if _edit_processing_ack(chat_id, status_msg, message):
        return
    kwargs = {"message_thread_id": thread_id} if thread_id else {}
    try:
        bot.send_message(chat_id, message, **kwargs)
    except Exception as exc:
        print(f"[Overload Notice Error]: {type(exc).__name__}")

# ==========================================
# 🌐 تنظیم سوکت شبکه با پکت‌های زنده
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
adapter = TCPKeepAliveAdapter(pool_connections=30, pool_maxsize=60)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

# Use a persistent per-worker session for model APIs. Redis and image/video traffic use
# the general session above; keeping model connections isolated avoids pool contention
# and reuses TLS connections between requests handled by the same AI worker.
_API_HTTP_LOCAL = threading.local()

def get_api_http_session():
    session = getattr(_API_HTTP_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        api_adapter = TCPKeepAliveAdapter(pool_connections=12, pool_maxsize=4)
        session.mount("https://", api_adapter)
        session.mount("http://", api_adapter)
        session.headers.update({"Connection": "keep-alive"})
        _API_HTTP_LOCAL.session = session
    return session

# ==========================================
# ۰. توابع کمکی دیتابیس Upstash Redis
# ==========================================
def upstash_command(cmd):
    try:
        headers = {
            "Authorization": f"Bearer {UPSTASH_TOKEN}",
            "Content-Type": "application/json"
        }
        res = http_session.post(UPSTASH_URL, headers=headers, json=cmd, timeout=8)
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


def _history_cache_put(key, history):
    """Cache only the compact sanitized history representation, never base64 image data."""
    try:
        safe_history = json.loads(json.dumps(history if isinstance(history, list) else [], ensure_ascii=False))
    except Exception:
        safe_history = []
    now = time.monotonic()
    with _CHAT_HISTORY_CACHE_LOCK:
        _CHAT_HISTORY_CACHE[key] = (now, safe_history)
        if len(_CHAT_HISTORY_CACHE) > _CHAT_HISTORY_CACHE_MAX:
            oldest = sorted(_CHAT_HISTORY_CACHE.items(), key=lambda item: item[1][0])
            for old_key, _ in oldest[:max(1, len(_CHAT_HISTORY_CACHE) - _CHAT_HISTORY_CACHE_MAX)]:
                _CHAT_HISTORY_CACHE.pop(old_key, None)


def _history_cache_delete(key):
    with _CHAT_HISTORY_CACHE_LOCK:
        _CHAT_HISTORY_CACHE.pop(key, None)


def _load_chat_history(key):
    now = time.monotonic()
    with _CHAT_HISTORY_CACHE_LOCK:
        cached = _CHAT_HISTORY_CACHE.get(key)
        if cached and now - cached[0] < _CHAT_HISTORY_CACHE_TTL:
            try:
                return json.loads(json.dumps(cached[1], ensure_ascii=False))
            except Exception:
                _CHAT_HISTORY_CACHE.pop(key, None)
    raw = safe_kv_get(key)
    try:
        history = json.loads(raw or "[]")
        if not isinstance(history, list):
            history = []
    except Exception:
        history = []
    _history_cache_put(key, history)
    return history


def _set_active_session_cache(user_id, session_id):
    with _ACTIVE_SESSION_CACHE_LOCK:
        if session_id:
            _ACTIVE_SESSION_CACHE[str(user_id)] = (time.monotonic(), str(session_id))
        else:
            _ACTIVE_SESSION_CACHE.pop(str(user_id), None)


def _get_active_session_cache(user_id):
    now = time.monotonic()
    with _ACTIVE_SESSION_CACHE_LOCK:
        cached = _ACTIVE_SESSION_CACHE.get(str(user_id))
        if cached and now - cached[0] < _ACTIVE_SESSION_CACHE_TTL:
            return cached[1]
        _ACTIVE_SESSION_CACHE.pop(str(user_id), None)
    return None


def _temp_state_get(key):
    """Cache transient image-prompt/file-id state so ordinary prompts avoid extra Redis GETs."""
    now = time.monotonic()
    with _TEMP_STATE_CACHE_LOCK:
        cached = _TEMP_STATE_CACHE.get(key)
        if cached and now - cached[0] < _TEMP_STATE_CACHE_TTL:
            return cached[1]
        _TEMP_STATE_CACHE.pop(key, None)
    value = safe_kv_get(key)
    with _TEMP_STATE_CACHE_LOCK:
        _TEMP_STATE_CACHE[key] = (time.monotonic(), value)
        if len(_TEMP_STATE_CACHE) > _TEMP_STATE_CACHE_MAX:
            oldest = sorted(_TEMP_STATE_CACHE.items(), key=lambda item: item[1][0])
            for old_key, _ in oldest[:max(1, len(_TEMP_STATE_CACHE) - _TEMP_STATE_CACHE_MAX)]:
                _TEMP_STATE_CACHE.pop(old_key, None)
    return value


def _temp_state_put(key, value, expiration_ttl=None):
    str_value = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    with _TEMP_STATE_CACHE_LOCK:
        _TEMP_STATE_CACHE[key] = (time.monotonic(), str_value)
    return safe_kv_put(key, str_value, expiration_ttl=expiration_ttl)


def _temp_state_delete(key):
    with _TEMP_STATE_CACHE_LOCK:
        _TEMP_STATE_CACHE.pop(key, None)
    return safe_kv_delete(key)


def _persist_kv_async(key, value, expiration_ttl=None):
    """Persist UI settings outside callback workers so menu updates do not wait on Redis."""
    try:
        _SETTINGS_PERSIST_EXECUTOR.submit(safe_kv_put, key, value, expiration_ttl)
        return True
    except Exception as exc:
        print(f"[Async Settings Persist Error {key}]: {type(exc).__name__}")
        return False


def _model_selection_get_cached(key):
    now = time.monotonic()
    with _MODEL_SELECTION_CACHE_LOCK:
        cached = _MODEL_SELECTION_CACHE.get(key)
        if cached and (now - cached[0]) < _MODEL_SELECTION_CACHE_TTL:
            return cached[1]
    return None


def _model_selection_get_or_load(key, default="0"):
    """Get a selected index from RAM; query Redis only on a cold cache."""
    value = _model_selection_get_cached(key)
    if value is not None:
        return str(value)
    value = safe_kv_get(key) or default
    with _MODEL_SELECTION_CACHE_LOCK:
        _MODEL_SELECTION_CACHE[key] = (time.monotonic(), str(value))
    return str(value)


def _model_selection_set_cached(key, value, persist=True):
    value = str(value)
    with _MODEL_SELECTION_CACHE_LOCK:
        _MODEL_SELECTION_CACHE[key] = (time.monotonic(), value)
    if persist:
        _persist_kv_async(key, value)
    return value


def _send_processing_ack(chat_id, text, thread_id=None, reply_to_message_id=None, reply_markup=None):
    """Send a quick status message before Redis/API work or queue waiting."""
    kwargs = {}
    if thread_id:
        kwargs["message_thread_id"] = thread_id
    if reply_to_message_id:
        kwargs["reply_to_message_id"] = reply_to_message_id
        kwargs["allow_sending_without_reply"] = True
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as exc:
        print(f"[Fast Acknowledgement Warning] chat={chat_id}: {type(exc).__name__}")
        return None


def _prepare_ai_job_status(chat_id, user_id, status_msg, thread_id=None, reply_to_message_id=None, received_at=None, is_group=False):
    """Attach a cancel button before placing a text/code AI task in a possibly busy queue."""
    request_id = f"{user_id}_{time.time_ns()}"
    if received_at is not None:
        print(f"[AI Timing] handler_to_enqueue user={user_id} group={is_group} elapsed={max(0.0, time.monotonic()-received_at):.2f}s")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ لغو درخواست", callback_data=f"cancel_req_{request_id}", style="danger"))
    status_text = "💬 در حال فکر کردن..."
    if status_msg is not None:
        _edit_processing_ack(chat_id, status_msg, status_text, reply_markup=markup)
    else:
        status_msg = _send_processing_ack(
            chat_id, status_text, thread_id=thread_id,
            reply_to_message_id=reply_to_message_id, reply_markup=markup,
        )
    return request_id, status_msg, time.monotonic()


def _edit_processing_ack(chat_id, status_msg, text, reply_markup=None, parse_mode=None):
    if status_msg is None:
        return False
    try:
        bot.edit_message_text(
            text, chat_id=chat_id, message_id=status_msg.message_id,
            reply_markup=reply_markup, parse_mode=parse_mode,
        )
        return True
    except Exception:
        return False


def _delete_processing_ack(chat_id, status_msg):
    if status_msg is None:
        return
    try:
        bot.delete_message(chat_id, status_msg.message_id)
    except Exception:
        pass


def _clear_active_history_async(user_id):
    def _clear():
        active_session = safe_kv_get(f"ACTIVE_SESSION_{user_id}")
        if active_session:
            safe_kv_delete(f"HISTORY_{user_id}_{active_session}")
    try:
        _SETTINGS_PERSIST_EXECUTOR.submit(_clear)
    except Exception as exc:
        print(f"[Async History Clear Warning] user={user_id}: {type(exc).__name__}")

# ==========================================
# ⚡ توابع ایمن مدیریت کش‌ها (ضد SyntaxError)
# ==========================================
def set_bot_status(is_active):
    global _BOT_STATUS_CACHE, _BOT_STATUS_TIME
    _BOT_STATUS_CACHE = is_active
    _BOT_STATUS_TIME = time.time()

def is_bot_globally_active():
    global _BOT_STATUS_CACHE, _BOT_STATUS_TIME
    now = time.time()
    if _BOT_STATUS_CACHE is not None and (now - _BOT_STATUS_TIME) < 120:
        return _BOT_STATUS_CACHE
    res = safe_kv_get("BOT_GLOBAL_STATUS") != "off"
    _BOT_STATUS_CACHE = res
    _BOT_STATUS_TIME = now
    return res


def _get_cached_state_flag(cache_key, redis_key):
    """Read a true/false Redis flag with a tiny TTL for high-traffic message paths."""
    now = time.monotonic()
    with _STATE_FLAG_LOCK:
        cached = _STATE_FLAG_CACHE.get(cache_key)
        if cached and (now - cached[0]) < _STATE_FLAG_TTL:
            return cached[1]
    value = str(safe_kv_get(redis_key) or "").lower() == "true"
    with _STATE_FLAG_LOCK:
        _STATE_FLAG_CACHE[cache_key] = (time.monotonic(), value)
    return value


def _invalidate_state_flag(cache_key):
    with _STATE_FLAG_LOCK:
        _STATE_FLAG_CACHE.pop(cache_key, None)


def is_user_banned_cached(user_id):
    user_id = str(user_id)
    return _get_cached_state_flag(("banned", user_id), f"BANNED_{user_id}")


def is_group_muted_cached(chat_id):
    chat_id = str(chat_id)
    return _get_cached_state_flag(("group_muted", chat_id), f"GROUP_MUTED_{chat_id}")


def notify_bot_disabled_once(chat_id, thread_id=None):
    """Rate-limit the disabled notice and swallow transient Telegram network failures."""
    now = time.monotonic()
    key = str(chat_id)
    with _INACTIVE_NOTICE_LOCK:
        last_sent = _INACTIVE_NOTICE_LAST_SENT.get(key, 0.0)
        if now - last_sent < _INACTIVE_NOTICE_INTERVAL:
            return False
        # Throttle before attempting the API call, including failed sends.
        _INACTIVE_NOTICE_LAST_SENT[key] = now
        if len(_INACTIVE_NOTICE_LAST_SENT) > 4096:
            cutoff = now - (_INACTIVE_NOTICE_INTERVAL * 5)
            for old_key, old_time in list(_INACTIVE_NOTICE_LAST_SENT.items()):
                if old_time < cutoff:
                    _INACTIVE_NOTICE_LAST_SENT.pop(old_key, None)
    kwargs = {"parse_mode": "Markdown"}
    if thread_id:
        kwargs["message_thread_id"] = thread_id
    try:
        bot.send_message(
            chat_id,
            "⚠️ **ربات موقتاً توسط مدیریت خاموش است.**",
            **kwargs,
        )
        return True
    except Exception as exc:
        # Avoid logging the exception URL because Telegram URLs may contain the bot token.
        print(f"[Disabled Notice Delivery Warning] chat={key}: {type(exc).__name__}; Telegram API connection failed or timed out.")
        return False

def clean_channel_username(raw_ch):
    if not raw_ch:
        return ""
    clean = str(raw_ch).strip()
    clean = re.sub(r'^(https?://)?(www\.)?(t\.me/|telegram\.me/)', '', clean, flags=re.IGNORECASE)
    clean = clean.lstrip('@').strip().rstrip('/')
    return clean

def invalidate_sponsors_cache():
    global _SPONSORS_CACHE, _SPONSORS_CACHE_TIME
    _SPONSORS_CACHE = None
    _SPONSORS_CACHE_TIME = 0
    with _SPONSOR_JOIN_VERIFIED_LOCK:
        _SPONSOR_JOIN_VERIFIED_CACHE.clear()

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

def invalidate_models_cache():
    global _AI_MODELS_CACHE, _AI_MODELS_CACHE_TIME, _CODE_MODELS_CACHE, _CODE_MODELS_CACHE_TIME, _IMAGE_MODELS_CACHE, _IMAGE_MODELS_CACHE_TIME
    global _VIDEO_MODELS_CACHE, _VIDEO_MODELS_CACHE_TIME
    with _SELECTED_MODEL_DISPLAY_LOCK:
        _SELECTED_MODEL_DISPLAY_CACHE.clear()
    _AI_MODELS_CACHE = None
    _AI_MODELS_CACHE_TIME = 0
    _CODE_MODELS_CACHE = None
    _CODE_MODELS_CACHE_TIME = 0
    _IMAGE_MODELS_CACHE = None
    _IMAGE_MODELS_CACHE_TIME = 0
    _VIDEO_MODELS_CACHE = None
    _VIDEO_MODELS_CACHE_TIME = 0

def get_ai_models_cached():
    global _AI_MODELS_CACHE, _AI_MODELS_CACHE_TIME
    now = time.time()
    if _AI_MODELS_CACHE is not None and (now - _AI_MODELS_CACHE_TIME) < _MODEL_REGISTRY_CACHE_TTL:
        return _AI_MODELS_CACHE
    models = json.loads(safe_kv_get("AI_MODELS") or "[]")
    _AI_MODELS_CACHE = models
    _AI_MODELS_CACHE_TIME = now
    return models

def get_code_models_cached():
    """Dedicated programming-model registry; unlike chat models it is independently editable."""
    global _CODE_MODELS_CACHE, _CODE_MODELS_CACHE_TIME
    now = time.time()
    if _CODE_MODELS_CACHE is not None and (now - _CODE_MODELS_CACHE_TIME) < _MODEL_REGISTRY_CACHE_TTL:
        return _CODE_MODELS_CACHE
    try:
        raw = safe_kv_get("CODE_MODELS") or "[]"
        parsed = json.loads(raw)
        _CODE_MODELS_CACHE = parsed if isinstance(parsed, list) else []
    except Exception as exc:
        print(f"[Code Models Cache Error]: {exc}")
        _CODE_MODELS_CACHE = []
    _CODE_MODELS_CACHE_TIME = now
    return _CODE_MODELS_CACHE

def get_img_models_cached():
    global _IMAGE_MODELS_CACHE, _IMAGE_MODELS_CACHE_TIME
    now = time.time()
    if _IMAGE_MODELS_CACHE is not None and (now - _IMAGE_MODELS_CACHE_TIME) < _MODEL_REGISTRY_CACHE_TTL:
        return _IMAGE_MODELS_CACHE
    models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
    _IMAGE_MODELS_CACHE = models
    _IMAGE_MODELS_CACHE_TIME = now
    return models

def get_video_models_cached():
    global _VIDEO_MODELS_CACHE, _VIDEO_MODELS_CACHE_TIME
    now = time.time()
    if _VIDEO_MODELS_CACHE is not None and (now - _VIDEO_MODELS_CACHE_TIME) < _MODEL_REGISTRY_CACHE_TTL:
        return _VIDEO_MODELS_CACHE
    models = json.loads(safe_kv_get("VIDEO_MODELS") or "[]")
    if not isinstance(models, list):
        models = []
    _VIDEO_MODELS_CACHE = models
    _VIDEO_MODELS_CACHE_TIME = now
    return models


def warm_model_registry_cache():
    """Preload all model registries with one Redis MGET so the first menu opens quickly."""
    global _AI_MODELS_CACHE, _AI_MODELS_CACHE_TIME
    global _CODE_MODELS_CACHE, _CODE_MODELS_CACHE_TIME
    global _IMAGE_MODELS_CACHE, _IMAGE_MODELS_CACHE_TIME
    global _VIDEO_MODELS_CACHE, _VIDEO_MODELS_CACHE_TIME
    keys = ("AI_MODELS", "CODE_MODELS", "IMAGE_MODELS", "VIDEO_MODELS")
    values = batch_kv_get(keys)
    # Do not cache an apparent empty registry when Upstash is unreachable; otherwise
    # a transient startup network failure could hide configured models for two minutes.
    if not any(values.get(key) is not None for key in keys):
        raise RuntimeError("Upstash model registry warm-up returned no values")
    parsed = {}
    for key in keys:
        raw = values.get(key)
        try:
            value = json.loads(raw) if raw else []
        except (TypeError, ValueError, json.JSONDecodeError):
            value = []
        parsed[key] = value if isinstance(value, list) else []
    now = time.time()
    _AI_MODELS_CACHE, _AI_MODELS_CACHE_TIME = parsed["AI_MODELS"], now
    _CODE_MODELS_CACHE, _CODE_MODELS_CACHE_TIME = parsed["CODE_MODELS"], now
    _IMAGE_MODELS_CACHE, _IMAGE_MODELS_CACHE_TIME = parsed["IMAGE_MODELS"], now
    _VIDEO_MODELS_CACHE, _VIDEO_MODELS_CACHE_TIME = parsed["VIDEO_MODELS"], now
    return {key: len(value) for key, value in parsed.items()}

def invalidate_users_cache():
    global _ALL_USERS_CACHE, _ALL_USERS_CACHE_TIME
    _ALL_USERS_CACHE = None
    _ALL_USERS_CACHE_TIME = 0

# ==========================================
# 🌐 وب‌گردی بومیِ ارائه‌دهندهٔ API (بدون موتور جست‌وجوی جداگانه)
# ==========================================
def _model_supports_known_native_web_search(model_name, provider):
    """Conservative model-name check for native-search-capable model families."""
    name = str(model_name or "").strip().lower()
    if not name:
        return False
    if provider == "perplexity":
        return True  # Perplexity's public chat API is built around its search-capable models.
    if provider == "openai_responses":
        prefixes = ("gpt-4.1", "gpt-5", "gpt-6", "o3", "o4-mini")
        return name.startswith(prefixes) or any(f"/{prefix}" in name for prefix in prefixes)
    if provider == "xai_responses":
        return name.startswith("grok-4") or "/grok-4" in name
    if provider == "openrouter":
        # OpenRouter's native search support is provider/model dependent. Do not use
        # its fallback search engines for model IDs that aren't known to support native search.
        supported_fragments = (
            "openai/gpt-4.1", "openai/gpt-5", "openai/gpt-6", "openai/o3", "openai/o4-mini",
            "anthropic/claude-3.5-haiku", "anthropic/claude-3.7-sonnet", "anthropic/claude-4",
            "anthropic/claude-sonnet-4", "anthropic/claude-opus-4", "anthropic/claude-haiku-4",
            "google/gemini-3", "google/gemini-3.1", "google/gemini-3.5",
            "x-ai/grok-4", "perplexity/sonar", "perplexity/",
        )
        if any(fragment in name for fragment in supported_fragments):
            return True
        # Accommodate provider-prefixed-free model IDs when the OpenRouter endpoint is used.
        return name.startswith(("gpt-4.1", "gpt-5", "gpt-6", "o3", "o4-mini", "claude-3.5-haiku", "claude-3.7-sonnet", "claude-4", "gemini-3", "grok-4", "sonar"))
    return False


def get_native_web_provider(model):
    """Return a provider only when its API/model is known to support native web search.

    A standard chat-completions endpoint does not gain internet access from a prompt.
    Unknown API hosts and model families are treated as offline; there is no local search engine.
    """
    if not isinstance(model, dict):
        return None

    mode = str(model.get("nativeWebSearch", "auto")).strip().lower()
    if mode in {"off", "false", "0", "disabled", "none"}:
        return None

    base_url = str(model.get("baseUrl", "")).strip()
    model_name = str(model.get("modelName", "")).strip()
    try:
        host = (urllib.parse.urlparse(base_url).hostname or "").lower()
    except Exception:
        host = ""

    # Explicit provider override can be stored in model configuration for compatible proxies.
    if mode in {"openrouter", "openai_responses", "xai_responses", "perplexity"}:
        provider = mode
        return provider if _model_supports_known_native_web_search(model_name, provider) else None
    if host == "openrouter.ai" or host.endswith(".openrouter.ai"):
        return "openrouter" if _model_supports_known_native_web_search(model_name, "openrouter") else None
    if host == "api.openai.com":
        return "openai_responses" if _model_supports_known_native_web_search(model_name, "openai_responses") else None
    if host == "api.x.ai" or host.endswith(".x.ai"):
        return "xai_responses" if _model_supports_known_native_web_search(model_name, "xai_responses") else None
    if host == "api.perplexity.ai" or host.endswith(".perplexity.ai"):
        return "perplexity" if _model_supports_known_native_web_search(model_name, "perplexity") else None
    return None


def get_responses_endpoint(base_url):
    """Build a provider Responses API URL from common Base URL formats."""
    value = str(base_url or "").strip().rstrip("/")
    if value.endswith("/v1/responses"):
        return value
    if value.endswith("/chat/completions"):
        value = value[:-len("/chat/completions")]
    if value.endswith("/v1"):
        return value + "/responses"
    if "/v1/" in value:
        value = value.split("/v1/", 1)[0] + "/v1"
        return value + "/responses"
    return value + "/v1/responses"


def extract_native_citation_links(payload):
    """Extract citations returned by provider APIs without fetching/searching URLs."""
    found = []
    if not isinstance(payload, dict):
        return found

    def add(value):
        if isinstance(value, str):
            url = value.strip()
        elif isinstance(value, dict):
            url = str(value.get("url") or value.get("uri") or value.get("link") or "").strip()
        else:
            return
        if url.startswith(("https://", "http://")):
            try:
                if urllib.parse.urlparse(url).hostname:
                    found.append(url)
            except Exception:
                pass

    for citation in payload.get("citations", []) or []:
        add(citation)
    for item in payload.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        action = item.get("action", {}) or {}
        if isinstance(action, dict):
            for source in action.get("sources", []) or []:
                add(source)
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            for annotation in content.get("annotations", []) or []:
                add(annotation)
        for citation in item.get("citations", []) or []:
            add(citation)
    for choice in payload.get("choices", []) or []:
        if not isinstance(choice, dict):
            continue
        msg = choice.get("message", {}) or {}
        if isinstance(msg, dict):
            for citation in msg.get("citations", []) or []:
                add(citation)
            for annotation in msg.get("annotations", []) or []:
                add(annotation)
    return list(dict.fromkeys(found))[:6]


def parse_openai_responses_payload(payload):
    """Return output text and source URLs from an OpenAI Responses API response."""
    text_value = str(payload.get("output_text", "") or "").strip()
    if not text_value:
        chunks = []
        for item in payload.get("output", []) or []:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for part in item.get("content", []) or []:
                if isinstance(part, dict) and part.get("type") in {"output_text", "text"}:
                    part_text = str(part.get("text", "") or "").strip()
                    if part_text:
                        chunks.append(part_text)
        text_value = "\n\n".join(chunks).strip()
    return text_value, extract_native_citation_links(payload)


def explicit_web_search_requested(text):
    if not text:
        return False
    lowered = text.lower()
    terms = (
        "/web", "سرچ کن", "جستجو کن", "توی وب بگرد", "تو وب بگرد",
        "تو اینترنت بگرد", "توی اینترنت بگرد", "در سطح اینترنت",
        "از اینترنت", "آخرین اخبار", "آخرین نسخه", "قیمت امروز", "search online",
        "search the web", "browse the web", "look up online", "latest news",
        "current version", "as of today"
    )
    return any(term in lowered for term in terms)


def clean_extracted_image_prompt(p_text):
    if not p_text:
        return ""
    p = p_text.strip().lstrip(':').strip()
    p = re.sub(r'^(?:با\s+این\s+(?:پرامپت|مشخصات|توصیف|دستور)[:\s]*)+', '', p, flags=re.IGNORECASE)
    p = re.sub(r'^(?:که\s+توش|که\s+در\s+آن|شامل|از|یک|یه)\s+', '', p, flags=re.IGNORECASE)
    p = re.sub(r'\s+(?:بساز|بکش|طراحی\s+کن|درست\s+کن)$', '', p, flags=re.IGNORECASE)
    return p.strip() or p_text.strip()

def detect_and_extract_image_prompt(text):
    if not text:
        return False, ""
    clean = text.strip()
    lower = clean.lower()

    if is_explicit_code_request(clean) or any(g in lower for g in ['کد پایتون', 'اسکریپت', 'توضیح بده', 'ترجمه کن', 'مقاله بنویس', 'شعر بنویس']):
        return False, clean

    explicit_prefixes = ["/image", "/draw", "/img", "/photo", "عکس:", "تصویر:", "نقاشی:"]
    for ep in explicit_prefixes:
        if lower.startswith(ep):
            extracted = clean[len(ep):].strip()
            return True, clean_extracted_image_prompt(extracted)

    image_verbs = r'(?:بساز|بکش|طراحی\s+کن|نقاشی\s+کن|تولید\s+کن|تصویرسازی\s+کن|خلق\s+کن|ایجاد\s+کن)'
    image_nouns = r'(?:عکس|تصویر|نقاشی|طرح|پوستر|والپیپر|آرت|طراحی)'

    pattern_direct_noun = re.compile(
        rf'^(?:لطفاً|لطفا|بی\s+زحمت|برام|برای\s+من)?\s*(?:یه|یک|این)?\s*{image_nouns}\s+(?:از\s+)?(.*?)(?:\s+(?:رو|را))?(?:\s+{image_verbs})?$',
        flags=re.IGNORECASE | re.DOTALL
    )
    m1 = pattern_direct_noun.match(clean)
    if m1 and m1.group(1).strip():
        core = clean_extracted_image_prompt(m1.group(1))
        if len(core) >= 2:
            return True, core

    pattern_with_prompt = re.compile(
        rf'^(?:لطفاً|لطفا|بی\s+زحمت|برام|برای\s+من)?\s*(?:یه|یک|این)?\s*{image_nouns}\s*(?:رو|را)?\s*(?:با\s+این\s+(?:پرامپت|مشخصات|توصیف|دستور))?\s*{image_verbs}[:\s]*(.*)$',
        flags=re.IGNORECASE | re.DOTALL
    )
    m2 = pattern_with_prompt.match(clean)
    if m2 and m2.group(1).strip():
        core = clean_extracted_image_prompt(m2.group(1))
        if len(core) >= 2:
            return True, core

    en_triggers = ["draw ", "generate image", "create image", "create photo", "create picture", "image of "]
    for et in en_triggers:
        if et in lower:
            prompt = re.sub(r'^(?:please\s+)?(?:make|draw|paint|generate|create)\s+(?:a|an|the)?\s*(?:image|photo|picture)?\s*(?:of)?\s*', '', clean, flags=re.IGNORECASE)
            return True, prompt.strip() or clean

    return False, clean

# ==========================================
# 🧠 تشخیص دقیق و قطعی قصد کدنویسی
# ==========================================
def is_explicit_code_request(text):
    if not text:
        return False
    clean = text.strip()
    lower = clean.lower()

    capability_triggers = [
        'میتونی', 'می تونی', 'می‌تونی', 'میتونید', 'می‌تونید', 'بلدی', 'امکانش هست',
        'میشه', 'میشه برام', 'آیا میتونی', 'آیا بلدی', 'می شود', 'چطور میشه', 'چگونه'
    ]
    is_asking_ability = any(q in lower for q in capability_triggers) or ('؟' in clean or '?' in clean)
    
    if is_asking_ability:
        has_specific_task = any(tech in lower for tech in ['پایتون', 'جاوا', 'html', 'css', 'php', 'c++', 'sql', 'js', 'برام بنویس', 'رو بنویس'])
        if not has_specific_task:
            return False

    explicit_coding_phrases = [
        'سورس کد', 'کد پایتون', 'کد جاوا', 'کد html', 'کد css', 'کد php', 'کد js',
        'کد c++', 'کد نویسی', 'کدنویسی', 'اسکریپت پایتون', 'برنامه پایتون',
        'برنامه نویسی', 'دیباگ کن', 'باگ این کد', 'ارور این کد', 'خطای این کد',
        'تابع پایتون', 'الگوریتم پایتون', 'یک کد بنویس', 'کد زیر رو', 'کد زیر را'
    ]
    if any(phrase in lower for phrase in explicit_coding_phrases):
        return True

    has_exact_word_code = bool(re.search(r'(?:^|[\s\.,;:!؟])کد(?:$|[\s\.,;:!؟])', clean))
    if has_exact_word_code:
        coding_actions = ['بنویس', 'طراحی کن', 'درست کن', 'بزن', 'حل کن', 'دیباگ', 'پایتون', 'جاوا', 'ارور', 'باگ']
        if any(act in lower for act in coding_actions) and not is_asking_ability:
            return True

    return False

# ==========================================
# ⚡ سیستم کم‌مصرف CRM و مانیتورینگ کاربران ادمین
# ==========================================
def get_all_bot_users():
    global _ALL_USERS_CACHE, _ALL_USERS_CACHE_TIME
    now = time.time()
    if _ALL_USERS_CACHE is not None and (now - _ALL_USERS_CACHE_TIME) < 30:
        return _ALL_USERS_CACHE
    set_users = upstash_command(["SMEMBERS", "BOT_USERS_SET"]) or []
    all_u = list(set([str(u) for u in set_users if str(u).strip()]))
    _KNOWN_USERS_CACHE.update(all_u)
    _ALL_USERS_CACHE = all_u
    _ALL_USERS_CACHE_TIME = now
    return all_u

def batch_kv_get(keys, batch_size=100):
    """Fetch many Redis keys using MGET to avoid a slow GET request per user."""
    out = {}
    keys = list(keys or [])
    for start in range(0, len(keys), max(1, int(batch_size))):
        batch = keys[start:start + batch_size]
        try:
            values = upstash_command(["MGET"] + batch)
            if isinstance(values, list):
                for key, value in zip(batch, values):
                    out[key] = value
            else:
                for key in batch:
                    out[key] = None
        except Exception as exc:
            print(f"[MGET Error]: {exc}")
            for key in batch:
                out.setdefault(key, None)
    return out


def mark_user_unreachable(user_id, error):
    """Record only clear Telegram 'blocked/chat unavailable' errors, not every send failure."""
    desc = str(getattr(error, "description", "") or error or "").lower()
    patterns = (
        "bot was blocked by the user", "user is deactivated", "chat not found",
        "bot can't initiate conversation", "bot can't send messages to bots",
        "forbidden: the user", "peer_id_invalid"
    )
    if any(part in desc for part in patterns):
        upstash_command(["SADD", "BOT_UNREACHABLE_USERS_SET", str(user_id)])

def track_user_activity(user_id, first_name="", username=""):
    now = time.time()
    u_str = str(user_id)

    # Only one tracking job per user at a time. Normal consecutive messages do not
    # need a background thread or Redis writes until the 120-second activity interval expires.
    with _ACTIVITY_LOCK:
        need_sadd = u_str not in _KNOWN_USERS_CACHE
        need_active = (now - _LAST_ACTIVE_CACHE.get(u_str, 0)) > 120
        if not (need_sadd or need_active) or u_str in _TRACKING_USERS:
            return
        _TRACKING_USERS.add(u_str)

    def _worker():
        try:
            if need_sadd:
                upstash_command(["SADD", "BOT_USERS_SET", u_str])
                with _ACTIVITY_LOCK:
                    _KNOWN_USERS_CACHE.add(u_str)

            if need_active or need_sadd:
                safe_kv_put(f"LAST_ACTIVE_{u_str}", str(int(now * 1000)))
                with _ACTIVITY_LOCK:
                    _LAST_ACTIVE_CACHE[u_str] = now
                # If the user returned, clear any old unreachable marker.
                upstash_command(["SREM", "BOT_UNREACHABLE_USERS_SET", u_str])

                existing_info_raw = safe_kv_get(f"USER_INFO_{u_str}")
                info = {}
                if existing_info_raw:
                    try:
                        info = json.loads(existing_info_raw)
                    except Exception:
                        pass

                info["id"] = u_str
                if first_name:
                    info["name"] = first_name
                elif "name" not in info:
                    info["name"] = "کاربر"

                info["username"] = f"@{username}" if username else (info.get("username") or "ندارد")
                if "joined" not in info:
                    info["joined"] = get_jalali_date()

                safe_kv_put(f"USER_INFO_{u_str}", info)
        except Exception as e:
            print(f"[Track User Error]: {e}")
        finally:
            with _ACTIVITY_LOCK:
                _TRACKING_USERS.discard(u_str)

    threading.Thread(target=_worker, daemon=True, name=f"user-activity-{u_str}").start()

def clear_user_state(user_id):
    keys = [
        f"ADMIN_STEP_{user_id}", f"TEMP_MODEL_{user_id}",
        f"TEMP_IMG_{user_id}", f"TEMP_VIDEO_{user_id}", f"ADMIN_EDIT_IDX_{user_id}",
        f"ADMIN_EDIT_IMG_IDX_{user_id}", f"USER_SUPPORT_STEP_{user_id}",
        f"AWAITING_IMG_{user_id}", f"USER_MODE_{user_id}",
        f"VIDEO_PROMPT_AWAITING_{user_id}"
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
    if str(user_id) == str(ADMIN_ID):
        return True, []
    uid = str(user_id)
    now = time.monotonic()
    with _SPONSOR_JOIN_VERIFIED_LOCK:
        checked_at = _SPONSOR_JOIN_VERIFIED_CACHE.get(uid)
        if checked_at is not None and (now - checked_at) < _SPONSOR_JOIN_VERIFIED_TTL:
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

    if not unjoined:
        with _SPONSOR_JOIN_VERIFIED_LOCK:
            _SPONSOR_JOIN_VERIFIED_CACHE[uid] = time.monotonic()
            if len(_SPONSOR_JOIN_VERIFIED_CACHE) > 10000:
                cutoff = time.monotonic() - (_SPONSOR_JOIN_VERIFIED_TTL * 3)
                for cached_uid, cached_time in list(_SPONSOR_JOIN_VERIFIED_CACHE.items()):
                    if cached_time < cutoff:
                        _SPONSOR_JOIN_VERIFIED_CACHE.pop(cached_uid, None)
    else:
        with _SPONSOR_JOIN_VERIFIED_LOCK:
            _SPONSOR_JOIN_VERIFIED_CACHE.pop(uid, None)
    return len(unjoined) == 0, unjoined

MAX_SAVED_SESSIONS = 7
_NEW_CHAT_TITLES = {"گفتگوی جدید 💬", "New Chat 💬", "گفتگوی جدید", "New Chat"}

def load_user_sessions(user_id):
    try:
        sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
        return [x for x in sessions if isinstance(x, dict) and x.get("id")] if isinstance(sessions, list) else []
    except Exception:
        return []

_ACTIVE_SESSION_NOT_PROVIDED = object()

def save_sessions_limited(user_id, sessions, limit=MAX_SAVED_SESSIONS, active_id=_ACTIVE_SESSION_NOT_PROVIDED):
    """Persist newest-first session metadata and remove history for sessions beyond the cap."""
    cleaned = []
    seen = set()
    for item in sessions or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        sid = str(item.get("id"))
        if sid in seen:
            continue
        item = dict(item)
        item["id"] = sid
        cleaned.append(item)
        seen.add(sid)
    # Keep the current active chat near the top so it is not removed when pruning old records.
    if active_id is _ACTIVE_SESSION_NOT_PROVIDED:
        active_id = safe_kv_get(f"ACTIVE_SESSION_{user_id}")
    active_id = str(active_id or "")
    if active_id:
        active_pos = next((i for i, item in enumerate(cleaned) if item["id"] == active_id), None)
        if active_pos is not None and active_pos > 0:
            cleaned.insert(0, cleaned.pop(active_pos))
    kept = cleaned[:max(1, int(limit))]
    keep_ids = {x["id"] for x in kept}
    for old_item in cleaned[len(kept):]:
        old_sid = str(old_item.get("id") or "")
        if old_sid and old_sid not in keep_ids:
            safe_kv_delete(f"HISTORY_{user_id}_{old_sid}")
    safe_kv_put(f"SESSIONS_{user_id}", kept)
    return kept

def create_new_session(user_id):
    # Nanosecond timestamp avoids collisions when the user taps New Chat rapidly.
    new_id = f"sess_{time.time_ns()}"
    sessions = load_user_sessions(user_id)
    sessions.insert(0, make_session_record(new_id))
    safe_kv_put(f"ACTIVE_SESSION_{user_id}", new_id)
    save_sessions_limited(user_id, sessions, active_id=new_id)
    _set_active_session_cache(user_id, new_id)
    return new_id

def get_or_create_active_session(user_id):
    # Most messages belong to the same active session; avoid re-reading and re-writing
    # SESSIONS metadata on every prompt. New/switch/delete operations update this cache.
    cached_id = _get_active_session_cache(user_id)
    if cached_id:
        return str(cached_id)

    active_id = safe_kv_get(f"ACTIVE_SESSION_{user_id}")
    if active_id:
        _set_active_session_cache(user_id, active_id)
        return str(active_id)

    sessions = load_user_sessions(user_id)
    if sessions:
        active_id = str(sessions[0]["id"])
    else:
        active_id = f"sess_{time.time_ns()}"
        sessions.insert(0, make_session_record(active_id))
    safe_kv_put(f"ACTIVE_SESSION_{user_id}", active_id)
    save_sessions_limited(user_id, sessions, active_id=active_id)
    _set_active_session_cache(user_id, active_id)
    return str(active_id)

def update_session_title_if_new(user_id, session_id, first_msg):
    sessions = load_user_sessions(user_id)
    changed = False
    clean_title = " ".join(str(first_msg or "").split()).strip()
    if not clean_title:
        return
    # Keep the title compact and safe to display in Telegram buttons.
    clean_title = clean_title[:38].rstrip()
    if len(" ".join(str(first_msg or "").split())) > 38:
        clean_title += "…"
    for item in sessions:
        if str(item.get("id")) == str(session_id) and str(item.get("title") or "") in _NEW_CHAT_TITLES:
            item["title"] = clean_title
            changed = True
            break
    if changed:
        save_sessions_limited(user_id, sessions)

def chunk_string(s, size=4000):
    return [s[i:i + size] for i in range(0, len(s), size)]

def send_safe_ai_response(chat_id, message_id, text, reply_to_id=None, thread_id=None):
    if message_id is None:
        kwargs = {}
        if reply_to_id:
            kwargs["reply_to_message_id"] = reply_to_id
            kwargs["allow_sending_without_reply"] = True
        if thread_id:
            kwargs["message_thread_id"] = thread_id
        try:
            bot.send_message(chat_id, text[:4000], **kwargs)
        except Exception as exc:
            print(f"[AI Final Send Error] chat={chat_id}: {type(exc).__name__}")
        return
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
            if len(clean_code) < 180 and clean_code.count('\n') < 8:
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

def _keyboard_callback_values(markup):
    """Extract callback_data from a Telegram inline markup object."""
    values = []
    for row in getattr(markup, "keyboard", []) or []:
        for button in row or []:
            callback_data = getattr(button, "callback_data", None)
            if callback_data is not None:
                values.append(str(callback_data))
    return values


def _callback_route_rules():
    """Read dispatcher conditions so the self-test can detect buttons with no route."""
    exact = set()
    prefixes = set()
    source = inspect.getsource(_handle_callbacks_impl)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "data":
            for op, comp in zip(node.ops, node.comparators):
                if isinstance(op, ast.Eq) and isinstance(comp, ast.Constant) and isinstance(comp.value, str):
                    exact.add(comp.value)
                elif isinstance(op, ast.In) and isinstance(comp, (ast.List, ast.Tuple, ast.Set)):
                    exact.update(elt.value for elt in comp.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and node.func.value.id == "data"
                    and node.func.attr == "startswith" and node.args
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                prefixes.add(node.args[0].value)
        elif isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if names.intersection({"group_allowed_actions", "pv_only"}) and isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                exact.update(elt.value for elt in node.value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str))
    return exact, prefixes


def _callback_route_known(callback_data, exact_routes, prefixes):
    return callback_data in exact_routes or any(callback_data.startswith(prefix) for prefix in prefixes)


def run_admin_self_tests():
    """Run bounded, non-destructive system checks; never prints secrets or calls paid AI models."""
    checks = []
    def record(label, status, detail):
        checks.append((label, status, str(detail)))

    # Telegram Bot API reachability and bot identity.
    try:
        info = get_bot_info_cached(force_refresh=True)
        record("اتصال Telegram API", "PASS", f"ربات @{getattr(info, 'username', '') or 'بدون‌نام'} پاسخ داد")
    except Exception as exc:
        # Exception messages may contain the Telegram bot token in a request URL. Never print it.
        safe_detail = str(exc)
        if BOT_TOKEN:
            safe_detail = safe_detail.replace(str(BOT_TOKEN), "[REDACTED_TOKEN]")
        safe_detail = re.sub(r"(/bot)[^/]+(/)", r"\1[REDACTED]\2", safe_detail)
        record("اتصال Telegram API", "FAIL", f"{type(exc).__name__}: {safe_detail[:120]}")

    # Upstash REST connectivity.
    try:
        pong = upstash_command(["PING"])
        if str(pong).upper() == "PONG":
            record("اتصال Upstash Redis", "PASS", "PING / PONG موفق")
        else:
            record("اتصال Upstash Redis", "FAIL", f"پاسخ غیرمنتظره: {str(pong)[:100]}")
    except Exception as exc:
        record("اتصال Upstash Redis", "FAIL", f"{type(exc).__name__}: {str(exc)[:150]}")

    # Model registries: JSON shape and required record shape only; no provider token is displayed.
    registry_keys = ["AI_MODELS", "CODE_MODELS", "IMAGE_MODELS", "VIDEO_MODELS"]
    try:
        registry_raw = batch_kv_get(registry_keys)
    except Exception as exc:
        registry_raw = {}
        record("خواندن فهرست مدل‌ها", "FAIL", f"{type(exc).__name__}: {str(exc)[:120]}")
    registry_counts = {}
    registry_lists = {}
    for key in registry_keys:
        raw = registry_raw.get(key)
        try:
            items = json.loads(raw or "[]")
            if not isinstance(items, list):
                raise ValueError("ریشه JSON باید فهرست باشد")
            malformed = sum(1 for item in items if not isinstance(item, dict))
            registry_counts[key] = len(items)
            registry_lists[key] = [item for item in items if isinstance(item, dict)]
            if malformed:
                record(f"ساختار {key}", "FAIL", f"{malformed} مورد از نوع دیکشنری نیست")
            elif not items and key == "AI_MODELS":
                record(f"ساختار {key}", "WARN", "مدل چت ثبت نشده؛ پاسخ‌گویی AI ممکن نیست")
            elif not items:
                record(f"ساختار {key}", "WARN", "در این دسته مدلی ثبت نشده است")
            else:
                record(f"ساختار {key}", "PASS", f"{len(items)} مدل/رکورد با JSON معتبر")
        except Exception as exc:
            registry_counts[key] = 0
            registry_lists[key] = []
            record(f"ساختار {key}", "FAIL", f"JSON نامعتبر: {str(exc)[:100]}")

    # Verify Telegram handlers are registered.
    try:
        callback_handlers = getattr(bot, "callback_query_handlers", [])
        message_handlers = getattr(bot, "message_handlers", [])
        callback_ok = bool(callback_handlers)
        message_ok = bool(message_handlers)
        record("ثبت هندلر دکمه‌های شیشه‌ای", "PASS" if callback_ok else "FAIL", f"{len(callback_handlers)} هندلر callback")
        record("ثبت هندلر پیام‌ها", "PASS" if message_ok else "FAIL", f"{len(message_handlers)} هندلر پیام")
    except Exception as exc:
        record("ثبت هندلرها", "FAIL", f"{type(exc).__name__}: {str(exc)[:100]}")

    # Test the very same group-call parser used by the message handler.
    try:
        try:
            test_username = getattr(get_bot_info_cached(), "username", "") or "NeoTenetBot"
        except Exception:
            test_username = "NeoTenetBot"
        samples = [
            ("نئو سلام", "سلام"),
            ("نئو-سلام", "سلام"),
            ("نعو - سلام", "سلام"),
            ("neo-hello", "hello"),
            ("Neo: hello", "hello"),
            ("NEO - hello", "hello"),
            ("ربات سلام", "سلام"),
            ("ربات: سلام", "سلام"),
            ("بات سلام", "سلام"),
            ("بات، سلام", "سلام"),
            ("tenet, hi", "hi"),
            (f"@{test_username} سلام", "سلام"),
        ]
        failed_samples = []
        for sample, expected in samples:
            invoked, prompt = extract_group_invocation(sample, test_username)
            if not invoked or prompt.strip().lower() != expected.lower():
                failed_samples.append(sample)
        record("تشخیص فراخوانی گروه/منشن", "PASS" if not failed_samples else "FAIL",
               "۱۲ نمونه موفق" if not failed_samples else "نمونه ناموفق: " + ", ".join(failed_samples))
    except Exception as exc:
        record("تشخیص فراخوانی گروه/منشن", "FAIL", f"{type(exc).__name__}: {str(exc)[:100]}")
    record("پیش‌نیاز فراخوانی با کلمات ساده در گروه", "INFO",
           "اگر کلماتی مثل «نئو/ربات» به ربات نمی‌رسند، در BotFather دستور /setprivacy را برای همین ربات روی Disable قرار بده؛ وضعیت Privacy Mode از Bot API قابل بررسی مستقیم نیست.")

    # Safe streaming preview must never expose an unfinished or completed internal <think> block.
    try:
        preview_cases = [
            ("پاسخ عادی", "سلام دنیا", "سلام دنیا"),
            ("فیلتر فکر کامل", "پاسخ <think>متن داخلی</think> نهایی", "پاسخ نهایی"),
            ("فیلتر فکر ناقص", "پاسخ قابل نمایش <think>متن داخلی", "پاسخ قابل نمایش"),
        ]
        failed_preview = [name for name, raw, expected in preview_cases if _safe_stream_preview(raw) != expected]
        record("امنیت پیش‌نمایش تدریجی پاسخ گروه", "FAIL" if failed_preview else "PASS",
               "نمونه ناموفق: " + ", ".join(failed_preview) if failed_preview else "۳ نمونه؛ متن داخلی <think> نمایش داده نمی‌شود")
    except Exception as exc:
        record("امنیت پیش‌نمایش تدریجی پاسخ گروه", "FAIL", f"{type(exc).__name__}: {str(exc)[:100]}")

    # Controlled burst test: enqueue harmless work directly into each worker pool.
    # These are not AI requests and do not use external services or credits.
    for label, executor, worker_count in (
        ("صف چت و کدنویسی خصوصی", _AI_JOB_EXECUTOR, AI_JOB_WORKERS),
        ("صف پاسخ متنی گروه", _GROUP_AI_JOB_EXECUTOR, GROUP_AI_JOB_WORKERS),
        ("صف callback", _CALLBACK_EXECUTOR, CALLBACK_WORKERS),
        ("صف ساخت تصویر", _IMAGE_JOB_EXECUTOR, IMAGE_JOB_WORKERS),
        ("صف ساخت ویدیو", _VIDEO_JOB_EXECUTOR, VIDEO_JOB_WORKERS),
    ):
        try:
            probe_count = min(24, max(4, int(worker_count) * 2))
            futures = [executor.submit(lambda value=index: value * value) for index in range(probe_count)]
            results = [future.result(timeout=5) for future in futures]
            expected = [index * index for index in range(probe_count)]
            valid = results == expected
            record(label, "PASS" if valid else "FAIL",
                   f"{probe_count} کار سبک صف شد و {'کامل' if valid else 'ناقص'} اجرا شد؛ بدون درخواست AI واقعی")
        except Exception as exc:
            record(label, "FAIL", f"{type(exc).__name__}: {str(exc)[:120]}")

    # Build the same production keyboards and perform a non-destructive route walk.
    # This does not send test messages, alter real user data, or call paid AI services.
    try:
        test_uid = str(ADMIN_ID)
        test_target = f"__neo_selftest_{threading.get_ident()}__"
        old_lang = _USER_LANG_CACHE.get(test_uid)
        had_lang = test_uid in _USER_LANG_CACHE
        _USER_LANG_CACHE[test_uid] = "fa"
        _USER_MODES_CACHE[test_target] = "CHAT"
        _USER_MODES_CACHE[test_target + "_group"] = "CHAT"

        model_fixture = [{"name": "Self Test Model", "modelName": "self-test", "supportsVision": True}]
        chat_models = registry_lists.get("AI_MODELS", [])
        code_models = registry_lists.get("CODE_MODELS", [])
        image_models = registry_lists.get("IMAGE_MODELS", [])
        video_models = registry_lists.get("VIDEO_MODELS", [])
        override_models = {
            "chat": chat_models or model_fixture,
            "code": code_models or chat_models or model_fixture,
            "image": image_models or model_fixture,
            "video": video_models or model_fixture,
        }
        hub_state = {
            f"USER_MODEL_{test_target}": "0", f"USER_CODE_MODEL_{test_target}": "0",
            f"USER_IMG_MODEL_{test_target}": "0", f"USER_VIDEO_MODEL_{test_target}": "0",
        }

        history_fixture = [{"id": "selftest_session", "title": "تست منو", "date": get_jalali_date()}]
        history_text, history_markup = build_history_menu_markup(test_uid, history_fixture, "selftest_session")
        hub_text, hub_markup = build_models_hub_menu(test_target, False, override_models, hub_state)
        group_hub_text, group_hub_markup = build_models_hub_menu(test_target + "_group", True, override_models, hub_state)

        menus = [
            ("منوی اصلی", get_main_menu_markup(test_uid, "CHAT")),
            ("پنل ادمین", get_admin_panel_markup()),
            ("هاب مدل‌ها", hub_markup),
            ("هاب مدل‌های گروه", group_hub_markup),
            ("مدل چت", build_model_selection_markup(test_target, models=override_models["chat"], current_idx="0")),
            ("مدل کدنویسی", build_model_selection_markup(test_target, models=override_models["code"], current_idx="0", is_code_category=True)),
            ("مدل عکس", build_image_model_selection_markup(test_target, img_models=override_models["image"], current_idx="0")),
            ("مدل ویدیو", build_video_model_selection_markup(test_target, video_models=override_models["video"], current_idx="0")),
            ("تاریخچه", history_markup),
            ("انتخاب زبان", build_lang_selection_markup(test_uid)),
            ("لغو عملیات ادمین", get_admin_cancel_markup()),
            ("عضویت اسپانسر", build_sponsor_markup(test_uid, ["neotenet"])),
        ]
        exact_routes, prefixes = _callback_route_rules()
        all_buttons = 0
        missing_routes = []
        overlong_callbacks = []
        for menu_name, menu_markup in menus:
            values = _keyboard_callback_values(menu_markup)
            all_buttons += len(values)
            for value in values:
                if not _callback_route_known(value, exact_routes, prefixes):
                    missing_routes.append(f"{menu_name}:{value}")
                if len(value.encode("utf-8")) > 64:
                    overlong_callbacks.append(f"{menu_name}:{value[:30]}")
            record(f"ساخت منوی {menu_name}", "PASS" if menu_markup is not None else "FAIL",
                   f"{len(values)} callback ساخته شد")

        record("مسیریابی خودکار دکمه‌ها", "PASS" if not missing_routes else "FAIL",
               f"{all_buttons} دکمه در {len(menus)} منو بررسی شد؛ " +
               ("همه callbackها مسیر شناخته‌شده دارند" if not missing_routes else "بدون مسیر: " + ", ".join(missing_routes[:8])))
        record("محدودیت callback تلگرام", "PASS" if not overlong_callbacks else "FAIL",
               "همه callback_dataها حداکثر ۶۴ بایت‌اند" if not overlong_callbacks else "بیش از حد: " + ", ".join(overlong_callbacks[:5]))

        # Model the common menu-to-submenu walk; each transition must be routable and its target menu buildable.
        navigation_pairs = [
            ("منوی اصلی → هاب مدل‌ها", "models_hub", hub_markup),
            ("هاب مدل‌ها → مدل چت", "models_cat_chat", build_model_selection_markup(test_target, models=override_models["chat"], current_idx="0")),
            ("هاب مدل‌ها → مدل کدنویسی", "models_cat_code", build_model_selection_markup(test_target, models=override_models["code"], current_idx="0", is_code_category=True)),
            ("هاب مدل‌ها → مدل عکس", "models_cat_image", build_image_model_selection_markup(test_target, img_models=override_models["image"], current_idx="0")),
            ("هاب مدل‌ها → مدل ویدیو", "models_cat_video", build_video_model_selection_markup(test_target, video_models=override_models["video"], current_idx="0")),
            ("منوی اصلی → تاریخچه", "history_menu", history_markup),
            ("منوی اصلی → پنل ادمین", "admin_panel", get_admin_panel_markup()),
            ("پنل ادمین → تست سلامت", "admin_self_test", get_admin_panel_markup()),
        ]
        broken_walk = [name for name, callback, target_markup in navigation_pairs
                       if not _callback_route_known(callback, exact_routes, prefixes) or target_markup is None]
        record("گردش خودکار بین زیرمنوها", "PASS" if not broken_walk else "FAIL",
               f"{len(navigation_pairs)} مسیر بررسی شد؛ بدون ارسال پیام آزمایشی یا تغییر داده واقعی" +
               ("" if not broken_walk else "; مشکل: " + ", ".join(broken_walk)))
    except Exception as exc:
        record("تست خودکار منوها و دکمه‌ها", "FAIL", f"{type(exc).__name__}: {str(exc)[:160]}")
    finally:
        try:
            if 'test_uid' in locals():
                if had_lang:
                    _USER_LANG_CACHE[test_uid] = old_lang
                else:
                    _USER_LANG_CACHE.pop(test_uid, None)
            if 'test_target' in locals():
                _USER_MODES_CACHE.pop(test_target, None)
                _USER_MODES_CACHE.pop(test_target + "_group", None)
        except Exception:
            pass

    # Capacity snapshot, not a performance guarantee.
    try:
        ai_waiting = getattr(getattr(_AI_JOB_EXECUTOR, "_work_queue", None), "qsize", lambda: -1)()
        group_ai_waiting = getattr(getattr(_GROUP_AI_JOB_EXECUTOR, "_work_queue", None), "qsize", lambda: -1)()
        callback_waiting = getattr(getattr(_CALLBACK_EXECUTOR, "_work_queue", None), "qsize", lambda: -1)()
        image_waiting = getattr(getattr(_IMAGE_JOB_EXECUTOR, "_work_queue", None), "qsize", lambda: -1)()
        video_waiting = getattr(getattr(_VIDEO_JOB_EXECUTOR, "_work_queue", None), "qsize", lambda: -1)()
        record("ظرفیت پردازش (نمای لحظه‌ای)", "INFO",
               f"Handler={TELEGRAM_HANDLER_THREADS} | Callback={CALLBACK_WORKERS}+{CALLBACK_QUEUE_LIMIT} | "
               f"Chat/Code={AI_JOB_WORKERS}+{AI_JOB_QUEUE_LIMIT} | Group={GROUP_AI_JOB_WORKERS}+{GROUP_AI_JOB_QUEUE_LIMIT} | "
               f"Image={IMAGE_JOB_WORKERS}+{IMAGE_JOB_QUEUE_LIMIT} | Video={VIDEO_JOB_WORKERS}+{VIDEO_JOB_QUEUE_LIMIT} | "
               f"صف فعلی callback={callback_waiting}، چت={ai_waiting}، گروه={group_ai_waiting}، عکس={image_waiting}، ویدیو={video_waiting}")
    except Exception as exc:
        record("ظرفیت پردازش", "WARN", f"قابل خواندن نیست: {type(exc).__name__}")

    passed = sum(1 for _, status, _ in checks if status == "PASS")
    failed = sum(1 for _, status, _ in checks if status == "FAIL")
    warnings = sum(1 for _, status, _ in checks if status == "WARN")
    lines = [
        "🧪 گزارش تست سلامت ربات Neo AI",
        f"نتیجه: ✅ {passed} موفق | ❌ {failed} خطا | ⚠️ {warnings} هشدار",
        "",
    ]
    icons = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️"}
    for label, status, detail in checks:
        lines.append(f"{icons.get(status, 'ℹ️')} {label}: {detail}")
    lines.extend([
        "",
        "محدودیت تست: منوها و مسیرهای callback به‌صورت داخلی و بدون دست‌کاری اطلاعات واقعی شبیه‌سازی می‌شوند؛ از مدل‌ها درخواست پولی ارسال نمی‌شود. تست مسیر منو، اتصال شبکه یا پاسخ واقعی همه سرویس‌ها را تضمین نمی‌کند. درخواست‌های متنی گروه صف مجزایی دارند و پاسخ استریم‌شده در گروه به‌صورت تدریجی نمایش داده می‌شود.",
    ])
    return "\n".join(lines), {"passed": passed, "failed": failed, "warnings": warnings}


# ==========================================
# ۱. رابط کاربری ۳ حالته و تفکیک‌شده دو زبانه
# ==========================================
def get_user_current_mode(target_key_id):
    if target_key_id in _USER_MODES_CACHE:
        return _USER_MODES_CACHE[target_key_id]
    mode = safe_kv_get(f"BOT_MODE_{target_key_id}")
    if mode not in ["CHAT", "CODE", "IMAGE", "VIDEO"]:
        mode = "CHAT"
    _USER_MODES_CACHE[target_key_id] = mode
    return mode

def get_main_menu_markup(user_id, current_mode="CHAT"):
    """Main menu: everyday AI modes plus a dedicated submenu for independent tools."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    chat_lbl = f"✅ {tr(user_id, 'btn_chat')}" if current_mode == "CHAT" else tr(user_id, 'btn_chat')
    code_lbl = f"✅ {tr(user_id, 'btn_code')}" if current_mode == "CODE" else tr(user_id, 'btn_code')
    img_lbl  = f"✅ {tr(user_id, 'btn_img')}" if current_mode == "IMAGE" else tr(user_id, 'btn_img')

    markup.add(
        types.InlineKeyboardButton(chat_lbl, callback_data="switch_mode_chat", style="primary"),
        types.InlineKeyboardButton(code_lbl, callback_data="switch_mode_code", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton(img_lbl, callback_data="switch_mode_image", style="success"),
        types.InlineKeyboardButton(tr(user_id, 'btn_video'), callback_data="video_prompt_start", style="success")
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


def get_persistent_menu_markup(user_id):
    """A normal Telegram reply keyboard shown under the chat alongside inline glass buttons."""
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True, row_width=2)
    except TypeError:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if get_user_lang(user_id) == "fa":
        markup.row(types.KeyboardButton("📋 منوی اصلی"), types.KeyboardButton("📜 تاریخچه گفتگوها"))
        if str(user_id) == str(ADMIN_ID):
            markup.row(types.KeyboardButton("⚙️ مدیریت ربات"))
    else:
        markup.row(types.KeyboardButton("📋 Main Menu"), types.KeyboardButton("📜 Chat History"))
        if str(user_id) == str(ADMIN_ID):
            markup.row(types.KeyboardButton("⚙️ Admin Panel"))
    return markup

def _escape_markdown_value(value):
    """Keep a model name safe inside a Markdown inline-code span."""
    # The model name is rendered between backticks, so escaping underscores would
    # show unwanted backslashes. Replace only embedded backticks/newlines instead.
    clean = re.sub(r"[\r\n]+", " ", str(value or "").strip())
    return clean.replace("`", "ˋ")


def _cache_selected_model_display_name(user_id, mode, name, lang=None):
    lang_key = lang or _USER_LANG_CACHE.get(str(user_id), "fa")
    result = _escape_markdown_value(name) if name else ("انتخاب نشده" if lang_key == "fa" else "Not selected")
    cache_key = (str(user_id), str(mode), lang_key)
    with _SELECTED_MODEL_DISPLAY_LOCK:
        _SELECTED_MODEL_DISPLAY_CACHE[cache_key] = (time.monotonic(), result)
    return result


def get_selected_model_display_name(user_id, current_mode=None):
    """Return the selected model name with short caching to keep menu edits responsive."""
    mode = current_mode or get_user_current_mode(user_id)
    lang = get_user_lang(user_id)
    lang_fallback = "انتخاب نشده" if lang == "fa" else "Not selected"
    cache_key = (str(user_id), str(mode), lang)
    now = time.monotonic()
    with _SELECTED_MODEL_DISPLAY_LOCK:
        cached = _SELECTED_MODEL_DISPLAY_CACHE.get(cache_key)
        if cached and (now - cached[0]) < _SELECTED_MODEL_DISPLAY_TTL:
            return cached[1]

    if mode == "CHAT":
        models = get_ai_models_cached() or []
        index_key = f"USER_MODEL_{user_id}"
    elif mode == "CODE":
        models = get_code_models_cached() or []
        index_key = f"USER_CODE_MODEL_{user_id}"
        if not models:
            models = get_ai_models_cached() or []
            index_key = f"USER_MODEL_{user_id}"
    elif mode == "IMAGE":
        models = get_img_models_cached() or []
        index_key = f"USER_IMG_MODEL_{user_id}"
    elif mode == "VIDEO":
        models = get_video_models_cached() or []
        index_key = f"USER_VIDEO_MODEL_{user_id}"
    else:
        return "نامشخص" if lang == "fa" else "Unknown"

    index_raw = _model_selection_get_cached(index_key)
    if index_raw is None:
        index_raw = safe_kv_get(index_key) or "0"
        with _MODEL_SELECTION_CACHE_LOCK:
            _MODEL_SELECTION_CACHE[index_key] = (time.monotonic(), str(index_raw))
    if not models:
        return _cache_selected_model_display_name(user_id, mode, None, lang)
    try:
        idx = int(index_raw)
    except (TypeError, ValueError):
        idx = 0
    if idx < 0 or idx >= len(models):
        idx = 0
    model = models[idx] if isinstance(models[idx], dict) else {}
    name = model.get("name") or model.get("modelName") or model.get("model")
    return _cache_selected_model_display_name(user_id, mode, name, lang) if name else _cache_selected_model_display_name(user_id, mode, None, lang)


def build_main_menu_welcome_text(user_id, current_mode=None):
    mode = current_mode or get_user_current_mode(user_id)
    mode_key_map = {"CHAT": "mode_chat_name", "CODE": "mode_code_name", "IMAGE": "mode_image_name", "VIDEO": "mode_video_name"}
    mode_text = tr(user_id, mode_key_map.get(mode, "mode_chat_name"))
    model_name = get_selected_model_display_name(user_id, mode)
    return tr(user_id, "welcome", mode=mode_text, model_name=model_name)


def refresh_main_menu_banner(chat_id, user_id, message_id=None):
    """Edit the stored welcome/menu banner in place when the mode/model changes."""
    if str(chat_id) != str(user_id):
        return False  # private welcome banners are never edited from group callbacks
    if message_id is None:
        with _MAIN_MENU_MESSAGE_ID_LOCK:
            message_id = _MAIN_MENU_MESSAGE_ID_CACHE.get(str(user_id))
        if not message_id:
            raw_id = safe_kv_get(f"MAIN_MENU_MESSAGE_ID_{user_id}")
            try:
                message_id = int(raw_id) if raw_id else None
            except (TypeError, ValueError):
                message_id = None
            if message_id:
                with _MAIN_MENU_MESSAGE_ID_LOCK:
                    _MAIN_MENU_MESSAGE_ID_CACHE[str(user_id)] = int(message_id)
    if not message_id:
        return False
    mode = get_user_current_mode(user_id)
    try:
        bot.edit_message_text(
            build_main_menu_welcome_text(user_id, mode),
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="Markdown",
            reply_markup=get_main_menu_markup(user_id, mode),
        )
        with _MAIN_MENU_MESSAGE_ID_LOCK:
            _MAIN_MENU_MESSAGE_ID_CACHE[str(user_id)] = int(message_id)
        return True
    except Exception as exc:
        if "message is not modified" in str(exc).lower():
            with _MAIN_MENU_MESSAGE_ID_LOCK:
                _MAIN_MENU_MESSAGE_ID_CACHE[str(user_id)] = int(message_id)
            return True
        print(f"[Main Menu Banner Refresh Error]: {exc}")
        return False


def send_main_menu(chat_id, user_id, message_id=None):
    current_mode = get_user_current_mode(user_id)
    welcome_text = build_main_menu_welcome_text(user_id, current_mode)
    if message_id:
        try:
            bot.edit_message_text(
                welcome_text,
                chat_id=chat_id,
                message_id=message_id,
                parse_mode="Markdown",
                reply_markup=get_main_menu_markup(user_id, current_mode),
            )
            with _MAIN_MENU_MESSAGE_ID_LOCK:
                _MAIN_MENU_MESSAGE_ID_CACHE[str(user_id)] = int(message_id)
            return
        except Exception:
            # Fall back to a new menu if the clicked message cannot be edited.
            pass
    # Telegram cannot attach a ReplyKeyboardMarkup and an InlineKeyboardMarkup to one message.
    # Send them as two messages: persistent bottom buttons + the existing inline menu.
    bot.send_message(
        chat_id,
        "⌨️ از دکمه‌های ثابت پایین چت برای بازکردن منو و تاریخچه استفاده کن." if get_user_lang(user_id) == "fa" else "⌨️ Use the fixed buttons below the chat to open the menu and history.",
        reply_markup=get_persistent_menu_markup(user_id),
    )
    menu_message = bot.send_message(
        chat_id,
        welcome_text,
        parse_mode="Markdown",
        reply_markup=get_main_menu_markup(user_id, current_mode),
    )
    try:
        with _MAIN_MENU_MESSAGE_ID_LOCK:
            _MAIN_MENU_MESSAGE_ID_CACHE[str(user_id)] = int(menu_message.message_id)
        _persist_kv_async(f"MAIN_MENU_MESSAGE_ID_{user_id}", str(menu_message.message_id))
    except Exception as exc:
        print(f"[Main Menu Message Save Error]: {type(exc).__name__}")

def build_lang_selection_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="set_lang_fa", style="primary"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en", style="primary")
    )
    markup.add(types.InlineKeyboardButton("🔙 بازگشت / Back", callback_data="main_menu"))
    return markup


def send_lang_selection_menu(chat_id, user_id, message_id=None):
    markup = build_lang_selection_markup(user_id)
    text = tr(user_id, "lang_select_title")
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def build_sponsor_markup(user_id, unjoined_channels):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch in unjoined_channels:
        clean_ch = clean_channel_username(ch)
        btn_label = tr(user_id, "sponsor_btn", ch=clean_ch)
        btn_url = f"https://t.me/{clean_ch}"
        markup.add(types.InlineKeyboardButton(btn_label, url=btn_url))
    markup.add(types.InlineKeyboardButton(tr(user_id, "sponsor_check_btn"), callback_data="check_sponsor", style="success"))
    return markup

def build_history_menu_markup(user_id, sessions, active_sess):
    """Build the real history-menu keyboard without performing writes or sending messages."""
    markup = types.InlineKeyboardMarkup()
    for session in (sessions or [])[:MAX_SAVED_SESSIONS]:
        sid = session.get("id")
        is_cur = "🟢 " if str(sid) == str(active_sess) else "💬 "
        date_str = format_session_display(session, user_id)
        safe_title = " ".join(str(session.get("title") or "گفتگوی بدون عنوان").split())
        title_budget = max(12, 61 - len(is_cur) - len(date_str))
        safe_title = safe_title[:title_budget]
        title = f"{is_cur}{safe_title} [{date_str}]"[:64]
        markup.row(
            types.InlineKeyboardButton(title, callback_data=f"switch_sess_{sid}"),
            types.InlineKeyboardButton("🗑", callback_data=f"del_single_sess_{sid}", style="danger")
        )

    markup.add(
        types.InlineKeyboardButton("➕ ایجاد چت جدید" if get_user_lang(user_id) == "fa" else "➕ New Chat", callback_data="new_chat", style="success"),
        types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی" if get_user_lang(user_id) == "fa" else "🔙 Main Menu", callback_data="main_menu")
    )
    markup.add(types.InlineKeyboardButton(
        "❔ راهنمای تاریخچه گفتگوها" if get_user_lang(user_id) == "fa" else "❔ Chat history guide",
        callback_data="history_help"
    ))
    text = ("📜 تاریخچه گفتگوها (حداکثر ۷ مورد) — ساعت به وقت ایران:\n"
            "🟢 گفتگوی علامت‌دار، گفتگوی فعال شماست. چت‌های جدید خودکار ذخیره می‌شوند." if get_user_lang(user_id) == "fa"
            else "📜 Saved chats (up to 7) — Iran local time. New chats are saved automatically; 🟢 marks the active chat.")
    return text, markup


def send_history_menu(chat_id, user_id, message_id=None):
    # Read the two history keys in a single Redis round-trip.
    history_values = batch_kv_get([f"SESSIONS_{user_id}", f"ACTIVE_SESSION_{user_id}"])
    try:
        raw_sessions = json.loads(history_values.get(f"SESSIONS_{user_id}") or "[]")
        sessions = [item for item in raw_sessions if isinstance(item, dict) and item.get("id")] if isinstance(raw_sessions, list) else []
    except Exception:
        sessions = []
    active_sess = history_values.get(f"ACTIVE_SESSION_{user_id}")
    if not sessions:
        get_or_create_active_session(user_id)
        sessions = load_user_sessions(user_id)
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

    sessions = save_sessions_limited(user_id, sessions, active_id=active_sess)
    text, markup = build_history_menu_markup(user_id, sessions, active_sess)
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

# ==========================================
# 🎛 هاب جامع انتخاب ۳ مدل کاملاً مستقل
# ==========================================
def build_models_hub_menu(target_key_id, is_group=False, models_override=None, state_values_override=None):
    """Build the actual model-hub screen without sending a Telegram message."""
    if models_override is None:
        chat_models = get_ai_models_cached()
        code_models = get_code_models_cached() or chat_models
        img_models = get_img_models_cached()
        video_models = get_video_models_cached()
    else:
        chat_models = models_override.get("chat", [])
        code_models = models_override.get("code", []) or chat_models
        img_models = models_override.get("image", [])
        video_models = models_override.get("video", [])

    state_keys = [
        f"USER_MODEL_{target_key_id}",
        f"USER_CODE_MODEL_{target_key_id}",
        f"USER_IMG_MODEL_{target_key_id}",
        f"USER_VIDEO_MODEL_{target_key_id}",
    ]
    if state_values_override is not None:
        state_values = state_values_override
    else:
        state_values = {}
        missing_state_keys = []
        now_cache = time.monotonic()
        with _MODEL_SELECTION_CACHE_LOCK:
            for state_key in state_keys:
                cached_state = _MODEL_SELECTION_CACHE.get(state_key)
                if cached_state and (now_cache - cached_state[0]) < _MODEL_SELECTION_CACHE_TTL:
                    state_values[state_key] = cached_state[1]
                else:
                    missing_state_keys.append(state_key)
        if missing_state_keys:
            fetched_state = batch_kv_get(missing_state_keys)
            state_values.update(fetched_state)
            with _MODEL_SELECTION_CACHE_LOCK:
                fetched_at = time.monotonic()
                for state_key, state_value in fetched_state.items():
                    if state_value is not None:
                        _MODEL_SELECTION_CACHE[state_key] = (fetched_at, str(state_value))
        for state_key in state_keys:
            state_values.setdefault(state_key, None)

    def _safe_index(value, default=0):
        try:
            return max(0, int(value if value is not None else default))
        except (TypeError, ValueError):
            return default

    cur_chat_idx = _safe_index(state_values.get(state_keys[0]))
    cur_code_idx = _safe_index(state_values.get(state_keys[1]) or state_values.get(state_keys[0]))
    if code_models and not (0 <= cur_code_idx < len(code_models)):
        cur_code_idx = 0
    cur_img_idx = _safe_index(state_values.get(state_keys[2]))
    cur_video_idx = _safe_index(state_values.get(state_keys[3]))

    chat_name = chat_models[cur_chat_idx].get("name") if cur_chat_idx < len(chat_models) else "تعریف نشده"
    code_name = code_models[cur_code_idx].get("name") if cur_code_idx < len(code_models) else "تعریف نشده"
    img_name = img_models[cur_img_idx].get("name") if cur_img_idx < len(img_models) else "تعریف نشده"
    video_name = video_models[cur_video_idx].get("name") if cur_video_idx < len(video_models) else "تعریف نشده"

    current_mode = get_user_current_mode(target_key_id)
    mode_names = {"CHAT": "💬 پرسش و پاسخ (چت عادی)", "CODE": "💻 کدنویسی و توسعه نرم‌افزار", "IMAGE": "🎨 استودیوی ساخت عکس", "VIDEO": "🎬 استودیوی ساخت ویدیو"}
    cur_mode_name = mode_names.get(current_mode, "💬 پرسش و پاسخ")

    if is_group:
        text = (
            "✨ **منوی جامع مدیریت مدل‌ها و حالت ربات در گروه**\n\n"
            f"🎯 **حالت فعال گروه:** `{cur_mode_name}`\n"
            f"💬 مدل فعال چت: **{chat_name}**\n"
            f"💻 مدل فعال کدنویسی: **{code_name}**\n"
            f"🎨 مدل فعال ساخت عکس: **{img_name}**\n"
            f"🎬 مدل فعال ساخت ویدیو: **{video_name}**\n\n"
            "ادمین گرامی، بخش مورد نظر را جهت تغییر انتخاب کنید:"
        )
    else:
        text = (
            "✨ **منوی جامع انتخاب مدل‌های هوش مصنوعی**\n\n"
            f"💬 مدل فعال چت: **{chat_name}**\n"
            f"💻 مدل فعال کدنویسی: **{code_name}**\n"
            f"🎨 مدل فعال ساخت عکس: **{img_name}**\n"
            f"🎬 مدل فعال ساخت ویدیو: **{video_name}**\n\n"
            "بخش مورد نظر را برای تغییر مدل انتخاب کنید:"
        )

    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_group:
        c_chk = "✅ " if current_mode == "CHAT" else ""
        co_chk = "✅ " if current_mode == "CODE" else ""
        im_chk = "✅ " if current_mode == "IMAGE" else ""
        vi_chk = "✅ " if current_mode == "VIDEO" else ""
        markup.add(
            types.InlineKeyboardButton(f"{c_chk}💬 چت گروه", callback_data="switch_group_chat", style="primary"),
            types.InlineKeyboardButton(f"{co_chk}💻 کد گروه", callback_data="switch_group_code", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton(f"{im_chk}🎨 عکس گروه", callback_data="switch_group_image", style="success"),
            types.InlineKeyboardButton(f"{vi_chk}🎬 ویدیو گروه", callback_data="switch_group_video", style="success")
        )
        markup.add(
            types.InlineKeyboardButton("💬 مدل چت", callback_data="models_cat_chat", style="primary"),
            types.InlineKeyboardButton("💻 مدل کدنویسی", callback_data="models_cat_code", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton("🎨 مدل‌های ساخت عکس", callback_data="models_cat_image", style="success"),
            types.InlineKeyboardButton("🎬 مدل‌های ساخت ویدیو", callback_data="models_cat_video", style="success")
        )
        markup.add(types.InlineKeyboardButton("❌ بستن منو", callback_data="close_menu", style="danger"))
    else:
        markup.add(
            types.InlineKeyboardButton("💬 مدل چت", callback_data="models_cat_chat", style="primary"),
            types.InlineKeyboardButton("💻 مدل کدنویسی", callback_data="models_cat_code", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton("🎨 مدل‌های ساخت عکس", callback_data="models_cat_image", style="success"),
            types.InlineKeyboardButton("🎬 مدل‌های ساخت ویدیو", callback_data="models_cat_video", style="success")
        )
        markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu"))

    return text, markup


def send_models_hub(chat_id, target_key_id, is_group=False, message_id=None):
    text, markup = build_models_hub_menu(target_key_id, is_group=is_group)
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def build_model_selection_markup(target_key_id, is_group=False, models=None, current_idx=None, is_code_category=False):
    prefix = "set_code_model_" if is_code_category else "set_model_"
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for idx, m in enumerate(models or []):
        chk = "✅ " if str(idx) == str(current_idx) else "🤖 "
        vis = " 👁️" if m.get("supportsVision") else ""
        btn_text = f"{chk}{m.get('name')}{vis}"
        buttons.append(types.InlineKeyboardButton(btn_text, callback_data=f"{prefix}{idx}"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی مدل‌ها", callback_data="models_hub"))
    return markup

def build_video_model_selection_markup(target_key_id, is_group=False, video_models=None, current_idx=None):
    if video_models is None or current_idx is None:
        video_models = get_video_models_cached()
        current_idx = _model_selection_get_or_load(f"USER_VIDEO_MODEL_{target_key_id}")
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for idx, model in enumerate(video_models):
        chk = "✅ " if str(idx) == str(current_idx) else "🎬 "
        buttons.append(types.InlineKeyboardButton(f"{chk}{model.get('name', 'Video model')}", callback_data=f"set_video_model_{idx}"))
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i + 2])
    if not buttons:
        markup.add(types.InlineKeyboardButton("مدلی تعریف نشده است", callback_data="noop_btn"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی مدل‌ها", callback_data="models_hub"))
    return markup


def build_image_model_selection_markup(target_key_id, is_group=False, img_models=None, current_idx=None):
    if img_models is None or current_idx is None:
        img_models = get_img_models_cached()
        current_idx = _model_selection_get_or_load(f"USER_IMG_MODEL_{target_key_id}")

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for idx, m in enumerate(img_models):
        chk = "✅ " if str(idx) == str(current_idx) else "🎨 "
        buttons.append(types.InlineKeyboardButton(f"{chk}{m.get('name')}", callback_data=f"set_img_model_{idx}"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی مدل‌ها", callback_data="models_hub"))
    return markup

# ==========================================
# 👥 سیستم کامل مانیتورینگ و CRM کاربران در پنل ادمین
# ==========================================
def send_admin_users_list(chat_id, page=0, message_id=None):
    """Fast paginated CRM list; user details/status are fetched in batched MGETs."""
    users = sorted(get_all_bot_users(), key=lambda value: int(value) if str(value).isdigit() else -1, reverse=True)
    total_users = len(users)
    per_page = 8
    total_pages = max(1, (total_users + per_page - 1) // per_page)
    page = max(0, min(int(page), total_pages - 1))
    page_users = users[page * per_page : (page + 1) * per_page]

    keys = []
    for u in page_users:
        keys.extend((f"USER_INFO_{u}", f"BANNED_{u}"))
    data_by_key = batch_kv_get(keys)

    markup = types.InlineKeyboardMarkup(row_width=1)
    for u in page_users:
        info_raw = data_by_key.get(f"USER_INFO_{u}")
        try:
            info = json.loads(info_raw) if info_raw else {}
        except Exception:
            info = {}
        name = str(info.get("name") or "کاربر").replace("\n", " ")[:35]
        is_banned = str(data_by_key.get(f"BANNED_{u}") or "").lower() == "true"
        status_icon = "🔴" if is_banned else "🟢"
        btn_text = f"{status_icon} {name} | ID: {u}"[:64]
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"user_card_{u}_{page}"))

    nav_btns = []
    if page > 0:
        nav_btns.append(types.InlineKeyboardButton("◀️ قبلی", callback_data=f"admin_users_p_{page-1}"))
    nav_btns.append(types.InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop_btn"))
    if page < total_pages - 1:
        nav_btns.append(types.InlineKeyboardButton("بعدی ▶️", callback_data=f"admin_users_p_{page+1}"))
    markup.row(*nav_btns)
    markup.add(types.InlineKeyboardButton("🔍 جستجو با آیدی عددی", callback_data="admin_search_user_id", style="primary"))
    markup.add(types.InlineKeyboardButton("➕ افزودن دستی کاربر", callback_data="admin_add_user_manual", style="success"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin_panel", style="primary"))

    text = (
        f"👥 **سامانه مدیریت و مانیتورینگ کاربران**\n\n"
        f"📊 کل کاربران ثبت‌نامی: **{total_users}**\n"
        f"📄 صفحه **{page + 1}** از **{total_pages}**\n\n"
        "برای مشاهده مشخصات، بن/آنبن، اخراج یا ارسال پیام اختصاصی، روی کاربر کلیک کنید:"
    )
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def send_user_profile_card(chat_id, target_uid, page=0, message_id=None):
    info_raw = safe_kv_get(f"USER_INFO_{target_uid}")
    info = json.loads(info_raw) if info_raw else {}
    name = info.get("name", "کاربر")
    uname = info.get("username", "ندارد")
    joined = info.get("joined", "نامشخص")
    is_banned = safe_kv_get(f"BANNED_{target_uid}") == "true"
    status_text = "🔴 مسدود (بلاک شده)" if is_banned else "🟢 فعال و مجاز"
    ban_btn_text = "✅ رفع مسدودی کاربر" if is_banned else "🚫 مسدودسازی کاربر"
    ban_style = "success" if is_banned else "danger"

    text = (
        f"👤 **شناسنامه و مدیریت کاربر:**\n\n"
        f"🔹 **نام کاربر:** {name}\n"
        f"🔹 **یوزرنیم:** {uname}\n"
        f"🔹 **آیدی عددی:** `{target_uid}`\n"
        f"🔹 **وضعیت دسترسی:** {status_text}\n"
        f"📅 **تاریخ ثبت‌نام:** `{joined}`\n\n"
        "عملیات مورد نظر برای این کاربر را انتخاب کنید:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(ban_btn_text, callback_data=f"toggle_ban_{target_uid}_{page}", style=ban_style),
        types.InlineKeyboardButton("🗑 اخراج از دیتابیس", callback_data=f"kick_user_{target_uid}_{page}", style="danger")
    )
    markup.add(types.InlineKeyboardButton("📩 ارسال پیام اختصاصی به کاربر (DM)", callback_data=f"dm_user_{target_uid}", style="primary"))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به لیست کاربران", callback_data=f"admin_users_p_{page}"))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

# ==========================================
# 🛠 سامانه جامع لیست و ویرایش مشخصات مدل‌ها
# ==========================================
def send_admin_models_list(chat_id, message_id=None):
    chat_models = get_ai_models_cached()
    code_models = get_code_models_cached()
    img_models = get_img_models_cached()
    video_models = get_video_models_cached()
    markup = types.InlineKeyboardMarkup(row_width=2)

    buttons = []
    for idx, m in enumerate(chat_models):
        vis = " 👁️" if m.get("supportsVision") else ""
        buttons.append(types.InlineKeyboardButton(f"⚙️ {m.get('name')}{vis}", callback_data=f"admin_view_m_{idx}", style="primary"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    code_buttons = [types.InlineKeyboardButton(f"💻 {m.get('name', 'Code')}", callback_data=f"admin_view_code_{idx}", style="primary") for idx, m in enumerate(code_models)]
    for i in range(0, len(code_buttons), 2):
        markup.row(*code_buttons[i:i+2])

    img_buttons = []
    for idx, m in enumerate(img_models):
        img_buttons.append(types.InlineKeyboardButton(f"🎨 {m.get('name')}", callback_data=f"admin_view_img_{idx}", style="success"))

    for i in range(0, len(img_buttons), 2):
        markup.row(*img_buttons[i:i+2])

    video_buttons = [types.InlineKeyboardButton(f"🎬 {m.get('name', 'Video')}", callback_data=f"admin_view_video_{idx}", style="success") for idx, m in enumerate(video_models)]
    for i in range(0, len(video_buttons), 2):
        markup.row(*video_buttons[i:i+2])

    markup.add(
        types.InlineKeyboardButton("➕ افزودن مدل چت", callback_data="admin_add_model", style="success"),
        types.InlineKeyboardButton("💻 افزودن مدل برنامه‌نویسی", callback_data="admin_add_code_model", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("🎨 افزودن مدل عکس", callback_data="admin_add_img_model", style="success"),
        types.InlineKeyboardButton("🎬 افزودن مدل ویدیو", callback_data="admin_add_video_model", style="success")
    )
    markup.add(
        types.InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin_panel"),
        types.InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")
    )

    text = (
        "📋 **سامانه جامع مدیریت و ویرایش مدل‌ها:**\n\n"
        "مدل‌های 💬 چت، 💻 برنامه‌نویسی، 🎨 عکس و 🎬 ویدیو به‌صورت جداگانه فهرست می‌شوند. "
        "برای ویرایش یا حذف، روی مدل مربوط کلیک کنید:"
    )
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def send_admin_model_edit_card(chat_id, idx, is_img=False, message_id=None, is_video=False, is_code=False):
    if is_img:
        models = get_img_models_cached()
        if idx >= len(models):
            send_admin_models_list(chat_id, message_id)
            return
        m = models[idx]
        title = f"🎨 **شناسنامه و ویرایش مدل ساخت عکس:** `{m.get('name')}`"
        mask_key = (m.get('apiKey', '')[:6] + "...") if m.get('apiKey') else "ندارد / رایگان"
        text = (
            f"{title}\n\n"
            f"🔹 **نام عمومی:** `{m.get('name')}`\n"
            f"🌐 **Base URL:** `{m.get('baseUrl')}`\n"
            f"🔑 **API Key:** `{mask_key}`\n"
            f"📌 **Model Name:** `{m.get('modelName')}`\n"
            f"🔗 **وب‌سایت (اختیاری):** `{m.get('siteUrl') or 'تنظیم نشده'}`\n\n"
            "جهت تغییر مشخصات روی گزینه مورد نظر کلیک کنید:"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ تغییر نام", callback_data=f"edit_img_name_{idx}", style="primary"),
            types.InlineKeyboardButton("🌐 تغییر Base URL", callback_data=f"edit_img_url_{idx}", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton("🔑 تغییر API Key", callback_data=f"edit_img_key_{idx}", style="primary"),
            types.InlineKeyboardButton("📌 تغییر Model Name", callback_data=f"edit_img_id_{idx}", style="primary")
        )
        markup.add(types.InlineKeyboardButton("🔗 تغییر آدرس وب‌سایت", callback_data=f"edit_img_site_{idx}", style="primary"))
        markup.add(
            types.InlineKeyboardButton("🗑 حذف این مدل", callback_data=f"del_img_model_{idx}", style="danger"),
            types.InlineKeyboardButton("🔙 لیست مدل‌ها", callback_data="admin_list_models")
        )
    elif is_video:
        models = get_video_models_cached()
        if idx >= len(models):
            send_admin_models_list(chat_id, message_id)
            return
        m = models[idx]
        mask_key = (m.get('apiKey', '')[:6] + "...") if m.get('apiKey') else "ندارد / عمومی"
        text = (
            f"🎬 **شناسنامه و ویرایش مدل ساخت ویدیو:** `{m.get('name')}`\n\n"
            f"🔹 **نام عمومی:** `{m.get('name')} `\n"
            f"🌐 **Base URL / Endpoint:** `{m.get('baseUrl') or 'تنظیم نشده'}`\n"
            f"🔑 **API Key:** `{mask_key}`\n"
            f"📌 **Model Name:** `{m.get('modelName') or 'تنظیم نشده'}`\n"
            f"🔗 **وب‌سایت:** `{m.get('siteUrl') or 'تنظیم نشده'}`\n"
            f"🔄 **Status URL Template:** `{m.get('statusUrlTemplate') or 'پیش‌فرض endpoint/{id}'}`\n\n"
            "Base URL باید endpoint API ساخت ویدیو یا Base URL مستندشدهٔ سرویس باشد؛ آدرس صفحهٔ معمولی سایت به‌تنهایی کافی نیست."
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ تغییر نام", callback_data=f"edit_video_name_{idx}", style="primary"),
            types.InlineKeyboardButton("🌐 تغییر Base URL", callback_data=f"edit_video_url_{idx}", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton("🔑 تغییر API Key", callback_data=f"edit_video_key_{idx}", style="primary"),
            types.InlineKeyboardButton("📌 تغییر Model Name", callback_data=f"edit_video_id_{idx}", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton("🔗 تغییر وب‌سایت", callback_data=f"edit_video_site_{idx}", style="primary"),
            types.InlineKeyboardButton("🔄 تغییر Status URL", callback_data=f"edit_video_status_{idx}", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton("🗑 حذف مدل", callback_data=f"del_video_model_{idx}", style="danger"),
            types.InlineKeyboardButton("🔙 لیست مدل‌ها", callback_data="admin_list_models")
        )
    elif is_code:
        models = get_code_models_cached()
        if idx < 0 or idx >= len(models):
            send_admin_models_list(chat_id, message_id)
            return
        m = models[idx]
        mask_key = (m.get("apiKey", "")[:6] + "...") if m.get("apiKey") else "ندارد / عمومی"
        vision_state = "فعال ✅" if m.get("supportsVision") else "غیرفعال ❌"
        text = (
            f"💻 **شناسنامه و ویرایش مدل برنامه‌نویسی:** `{m.get('name')}`\n\n"
            f"🔹 **نام عمومی:** `{m.get('name')}`\n"
            f"🌐 **Base URL:** `{m.get('baseUrl') or 'تنظیم نشده'}`\n"
            f"🔑 **API Key:** `{mask_key}`\n"
            f"📌 **Model Name:** `{m.get('modelName') or 'تنظیم نشده'}`\n"
            f"👁 **Vision:** `{vision_state}`\n\n"
            "این مدل فقط برای حالت برنامه‌نویسی استفاده می‌شود."
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ تغییر نام", callback_data=f"edit_code_name_{idx}", style="primary"),
            types.InlineKeyboardButton("🌐 تغییر Base URL", callback_data=f"edit_code_url_{idx}", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton("🔑 تغییر API Key", callback_data=f"edit_code_key_{idx}", style="primary"),
            types.InlineKeyboardButton("📌 تغییر Model Name", callback_data=f"edit_code_id_{idx}", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton("👁 تغییر Vision", callback_data=f"toggle_code_vision_{idx}", style="success"),
            types.InlineKeyboardButton("🗑 حذف مدل", callback_data=f"del_code_model_{idx}", style="danger")
        )
        markup.add(types.InlineKeyboardButton("🔙 بازگشت به لیست مدل‌ها", callback_data="admin_list_models"))
    else:
        models = get_ai_models_cached()
        if idx >= len(models):
            send_admin_models_list(chat_id, message_id)
            return
        m = models[idx]
        title = f"🤖 **شناسنامه و ویرایش مدل چت:** `{m.get('name')}`"
        mask_key = (m.get('apiKey', '')[:6] + "...") if m.get('apiKey') else "ندارد / عمومی"
        vision_state = "فعال ✅" if m.get('supportsVision') else "غیرفعال ❌"
        text = (
            f"{title}\n\n"
            f"🔹 **نام عمومی:** `{m.get('name')}`\n"
            f"🌐 **Base URL:** `{m.get('baseUrl')}`\n"
            f"🔑 **API Key:** `{mask_key}`\n"
            f"📌 **Model Name:** `{m.get('modelName')}`\n"
            f"👁 **وضعیت تحلیل تصویر (Vision):** `{vision_state}`\n\n"
            "جهت تغییر مشخصات روی گزینه مورد نظر کلیک کنید:"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ تغییر نام", callback_data=f"edit_m_name_{idx}", style="primary"),
            types.InlineKeyboardButton("🌐 تغییر Base URL", callback_data=f"edit_m_url_{idx}", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton("🔑 تغییر API Key", callback_data=f"edit_m_key_{idx}", style="primary"),
            types.InlineKeyboardButton("📌 تغییر Model Name", callback_data=f"edit_m_id_{idx}", style="primary")
        )
        markup.add(
            types.InlineKeyboardButton("👁 تغییر وضعیت Vision", callback_data=f"toggle_m_vision_{idx}", style="success"),
            types.InlineKeyboardButton("🗑 حذف این مدل", callback_data=f"del_model_{idx}", style="danger")
        )
        markup.add(types.InlineKeyboardButton("🔙 بازگشت به لیست مدل‌ها", callback_data="admin_list_models"))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

# ==========================================
# پنل مدیریت ادمین
# ==========================================
# متن راهنمای فارسی داخل خود فایل جاسازی شده است تا در هاست نیاز به فایل TXT جدا نباشد.
ADMIN_SETUP_GUIDE_TEXT = r"""راهنمای تنظیم مدل‌های چت، برنامه‌نویسی، عکس و ویدیو در ربات
============================================

بخش اول ـ افزودن مدل ویدیو
--------------------------
مسیر:
/start ← پنل مدیریت ادمین ← لیست مدل‌های ربات / مدیریت مدل‌ها ← افزودن مدل ویدیو

در هر مرحله فقط جواب همان سؤال را ارسال کن:

1) نام نمایشی مدل
یک اسم دلخواه برای نمایش در منو؛ مثلاً «سایت ساخت ویدیو». این فقط نام دکمه است.

2) Base URL یا Endpoint API
اگر می‌خواهی ویدیو مستقیماً داخل تلگرام ساخته شود، باید آدرس API واقعی را از مستندات سرویس برداری.
اگر فقط می‌خواهی کاربر سایت را باز کند و ساخت ویدیو را در سایت انجام دهد، یک نقطه (.) بفرست تا این فیلد خالی بماند.

3) API Key
برای اتصال مستقیم به API، کلید همان سرویس را وارد کن. اگر فقط سایت را نگه می‌داری یا سرویس واقعاً کلید نمی‌خواهد، نقطه (.) بفرست.
کلید خصوصی را برای دیگران ارسال نکن.

4) Model Name
شناسه دقیق مدل در API است، نه لزوماً اسم تبلیغاتی سایت. اگر فقط سایت داری و API نداری، نقطه (.) بفرست.

5) آدرس وب‌سایت سرویس
اینجا لینک کامل سایت را وارد کن؛ مثلاً https://video.example.com (این فقط نمونه ساختگی است؛ لینک واقعی سرویس خودت را قرار بده).
این همان لینکی است که کاربر با زدن دکمهٔ سایت ساخت ویدیو باز می‌کند.

6) Status URL Template
فقط برای APIهایی لازم است که ابتدا یک شناسه کار (job/task ID) برمی‌گردانند و بعد باید وضعیت آن را بررسی کرد. اگر فقط سایت داری یا نمی‌دانی لازم است، نقطه (.) بفرست.

مهم:
- اگر فقط Website URL را وارد کرده باشی و Base URL خالی باشد، کاربر با زدن دکمهٔ «ساخت ویدیو» مستقیماً دکمهٔ بازکردن سایت را می‌بیند؛ لازم نیست پرامپت را اول برای ربات بفرستد. تولید داخل تلگرام انجام نمی‌شود.
- آدرس صفحه اصلی سایت را در فیلد Base URL نگذار؛ Base URL باید endpoint رسمی API باشد.
- هر API ساخت ویدیو ممکن است روش و قالب متفاوتی داشته باشد. واردکردن نام و لینک سایت به‌تنهایی API آن را سازگار نمی‌کند.

بخش دوم ـ افزودن مدل برنامه‌نویسی
---------------------------------
مسیر:
/start ← پنل مدیریت ادمین ← افزودن مدل برنامه‌نویسی

ربات این موارد را می‌پرسد:
1) نام نمایشی: نام دلخواه برای نمایش در فهرست مدل‌های کدنویسی.
2) Base URL: آدرس endpoint واقعی API؛ آدرس سایت عادی کافی نیست.
3) API Key: کلید خصوصی همان ارائه‌دهنده؛ اگر سرویس واقعاً به کلید نیاز ندارد، نقطه (.) بفرست.
4) Model Name: شناسهٔ مدل از مستندات API؛ حدس نزن.
5) Vision: اگر مدل ورودی تصویر را می‌پذیرد yes و در غیر این صورت no بفرست.

مدل‌های این بخش فقط برای حالت «برنامه‌نویسی» استفاده می‌شوند و انتخابشان از مدل‌های چت مستقل است. تا وقتی در این بخش مدل اضافه نکرده‌ای، ربات برای حفظ سازگاری از مدل‌های چت استفاده می‌کند.

بخش سوم ـ افزودن مدل عکس
------------------------
مسیر:
/start ← پنل مدیریت ادمین ← لیست مدل‌های ربات / مدیریت مدل‌ها ← افزودن مدل عکس

ربات اطلاعات زیر را می‌پرسد:
1) نام نمایشی: اسم دلخواه برای دکمه.
2) Base URL: آدرس endpoint واقعی API ساخت تصویر.
3) API Key: کلید همان سرویس؛ اگر واقعاً لازم نیست، نقطه (.) بفرست.
4) Model Name: شناسه دقیق مدل API؛ اگر لازم نیست، فقط طبق مستندات سرویس نقطه (.) بفرست.
5) Website URL: لینک سایت برای بازکردن در مرورگر؛ این لینک جای API را نمی‌گیرد.

چطور اطلاعات درست را پیدا کنم؟
------------------------------
در سایت سرویس دنبال API Documentation، Developers یا Quickstart بگرد. برای ساخت مستقیم در تلگرام باید endpoint ساخت، شیوه احراز هویت، شناسه مدل و قالب پاسخ API مشخص باشد.
اگر سرویس فقط سایت عادی دارد و API عمومی ندارد، آدرس آن را در Website URL ذخیره کن و فیلدهای API را با نقطه (.) خالی بگذار.
برای راهنمایی دقیق‌تر می‌توانی نام سرویس یا لینک مستندات عمومی API آن را بررسی کنی؛ هرگز API Key یا توکن خصوصی را برای کسی نفرست."""

def get_admin_cancel_markup():
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت به پنل", callback_data="admin_cancel_wizard", style="danger"))
    return m

def get_admin_panel_markup():
    is_active = is_bot_globally_active()
    power_btn_text = "🔴 خاموش کردن کل ربات" if is_active else "🟢 روشن کردن کل ربات"
    power_callback = "admin_toggle_off" if is_active else "admin_toggle_on"
    power_style = "danger" if is_active else "success"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(power_btn_text, callback_data=power_callback, style=power_style),
        types.InlineKeyboardButton("📊 آمار سرور", callback_data="admin_stats", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users_menu", style="success"),
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("💾 خروجی بکاپ چت‌ها", callback_data="admin_backup_chats", style="success"),
        types.InlineKeyboardButton("📥 بازگردانی بکاپ", callback_data="admin_restore_chats", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("🧹 پاکسازی کش موقت", callback_data="admin_clean_cache", style="danger"),
        types.InlineKeyboardButton("🟡 لیست مدل های ربات", callback_data="admin_list_models", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("➕ افزودن مدل چت", callback_data="admin_add_model", style="success"),
        types.InlineKeyboardButton("💻 افزودن مدل برنامه‌نویسی", callback_data="admin_add_code_model", style="primary")
    )
    markup.add(
        types.InlineKeyboardButton("🎨 افزودن مدل عکس", callback_data="admin_add_img_model", style="success"),
        types.InlineKeyboardButton("🎬 افزودن مدل ویدیو", callback_data="admin_add_video_model", style="success")
    )
    markup.add(
        types.InlineKeyboardButton("🧪 تست سلامت و بار ربات", callback_data="admin_self_test", style="success"),
        types.InlineKeyboardButton("📘 راهنمای تنظیم مدل‌ها", callback_data="admin_setup_guide", style="primary"),
    )
    markup.add(
        types.InlineKeyboardButton("📢 افزودن اسپانسر", callback_data="admin_add_sponsor", style="primary"),
        types.InlineKeyboardButton("📋 لیست کانال‌های اسپانسر", callback_data="admin_del_sponsor_menu", style="danger")
    )
    markup.add(types.InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu"))
    return markup

def _rtlize_guide_text(text):
    """Add RTL marks so Persian paragraphs are rendered in the correct direction in Telegram."""
    rtl_mark = "\u200f"
    lines = str(text or "").strip().splitlines()
    return "\n".join((rtl_mark + line if line.strip() else rtl_mark) for line in lines)


def send_admin_setup_guide(chat_id):
    """Send the embedded Persian setup guide in readable, Telegram-sized pages."""
    headings = (
        "بخش دوم ـ افزودن مدل برنامه‌نویسی",
        "بخش سوم ـ افزودن مدل عکس",
        "چطور اطلاعات درست را پیدا کنم؟",
    )
    split_pattern = r"(?=" + "|".join(re.escape(h) for h in headings) + r")"
    pages = [p.strip() for p in re.split(split_pattern, ADMIN_SETUP_GUIDE_TEXT.strip()) if p.strip()]

    # A defensive fallback avoids sending an empty guide if the headings are edited later.
    if not pages:
        pages = [ADMIN_SETUP_GUIDE_TEXT.strip()]

    for index, page in enumerate(pages, 1):
        header = f"📘 راهنمای تنظیمات ادمین | صفحه {index} از {len(pages)}\n\n"
        message_text = _rtlize_guide_text(header + page)
        markup = None
        if index == len(pages):
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin_panel", style="primary"))
        # Telegram messages must stay below 4096 characters; these guide sections are split by topic.
        if len(message_text) <= 3900:
            bot.send_message(chat_id, message_text, reply_markup=markup, disable_web_page_preview=True)
        else:
            # Fallback split for longer edits while keeping every sub-message readable.
            remaining = message_text
            chunks = []
            while len(remaining) > 3900:
                cut = remaining.rfind("\n", 0, 3900)
                if cut < 1000:
                    cut = 3900
                chunks.append(remaining[:cut])
                remaining = "\u200f" + remaining[cut:].lstrip("\n")
            chunks.append(remaining)
            for chunk_index, chunk in enumerate(chunks):
                bot.send_message(
                    chat_id,
                    chunk,
                    reply_markup=markup if chunk_index == len(chunks) - 1 else None,
                    disable_web_page_preview=True,
                )


INACTIVE_USER_DAYS = 30

def get_admin_status_user_ids(category):
    """Return numeric IDs by observed bot status; inactive is no activity for 30+ days."""
    users = [str(u) for u in get_all_bot_users() if str(u).strip()]
    if category == "banned":
        ids = upstash_command(["SMEMBERS", "BANNED_USERS_SET"]) or []
        candidates = {str(x) for x in ids}
        # Include users marked by the per-user key even if an old build did not maintain the set.
        for start in range(0, len(users), 100):
            batch = users[start:start + 100]
            kvs = batch_kv_get([f"BANNED_{u}" for u in batch])
            candidates.update(u for u in batch if str(kvs.get(f"BANNED_{u}") or "").lower() == "true")
        return sorted(candidates, key=lambda value: int(value) if value.isdigit() else -1, reverse=True)
    if category == "unreachable":
        ids = upstash_command(["SMEMBERS", "BOT_UNREACHABLE_USERS_SET"]) or []
        known = set(users)
        candidates = {str(x) for x in ids if str(x) in known}
        return sorted(candidates, key=lambda value: int(value) if value.isdigit() else -1, reverse=True)
    if category == "inactive":
        now_ms = int(time.time() * 1000)
        cutoff = now_ms - INACTIVE_USER_DAYS * 24 * 60 * 60 * 1000
        inactive = []
        for start in range(0, len(users), 100):
            batch = users[start:start + 100]
            values = batch_kv_get([f"LAST_ACTIVE_{u}" for u in batch])
            for uid in batch:
                raw = values.get(f"LAST_ACTIVE_{uid}")
                try:
                    last = int(raw)
                except (TypeError, ValueError):
                    last = 0
                if not last or last < cutoff:
                    inactive.append(uid)
        return sorted(inactive, key=lambda value: int(value) if value.isdigit() else -1, reverse=True)
    return []


def send_admin_status_user_list(chat_id, category, page=0, message_id=None):
    titles = {
        "inactive": f"😴 کاربران غیرفعال (بدون فعالیت طی {INACTIVE_USER_DAYS} روز اخیر)",
        "unreachable": "⚠️ ارسال ناموفق؛ احتمال بلاک یا چت ناموجود",
        "banned": "🚫 کاربران مسدودشده توسط ادمین",
    }
    ids = get_admin_status_user_ids(category)
    per_page = 12
    total_pages = max(1, (len(ids) + per_page - 1) // per_page)
    page = max(0, min(int(page), total_pages - 1))
    current_ids = ids[page * per_page:(page + 1) * per_page]
    text = f"{titles.get(category, 'فهرست کاربران')}\n\nتعداد: {len(ids)}\nصفحه {page + 1} از {total_pages}\n\nآیدی‌های عددی:"
    if not current_ids:
        text += "\nدر این دسته کاربری پیدا نشد."
    else:
        text += "\n" + "\n".join(f"• `{uid}`" for uid in current_ids)
    markup = types.InlineKeyboardMarkup(row_width=2)
    for uid in current_ids:
        markup.add(types.InlineKeyboardButton(f"👤 مدیریت {uid}", callback_data=f"user_card_{uid}_0"))
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("◀️ قبلی", callback_data=f"admin_status_{category}_{page-1}"))
    nav.append(types.InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop_btn"))
    if page < total_pages - 1:
        nav.append(types.InlineKeyboardButton("بعدی ▶️", callback_data=f"admin_status_{category}_{page+1}"))
    markup.row(*nav)
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به آمار", callback_data="admin_stats"))
    if message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="Markdown", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)


def send_bot_stats(chat_id):
    users = get_all_bot_users()
    total_users = len(users)
    now_ms = int(time.time() * 1000)
    day_ms = 24 * 60 * 60 * 1000
    active_count = 0
    if users:
        last_active = batch_kv_get([f"LAST_ACTIVE_{u}" for u in users])
        for u in users:
            val = last_active.get(f"LAST_ACTIVE_{u}")
            try:
                if val and (now_ms - int(val)) < day_ms:
                    active_count += 1
            except (TypeError, ValueError):
                pass
    inactive_count = len(get_admin_status_user_ids("inactive"))
    banned_count = len(get_admin_status_user_ids("banned"))
    unreachable_count = len(get_admin_status_user_ids("unreachable"))
    status_str = "🟢 روشن و فعال" if is_bot_globally_active() else "?? خاموش (متوقف)"
    text = (
        f"📊 **آمار جامع کاربران و وضعیت ربات:**\n\n"
        f"⚡ وضعیت ربات: **{status_str}**\n"
        f"👥 کل کاربران ثبت‌نامی: **{total_users}**\n"
        f"🟢 فعال در ۲۴ ساعت اخیر: **{active_count}**\n"
        f"😴 غیرفعال طی {INACTIVE_USER_DAYS} روز اخیر: **{inactive_count}**\n"
        f"⚠️ ارسال ناموفق/احتمال بلاک: **{unreachable_count}**\n"
        f"🚫 مسدودشده توسط ادمین: **{banned_count}**\n\n"
        "توجه: تلگرام اعلام مستقیمِ «لفت از ربات» نمی‌دهد؛ فهرست ارسال ناموفق بر اساس خطاهای قابل‌شناسایی ارسال پیام ساخته می‌شود."
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("😴 فهرست غیرفعال‌ها", callback_data="admin_stats_inactive", style="primary"),
        types.InlineKeyboardButton("⚠️ فهرست ارسال ناموفق", callback_data="admin_stats_unreachable", style="primary")
    )
    markup.add(types.InlineKeyboardButton("🚫 فهرست بن‌شده‌ها", callback_data="admin_stats_banned", style="danger"))
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
                        "created_at": s.get("created_at"),
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

# ==========================================
# ⚡ پاکسازی پرسرعت کش موقت (زیر ۰.۱ ثانیه)
# ==========================================
def clean_system_cache(admin_chat_id):
    invalidate_models_cache()
    invalidate_users_cache()
    invalidate_sponsors_cache()
    _USER_MODES_CACHE.clear()
    _USER_LANG_CACHE.clear()
    _CANCEL_REQS.clear()

    keys_to_del = [
        f"ADMIN_STEP_{ADMIN_ID}", f"TEMP_MODEL_{ADMIN_ID}", f"TEMP_CODE_MODEL_{ADMIN_ID}", f"TEMP_IMG_{ADMIN_ID}", f"TEMP_VIDEO_{ADMIN_ID}",
        f"USER_SUPPORT_STEP_{ADMIN_ID}", f"AWAITING_IMG_{ADMIN_ID}"
    ]
    upstash_command(["DEL"] + keys_to_del)
    with _TEMP_STATE_CACHE_LOCK:
        for temp_key in keys_to_del:
            _TEMP_STATE_CACHE.pop(temp_key, None)

    report = (
        "⚡ **عملیات پاکسازی کش موقت با موفقیت و در کمتر از ۰.۱ ثانیه انجام شد!**\n\n"
        "🔹 تمام کش‌های موقت پردازنده و رم آزاد شدند.\n"
        "🔒 اطلاعات پایگاه داده کاربران و تاریخچه گفتگوها دست‌نخورده باقی ماند."
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
            mark_user_unreachable(u, te)
            if te.error_code == 429:
                try:
                    time.sleep(te.result_json.get('parameters', {}).get('retry_after', 3))
                except Exception:
                    time.sleep(3)
        except Exception as exc:
            failed += 1
            mark_user_unreachable(u, exc)

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

def send_admin_sponsor_list(chat_id, message_id=None):
    channels = get_sponsor_channels_cached()
    list_text = "📢 هیچ کانال اسپانسری ثبت نشده است." if not channels else "📢 **لیست کانال‌های اسپانسری:**"
    markup = types.InlineKeyboardMarkup(row_width=2)

    for idx, ch in enumerate(channels):
        shown = str(ch)[:35]
        markup.row(
            types.InlineKeyboardButton(f"✏️ {shown}", callback_data=f"edit_sponsor_{idx}", style="primary"),
            types.InlineKeyboardButton("🗑 حذف", callback_data=f"del_sponsor_{idx}", style="danger")
        )

    markup.add(types.InlineKeyboardButton("➕ افزودن کانال اسپانسر", callback_data="admin_add_sponsor", style="success"))
    markup.add(
        types.InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin_panel"),
        types.InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")
    )
    if message_id:
        try:
            bot.edit_message_text(list_text, chat_id=chat_id, message_id=message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, list_text, reply_markup=markup)

# ==========================================
# ⚡ آماده‌سازی سریع زمینهٔ AI با یک MGET دسته‌ای
# ==========================================
def _prepare_ai_context_fast(user_id, target_key_id, is_group, active_mode, chat_id):
    """Resolve language, session id and model selection with one batched Redis read.

    Previously cold caches could trigger sequential Redis REST calls for language,
    active session, session list and model selection before the AI API was contacted.
    This combines cold state lookups and persists a newly-created empty session in the
    background, while still loading existing conversation history before making a prompt.
    """
    total_started = time.monotonic()
    uid = str(user_id)
    now = time.monotonic()

    lang_cached = _USER_LANG_CACHE.get(uid)
    lang_cache_hit = lang_cached in ("fa", "en")
    if not lang_cache_hit:
        lang_cached = None

    active_session_id = None
    session_cache_hit = False
    if not is_group:
        active_session_id = _get_active_session_cache(uid)
        session_cache_hit = bool(active_session_id)

    if active_mode == "CODE":
        selection_keys = [f"USER_CODE_MODEL_{target_key_id}", f"USER_MODEL_{target_key_id}", f"USER_MODEL_{uid}"]
    else:
        selection_keys = [f"USER_MODEL_{target_key_id}", f"USER_MODEL_{uid}"]

    selection_values = {}
    missing_keys = []
    selection_cache_hits = 0
    with _MODEL_SELECTION_CACHE_LOCK:
        for key in selection_keys:
            cached = _MODEL_SELECTION_CACHE.get(key)
            if cached and (now - cached[0]) < _MODEL_SELECTION_CACHE_TTL:
                selection_values[key] = str(cached[1])
                selection_cache_hits += 1
            else:
                missing_keys.append(key)

    # A single MGET carries all cold preflight fields. Include SESSIONS only when the
    # active-session cache is cold; this lets us recover an existing active session
    # without serializing several REST requests.
    batch_keys = list(missing_keys)
    if not lang_cache_hit:
        batch_keys.append(f"USER_LANG_{uid}")
    if not is_group and not session_cache_hit:
        batch_keys.extend((f"ACTIVE_SESSION_{uid}", f"SESSIONS_{uid}"))

    fetched = batch_kv_get(list(dict.fromkeys(batch_keys))) if batch_keys else {}

    if not lang_cache_hit:
        lang = str(fetched.get(f"USER_LANG_{uid}") or "fa")
        if lang not in ("fa", "en"):
            lang = "fa"
        _USER_LANG_CACHE[uid] = lang
    else:
        lang = lang_cached

    for key in missing_keys:
        value = fetched.get(key)
        stored_value = str(value) if value not in (None, "") else "0"
        selection_values[key] = stored_value
        with _MODEL_SELECTION_CACHE_LOCK:
            _MODEL_SELECTION_CACHE[key] = (time.monotonic(), stored_value)

    if not is_group:
        if not active_session_id:
            active_session_id = str(fetched.get(f"ACTIVE_SESSION_{uid}") or "").strip()
            if active_session_id:
                _set_active_session_cache(uid, active_session_id)
            else:
                sessions_raw = fetched.get(f"SESSIONS_{uid}")
                try:
                    parsed_sessions = json.loads(sessions_raw or "[]")
                    sessions = [item for item in parsed_sessions if isinstance(item, dict) and item.get("id")] if isinstance(parsed_sessions, list) else []
                except Exception:
                    sessions = []
                if sessions:
                    active_session_id = str(sessions[0]["id"])
                    _set_active_session_cache(uid, active_session_id)
                    _persist_kv_async(f"ACTIVE_SESSION_{uid}", active_session_id)
                else:
                    # No prior session exists: create an empty local session immediately
                    # and persist metadata asynchronously instead of blocking on several
                    # sequential Upstash calls before contacting the model API.
                    active_session_id = f"sess_{time.time_ns()}"
                    new_session = make_session_record(active_session_id)
                    _set_active_session_cache(uid, active_session_id)
                    _persist_kv_async(f"ACTIVE_SESSION_{uid}", active_session_id)
                    _persist_kv_async(f"SESSIONS_{uid}", [new_session])
                    _history_cache_put(f"HISTORY_{uid}_{active_session_id}", [])
        history_key = f"HISTORY_{uid}_{active_session_id}"
    else:
        active_session_id = None
        history_key = f"GROUP_HISTORY_{chat_id}_{uid}"

    user_selected = next(
        (str(selection_values.get(key)) for key in selection_keys if selection_values.get(key) not in (None, "")),
        "0",
    )

    history_started = time.monotonic()
    with _CHAT_HISTORY_CACHE_LOCK:
        cached_history_item = _CHAT_HISTORY_CACHE.get(history_key)
        history_cache_hit = bool(cached_history_item and history_started - cached_history_item[0] < _CHAT_HISTORY_CACHE_TTL)
    history = _load_chat_history(history_key)
    state_elapsed = history_started - total_started
    history_elapsed = time.monotonic() - history_started
    print(
        f"[AI Timing] preflight user={uid} group={is_group} "
        f"state={state_elapsed:.2f}s history={history_elapsed:.2f}s total={time.monotonic()-total_started:.2f}s "
        f"lang_cache={int(lang_cache_hit)} session_cache={int(session_cache_hit)} "
        f"selection_cache={selection_cache_hits}/{len(selection_keys)} history_cache={int(history_cache_hit)}"
    )
    return active_session_id, history_key, lang, selection_values, user_selected, history


# ==========================================
# ۳. پردازش هوش مصنوعی با وضعیت ثابت و وب‌گردی فنی
# ==========================================
def _worker_ai_process_impl(chat_id, user_id, message, text_prompt, target_key_id, is_group,
                            target_reply_id, thread_id=None, active_mode="CHAT",
                            precreated_status_msg=None, request_id=None, submitted_at=None):
    # Edit the queued acknowledgement immediately, before Redis reads or model setup.
    worker_started_at = time.monotonic()
    req_id = request_id or f"{user_id}_{time.time_ns()}"
    reply_to = target_reply_id if target_reply_id else (message.message_id if is_group else None)
    status_msg = precreated_status_msg
    stream_preview_active = False
    cancel_markup = types.InlineKeyboardMarkup()
    cancel_markup.add(types.InlineKeyboardButton("❌ لغو درخواست", callback_data=f"cancel_req_{req_id}", style="danger"))
    if status_msg is not None:
        _edit_processing_ack(chat_id, status_msg, "💬 در حال فکر کردن...", reply_markup=cancel_markup)
    else:
        status_msg = _send_processing_ack(
            chat_id, "💬 در حال فکر کردن...", thread_id=thread_id,
            reply_to_message_id=reply_to, reply_markup=cancel_markup,
        )
    if submitted_at is not None:
        print(f"[AI Timing] worker_started user={user_id} group={is_group} queue_wait={max(0.0, time.monotonic()-submitted_at):.2f}s")
    if req_id in _CANCEL_REQS:
        _edit_processing_ack(chat_id, status_msg, "❌ درخواست لغو شد.")
        _CANCEL_REQS.discard(req_id)
        return
    if status_msg is None:
        print(f"[AI Worker Error] user={user_id}: could not create a Telegram status message")
        return

    # Only fetch the registry needed for this mode; model registries are warmed at startup.
    chat_models = get_ai_models_cached()
    models = (get_code_models_cached() or chat_models) if active_mode == "CODE" else chat_models
    (active_session_id, history_key, lang, selection_values, user_selected,
     history) = _prepare_ai_context_fast(user_id, target_key_id, is_group, active_mode, chat_id)

    try:
        model_idx = int(user_selected)
    except (TypeError, ValueError):
        model_idx = 0

    if active_mode == "CODE" and models and (model_idx < 0 or model_idx >= len(models)):
        # A dedicated programming model may have just been added or the list reordered.
        model_idx = 0
        safe_kv_put(f"USER_CODE_MODEL_{target_key_id}", "0")

    if not models or model_idx < 0 or model_idx >= len(models):
        need = "مدل برنامه‌نویسی" if active_mode == "CODE" else "مدل چت"
        warning_text = f"⚠️ ابتدا یک {need} در ربات ثبت کنید." if lang == "fa" else f"⚠️ Please add a {('coding' if active_mode == 'CODE' else 'chat')} model first."
        if status_msg is not None:
            try:
                bot.edit_message_text(warning_text, chat_id=chat_id, message_id=status_msg.message_id)
            except Exception:
                try:
                    bot.send_message(chat_id, warning_text, message_thread_id=thread_id)
                except Exception:
                    pass
        else:
            bot.send_message(chat_id, warning_text, message_thread_id=thread_id)
        return

    active_model = models[model_idx]
    if not text_prompt:
        text_prompt = "سلام" if lang == "fa" else "Hello"
        
    try:
        is_greeting = is_casual_greeting(text_prompt)
    except Exception:
        c_test = re.sub(r'[^\w\s]', '', text_prompt).strip().lower()
        is_greeting = c_test in {'سلام', 'درود', 'خوبی', 'چطوری', 'hi', 'hello'}

    # وب‌گردی فقط وقتی فعال است که API انتخاب‌شده واقعاً ابزار بومیِ شناخته‌شده داشته باشد.
    native_web_provider = get_native_web_provider(active_model)
    is_web_query = bool(text_prompt and text_prompt.strip()) and not is_greeting and bool(native_web_provider)

    if is_web_query:
        mode_icon = "🌐"
        initial_text = "🌐 در حال جست‌وجو با ابزار بومی API..." if lang == "fa" else "🌐 Searching with the API's native web tool..."
    else:
        mode_icon = "💻" if active_mode == "CODE" else "💬"
        initial_text = "💬 در حال فکر کردن..." if lang == "fa" else "💬 Thinking..."

    if status_msg is not None:
        _edit_processing_ack(chat_id, status_msg, initial_text, reply_markup=cancel_markup)
    else:
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
    api_response_text = None
    source_links = []
    res = None
    retry_res = None

    try:
        web_context_prompt = ""
        used_web_search = bool(is_web_query)
        user_prompt_final = text_prompt
        current_date_str = get_full_current_date_info()
        if explicit_web_search_requested(text_prompt) and not native_web_provider:
            web_context_prompt = (
                "The connected model endpoint did not match a supported provider-native web-search API. "
                "No native web-search tool is configured for this API. Do not claim you searched the live web; "
                "answer from existing knowledge only and clearly state this limitation when current web facts are required."
            )

        user_content = user_prompt_final

        if message.photo:
            if not active_model.get("supportsVision"):
                bot.edit_message_text("❌ این مدل از تحلیل عکس پشتیبانی نمی‌کند." if lang == "fa" else "❌ This model does not support Vision.", chat_id=chat_id, message_id=status_msg_id)
                return

            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            img_bytes = bot.download_file(file_info.file_path)
            b64_img = base64.b64encode(img_bytes).decode('utf-8')
            user_content = [
                {"type": "text", "text": user_prompt_final},
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
        if base_url.endswith("/chat/completions"):
            endpoint = base_url
        elif base_url.endswith("/v1"):
            endpoint = f"{base_url}/chat/completions"
        else:
            endpoint = f"{base_url}/chat/completions"

        target_lang_str = "Persian (Farsi)" if lang == "fa" else "English"
        if active_mode == "CODE":
            system_prompt_content = (
                f"You are {active_model.get('name')}, a software engineering assistant. "
                f"TODAY'S DATE: {current_date_str}\n"
                f"OPERATING RULES:\n"
                f"1. Provide complete, practical code when possible and explain how to run it in natural {target_lang_str}.\n"
                f"2. Do not claim to execute code, access files, or use tools unless this request actually provides such tools.\n"
                f"3. NEVER output internal thoughts or <think> tags."
            )
        else:
            system_prompt_content = (
                f"You are {active_model.get('name')}, a conversational and research assistant. "
                f"TODAY'S DATE: {current_date_str}\n"
                f"OPERATING RULES:\n"
                f"1. Give direct, well-structured answers in natural {target_lang_str}.\n"
                f"2. Use live web search only if a native search tool is actually enabled by the connected API for this request.\n"
                f"3. If no native web-search tool is available, never pretend to have browsed or verified current facts.\n"
                f"4. Do not invent citations, links, or tool results.\n"
                f"5. NEVER output internal monologue, notes, or <think> tags."
            )

        full_system_text = system_prompt_content
        if web_context_prompt:
            full_system_text += f"\n\n{web_context_prompt}"

        messages_payload = [{"role": "system", "content": full_system_text}] + cleaned_messages

        native_responses_mode = bool(is_web_query and native_web_provider in {"openai_responses", "xai_responses"} and not getattr(message, "photo", None))
        payload = {
            "model": active_model.get("modelName", "").strip(),
            "messages": messages_payload,
            "max_tokens": 4096,
            "stream": not (is_web_query and native_web_provider in {"openrouter", "perplexity"})
        }
        if is_web_query and native_web_provider == "openrouter":
            # This is a provider-side tool: the bot itself does not implement a separate search engine or page crawler.
            payload["tools"] = [{
                "type": "openrouter:web_search",
                "parameters": {"engine": "native", "max_uses": 4, "search_context_size": "medium"},
            }]
            payload["tool_choice"] = "required"

        api_key = active_model.get('apiKey', '').strip()
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream, application/json"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        if req_id in _CANCEL_REQS:
            _edit_processing_ack(chat_id, status_msg, "❌ درخواست لغو شد.")
            return
        api_started_at = time.monotonic()
        first_content_logged = False
        print(
            f"[AI Timing] api_request_started user={user_id} group={is_group} mode={active_mode} "
            f"model={str(active_model.get('modelName', ''))[:80]} "
            f"connect_timeout={API_CONNECT_TIMEOUT_SECONDS}s read_timeout={API_TIMEOUT_SECONDS}s"
        )
        if native_responses_mode:
            responses_payload = {
                "model": active_model.get("modelName", "").strip(),
                "input": messages_payload,
                "tools": [{"type": "web_search", "search_context_size": "medium"}],
                "tool_choice": "required",
                "include": ["web_search_call.action.sources"],
                "max_output_tokens": 4096,
                "store": False,
            }
            res = get_api_http_session().post(
                get_responses_endpoint(base_url), headers=headers,
                json=responses_payload, timeout=(API_CONNECT_TIMEOUT_SECONDS, API_TIMEOUT_SECONDS), stream=False
            )
            print(f"[AI Timing] response_received user={user_id} mode={active_mode} elapsed={time.monotonic()-api_started_at:.2f}s streaming=off")
        else:
            res = get_api_http_session().post(
                endpoint, headers=headers, json=payload,
                timeout=(API_CONNECT_TIMEOUT_SECONDS, API_TIMEOUT_SECONDS), stream=bool(payload.get("stream", True))
            )
            print(f"[AI Timing] response_headers user={user_id} mode={active_mode} elapsed={time.monotonic()-api_started_at:.2f}s content_type={res.headers.get('Content-Type', '')[:80]}")
        res.encoding = 'utf-8'

        if res.status_code == 200:
            if native_responses_mode:
                try:
                    response_data = res.json()
                    api_response_text, source_links = parse_openai_responses_payload(response_data)
                except Exception as parse_exc:
                    api_response_text = f"❌ پاسخ Responses API قابل‌خواندن نبود: {type(parse_exc).__name__}"
            else:
                full_content = ""
                full_reasoning = ""
                content_type = res.headers.get("Content-Type", "").lower()
                is_stream_response = "text/event-stream" in content_type

                if is_stream_response:
                    last_stream_edit = 0.0
                    last_stream_preview = ""
                    # Requests defaults to 512-byte chunks, which can delay short SSE tokens.
                    # A one-byte chunk size yields streamed lines as soon as the provider sends them.
                    for raw_line in res.iter_lines(chunk_size=1, decode_unicode=False):
                        if req_id in _CANCEL_REQS:
                            break
                        if not raw_line:
                            continue
                        line = raw_line.decode('utf-8', errors='replace') if isinstance(raw_line, bytes) else raw_line
                        line = line.strip()
                        if line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                choice = chunk.get("choices", [{}])[0]
                                delta = choice.get("delta", {}) or choice.get("message", {})
                                c = delta.get("content")
                                r = delta.get("reasoning_content") or delta.get("reasoning")
                                if not c and "text" in choice:
                                    c = choice.get("text")
                                if c:
                                    full_content += c
                                    if not first_content_logged:
                                        first_content_logged = True
                                        print(f"[AI Timing] first_content user={user_id} group={is_group} elapsed={time.monotonic()-api_started_at:.2f}s")
                                    # Group users see safe partial text earlier; internal <think> is filtered.
                                    # Keep Telegram edits throttled to avoid excessive edit requests.
                                    if status_msg_id:
                                        now_mono = time.monotonic()
                                        preview = _safe_stream_preview(full_content)
                                        if (len(preview) >= 8 and preview != last_stream_preview
                                                and now_mono - last_stream_edit >= 1.5):
                                            try:
                                                bot.edit_message_text(
                                                    preview[:3900], chat_id=chat_id,
                                                    message_id=status_msg_id, reply_markup=cancel_markup,
                                                )
                                                last_stream_preview = preview[:3900]
                                                last_stream_edit = now_mono
                                                stream_preview_active = True
                                            except ApiTelegramException as stream_exc:
                                                last_stream_edit = now_mono + (3.0 if getattr(stream_exc, "error_code", None) == 429 else 1.0)
                                            except Exception:
                                                last_stream_edit = now_mono + 1.0
                                if r:
                                    full_reasoning += r
                            except Exception:
                                continue

                    clean_c = re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', full_content, flags=re.IGNORECASE).strip()
                    if clean_c:
                        api_response_text = clean_c
                    elif full_reasoning.strip():
                        api_response_text = re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', full_reasoning, flags=re.IGNORECASE).strip()
                    elif full_content.strip():
                        api_response_text = full_content.strip()
                else:
                    try:
                        response_data = res.json()
                    except Exception:
                        response_data = json.loads(res.content.decode('utf-8', errors='replace'))
                    source_links = extract_native_citation_links(response_data)
                    msg_obj = response_data.get("choices", [{}])[0].get("message", {})
                    c = msg_obj.get("content", "")
                    r = msg_obj.get("reasoning_content", "") or msg_obj.get("reasoning", "")
                    clean_c = re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', c, flags=re.IGNORECASE).strip()
                    api_response_text = clean_c or c.strip() or r.strip()

        if not native_responses_mode and (not api_response_text or not api_response_text.strip() or (res.status_code != 200 and res.status_code in [400, 404, 422])):
            try:
                retry_payload = dict(payload)
                retry_payload["stream"] = False
                retry_endpoint = endpoint
                if res.status_code == 404 and "/v1/" not in endpoint and not endpoint.endswith("/v1"):
                    clean_b = base_url.rstrip("/")
                    retry_endpoint = f"{clean_b}/v1/chat/completions"

                retry_res = get_api_http_session().post(
                    retry_endpoint, headers=headers, json=retry_payload,
                    timeout=(API_CONNECT_TIMEOUT_SECONDS, API_TIMEOUT_SECONDS)
                )
                if retry_res.status_code == 200:
                    r_data = retry_res.json()
                    r_msg = r_data.get("choices", [{}])[0].get("message", {})
                    c = r_msg.get("content", "")
                    r = r_msg.get("reasoning_content", "") or r_msg.get("reasoning", "")
                    clean_c = re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', c, flags=re.IGNORECASE).strip()
                    api_response_text = clean_c or c.strip() or r.strip()
            except Exception:
                pass

        print(f"[AI Timing] response_parsed user={user_id} group={is_group} elapsed={time.monotonic()-api_started_at:.2f}s")
        if not api_response_text or not api_response_text.strip():
            if res.status_code != 200:
                api_response_text = f"❌ خطای API ({res.status_code}):\n{res.text[:220]}"

        if api_response_text:
            api_response_text = re.sub(r'<think>[\s\S]*?(?:</think>|$)', '', api_response_text, flags=re.IGNORECASE).strip()
            
            if used_web_search and source_links:
                sources_text = "\n\n🌐 **منابعی که API برگردانده است:**\n"
                for lk in source_links[:3]:
                    domain = urllib.parse.urlparse(lk).netloc
                    sources_text += f"🔹 [{domain}]({lk})\n"
                api_response_text += sources_text

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

            # Update the local sanitized history first so the next prompt has context,
            # then persist in the background without delaying delivery to Telegram.
            _history_cache_put(history_key, hist_to_save)
            if is_group:
                _persist_kv_async(history_key, hist_to_save, 30 * 24 * 60 * 60)
            else:
                _persist_kv_async(history_key, hist_to_save)
                try:
                    _SETTINGS_PERSIST_EXECUTOR.submit(
                        update_session_title_if_new, user_id, active_session_id, text_prompt
                    )
                except Exception as persist_exc:
                    print(f"[Async Session Title Warning] user={user_id}: {type(persist_exc).__name__}")

    except requests.exceptions.Timeout:
        api_response_text = "❌ زمان پاسخ بیش از ۱ ساعت شد و قطع گردید." if lang == "fa" else "❌ Request timed out."
    except requests.exceptions.ConnectionError:
        api_response_text = "❌ خطای قطع ارتباط با سرور هوش مصنوعی." if lang == "fa" else "❌ Connection error with AI server."
    except Exception as e:
        api_response_text = f"❌ Error: {type(e).__name__} - {str(e)[:100]}"
    finally:
        # Always close streamed responses. If a user cancels while a stream is active,
        # this releases the HTTP connection back to the per-worker pool for the next turn.
        for _response in (retry_res, res):
            try:
                if _response is not None:
                    _response.close()
            except Exception:
                pass
        _CANCEL_REQS.discard(req_id)
        safe_kv_delete(f"CANCEL_{req_id}")

    print(f"[AI Timing] worker_finished user={user_id} group={is_group} total={time.monotonic()-worker_started_at:.2f}s")
    if api_response_text and not api_response_text.startswith("❌"):
        # Do not prepend internal user/model metadata to group replies.
        # The temporary status remains generic and never exposes the selected model name.
        final_text = clean_text
        send_safe_ai_response(chat_id, status_msg_id, final_text, reply_to, thread_id)
        
        if active_mode == "CODE" and code_files:
            should_send_file = not is_group or any(w in text_prompt.lower() for w in ['فایل', 'دانلود', 'file', 'script', 'اسکریپت'])
            if should_send_file:
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
                bot.edit_message_text(api_response_text or "❌ پاسخی دریافت نشد. لطفاً مجدداً امتحان کنید.", chat_id=chat_id, message_id=status_msg_id)
            except Exception:
                pass


def worker_ai_process(chat_id, user_id, message, text_prompt, target_key_id, is_group,
                      target_reply_id, thread_id=None, active_mode="CHAT",
                      precreated_status_msg=None, request_id=None, submitted_at=None):
    """Guard the entire AI worker, including model/Redis preflight before API call."""
    try:
        return _worker_ai_process_impl(
            chat_id, user_id, message, text_prompt, target_key_id, is_group, target_reply_id,
            thread_id=thread_id, active_mode=active_mode,
            precreated_status_msg=precreated_status_msg, request_id=request_id,
            submitted_at=submitted_at,
        )
    except Exception as exc:
        print(f"[AI Worker Fatal] user={user_id} group={is_group} error={type(exc).__name__}: {exc}")
        print(traceback.format_exc(limit=8))
        fail_text = "❌ هنگام آماده‌سازی پاسخ خطای داخلی رخ داد؛ لطفاً دوباره تلاش کن."
        if not _edit_processing_ack(chat_id, precreated_status_msg, fail_text):
            try:
                bot.send_message(chat_id, fail_text, message_thread_id=thread_id)
            except Exception as send_exc:
                print(f"[AI Worker Error Notice Failed] user={user_id}: {type(send_exc).__name__}")
        if request_id:
            _CANCEL_REQS.discard(request_id)


# ==========================================
# ۴. پردازش ساخت عکس (استودیوی مستقل تصویرسازی)
# ==========================================
def worker_image_process(chat_id, user_id, prompt_text, target_key_id, thread_id=None, source_message=None, precreated_status_msg=None):
    img_models = get_img_models_cached()
    img_idx_str = safe_kv_get(f"USER_IMG_MODEL_{target_key_id}") or safe_kv_get(f"USER_IMG_MODEL_{user_id}") or "0"
    lang = get_user_lang(user_id)
    try:
        img_idx = int(img_idx_str)
    except:
        img_idx = 0

    if not img_models or img_idx >= len(img_models):
        warning = "⚠️ هیچ مدل تصویرسازی تعریف نشده است." if lang == "fa" else "⚠️ No image models defined."
        if not _edit_processing_ack(chat_id, precreated_status_msg, warning):
            bot.send_message(chat_id, warning, message_thread_id=thread_id)
        return

    active_img_model = img_models[img_idx]

    # اگر فقط آدرس سایت ثبت شده باشد، دکمهٔ سایت را می‌دهیم؛ صفحهٔ عادی سایت API قابل فراخوانی نیست.
    base_url = str(active_img_model.get("baseUrl", "") or "").strip()
    site_url = str(active_img_model.get("siteUrl", "") or "").strip()
    if not base_url and site_url.startswith(("https://", "http://")):
        link_markup = types.InlineKeyboardMarkup()
        link_markup.add(types.InlineKeyboardButton("🌐 باز کردن سایت ساخت عکس", url=site_url))
        bot.send_message(
            chat_id,
            ("این مدل فقط آدرس وب‌سایت دارد و API ساخت عکس تنظیم نشده است. برای تولید مستقیم داخل ربات، Base URL و endpoint مستند API لازم است." if lang == "fa" else
             "This model only has a website URL and no image-generation API endpoint. To generate inside the bot, configure the documented API Base URL/endpoint."),
            reply_markup=link_markup,
            message_thread_id=thread_id,
        )
        return

    # اگر عکس ورودی وجود داشته باشد، همان عکس به endpoint ویرایش ارسال می‌شود.
    source_image_bytes = None
    if source_message is not None:
        photo_sizes = getattr(source_message, "photo", None) or []
        if not photo_sizes and getattr(source_message, "reply_to_message", None):
            photo_sizes = getattr(source_message.reply_to_message, "photo", None) or []
        if photo_sizes:
            try:
                file_info = bot.get_file(photo_sizes[-1].file_id)
                source_image_bytes = bot.download_file(file_info.file_path)
            except Exception as download_exc:
                bot.send_message(
                    chat_id,
                    f"❌ دریافت عکس برای ویرایش ناموفق بود: {download_exc}" if lang == "fa" else f"❌ Could not download the input image: {download_exc}",
                    message_thread_id=thread_id,
                )
                return

    if source_image_bytes and not (prompt_text or "").strip():
        prompt_text = "عکس ورودی را با حفظ سوژه و جزئیات اصلی، به‌صورت طبیعی و باکیفیت ویرایش کن."

    req_id = f"{user_id}_img_{int(time.time()*1000)}"
    cancel_markup = types.InlineKeyboardMarkup()
    cancel_markup.add(types.InlineKeyboardButton(tr(user_id, "cancel_btn"), callback_data=f"cancel_req_{req_id}", style="danger"))

    loading_msg = (f"🖌️ در حال ویرایش عکس با {active_img_model.get('name')}..." if source_image_bytes else f"🎨 در حال ساخت تصویر با {active_img_model.get('name')}...") if lang == "fa" else (f"🖌️ Editing image with {active_img_model.get('name')}..." if source_image_bytes else f"🎨 Generating image with {active_img_model.get('name')}...")
    if precreated_status_msg is not None:
        _edit_processing_ack(chat_id, precreated_status_msg, loading_msg, reply_markup=cancel_markup)
        status_msg = precreated_status_msg
    else:
        status_msg = bot.send_message(
            chat_id,
            loading_msg,
            reply_markup=cancel_markup,
            message_thread_id=thread_id
        )
    status_msg_id = status_msg.message_id
    image_data = None
    error_msg = None

    try:
        base_url = active_img_model.get("baseUrl", "").strip().rstrip("/")
        api_key = active_img_model.get("apiKey", "").strip()
        model_name = active_img_model.get("modelName", "").strip()

        if source_image_bytes:
            edit_prompt = (
                "Edit the provided input image according to the user's instructions. "
                "Preserve the original subject, identity, framing, and all details not explicitly requested to change.\n\n"
                f"User instructions: {prompt_text}"
            )
            if "pollinations.ai" in base_url:
                error_msg = (
                    "این endpoint از Pollinations در این ربات فقط برای ساخت تصویر استفاده می‌شود و API ویرایش عکس ورودی را ارائه نمی‌کند. "
                    "برای ویرایش عکس، یک مدل تصویری سازگار با endpoint استاندارد /v1/images/edits انتخاب کن."
                    if lang == "fa" else
                    "This Pollinations endpoint is configured for image generation only and does not expose an input-image editing endpoint here. "
                    "Choose an image model compatible with /v1/images/edits to edit uploaded photos."
                )
            elif "stability.ai" in base_url:
                edit_url = base_url
                if "/v2beta/stable-image/generate/" in edit_url:
                    edit_url = edit_url.replace("/v2beta/stable-image/generate/", "/v2beta/stable-image/edit/")
                    if edit_url.endswith("/core"):
                        edit_url = edit_url[:-len("/core")] + "/fast"
                edit_headers = {"Authorization": f"Bearer {api_key}", "Accept": "image/*"}
                edit_res = http_session.post(
                    edit_url,
                    headers=edit_headers,
                    files={"image": ("input.jpg", source_image_bytes, "image/jpeg")},
                    data={"prompt": edit_prompt, "output_format": "png"},
                    timeout=(60, API_TIMEOUT_SECONDS),
                )
                if req_id in _CANCEL_REQS:
                    return
                if edit_res.status_code == 200 and edit_res.headers.get("content-type", "").lower().startswith("image/"):
                    image_data = edit_res.content
                elif edit_res.status_code == 200:
                    try:
                        edit_json = edit_res.json()
                        data_list = edit_json.get("data", [])
                        if data_list:
                            if data_list[0].get("b64_json"):
                                image_data = base64.b64decode(data_list[0]["b64_json"])
                            elif data_list[0].get("url"):
                                image_data = data_list[0]["url"]
                    except Exception:
                        pass
                    if not image_data:
                        error_msg = f"پاسخ endpoint ویرایش تصویر قابل‌شناسایی نبود: {edit_res.text[:200]}"
                else:
                    error_msg = f"خطای ویرایش تصویر Stability ({edit_res.status_code}):\n{edit_res.text[:300]}"
            elif "api.xkiro.com" in base_url.lower():
                # xKiro uses async jobs for image edits. Do not pass `n` here:
                # its multipart endpoint can reject the string value sent by requests.
                # The edit job must be polled through /v1/images/generations/{job_id}.
                if "sensenova-u1.5-lite" in model_name.lower():
                    error_msg = (
                        "مدل sensenova/sensenova-u1.5-lite در xKiro فقط ساخت تصویر از متن را پشتیبانی می‌کند و برای ویرایش عکس ورودی مناسب نیست. "
                        "برای ویرایش عکس، مدل openai/gpt-image-2.5 را در بخش مدل تصویر انتخاب کن."
                        if lang == "fa" else
                        "The xKiro sensenova/sensenova-u1.5-lite model supports text-to-image generation only, not input-image editing. "
                        "Select openai/gpt-image-2.5 as the image model to edit uploaded photos."
                    )
                else:
                    clean_base = base_url.rstrip("/")
                    origin = clean_base.split("/v1", 1)[0].rstrip("/")
                    if not origin:
                        origin = "https://api.xkiro.com"
                    edit_endpoint = f"{origin}/v1/images/edits"
                    poll_base = f"{origin}/v1/images/generations"
                    edit_headers = {"Accept": "application/json"}
                    if api_key:
                        edit_headers["Authorization"] = f"Bearer {api_key}"

                    # xKiro expects multipart/form-data. Let requests set its boundary.
                    # `n` is intentionally omitted (the API defaults to one image).
                    edit_data = {
                        "model": model_name,
                        "prompt": edit_prompt,
                        "size": "1024x1024",
                    }
                    edit_res = http_session.post(
                        edit_endpoint,
                        headers=edit_headers,
                        data=edit_data,
                        files={"image": ("input.jpg", source_image_bytes, "image/jpeg")},
                        timeout=(60, API_TIMEOUT_SECONDS),
                    )
                    if req_id in _CANCEL_REQS:
                        return

                    if edit_res.status_code in (200, 202):
                        try:
                            edit_json = edit_res.json()
                        except Exception:
                            edit_json = {}

                        # Some gateways may return the result immediately, but xKiro normally
                        # returns 202 + a job ID.
                        data_items = edit_json.get("data", []) if isinstance(edit_json, dict) else []
                        if data_items:
                            item = data_items[0]
                            if item.get("url"):
                                image_data = item["url"]
                            elif item.get("b64_json"):
                                image_data = base64.b64decode(item["b64_json"])

                        job_id = edit_json.get("id") if isinstance(edit_json, dict) else None
                        if not image_data and job_id:
                            poll_url = f"{poll_base}/{job_id}"
                            deadline = time.time() + API_TIMEOUT_SECONDS
                            poll_interval = 2.0

                            while time.time() < deadline:
                                time.sleep(poll_interval)
                                if req_id in _CANCEL_REQS:
                                    return
                                try:
                                    poll_res = http_session.get(
                                        poll_url,
                                        headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                                        timeout=20,
                                    )
                                    if poll_res.status_code in (200, 202):
                                        try:
                                            poll_data = poll_res.json()
                                        except Exception:
                                            poll_data = {}
                                        status = poll_data.get("status") if isinstance(poll_data, dict) else None
                                        if status == "succeeded":
                                            data_items = poll_data.get("data", [])
                                            if data_items:
                                                item = data_items[0]
                                                if item.get("url"):
                                                    image_data = item["url"]
                                                elif item.get("b64_json"):
                                                    image_data = base64.b64decode(item["b64_json"])
                                            if not image_data:
                                                error_msg = "کار ساخت تصویر موفق اعلام شد، اما نتیجه‌ای در data[] وجود نداشت."
                                            break
                                        if status in ("failed", "blocked"):
                                            upstream_error = poll_data.get("error", status)
                                            if isinstance(upstream_error, dict):
                                                upstream_error = upstream_error.get("message") or status
                                            error_msg = f"پردازش تصویر در xKiro با وضعیت {status} پایان یافت: {upstream_error}"
                                            break
                                        # processing / pending / queued: keep polling.
                                    else:
                                        error_msg = f"خطای پیگیری job در xKiro (HTTP {poll_res.status_code}):\n{poll_res.text[:400]}"
                                        break
                                except Exception as poll_exc:
                                    print(f"[xKiro Image Polling Error]: {poll_exc}")
                                poll_interval = min(poll_interval * 1.5, 10.0)

                            if not image_data and not error_msg:
                                error_msg = "زمان انتظار برای ویرایش عکس در xKiro به پایان رسید (Timeout)."
                        elif not image_data and not job_id:
                            error_msg = f"پاسخ xKiro فاقد شناسه job یا تصویر بود: {edit_res.text[:400]}"
                    else:
                        error_msg = (
                            f"خطای ویرایش تصویر xKiro (HTTP {edit_res.status_code}):\n{edit_res.text[:700]}"
                        )
            else:
                clean_base = base_url.rstrip("/")
                if clean_base.endswith("/images/edits"):
                    edit_endpoint = clean_base
                elif clean_base.endswith("/images/generations"):
                    edit_endpoint = clean_base[:-len("/images/generations")] + "/images/edits"
                elif clean_base.endswith("/v1"):
                    edit_endpoint = clean_base + "/images/edits"
                elif "/v1/" in clean_base:
                    edit_endpoint = clean_base.split("/images/", 1)[0] + "/images/edits" if "/images/" in clean_base else clean_base.rstrip("/") + "/images/edits"
                else:
                    edit_endpoint = clean_base + "/v1/images/edits"

                edit_headers = {"Connection": "keep-alive", "Accept": "application/json"}
                if api_key:
                    edit_headers["Authorization"] = f"Bearer {api_key}"
                edit_data = {"model": model_name, "prompt": edit_prompt, "n": "1", "size": "1024x1024"}
                # OpenAI documents the multipart field as image[]; some compatible gateways use image.
                field_name = "image[]" if "api.openai.com" in edit_endpoint.lower() else "image"
                edit_res = http_session.post(
                    edit_endpoint,
                    headers=edit_headers,
                    data=edit_data,
                    files={field_name: ("input.jpg", source_image_bytes, "image/jpeg")},
                    timeout=(60, API_TIMEOUT_SECONDS),
                )
                if req_id in _CANCEL_REQS:
                    return
                # Retry once with the alternate field name for OpenAI-compatible APIs.
                if edit_res.status_code in (400, 422) and any(word in edit_res.text.lower() for word in ("image[]", "image field", "missing image", "image is required")):
                    alt_name = "image" if field_name == "image[]" else "image[]"
                    edit_res = http_session.post(
                        edit_endpoint,
                        headers=edit_headers,
                        data=edit_data,
                        files={alt_name: ("input.jpg", source_image_bytes, "image/jpeg")},
                        timeout=(60, API_TIMEOUT_SECONDS),
                    )
                if edit_res.status_code == 200:
                    try:
                        edit_json = edit_res.json()
                    except Exception:
                        edit_json = None
                    data_list = edit_json.get("data", []) if isinstance(edit_json, dict) else []
                    if data_list:
                        item = data_list[0]
                        if item.get("b64_json"):
                            image_data = base64.b64decode(item["b64_json"])
                        elif item.get("url"):
                            image_data = item["url"]
                    if not image_data:
                        error_msg = "پاسخ API ویرایش تصویر فاقد data[0].url یا data[0].b64_json است."
                else:
                    error_msg = (
                        f"ویرایش عکس توسط این endpoint انجام نشد (HTTP {edit_res.status_code}).\n"
                        f"{edit_res.text[:500]}\n\n"
                        "اگر مدل فقط ساخت تصویر را پشتیبانی می‌کند یا endpoint ویرایش را ندارد، باید endpoint ویرایش همان سرویس تنظیم شود."
                    )
        elif "stability.ai" in base_url:
            headers = {"Authorization": f"Bearer {api_key}", "Accept": "image/*"}
            res = http_session.post(
                base_url,
                headers=headers,
                files={"none": ''},
                data={"prompt": prompt_text, "output_format": "webp"},
                timeout=(60, API_TIMEOUT_SECONDS)
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
            clean_base = base_url.rstrip("/")
            if clean_base.endswith("/images/generations"):
                endpoint = clean_base
            elif clean_base.endswith("/v1"):
                endpoint = f"{clean_base}/images/generations"
            else:
                endpoint = f"{clean_base}/v1/images/generations" if "/v1" not in clean_base else f"{clean_base}/images/generations"

            headers = {
                "Content-Type": "application/json",
                "Connection": "keep-alive"
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {"model": model_name, "prompt": prompt_text, "n": 1, "size": "1024x1024"}
            res = http_session.post(endpoint, headers=headers, json=payload, timeout=(60, API_TIMEOUT_SECONDS))
            if req_id in _CANCEL_REQS:
                return
            
            res_json = None
            try:
                res_json = res.json()
            except Exception:
                pass

            if res.status_code == 200 and res_json and "data" in res_json and isinstance(res_json["data"], list) and len(res_json["data"]) > 0:
                d_item = res_json["data"][0]
                if "url" in d_item:
                    image_data = d_item.get("url")
                elif "b64_json" in d_item:
                    image_data = base64.b64decode(d_item.get("b64_json"))

            elif (res.status_code == 202 or (res.status_code == 200 and res_json and res_json.get("status") in ["processing", "pending", "queued"])) and res_json:
                job_id = res_json.get("id")
                if not job_id:
                    error_msg = f"Job ID missing in response:\n{res.text[:200]}"
                else:
                    poll_url = f"{endpoint.rstrip('/')}/{job_id}"
                    deadline = time.time() + API_TIMEOUT_SECONDS
                    poll_headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                    poll_interval = 2.0

                    while time.time() < deadline:
                        time.sleep(poll_interval)
                        if req_id in _CANCEL_REQS:
                            return

                        try:
                            poll_res = http_session.get(poll_url, headers=poll_headers, timeout=20)
                            if poll_res.status_code == 200:
                                p_data = poll_res.json()
                                p_status = p_data.get("status")
                                if p_status == "succeeded":
                                    d_list = p_data.get("data", [])
                                    if d_list and len(d_list) > 0:
                                        if "url" in d_list[0]:
                                            image_data = d_list[0].get("url")
                                        elif "b64_json" in d_list[0]:
                                            image_data = base64.b64decode(d_list[0].get("b64_json"))
                                    break
                                elif p_status in ["failed", "blocked"]:
                                    err_text = p_data.get("error", {}).get("message") or p_status
                                    error_msg = f"خطا در پردازش تصویر ({p_status}): {err_text}"
                                    break
                                elif p_status in ["processing", "pending", "queued"]:
                                    continue
                                else:
                                    d_list = p_data.get("data", [])
                                    if d_list and len(d_list) > 0:
                                        image_data = d_list[0].get("url")
                                        break
                            elif poll_res.status_code == 202:
                                continue
                            else:
                                error_msg = f"کد خطای استعلام ({poll_res.status_code}):\n{poll_res.text[:200]}"
                                break
                        except Exception as pe:
                            print(f"[Polling Error]: {pe}")
                            continue

                    if not image_data and not error_msg:
                        error_msg = "زمان ساخت تصویر توسط سرور به پایان رسید (Timeout)."
            else:
                error_msg = f"Code: {res.status_code}\n{res.text[:200]}"

    except Exception as e:
        error_msg = str(e)

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
        fail_markup = None
        if site_url.startswith(("https://", "http://")):
            fail_markup = types.InlineKeyboardMarkup()
            fail_markup.add(types.InlineKeyboardButton("🌐 باز کردن سایت ساخت عکس", url=site_url))
        try:
            bot.edit_message_text(f"❌ ساخت تصویر با خطا مواجه شد.\n{error_msg or ''}" if lang == "fa" else f"❌ Image generation failed.\n{error_msg or ''}", chat_id=chat_id, message_id=status_msg_id, reply_markup=fail_markup)
        except Exception:
            pass

# ==========================================
# 🎬 پردازش ویدیو با APIهای JSON/Job-based متداول
# ==========================================
def _video_generation_endpoint(base_url):
    value = str(base_url or "").strip().rstrip("/")
    if not value:
        return ""
    known_suffixes = ("/v1/videos/generations", "/videos/generations", "/v1/videos", "/videos")
    if any(value.lower().endswith(suffix) for suffix in known_suffixes):
        return value
    if value.lower().endswith("/v1"):
        return value + "/videos/generations"
    return value + "/v1/videos/generations"


def _find_video_url(payload):
    """Extract likely output video URLs from common JSON API response shapes."""
    url_keys = ("video_url", "videoUrl", "output_url", "outputUrl", "result_url", "resultUrl", "download_url", "downloadUrl")
    if isinstance(payload, dict):
        for key in url_keys:
            value = payload.get(key)
            if isinstance(value, str) and value.startswith(("https://", "http://")):
                return value
        # A plain `url` is only considered if it looks like an output rather than a status endpoint.
        value = payload.get("url")
        if isinstance(value, str) and value.startswith(("https://", "http://")):
            low = value.lower().split("?", 1)[0]
            if any(ext in low for ext in (".mp4", ".webm", ".mov", ".m4v")) or payload.get("status") in {"succeeded", "completed", "success", "done"}:
                return value
        for key in ("data", "output", "result", "results", "artifacts", "videos"):
            value = payload.get(key)
            found = _find_video_url(value)
            if found:
                return found
        # Providers sometimes nest the actual answer under a video object.
        for value in payload.values():
            if isinstance(value, (dict, list)):
                found = _find_video_url(value)
                if found:
                    return found
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, str) and item.startswith(("https://", "http://")):
                low = item.lower().split("?", 1)[0]
                if any(ext in low for ext in (".mp4", ".webm", ".mov", ".m4v")):
                    return item
            found = _find_video_url(item)
            if found:
                return found
    return None


def _find_video_job_id(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("id", "job_id", "jobId", "task_id", "taskId", "request_id", "requestId"):
        value = payload.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value).strip()
    for key in ("data", "result", "job", "task"):
        value = payload.get(key)
        if isinstance(value, dict):
            found = _find_video_job_id(value)
            if found:
                return found
    return None


def _status_url_for_video_model(model, endpoint, job_id):
    template = str(model.get("statusUrlTemplate", "") or "").strip()
    if template:
        candidate = template.replace("{id}", urllib.parse.quote(str(job_id), safe=""))
        try:
            base_host = (urllib.parse.urlparse(endpoint).hostname or "").lower()
            target = urllib.parse.urlparse(candidate)
            if target.scheme in ("https", "http") and target.hostname and target.hostname.lower() == base_host:
                return candidate
        except Exception:
            pass
    return endpoint.rstrip("/") + "/" + urllib.parse.quote(str(job_id), safe="")


def worker_video_process(chat_id, user_id, prompt_text, target_key_id, thread_id=None, precreated_status_msg=None):
    lang = get_user_lang(user_id)
    models = get_video_models_cached()
    try:
        idx = int(safe_kv_get(f"USER_VIDEO_MODEL_{target_key_id}") or safe_kv_get(f"USER_VIDEO_MODEL_{user_id}") or "0")
    except (TypeError, ValueError):
        idx = 0
    if not models or idx < 0 or idx >= len(models):
        warning = "⚠️ هنوز مدل ساخت ویدیویی تعریف نشده است. از ادمین بخواه یک مدل ویدیو اضافه کند." if lang == "fa" else "⚠️ No video models are configured. Ask the admin to add one."
        if not _edit_processing_ack(chat_id, precreated_status_msg, warning):
            bot.send_message(chat_id, warning, message_thread_id=thread_id)
        return

    model = models[idx]
    model_name = str(model.get("name", "Video model"))
    base_url = str(model.get("baseUrl", "") or "").strip()
    api_key = str(model.get("apiKey", "") or "").strip()
    api_model_name = str(model.get("modelName", "") or "").strip()
    site_url = str(model.get("siteUrl", "") or "").strip()

    if not base_url:
        if site_url.startswith(("https://", "http://")):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🌐 باز کردن سایت ساخت ویدیو", url=site_url))
            note = ("این مدل فقط آدرس سایت دارد؛ برای ساخت ویدیو داخل خود ربات باید endpoint مستند API هم وارد شود. فعلاً می‌توانی سایت را باز کنی." if lang == "fa" else
                    "This model has a website URL only. To generate videos inside Telegram, configure its documented API endpoint. You can open the website for now.")
            if not _edit_processing_ack(chat_id, precreated_status_msg, note, reply_markup=markup):
                bot.send_message(chat_id, note, reply_markup=markup, message_thread_id=thread_id)
        else:
            note = "❌ برای این مدل Base URL/Endpoint API تنظیم نشده است."
            if not _edit_processing_ack(chat_id, precreated_status_msg, note):
                bot.send_message(chat_id, note, message_thread_id=thread_id)
        return

    if not prompt_text or not prompt_text.strip():
        note = "لطفاً توضیح ویدیویی که می‌خواهی ساخته شود را بنویس."
        if not _edit_processing_ack(chat_id, precreated_status_msg, note):
            bot.send_message(chat_id, note, message_thread_id=thread_id)
        return

    endpoint = _video_generation_endpoint(base_url)
    parsed_endpoint = urllib.parse.urlparse(endpoint)
    if parsed_endpoint.scheme not in ("https", "http") or not parsed_endpoint.hostname:
        bot.send_message(chat_id, "❌ آدرس API ویدیو معتبر نیست. آدرس کامل https:// را وارد کن.", message_thread_id=thread_id)
        return

    req_id = f"{user_id}_video_{int(time.time() * 1000)}"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(tr(user_id, "cancel_btn"), callback_data=f"cancel_req_{req_id}", style="danger"))
    loading_text = (f"🎬 درخواست ساخت ویدیو با {model_name} ثبت شد؛ در حال پردازش..." if lang == "fa" else f"🎬 Video generation with {model_name} is processing...")
    if precreated_status_msg is not None:
        _edit_processing_ack(chat_id, precreated_status_msg, loading_text, reply_markup=markup)
        status_msg = precreated_status_msg
    else:
        status_msg = bot.send_message(chat_id, loading_text, reply_markup=markup, message_thread_id=thread_id)
    video_url = None
    video_bytes = None
    error_msg = None
    try:
        headers = {"Accept": "application/json, video/*", "Connection": "keep-alive"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {"prompt": prompt_text.strip()}
        if api_model_name:
            payload["model"] = api_model_name

        # This common JSON/job adapter covers APIs that accept prompt/model JSON and return a URL or a job ID.
        # APIs with proprietary payloads require a provider-specific adapter; a webpage URL is not an API.
        response = http_session.post(endpoint, headers=headers, json=payload, timeout=(30, API_TIMEOUT_SECONDS))
        if req_id in _CANCEL_REQS:
            return
        content_type = str(response.headers.get("content-type", "")).lower()
        if response.status_code in (200, 201) and content_type.startswith("video/"):
            video_bytes = response.content
        else:
            try:
                result = response.json()
            except Exception:
                result = {}
            if response.status_code not in (200, 201, 202):
                detail = result.get("error", {}) if isinstance(result, dict) else {}
                if isinstance(detail, dict):
                    detail = detail.get("message") or detail.get("detail") or detail
                error_msg = f"HTTP {response.status_code}: {str(detail or response.text)[:700]}"
            else:
                video_url = _find_video_url(result)
                if not video_url:
                    job_id = _find_video_job_id(result)
                    status_val = str(result.get("status", "") if isinstance(result, dict) else "").lower()
                    if job_id and (response.status_code == 202 or status_val in {"queued", "pending", "processing", "in_progress", "running", "starting"} or not video_url):
                        poll_url = _status_url_for_video_model(model, endpoint, job_id)
                        deadline = time.time() + API_TIMEOUT_SECONDS
                        interval = 3.0
                        while time.time() < deadline:
                            if req_id in _CANCEL_REQS:
                                return
                            time.sleep(interval)
                            poll_res = http_session.get(poll_url, headers=headers, timeout=(15, 45))
                            if poll_res.status_code not in (200, 202):
                                if poll_res.status_code == 404 and endpoint.lower().endswith("/videos/generations"):
                                    # Some APIs use /v1/videos/{id} for status even when creation uses /v1/videos/generations.
                                    alternate = re.sub(r"/videos/generations$", "/videos", endpoint, flags=re.IGNORECASE).rstrip("/") + "/" + urllib.parse.quote(job_id, safe="")
                                    alt_res = http_session.get(alternate, headers=headers, timeout=(15, 45))
                                    if alt_res.status_code in (200, 202):
                                        poll_res = alt_res
                                        poll_url = alternate
                                    else:
                                        error_msg = f"خطای استعلام وضعیت ویدیو (HTTP {poll_res.status_code}): {poll_res.text[:300]}"
                                        break
                                else:
                                    error_msg = f"خطای استعلام وضعیت ویدیو (HTTP {poll_res.status_code}): {poll_res.text[:300]}"
                                    break
                            try:
                                poll_data = poll_res.json()
                            except Exception:
                                poll_data = {}
                            video_url = _find_video_url(poll_data)
                            if video_url:
                                break
                            p_status = str((poll_data.get("status") or poll_data.get("state") or "") if isinstance(poll_data, dict) else "").lower()
                            if p_status in {"failed", "error", "cancelled", "canceled", "rejected", "blocked"}:
                                err = poll_data.get("error") or poll_data.get("message") or p_status
                                if isinstance(err, dict):
                                    err = err.get("message") or err.get("detail") or str(err)
                                error_msg = f"ساخت ویدیو ناموفق بود: {str(err)[:500]}"
                                break
                            if p_status in {"completed", "complete", "succeeded", "success", "succeeded", "done"}:
                                # OpenAI-style video APIs expose a content endpoint when status is completed.
                                content_url = poll_url.rstrip("/") + "/content"
                                content_res = http_session.get(content_url, headers={**headers, "Accept": "video/*"}, timeout=(30, 240))
                                if content_res.status_code == 200 and str(content_res.headers.get("content-type", "")).lower().startswith("video/"):
                                    video_bytes = content_res.content
                                else:
                                    error_msg = "وضعیت job تکمیل شد، اما URL یا محتوای ویدیو در پاسخ API پیدا نشد."
                                break
                            interval = min(interval * 1.25, 10.0)
                        if not video_url and not video_bytes and not error_msg:
                            error_msg = "مهلت انتظار برای ساخت ویدیو به پایان رسید (۱ ساعت)."
                    else:
                        detail = result.get("error") or result.get("message") or result if isinstance(result, dict) else response.text
                        if isinstance(detail, dict):
                            detail = detail.get("message") or detail.get("detail") or str(detail)
                        error_msg = f"پاسخ API شامل URL ویدیو یا شناسهٔ job قابل‌شناسایی نبود: {str(detail)[:500]}"

        if req_id in _CANCEL_REQS:
            return
        if video_url and not video_bytes:
            video_res = http_session.get(video_url, headers={"Connection": "keep-alive"}, timeout=(30, 240), stream=True)
            if video_res.status_code == 200:
                chunks = []
                total = 0
                for chunk in video_res.iter_content(chunk_size=1024 * 512):
                    if req_id in _CANCEL_REQS:
                        return
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > 49 * 1024 * 1024:
                        error_msg = "فایل ویدیو از سقف ۴۹ مگابایت این آپلودر بزرگ‌تر است؛ لینک خروجی را باز کن."
                        break
                    chunks.append(chunk)
                if not error_msg:
                    video_bytes = b"".join(chunks)
            else:
                error_msg = f"دریافت فایل ویدیو ناموفق بود (HTTP {video_res.status_code})."

        if video_bytes and len(video_bytes) > 49 * 1024 * 1024:
            error_msg = "حجم ویدیو از سقف ۴۹ مگابایت آپلود این ربات بیشتر است."
            video_bytes = None

    except requests.RequestException as exc:
        error_msg = f"خطای شبکه هنگام اتصال به API ویدیو: {str(exc)[:500]}"
    except Exception as exc:
        error_msg = f"خطای پردازش ویدیو: {str(exc)[:500]}"

    if req_id in _CANCEL_REQS:
        _CANCEL_REQS.discard(req_id)
        safe_kv_delete(f"CANCEL_{req_id}")
        try:
            bot.edit_message_text("❌ ساخت ویدیو لغو شد." if lang == "fa" else "❌ Video generation canceled.", chat_id=chat_id, message_id=status_msg.message_id)
        except Exception:
            pass
        return
    _CANCEL_REQS.discard(req_id)
    safe_kv_delete(f"CANCEL_{req_id}")

    if video_bytes:
        try:
            bot.delete_message(chat_id, status_msg.message_id)
        except Exception:
            pass
        file_obj = io.BytesIO(video_bytes)
        file_obj.name = "generated_video.mp4"
        caption = (f"🎬 ویدیو با مدل {model_name} ساخته شد.\\n📝 پرامپت: {prompt_text[:700]}" if lang == "fa" else f"🎬 Video generated with {model_name}.\\n📝 Prompt: {prompt_text[:700]}")
        try:
            bot.send_video(chat_id, file_obj, caption=caption[:1000], supports_streaming=True, message_thread_id=thread_id)
        except Exception as send_exc:
            if video_url:
                link_markup = types.InlineKeyboardMarkup()
                link_markup.add(types.InlineKeyboardButton("▶️ باز کردن ویدیو", url=video_url))
                bot.send_message(chat_id, f"آپلود ویدیو به تلگرام ناموفق بود: {str(send_exc)[:250]}\\nلینک مستقیم خروجی:", reply_markup=link_markup, message_thread_id=thread_id)
            else:
                bot.send_message(chat_id, f"❌ آپلود ویدیو ناموفق بود: {str(send_exc)[:350]}", message_thread_id=thread_id)
    else:
        message = (f"❌ ساخت ویدیو ناموفق بود.\\n{error_msg or 'جزئیات بیشتری از API دریافت نشد.'}" if lang == "fa" else f"❌ Video generation failed.\\n{error_msg or 'The API returned no further details.'}")
        reply_markup = None
        # If an output URL is available but the file could not be uploaded (e.g. >49 MB),
        # expose that result URL first; otherwise offer the configured provider site.
        if video_url and video_url.startswith(("https://", "http://")):
            reply_markup = types.InlineKeyboardMarkup()
            reply_markup.add(types.InlineKeyboardButton("▶️ باز کردن ویدیو", url=video_url))
        elif site_url.startswith(("https://", "http://")):
            reply_markup = types.InlineKeyboardMarkup()
            reply_markup.add(types.InlineKeyboardButton("🌐 باز کردن سایت سرویس", url=site_url))
        try:
            bot.edit_message_text(message[:3900], chat_id=chat_id, message_id=status_msg.message_id, reply_markup=reply_markup)
        except Exception:
            bot.send_message(chat_id, message[:3900], reply_markup=reply_markup, message_thread_id=thread_id)


# ==========================================
# ⚡ هندلر اختصاصی دستور /start (زیر ۰.۲ ثانیه)
# ==========================================
@bot.message_handler(commands=['start'])
def handle_start_command(msg):
    chat_id = msg.chat.id
    user_id = str(msg.from_user.id)
    first_name = msg.from_user.first_name or "کاربر"
    username = msg.from_user.username or ""
    is_group = msg.chat.type in ["group", "supergroup"]
    thread_id = getattr(msg, 'message_thread_id', None) if getattr(msg, 'is_topic_message', False) else None

    if not is_bot_globally_active() and user_id != ADMIN_ID:
        notify_bot_disabled_once(chat_id, thread_id)
        return

    track_user_activity(user_id, first_name, username)

    if is_group:
        if not is_group_admin(chat_id, user_id):
            return
        bot_info = get_bot_info_cached()
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

    ok_sponsor, unjoined = check_sponsor_join(user_id)
    if not ok_sponsor and ADMIN_ID and user_id != ADMIN_ID:
        markup = build_sponsor_markup(user_id, unjoined)
        bot.send_message(chat_id, tr(user_id, "sponsor_warn"), parse_mode="Markdown", reply_markup=markup)
        return

    threading.Thread(target=clear_user_state, args=(user_id,), daemon=True).start()
    # Create/register the current conversation automatically so history never needs manual setup.
    get_or_create_active_session(user_id)
    send_main_menu(chat_id, user_id)

# ==========================================
# ۵. هندلر پیام‌ها و تفکیک کامل دستورات و هوش مصنوعی
# ==========================================
@bot.message_handler(content_types=['text', 'photo', 'document', 'video', 'audio', 'voice', 'sticker'])
def handle_all_messages(msg):
    handler_received_at = time.monotonic()
    if not msg.from_user:
        return

    chat_id = msg.chat.id
    user_id = str(msg.from_user.id)
    first_name = msg.from_user.first_name or "کاربر"
    username = msg.from_user.username or ""
    text = msg.text or msg.caption or ""
    command_text = str(text or "").strip()
    command_lower = command_text.lower()
    is_group = msg.chat.type in ["group", "supergroup"]
    thread_id = getattr(msg, 'message_thread_id', None) if getattr(msg, 'is_topic_message', False) else None
    target_key_id = f"group_{chat_id}" if is_group else user_id
    pre_ack_msg = None
    keyboard_labels = {"📋 منوی اصلی", "📋 Main Menu", "📜 تاریخچه گفتگوها", "📜 Chat History", "⚙️ مدیریت ربات", "⚙️ Admin Panel"}
    # Only private-chat messages may receive a generic early acknowledgement.
    # In groups, an acknowledgement is allowed exclusively after an explicit bot
    # invocation (prefix/@mention) or a reply to this bot. Otherwise, replying to
    # an ordinary user's message must stay silent and must not leave a stuck status.
    plain_private_candidate = (
        not is_group
        and bool(msg.text)
        and not command_text.startswith("/")
        and command_text not in keyboard_labels
    )

    # For group calls, only acknowledge messages that really look like a call/reply to this bot.
    early_group_call = False
    early_invoked = False
    if is_group and bool(msg.text):
        cached_bot_username = str(getattr(_BOT_INFO_CACHE, "username", "") or "")
        early_invoked, _early_prompt = extract_group_invocation(command_text, cached_bot_username)
        reply_from_user = getattr(getattr(msg, "reply_to_message", None), "from_user", None)
        token_bot_id = BOT_TOKEN.split(":", 1)[0] if ":" in BOT_TOKEN else ""
        is_early_reply_to_bot = bool(reply_from_user and (
            str(getattr(reply_from_user, "id", "")) == str(token_bot_id) and token_bot_id.isdigit()
            or (cached_bot_username and str(getattr(reply_from_user, "username", "") or "").lower() == cached_bot_username.lower())
        ))
        is_early_bot_control = bool(re.match(
            r"^(?:/bot|ربات|روبات|بات|نئو|نعو)\s*(?:صحبت|حرف\s*بزن|فعال|روشن|سکوت|بی\s*صدا|ساکت|خاموش)$",
            command_text, flags=re.IGNORECASE
        ))
        is_early_reply_moderation = bool(msg.reply_to_message and reply_from_user and not is_early_reply_to_bot and re.match(
            r"^(?:نئو|نعو|neo|tenet|ربات|روبات|بات)?\s*(?:سکوت|بی\s*صدا|بیصدا|ساکت|اخراج|بن|مسدود|حذف|پاک|رفع سکوت|رفع بی\s*صدا|/mute|/ban|/kick|/del|/delete)",
            command_text, flags=re.IGNORECASE
        ))
        early_group_call = (early_invoked or is_early_reply_to_bot) and not is_early_bot_control and not is_early_reply_moderation

    should_fast_ack = (plain_private_candidate and user_id != ADMIN_ID) or early_group_call
    # Don't create an acknowledgement while an explicitly-disabled bot is already known to be off.
    if should_fast_ack and _BOT_STATUS_CACHE is not False:
        # Use one stable status label. It is upgraded with a cancel button at queue submission.
        early_text = "💬 در حال فکر کردن..."
        pre_ack_msg = _send_processing_ack(
            chat_id, early_text, thread_id=thread_id,
            reply_to_message_id=(msg.message_id if is_group else None),
        )

    if not is_bot_globally_active() and user_id != ADMIN_ID:
        if pre_ack_msg is not None:
            if not _edit_processing_ack(chat_id, pre_ack_msg, "⚠️ ربات موقتاً توسط مدیریت خاموش است.", parse_mode="Markdown"):
                _delete_processing_ack(chat_id, pre_ack_msg)
                notify_bot_disabled_once(chat_id, thread_id)
        else:
            notify_bot_disabled_once(chat_id, thread_id)
        return

    track_user_activity(user_id, first_name, username)

    # Persistent reply-keyboard actions are handled before admin wizards, so the user can always navigate.
    if not is_group and command_text in {"📋 منوی اصلی", "📋 Main Menu"}:
        clear_user_state(user_id)
        safe_kv_delete(f"VIDEO_PROMPT_AWAITING_{user_id}")
        send_main_menu(chat_id, user_id)
        return
    if not is_group and command_text in {"📜 تاریخچه گفتگوها", "📜 Chat History"}:
        clear_user_state(user_id)
        safe_kv_delete(f"VIDEO_PROMPT_AWAITING_{user_id}")
        send_history_menu(chat_id, user_id)
        return
    if not is_group and command_text in {"⚙️ مدیریت ربات", "⚙️ Admin Panel"}:
        if user_id != ADMIN_ID:
            bot.send_message(chat_id, "⛔ این دکمه فقط برای ادمین اصلی فعال است.")
        else:
            clear_user_state(user_id)
            safe_kv_delete(f"VIDEO_PROMPT_AWAITING_{user_id}")
            bot.send_message(chat_id, "🛠 پنل مدیریت ربات", reply_markup=get_admin_panel_markup())
        return

    if not is_group and user_id == ADMIN_ID:
        admin_step = safe_kv_get(f"ADMIN_STEP_{user_id}")
        
        if admin_step and admin_step.startswith("DM_TO_"):
            target_uid = admin_step.replace("DM_TO_", "")
            safe_kv_delete(f"ADMIN_STEP_{user_id}")
            try:
                bot.send_message(target_uid, "📩 **پیام مستقیم از طرف مدیریت ربات:**", parse_mode="Markdown")
                bot.copy_message(chat_id=target_uid, from_chat_id=chat_id, message_id=msg.message_id)
                bot.send_message(chat_id, f"✅ پیام شما با موفقیت به کاربر `{target_uid}` تحویل داده شد.", parse_mode="Markdown")
                send_user_profile_card(chat_id, target_uid)
            except Exception as e:
                mark_user_unreachable(target_uid, e)
                bot.send_message(chat_id, f"❌ خطا در ارسال پیام به کاربر: {e}")
            return

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
                                    "date": item.get("date", get_jalali_date()),
                                    "created_at": item.get("created_at")
                                })
                                existing_sids.add(sid)
                            else:
                                for existing_item in cur_sessions:
                                    if str(existing_item.get("id")) == str(sid) and not existing_item.get("created_at") and item.get("created_at"):
                                        existing_item["created_at"] = item.get("created_at")
                                        break
                            msgs = item.get("messages", [])
                            if msgs:
                                safe_kv_put(f"HISTORY_{u_str}_{sid}", msgs)
                                restored_sessions += 1

                    cur_sessions = save_sessions_limited(u_str, cur_sessions)
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

    if pre_ack_msg is None and plain_private_candidate and user_id == ADMIN_ID and _BOT_STATUS_CACHE is not False:
        pre_ack_msg = _send_processing_ack(chat_id, "💬 در حال فکر کردن...", thread_id=thread_id)

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

    if is_user_banned_cached(user_id):
        banned_text = "⛔ حساب شما توسط مدیریت مسدود شده است."
        if not _edit_processing_ack(chat_id, pre_ack_msg, banned_text):
            bot.send_message(chat_id, banned_text, message_thread_id=thread_id)
        return

    if not is_group and safe_kv_get(f"USER_SUPPORT_STEP_{user_id}") == "AWAITING_MSG":
        safe_kv_delete(f"USER_SUPPORT_STEP_{user_id}")
        _edit_processing_ack(chat_id, pre_ack_msg, "📨 پیام شما در حال ارسال به پشتیبانی است...")
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
            if not _edit_processing_ack(chat_id, pre_ack_msg, "✅ پیام شما با موفقیت به پشتیبانی ارسال شد."):
                bot.send_message(chat_id, "✅ پیام شما با موفقیت به پشتیبانی ارسال شد.")
        except Exception as e:
            error_text = f"❌ خطا در ارسال: {e}"
            if not _edit_processing_ack(chat_id, pre_ack_msg, error_text):
                bot.send_message(chat_id, error_text)
        return

    if not is_group:
        ok_sponsor, unjoined = check_sponsor_join(user_id)
        if not ok_sponsor and ADMIN_ID and user_id != ADMIN_ID:
            markup = build_sponsor_markup(user_id, unjoined)
            if not _edit_processing_ack(chat_id, pre_ack_msg, tr(user_id, "sponsor_warn"), reply_markup=markup, parse_mode="Markdown"):
                bot.send_message(chat_id, tr(user_id, "sponsor_warn"), parse_mode="Markdown", reply_markup=markup)
            return

    if (not is_group and safe_kv_get(f"VIDEO_PROMPT_AWAITING_{user_id}") == "true"
            and command_text and not command_text.startswith("/")):
        safe_kv_delete(f"VIDEO_PROMPT_AWAITING_{user_id}")
        if not _submit_bounded(
            _VIDEO_JOB_EXECUTOR, _VIDEO_JOB_SLOTS, worker_video_process,
            chat_id, user_id, command_text[:2000], target_key_id, thread_id, pre_ack_msg,
        ):
            _notify_job_queue_full(chat_id, thread_id, pre_ack_msg)
        return

    if command_lower.startswith("/video") and not is_group:
        pieces = command_text.split(maxsplit=1)
        prompt = pieces[1].strip() if len(pieces) > 1 else ""
        _USER_MODES_CACHE[target_key_id] = "VIDEO"
        _persist_kv_async(f"BOT_MODE_{target_key_id}", "VIDEO")
        if prompt:
            if not _submit_bounded(
                _VIDEO_JOB_EXECUTOR, _VIDEO_JOB_SLOTS, worker_video_process,
                chat_id, user_id, prompt, target_key_id, thread_id,
            ):
                _notify_job_queue_full(chat_id, thread_id)
        else:
            bot.send_message(chat_id, "🎬 حالت ساخت ویدیو فعال شد. حالا توضیح ویدیوی مورد نظرت را ارسال کن؛ برای انتخاب مدل از «انتخاب مدل هوش مصنوعی» استفاده کن.", message_thread_id=thread_id)
        return

    if text.startswith("/models"):
        if is_group:
            if not is_group_admin(chat_id, user_id):
                bot.reply_to(msg, "⛔ تغییر تنظیمات و مدل‌های ربات در گروه فقط توسط ادمین امکان‌پذیر است.", allow_sending_without_reply=True)
                return
        elif ADMIN_ID and user_id != ADMIN_ID:
            bot.send_message(chat_id, "⛔ این دستور تنها برای ادمین ربات مجاز است.")
            return

        send_models_hub(chat_id, target_key_id, is_group)
        return

    target_reply_id = msg.message_id
    if is_group:
        # Prefix/reply requests do not need a synchronous Telegram getMe round-trip.
        # The numeric bot ID is encoded in the token; use cached username for @mentions.
        token_bot_id = BOT_TOKEN.split(":", 1)[0] if ":" in BOT_TOKEN else ""
        cached_info = _BOT_INFO_CACHE
        bot_id = str(getattr(cached_info, "id", "") or token_bot_id)
        bot_username = str(getattr(cached_info, "username", "") or "").lower()
        if (not bot_username and not early_invoked and re.search(r"(?<![\w])@[A-Za-z0-9_]{5,}", text or "")):
            try:
                bot_info = get_bot_info_cached()
                bot_id = str(getattr(bot_info, "id", "") or bot_id)
                bot_username = str(getattr(bot_info, "username", "") or "").lower()
            except Exception as bot_info_exc:
                print(f"[Group Invocation Warning] getMe unavailable: {type(bot_info_exc).__name__}")
        clean_text_raw = text.strip()
        lower_text = clean_text_raw.lower()

        is_bot_unmute_cmd = bool(re.search(r'^(?:/bot|ربات|روبات|بات|نئو|نعو)\s*(?:صحبت|حرف\s*بزن|فعال|روشن)$', clean_text_raw, flags=re.IGNORECASE)) or lower_text in ["/unmute_bot", "/bot_on"]
        if is_bot_unmute_cmd:
            if is_group_admin(chat_id, user_id):
                safe_kv_delete(f"GROUP_MUTED_{chat_id}")
                _invalidate_state_flag(("group_muted", str(chat_id)))
                bot.reply_to(msg, "🔊 **ربات با موفقیت در این گروه فعال شد و از حالت سکوت خارج گردید.**", parse_mode="Markdown")
            else:
                bot.reply_to(msg, "⛔ این دستور فقط توسط مدیران گروه قابل اجراست.")
            return

        is_bot_mute_cmd = bool(re.search(r'^(?:/bot|ربات|روبات|بات|نئو|نعو)\s*(?:سکوت|بی\s*صدا|ساکت|خاموش)$', clean_text_raw, flags=re.IGNORECASE)) or lower_text in ["/mute_bot", "/bot_off"]
        if is_bot_mute_cmd and not msg.reply_to_message:
            if is_group_admin(chat_id, user_id):
                safe_kv_put(f"GROUP_MUTED_{chat_id}", "true")
                _invalidate_state_flag(("group_muted", str(chat_id)))
                bot.reply_to(msg, "🔇 **ربات در این گروه به حالت سکوت رفت.**\n(جهت فعال‌سازی مجدد، دستور `/bot صحبت` را ارسال کنید)", parse_mode="Markdown")
            else:
                bot.reply_to(msg, "⛔ این دستور فقط توسط مدیران گروه قابل اجراست.")
            return

        is_lock_group_cmd = bool(re.search(
            r'^(?:(?:نئو|نعو|ربات|روبات|بات)\s+)?(?:قفل\s*گروه|بستن\s*چت|بستن\s*گروه|سکوت\s*گروه|قفل\s*چت|/lock|/close|(?:گروه|چت)\s*(?:رو|را)?\s*(?:ببند|قفل\s*کن|بی\s*صدا\s*کن|ساکت\s*کن|ببندش|بگذار\s*رو\s*حالت\s*بی\s*صدا|بزار\s*رو\s*حال[ت]?\s*بی\s*صدا))$',
            clean_text_raw, flags=re.IGNORECASE
        ))
        if is_lock_group_cmd:
            if is_group_admin(chat_id, user_id):
                try:
                    bot.set_chat_permissions(
                        chat_id=chat_id,
                        permissions=ChatPermissions(
                            can_send_messages=False,
                            can_send_audios=False,
                            can_send_documents=False,
                            can_send_photos=False,
                            can_send_videos=False,
                            can_send_video_notes=False,
                            can_send_voice_notes=False,
                            can_send_polls=False,
                            can_send_other_messages=False,
                            can_add_web_page_previews=False
                        )
                    )
                    bot.reply_to(msg, "🔒 **چت گروه توسط ادمین قفل و بی‌صدا شد.**\n(ارسال پیام برای اعضای عادی مسدود گردید)", parse_mode="Markdown")
                except Exception:
                    bot.reply_to(msg, "❌ **خطا:** ربات به دسترسی «محدودسازی اعضا» (Restrict Members) نیاز دارد.")
            else:
                bot.reply_to(msg, "⛔ بستن چت گروه فقط توسط مدیران مجاز است.")
            return

        is_unlock_group_cmd = bool(re.search(
            r'^(?:(?:نئو|نعو|ربات|روبات|بات)\s+)?(?:باز\s*کردن\s*چت|باز\s*کردن\s*گروه|بازگشایی\s*چت|بازگشایی\s*گروه|رفع\s*قفل|/unlock|/open|(?:گروه|چت)\s*(?:رو|را)?\s*(?:باز\s*کن|بازگشایی\s*کن|بازش\s*کن))$',
            clean_text_raw, flags=re.IGNORECASE
        ))
        if is_unlock_group_cmd:
            if is_group_admin(chat_id, user_id):
                try:
                    bot.set_chat_permissions(
                        chat_id=chat_id,
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_audios=True,
                            can_send_documents=True,
                            can_send_photos=True,
                            can_send_videos=True,
                            can_send_video_notes=True,
                            can_send_voice_notes=True,
                            can_send_polls=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True
                        )
                    )
                    bot.reply_to(msg, "🔓 **چت گروه توسط ادمین باز شد.**\n(همه اعضا مجدداً می‌توانند پیام ارسال کنند)", parse_mode="Markdown")
                except Exception:
                    bot.reply_to(msg, "❌ **خطا:** ربات دسترسی کافی برای تغییر تنظیمات گروه را ندارد.")
            else:
                bot.reply_to(msg, "⛔ باز کردن چت گروه فقط توسط مدیران مجاز است.")
            return

        if msg.reply_to_message and is_group_admin(chat_id, user_id):
            target_user = msg.reply_to_message.from_user
            target_uid = target_user.id
            target_name = target_user.first_name or "کاربر"
            cmd_text = re.sub(r'^(?:نئو|نعو|neo|tenet|تننت|ربات|روبات|بات)\s*[:،,-]?\s*', '', clean_text_raw, flags=re.IGNORECASE).strip().lower()

            if cmd_text.startswith("سکوت") or cmd_text.startswith("بی صدا") or cmd_text.startswith("بیصدا") or cmd_text.startswith("ساکت") or cmd_text.startswith("/mute"):
                minutes = 0
                match_num = re.search(r'\d+', cmd_text)
                if match_num:
                    minutes = int(match_num.group())

                until_date = int(time.time() + minutes * 60) if minutes > 0 else 0
                try:
                    bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=target_uid,
                        permissions=ChatPermissions(
                            can_send_messages=False,
                            can_send_audios=False,
                            can_send_documents=False,
                            can_send_photos=False,
                            can_send_videos=False,
                            can_send_video_notes=False,
                            can_send_voice_notes=False,
                            can_send_polls=False,
                            can_send_other_messages=False,
                            can_add_web_page_previews=False
                        ),
                        until_date=until_date
                    )
                    time_msg = f"به مدت **{minutes} دقیقه**" if minutes > 0 else "**دائم**"
                    bot.reply_to(msg, f"🔇 کاربر [{target_name}](tg://user?id={target_uid}) {time_msg} بی‌صدا شد.", parse_mode="Markdown")
                except Exception:
                    bot.reply_to(msg, "❌ **خطا:** امکان اعمال محدودیت برای این کاربر وجود ندارد.")
                return

            elif cmd_text in ["رفع سکوت", "ازاد", "آزاد", "رفع بی صدا", "رفع بیصدا", "آزادش کن", "ازادش کن", "/unmute"]:
                try:
                    bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=target_uid,
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_audios=True,
                            can_send_documents=True,
                            can_send_photos=True,
                            can_send_videos=True,
                            can_send_video_notes=True,
                            can_send_voice_notes=True,
                            can_send_polls=True,
                            can_send_other_messages=True,
                            can_add_web_page_previews=True
                        )
                    )
                    bot.reply_to(msg, f"🔊 سکوت کاربر [{target_name}](tg://user?id={target_uid}) لغو شد.", parse_mode="Markdown")
                except Exception:
                    bot.reply_to(msg, "❌ **خطا:** امکان رفع سکوت وجود ندارد.")
                return

            elif cmd_text in ["اخراج", "بن", "مسدود", "اخراجش کن", "بنش کن", "/ban", "/kick"]:
                try:
                    bot.ban_chat_member(chat_id, target_uid)
                    bot.reply_to(msg, f"🚫 کاربر [{target_name}](tg://user?id={target_uid}) از گروه اخراج و مسدود گردید.", parse_mode="Markdown")
                except Exception:
                    bot.reply_to(msg, "❌ **خطا:** ربات دسترسی اخراج کاربران ندارد یا کاربر مورد نظر ادمین است.")
                return

            elif cmd_text in ["حذف", "پاک", "دیل", "پاکش کن", "حذفش کن", "/del", "/delete"]:
                try:
                    bot.delete_message(chat_id, msg.reply_to_message.message_id)
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    bot.reply_to(msg, "❌ **خطا:** ربات دسترسی حذف پیام (Delete Messages) ندارد.")
                return

        if is_group_muted_cached(chat_id):
            _delete_processing_ack(chat_id, pre_ack_msg)
            return

        replied_from_user = getattr(getattr(msg, 'reply_to_message', None), 'from_user', None)
        is_reply_to_bot = bool(replied_from_user and str(replied_from_user.id) == bot_id)
        is_reply_to_other_human = bool(replied_from_user and str(replied_from_user.id) != bot_id)

        invoked, extracted_prompt = extract_group_invocation(text, bot_username)
        if is_reply_to_other_human and not invoked:
            return
        if not is_reply_to_bot and not invoked:
            return

        if invoked:
            text = extracted_prompt.strip()
            if not text:
                text = "سلام! در خدمتم، چطور می‌تونم کمکت کنم؟" if get_user_lang(user_id) == "fa" else "Hello! How can I help you today?"

        replied_target_user = getattr(msg.reply_to_message, "from_user", None) if msg.reply_to_message else None
        if msg.reply_to_message and replied_target_user and str(replied_target_user.id) != bot_id:
            target_user = replied_target_user
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

    has_photo_attached = bool(msg.photo or (msg.reply_to_message and msg.reply_to_message.photo))
    active_mode = get_user_current_mode(target_key_id)
    photo_source_for_image = msg

    # کاربر می‌تواند عکس را ابتدا و توضیح ویرایش را در پیام بعدی ارسال کند.
    pending_photo_key = f"PENDING_IMAGE_EDIT_{target_key_id}"
    if has_photo_attached:
        attached_sizes = getattr(msg, "photo", None) or []
        if not attached_sizes and getattr(msg, "reply_to_message", None):
            attached_sizes = getattr(msg.reply_to_message, "photo", None) or []
        if attached_sizes:
            attached_file_id = attached_sizes[-1].file_id
            if not (text or "").strip():
                _temp_state_put(pending_photo_key, {"file_id": attached_file_id, "created_at": time.time()}, expiration_ttl=600)
                if active_mode == "IMAGE":
                    bot.send_message(
                        chat_id,
                        "✅ عکس دریافت شد. حالا در پیام بعدی توضیح بده چه تغییری می‌خواهی؛ تا ۱۰ دقیقه همین عکس را برای ویرایش نگه می‌دارم.",
                        message_thread_id=thread_id,
                    )
                    return
            else:
                # عکس و کپشن در یک پیام هستند؛ pending قبلی نباید اشتباهاً استفاده شود.
                _temp_state_delete(pending_photo_key)
    else:
        pending_raw = _temp_state_get(pending_photo_key)
        if pending_raw:
            try:
                pending_data = json.loads(pending_raw)
                pending_file_id = str(pending_data.get("file_id", "")).strip()
                created_at = float(pending_data.get("created_at", 0))
                if pending_file_id and time.time() - created_at <= 600:
                    # شیء سبک با همان file_id؛ worker عکس اصلی را از Telegram دریافت می‌کند.
                    photo_source_for_image = SimpleNamespace(
                        photo=[SimpleNamespace(file_id=pending_file_id)],
                        reply_to_message=None,
                    )
                    # فقط در حالت استودیوی عکس یا وقتی درخواست واقعاً دربارهٔ ویرایش است، از pending استفاده شود.
                    text_looks_like_edit = bool(re.search(
                        r"ویرایش|تغییر|ادیت|اصلاح|بازطراحی|عوض کن|جایگزین|رنگ|پس.?زمینه|بک.?گراند|موها|چشم|لباس|صورت|کیفیت|حذف کن|اضافه کن|تبدیل کن|edit|modify|retouch|inpaint|background|hair|eyes|remove|replace|enhance|upscale",
                        text or "", flags=re.IGNORECASE
                    ))
                    if active_mode == "IMAGE" or text_looks_like_edit:
                        has_photo_attached = True
                        _temp_state_delete(pending_photo_key)
                    else:
                        photo_source_for_image = msg
                else:
                    _temp_state_delete(pending_photo_key)
            except Exception:
                _temp_state_delete(pending_photo_key)
    
    active_mode = get_user_current_mode(target_key_id)
    if active_mode == "VIDEO" and not has_photo_attached and text.strip():
        if not _submit_bounded(
            _VIDEO_JOB_EXECUTOR, _VIDEO_JOB_SLOTS, worker_video_process,
            chat_id, user_id, text.strip(), target_key_id, thread_id, pre_ack_msg,
        ):
            _notify_job_queue_full(chat_id, thread_id, pre_ack_msg)
        return

    try:
        is_code = is_explicit_code_request(text)
    except Exception as e:
        print(f"[Code Request Check Error]: {e}")
        is_code = False
    
    is_img_prompt, clean_img_prompt = detect_and_extract_image_prompt(text) if not has_photo_attached else (False, text)

    # اگر کاربر در گروه با کلیدواژهٔ ربات درخواست ساخت عکس بدهد ولی توضیحی ننویسد،
    # درخواست را گم نکن؛ توضیح را بخواه و پاسخ بعدیِ ریپلای‌شده به ربات را به ساخت عکس بده.
    bare_image_request = bool(re.fullmatch(
        r"\s*(?:(?:لطفاً|لطفا|بی\s*زحمت|برام|برای\s*من)\s*)?(?:(?:یه|یک|این)\s*)?"
        r"(?:عکس|تصویر|نقاشی|طرح|پوستر|والپیپر|آرت|طراحی)\s*(?:رو|را)?\s*"
        r"(?:بساز|بکش|طراحی\s*کن|نقاشی\s*کن|تولید\s*کن|تصویرسازی\s*کن|خلق\s*کن|ایجاد\s*کن)\s*[.!؟،,]*\s*",
        text or "", flags=re.IGNORECASE
    ))
    awaiting_img_key = f"AWAITING_IMG_{target_key_id}"
    awaiting_image_prompt = _temp_state_get(awaiting_img_key) == "true"

    if awaiting_image_prompt and not has_photo_attached and (text or "").strip():
        _temp_state_delete(awaiting_img_key)
        is_img_prompt = True
        clean_img_prompt = text.strip()

    if bare_image_request and not has_photo_attached:
        _temp_state_put(awaiting_img_key, "true", expiration_ttl=600)
        ask_prompt = (
            "🎨 حتماً عزیزم! توضیح بده چه عکسی بسازم.\n"
            "مثلاً: «ماه کامل در آسمان شب، سبک واقع‌گرایانه».\n"
            "پیامت را در پاسخ به همین پیام بفرست."
        ) if get_user_lang(user_id) == "fa" else (
            "🎨 Sure! Describe the image you want me to create.\n"
            "For example: “A full moon in the night sky, photorealistic style.”\n"
            "Reply to this message with your prompt."
        )
        if not _edit_processing_ack(chat_id, pre_ack_msg, ask_prompt):
            bot.send_message(chat_id, ask_prompt, reply_to_message_id=msg.message_id,
                             allow_sending_without_reply=True, message_thread_id=thread_id)
        return

    # ۱. تولید کد
    if is_code:
        if not is_group:
            _USER_MODES_CACHE[target_key_id] = "CODE"
            _persist_kv_async(f"BOT_MODE_{target_key_id}", "CODE")
        group_request = is_group
        ai_executor = _GROUP_AI_JOB_EXECUTOR if group_request else _AI_JOB_EXECUTOR
        ai_slots = _GROUP_AI_JOB_SLOTS if group_request else _AI_JOB_SLOTS
        request_id, pre_ack_msg, submitted_at = _prepare_ai_job_status(
            chat_id, user_id, pre_ack_msg, thread_id=thread_id,
            reply_to_message_id=(msg.message_id if is_group else None),
            received_at=handler_received_at, is_group=is_group,
        )
        if not _submit_bounded(
            ai_executor, ai_slots, worker_ai_process,
            chat_id, user_id, msg, text, target_key_id, is_group, target_reply_id, thread_id, "CODE", pre_ack_msg,
            request_id=request_id, submitted_at=submitted_at,
        ):
            _notify_job_queue_full(chat_id, thread_id, pre_ack_msg)
        return

    # ۲. ساخت تصویر یا ویرایش عکسِ پیوست‌شده با همان مدل تصویری انتخاب‌شده
    image_edit_intent = bool(re.search(
        r"ویرایش|ویرایشش|تغییر|ادیت|اصلاح|بازطراحی|عوض کن|جایگزین|رنگ|پس.?زمینه|بک.?گراند|موها|چشم|لباس|صورت|کیفیت|حذف کن|اضافه کن|تبدیل کن|روشن.?تر|تیره.?تر|زیباتر|edit|modify|retouch|inpaint|background|hair|eyes|clothes|color|remove|replace|enhance|upscale|make it",
        text or "", flags=re.IGNORECASE
    ))
    if has_photo_attached and (active_mode == "IMAGE" or image_edit_intent):
        img_prompt_to_use = text.strip() or "عکس ورودی را با حفظ جزئیات اصلی ویرایش کن."
        if not _submit_bounded(
            _IMAGE_JOB_EXECUTOR, _IMAGE_JOB_SLOTS, worker_image_process,
            chat_id, user_id, img_prompt_to_use, target_key_id, thread_id, photo_source_for_image, pre_ack_msg,
        ):
            _notify_job_queue_full(chat_id, thread_id, pre_ack_msg)
        return

    if (active_mode == "IMAGE" or is_img_prompt) and not has_photo_attached:
        img_prompt_to_use = clean_img_prompt if is_img_prompt else text
        if not _submit_bounded(
            _IMAGE_JOB_EXECUTOR, _IMAGE_JOB_SLOTS, worker_image_process,
            chat_id, user_id, img_prompt_to_use, target_key_id, thread_id, None, pre_ack_msg,
        ):
            _notify_job_queue_full(chat_id, thread_id, pre_ack_msg)
        return

    # ۳. مکالمه و پرسش و پاسخ
    current_ai_mode = "CODE" if active_mode == "CODE" else "CHAT"
    ai_executor = _GROUP_AI_JOB_EXECUTOR if is_group else _AI_JOB_EXECUTOR
    ai_slots = _GROUP_AI_JOB_SLOTS if is_group else _AI_JOB_SLOTS
    request_id, pre_ack_msg, submitted_at = _prepare_ai_job_status(
        chat_id, user_id, pre_ack_msg, thread_id=thread_id,
        reply_to_message_id=(msg.message_id if is_group else None),
        received_at=handler_received_at, is_group=is_group,
    )
    if not _submit_bounded(
        ai_executor, ai_slots, worker_ai_process,
        chat_id, user_id, msg, text, target_key_id, is_group, target_reply_id, thread_id, current_ai_mode, pre_ack_msg,
        request_id=request_id, submitted_at=submitted_at,
    ):
        _notify_job_queue_full(chat_id, thread_id, pre_ack_msg)

# ==========================================
# ۶. هندلر دکمه‌های شیشه‌ای
# ==========================================
def _handle_callbacks_impl(query):
    chat_id = query.message.chat.id
    user_id = str(query.from_user.id)
    data = query.data
    is_group = query.message.chat.type in ["group", "supergroup"]
    target_key_id = f"group_{chat_id}" if is_group else user_id

    if not is_bot_globally_active() and user_id != ADMIN_ID:
        try:
            bot.answer_callback_query(query.id, "⚠️ ربات در حال حاضر خاموش است.")
        except Exception:
            pass
        return

    if data == "noop_btn":
        try:
            bot.answer_callback_query(query.id)
        except Exception:
            pass
        return

    if data == "admin_cancel_wizard" and user_id == ADMIN_ID:
        try:
            bot.answer_callback_query(query.id)
        except Exception:
            pass
        clear_user_state(user_id)
        bot.send_message(chat_id, "❌ **عملیات با موفقیت لغو شد.**", reply_markup=get_admin_panel_markup(), parse_mode="Markdown")
        return

    if data.startswith("cancel_req_"):
        req_id = data.replace("cancel_req_", "")
        owner_id = req_id.split("_")[0]
        if user_id != owner_id:
            try:
                bot.answer_callback_query(query.id, "⛔ شما درخواست دهنده نیستید.")
            except Exception:
                pass
            return
        _CANCEL_REQS.add(req_id)
        safe_kv_put(f"CANCEL_{req_id}", "true", API_TIMEOUT_SECONDS)
        try:
            bot.answer_callback_query(query.id, "درخواست متوقف شد.")
            bot.edit_message_text(tr(user_id, "req_canceled"), chat_id=chat_id, message_id=query.message.message_id)
        except Exception:
            pass
        return

    if data == "check_sponsor" and not is_group:
        try:
            bot.answer_callback_query(query.id)
        except Exception:
            pass
        ok_sponsor, unjoined = check_sponsor_join(user_id)
        if not ok_sponsor:
            try:
                markup = build_sponsor_markup(user_id, unjoined)
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=markup)
            except Exception:
                pass
            return
        else:
            try:
                bot.delete_message(chat_id, query.message.message_id)
            except Exception:
                pass
            send_main_menu(chat_id, user_id)
            return

    if is_group:
        group_allowed_actions = [
            "models_hub", "models_cat_chat", "models_cat_code", "models_cat_image", "models_cat_video", "close_menu",
            "switch_group_chat", "switch_group_code", "switch_group_image", "switch_group_video"
        ]
        is_set_action = data.startswith("set_model_") or data.startswith("set_code_model_") or data.startswith("set_img_model_") or data.startswith("set_video_model_")

        if data in group_allowed_actions or is_set_action:
            if not is_group_admin(chat_id, user_id):
                try:
                    bot.answer_callback_query(query.id, "⛔ فقط ادمین‌های گروه به این منو دسترسی دارند.", show_alert=True)
                except Exception:
                    pass
                return

        pv_only = ["main_menu", "history_menu", "new_chat", "switch_mode_chat", "switch_mode_code", "switch_mode_image", "switch_mode_video", "video_prompt_start", "contact_admin", "open_lang_menu"]
        if data in pv_only or data.startswith("switch_sess_") or data.startswith("del_single_sess_") or data.startswith("admin_"):
            try:
                bot.answer_callback_query(query.id)
            except Exception:
                pass
            return

    if data in ["main_menu", "history_menu", "new_chat"]:
        clear_user_state(user_id)

    # انتخاب مدل‌ها با جابه‌جایی آنی تیک سبز
    if data.startswith("set_model_"):
        idx = data.replace("set_model_", "")
        _model_selection_set_cached(f"USER_MODEL_{target_key_id}", idx, persist=True)
        _clear_active_history_async(user_id)
        models = get_ai_models_cached()
        name = models[int(idx)].get("name") if idx.isdigit() and int(idx) < len(models) else "انتخاب شده"
        if not is_group:
            _cache_selected_model_display_name(user_id, "CHAT", name)

        new_markup = build_model_selection_markup(target_key_id, is_group, models, current_idx=idx, is_code_category=False)
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=new_markup)
        except Exception:
            pass
        try:
            bot.answer_callback_query(query.id, f"✅ مدل چت تنظیم شد روی: {name}", show_alert=False)
        except Exception:
            pass
        if not is_group:
            refresh_main_menu_banner(chat_id, user_id)
        return

    elif data.startswith("set_code_model_"):
        idx = data.replace("set_code_model_", "")
        models = get_code_models_cached() or get_ai_models_cached()
        if not idx.isdigit() or int(idx) < 0 or int(idx) >= len(models):
            bot.answer_callback_query(query.id, "مدل برنامه‌نویسی معتبر نیست.", show_alert=True)
            return
        _model_selection_set_cached(f"USER_CODE_MODEL_{target_key_id}", idx, persist=True)
        name = models[int(idx)].get("name") if idx.isdigit() and int(idx) < len(models) else "انتخاب شده"
        if not is_group:
            _cache_selected_model_display_name(user_id, "CODE", name)

        new_markup = build_model_selection_markup(target_key_id, is_group, models, current_idx=idx, is_code_category=True)
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=new_markup)
        except Exception:
            pass
        try:
            bot.answer_callback_query(query.id, f"💻 مدل کدنویسی تنظیم شد روی: {name}", show_alert=False)
        except Exception:
            pass
        if not is_group:
            refresh_main_menu_banner(chat_id, user_id)
        return

    elif data.startswith("set_img_model_"):
        idx = data.replace("set_img_model_", "")
        _model_selection_set_cached(f"USER_IMG_MODEL_{target_key_id}", idx, persist=True)
        img_models = get_img_models_cached()
        name = img_models[int(idx)].get("name") if idx.isdigit() and int(idx) < len(img_models) else "انتخاب شده"
        if not is_group:
            _cache_selected_model_display_name(user_id, "IMAGE", name)

        new_markup = build_image_model_selection_markup(target_key_id, is_group, img_models, current_idx=idx)
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=new_markup)
        except Exception:
            pass
        try:
            bot.answer_callback_query(query.id, f"🎨 مدل عکس تنظیم شد روی: {name}", show_alert=False)
        except Exception:
            pass
        if not is_group:
            refresh_main_menu_banner(chat_id, user_id)
        return

    elif data.startswith("set_video_model_"):
        idx = data.replace("set_video_model_", "")
        video_models = get_video_models_cached()
        if not idx.isdigit() or int(idx) < 0 or int(idx) >= len(video_models):
            bot.answer_callback_query(query.id, "مدل ویدیو معتبر نیست.", show_alert=True)
            return
        _model_selection_set_cached(f"USER_VIDEO_MODEL_{target_key_id}", idx, persist=True)
        name = video_models[int(idx)].get("name", "Video model")
        if not is_group:
            _cache_selected_model_display_name(user_id, "VIDEO", name)
        new_markup = build_video_model_selection_markup(target_key_id, is_group, video_models, current_idx=idx)
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=new_markup)
            bot.answer_callback_query(query.id, f"✅ مدل ویدیو تنظیم شد روی: {name}")
        except Exception:
            pass
        if not is_group:
            refresh_main_menu_banner(chat_id, user_id)
        return

    # ==========================================
    # 🛠 مدیریت، مشاهده و ویرایش مدل‌ها در پنل ادمین
    # ==========================================
    if data.startswith("admin_view_video_") and user_id == ADMIN_ID:
        safe_kv_delete(f"ADMIN_STEP_{user_id}")
        idx = int(data.replace("admin_view_video_", ""))
        send_admin_model_edit_card(chat_id, idx, is_video=True, message_id=query.message.message_id)
        return

    if data.startswith("admin_view_m_") and user_id == ADMIN_ID:
        safe_kv_delete(f"ADMIN_STEP_{user_id}")
        idx = int(data.replace("admin_view_m_", ""))
        send_admin_model_edit_card(chat_id, idx, is_img=False, message_id=query.message.message_id)
        return

    elif data.startswith("admin_view_img_") and user_id == ADMIN_ID:
        safe_kv_delete(f"ADMIN_STEP_{user_id}")
        idx = int(data.replace("admin_view_img_", ""))
        send_admin_model_edit_card(chat_id, idx, is_img=True, message_id=query.message.message_id)
        return

    elif data.startswith("admin_view_code_") and user_id == ADMIN_ID:
        safe_kv_delete(f"ADMIN_STEP_{user_id}")
        idx = int(data.replace("admin_view_code_", ""))
        send_admin_model_edit_card(chat_id, idx, is_code=True, message_id=query.message.message_id)
        return

    elif data.startswith("edit_code_name_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_code_name_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_CODE_NAME_{idx}")
        bot.send_message(chat_id, "📝 نام جدید مدل برنامه‌نویسی را بفرست:", reply_markup=get_admin_cancel_markup()); return
    elif data.startswith("edit_code_url_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_code_url_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_CODE_URL_{idx}")
        bot.send_message(chat_id, "🌐 Base URL جدید مدل برنامه‌نویسی را بفرست:", reply_markup=get_admin_cancel_markup()); return
    elif data.startswith("edit_code_key_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_code_key_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_CODE_KEY_{idx}")
        bot.send_message(chat_id, "🔑 API Key جدید را بفرست؛ برای حذف کلید نقطه . بفرست:", reply_markup=get_admin_cancel_markup()); return
    elif data.startswith("edit_code_id_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_code_id_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_CODE_ID_{idx}")
        bot.send_message(chat_id, "📌 شناسه Model Name جدید را بفرست:", reply_markup=get_admin_cancel_markup()); return
    elif data.startswith("toggle_code_vision_") and user_id == ADMIN_ID:
        idx = int(data.replace("toggle_code_vision_", ""))
        models = json.loads(safe_kv_get("CODE_MODELS") or "[]")
        if 0 <= idx < len(models):
            models[idx]["supportsVision"] = not bool(models[idx].get("supportsVision", False))
            safe_kv_put("CODE_MODELS", models)
            invalidate_models_cache()
            send_admin_model_edit_card(chat_id, idx, is_code=True, message_id=query.message.message_id)
        return

    elif data.startswith("edit_m_name_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_m_name_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_M_NAME_{idx}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data=f"admin_view_m_{idx}", style="danger"))
        bot.send_message(chat_id, f"📝 **نام جدید را برای مدل چت وارد کنید:**", parse_mode="Markdown", reply_markup=markup)
        return

    elif data.startswith("edit_m_url_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_m_url_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_M_URL_{idx}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data=f"admin_view_m_{idx}", style="danger"))
        bot.send_message(chat_id, f"🌐 **آدرس Base URL جدید را وارد کنید:**", parse_mode="Markdown", reply_markup=markup)
        return

    elif data.startswith("edit_m_key_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_m_key_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_M_KEY_{idx}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data=f"admin_view_m_{idx}", style="danger"))
        bot.send_message(chat_id, f"🔑 **کلید API Key جدید را وارد کنید:**", parse_mode="Markdown", reply_markup=markup)
        return

    elif data.startswith("edit_m_id_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_m_id_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_M_ID_{idx}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data=f"admin_view_m_{idx}", style="danger"))
        bot.send_message(chat_id, f"📌 **شناسه Model Name سرور را وارد کنید:**", parse_mode="Markdown", reply_markup=markup)
        return

    elif data.startswith("toggle_m_vision_") and user_id == ADMIN_ID:
        idx = int(data.replace("toggle_m_vision_", ""))
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if 0 <= idx < len(models):
            models[idx]["supportsVision"] = not models[idx].get("supportsVision", False)
            safe_kv_put("AI_MODELS", models)
            invalidate_models_cache()
            send_admin_model_edit_card(chat_id, idx, is_img=False, message_id=query.message.message_id)
        return

    elif data.startswith("edit_img_name_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_img_name_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_IMG_NAME_{idx}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data=f"admin_view_img_{idx}", style="danger"))
        bot.send_message(chat_id, f"🎨 **نام جدید را برای مدل عکس وارد کنید:**", parse_mode="Markdown", reply_markup=markup)
        return

    elif data.startswith("edit_img_url_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_img_url_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_IMG_URL_{idx}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data=f"admin_view_img_{idx}", style="danger"))
        bot.send_message(chat_id, f"🌐 **آدرس Base URL جدید تصویرساز را وارد کنید:**", parse_mode="Markdown", reply_markup=markup)
        return

    elif data.startswith("edit_img_key_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_img_key_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_IMG_KEY_{idx}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data=f"admin_view_img_{idx}", style="danger"))
        bot.send_message(chat_id, f"🔑 **کلید API Key جدید تصویرساز را وارد کنید (یا . برای خالی):**", parse_mode="Markdown", reply_markup=markup)
        return

    elif data.startswith("edit_img_id_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_img_id_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_IMG_ID_{idx}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data=f"admin_view_img_{idx}", style="danger"))
        bot.send_message(chat_id, f"📌 **شناسه Model Name تصویرساز را وارد کنید:**", parse_mode="Markdown", reply_markup=markup)
        return

    elif data.startswith("edit_img_site_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_img_site_", ""))
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_IMG_SITE_{idx}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data=f"admin_view_img_{idx}", style="danger"))
        bot.send_message(chat_id, "🔗 آدرس کامل وب‌سایت تصویرساز را وارد کن (برای حذف مقدار فعلی، نقطه . بفرست):", reply_markup=markup)
        return

    elif data.startswith("edit_video_name_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_video_name_", "")); safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_VIDEO_NAME_{idx}")
        bot.send_message(chat_id, "📝 نام نمایشی جدید مدل ویدیو را بفرست.", reply_markup=get_admin_cancel_markup()); return
    elif data.startswith("edit_video_url_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_video_url_", "")); safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_VIDEO_URL_{idx}")
        bot.send_message(chat_id, "🌐 Base URL یا endpoint مستند API ساخت ویدیو را بفرست (برای خالی کردن، . بفرست).", reply_markup=get_admin_cancel_markup()); return
    elif data.startswith("edit_video_key_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_video_key_", "")); safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_VIDEO_KEY_{idx}")
        bot.send_message(chat_id, "🔑 API Key جدید را بفرست؛ برای API بدون کلید یا حذف کلید فعلی، . بفرست.", reply_markup=get_admin_cancel_markup()); return
    elif data.startswith("edit_video_id_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_video_id_", "")); safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_VIDEO_ID_{idx}")
        bot.send_message(chat_id, "📌 Model Name را دقیقاً مطابق مستندات سرویس بفرست (برای خالی‌کردن، . بفرست).", reply_markup=get_admin_cancel_markup()); return
    elif data.startswith("edit_video_site_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_video_site_", "")); safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_VIDEO_SITE_{idx}")
        bot.send_message(chat_id, "🔗 آدرس وب‌سایت (اختیاری) را بفرست؛ برای حذف، . بفرست.", reply_markup=get_admin_cancel_markup()); return
    elif data.startswith("edit_video_status_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_video_status_", "")); safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_VIDEO_STATUS_{idx}")
        bot.send_message(chat_id, "🔄 قالب آدرس پیگیری وضعیت job را بفرست؛ شناسهٔ job باید با {id} مشخص شود، مثل https://api.example.com/v1/videos/{id}. برای پیش‌فرض، . بفرست.", reply_markup=get_admin_cancel_markup()); return

    try:
        bot.answer_callback_query(query.id)
    except Exception:
        pass

    if is_group:
        if data == "switch_group_chat":
            _USER_MODES_CACHE[target_key_id] = "CHAT"
            _persist_kv_async(f"BOT_MODE_{target_key_id}", "CHAT")
            send_models_hub(chat_id, target_key_id, is_group=True, message_id=query.message.message_id)
            bot.send_message(chat_id, "💬 **حالت ربات در این گروه روی «پرسش و پاسخ و گفتگو» تنظیم شد.**")
            return

        elif data == "switch_group_code":
            _USER_MODES_CACHE[target_key_id] = "CODE"
            _persist_kv_async(f"BOT_MODE_{target_key_id}", "CODE")
            send_models_hub(chat_id, target_key_id, is_group=True, message_id=query.message.message_id)
            bot.send_message(chat_id, "💻 **حالت ربات در این گروه روی «کدنویسی و توسعه نرم‌افزار» تنظیم شد.**")
            return

        elif data == "switch_group_image":
            _USER_MODES_CACHE[target_key_id] = "IMAGE"
            _persist_kv_async(f"BOT_MODE_{target_key_id}", "IMAGE")
            send_models_hub(chat_id, target_key_id, is_group=True, message_id=query.message.message_id)
            bot.send_message(chat_id, "🎨 **حالت ربات در این گروه روی «استودیو ساخت عکس» تنظیم شد.**")
            return

        elif data == "switch_group_video":
            _USER_MODES_CACHE[target_key_id] = "VIDEO"
            _persist_kv_async(f"BOT_MODE_{target_key_id}", "VIDEO")
            send_models_hub(chat_id, target_key_id, is_group=True, message_id=query.message.message_id)
            bot.send_message(chat_id, "🎬 **حالت ساخت ویدیو برای این گروه فعال شد.**")
            return

    if data == "open_lang_menu" and not is_group:
        send_lang_selection_menu(chat_id, user_id, query.message.message_id)

    elif data == "set_lang_fa" and not is_group:
        _USER_LANG_CACHE[user_id] = "fa"
        safe_kv_put(f"USER_LANG_{user_id}", "fa")
        send_main_menu(chat_id, user_id)

    elif data == "set_lang_en" and not is_group:
        _USER_LANG_CACHE[user_id] = "en"
        safe_kv_put(f"USER_LANG_{user_id}", "en")
        send_main_menu(chat_id, user_id)

    elif data == "switch_mode_chat" and not is_group:
        _USER_MODES_CACHE[target_key_id] = "CHAT"
        _persist_kv_async(f"BOT_MODE_{target_key_id}", "CHAT")
        refresh_main_menu_banner(chat_id, user_id, query.message.message_id)
        bot.send_message(chat_id, tr(user_id, "chat_mode_msg"), parse_mode="Markdown")

    elif data == "switch_mode_code" and not is_group:
        _USER_MODES_CACHE[target_key_id] = "CODE"
        _persist_kv_async(f"BOT_MODE_{target_key_id}", "CODE")
        refresh_main_menu_banner(chat_id, user_id, query.message.message_id)
        bot.send_message(chat_id, tr(user_id, "code_mode_msg"), parse_mode="Markdown")

    elif data == "switch_mode_image" and not is_group:
        _USER_MODES_CACHE[target_key_id] = "IMAGE"
        _persist_kv_async(f"BOT_MODE_{target_key_id}", "IMAGE")
        refresh_main_menu_banner(chat_id, user_id, query.message.message_id)
        bot.send_message(chat_id, tr(user_id, "image_mode_msg"), parse_mode="Markdown")

    elif data == "switch_mode_video" and not is_group:
        _USER_MODES_CACHE[target_key_id] = "VIDEO"
        _persist_kv_async(f"BOT_MODE_{target_key_id}", "VIDEO")
        refresh_main_menu_banner(chat_id, user_id, query.message.message_id)
        bot.send_message(chat_id, tr(user_id, "video_mode_msg"), parse_mode="Markdown")

    elif data == "video_prompt_start" and not is_group:
        # If the selected video model is website-only, open the provider site directly.
        # Do not ask for a prompt that cannot be forwarded to the external website.
        video_models = get_video_models_cached()
        try:
            video_idx = int(safe_kv_get(f"USER_VIDEO_MODEL_{target_key_id}") or safe_kv_get(f"USER_VIDEO_MODEL_{user_id}") or "0")
        except (TypeError, ValueError):
            video_idx = 0

        if not video_models or video_idx < 0 or video_idx >= len(video_models):
            bot.send_message(
                chat_id,
                "⚠️ هنوز مدل یا سایت ساخت ویدیویی تنظیم نشده است. از ادمین بخواه از پنل مدیریت، یک مدل ویدیو اضافه کند.",
            )
            return

        selected_video_model = video_models[video_idx]
        selected_base_url = str(selected_video_model.get("baseUrl", "") or "").strip()
        selected_site_url = str(selected_video_model.get("siteUrl", "") or "").strip()
        if not selected_base_url:
            if selected_site_url.startswith(("https://", "http://")):
                site_markup = types.InlineKeyboardMarkup(row_width=1)
                site_markup.add(types.InlineKeyboardButton("🌐 باز کردن سایت ساخت ویدیو", url=selected_site_url))
                site_markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu"))
                bot.send_message(
                    chat_id,
                    "🎬 این مدل فقط به‌صورت سایت تنظیم شده است. با زدن دکمهٔ زیر سایت را باز کن و ویدیو را همان‌جا بساز. برای ساخت مستقیم داخل تلگرام باید API سرویس تنظیم شود.",
                    reply_markup=site_markup,
                    disable_web_page_preview=True,
                )
            else:
                bot.send_message(chat_id, "⚠️ برای مدل انتخاب‌شده نه API و نه آدرس سایت تنظیم نشده است. از ادمین بخواه تنظیمات مدل ویدیو را کامل کند.")
            return

        safe_kv_put(f"VIDEO_PROMPT_AWAITING_{user_id}", "true", expiration_ttl=600)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(tr(user_id, "btn_back_main"), callback_data="main_menu"))
        bot.send_message(chat_id, tr(user_id, "video_prompt_request"), reply_markup=markup)

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

    elif data == "admin_toggle_off" and user_id == ADMIN_ID:
        set_bot_status(False)
        safe_kv_put("BOT_GLOBAL_STATUS", "off")
        bot.send_message(chat_id, "🔴 **ربات با موفقیت خاموش شد.**")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=get_admin_panel_markup())
        except Exception:
            pass

    elif data == "admin_toggle_on" and user_id == ADMIN_ID:
        set_bot_status(True)
        safe_kv_delete("BOT_GLOBAL_STATUS")
        bot.send_message(chat_id, "🟢 **ربات با موفقیت روشن شد.**")
        try:
            bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=get_admin_panel_markup())
        except Exception:
            pass

    elif data == "admin_clean_cache" and user_id == ADMIN_ID:
        clean_system_cache(chat_id)

    elif data == "admin_backup_chats" and user_id == ADMIN_ID:
        threading.Thread(target=export_all_chats_backup, args=(chat_id,), daemon=True).start()

    elif data == "admin_restore_chats" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "AWAITING_BACKUP_FILE")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel", style="danger"))
        bot.send_message(
            chat_id,
            "📥 **بازگردانی اطلاعات از فایل پشتیبان (بکاپ):**\n\n"
            "لطفاً فایل پشتیبان `.json` را ارسال کنید.",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif data == "main_menu":
        if not is_group:
            send_main_menu(chat_id, user_id, query.message.message_id)

    elif data == "close_menu":
        try:
            bot.delete_message(chat_id, query.message.message_id)
        except Exception:
            pass

    elif data == "models_hub":
        send_models_hub(chat_id, target_key_id, is_group, query.message.message_id)

    elif data == "models_cat_chat":
        models = get_ai_models_cached()
        current_idx = _model_selection_get_or_load(f"USER_MODEL_{target_key_id}")
        new_markup = build_model_selection_markup(target_key_id, is_group, models, current_idx, is_code_category=False)
        try:
            bot.edit_message_text("✨ **مدل هوش مصنوعی چت و گفتگو را انتخاب کنید:**", chat_id=chat_id, message_id=query.message.message_id, parse_mode="Markdown", reply_markup=new_markup)
        except Exception:
            pass

    elif data == "models_cat_code":
        models = get_code_models_cached() or get_ai_models_cached()
        code_key = f"USER_CODE_MODEL_{target_key_id}"
        current_idx = _model_selection_get_cached(code_key)
        if current_idx is None:
            current_idx = safe_kv_get(code_key)
            if current_idx is None:
                current_idx = _model_selection_get_or_load(f"USER_MODEL_{target_key_id}")
            else:
                with _MODEL_SELECTION_CACHE_LOCK:
                    _MODEL_SELECTION_CACHE[code_key] = (time.monotonic(), str(current_idx))
        current_idx = str(current_idx or "0")
        if current_idx.isdigit() and int(current_idx) >= len(models):
            current_idx = "0"
        new_markup = build_model_selection_markup(target_key_id, is_group, models, current_idx, is_code_category=True)
        code_notice = "💻 **مدل اختصاصی برنامه‌نویسی را انتخاب کنید:**" if get_code_models_cached() else "💻 **مدل برنامه‌نویسی هنوز جداگانه تعریف نشده؛ فعلاً مدل‌های چت نمایش داده می‌شوند.**"
        try:
            bot.edit_message_text(code_notice, chat_id=chat_id, message_id=query.message.message_id, parse_mode="Markdown", reply_markup=new_markup)
        except Exception:
            pass

    elif data == "models_cat_image":
        new_markup = build_image_model_selection_markup(target_key_id, is_group)
        try:
            bot.edit_message_text("🎨 **مدل ساخت عکس را انتخاب کنید:**", chat_id=chat_id, message_id=query.message.message_id, parse_mode="Markdown", reply_markup=new_markup)
        except Exception:
            pass

    elif data == "models_cat_video":
        new_markup = build_video_model_selection_markup(target_key_id, is_group)
        try:
            bot.edit_message_text("🎬 **مدل ساخت ویدیو را انتخاب کن:**", chat_id=chat_id, message_id=query.message.message_id, parse_mode="Markdown", reply_markup=new_markup)
        except Exception:
            pass

    elif data == "history_help" and not is_group:
        if get_user_lang(user_id) == "fa":
            guide_text = (
                "📘 راهنمای تاریخچه گفتگوها\n\n"
                "• هر بار که «چت جدید» را می‌زنی، گفت‌وگوی تازه به‌صورت خودکار در تاریخچه ثبت می‌شود؛ لازم نیست دستی چیزی اضافه کنی.\n\n"
                "• ربات حداکثر ۷ گفت‌وگوی اخیر را نگه می‌دارد. وقتی گفت‌وگوی هشتم ساخته شود، قدیمی‌ترین مورد از فهرست و پیام‌های ذخیره‌شدهٔ همان گفت‌وگو پاک می‌شود.\n\n"
                "• عنوان هر گفت‌وگو از اولین پیام آن ساخته می‌شود؛ اگر هنوز پیامی نفرستاده باشی، عنوان پیش‌فرض دیده می‌شود.\n\n"
                "• تاریخ شمسی و ساعت بر اساس زمان ایران نمایش داده می‌شوند. برای گفت‌وگوهای قدیمی که ساعتشان ذخیره نشده، ساعت حدسی نمایش داده نمی‌شود.\n\n"
                "• علامت 🟢 یعنی همین گفت‌وگوی فعال است. روی عنوان گفت‌وگو بزن تا به آن برگردی و روی 🗑 بزن تا حذفش کنی."
            )
        else:
            guide_text = (
                "📘 Chat history guide\n\n"
                "• Every time you tap New Chat, it is added automatically. No manual saving is needed.\n\n"
                "• Up to 7 recent conversations are kept. Creating an eighth removes the oldest conversation and its saved messages.\n\n"
                "• A conversation title is based on its first message. Empty chats keep the default title.\n\n"
                "• Dates and times use Iran local time. Old chats without an exact timestamp will not be given a made-up time.\n\n"
                "• 🟢 marks the active conversation. Tap a title to switch to it or 🗑 to delete it."
            )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📜 بازگشت به تاریخچه" if get_user_lang(user_id) == "fa" else "📜 Back to history", callback_data="history_menu"))
        markup.add(types.InlineKeyboardButton("🏠 منوی اصلی" if get_user_lang(user_id) == "fa" else "🏠 Main menu", callback_data="main_menu"))
        bot.send_message(chat_id, _rtlize_guide_text(guide_text), reply_markup=markup)

    elif data == "history_menu" and not is_group:
        send_history_menu(chat_id, user_id, query.message.message_id)

    elif data.startswith("del_single_sess_") and not is_group:
        del_id = data.replace("del_single_sess_", "")
        sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
        active_sess = safe_kv_get(f"ACTIVE_SESSION_{user_id}")
        safe_kv_delete(f"HISTORY_{user_id}_{del_id}")
        _history_cache_delete(f"HISTORY_{user_id}_{del_id}")

        new_sessions = [s for s in sessions if s.get("id") != del_id]
        safe_kv_put(f"SESSIONS_{user_id}", new_sessions)

        if active_sess == del_id:
            if new_sessions:
                safe_kv_put(f"ACTIVE_SESSION_{user_id}", new_sessions[0]["id"])
                _set_active_session_cache(user_id, new_sessions[0]["id"])
            else:
                new_sess_id = f"sess_{time.time_ns()}"
                safe_kv_put(f"ACTIVE_SESSION_{user_id}", new_sess_id)
                _set_active_session_cache(user_id, new_sess_id)
                new_sessions = [make_session_record(new_sess_id)]
                save_sessions_limited(user_id, new_sessions, active_id=new_sess_id)
        else:
            save_sessions_limited(user_id, new_sessions)

        send_history_menu(chat_id, user_id, message_id=query.message.message_id)

    elif data == "new_chat" and not is_group:
        create_new_session(user_id)
        bot.send_message(chat_id, tr(user_id, "new_chat_msg"), parse_mode="Markdown", reply_markup=get_persistent_menu_markup(user_id))

    elif data.startswith("switch_sess_") and not is_group:
        sess_id = data.replace("switch_sess_", "")
        safe_kv_put(f"ACTIVE_SESSION_{user_id}", sess_id)
        _set_active_session_cache(user_id, sess_id)
        bot.send_message(chat_id, "🔄 با موفقیت به این گفتگو منتقل شدید.")
        send_history_menu(chat_id, user_id, message_id=query.message.message_id)

    elif data == "admin_panel" and user_id == ADMIN_ID:
        clear_user_state(user_id)
        try:
            bot.edit_message_text(
                "🛠 **پنل مدیریت ربات**",
                chat_id=chat_id,
                message_id=query.message.message_id,
                parse_mode="Markdown",
                reply_markup=get_admin_panel_markup(),
            )
        except Exception:
            bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", parse_mode="Markdown", reply_markup=get_admin_panel_markup())

    elif data == "admin_self_test" and user_id == ADMIN_ID:
        try:
            bot.answer_callback_query(query.id)
        except Exception:
            pass
        try:
            bot.edit_message_text(
                "🧪 تست سلامت شروع شد؛ اتصال‌ها، ساختار مدل‌ها و مسیر فراخوانی گروه در حال بررسی هستند...",
                chat_id=chat_id,
                message_id=query.message.message_id,
            )
        except Exception:
            pass
        report, summary = run_admin_self_tests()
        report_markup = types.InlineKeyboardMarkup(row_width=1)
        report_markup.add(types.InlineKeyboardButton("🔄 اجرای دوباره تست", callback_data="admin_self_test", style="success"))
        report_markup.add(types.InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin_panel"))
        try:
            bot.edit_message_text(
                report[:3900],
                chat_id=chat_id,
                message_id=query.message.message_id,
                reply_markup=report_markup,
                disable_web_page_preview=True,
            )
        except Exception:
            bot.send_message(chat_id, report[:3900], reply_markup=report_markup, disable_web_page_preview=True)
        print(f"[Admin Self Test] passed={summary['passed']} failed={summary['failed']} warnings={summary['warnings']}")
        return

    elif data == "admin_setup_guide" and user_id == ADMIN_ID:
        try:
            bot.answer_callback_query(query.id)
        except Exception:
            pass
        send_admin_setup_guide(chat_id)
        return

    elif data == "admin_stats" and user_id == ADMIN_ID:
        send_bot_stats(chat_id)

    elif data == "admin_stats_inactive" and user_id == ADMIN_ID:
        send_admin_status_user_list(chat_id, "inactive", page=0, message_id=query.message.message_id)

    elif data == "admin_stats_unreachable" and user_id == ADMIN_ID:
        send_admin_status_user_list(chat_id, "unreachable", page=0, message_id=query.message.message_id)

    elif data == "admin_stats_banned" and user_id == ADMIN_ID:
        send_admin_status_user_list(chat_id, "banned", page=0, message_id=query.message.message_id)

    elif data.startswith("admin_status_") and user_id == ADMIN_ID:
        parts = data.split("_")
        if len(parts) >= 4:
            category = parts[2]
            try:
                page = int(parts[3])
            except ValueError:
                page = 0
            if category in {"inactive", "unreachable", "banned"}:
                send_admin_status_user_list(chat_id, category, page=page, message_id=query.message.message_id)

    elif data == "admin_broadcast" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "BROADCAST_MSG")
        bot.send_message(chat_id, "📢 **ارسال پیام همگانی:**\n\nپیام خود را بفرستید:", parse_mode="Markdown", reply_markup=get_admin_cancel_markup())

    # ==========================================
    # 👥 دکمه‌های شیشه‌ای مدیریت کاربران ادمین
    # ==========================================
    elif data == "admin_users_menu" and user_id == ADMIN_ID:
        clear_user_state(user_id)
        send_admin_users_list(chat_id, page=0, message_id=query.message.message_id)

    elif data == "admin_search_user_id" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "SEARCH_USER_BY_ID")
        bot.send_message(
            chat_id,
            "🔍 **جستجوی کاربر با آیدی عددی:**\n\nلطفاً آیدی عددی کاربر مورد نظر را ارسال کنید:",
            parse_mode="Markdown",
            reply_markup=get_admin_cancel_markup()
        )

    elif data.startswith("admin_users_p_") and user_id == ADMIN_ID:
        page = int(data.replace("admin_users_p_", ""))
        send_admin_users_list(chat_id, page=page, message_id=query.message.message_id)

    elif data.startswith("user_card_") and user_id == ADMIN_ID:
        parts = data.split("_")
        target_uid = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 0
        send_user_profile_card(chat_id, target_uid, page=page, message_id=query.message.message_id)

    elif data.startswith("toggle_ban_") and user_id == ADMIN_ID:
        parts = data.split("_")
        target_uid = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 0

        is_banned = safe_kv_get(f"BANNED_{target_uid}") == "true"
        if is_banned:
            safe_kv_delete(f"BANNED_{target_uid}")
            _invalidate_state_flag(("banned", str(target_uid)))
            upstash_command(["SREM", "BANNED_USERS_SET", target_uid])
        else:
            safe_kv_put(f"BANNED_{target_uid}", "true")
            _invalidate_state_flag(("banned", str(target_uid)))
            upstash_command(["SADD", "BANNED_USERS_SET", target_uid])
        
        send_user_profile_card(chat_id, target_uid, page=page, message_id=query.message.message_id)

    elif data.startswith("kick_user_") and user_id == ADMIN_ID:
        parts = data.split("_")
        target_uid = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 0

        upstash_command(["SREM", "BOT_USERS_SET", target_uid])
        upstash_command(["SREM", "BANNED_USERS_SET", target_uid])
        upstash_command(["SREM", "BOT_UNREACHABLE_USERS_SET", target_uid])
        _KNOWN_USERS_CACHE.discard(target_uid)
        safe_kv_delete(f"USER_INFO_{target_uid}")
        safe_kv_delete(f"BANNED_{target_uid}")
        _invalidate_state_flag(("banned", str(target_uid)))
        safe_kv_delete(f"LAST_ACTIVE_{target_uid}")
        safe_kv_delete(f"SESSIONS_{target_uid}")
        safe_kv_delete(f"ACTIVE_SESSION_{target_uid}")
        _set_active_session_cache(target_uid, None)
        with _CHAT_HISTORY_CACHE_LOCK:
            for cached_history_key in [key for key in _CHAT_HISTORY_CACHE if key.startswith(f"HISTORY_{target_uid}_")]:
                _CHAT_HISTORY_CACHE.pop(cached_history_key, None)
        invalidate_users_cache()
        send_admin_users_list(chat_id, page=page, message_id=query.message.message_id)

    elif data.startswith("dm_user_") and user_id == ADMIN_ID:
        target_uid = data.replace("dm_user_", "").strip()
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"DM_TO_{target_uid}")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 انصراف", callback_data=f"user_card_{target_uid}_0", style="danger"))
        bot.send_message(
            chat_id,
            f"📩 **ارسال پیام مستقیم به کاربر:** `{target_uid}`\n\nمتن، تصویر یا فایل خود را بفرستید تا فوراً به پیوی کاربر منتقل شود:",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif data == "admin_add_user_manual" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "MANUAL_ADD_USER")
        bot.send_message(
            chat_id,
            "➕ **افزودن دستی کاربر:**\n\nلطفاً آیدی عددی کاربر (Numeric User ID) را ارسال نمایید:",
            parse_mode="Markdown",
            reply_markup=get_admin_cancel_markup()
        )

    elif data == "admin_add_model" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_MODEL_NAME")
        bot.send_message(chat_id, "📝 نام عمومی مدل چت را وارد کنید:", reply_markup=get_admin_cancel_markup())

    elif data == "admin_add_code_model" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_CODE_NAME")
        bot.send_message(chat_id, "💻 نام نمایشی مدل برنامه‌نویسی را وارد کن:", reply_markup=get_admin_cancel_markup())

    elif data == "admin_add_img_model" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_IMG_NAME")
        bot.send_message(chat_id, "🎨 نام عمومی مدل ساخت عکس را وارد کنید:", reply_markup=get_admin_cancel_markup())

    elif data == "admin_add_video_model" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_VIDEO_NAME")
        bot.send_message(chat_id, "🎬 نام نمایشی مدل ساخت ویدیو را وارد کن:", reply_markup=get_admin_cancel_markup())

    elif data == "admin_list_models" and user_id == ADMIN_ID:
        send_admin_models_list(chat_id, query.message.message_id)

    elif data.startswith("del_model_") and user_id == ADMIN_ID:
        idx = int(data.replace("del_model_", ""))
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if 0 <= idx < len(models):
            models.pop(idx)
            safe_kv_put("AI_MODELS", models)
            invalidate_models_cache()
        send_admin_models_list(chat_id, query.message.message_id)

    elif data.startswith("del_code_model_") and user_id == ADMIN_ID:
        idx = int(data.replace("del_code_model_", ""))
        code_models = json.loads(safe_kv_get("CODE_MODELS") or "[]")
        if 0 <= idx < len(code_models):
            code_models.pop(idx)
            safe_kv_put("CODE_MODELS", code_models)
            invalidate_models_cache()
        send_admin_models_list(chat_id, query.message.message_id)

    elif data.startswith("del_img_model_") and user_id == ADMIN_ID:
        idx = int(data.replace("del_img_model_", ""))
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if 0 <= idx < len(img_models):
            img_models.pop(idx)
            safe_kv_put("IMAGE_MODELS", img_models)
            invalidate_models_cache()
        send_admin_models_list(chat_id, query.message.message_id)

    elif data.startswith("del_video_model_") and user_id == ADMIN_ID:
        idx = int(data.replace("del_video_model_", ""))
        video_models = json.loads(safe_kv_get("VIDEO_MODELS") or "[]")
        if 0 <= idx < len(video_models):
            video_models.pop(idx)
            safe_kv_put("VIDEO_MODELS", video_models)
            invalidate_models_cache()
        send_admin_models_list(chat_id, query.message.message_id)

    elif data == "admin_add_sponsor" and user_id == ADMIN_ID:
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_SPONSOR")
        bot.send_message(
            chat_id,
            "📢 **افزودن کانال اسپانسر:**\n\nیوزرنیم کانال را بفرستید (مثال: `@neotenet` یا `neotenet`):",
            parse_mode="Markdown",
            reply_markup=get_admin_cancel_markup()
        )

    elif data == "admin_del_sponsor_menu" and user_id == ADMIN_ID:
        send_admin_sponsor_list(chat_id)

    elif data.startswith("edit_sponsor_") and user_id == ADMIN_ID:
        idx = int(data.replace("edit_sponsor_", ""))
        channels = get_sponsor_channels_cached()
        if idx < 0 or idx >= len(channels):
            send_admin_sponsor_list(chat_id, query.message.message_id)
            return
        safe_kv_put(f"ADMIN_STEP_{user_id}", f"EDIT_SPONSOR_{idx}")
        bot.send_message(
            chat_id,
            f"✏️ لینک یا یوزرنیم جدید کانال شمارهٔ {idx + 1} را بفرست.\nمثال: @channelname یا https://t.me/channelname\nبرای لغو از دکمهٔ انصراف استفاده کن.",
            reply_markup=get_admin_cancel_markup()
        )
        return

    elif data.startswith("del_sponsor_") and user_id == ADMIN_ID:
        idx = int(data.replace("del_sponsor_", ""))
        channels = get_sponsor_channels_cached()
        if 0 <= idx < len(channels):
            channels.pop(idx)
            safe_kv_put("SPONSOR_CHANNELS", channels)
            invalidate_sponsors_cache()
        send_admin_sponsor_list(chat_id, query.message.message_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(query):
    """Dispatch callbacks off the update pool; acknowledge safe navigation instantly."""
    # These callbacks only navigate or redraw a screen. Close Telegram's click spinner
    # before the worker does cache/Redis reads and edits the actual menu message.
    fast_navigation = {
        "main_menu", "models_hub", "models_cat_chat", "models_cat_code",
        "models_cat_image", "models_cat_video", "history_menu", "history_help", "close_menu",
    }
    callback_message = getattr(query, "message", None)
    callback_chat_type = getattr(getattr(callback_message, "chat", None), "type", "")
    callback_user_id = str(getattr(getattr(query, "from_user", None), "id", ""))
    if (getattr(query, "data", None) in fast_navigation
            and callback_chat_type not in ("group", "supergroup")
            and (_BOT_STATUS_CACHE is True or callback_user_id == ADMIN_ID)):
        try:
            bot.answer_callback_query(query.id)
        except Exception:
            pass
    try:
        accepted = _submit_bounded(
            _CALLBACK_EXECUTOR, _CALLBACK_SLOTS, _process_callback_query_safely, query
        )
    except Exception as exc:
        print(f"[Callback Dispatch Error]: {exc}")
        accepted = False

    if not accepted:
        # Acknowledge overload so Telegram does not leave the button spinner running forever.
        try:
            bot.answer_callback_query(
                query.id,
                "ربات در حال پردازش درخواست‌های زیادی است؛ لطفاً دوباره تلاش کن.",
                show_alert=False,
            )
        except Exception:
            pass
        message = getattr(query, "message", None)
        if message is not None:
            _notify_job_queue_full(message.chat.id, getattr(message, "message_thread_id", None))


def _process_callback_query_safely(query):
    try:
        _handle_callbacks_impl(query)
    except Exception as exc:
        print(f"[Callback Handler Error] data={getattr(query, 'data', None)!r}: {exc}")
        traceback.print_exc()
        try:
            bot.answer_callback_query(
                query.id,
                "در اجرای این گزینه خطایی رخ داد. لطفاً دوباره تلاش کن.",
                show_alert=True,
            )
        except Exception:
            message = getattr(query, "message", None)
            if message is not None:
                try:
                    bot.send_message(message.chat.id, "⚠️ اجرای این گزینه با خطا روبه‌رو شد؛ دوباره تلاش کن.")
                except Exception:
                    pass


# ==========================================
# ۷. هندلر مراحل پنل مدیریت و ویرایشگر مدل‌ها
# ==========================================
def handle_admin_steps(chat_id, user_id, text, step):
    cancel_m = get_admin_cancel_markup()
    
    if step == "SEARCH_USER_BY_ID":
        target_uid = text.strip()
        if target_uid.isdigit():
            clear_user_state(user_id)
            send_user_profile_card(chat_id, target_uid)
        else:
            bot.send_message(chat_id, "❌ لطفاً فقط آیدی عددی معتبر وارد نمایید:", reply_markup=cancel_m)

    elif step == "MANUAL_ADD_USER":
        new_uid = text.strip()
        if new_uid.isdigit():
            track_user_activity(new_uid, first_name="کاربر ثبت دستی", username="")
            clear_user_state(user_id)
            invalidate_users_cache()
            bot.send_message(chat_id, f"✅ **کاربر با آیدی `{new_uid}` با موفقیت به سیستم اضافه شد.**", parse_mode="Markdown")
            send_user_profile_card(chat_id, new_uid)
        else:
            bot.send_message(chat_id, "❌ لطفاً فقط آیدی عددی معتبر وارد نمایید:", reply_markup=cancel_m)

    elif step == "ADD_MODEL_NAME":
        safe_kv_put(f"TEMP_MODEL_{user_id}", {"name": text})
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_MODEL_URL")
        bot.send_message(chat_id, "🌐 **URL BASE** مربوط به API را وارد کنید:", parse_mode="Markdown", reply_markup=cancel_m)

    elif step == "ADD_MODEL_URL":
        temp = json.loads(safe_kv_get(f"TEMP_MODEL_{user_id}") or "{}")
        temp["baseUrl"] = text
        safe_kv_put(f"TEMP_MODEL_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_MODEL_KEY")
        bot.send_message(chat_id, "🔑 **API KEY** را وارد کنید:", parse_mode="Markdown", reply_markup=cancel_m)

    elif step == "ADD_MODEL_KEY":
        temp = json.loads(safe_kv_get(f"TEMP_MODEL_{user_id}") or "{}")
        temp["apiKey"] = text
        safe_kv_put(f"TEMP_MODEL_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_MODEL_ID")
        bot.send_message(chat_id, "📌 **MODEL NAME** اصلی را وارد کنید:", parse_mode="Markdown", reply_markup=cancel_m)

    elif step == "ADD_MODEL_ID":
        temp = json.loads(safe_kv_get(f"TEMP_MODEL_{user_id}") or "{}")
        temp["modelName"] = text
        safe_kv_put(f"TEMP_MODEL_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_MODEL_VISION")
        bot.send_message(chat_id, "👁 آیا این مدل **Vision** دارد؟ (`yes` یا `no`)", parse_mode="Markdown", reply_markup=cancel_m)

    elif step == "ADD_MODEL_VISION":
        temp = json.loads(safe_kv_get(f"TEMP_MODEL_{user_id}") or "{}")
        temp["supportsVision"] = (text.strip().lower() == "yes")
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        models.append(temp)
        safe_kv_put("AI_MODELS", models)
        invalidate_models_cache()
        clear_user_state(user_id)
        bot.send_message(chat_id, f"✅ مدل چت **{temp.get('name')}** اضافه شد!", parse_mode="Markdown")
        send_admin_models_list(chat_id)

    elif step == "ADD_CODE_NAME":
        safe_kv_put(f"TEMP_CODE_MODEL_{user_id}", {"name": text.strip()})
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_CODE_URL")
        bot.send_message(chat_id, "🌐 Base URL یا endpoint API مدل برنامه‌نویسی را بفرست:", reply_markup=cancel_m)

    elif step == "ADD_CODE_URL":
        temp = json.loads(safe_kv_get(f"TEMP_CODE_MODEL_{user_id}") or "{}")
        temp["baseUrl"] = "" if text.strip() == "." else text.strip()
        safe_kv_put(f"TEMP_CODE_MODEL_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_CODE_KEY")
        bot.send_message(chat_id, "🔑 API Key مدل برنامه‌نویسی را بفرست؛ اگر کلید ندارد، نقطه . بفرست:", reply_markup=cancel_m)

    elif step == "ADD_CODE_KEY":
        temp = json.loads(safe_kv_get(f"TEMP_CODE_MODEL_{user_id}") or "{}")
        temp["apiKey"] = "" if text.strip() == "." else text.strip()
        safe_kv_put(f"TEMP_CODE_MODEL_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_CODE_ID")
        bot.send_message(chat_id, "📌 شناسهٔ Model Name را دقیقاً مطابق مستندات API بفرست:", reply_markup=cancel_m)

    elif step == "ADD_CODE_ID":
        temp = json.loads(safe_kv_get(f"TEMP_CODE_MODEL_{user_id}") or "{}")
        temp["modelName"] = "" if text.strip() == "." else text.strip()
        safe_kv_put(f"TEMP_CODE_MODEL_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_CODE_VISION")
        bot.send_message(chat_id, "👁 مدل برنامه‌نویسی قابلیت دریافت تصویر دارد؟ yes یا no بنویس:", reply_markup=cancel_m)

    elif step == "ADD_CODE_VISION":
        temp = json.loads(safe_kv_get(f"TEMP_CODE_MODEL_{user_id}") or "{}")
        temp["supportsVision"] = text.strip().lower() in {"yes", "y", "بله", "آره", "اره"}
        models = json.loads(safe_kv_get("CODE_MODELS") or "[]")
        if not isinstance(models, list):
            models = []
        models.append(temp)
        safe_kv_put("CODE_MODELS", models)
        invalidate_models_cache()
        clear_user_state(user_id)
        bot.send_message(chat_id, f"✅ مدل برنامه‌نویسی **{temp.get('name')}** اضافه شد.", parse_mode="Markdown")
        send_admin_models_list(chat_id)

    elif step == "ADD_IMG_NAME":
        safe_kv_put(f"TEMP_IMG_{user_id}", {"name": text})
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_IMG_URL")
        bot.send_message(chat_id, "🌐 **URL BASE** تصویرساز را وارد کنید:", parse_mode="Markdown", reply_markup=cancel_m)

    elif step == "ADD_IMG_URL":
        temp = json.loads(safe_kv_get(f"TEMP_IMG_{user_id}") or "{}")
        temp["baseUrl"] = "" if text.strip() == "." else text.strip()
        safe_kv_put(f"TEMP_IMG_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_IMG_KEY")
        bot.send_message(chat_id, "🔑 **API KEY** تصویرساز (اگر Pollinations است . بفرستید):", parse_mode="Markdown", reply_markup=cancel_m)

    elif step == "ADD_IMG_KEY":
        temp = json.loads(safe_kv_get(f"TEMP_IMG_{user_id}") or "{}")
        temp["apiKey"] = "" if text == "." else text
        safe_kv_put(f"TEMP_IMG_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_IMG_ID")
        bot.send_message(chat_id, "📌 **MODEL NAME** تصویرساز را وارد کنید:", parse_mode="Markdown", reply_markup=cancel_m)

    elif step == "ADD_IMG_ID":
        temp = json.loads(safe_kv_get(f"TEMP_IMG_{user_id}") or "{}")
        temp["modelName"] = "" if text.strip() == "." else text.strip()
        safe_kv_put(f"TEMP_IMG_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_IMG_SITE")
        bot.send_message(chat_id, "🔗 آدرس سایت رسمی یا صفحهٔ مدل تصویرساز را وارد کن؛ اگر سایت جداگانه ندارد، نقطه . بفرست. این آدرس به‌تنهایی جای API را نمی‌گیرد.", reply_markup=cancel_m)

    elif step == "ADD_IMG_SITE":
        temp = json.loads(safe_kv_get(f"TEMP_IMG_{user_id}") or "{}")
        temp["siteUrl"] = "" if text.strip() == "." else text.strip()
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        img_models.append(temp)
        safe_kv_put("IMAGE_MODELS", img_models)
        invalidate_models_cache()
        clear_user_state(user_id)
        bot.send_message(chat_id, f"🎨 مدل عکس **{temp.get('name')}** اضافه شد!", parse_mode="Markdown")
        send_admin_models_list(chat_id)

    elif step == "ADD_VIDEO_NAME":
        safe_kv_put(f"TEMP_VIDEO_{user_id}", {"name": text.strip(), "apiKey": "", "baseUrl": "", "modelName": "", "siteUrl": "", "statusUrlTemplate": ""})
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_VIDEO_URL")
        bot.send_message(chat_id, "🌐 Base URL یا endpoint مستند API ساخت ویدیو را وارد کن. اگر فعلاً فقط سایت داری، نقطه . بفرست؛ بعداً می‌توانی سایت را جدا وارد کنی.", reply_markup=cancel_m)

    elif step == "ADD_VIDEO_URL":
        temp = json.loads(safe_kv_get(f"TEMP_VIDEO_{user_id}") or "{}")
        temp["baseUrl"] = "" if text.strip() == "." else text.strip()
        safe_kv_put(f"TEMP_VIDEO_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_VIDEO_KEY")
        bot.send_message(chat_id, "🔑 API Key سرویس ویدیو را بفرست؛ اگر لازم ندارد یا فعلاً فقط سایت داری، نقطه . بفرست.", reply_markup=cancel_m)

    elif step == "ADD_VIDEO_KEY":
        temp = json.loads(safe_kv_get(f"TEMP_VIDEO_{user_id}") or "{}")
        temp["apiKey"] = "" if text.strip() == "." else text.strip()
        safe_kv_put(f"TEMP_VIDEO_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_VIDEO_ID")
        bot.send_message(chat_id, "📌 نام مدل (Model Name) را دقیقاً مطابق مستندات API بفرست؛ اگر نام جداگانه ندارد نقطه . بفرست.", reply_markup=cancel_m)

    elif step == "ADD_VIDEO_ID":
        temp = json.loads(safe_kv_get(f"TEMP_VIDEO_{user_id}") or "{}")
        temp["modelName"] = "" if text.strip() == "." else text.strip()
        safe_kv_put(f"TEMP_VIDEO_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_VIDEO_SITE")
        bot.send_message(chat_id, "🔗 آدرس صفحهٔ سایت سرویس (اختیاری) را بفرست؛ اگر ندارد نقطه . بفرست.", reply_markup=cancel_m)

    elif step == "ADD_VIDEO_SITE":
        temp = json.loads(safe_kv_get(f"TEMP_VIDEO_{user_id}") or "{}")
        temp["siteUrl"] = "" if text.strip() == "." else text.strip()
        safe_kv_put(f"TEMP_VIDEO_{user_id}", temp)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "ADD_VIDEO_STATUS")
        bot.send_message(chat_id, "🔄 قالب URL پیگیری وضعیت job را بفرست؛ جای شناسه از {id} استفاده کن، مثل https://api.example.com/v1/videos/{id}. اگر API مسیر پیش‌فرض endpoint/{id} دارد، نقطه . بفرست.", reply_markup=cancel_m)

    elif step == "ADD_VIDEO_STATUS":
        temp = json.loads(safe_kv_get(f"TEMP_VIDEO_{user_id}") or "{}")
        temp["statusUrlTemplate"] = "" if text.strip() == "." else text.strip()
        video_models = json.loads(safe_kv_get("VIDEO_MODELS") or "[]")
        if not isinstance(video_models, list):
            video_models = []
        video_models.append(temp)
        safe_kv_put("VIDEO_MODELS", video_models)
        invalidate_models_cache()
        clear_user_state(user_id)
        bot.send_message(chat_id, f"🎬 مدل ویدیو **{temp.get('name')}** اضافه شد!\n\nتوجه: سازگاری به نوع API و قالب پاسخ سرویس بستگی دارد.", parse_mode="Markdown")
        send_admin_models_list(chat_id)

    # ویرایش مدل‌های برنامه‌نویسی در فهرست مستقل
    elif step.startswith("EDIT_CODE_NAME_") or step.startswith("EDIT_CODE_URL_") or step.startswith("EDIT_CODE_KEY_") or step.startswith("EDIT_CODE_ID_"):
        prefix_to_field = {
            "EDIT_CODE_NAME_": "name", "EDIT_CODE_URL_": "baseUrl",
            "EDIT_CODE_KEY_": "apiKey", "EDIT_CODE_ID_": "modelName"
        }
        matched_prefix = next((prefix for prefix in prefix_to_field if step.startswith(prefix)), None)
        if matched_prefix:
            idx = int(step.replace(matched_prefix, ""))
            code_models = json.loads(safe_kv_get("CODE_MODELS") or "[]")
            if isinstance(code_models, list) and 0 <= idx < len(code_models):
                value = "" if text.strip() == "." else text.strip()
                code_models[idx][prefix_to_field[matched_prefix]] = value
                safe_kv_put("CODE_MODELS", code_models)
                invalidate_models_cache(); clear_user_state(user_id)
                bot.send_message(chat_id, "✅ تنظیم مدل برنامه‌نویسی ذخیره شد.")
                send_admin_model_edit_card(chat_id, idx, is_code=True)

    # ویرایش مدل‌های چت
    elif step.startswith("EDIT_M_NAME_"):
        idx = int(step.replace("EDIT_M_NAME_", ""))
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if 0 <= idx < len(models):
            models[idx]["name"] = text.strip()
            safe_kv_put("AI_MODELS", models)
            invalidate_models_cache()
            clear_user_state(user_id)
            bot.send_message(chat_id, f"✅ نام مدل با موفقیت به **{text.strip()}** تغییر یافت.")
            send_admin_model_edit_card(chat_id, idx, is_img=False)

    elif step.startswith("EDIT_M_URL_"):
        idx = int(step.replace("EDIT_M_URL_", ""))
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if 0 <= idx < len(models):
            models[idx]["baseUrl"] = text.strip()
            safe_kv_put("AI_MODELS", models)
            invalidate_models_cache()
            clear_user_state(user_id)
            bot.send_message(chat_id, f"✅ آدرس Base URL مدل با موفقیت به‌روزرسانی شد.")
            send_admin_model_edit_card(chat_id, idx, is_img=False)

    elif step.startswith("EDIT_M_KEY_"):
        idx = int(step.replace("EDIT_M_KEY_", ""))
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if 0 <= idx < len(models):
            models[idx]["apiKey"] = "" if text.strip() == "." else text.strip()
            safe_kv_put("AI_MODELS", models)
            invalidate_models_cache()
            clear_user_state(user_id)
            bot.send_message(chat_id, f"✅ کلید API Key مدل با موفقیت ذخیره شد.")
            send_admin_model_edit_card(chat_id, idx, is_img=False)

    elif step.startswith("EDIT_M_ID_"):
        idx = int(step.replace("EDIT_M_ID_", ""))
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if 0 <= idx < len(models):
            models[idx]["modelName"] = text.strip()
            safe_kv_put("AI_MODELS", models)
            invalidate_models_cache()
            clear_user_state(user_id)
            bot.send_message(chat_id, f"✅ شناسه Model Name با موفقیت به **{text.strip()}** تغییر یافت.")
            send_admin_model_edit_card(chat_id, idx, is_img=False)

    # ویرایش مدل‌های تصویر
    elif step.startswith("EDIT_IMG_NAME_"):
        idx = int(step.replace("EDIT_IMG_NAME_", ""))
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if 0 <= idx < len(img_models):
            img_models[idx]["name"] = text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
            invalidate_models_cache()
            clear_user_state(user_id)
            bot.send_message(chat_id, f"🎨 نام مدل عکس با موفقیت به **{text.strip()}** تغییر یافت.")
            send_admin_model_edit_card(chat_id, idx, is_img=True)

    elif step.startswith("EDIT_IMG_URL_"):
        idx = int(step.replace("EDIT_IMG_URL_", ""))
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if 0 <= idx < len(img_models):
            img_models[idx]["baseUrl"] = text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
            invalidate_models_cache()
            clear_user_state(user_id)
            bot.send_message(chat_id, f"🌐 آدرس Base URL مدل عکس با موفقیت به‌روزرسانی شد.")
            send_admin_model_edit_card(chat_id, idx, is_img=True)

    elif step.startswith("EDIT_IMG_KEY_"):
        idx = int(step.replace("EDIT_IMG_KEY_", ""))
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if 0 <= idx < len(img_models):
            img_models[idx]["apiKey"] = "" if text.strip() == "." else text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
            invalidate_models_cache()
            clear_user_state(user_id)
            bot.send_message(chat_id, f"🔑 کلید API Key مدل عکس با موفقیت ذخیره شد.")
            send_admin_model_edit_card(chat_id, idx, is_img=True)

    elif step.startswith("EDIT_IMG_ID_"):
        idx = int(step.replace("EDIT_IMG_ID_", ""))
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if 0 <= idx < len(img_models):
            img_models[idx]["modelName"] = text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
            invalidate_models_cache()
            clear_user_state(user_id)
            bot.send_message(chat_id, f"📌 شناسه Model Name مدل عکس با موفقیت به **{text.strip()}** تغییر یافت.")
            send_admin_model_edit_card(chat_id, idx, is_img=True)

    elif step.startswith("EDIT_IMG_SITE_"):
        idx = int(step.replace("EDIT_IMG_SITE_", ""))
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        if 0 <= idx < len(img_models):
            img_models[idx]["siteUrl"] = "" if text.strip() == "." else text.strip()
            safe_kv_put("IMAGE_MODELS", img_models)
            invalidate_models_cache(); clear_user_state(user_id)
            bot.send_message(chat_id, "🔗 آدرس وب‌سایت تصویرساز ذخیره شد.")
            send_admin_model_edit_card(chat_id, idx, is_img=True)

    elif step.startswith("EDIT_VIDEO_NAME_") or step.startswith("EDIT_VIDEO_URL_") or step.startswith("EDIT_VIDEO_KEY_") or step.startswith("EDIT_VIDEO_ID_") or step.startswith("EDIT_VIDEO_SITE_") or step.startswith("EDIT_VIDEO_STATUS_"):
        prefix_to_field = {
            "EDIT_VIDEO_NAME_": "name", "EDIT_VIDEO_URL_": "baseUrl", "EDIT_VIDEO_KEY_": "apiKey",
            "EDIT_VIDEO_ID_": "modelName", "EDIT_VIDEO_SITE_": "siteUrl", "EDIT_VIDEO_STATUS_": "statusUrlTemplate"
        }
        matched_prefix = next((prefix for prefix in prefix_to_field if step.startswith(prefix)), None)
        if matched_prefix:
            idx = int(step.replace(matched_prefix, ""))
            video_models = json.loads(safe_kv_get("VIDEO_MODELS") or "[]")
            if isinstance(video_models, list) and 0 <= idx < len(video_models):
                value = "" if text.strip() == "." else text.strip()
                video_models[idx][prefix_to_field[matched_prefix]] = value
                safe_kv_put("VIDEO_MODELS", video_models)
                invalidate_models_cache(); clear_user_state(user_id)
                bot.send_message(chat_id, "✅ تنظیم مدل ویدیو ذخیره شد.")
                send_admin_model_edit_card(chat_id, idx, is_video=True)

    elif step.startswith("EDIT_SPONSOR_"):
        try:
            idx = int(step.replace("EDIT_SPONSOR_", ""))
            clean_ch = clean_channel_username(text)
            if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", clean_ch):
                raise ValueError("invalid public channel username")
            channels = get_sponsor_channels_cached()
            if idx < 0 or idx >= len(channels):
                clear_user_state(user_id)
                bot.send_message(chat_id, "❌ کانال انتخاب‌شده دیگر در فهرست نیست.")
                send_admin_sponsor_list(chat_id)
                return
            if clean_ch in channels and channels[idx] != clean_ch:
                bot.send_message(chat_id, "⚠️ این کانال از قبل در فهرست وجود دارد. لینک دیگری بفرست:", reply_markup=cancel_m)
                return
            channels[idx] = clean_ch
            safe_kv_put("SPONSOR_CHANNELS", channels)
            invalidate_sponsors_cache()
            clear_user_state(user_id)
            bot.send_message(chat_id, f"✅ لینک کانال اسپانسر به @{clean_ch} تغییر کرد.")
            send_admin_sponsor_list(chat_id)
        except Exception:
            bot.send_message(chat_id, "❌ یوزرنیم عمومی معتبر بفرست؛ مثلاً @channelname. لینک دعوت خصوصی به‌عنوان یوزرنیم قابل استفاده نیست.", reply_markup=cancel_m)

    elif step == "ADD_SPONSOR":
        clean_ch = clean_channel_username(text)
        if clean_ch:
            channels = get_sponsor_channels_cached()
            if clean_ch not in channels:
                channels.append(clean_ch)
                safe_kv_put("SPONSOR_CHANNELS", channels)
                invalidate_sponsors_cache()
            clear_user_state(user_id)
            bot.send_message(chat_id, f"📢 کانال اسپانسر `{clean_ch}` با موفقیت اضافه شد.", parse_mode="Markdown")
            bot.send_message(chat_id, "🛠 **پنل مدیریت ربات**", reply_markup=get_admin_panel_markup())
        else:
            bot.send_message(chat_id, "❌ یوزرنیم کانال نامعتبر است.", reply_markup=cancel_m)

# ==========================================
# ۸. اجرای مداوم ربات (Long Polling بدون قطعی)
# ==========================================
if __name__ == "__main__":
    required_env = {
        "BOT_TOKEN": BOT_TOKEN,
        "ADMIN_ID": ADMIN_ID,
        "UPSTASH_URL": UPSTASH_URL,
        "UPSTASH_TOKEN": UPSTASH_TOKEN,
    }
    missing_env = [key for key, value in required_env.items() if not value]
    if missing_env:
        raise SystemExit(
            "Missing required environment variables: " + ", ".join(missing_env) +
            ". Configure them in your hosting panel before starting the bot."
        )

    print("=" * 45)
    print("🤖 Neo-AI-Bot (Ultra-Fast Tech & Model Editor Engine) Started")
    print("⚡ Connected to Upstash Redis REST Database")
    print(f"API read timeout: {API_TIMEOUT_SECONDS // 60} minutes | Static processing status | Fast UI caches active")
    print(f"🧵 Telegram handlers: {TELEGRAM_HANDLER_THREADS} | Callback workers: {CALLBACK_WORKERS}+{CALLBACK_QUEUE_LIMIT}")
    print(f"⚙️ Chat/Code workers: {AI_JOB_WORKERS}+{AI_JOB_QUEUE_LIMIT} | Group workers: {GROUP_AI_JOB_WORKERS}+{GROUP_AI_JOB_QUEUE_LIMIT}")
    print(f"🎨 Image workers: {IMAGE_JOB_WORKERS}+{IMAGE_JOB_QUEUE_LIMIT} | 🎬 Video workers: {VIDEO_JOB_WORKERS}+{VIDEO_JOB_QUEUE_LIMIT}")
    print("🚀 Instant /start Enabled (< 0.2s)")
    print("🌐 Bilingual Support Active (FA / EN)")
    print("🛠 Full Model Editing & Vision Toggling Enabled")
    print("🌐 Provider-native web search enabled when supported by the selected API")
    print("🛡️ Group Moderation & Administration Engine Active")
    print("👥 Complete User Management CRM Active")
    print("=" * 45)

    try:
        bot.remove_webhook()
    except Exception as e:
        print(f"[Webhook Removal]: {type(e).__name__}")

    # Warm quick-read caches before polling so the first real request is not delayed by preflight GETs.
    try:
        is_bot_globally_active()
    except Exception as exc:
        print(f"[Startup Status Cache Warning]: {type(exc).__name__}")
    try:
        get_bot_info_cached(force_refresh=True)
    except Exception as exc:
        print(f"[Startup getMe Cache Warning]: {type(exc).__name__}")
    try:
        warm_counts = warm_model_registry_cache()
        print("[Startup Model Cache] " + ", ".join(f"{key}={count}" for key, count in warm_counts.items()))
    except Exception as exc:
        print(f"[Startup Model Cache Warning]: {type(exc).__name__}")

    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
        except Exception as e:
            print(f"[Polling Error]: {e}")
            time.sleep(5)
