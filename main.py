from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime
import pandas as pd
import os
import sys

app = FastAPI()

# Configurar ruta base segura para plantillas y recursos tanto en desarrollo como en el .exe compilado
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

# Montar carpeta estática
static_dir = os.path.join(base_path, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates_dir = os.path.join(base_path, "templates")
templates = Jinja2Templates(directory=templates_dir)

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehiculos_conductores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_conductor TEXT NOT NULL,
            grado_cargo TEXT,
            numero_licencia TEXT,
            unidad_destino TEXT,
            tipo_vehiculo TEXT,
            placa TEXT UNIQUE NOT NULL,
            marca TEXT,
            modelo TEXT,
            color TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registros_accesos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehiculo_id INTEGER,
            tipo TEXT,
            fecha_hora TEXT,
            motivo TEXT,
            observaciones TEXT,
            FOREIGN KEY (vehiculo_id) REFERENCES vehiculos_conductores(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- RUTA PRINCIPAL (Dashboard de Hoy) ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT r.fecha_hora, r.tipo, v.grado_cargo, v.nombre_conductor, 
               v.numero_licencia, v.unidad_destino, v.tipo_vehiculo, 
               v.placa, v.marca, v.modelo, v.color, r.motivo, r.observaciones
        FROM registros_accesos r
        JOIN vehiculos_conductores v ON r.vehiculo_id = v.id
        WHERE r.fecha_hora LIKE ?
        ORDER BY r.id DESC
    """, (f"{hoy_str}%",))
    registros_hoy = cursor.fetchall()
    conn.close()
    
    return templates.TemplateResponse(request, "index.html", {"registros": registros_hoy, "fecha_hoy": hoy_str})

# --- API PARA ACTUALIZACIÓN EN TIEMPO REAL (JSON) ---
@app.get("/api/registros_hoy")
def api_registros_hoy():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("""
        SELECT r.fecha_hora, r.tipo, v.grado_cargo, v.nombre_conductor, 
               v.numero_licencia, v.unidad_destino, v.tipo_vehiculo, 
               v.placa, v.marca, v.modelo, v.color, r.motivo, r.observaciones
        FROM registros_accesos r
        JOIN vehiculos_conductores v ON r.vehiculo_id = v.id
        WHERE r.fecha_hora LIKE ?
        ORDER BY r.id DESC
    """, (f"{hoy_str}%",))
    registros = cursor.fetchall()
    conn.close()
    return {"registros": registros}

# --- RUTA VISTA DE REGISTRO ---
@app.get("/registrar", response_class=HTMLResponse)
def registrar_page(request: Request):
    return templates.TemplateResponse(request, "registrar.html")

# --- RUTA LISTA DE VEHÍCULOS ---
@app.get("/vehiculos", response_class=HTMLResponse)
def vehiculos_page(request: Request):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehiculos_conductores ORDER BY id DESC")
    vehiculos = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse(request, "vehiculos.html", {"vehiculos": vehiculos})

# CRUD: Guardar Vehículo
@app.post("/guardar_vehiculo")
def guardar_vehiculo(
    nombre_conductor: str = Form(...),
    grado_cargo: str = Form(...),
    numero_licencia: str = Form(...),
    unidad_destino: str = Form(...),
    tipo_vehiculo: str = Form(...),
    placa: str = Form(...),
    marca: str = Form(...),
    modelo: str = Form(...),
    color: str = Form(...)
):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO vehiculos_conductores 
            (nombre_conductor, grado_cargo, numero_licencia, unidad_destino, tipo_vehiculo, placa, marca, modelo, color)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nombre_conductor, grado_cargo, numero_licencia, unidad_destino, tipo_vehiculo, placa.upper(), marca, modelo, color))
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
    return {"status": "ok", "message": "Vehículo registrado con éxito"}

# --- ACTUALIZAR VEHÍCULO ---
@app.post("/actualizar_vehiculo/{vehiculo_id}")
def actualizar_vehiculo(
    vehiculo_id: int,
    nombre_conductor: str = Form(...),
    grado_cargo: str = Form(...),
    numero_licencia: str = Form(...),
    unidad_destino: str = Form(...),
    tipo_vehiculo: str = Form(...),
    placa: str = Form(...),
    marca: str = Form(...),
    modelo: str = Form(...),
    color: str = Form(...)
):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE vehiculos_conductores 
            SET nombre_conductor=?, grado_cargo=?, numero_licencia=?, unidad_destino=?, 
                tipo_vehiculo=?, placa=?, marca=?, modelo=?, color=?
            WHERE id=?
        """, (nombre_conductor, grado_cargo, numero_licencia, unidad_destino, tipo_vehiculo, placa.upper(), marca, modelo, color, vehiculo_id))
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
    return {"status": "ok", "message": "Vehículo actualizado con éxito"}

# --- ELIMINAR VEHÍCULO ---
@app.get("/eliminar_vehiculo/{vehiculo_id}")
def eliminar_vehiculo(vehiculo_id: int):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM registros_accesos WHERE vehiculo_id = ?", (vehiculo_id,))
        cursor.execute("DELETE FROM vehiculos_conductores WHERE id = ?", (vehiculo_id,))
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()
    return {"status": "ok", "message": "Vehículo eliminado con éxito"}

# Generar QR Personalizado con Texto Superior y Logo en el Centro
@app.get("/generar_qr/{placa}")
def generar_qr(placa: str):
    qr = qrcode.QRCode(
        version=3,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(placa.upper())
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

    logo_path = os.path.join(static_dir, "logo.png")
    if os.path.exists(logo_path):
        try:
            logo = Image.open(logo_path)
            basewidth = 80
            wpercent = (basewidth / float(logo.size[0]))
            hsize = int(float(logo.size[1]) * float(wpercent))
            logo = logo.resize((basewidth, hsize), Image.Resampling.LANCZOS)
            
            pos = ((qr_img.size[0] - logo.size[0]) // 2, (qr_img.size[1] - logo.size[1]) // 2)
            
            box_logo = Image.new("RGB", (logo.size[0] + 10, logo.size[1] + 10), "white")
            box_pos = ((qr_img.size[0] - box_logo.size[0]) // 2, (qr_img.size[1] - box_logo.size[1]) // 2)
            qr_img.paste(box_logo, box_pos)
            qr_img.paste(logo, pos)
        except Exception as e:
            print(f"No se pudo adjuntar el logo al QR: {e}")

    margin_top = 70
    width, height = qr_img.size
    final_img = Image.new("RGB", (width, height + margin_top), "white")
    final_img.paste(qr_img, (0, margin_top))

    draw = ImageDraw.Draw(final_img)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except:
        font = ImageFont.load_default()

    texto = "QR exclusivo para el parqueo de la EAATE"
    
    try:
        bbox = draw.textbbox((0, 0), texto, font=font)
        text_width = bbox[2] - bbox[0]
    except:
        text_width = font.getlength(texto) if hasattr(font, 'getlength') else 200

    text_x = (width - text_width) // 2
    text_y = 25
    draw.text((text_x, text_y), texto, fill="black", font=font)

    buf = io.BytesIO()
    final_img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

# Vista Escáner
@app.get("/scanner", response_class=HTMLResponse)
def scanner(request: Request):
    return templates.TemplateResponse(request, "scanner.html")

# API Escaneo con manejo seguro de excepciones (QR ajenos al sistema)
@app.post("/api/escaneo")
def registrar_escaneo(
    placa: str = Form(...), 
    tipo: str = Form(...), 
    motivo: str = Form("Visita institucional"), 
    observaciones: str = Form("Ninguna")
):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, nombre_conductor FROM vehiculos_conductores WHERE placa = ?", (placa.strip().upper(),))
        vehiculo = cursor.fetchone()
        
        if not vehiculo:
            conn.close()
            return {
                "status": "error", 
                "message": f"❌ Código QR no válido: La placa '{placa.upper()}' no pertenece al sistema de la institución."
            }
        
        vehiculo_id, nombre = vehiculo
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO registros_accesos (vehiculo_id, tipo, fecha_hora, motivo, observaciones)
            VALUES (?, ?, ?, ?, ?)
        """, (vehiculo_id, tipo, fecha_actual, motivo, observaciones))
        
        conn.commit()
        return {"status": "ok", "message": f"✅ {tipo} registrada con éxito:\nConductor: {nombre}\nPlaca: {placa.upper()}"}
        
    except Exception as e:
        conn.rollback()
        return {"status": "error", "message": f"⚠️ Error interno procesando el escaneo: {str(e)}"}
    finally:
        conn.close()

# Exportar Excel por Rango de Fechas
@app.get("/exportar_excel")
def exportar_excel(fecha_inicio: str = None, fecha_fin: str = None):
    conn = sqlite3.connect("database.db")
    query = """
        SELECT r.fecha_hora AS 'Fecha y Hora', r.tipo AS 'Tipo de Acceso', 
               v.grado_cargo AS 'Grado/Cargo', v.nombre_conductor AS 'Conductor', 
               v.numero_licencia AS 'Nro Licencia', v.unidad_destino AS 'Unidad Destino', 
               v.tipo_vehiculo AS 'Tipo Vehículo', v.placa AS 'Placa', 
               v.marca AS 'Marca', v.modelo AS 'Modelo', v.color AS 'Color', 
               r.motivo AS 'Motivo', r.observaciones AS 'Observaciones'
        FROM registros_accesos r
        JOIN vehiculos_conductores v ON r.vehiculo_id = v.id
    """
    params = []
    if fecha_inicio and fecha_fin:
        query += " WHERE date(r.fecha_hora) BETWEEN ? AND ?"
        params = [fecha_inicio, fecha_fin]
    elif fecha_inicio:
        query += " WHERE date(r.fecha_hora) >= ?"
        params = [fecha_inicio]
    elif fecha_fin:
        query += " WHERE date(r.fecha_hora) <= ?"
        params = [fecha_fin]
        
    query += " ORDER BY r.id DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Reporte_Vehicular')
    output.seek(0)
    
    filename = f"reporte_{fecha_inicio or 'inicio'}_al_{fecha_fin or 'fin'}.xlsx"
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# Bloque optimizado con host="0.0.0.0" para permitir conexión desde el celular y red local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")