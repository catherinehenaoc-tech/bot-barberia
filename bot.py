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

async def exportar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT servicio, barbero, valor, fecha FROM registros")
    datos = cursor.fetchall()

    if not datos:
        await update.message.reply_text("No hay datos para exportar")
        return

    filename = "reporte.csv"

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["servicio", "barbero", "valor", "fecha"])
        writer.writerows(datos)

    with open(filename, "rb") as f:
        await update.message.reply_document(document=f)

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

def obtener_datos(fecha_inicio, fecha_fin=None):
    if fecha_fin:
        cursor.execute("""
            SELECT barbero, servicio, COUNT(*), SUM(valor)
            FROM registros
            WHERE fecha BETWEEN ? AND ?
            GROUP BY barbero, servicio
            ORDER BY barbero
        """, (fecha_inicio, fecha_fin))
    else:
        cursor.execute("""
            SELECT barbero, servicio, COUNT(*), SUM(valor)
            FROM registros
            WHERE fecha = ?
            GROUP BY barbero, servicio
            ORDER BY barbero
        """, (fecha_inicio,))

    return cursor.fetchall()

async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("❌ Usa: /resumen hoy | ayer | semana | YYYY-MM-DD")
        return

    filtro = context.args[0].lower()
    hoy = datetime.now()

    # ----------------------------
    # FECHAS
    # ----------------------------

    if filtro == "hoy":
        fecha_inicio = fecha_fin = hoy.strftime("%Y-%m-%d")

    elif filtro == "ayer":
        fecha_inicio = fecha_fin = (hoy - timedelta(days=1)).strftime("%Y-%m-%d")

    elif filtro == "semana":
        inicio = hoy - timedelta(days=hoy.weekday())
        fecha_inicio = inicio.strftime("%Y-%m-%d")
        fecha_fin = hoy.strftime("%Y-%m-%d")

    else:
        fecha_inicio = fecha_fin = filtro

    # ----------------------------
    # 1. POR BARBERO + SERVICIO
    # ----------------------------

    cursor.execute("""
        SELECT barbero, servicio, SUM(valor)
        FROM registros
        WHERE fecha BETWEEN ? AND ?
        GROUP BY barbero, servicio
        ORDER BY barbero
    """, (fecha_inicio, fecha_fin))

    por_barbero = cursor.fetchall()

    # ----------------------------
    # 2. GLOBAL POR SERVICIO
    # ----------------------------

    cursor.execute("""
        SELECT servicio, SUM(valor)
        FROM registros
        WHERE fecha BETWEEN ? AND ?
        GROUP BY servicio
    """, (fecha_inicio, fecha_fin))

    por_servicio = cursor.fetchall()

    # ----------------------------
    # CONSTRUCCIÓN MENSAJE
    # ----------------------------

    mensaje = f"📊 Resumen {fecha_inicio}\n\n"

    total_general = 0
    barbero_actual = None
    total_barbero = 0

    # ----------------------------
    # DETALLE POR BARBERO
    # ----------------------------

    for barbero, servicio, total in por_barbero:

        if barbero != barbero_actual:
            if barbero_actual is not None:
                mensaje += f"Total barbero: ${total_barbero:,.0f}\n\n"

            mensaje += f"💈 {barbero}\n"
            barbero_actual = barbero
            total_barbero = 0

        mensaje += f"{servicio}: ${total:,.0f}\n"

        total_barbero += total
        total_general += total

    # cerrar último barbero
    mensaje += f"Total barbero: ${total_barbero:,.0f}\n\n"

    # ----------------------------
    # TOTAL GLOBAL POR SERVICIO
    # ----------------------------

    mensaje += "📌 TOTAL POR SERVICIO\n"

    for servicio, total in por_servicio:
        mensaje += f"{servicio}: ${total:,.0f}\n"

    # ----------------------------
    # 🔴 TOTAL GENERAL (ÚLTIMA LÍNEA)
    # ----------------------------

    mensaje += f"\n💰 TOTAL GENERAL: ${total_general:,.0f}"

    await update.message.reply_text(mensaje)



        
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, guardar))
app.add_handler(CommandHandler("resumen", resumen))
app.add_handler(CommandHandler("exportar", exportar))

app.run_polling()
