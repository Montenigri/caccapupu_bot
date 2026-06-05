import logging
import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from telegram import BotCommand, BotCommandScopeAllGroupChats, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import dotenv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io

dotenv.load_dotenv()
token = os.getenv("BOT_TOKEN", "")

log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=log_level
)
logger = logging.getLogger(__name__)

DB_DIR = os.getenv("DB_DIR", "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "emoji_count.db")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
conn.execute('''CREATE TABLE IF NOT EXISTS emoji_count
             (group_id INTEGER, user_id INTEGER, date TEXT)''')
conn.execute('''CREATE INDEX IF NOT EXISTS idx_emoji_group_date
             ON emoji_count (group_id, date)''')
conn.execute('''CREATE INDEX IF NOT EXISTS idx_emoji_group_user_date
             ON emoji_count (group_id, user_id, date)''')
conn.commit()

# Emoji da contare
TARGET_EMOJI = '💩'
MILESTONES = [100, 500, 1000, 5000]  

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Bot avviato! Conta cacche attivata.")

async def get_username(context: ContextTypes.DEFAULT_TYPE, group_id: int, user_id: int) -> str:
    cache = context.chat_data.setdefault("username_cache", {})
    if user_id in cache:
        return cache[user_id]
    try:
        member = await context.bot.get_chat_member(group_id, user_id)
        username = member.user.username or f"{member.user.first_name} {member.user.last_name or ''}".strip()
        cache[user_id] = username
        return username
    except Exception as e:
        logger.error(f"Errore nel recuperare l'username per user_id {user_id} in group_id {group_id}: {e}")
        return "Unknown"

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Questo bot conta una particolare emoji nei gruppi.\n\n"
        "/start - Avvia il bot\n"
        "/help - Mostra questo\n"
        "/lastmonth - Classifica ultimi 30 giorni\n"
        "/currentmonth - Classifica mese corrente\n"
        "/all - Classifica totale\n"
        "/lasttime - Ultima cacca per utente\n"
        "/personalstat - Statistiche personali\n"
        "/chart [settimana|mese|anno] - Grafico personale\n"
        "/streak - La tua striscia di 💩 consecutivi\n"
        "/nostreak - Chi non 💩 da più tempo\n"
        "/burn - Prendi in giro chi non 💩 da tanto\n"
        "/ranking [giorno|settimana|mese|anno] - Classifica con medaglie\n"
        "/monthwinner - Vincitore del mese\n\n"
        "Se vuoi offrirmi un caffé: https://www.buymeacoffee.com/montenigri"
    )

async def count_emoji(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    message = update.message.text
    if TARGET_EMOJI in message:
        group_id = update.message.chat_id
        user_id = update.message.from_user.id
        date = datetime.now(timezone.utc).isoformat()

        with conn:
            conn.execute("INSERT INTO emoji_count (group_id, user_id, date) VALUES (?, ?, ?)", (group_id, user_id, date))
            count = conn.execute(
                "SELECT COUNT(*) FROM emoji_count WHERE group_id = ? AND user_id = ?",
                (group_id, user_id)
            ).fetchone()[0]

        if count in MILESTONES:
            username = await get_username(context, group_id, user_id)
            await update.message.reply_text(f"🏆 {username} ha raggiunto {count} 💩!")

async def last_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id
    one_month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    
    with conn:
        results = conn.execute(
            "SELECT user_id, COUNT(*) FROM emoji_count WHERE group_id = ? AND date >= ? GROUP BY user_id ORDER BY COUNT(*) DESC",
            (group_id, one_month_ago.isoformat())
        ).fetchall()
    
    lines = ["Conteggio delle cacche nell'ultimo mese:"]
    for user_id, count in results:
        username = await get_username(context, group_id, user_id)
        lines.append(f"{username}: {count}")
    
    await update.message.reply_text("\n".join(lines))

async def all_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id

    with conn:
        results = conn.execute(
            '''SELECT user_id, COUNT(*), MIN(date) 
                     FROM emoji_count 
                     WHERE group_id = ? 
                     GROUP BY user_id 
                     ORDER BY COUNT(*) DESC''',
            (group_id,)
        ).fetchall()

        first_date_result = conn.execute(
            '''SELECT MIN(date) 
                     FROM emoji_count 
                     WHERE group_id = ?''',
            (group_id,)
        ).fetchone()
        first_date = first_date_result[0] if first_date_result else None
        first_date_formatted = datetime.fromisoformat(first_date).strftime('%d/%m/%Y') if first_date else "N/A"
    
    lines = [f"Conteggio totale delle emoji (prima cacca registrata il {first_date_formatted}):"]
    for user_id, count, _ in results:
        username = await get_username(context, group_id, user_id)
        lines.append(f"{username}: {count}")
    
    await update.message.reply_text("\n".join(lines))


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

async def last_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id
    
    with conn:
        results = conn.execute(
            '''SELECT user_id, MAX(date) 
                     FROM emoji_count 
                     WHERE group_id = ? 
                     GROUP BY user_id 
                     ORDER BY MAX(date) DESC''',
            (group_id,)
        ).fetchall()
    
    response = "Ultima volta che ogni utente ha inviato l'emoji:\n"
    lines = ["Ultima volta che ogni utente ha inviato l'emoji:"]
    for user_id, last_date in results:
        username = await get_username(context, group_id, user_id)
        last_date_dt = datetime.fromisoformat(last_date)
        if not last_date_dt.tzinfo:
            last_date_dt = last_date_dt.replace(tzinfo=timezone.utc)
        last_date_formatted = last_date_dt.strftime('%d-%m %H:%M')
        time_diff = datetime.now(timezone.utc) - last_date_dt
        time_ago = format_time_ago(time_diff)
            
        lines.append(f"{username}: {last_date_formatted} ({time_ago})")
    
    await update.message.reply_text("\n".join(lines))

    
async def current_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    with conn:
        results = conn.execute(
            '''SELECT user_id, COUNT(*) 
                     FROM emoji_count 
                     WHERE group_id = ? AND date >= ? 
                     GROUP BY user_id 
                     ORDER BY COUNT(*) DESC''',
            (group_id, start_of_month.isoformat())
        ).fetchall()
    
    lines = ["Conteggio delle emoji nel mese corrente:"]
    for user_id, count in results:
        username = await get_username(context, group_id, user_id)
        lines.append(f"{username}: {count}")
    
    await update.message.reply_text("\n".join(lines))


async def streak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id
    user_id = update.message.from_user.id

    if context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            user_id = update.message.from_user.id

    with conn:
        rows = conn.execute(
            '''SELECT DISTINCT DATE(date) as d
               FROM emoji_count
               WHERE group_id = ? AND user_id = ?
               ORDER BY d''',
            (group_id, user_id)
        ).fetchall()

    if not rows:
        await update.message.reply_text("Nessuna 💩 trovata per questo utente.")
        return

    dates = [row[0] for row in rows]

    longest = 1
    current_run = 1
    for i in range(1, len(dates)):
        prev = datetime.strptime(dates[i - 1], '%Y-%m-%d').date()
        curr = datetime.strptime(dates[i], '%Y-%m-%d').date()
        if (curr - prev).days == 1:
            current_run += 1
            longest = max(longest, current_run)
        else:
            current_run = 1

    active = 0
    for i in range(len(dates) - 1, -1, -1):
        d = datetime.strptime(dates[i], '%Y-%m-%d').date()
        if i == len(dates) - 1:
            if (datetime.now(timezone.utc).date() - d).days > 1:
                active = 0
                break
            active = 1
        else:
            prev_d = datetime.strptime(dates[i], '%Y-%m-%d').date()
            next_d = datetime.strptime(dates[i + 1], '%Y-%m-%d').date()
            if (next_d - prev_d).days == 1:
                active += 1
            else:
                break

    username = await get_username(context, group_id, user_id)
    await update.message.reply_text(
        f"💩 Streak di {username}:\n"
        f"🏆 Record: {longest} giorni consecutivi\n"
        f"🔥 Serie attiva: {active} giorni"
    )


async def get_nostreak_data(context: ContextTypes.DEFAULT_TYPE, group_id: int) -> list:
    with conn:
        rows = conn.execute(
            '''SELECT user_id, MAX(date) as last_date
               FROM emoji_count
               WHERE group_id = ?
               GROUP BY user_id
               ORDER BY last_date ASC''',
            (group_id,)
        ).fetchall()

    now = datetime.now(timezone.utc)
    result = []
    for user_id, last_date_str in rows:
        last_date = datetime.fromisoformat(last_date_str)
        if last_date.tzinfo is None:
            last_date = last_date.replace(tzinfo=timezone.utc)
        days = (now - last_date).days
        username = await get_username(context, group_id, user_id)
        result.append((username, user_id, days, last_date))
    return result


async def nostreak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id
    data = await get_nostreak_data(context, group_id)

    if not data:
        await update.message.reply_text("Nessuna 💩 registrata in questo gruppo.")
        return

    data.sort(key=lambda x: x[2])
    lines = ["⏰ Classifica dell'astinenza da 💩 (dal più recente):"]
    for username, _, days, _ in data:
        lines.append(f"{username}: {days} giorni fa")

    await update.message.reply_text("\n".join(lines))


BURN_ROASTS = [
    "{0} non 💩 da {1} giorni. Tutto bene a casa?",
    "{0} è in sciopero della 💩 da {1} giorni!",
    "{0} ha smesso di 💩 da {1} giorni. Dovremmo preoccuparci?",
    "{0} non 💩 da {1} giorni. Blocco intestinale?",
    "{0} sta accumulando da {1} giorni. Sarà un'esplosione atomica.",
    "{0} non 💩 da {1} giorni. Record personale?",
]


async def burn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id
    data = await get_nostreak_data(context, group_id)

    if not data:
        await update.message.reply_text("Nessuna 💩 registrata. Non posso prendere in giro nessuno.")
        return

    data.sort(key=lambda x: x[2])
    username, _, days, _ = data[-1]
    msg = random.choice(BURN_ROASTS).format(username, days)
    await update.message.reply_text(msg)


async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id

    periods = {
        "giorno": timedelta(days=1),
        "settimana": timedelta(days=7),
        "mese": timedelta(days=30),
        "anno": timedelta(days=365),
    }

    period_label = "di sempre"
    if context.args and context.args[0] in periods:
        delta = periods[context.args[0]]
        cutoff = datetime.now(timezone.utc) - delta
        period_label = f"dell'ultimo {context.args[0]}"
        with conn:
            results = conn.execute(
                '''SELECT user_id, COUNT(*)
                   FROM emoji_count
                   WHERE group_id = ? AND date >= ?
                   GROUP BY user_id
                   ORDER BY COUNT(*) DESC''',
                (group_id, cutoff.isoformat())
            ).fetchall()
    else:
        with conn:
            results = conn.execute(
                '''SELECT user_id, COUNT(*)
                   FROM emoji_count
                   WHERE group_id = ?
                   GROUP BY user_id
                   ORDER BY COUNT(*) DESC''',
                (group_id,)
            ).fetchall()

    if not results:
        await update.message.reply_text("Nessun dato disponibile.")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = [f"🏆 Classifica {period_label}:"]
    for i, (user_id, count) in enumerate(results):
        username = await get_username(context, group_id, user_id)
        medal = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{medal} {username}: {count}")

    await update.message.reply_text("\n".join(lines))


async def month_winner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    with conn:
        results = conn.execute(
            '''SELECT user_id, COUNT(*)
               FROM emoji_count
               WHERE group_id = ? AND date >= ?
               GROUP BY user_id
               ORDER BY COUNT(*) DESC
               LIMIT 1''',
            (group_id, start_of_month.isoformat())
        ).fetchone()

    if not results:
        await update.message.reply_text("Nessun dato per questo mese.")
        return

    user_id, count = results
    username = await get_username(context, group_id, user_id)
    month_name = now.strftime('%B')
    await update.message.reply_text(
        f"👑 Il re di {month_name} è {username} con {count} 💩!"
    )


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

    normalized_dates = []
    for dt in dates:
        if dt.tzinfo is None:
            normalized_dates.append(dt.replace(tzinfo=timezone.utc))
        else:
            normalized_dates.append(dt.astimezone(timezone.utc))

    # Calcolo del tempo totale in giorni
    total_days = (datetime.now(timezone.utc) - normalized_dates[0]).days + 1

    frequency_per_day = total_emojis / total_days

    # Calcolo della distanza media tra le emoji
    time_diffs = [
        (normalized_dates[i + 1] - normalized_dates[i]).total_seconds()
        for i in range(total_emojis - 1)
    ]

    avg_time_diff_hours = sum(time_diffs) / len(time_diffs) / 3600 if time_diffs else 0

    weekdays = [dt.weekday() for dt in normalized_dates]  # 0 = Lunedì, ..., 6 = Domenica
    hours = [dt.hour for dt in normalized_dates]

    most_common_weekday = max(set(weekdays), key=weekdays.count) if weekdays else None
    most_common_hour = max(set(hours), key=hours.count) if hours else None

    last_emoji_date = normalized_dates[-1] if normalized_dates else None

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
        user_dates = conn.execute(
            '''SELECT date 
                     FROM emoji_count 
                     WHERE group_id = ? AND user_id = ? 
                     ORDER BY date ASC''',
            (group_id, user_id)
        ).fetchall()

        # Recupera tutte le date di invio delle emoji per tutti gli utenti del gruppo
        group_data = conn.execute(
            '''SELECT user_id, date 
                     FROM emoji_count 
                     WHERE group_id = ? 
                     ORDER BY user_id, date ASC''',
            (group_id,)
        ).fetchall()
    
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



async def personal_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id
    user_id = update.message.from_user.id

    stats = get_user_and_group_stats(group_id, user_id)
    
    if "error" in stats:
        await update.message.reply_text(stats["error"])
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

async def chart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    group_id = update.message.chat_id
    user_id = update.message.from_user.id

    date_delta = {
        "settimana": 7,
        "mese": 30,
        "anno": 365
    }
    if len(context.args) != 1 or context.args[0] not in date_delta:
        await update.message.reply_text("Uso corretto: /chart [settimana|mese|anno]")
        return

    period_type = context.args[0]
    days = date_delta[period_type]
    selected_delta = datetime.now(timezone.utc) - timedelta(days=days)

    with conn:
        data = conn.execute(
            '''SELECT user_id, date 
                    FROM emoji_count 
                    WHERE user_id = ? AND group_id = ? AND date >= ? 
                    ORDER BY date ASC''',
            (user_id, group_id, selected_delta.isoformat())
        ).fetchall()

    if not data:
        await update.message.reply_text("Nessun dato disponibile per il grafico.")
        return

    # Organizza i dati in base al periodo
    time_counts = {}
    for user_id, date_str in data:
        date = datetime.fromisoformat(date_str)
        if period_type == "settimana":
            time_key = date.strftime('%d/%m')  # Giorno per giorno
        elif period_type == "mese":
            week_num = (date.day - 1) // 7 + 1
            time_key = f"Sett. {week_num}"  # Settimana per settimana
        else:  # anno
            time_key = date.strftime('%b')  # Mese per mese     
        if time_key not in time_counts:
            time_counts[time_key] = 0
        time_counts[time_key] += 1

    # Prepara i dati per il grafico
    time_labels = list(time_counts.keys())
    counts = list(time_counts.values())

    # Crea il grafico quadrato
    plt.figure(figsize=(8, 8))
    plt.plot(time_labels, counts, color='skyblue', linewidth=3.0)
    plt.ylabel('Numero di cacche')
    plt.title('Le tue cacche')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Salva il grafico in un buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    # Invia il grafico come immagine
    await update.message.reply_photo(photo=buf)
    buf.close()


async def post_init(application):
    commands = [
        BotCommand("start", "Avvia il bot"),
        BotCommand("help", "Mostra aiuto"),
        BotCommand("lastmonth", "Classifica ultimi 30 giorni"),
        BotCommand("currentmonth", "Classifica mese corrente"),
        BotCommand("all", "Classifica totale"),
        BotCommand("lasttime", "Ultima cacca per utente"),
        BotCommand("personalstat", "Statistiche personali"),
        BotCommand("chart", "Grafico personale"),
        BotCommand("streak", "La tua striscia di 💩"),
        BotCommand("nostreak", "Astinenza da 💩"),
        BotCommand("burn", "Prendi in giro chi non 💩"),
        BotCommand("ranking", "Classifica con medaglie"),
        BotCommand("monthwinner", "Vincitore del mese"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        await application.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())
        logger.info("Comandi Telegram registrati con successo")
    except Exception as e:
        logger.error(f"Errore registrazione comandi: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Errore non gestito durante l'elaborazione di un update", exc_info=context.error)

def main() -> None:
    if not token:
        raise RuntimeError("BOT_TOKEN non trovato. Imposta BOT_TOKEN in variabile ambiente o nel file .env")
    
    app = ApplicationBuilder().token(token).post_init(post_init).build()


    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("lastmonth", last_month))
    app.add_handler(CommandHandler("currentmonth", current_month))
    app.add_handler(CommandHandler("all", all_time))
    app.add_handler(CommandHandler("lasttime", last_time))
    app.add_handler(CommandHandler("personalstat", personal_stats))
    app.add_handler(CommandHandler("chart", chart))
    app.add_handler(CommandHandler("streak", streak))
    app.add_handler(CommandHandler("nostreak", nostreak))
    app.add_handler(CommandHandler("burn", burn))
    app.add_handler(CommandHandler("ranking", ranking))
    app.add_handler(CommandHandler("monthwinner", month_winner))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, count_emoji))
    app.add_error_handler(error_handler)

    app.run_polling()


if __name__ == '__main__':
    main()

