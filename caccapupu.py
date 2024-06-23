import logging
import sqlite3
from datetime import datetime, timedelta, timezone
import pytz
from telegram import Update
from telegram.ext import ApplicationBuilder, Updater, CommandHandler, MessageHandler, filters, CallbackContext
import dotenv

token = dotenv.dotenv_values()["BOT_TOKEN"]
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

conn = sqlite3.connect('emoji_count.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS emoji_count
             (group_id INTEGER, user_id INTEGER, date TEXT)''')
conn.commit()

# Emoji da contare
TARGET_EMOJI = '💩'  

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Bot avviato! Conta cacche attivata.")

async def get_username(context: CallbackContext, group_id: int, user_id: int) -> str:
    try:
        member = await context.bot.get_chat_member(group_id, user_id)
        username = member.user.username or f"{member.user.first_name} {member.user.last_name or ''}".strip()
        return username
    except Exception as e:
        logger.error(f"Errore nel recuperare l'username per user_id {user_id} in group_id {group_id}: {e}")
        return "Unknown"

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Questo bot conta una particolare emoji nei gruppi.\n"
                              "/start - Avvia il bot\n"
                              "/lastmonth - Mostra il conteggio delle emoji dell'ultimo mese\n"
                              "/all - Mostra il conteggio totale delle emoji\n"
                              "/help - Mostra questo \n"
                              "Se vuoi offrirmi un caffé ecco il link https://www.buymeacoffee.com/montenigri")

async def count_emoji(update: Update, context: CallbackContext) -> None:
    message = update.message.text
    if TARGET_EMOJI in message:
        group_id = update.message.chat_id
        user_id = update.message.from_user.id
        date = datetime.now(timezone.utc).isoformat()

        #print(f"User {user_id} used the emoji {TARGET_EMOJI} in group {group_id} at {date}")
        
        with conn:
            c.execute("INSERT INTO emoji_count (group_id, user_id, date) VALUES (?, ?, ?)", (group_id, user_id, date))

async def last_month(update: Update, context: CallbackContext) -> None:
    group_id = update.message.chat_id
    one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    with conn:
        c.execute("SELECT user_id, COUNT(*) FROM emoji_count WHERE group_id = ? AND date >= ? GROUP BY user_id ORDER BY COUNT(*) DESC", 
                  (group_id, one_month_ago.isoformat()))
        results = c.fetchall()
    
    response = "Conteggio delle cacche nell'ultimo mese:\n"
    for user_id, count in results:
        username = await get_username(context, group_id, user_id)
        response += f"{username}: {count}\n"
    
    await update.message.reply_text(response)

async def all_time(update: Update, context: CallbackContext) -> None:
    group_id = update.message.chat_id

    with conn:
        c.execute('''SELECT user_id, COUNT(*), MIN(date) 
                     FROM emoji_count 
                     WHERE group_id = ? 
                     GROUP BY user_id 
                     ORDER BY COUNT(*) DESC''', 
                  (group_id,))
        results = c.fetchall()
        
        c.execute('''SELECT MIN(date) 
                     FROM emoji_count 
                     WHERE group_id = ?''', 
                  (group_id,))
        first_date_result = c.fetchone()
        first_date = first_date_result[0] if first_date_result else None
        first_date_formatted = datetime.fromisoformat(first_date).strftime('%d/%m/%Y') if first_date else "N/A"
    
    response = f"Conteggio totale delle emoji (prima cacca registrata il {first_date_formatted}):\n"
    for user_id, count, _ in results:
        username = await get_username(context, group_id, user_id)
        response += f"{username}: {count}\n"
    
    await update.message.reply_text(response)


def format_time_ago(time_diff: datetime) -> str:
    
    days = time_diff.days
    hours = (time_diff.seconds // 3600) % 24
    minutes = (time_diff.seconds // 60) % 60

    if days > 0:
        if days == 1:
            days_str = f"{days} giorno"
        else:
            days_str = f"{days} giorni"
        if hours == 1:
            hours_str = f"{hours} ora"
        else:
            hours_str = f"{hours} ore"
        return f"{days_str} e {hours_str} fa"
    elif hours > 0:
        if hours == 1:
            hours_str = f"{hours} ora"
        else:
            hours_str = f"{hours} ore"
        if minutes == 1:
            minutes_str = f"{minutes} minuto"
        else:
            minutes_str = f"{minutes} minuti"
        return f"{hours_str} e {minutes_str} fa"
    else:
        if minutes == 1:
            return f"{minutes} minuto fa"
        else:
            return f"{minutes} minuti fa"

async def last_time(update: Update, context: CallbackContext) -> None:
    group_id = update.message.chat_id
    
    with conn:
        c.execute('''SELECT user_id, MAX(date) 
                     FROM emoji_count 
                     WHERE group_id = ? 
                     GROUP BY user_id 
                     ORDER BY MAX(date) DESC''', 
                  (group_id,))
        results = c.fetchall()
    
    response = "Ultima volta che ogni utente ha inviato l'emoji:\n"
    for user_id, last_date in results:
        username = await get_username(context, group_id, user_id)
        last_date_dt = datetime.fromisoformat(last_date)
        if not last_date_dt.tzinfo:
            last_date_dt = pytz.utc.localize(last_date_dt)
        last_date_formatted = last_date_dt.strftime('%d-%m %H:%M')
        time_diff = datetime.now(timezone.utc) - last_date_dt
        time_ago = format_time_ago(time_diff)
            
        response += f"{username}: {last_date_formatted} ({time_ago})\n"
    
    await update.message.reply_text(response)

def main() -> None:
    
    app = ApplicationBuilder().token(token).build()


    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lastmonth", last_month))
    app.add_handler(CommandHandler("all", all_time))
    app.add_handler(CommandHandler("lasttime", last_time))
    app.add_handler(MessageHandler(filters.TEXT, count_emoji))

    app.run_polling()


if __name__ == '__main__':
    main()

#processo numero 2836688