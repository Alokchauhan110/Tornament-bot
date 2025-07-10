# set_webhook.py
import asyncio
from telegram import Bot

## ------------------------------------------------------------------
## IMPORTANT: PASTE YOUR CREDENTIALS AND RENDER URL HERE
## ------------------------------------------------------------------

# 1. Paste your bot's token from BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE" 

# 2. Paste the URL of your deployed Render service.
# It will look like: https://your-service-name.onrender.com
RENDER_WEBHOOK_URL = "YOUR_RENDER_URL_HERE" 

## ------------------------------------------------------------------

async def main():
    """Sets the bot's webhook to the Render URL."""
    if "YOUR_BOT_TOKEN_HERE" in BOT_TOKEN or "YOUR_RENDER_URL_HERE" in RENDER_WEBHOOK_URL:
        print("ERROR: Please replace the placeholder values in this script before running.")
        return

    bot = Bot(token=BOT_TOKEN)
    webhook_url_with_token = f"{RENDER_WEBHOOK_URL}/{BOT_TOKEN}"
    
    print(f"Setting webhook to: {webhook_url_with_token}")
    
    # Set the webhook
    success = await bot.set_webhook(
        url=webhook_url_with_token,
        allowed_updates=["message", "callback_query"]
    )
    
    if success:
        print("\n✅ Webhook was set successfully!")
        info = await bot.get_webhook_info()
        print(f"\nCurrent webhook info: {info}")
    else:
        print("\n❌ Failed to set webhook.")

if __name__ == "__main__":
    # You might need to install telegram bot library locally first:
    # pip install python-telegram-bot
    asyncio.run(main())