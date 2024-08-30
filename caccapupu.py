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



def calculate_user_stats(dates: list[datetime]) -> dict:
    """
    Calcola le statistiche di utilizzo delle emoji per un singolo utente.

    :param dates: Una lista di oggetti datetime che rappresentano i momenti in cui sono state inviate le emoji.
    :return: Un dizionario con le statistiche calcolate.
    """
    total_emojis = len(dates)
    
    if total_emojis == 0:
        return {
            "total_emojis": 0,
            "frequency_per_day": 0,
            "avg_time_diff_hours": 0,
            "most_common_weekday": None,
            "most_common_hour": None,
            "last_emoji_date": None
        }

    # Calcolo del tempo totale in giorni
    total_days = (datetime.now(timezone.utc).replace(tzinfo=None) - dates[0]).days + 1

    frequency_per_day = total_emojis / total_days

    # Calcolo della distanza media tra le emoji
    time_diffs = [(dates[i+1] - dates[i]).total_seconds() for i in range(total_emojis - 1) if dates[i+1].tzinfo is not None and dates[i].tzinfo is not None]

    avg_time_diff_hours = sum(time_diffs) / len(time_diffs) / 3600 if time_diffs else 0

    weekdays = [dt.weekday() for dt in dates]  # 0 = Lunedì, ..., 6 = Domenica
    hours = [dt.hour for dt in dates]

    most_common_weekday = max(set(weekdays), key=weekdays.count) if weekdays else None
    most_common_hour = max(set(hours), key=hours.count) if hours else None

    last_emoji_date = dates[-1] if dates else None

    return {
        "total_emojis": total_emojis,
        "frequency_per_day": frequency_per_day,
        "avg_time_diff_hours": avg_time_diff_hours,
        "most_common_weekday": most_common_weekday,
        "most_common_hour": most_common_hour,
        "last_emoji_date": last_emoji_date
    }


def get_user_and_group_stats(group_id: int, user_id: int) -> dict:
    """
    Calcola le statistiche per un utente specifico e le medie per il gruppo di appartenenza.

    :param group_id: L'ID del gruppo Telegram.
    :param user_id: L'ID dell'utente Telegram.
    :return: Un dizionario con le statistiche dell'utente e le medie del gruppo.
    """
    with conn:
        # Recupera tutte le date di invio delle emoji per l'utente specifico
        c.execute('''SELECT date 
                     FROM emoji_count 
                     WHERE group_id = ? AND user_id = ? 
                     ORDER BY date ASC''', 
                  (group_id, user_id))
        user_dates = c.fetchall()

        # Recupera tutte le date di invio delle emoji per tutti gli utenti del gruppo
        c.execute('''SELECT user_id, date 
                     FROM emoji_count 
                     WHERE group_id = ? 
                     ORDER BY user_id, date ASC''', 
                  (group_id,))
        group_data = c.fetchall()
    
    if not user_dates:
        return {
            "error": "L'utente non ha ancora inviato alcuna emoji in questo gruppo."
        }

    # Trasforma le date in oggetti datetime
    user_date_times = [datetime.fromisoformat(date[0]) for date in user_dates]

    # Calcola le statistiche per l'utente specifico
    user_stats = calculate_user_stats(user_date_times)

    # Organizza i dati per ogni utente nel gruppo
    group_user_stats = {}
    for uid, date_str in group_data:
        date_time = datetime.fromisoformat(date_str)
        if uid not in group_user_stats:
            group_user_stats[uid] = []
        group_user_stats[uid].append(date_time)

    # Aggrega le statistiche per il gruppo
    group_stats_aggregate = {
        "total_emojis": 0,
        "frequency_per_day": 0,
        "avg_time_diff_hours": 0,
        "most_common_weekday": [],
        "most_common_hour": [],
    }
    
    total_users = len(group_user_stats)

    for dates in group_user_stats.values():
        stats = calculate_user_stats(dates)
        group_stats_aggregate["total_emojis"] += stats["total_emojis"]
        group_stats_aggregate["frequency_per_day"] += stats["frequency_per_day"]
        group_stats_aggregate["avg_time_diff_hours"] += stats["avg_time_diff_hours"]
        group_stats_aggregate["most_common_weekday"].append(stats["most_common_weekday"])
        group_stats_aggregate["most_common_hour"].append(stats["most_common_hour"])

    # Calcolo delle medie per il gruppo
    avg_group_stats = {
        "total_emojis": group_stats_aggregate["total_emojis"] / total_users,
        "frequency_per_day": group_stats_aggregate["frequency_per_day"] / total_users,
        "avg_time_diff_hours": group_stats_aggregate["avg_time_diff_hours"] / total_users,
        "most_common_weekday": max(set(group_stats_aggregate["most_common_weekday"]), key=group_stats_aggregate["most_common_weekday"].count),
        "most_common_hour": max(set(group_stats_aggregate["most_common_hour"]), key=group_stats_aggregate["most_common_hour"].count),
    }

    return {
        "user_stats": user_stats,
        "group_avg_stats": avg_group_stats
    }



async def personal_stats(update: Update, context: CallbackContext) -> None:
    group_id = update.message.chat_id
    user_id = update.message.from_user.id

    stats = get_user_and_group_stats(group_id, user_id)
    
    if "error" in stats:
        update.message.reply_text(stats["error"])
        return
    
    user_stats = stats["user_stats"]
    group_avg_stats = stats["group_avg_stats"]

    weekday_names = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    most_common_user_weekday_name = weekday_names[user_stats["most_common_weekday"]]
    most_common_group_weekday_name = weekday_names[group_avg_stats["most_common_weekday"]]

    response = (
        f"Statistiche personali per {update.message.from_user.username}:\n\n"
        f"Totale emoji inviate: {user_stats['total_emojis']}\n"
        f"Frequenza di invio ({update.message.from_user.username}): {user_stats['frequency_per_day']:.2f} emoji al giorno\n"
        f"Frequenza di invio media (gruppo): {group_avg_stats['frequency_per_day']:.2f} emoji al giorno\n\n"
        f"Distanza media tra le emoji ({update.message.from_user.username}): {user_stats['avg_time_diff_hours']:.2f} ore\n"
        f"Distanza media tra le emoji (media gruppo): {group_avg_stats['avg_time_diff_hours']:.2f} ore\n\n"
        f"Giorno più attivo ({update.message.from_user.username}): {most_common_user_weekday_name}\n"
        f"Giorno più attivo (media gruppo): {most_common_group_weekday_name}\n\n"
        f"Orario più frequente di invio ({update.message.from_user.username}): {user_stats['most_common_hour']}:00\n"
        f"Orario più frequente di invio (media gruppo): {group_avg_stats['most_common_hour']}:00\n"
    )
    
    await update.message.reply_text(response)


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