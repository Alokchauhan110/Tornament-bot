# main.py (Final complete version with all features and fixes for Render/Uvicorn)

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

# --- Conversation States ---
(ADD_TOURNAMENT_MODE, ADD_TOURNAMENT_DATETIME, ADD_TOURNAMENT_FEE,
 BROADCAST_MESSAGE, VIEW_REGISTRATIONS) = range(5)
REGISTER_GET_USERNAME, REGISTER_GET_USERID = range(5, 7)
(SEND_ROOM_GET_TID, SEND_ROOM_GET_RID, SEND_ROOM_GET_RPASS, SEND_ROOM_CONFIRM) = range(7, 11)


# ========== USER COMMANDS & HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.add_or_update_user(user.id)
    await update.message.reply_html(
        f"🔥 Welcome, {user.first_name}! 🔥\n\n"
        "I am your Free Fire Tournament Bot.\n\n"
        "Use /register to join a tournament.\n"
        "Use /myinfo to see your details.\n"
        "Use /help to see all commands."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>Available Commands:</b>\n"
        "/start - Welcome message\n"
        "/register - Join an open tournament\n"
        "/myinfo - View your registered FF username and ID\n"
        "/help - Show this message\n\n"
        "<b>Admin Commands:</b>\n"
        "/admin - Open the admin panel\n"
        "/sendroom - Send Room ID/Pass to players"
    )
    await update.message.reply_html(text)

async def my_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = db.get_user(update.effective_user.id)
    if user_data and user_data['ff_username']:
        await update.message.reply_html(
            "<b>Your Information:</b>\n"
            f"👤 Free Fire Name: {user_data['ff_username']}\n"
            f"🔢 Free Fire ID: {user_data['ff_userid']}"
        )
    else:
        await update.message.reply_text("You haven't set your Free Fire info yet. Please /register for a tournament to set it.")

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

# --- Admin Panel & Related Commands ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    keyboard = [['➕ Add Tournament', '📢 Broadcast'], ['📋 View Tournaments', '👥 View Registrations']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Welcome to the Admin Panel. Choose an option:\n\nUse /sendroom to send match details.", reply_markup=reply_markup)

async def add_tournament_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not db.is_admin(update.effective_user.id): return ConversationHandler.END
    keyboard = [['Battle Royale (50)', 'Clash Squad (8)']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Select tournament mode:", reply_markup=reply_markup)
    return ADD_TOURNAMENT_MODE

async def add_tournament_get_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    mode_text = update.message.text
    if 'Battle Royale' in mode_text:
        context.user_data['mode'] = 'BR'
        context.user_data['max_players'] = 50
    elif 'Clash Squad' in mode_text:
        context.user_data['mode'] = 'CS'
        context.user_data['max_players'] = 8
    else:
        await update.message.reply_text("Invalid mode. Please choose from the keyboard.")
        return ADD_TOURNAMENT_MODE
    
    await update.message.reply_text("Enter the date and time (e.g., 'July 10, 9:00 PM'):")
    return ADD_TOURNAMENT_DATETIME

async def add_tournament_get_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['date_time'] = update.message.text
    await update.message.reply_text("Enter the registration fee (enter 0 for free):")
    return ADD_TOURNAMENT_FEE

async def add_tournament_get_fee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        fee = int(update.message.text)
        db.add_tournament(
            mode=context.user_data['mode'],
            date_time=context.user_data['date_time'],
            fee=fee,
            max_players=context.user_data['max_players']
        )
        await update.message.reply_text("✅ Tournament successfully created!")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Invalid fee. Please enter a number.")
        return ADD_TOURNAMENT_FEE

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not db.is_admin(update.effective_user.id): return ConversationHandler.END
    await update.message.reply_text("Please send the message you want to broadcast to all users.")
    return BROADCAST_MESSAGE

async def broadcast_get_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message_to_send = update.message.text
    user_ids = db.get_all_user_ids()
    sent_count = 0
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=f"📢 **Admin Broadcast**\n\n{message_to_send}", parse_mode='Markdown')
            sent_count += 1
        except Exception as e:
            logger.error(f"Could not send broadcast to {user_id}: {e}")
    
    await update.message.reply_text(f"Broadcast sent to {sent_count}/{len(user_ids)} users.")
    return ConversationHandler.END

async def view_tournaments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not db.is_admin(update.effective_user.id): return
    tournaments = db.get_open_tournaments()
    if not tournaments:
        await update.message.reply_text("No open tournaments found.")
        return
    response = "<b>Open Tournaments:</b>\n\n"
    for t in tournaments:
        mode = "Battle Royale" if t['mode'] == 'BR' else "Clash Squad"
        regs = len(db.get_registrations_for_tournament(t['id']))
        response += f"<b>ID: {t['id']}</b> | {mode}\n"
        response += f"  - Date: {t['date_time']}\n"
        response += f"  - Fee: {t['fee']}\n"
        response += f"  - Registered: {regs}/{t['max_players']}\n\n"
    await update.message.reply_html(response)

async def view_registrations_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not db.is_admin(update.effective_user.id): return ConversationHandler.END
    await update.message.reply_text("Please enter the Tournament ID to view its registrations.")
    return VIEW_REGISTRATIONS

async def view_registrations_get_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        tournament_id = int(update.message.text)
        registrations = db.get_registrations_for_tournament(tournament_id)
        tournament = db.get_tournament_details(tournament_id)
        if not tournament:
            await update.message.reply_text("Tournament with that ID not found.")
            return ConversationHandler.END
        if not registrations:
            await update.message.reply_text(f"No one has registered for Tournament ID {tournament_id} yet.")
            return ConversationHandler.END
        response = f"<b>Registrations for Tournament ID {tournament_id}:</b>\n"
        response += f"({tournament['mode']} on {tournament['date_time']})\n\n"
        for i, reg in enumerate(registrations, 1):
            response += f"{i}. {reg['ff_username']} (ID: {reg['ff_userid']})\n"
        await update.message.reply_html(response)
    except ValueError:
        await update.message.reply_text("Invalid ID. Please enter a number.")
    return ConversationHandler.END

# --- Send Room Details Feature ---
async def send_room_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("This is an admin-only command.")
        return ConversationHandler.END
    await update.message.reply_text("Okay, let's send some room details. What is the Tournament ID?")
    return SEND_ROOM_GET_TID

async def send_room_get_tid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        tournament_id = int(update.message.text)
        tournament = db.get_tournament_details(tournament_id)
        if not tournament:
            await update.message.reply_text("Sorry, I can't find a tournament with that ID. Please try again or /cancel.")
            return SEND_ROOM_GET_TID
        context.user_data['send_room_tid'] = tournament_id
        await update.message.reply_text("Great. Now, what is the Room ID?")
        return SEND_ROOM_GET_RID
    except ValueError:
        await update.message.reply_text("That's not a valid number. Please enter the Tournament ID.")
        return SEND_ROOM_GET_TID

async def send_room_get_rid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['send_room_rid'] = update.message.text
    await update.message.reply_text("Got it. And the Room Password?")
    return SEND_ROOM_GET_RPASS

async def send_room_get_rpass(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['send_room_rpass'] = update.message.text
    tid = context.user_data['send_room_tid']
    rid = context.user_data['send_room_rid']
    rpass = context.user_data['send_room_rpass']
    registrations = db.get_registrations_for_tournament(tid)
    player_count = len(registrations)
    if player_count == 0:
        await update.message.reply_text("There are no players registered for this tournament. Nothing to send. /cancel")
        return ConversationHandler.END
    confirmation_text = (
        f"🚨 **Please Confirm** 🚨\n\n"
        f"You are about to send the following details:\n"
        f"  - **Tournament ID:** {tid}\n"
        f"  - **Room ID:** `{rid}`\n"
        f"  - **Password:** `{rpass}`\n\n"
        f"This will be sent to **{player_count}** registered players.\n\n"
        f"Are you sure you want to proceed?"
    )
    keyboard = [[InlineKeyboardButton("✅ Yes, Send It!", callback_data="send_room_confirm_yes"),
                 InlineKeyboardButton("❌ No, Cancel", callback_data="send_room_confirm_no")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(confirmation_text, reply_markup=reply_markup)
    return SEND_ROOM_CONFIRM

async def send_room_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "send_room_confirm_no":
        await query.edit_message_text("Operation cancelled. Nothing was sent.")
        return ConversationHandler.END
    await query.edit_message_text("Sending messages... Please wait.")
    tid = context.user_data['send_room_tid']
    rid = context.user_data['send_room_rid']
    rpass = context.user_data['send_room_rpass']
    registrations = db.get_registrations_for_tournament(tid)
    tournament = db.get_tournament_details(tid)
    mode = "Battle Royale" if tournament['mode'] == 'BR' else "Clash Squad"
    message_to_send = (
        f"🔥 **Tournament Room Details!** 🔥\n\n"
        f"Here are the details for your upcoming **{mode}** tournament on **{tournament['date_time']}**.\n\n"
        f"🔑 **Room ID:** `{rid}`\n"
        f"🔒 **Password:** `{rpass}`\n\n"
        f"Please join the room quickly. Good luck!"
    )
    sent_count = 0
    failed_count = 0
    for reg in registrations:
        try:
            await context.bot.send_message(chat_id=reg['telegram_id'], text=message_to_send, parse_mode='Markdown')
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to send room details to {reg['telegram_id']}: {e}")
            failed_count += 1
    await query.edit_message_text(f"✅ Done!\n\nRoom details sent to {sent_count} players.\nFailed to send to {failed_count} players (they may have blocked the bot).")
    return ConversationHandler.END

# --- General Utility ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


# ========== WEB SERVER & BOT SETUP ==========

application = Application.builder().token(BOT_TOKEN).build()
app = Flask(__name__)

@app.route("/")
def index():
    return "Hello, I am your Free Fire Bot and I am running!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update_json = request.get_json(force=True)
    update = Update.de_json(update_json, application.bot)
    await application.process_update(update)
    return "ok"

@app.before_serving
async def setup_bot():
    """Initializes the bot and sets up all handlers. Runs once before the server starts."""
    await application.initialize()
    db.setup_database()

    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO users (telegram_id) VALUES (?)", (ADMIN_ID,))
    conn.execute("UPDATE users SET is_admin = 1 WHERE telegram_id = ?", (ADMIN_ID,))
    conn.commit()
    conn.close()
    logger.info(f"Admin rights granted to user ID: {ADMIN_ID}")

    # Register all handlers
    register_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register_start)],
        states={
            REGISTER_GET_USERNAME: [
                CallbackQueryHandler(register_tournament_choice, pattern='^register_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_get_username),
            ],
            REGISTER_GET_USERID: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_get_userid)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    admin_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^➕ Add Tournament$'), add_tournament_start),
            MessageHandler(filters.Regex('^📢 Broadcast$'), broadcast_start),
            MessageHandler(filters.Regex('^👥 View Registrations$'), view_registrations_start)
        ],
        states={
            ADD_TOURNAMENT_MODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tournament_get_mode)],
            ADD_TOURNAMENT_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tournament_get_datetime)],
            ADD_TOURNAMENT_FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tournament_get_fee)],
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_get_message)],
            VIEW_REGISTRATIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_registrations_get_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    send_room_handler = ConversationHandler(
        entry_points=[CommandHandler("sendroom", send_room_start)],
        states={
            SEND_ROOM_GET_TID: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_room_get_tid)],
            SEND_ROOM_GET_RID: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_room_get_rid)],
            SEND_ROOM_GET_RPASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_room_get_rpass)],
            SEND_ROOM_CONFIRM: [CallbackQueryHandler(send_room_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myinfo", my_info))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.Regex('^📋 View Tournaments$'), view_tournaments))
    application.add_handler(register_conv_handler)
    application.add_handler(admin_conv_handler)
    application.add_handler(send_room_handler)
    
    logger.info("Bot setup complete. Handlers are registered and application is initialized.")

# The if __name__ == "__main__" block is intentionally removed as it's handled by @app.before_serving