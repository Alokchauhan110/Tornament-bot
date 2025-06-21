# main.py
import logging
import database as db
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

# --- Configuration ---
BOT_TOKEN = "YOUR_BOT_TOKEN"  # <-- IMPORTANT: PASTE YOUR BOT TOKEN HERE
ADMIN_ID = 123456789          # <-- IMPORTANT: PASTE YOUR TELEGRAM ID HERE

# --- Logging Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Conversation States ---
# Admin states
(ADD_TOURNAMENT_MODE, ADD_TOURNAMENT_DATETIME, ADD_TOURNAMENT_FEE,
 BROADCAST_MESSAGE, VIEW_REGISTRATIONS) = range(5)
# User states
REGISTER_GET_USERNAME, REGISTER_GET_USERID = range(5, 7)


# ========== USER COMMANDS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.add_or_update_user(user.id) # Add user to DB if not exists
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
        "/admin - Open the admin panel"
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


# ========== REGISTRATION PROCESS (User Conversation) ==========

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
    return REGISTER_GET_USERNAME # Initial state, but we wait for callback

async def register_tournament_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    tournament_id = int(query.data.split('_')[1])
    context.user_data['tournament_id'] = tournament_id

    # Check if tournament is full
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
    
    # Save user details
    db.add_or_update_user(user.id, ff_username, ff_userid)
    
    # Register for tournament
    result = db.register_user_for_tournament(tournament_id, user.id)

    if result == "SUCCESS":
        tournament = db.get_tournament_details(tournament_id)
        fee_message = f"Please pay the registration fee of <b>₹{tournament['fee']}</b> to confirm your slot. Contact the admin for payment details." if tournament['fee'] > 0 else "This is a free tournament."
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


# ========== ADMIN COMMANDS ==========

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not db.is_admin(update.effective_user.id):
        await update.message.reply_text("You are not authorized to use this command.")
        return

    keyboard = [
        ['➕ Add Tournament', '📢 Broadcast'],
        ['📋 View Tournaments', '👥 View Registrations'],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Welcome to the Admin Panel. Choose an option:", reply_markup=reply_markup)

# --- Add Tournament (Admin Conversation) ---
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
    
    await update.message.reply_text("Enter the date and time (e.g., 'May 25, 8:00 PM'):")
    return ADD_TOURNAMENT_DATETIME

async def add_tournament_get_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['date_time'] = update.message.text
    await update.message.reply_text("Enter the registration fee (enter 0 for free):")
    return ADD_TOURNAMENT_FEE

async def add_tournament_get_fee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        fee = int(update.message.text)
        # Add to database
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

# --- Broadcast (Admin Conversation) ---
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

# --- View Tournaments & Registrations ---
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


# ========== UTILITY & CANCEL ==========

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


def main() -> None:
    """Run the bot."""
    # First, set up the database
    db.setup_database()

    # Make the default user an admin
    conn = db.get_db_connection()
    conn.execute("INSERT OR IGNORE INTO users (telegram_id) VALUES (?)", (ADMIN_ID,))
    conn.execute("UPDATE users SET is_admin = 1 WHERE telegram_id = ?", (ADMIN_ID,))
    conn.commit()
    conn.close()
    print(f"Admin rights granted to user ID: {ADMIN_ID}")

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for user registration
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

    # Conversation handler for admin actions
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

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myinfo", my_info))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Admin simple commands
    application.add_handler(MessageHandler(filters.Regex('^📋 View Tournaments$'), view_tournaments))
    
    # Add conversation handlers
    application.add_handler(register_conv_handler)
    application.add_handler(admin_conv_handler)

    # Run the bot until the user presses Ctrl-C
    print("Bot is running...")
    application.run_polling()


if __name__ == "__main__":
    main()