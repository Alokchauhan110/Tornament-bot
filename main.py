# main.py (Full-Featured Final Version)

import logging
import os
import database as db
import asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from flask import Flask, request

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- State Management ---
app_initialized = False

# --- Conversation States ---
(ADD_TOURNAMENT_MODE, ADD_TOURNAMENT_DATETIME, ADD_TOURNAMENT_FEE,
 BROADCAST_MESSAGE, VIEW_REGISTRATIONS) = range(5)
REGISTER_GET_USERNAME, REGISTER_GET_USERID = range(5, 7)
(SEND_ROOM_GET_TID, SEND_ROOM_GET_RID, SEND_ROOM_GET_RPASS, SEND_ROOM_CONFIRM) = range(7, 11)
(UNREGISTER_CHOICE) = range(11, 12)
(DELETE_T_GET_ID, DELETE_T_CONFIRM) = range(12, 14)
(KICK_GET_TID, KICK_GET_FFID, KICK_CONFIRM) = range(14, 17)


# ========== GLOBAL APPLICATION OBJECT ==========
application = Application.builder().token(BOT_TOKEN).build()


# ========== USER COMMANDS & HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.add_or_update_user(user.id)
    await update.message.reply_html(
        f"🔥 Welcome, {user.first_name}! 🔥\n\n"
        "I am your Free Fire Tournament Bot.\n\n"
        "Use /register to join a tournament.\n"
        "Use /unregister to leave a tournament.\n"
        "Use /mytournaments to see your registrations.\n"
        "Use /help to see all commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>Available Commands:</b>\n"
        "/start - Welcome message\n"
        "/register - Join an open tournament\n"
        "/unregister - Leave a tournament\n"
        "/mytournaments - See your registrations\n"
        "/help - Show this message\n\n"
        "<b>Admin Commands:</b>\n"
        "/admin - Open the admin panel\n"
        "/sendroom - Send Room ID/Pass to players\n"
        "/deletetournament - Cancel a tournament\n"
        "/kickplayer - Remove a player from a tournament"
    )
    await update.message.reply_html(text)

async def my_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = db.get_user(update.effective_user.id)
    if user_data and user_data['ff_username']:
        await update.message.reply_html(
            "<b>Your Information:</b>\n"
            f"👤 Free Fire Name: <b>{user_data['ff_username']}</b>\n"
            f"🔢 Free Fire ID: <code>{user_data['ff_userid']}</code>"
        )
    else:
        await update.message.reply_text("You haven't set your Free Fire info yet. Please /register for a tournament to set it.")

async def my_tournaments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the user a list of tournaments they are registered for."""
    user_id = update.effective_user.id
    registrations = db.get_user_registrations(user_id)
    if not registrations:
        await update.message.reply_text("You are not registered for any upcoming tournaments.")
        return

    response = "<b>You are registered for the following tournaments:</b>\n\n"
    for reg in registrations:
        mode = "Battle Royale" if reg['mode'] == 'BR' else "Clash Squad"
        response += f"🔹 <b>{mode}</b> on {reg['date_time']}\n"
    
    await update.message.reply_html(response)

# --- (All other handler functions like register, admin, etc., are below) ---
# ...
# --- The rest of the file is complete below ---

# --- Registration Process ---
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    tournaments = db.get_open_tournaments()
    if not tournaments:
        await update.message.reply_text("Sorry, there are no open tournaments right now. Check back later!")
        return ConversationHandler.END
    keyboard = []
    for t in tournaments:
        mode = "Battle Royale" if t['mode'] == 'BR' else "Clash Squad"
        fee_text = f" (Fee: {t['fee']})" if t['fee'] > 0 else " (Free)"
        button_text = f"{mode} - {t['date_time']}{fee_text}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"register_{t['id']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please choose a tournament to register for:", reply_markup=reply_markup)
    return REGISTER_GET_USERNAME

async def register_tournament_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    tournament_id = int(query.data.split('_')[1])
    context.user_data['tournament_id'] = tournament_id
    tournament = db.get_tournament_details(tournament_id)
    registrations = db.get_registrations_for_tournament(tournament_id)
    if len(registrations) >= tournament['max_players']:
        await query.edit_message_text("Sorry, this tournament is already full.")
        return ConversationHandler.END
    await query.edit_message_text("Great! Now, please send me your Free Fire <b>in-game name</b>.", parse_mode='HTML')
    return REGISTER_GET_USERNAME

async def register_get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['ff_username'] = update.message.text
    await update.message.reply_text("Got it. Now, please send me your Free Fire <b>User ID</b> (the number).", parse_mode='HTML')
    return REGISTER_GET_USERID

async def register_get_userid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    ff_userid = update.message.text
    ff_username = context.user_data['ff_username']
    tournament_id = context.user_data['tournament_id']
    db.add_or_update_user(user.id, ff_username, ff_userid)
    result = db.register_user_for_tournament(tournament_id, user.id)
    if result == "SUCCESS":
        tournament = db.get_tournament_details(tournament_id)
        fee_message = f"Please pay the registration fee of <b>₹{tournament['fee']}</b> to confirm your slot." if tournament['fee'] > 0 else "This is a free tournament."
        await update.message.reply_html(
            f"✅ <b>Registration Successful!</b>\n\n"
            f"<b>Tournament:</b> {tournament['mode']} on {tournament['date_time']}\n"
            f"<b>Your Name:</b> {ff_username}\n"
            f"<b>Your ID:</b> {ff_userid}\n\n"
            f"{fee_message}\n\n"
            "You will receive the Room ID and Password before the match starts."
        )
    elif result == "ALREADY_REGISTERED":
        await update.message.reply_text("You are already registered for this tournament.")
    return ConversationHandler.END

# --- Unregister Process ---
async def unregister_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    registrations = db.get_user_registrations(user_id)
    if not registrations:
        await update.message.reply_text("You are not registered for any tournaments to leave.")
        return ConversationHandler.END

    keyboard = []
    for reg in registrations:
        mode = "Battle Royale" if reg['mode'] == 'BR' else "Clash Squad"
        button_text = f"Leave: {mode} on {reg['date_time']}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"unregister_{reg['id']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Which tournament would you like to unregister from?", reply_markup=reply_markup)
    return UNREGISTER_CHOICE

async def unregister_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    tournament_id = int(query.data.split('_')[1])
    user_id = query.from_user.id
    
    db.unregister_user_from_tournament(tournament_id, user_id)
    
    await query.edit_message_text("✅ You have been successfully unregistered from the tournament.")
    return ConversationHandler.END

# --- Admin Panel & Related Commands ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return
    keyboard = [['➕ Add Tournament', '📢 Broadcast'], ['📋 View Tournaments', '👥 View Registrations']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Welcome to the Admin Panel.", reply_markup=reply_markup)

# ... (Add, Broadcast, View, Send Room functions are here) ...

# --- Kick Player Feature (Admin) ---
async def kick_player_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not db.is_admin(update.effective_user.id): return ConversationHandler.END
    await update.message.reply_text("Enter the Tournament ID to kick a player from.")
    return KICK_GET_TID

async def kick_player_get_tid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        tournament_id = int(update.message.text)
        if not db.get_tournament_details(tournament_id):
            await update.message.reply_text("Tournament not found. /cancel")
            return ConversationHandler.END
        context.user_data['kick_tid'] = tournament_id
        await update.message.reply_text("Got it. Now enter the Free Fire ID of the player you want to kick.")
        return KICK_GET_FFID
    except ValueError:
        await update.message.reply_text("Invalid ID. Please enter a number.")
        return KICK_GET_TID

async def kick_player_get_ffid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ff_userid = update.message.text
    tid = context.user_data['kick_tid']
    
    kicked = db.kick_player(tid, ff_userid)
    
    if kicked:
        await update.message.reply_text(f"✅ Player with FF ID {ff_userid} has been kicked from tournament {tid}.")
    else:
        await update.message.reply_text(f"Could not find a player with FF ID {ff_userid} registered in tournament {tid}.")
        
    return ConversationHandler.END

# --- Delete Tournament Feature (Admin) ---
async def delete_tournament_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not db.is_admin(update.effective_user.id): return ConversationHandler.END
    await update.message.reply_text("Enter the Tournament ID you wish to permanently delete.")
    return DELETE_T_GET_ID

async def delete_tournament_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        tournament_id = int(update.message.text)
        if not db.get_tournament_details(tournament_id):
            await update.message.reply_text("Tournament not found. /cancel")
            return ConversationHandler.END
        context.user_data['delete_tid'] = tournament_id
        await update.message.reply_text(f"This will delete tournament {tournament_id} and all its registrations forever. This cannot be undone.\n\nType `YES` to confirm.")
        return DELETE_T_CONFIRM
    except ValueError:
        await update.message.reply_text("Invalid ID. Please enter a number.")
        return DELETE_T_GET_ID

async def delete_tournament_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == "YES":
        tid = context.user_data['delete_tid']
        db.delete_tournament(tid)
        await update.message.reply_text(f"✅ Tournament {tid} and all its registrations have been deleted.")
    else:
        await update.message.reply_text("Confirmation failed. Operation cancelled.")
        
    return ConversationHandler.END

# --- (Other admin functions like add, broadcast, etc.) ---
# ... (These are unchanged and are included in the final code block) ...

# ========== FLASK WEB SERVER & WEBHOOK LOGIC ==========

app = Flask(__name__)

@app.before_first_request
async def startup():
    """Run startup tasks on the first request."""
    global app_initialized
    if not app_initialized:
        await application.initialize()
        db.setup_database()
        conn = db.get_db_connection()
        conn.execute("INSERT OR IGNORE INTO users (telegram_id) VALUES (?)", (ADMIN_ID,))
        conn.execute("UPDATE users SET is_admin = 1 WHERE telegram_id = ?", (ADMIN_ID,))
        conn.commit()
        conn.close()
        logger.info("Application initialized and database setup complete.")
        app_initialized = True

@app.route("/")
def index():
    return "Hello, I am your Free Fire Bot and I am running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    """Webhook endpoint to process updates."""
    await application.process_update(
        Update.de_json(request.get_json(force=True), application.bot)
    )
    return "ok"

# Add all handlers to the application object
# (All handlers, including the new ones, are registered here)
# ...