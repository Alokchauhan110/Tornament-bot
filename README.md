# 🔥 Free Fire Tournament Bot for Telegram 🤖

A powerful and easy-to-use Telegram bot to manage your Free Fire tournaments seamlessly. Handle registrations, create new events, broadcast messages, and more, all from within Telegram.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Telegram%20Bot%20API-v6.x-blue?style=for-the-badge&logo=telegram" alt="Telegram Bot API">
  <img src="https://img.shields.io/badge/Database-SQLite-blue?style=for-the-badge&logo=sqlite" alt="SQLite">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT">
</p>

---

## 🌟 Key Features

### 👑 Admin Panel
-   **➕ Add Tournaments:** Easily create new tournaments for both **Battle Royale (50 players)** and **Clash Squad (8 players)** modes.
-   **💰 Set Registration Fee:** Specify an entry fee for a tournament or set it to `0` for a free event.
-   **🗓️ Set Date & Time:** Define the schedule for each tournament.
-   **📢 Broadcast System:** Send custom messages to all users who have interacted with the bot. Perfect for announcements or updates.
-   **📋 View Tournaments:** Get a quick overview of all upcoming tournaments, including registration counts.
-   **👥 View Registered Players:** List all registered players for a specific tournament with their Free Fire name and ID.
-   **🔐 Secure:** The admin panel is protected and only accessible to the authorized admin user.

### 🎮 User Panel
-   **📝 Easy Registration:** Users can register for any open tournament with a simple, guided process.
-   **ℹ️ Store User Info:** The bot saves the user's Free Fire Username and User ID for future registrations.
-   **🔔 Receive Notifications:** Users get confirmation of their registration and receive broadcasts from the admin.
-   **🙋‍♀️ User-Friendly Interface:** Clean commands and interactive buttons make the bot easy to navigate.

---

## 🛠️ Technology Stack

-   **Backend:** Python 3
-   **Telegram Bot Framework:** `python-telegram-bot`
-   **Database:** SQLite 3 (for lightweight, file-based storage)

---

## 🚀 Getting Started

Follow these steps to get your own instance of the Free Fire Tournament Bot up and running.

### Prerequisites

-   Python 3.8 or higher.
-   A Telegram account.

### Installation & Setup

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-username/freefire-tournament-bot.git
    cd freefire-tournament-bot
    ```

2.  **Install Dependencies**
    ```bash
    pip install python-telegram-bot --upgrade
    ```

3.  **Create a Telegram Bot**
    -   Open Telegram and talk to the **@BotFather**.
    -   Send the `/newbot` command and follow the instructions.
    -   BotFather will give you a **TOKEN**. Copy it.

4.  **Get Your Admin Telegram ID**
    -   Talk to the **@userinfobot** on Telegram.
    -   It will reply with your user information, including your `Id`. This will be your `ADMIN_ID`.

5.  **Configure the Bot**
    -   Open the `main.py` file.
    -   Find the following lines and replace the placeholder values with your own:
    ```python
    # --- Configuration ---
    BOT_TOKEN = "YOUR_BOT_TOKEN"  # <-- PASTE YOUR BOT TOKEN HERE
    ADMIN_ID = 123456789          # <-- PASTE YOUR TELEGRAM ID HERE
    ```

6.  **Run the Bot!**
    ```bash
    python main.py
    ```
    You should see a confirmation message in your terminal:
    ```
    Database setup complete.
    Admin rights granted to user ID: 123456789
    Bot is running...
    ```

Your bot is now live on Telegram!

---

## 🤖 How to Use the Bot

### As a Regular User
-   `/start` - Initializes the bot and shows a welcome message.
-   `/register` - Starts the process to register for an open tournament.
-   `/myinfo` - Shows your saved Free Fire name and ID.
-   `/help` - Displays a list of available commands.
-   `/cancel` - Cancels any ongoing operation (like registration).

### As an Admin
-   `/admin` - Opens the main admin control panel with custom keyboard buttons.
    -   **➕ Add Tournament:** A step-by-step conversation to create a new tournament.
    -   **📢 Broadcast:** Prompts you for a message to send to all bot users.
    -   **📋 View Tournaments:** Displays a list of all open tournaments and their status.
    -   **👥 View Registrations:** Asks for a Tournament ID and then shows the list of registered players.

---

## 📂 Project Structure