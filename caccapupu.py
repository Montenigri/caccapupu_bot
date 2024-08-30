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

    
async def current_month(update: Update, context: CallbackContext) -> None:
    group_id = update.message.chat_id
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    with conn:
        c.execute('''SELECT user_id, COUNT(*) 
                     FROM emoji_count 
                     WHERE group_id = ? AND date >= ? 
                     GROUP BY user_id 
                     ORDER BY COUNT(*) DESC''', 
                  (group_id, start_of_month.isoformat()))
        results = c.fetchall()
    
    response = "Conteggio delle emoji nel mese corrente:\n"
    for user_id, count in results:
        username = await get_username(context, group_id, user_id)
        response += f"{username}: {count}\n"
    
    await update.message.reply_text(response)




async def personal_stats(update: Update, context: CallbackContext) -> None:
    group_id = update.message.chat_id
    user_id = update.message.from_user.id
    
    with conn:
        # Recupera tutte le date di invio delle emoji per l'utente
        c.execute('''SELECT date 
                     FROM emoji_count 
                     WHERE group_id = ? AND user_id = ? 
                     ORDER BY date ASC''', 
                  (group_id, user_id))
        dates = c.fetchall()
    
    # Se l'utente non ha inviato nessuna emoji
    if not dates:
        update.message.reply_text("Non hai ancora inviato alcuna emoji in questo gruppo.")
        return
    
    # Conversione delle date in datetime
    date_times = [datetime.fromisoformat(date[0]) for date in dates]
    total_emojis = len(date_times)
    
    # Calcolo del tempo totale in giorni
    total_days = (datetime.utcnow() - date_times[0]).days + 1  # +1 per includere il giorno corrente
    frequency_per_day = total_emojis / total_days

    # Calcolo della distanza media tra le emoji
    time_diffs = [(date_times[i+1] - date_times[i]).total_seconds() for i in range(len(date_times) - 1)]
    if time_diffs:
        avg_time_diff_seconds = sum(time_diffs) / len(time_diffs)
        avg_time_diff_hours = avg_time_diff_seconds / 3600
    else:
        avg_time_diff_hours = 0
    
    # Calcolo della distanza massima e minima tra emoji
    if time_diffs:
        max_time_diff_seconds = max(time_diffs)
        min_time_diff_seconds = min(time_diffs)
        max_time_diff_hours = max_time_diff_seconds / 3600
        min_time_diff_minutes = min_time_diff_seconds / 60
    else:
        max_time_diff_hours = 0
        min_time_diff_minutes = 0

    # Calcolo del giorno della settimana e dell'ora più frequenti
    weekdays = [dt.weekday() for dt in date_times]  # 0 = Lunedì, ..., 6 = Domenica
    hours = [dt.hour for dt in date_times]
    
    most_common_weekday = max(set(weekdays), key=weekdays.count)
    most_common_hour = max(set(hours), key=hours.count)
    
    weekday_names = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    most_common_weekday_name = weekday_names[most_common_weekday]
    
    # Informazioni sull'ultima emoji inviata
    last_emoji_date = date_times[-1]

    # Informazioni sulla prima e ultima emoji del giorno
    first_emoji_of_day = min(date_times).strftime('%H:%M')
    last_emoji_of_day = max(date_times).strftime('%H:%M')

    # Confronto weekend vs giorni feriali
    weekdays_count = sum(1 for wd in weekdays if wd < 5)  # Lunedì-Venerdì
    weekends_count = sum(1 for wd in weekdays if wd >= 5)  # Sabato-Domenica
    
    # Formattazione delle informazioni
    response = (
        f"Statistiche personali per {update.message.from_user.username}:\n\n"
        f"Totale emoji inviate: {total_emojis}\n"
        f"Frequenza di invio: {frequency_per_day:.2f} emoji al giorno\n"
        f"Distanza media tra le emoji: {avg_time_diff_hours:.2f} ore\n"
        f"Distanza massima tra le emoji: {max_time_diff_hours:.2f} ore\n"
        f"Distanza minima tra le emoji: {min_time_diff_minutes:.2f} minuti\n"
        f"Ultima emoji inviata: {last_emoji_date.strftime('%d-%m-%Y %H:%M')}\n"
        f"Tempo trascorso dall'ultima emoji: {format_time_ago(last_emoji_date)}\n\n"
        f"Orario più frequente di invio: {most_common_hour}:00\n"
        f"Giorno più attivo della settimana: {most_common_weekday_name}\n\n"
        f"Prima emoji del giorno inviata alle: {first_emoji_of_day}\n"
        f"Ultima emoji del giorno inviata alle: {last_emoji_of_day}\n\n"
        f"Emoji inviate nei giorni feriali: {weekdays_count}\n"
        f"Emoji inviate nei weekend: {weekends_count}\n"
        f"Percentuale di emoji inviate nei weekend: {weekends_count / total_emojis * 100:.2f}%"
        f"Percentuale di emoji inviate nei giorni feriali: {weekdays_count / total_emojis * 100:.2f}%"
    )
    
    update.message.reply_text(response)


def main() -> None:
    
    app = ApplicationBuilder().token(token).build()


    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lastmonth", last_month))
    app.add_handler(CommandHandler("currentmonth", current_month))
    app.add_handler(CommandHandler("all", all_time))
    app.add_handler(CommandHandler("lasttime", last_time))
    app.add_handler(CommandHandler("personalStat", personal_stats))

    app.add_handler(MessageHandler(filters.TEXT, count_emoji))

    app.run_polling()


if __name__ == '__main__':
    main()

#processo numero 2836688