# -*- coding: utf-8 -*-
"""
Telegram AI Bot - Python + Upstash Redis (100% Safe & Stable)
Configured for: bot-hosting.net (Docker / NAT Environment)
Features:
- Guaranteed Group & Private File-Only Code Delivery (.py, .js, .html, .cpp, .txt)
- Anti-Clutter: No long code dumps in group or private chats
- Strict UTF-8 Streaming Engine (No Mojibake)
- Full Image Generation Support (SiliconFlow, Together, Flux)
- TCP Keep-Alive Connection Resilience
- Admin Broadcast Engine
Timeout: 35 Minutes (2100s) | Updates Every 5 Seconds
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
from telebot.apihelper import ApiTelegramException

# ==========================================
# ⚙️ تنظیمات اصلی و اطلاعات دیتابیس Upstash
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "7123456789:AAFlm4bXYZ_YOUR_REAL_TOKEN_HERE")
ADMIN_ID = str(os.getenv("ADMIN_ID", "123456789"))

UPSTASH_URL = os.getenv("UPSTASH_URL", "https://your-upstash-url.upstash.io")
UPSTASH_TOKEN = os.getenv("UPSTASH_TOKEN", "YOUR_UPSTASH_REST_TOKEN")

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
adapter = TCPKeepAliveAdapter()
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
# توابع بررسی دسترسی و مدیریت کاربر
# ==========================================
def track_user_activity(user_id):
    users = json.loads(safe_kv_get("BOT_USERS") or "[]")
    if user_id not in users:
        users.append(user_id)
        safe_kv_put("BOT_USERS", users)
    safe_kv_put(f"LAST_ACTIVE_{user_id}", str(int(time.time() * 1000)))

def clear_user_state(user_id):
    for key in [
        f"ADMIN_STEP_{user_id}", f"TEMP_MODEL_{user_id}",
        f"TEMP_IMG_{user_id}", f"ADMIN_EDIT_IDX_{user_id}",
        f"ADMIN_EDIT_IMG_IDX_{user_id}"
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
        sessions.insert(0, {"id": active_id, "title": "گفتگوی جدید 💬", "date": time.strftime("%Y/%m/%d")})
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
    if not text:
        return False
    lower = text.lower()
    code_keywords = [
        'code', 'script', 'bug', 'error', 'function', 'const', 'let', 'var', 
        'import', 'export', 'def', 'class', 'html', 'css', 'js', 'python', 
        'c++', 'java', 'sql', 'json', 'async', 'await', 'return', 'if', 'else',
        'کد', 'برنامه', 'اسکریپت', 'باگ', 'خطا', 'دیباگ', 'خط', 'توابع', 'متغیر', 'ارور', 'بساز', 'بنویس'
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
# 📁 سیستم تفکیک کد از متن و ساخت فایل
# ==========================================
def process_code_and_text(raw_text, is_code_prompt):
    pattern = r'```([a-zA-Z0-9_+-]*)[^\n]*\r?\n([\s\S]*?)```'
    matches = re.findall(pattern, raw_text)
    
    code_files = []

    ext_map = {
        'python': 'py', 'py': 'py',
        'javascript': 'js', 'js': 'js',
        'typescript': 'ts', 'ts': 'ts',
        'html': 'html', 'css': 'css',
        'cpp': 'cpp', 'c++': 'cpp', 'c': 'c',
        'java': 'java', 'kotlin': 'kt',
        'php': 'php', 'sql': 'sql',
        'json': 'json', 'xml': 'xml',
        'bash': 'sh', 'sh': 'sh', 'shell': 'sh',
        'go': 'go', 'golang': 'go',
        'rust': 'rs', 'rs': 'rs',
        'lua': 'lua', 'csharp': 'cs', 'cs': 'cs',
        'ruby': 'rb', 'rb': 'rb',
        'swift': 'swift', 'dart': 'dart',
        'yaml': 'yml', 'yml': 'yml',
        'txt': 'txt', 'text': 'txt'
    }

    if matches:
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

        def clean_replacer(match):
            lang = match.group(1).strip()
            lang_display = lang.upper() if lang else "کد"
            return f"\n\n📦 **[سورس {lang_display} در فایل زیر ضمیمه شد]**\n"

        cleaned_text = re.sub(pattern, clean_replacer, raw_text).strip()

        check_empty = re.sub(r'📦 \*\*\[سورس .*? ضمیمه شد\]\*\*', '', cleaned_text).strip()
        if len(check_empty) < 10:
            cleaned_text = "✅ **کد درخواستی شما با موفقیت تولید شد و در فایل زیر ضمیمه گردید:**"

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
        cleaned_text = "✅ **کد درخواستی شما با موفقیت آماده شد و در فایل زیر ضمیمه گردید:**"
        return cleaned_text, code_files

    return raw_text, []

# ==========================================
# 📤 تابع تضمینی ارسال فایل در گروه و پیوی (اصلاح باگ آرگومان)
# ==========================================
def send_code_document_safe(chat_id, byte_data, filename, ext, reply_to_id=None, thread_id=None):
    caption = f"📁 فایل سورس کد ({ext.upper()}): {filename}"

    def make_bio():
        b = io.BytesIO(byte_data)
        b.name = filename
        b.seek(0)
        return b

    # تلاش اول: ارسال با ریپلای و بدون باگ نام پارامتر
    try:
        kwargs = {"caption": caption}
        if reply_to_id:
            kwargs["reply_to_message_id"] = reply_to_id
            kwargs["allow_sending_without_reply"] = True
        if thread_id:
            kwargs["message_thread_id"] = thread_id

        # ارسال به صورت پوزیشنال (chat_id, data) برای حل قطعی ارور pyTelegramBotAPI
        bot.send_document(chat_id, make_bio(), **kwargs)
        return True
    except TypeError:
        # در صورتی که نسخه telebot آرگومان allow_sending_without_reply را نداشت
        try:
            bot.send_document(chat_id, make_bio(), caption=caption, reply_to_message_id=reply_to_id)
            return True
        except Exception:
            pass
    except Exception as e1:
        print(f"[Document Send Error 1]: {e1}")

    # تلاش دوم: ارسال مستقیم به چت گروه در صورت رد شدن ریپلای توسط تلگرام
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
# ۱. رابط کاربری و منوها (چینش ۲ تایی دکمه‌ها)
# ==========================================
def get_main_menu_markup(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💬 گفتگو و کدنویسی", callback_data="mode_chat"),
        types.InlineKeyboardButton("🎨 تصویرسازی هوش مصنوعی", callback_data="mode_image")
    )
    markup.add(
        types.InlineKeyboardButton("🤖 انتخاب مدل هوش مصنوعی", callback_data="select_model_menu"),
        types.InlineKeyboardButton("📜 تاریخچه گفتگوها", callback_data="history_menu")
    )
    row3 = [types.InlineKeyboardButton("➕ شروع گفتگوی جدید", callback_data="new_chat")]
    if str(user_id) == str(ADMIN_ID):
        row3.append(types.InlineKeyboardButton("⚙️ پنل مدیریت ادمین", callback_data="admin_panel"))
    markup.add(*row3)
    return markup

def send_main_menu(chat_id, user_id):
    bot.send_message(
        chat_id,
        "🚀سلام دوست خوبم به ربات هوش مصنوعی خودت خوش امدی از منو پایین گزینه مورد نظرت رو انتخاب کن 🫡!",
        reply_markup=get_main_menu_markup(user_id)
    )

def send_history_menu(chat_id, user_id):
    sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
    active_sess = safe_kv_get(f"ACTIVE_SESSION_{user_id}")

    if not sessions:
        bot.send_message(chat_id, "📜 هیچ تاریخچه گفتگویی یافت نشد.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for s in sessions[:10]:
        is_cur = "🟢 " if s.get("id") == active_sess else "💬 "
        date_str = s.get("date", "")
        title = f"{is_cur}{s.get('title')} [{date_str}]"
        buttons.append(types.InlineKeyboardButton(title, callback_data=f"switch_sess_{s.get('id')}"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    markup.add(
        types.InlineKeyboardButton("➕ ایجاد چت جدید", callback_data="new_chat"),
        types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu")
    )
    bot.send_message(chat_id, "📜 **لیست گفتگوهای قبلی شما:**", parse_mode="Markdown", reply_markup=markup)

def send_model_selection_menu(chat_id, target_key_id):
    models = json.loads(safe_kv_get("AI_MODELS") or "[]")
    current_idx = safe_kv_get(f"USER_MODEL_{target_key_id}") or "0"

    if not models:
        bot.send_message(chat_id, "⚠️ هیچ مدلی تعریف نشده است.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for idx, m in enumerate(models):
        chk = "✅ " if str(idx) == str(current_idx) else "🤖 "
        vis = " 👁️" if m.get("supportsVision") else ""
        btn_text = f"{chk}{m.get('name')}{vis}"
        buttons.append(types.InlineKeyboardButton(btn_text, callback_data=f"set_model_{idx}"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu"))
    bot.send_message(chat_id, "✨ **مدل هوش مصنوعی چت را انتخاب کنید:**", parse_mode="Markdown", reply_markup=markup)

def send_image_model_selection_menu(chat_id, user_id):
    img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
    current_idx = safe_kv_get(f"USER_IMG_MODEL_{user_id}") or "0"

    if not img_models:
        bot.send_message(chat_id, "⚠️ هیچ مدل تصویرسازی تعریف نشده است.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for idx, m in enumerate(img_models):
        chk = "✅ " if str(idx) == str(current_idx) else "🎨 "
        buttons.append(types.InlineKeyboardButton(f"{chk}{m.get('name')}", callback_data=f"set_img_model_{idx}"))

    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    markup.add(types.InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main_menu"))
    bot.send_message(chat_id, "🎨 **مدل ساخت عکس را انتخاب کنید:**", parse_mode="Markdown", reply_markup=markup)

# ==========================================
# ۲. پنل مدیریت ادمین (ارسال پیام همگانی)
# ==========================================
def get_admin_panel_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_stats"),
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")
    )
    markup.add(
        types.InlineKeyboardButton("➕ افزودن مدل چت", callback_data="admin_add_model"),
        types.InlineKeyboardButton("🎨 افزودن مدل عکس", callback_data="admin_add_img_model")
    )
    markup.add(
        types.InlineKeyboardButton("📋 لیست مدل‌ها", callback_data="admin_list_models"),
        types.InlineKeyboardButton("✏️ ویرایش مدل‌ها", callback_data="admin_edit_models_menu")
    )
    markup.add(
        types.InlineKeyboardButton("📢 افزودن اسپانسر", callback_data="admin_add_sponsor"),
        types.InlineKeyboardButton("🗑 حذف اسپانسر", callback_data="admin_del_sponsor_menu")
    )
    markup.add(
        types.InlineKeyboardButton("🚫 مسدودسازی کاربر", callback_data="admin_ban_user"),
        types.InlineKeyboardButton("✅ رفع مسدودی", callback_data="admin_unban_user")
    )
    markup.add(
        types.InlineKeyboardButton("🔙 منوی اصلی", callback_data="main_menu")
    )
    return markup

def send_bot_stats(chat_id):
    users = json.loads(safe_kv_get("BOT_USERS") or "[]")
    now_ms = int(time.time() * 1000)
    day_ms = 24 * 60 * 60 * 1000
    active_count = 0

    for u in users:
        last = safe_kv_get(f"LAST_ACTIVE_{u}")
        if last and (now_ms - int(last)) < day_ms:
            active_count += 1

    text = f"📊 **آمار جامع کاربران ربات:**\n\n👥 کل کاربران ثبت‌نامی: **{len(users)}**\n🟢 کاربران آنلاین / فعال (۲۴ ساعت گذشته): **{active_count}**"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin_panel"))
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def broadcast_worker(admin_chat_id, message_id):
    users = json.loads(safe_kv_get("BOT_USERS") or "[]")
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
        buttons.append(types.InlineKeyboardButton(f"🗑 چت: {m.get('name')}", callback_data=f"del_model_{idx}"))
    for idx, m in enumerate(img_models):
        buttons.append(types.InlineKeyboardButton(f"🗑 عکس: {m.get('name')}", callback_data=f"del_img_model_{idx}"))

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
        buttons.append(types.InlineKeyboardButton(f"✏️ چت: {m.get('name')}", callback_data=f"edit_model_{idx}"))
    for idx, m in enumerate(img_models):
        buttons.append(types.InlineKeyboardButton(f"✏️ عکس: {m.get('name')}", callback_data=f"edit_img_model_{idx}"))

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
        buttons.append(types.InlineKeyboardButton(f"🗑 {ch}", callback_data=f"del_sponsor_{idx}"))

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
# ۳. پردازش چت با Streaming، دیکود UTF-8 و ارسال قطعی فایل در گروه و پیوی
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
        text_prompt = "لطفاً بررسی کن یا پاسخ بده."
    is_code = is_code_request(text_prompt)

    req_id = f"{user_id}_{int(time.time()*1000)}"
    cancel_markup = types.InlineKeyboardMarkup()
    cancel_markup.add(types.InlineKeyboardButton("❌ لغو و توقف فکر کردن", callback_data=f"cancel_req_{req_id}"))

    reply_to = target_reply_id if target_reply_id else (message.message_id if is_group else None)
    initial_text = "💻 در حال نوشتن و آماده‌سازی فایل کد... (۵ ثانیه)" if is_code else "🧠 در حال فکر کردن و ارتباط با API... (۵ ثانیه)"

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

    def timer_loop():
        sec = 5
        while not is_done and sec < 2100:
            time.sleep(5)
            if is_done:
                break
            if safe_kv_get(f"CANCEL_{req_id}") == "true":
                break
            sec += 5
            try:
                bot.send_chat_action(chat_id, "typing")
            except:
                pass

            mins = sec // 60
            secs = sec % 60
            if mins > 0:
                time_display = f"{mins} دقیقه و {secs} ثانیه" if secs > 0 else f"{mins} دقیقه"
            else:
                time_display = f"{secs} ثانیه"

            cur_txt = f"💻 در حال پردازش و تولید فایل کد... ({time_display})" if is_code else f"🧠 در حال دریافت و تحلیل هوش مصنوعی... ({time_display})"
            try:
                bot.edit_message_text(cur_txt, chat_id=chat_id, message_id=status_msg_id, reply_markup=cancel_markup)
            except ApiTelegramException as te:
                if te.error_code == 429:
                    time.sleep(te.result_json.get('parameters', {}).get('retry_after', 3))
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

        cleaned_messages = []
        for idx, item in enumerate(history):
            if idx < len(history) - 1 and isinstance(item.get("content"), list):
                txt_part = next((p.get("text") for p in item["content"] if p.get("type") == "text"), "تصویر قبلی")
                cleaned_messages.append({"role": item["role"], "content": f"[تصویر ارسال شده: {txt_part}]"})
            else:
                cleaned_messages.append(item)

        while cleaned_messages and cleaned_messages[0].get("role") == "assistant":
            cleaned_messages.pop(0)

        if len(cleaned_messages) > 10:
            cleaned_messages = cleaned_messages[-10:]
            if cleaned_messages and cleaned_messages[0].get("role") == "assistant":
                cleaned_messages.pop(0)

        base_url = active_model.get("baseUrl", "").strip().rstrip("/")
        endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"

        system_prompt = {
            "role": "system",
            "content": "You are an expert AI software engineer. Whenever code is requested, ALWAYS enclose the complete code inside markdown codeblocks with the proper language tag (e.g. ```python\\n...\\n```). Provide a clean, brief summary."
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

                api_response_text = full_content if full_content.strip() else full_reasoning
            else:
                try:
                    data = res.json()
                except Exception:
                    data = json.loads(res.content.decode('utf-8', errors='replace'))
                
                msg_obj = data.get("choices", [{}])[0].get("message", {})
                c = msg_obj.get("content", "")
                r = msg_obj.get("reasoning_content", "")
                api_response_text = c if (c and c.strip()) else r
        else:
            api_response_text = f"❌ خطای سرور API (کد {res.status_code}):\n{res.text[:250]}"

        if api_response_text and not api_response_text.startswith("❌"):
            history.append({"role": "assistant", "content": api_response_text})
            hist_to_save = []
            for item in history[-12:]:
                if isinstance(item.get("content"), list):
                    txt_part = next((p.get("text") for p in item["content"] if p.get("type") == "text"), "تصویر")
                    hist_to_save.append({"role": item["role"], "content": txt_part})
                else:
                    hist_to_save.append(item)

            safe_kv_put(f"HISTORY_{user_id}_{active_session_id}", hist_to_save)
            update_session_title_if_new(user_id, active_session_id, text_prompt)

    except requests.exceptions.Timeout:
        api_response_text = "❌ زمان ارسال درخواست به بیش از ۳۵ دقیقه رسید و ارتباط قطع شد."
    except requests.exceptions.ConnectionError as ce:
        api_response_text = "❌ خطای قطع ارتباط با سرور هوش مصنوعی (ارتباط بسته شد)."
    except Exception as e:
        api_response_text = f"❌ خطای ارتباطی: {type(e).__name__} - {str(e)[:100]}"
    finally:
        is_done = True
        safe_kv_delete(f"CANCEL_{req_id}")

    if api_response_text and not api_response_text.startswith("❌"):
        clean_text, code_files = process_code_and_text(api_response_text, is_code)

        if is_group:
            sender_name = f"@{message.from_user.username}" if message.from_user.username else (message.from_user.first_name or "کاربر")
            final_text = f"👤 کاربر: {sender_name}\n🤖 مدل: {active_model.get('name')}\n-------------------\n\n{clean_text}"
        else:
            final_text = clean_text

        # ۱. ارسال متن تمیز
        send_safe_ai_response(chat_id, status_msg_id, final_text, reply_to, thread_id)
        
        # ۲. ارسال تضمینی و قطعی فایل در همان گروه یا پی‌وی
        for filename, byte_data, ext in code_files:
            send_code_document_safe(
                chat_id=chat_id,
                byte_data=byte_data,
                filename=filename,
                ext=ext,
                reply_to_id=reply_to,
                thread_id=thread_id
            )
    else:
        if safe_kv_get(f"CANCEL_{req_id}") != "true":
            try:
                bot.edit_message_text(api_response_text or "❌ سرور پاسخی ارسال نکرد (پاسخ خالی بود).", chat_id=chat_id, message_id=status_msg_id)
            except:
                pass

# ==========================================
# ۴. پردازش ساخت عکس (سازگار با SiliconFlow, Together و Pollinations)
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
    status_msg = bot.send_message(chat_id, "🎨 در حال ساخت تصویر... (۵ ثانیه)", message_thread_id=thread_id)
    status_msg_id = status_msg.message_id
    is_done = False
    image_url = None
    error_msg = None

    def timer_loop():
        sec = 5
        while not is_done and sec < 2100:
            time.sleep(5)
            if is_done:
                break
            sec += 5
            mins = sec // 60
            secs = sec % 60
            if mins > 0:
                time_display = f"{mins} دقیقه و {secs} ثانیه" if secs > 0 else f"{mins} دقیقه"
            else:
                time_display = f"{secs} ثانیه"
            try:
                bot.edit_message_text(f"🎨 در حال ساخت تصویر و رندر... ({time_display})", chat_id=chat_id, message_id=status_msg_id)
            except ApiTelegramException as te:
                if te.error_code == 429:
                    time.sleep(te.result_json.get('parameters', {}).get('retry_after', 3))
            except Exception:
                pass

    threading.Thread(target=timer_loop, daemon=True).start()

    try:
        base_url = active_img_model.get("baseUrl", "").strip().rstrip("/")
        api_key = active_img_model.get("apiKey", "").strip()
        model_name = active_img_model.get("modelName", "").strip()

        if "pollinations.ai" in base_url:
            encoded_prompt = urllib.parse.quote(prompt_text)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            if model_name and model_name.lower() != "flux":
                image_url += f"?model={model_name}"
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
            if res.status_code == 200:
                data = res.json()
                if "data" in data and len(data["data"]) > 0:
                    image_url = data["data"][0].get("url")
            else:
                error_msg = f"کد خطا: {res.status_code}\n{res.text[:200]}"
    except Exception as e:
        error_msg = str(e)
    finally:
        is_done = True

    if image_url:
        try:
            bot.delete_message(chat_id, status_msg_id)
        except:
            pass
        caption = f"✨ **تصویر تولید شده با {active_img_model.get('name')}**\n\n📝 **پرامپت:** {prompt_text}"
        try:
            bot.send_photo(chat_id, image_url, caption=caption, parse_mode="Markdown", message_thread_id=thread_id)
        except:
            bot.send_photo(chat_id, image_url, caption=caption, message_thread_id=thread_id)
    else:
        try:
            bot.edit_message_text(f"❌ ساخت تصویر با خطا مواجه شد.\n{error_msg or ''}", chat_id=chat_id, message_id=status_msg_id)
        except:
            pass

# ==========================================
# ۵. هندلر پیام‌ها و رویدادهای تلگرام
# ==========================================
@bot.message_handler(content_types=['text', 'photo', 'document', 'video', 'audio', 'voice'])
def handle_all_messages(msg):
    if not msg.from_user:
        return

    chat_id = msg.chat.id
    user_id = str(msg.from_user.id)
    text = msg.text or msg.caption or ""
    is_group = msg.chat.type in ["group", "supergroup"]
    thread_id = getattr(msg, 'message_thread_id', None) if getattr(msg, 'is_topic_message', False) else None

    threading.Thread(target=track_user_activity, args=(user_id,), daemon=True).start()

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

    if not is_group:
        admin_step = safe_kv_get(f"ADMIN_STEP_{user_id}")
        if admin_step and user_id == ADMIN_ID:
            if admin_step == "BROADCAST_MSG":
                clear_user_state(user_id)
                threading.Thread(target=broadcast_worker, args=(chat_id, msg.message_id), daemon=True).start()
                return
            else:
                handle_admin_steps(chat_id, user_id, text, admin_step)
                return

        ok_sponsor, unjoined = check_sponsor_join(user_id)
        if not ok_sponsor and ADMIN_ID and user_id != ADMIN_ID:
            markup = types.InlineKeyboardMarkup(row_width=2)
            buttons = [types.InlineKeyboardButton(f"📢 ورود به کانال {ch}", url=f"https://t.me/{ch.replace('@', '')}") for ch in unjoined]
            for i in range(0, len(buttons), 2):
                markup.row(*buttons[i:i+2])
            markup.add(types.InlineKeyboardButton("✅ عضو شدم / بررسی", callback_data="check_sponsor"))
            bot.send_message(chat_id, "⚠️ برای استفاده از ربات ابتدا باید در کانال(های) اسپانسر زیر عضو شوید:", reply_markup=markup)
            return

    if text.startswith("/start"):
        if is_group:
            if not is_group_admin(chat_id, user_id):
                return
            bot_info = bot.get_me()
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🤖 ورود به پیوی ربات", url=f"https://t.me/{bot_info.username}?start=true"))
            bot.reply_to(
                msg,
                "⚠️ **منوی تنظیمات و مدیریت ربات فقط در چت خصوصی (پیوی) قابل استفاده است.**\n\nجهت استفاده از امکانات ربات روی دکمه زیر کلیک کنید:",
                parse_mode="Markdown",
                reply_markup=markup,
                allow_sending_without_reply=True
            )
            return
        clear_user_state(user_id)
        send_main_menu(chat_id, user_id)
        return

    if text.startswith("/models"):
        if is_group:
            if not is_group_admin(chat_id, user_id):
                bot.reply_to(msg, "⛔ تغییر مدل ربات در گروه فقط توسط ادمین‌های گروه مجاز است.", allow_sending_without_reply=True)
                return
        elif ADMIN_ID and user_id != ADMIN_ID:
            bot.send_message(chat_id, "⛔ این دستور تنها برای ادمین ربات مجاز است.")
            return

        target_key = f"group_{chat_id}" if is_group else user_id
        send_model_selection_menu(chat_id, target_key)
        return

    target_reply_id = msg.message_id
    if is_group:
        bot_info = bot.get_me()
        bot_username = f"@{bot_info.username.lower()}"
        bot_id = str(bot_info.id)
        lower_text = text.lower().strip()

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
                    "🔹 `/bot صحبت` ➔ فعال‌سازی مجدد ربات در گروه\n\n"
                    "💡 *نکته:* این دستورات صرفاً توسط ادمین‌ها قابل اجرا هستند."
                )
                bot.reply_to(msg, help_text, parse_mode="Markdown", allow_sending_without_reply=True)
                return

        if safe_kv_get(f"GROUP_MUTED_{chat_id}") == "true":
            return

        is_reply_to_bot = msg.reply_to_message and str(msg.reply_to_message.from_user.id) == bot_id
        is_mentioned = False

        if msg.entities:
            for ent in msg.entities:
                if ent.type in ["mention", "text_mention"]:
                    mention_val = text[ent.offset:ent.offset + ent.length].lower()
                    if mention_val == bot_username:
                        is_mentioned = True

        if bot_username in lower_text:
            is_mentioned = True

        call_prefixes = ["bot", "ai", "ربات", "پاسخ"]
        starts_prefix = any(lower_text == p or lower_text.startswith(p + " ") or lower_text.startswith(p + "\n") for p in call_prefixes)

        if not is_reply_to_bot and not is_mentioned and not starts_prefix:
            return

        text = text.replace(bot_username, "").replace(f"@{bot_info.username}", "").strip()
        for p in call_prefixes:
            if lower_text == p or lower_text.startswith(p + " ") or lower_text.startswith(p + "\n"):
                text = text[len(p):].strip()
                break

        if msg.reply_to_message and str(msg.reply_to_message.from_user.id) != bot_id:
            target_user = msg.reply_to_message.from_user
            target_name = target_user.first_name or "کاربر"
            target_reply_id = msg.reply_to_message.message_id
            replied_text = msg.reply_to_message.text or msg.reply_to_message.caption or ""

            if msg.reply_to_message.photo and not msg.photo:
                msg.photo = msg.reply_to_message.photo

            prompt_inst = text.strip() if text.strip() else "لطفاً بررسی کن و پاسخ کامل بده."
            text = f'[پیام اصلی کاربر ({target_name}): "{replied_text or "تصویر/فایل بدون متن"}" ]\n\nدستور/سوال درباره این پیام:\n{prompt_inst}'

    target_key_id = f"group_{chat_id}" if is_group else user_id
    user_mode = safe_kv_get(f"USER_MODE_{target_key_id}") or "CHAT"

    if user_mode == "IMAGE_GEN":
        threading.Thread(target=worker_image_process, args=(chat_id, user_id, text, target_key_id, thread_id), daemon=True).start()
    else:
        threading.Thread(target=worker_ai_process, args=(chat_id, user_id, msg, text, target_key_id, is_group, target_reply_id, thread_id), daemon=True).start()

# ==========================================
# ۶. هندلر دکمه‌های شیشه‌ای (Callback Queries)
# ==========================================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(query):
    chat_id = query.message.chat.id
    user_id = str(query.from_user.id)
    data = query.data
    is_group = query.message.chat.type in ["group", "supergroup"]
    target_key_id = f"group_{chat_id}" if is_group else user_id

    if data.startswith("cancel_req_"):
        req_id = data.replace("cancel_req_", "")
        owner_id = req_id.split("_")[0]
        if user_id != owner_id:
            bot.answer_callback_query(query.id, "⛔ این درخواست متعلق به شما نیست!", show_alert=True)
            return

        bot.answer_callback_query(query.id, "✅ درخواست لغو شد.")
        safe_kv_put(f"CANCEL_{req_id}", "true", 2100)
        try:
            bot.edit_message_text("❌ درخواست توسط کاربر لغو شد.", chat_id=chat_id, message_id=query.message.message_id)
        except:
            pass
        return

    if is_group:
        settings_btns = ["mode_chat", "mode_image", "select_model_menu"]
        if data in settings_btns or data.startswith("set_model_") or data.startswith("set_img_model_"):
            if not is_group_admin(chat_id, user_id):
                bot.answer_callback_query(query.id, "⛔ تغییر تنظیمات ربات در گروه فقط توسط ادمین امکان‌پذیر است!", show_alert=True)
                return

        pv_only = ["main_menu", "check_sponsor", "history_menu", "new_chat"]
        if data in pv_only or data.startswith("switch_sess_") or data.startswith("admin_"):
            bot.answer_callback_query(query.id, "⚠️ این منو فقط در چت خصوصی (پیوی) ربات قابل استفاده است.", show_alert=True)
            return

    try:
        bot.answer_callback_query(query.id)
    except:
        pass

    if data in ["check_sponsor", "main_menu", "mode_chat", "mode_image", "select_model_menu", "history_menu", "new_chat"]:
        clear_user_state(user_id)

    if data in ["check_sponsor", "main_menu"]:
        if not is_group:
            send_main_menu(chat_id, user_id)

    elif data == "mode_chat":
        safe_kv_put(f"USER_MODE_{target_key_id}", "CHAT")
        bot.send_message(chat_id, "💬 حالت گفتگو متنی، تصویری، فایل و ساخت کد فعال شد.")

    elif data == "mode_image":
        safe_kv_put(f"USER_MODE_{target_key_id}", "IMAGE_GEN")
        if not is_group:
            send_image_model_selection_menu(chat_id, user_id)

    elif data == "select_model_menu":
        send_model_selection_menu(chat_id, target_key_id)

    elif data.startswith("set_model_"):
        idx = data.replace("set_model_", "")
        safe_kv_put(f"USER_MODEL_{target_key_id}", idx)
        active_sess = safe_kv_get(f"ACTIVE_SESSION_{user_id}")
        if active_sess:
            sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
            for s in sessions:
                if s.get("id") == active_sess:
                    s["modelIndex"] = idx
                    safe_kv_put(f"SESSIONS_{user_id}", sessions)
                    break
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        name = models[int(idx)].get("name") if idx.isdigit() and int(idx) < len(models) else "انتخاب شده"
        bot.send_message(chat_id, f"✅ مدل فعال چت روی **{name}** تنظیم شد.", parse_mode="Markdown")

    elif data.startswith("set_img_model_"):
        idx = data.replace("set_img_model_", "")
        safe_kv_put(f"USER_IMG_MODEL_{target_key_id}", idx)
        img_models = json.loads(safe_kv_get("IMAGE_MODELS") or "[]")
        name = img_models[int(idx)].get("name") if idx.isdigit() and int(idx) < len(img_models) else "انتخاب شده"
        bot.send_message(chat_id, f"🎨 مدل ساخت عکس روی **{name}** تنظیم شد.", parse_mode="Markdown")

    elif data == "history_menu" and not is_group:
        send_history_menu(chat_id, user_id)

    elif data == "new_chat" and not is_group:
        new_sess = f"sess_{int(time.time())}"
        safe_kv_put(f"ACTIVE_SESSION_{user_id}", new_sess)
        sessions = json.loads(safe_kv_get(f"SESSIONS_{user_id}") or "[]")
        sessions.insert(0, {"id": new_sess, "title": "گفتگوی جدید 💬", "date": time.strftime("%Y/%m/%d")})
        safe_kv_put(f"SESSIONS_{user_id}", sessions)
        bot.send_message(chat_id, "✨ چت جدید ایجاد شد! پیام خود را بفرستید.")

    elif data.startswith("switch_sess_") and not is_group:
        sess_id = data.replace("switch_sess_", "")
        safe_kv_put(f"ACTIVE_SESSION_{user_id}", sess_id)
        bot.send_message(chat_id, "🔄 با موفقیت به این گفتگو منتقل شدید.")

    # پنل ادمین
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
        bot.send_message(chat_id, "🌐 URL Base جدید (یا .):")

    elif step == "EDIT_MODEL_URL":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IDX_{user_id}") or "0")
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if text != "." and idx < len(models):
            models[idx]["baseUrl"] = text
            safe_kv_put("AI_MODELS", models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_MODEL_KEY")
        bot.send_message(chat_id, "🔑 API Key جدید (یا .):")

    elif step == "EDIT_MODEL_KEY":
        idx = int(safe_kv_get(f"ADMIN_EDIT_IDX_{user_id}") or "0")
        models = json.loads(safe_kv_get("AI_MODELS") or "[]")
        if text != "." and idx < len(models):
            models[idx]["apiKey"] = text
            safe_kv_put("AI_MODELS", models)
        safe_kv_put(f"ADMIN_STEP_{user_id}", "EDIT_MODEL_ID")
        bot.send_message(chat_id, "📌 Model Name جدید (یا .):")

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
    print("🤖 Neo-AI-Bot with Group & Private Code-to-File Started")
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
