from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from datetime import datetime

import sqlite3

TOKEN = "8791007606:AAEneEd5S2s7fM4frvND2lYgCuON514iAsc"

conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    servicio TEXT,
    barbero TEXT,
    valor REAL,
    fecha TEXT
)
""")

async def guardar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        servicio, valor = [x.strip() for x in update.message.text.split(",")]
        valor = float(valor)

        usuario = (update.effective_user.username or str(update.effective_user.id)).lower()

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(
            "INSERT INTO registros (servicio, barbero, valor, fecha) VALUES (?, ?, ?, ?)",
            (servicio.lower(), usuario.lower(), valor, fecha)
        )
        conn.commit()

        await update.message.reply_text("✅ Guardado")

    except:
        await update.message.reply_text("❌ Usa: servicio, valor")

async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoy = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT barbero, servicio, COUNT(*), SUM(valor)
        FROM registros
        WHERE fecha LIKE ?
        GROUP BY barbero, servicio
        ORDER BY barbero
    """, (f"{hoy}%",))

    resultados = cursor.fetchall()

    if not resultados:
        await update.message.reply_text("No hay registros hoy")
        return

    mensaje = "📊 Resumen del día\n\n"

    barbero_actual = None
    total_barbero = 0
    total_general = 0

    for barbero, servicio, cantidad, total in resultados:
        if barbero != barbero_actual:
            if barbero_actual is not None:
                mensaje += f"Total: ${total_barbero:,.0f}\n\n"

            mensaje += f"💈 {barbero}\n"
            barbero_actual = barbero
            total_barbero = 0

        mensaje += f"{servicio}: {cantidad} - ${total:,.0f}\n"
        total_barbero += total
        total_general += total

    # último barbero
    mensaje += f"Total: ${total_barbero:,.0f}\n\n"
    mensaje += f"💰 TOTAL GENERAL: ${total_general:,.0f}"

    await update.message.reply_text(mensaje)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guardar))
app.add_handler(CommandHandler("resumen", resumen))

app.run_polling()
