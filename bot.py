from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from datetime import datetime, timedelta

import sqlite3
import csv

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

        usuario = str(update.effective_user.id)

       fecha = datetime.now().strftime("%Y-%m-%d")

        cursor.execute(
            "INSERT INTO registros (servicio, barbero, valor, fecha) VALUES (?, ?, ?, ?)",
            (servicio.lower(), usuario.lower(), valor, fecha)
        )
        conn.commit()

        await update.message.reply_text("✅ Guardado")

    except:
        await update.message.reply_text("❌ Usa: servicio, valor")

def obtener_datos(filtro_fecha=None):
    if filtro_fecha:
        cursor.execute("""
            SELECT barbero, servicio, COUNT(*), SUM(valor)
            FROM registros
            WHERE fecha = ?
            GROUP BY barbero, servicio
            ORDER BY barbero
        """, (filtro_fecha,))
    else:
        cursor.execute("""
            SELECT barbero, servicio, COUNT(*), SUM(valor)
            FROM registros
            GROUP BY barbero, servicio
            ORDER BY barbero
        """)

    return cursor.fetchall()

def construir_mensaje(resultados, titulo):
    mensaje = f"{titulo}\n\n"

    total_general = 0
    ultimo_barbero = None
    total_barbero = 0

    for barbero, servicio, cantidad, total in resultados:

        if barbero != ultimo_barbero:
            if ultimo_barbero is not None:
                mensaje += f"Total: ${total_barbero:,.0f}\n\n"

            mensaje += f"💈 {barbero}\n"
            ultimo_barbero = barbero
            total_barbero = 0

        mensaje += f"{servicio}: {cantidad} - ${total:,.0f}\n"

        total_barbero += total
        total_general += total

    mensaje += f"Total: ${total_barbero:,.0f}\n\n"
    mensaje += f"💰 TOTAL GENERAL: ${total_general:,.0f}"

    return mensaje

def obtener_datos(fecha=None):
    if fecha:
        cursor.execute("""
            SELECT barbero, servicio, COUNT(*), SUM(valor)
            FROM registros
            WHERE fecha = ?
            GROUP BY barbero, servicio
            ORDER BY barbero
        """, (fecha,))
    else:
        cursor.execute("""
            SELECT barbero, servicio, COUNT(*), SUM(valor)
            FROM registros
            GROUP BY barbero, servicio
            ORDER BY barbero
        """)

    return cursor.fetchall()

async def resumen_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoy = datetime.now().strftime("%Y-%m-%d")

    resultados = obtener_datos(hoy)

    if not resultados:
        await update.message.reply_text("No hay registros hoy")
        return

    mensaje = construir_mensaje(resultados, "📊 Resumen de hoy")
    await update.message.reply_text(mensaje)

async def resumen_ayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    resultados = obtener_datos(ayer)

    if not resultados:
        await update.message.reply_text("No hay registros ayer")
        return

    mensaje = construir_mensaje(resultados, "📊 Resumen de ayer")
    await update.message.reply_text(mensaje)

async def resumen_semana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hoy = datetime.now()
    inicio = hoy - timedelta(days=hoy.weekday())

    cursor.execute("""
        SELECT barbero, servicio, COUNT(*), SUM(valor)
        FROM registros
        WHERE fecha >= ?
        GROUP BY barbero, servicio
        ORDER BY barbero
    """, (inicio.strftime("%Y-%m-%d"),))

    resultados = cursor.fetchall()

    mensaje = construir_mensaje(resultados, "📊 Resumen de la semana")

    await update.message.reply_text(mensaje)








        
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guardar))
app.add_handler(CommandHandler("resumen_hoy", resumen_hoy))
app.add_handler(CommandHandler("resumen_ayer", resumen_ayer))
app.add_handler(CommandHandler("resumen_semana", resumen_semana))
app.add_handler(CommandHandler("exportar", exportar))

app.run_polling()
