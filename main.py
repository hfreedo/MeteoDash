"""
Sistema Meteorológico - Backend Server
FastAPI + WebSocket + pySerial + SQLite

La conexión Serial al Arduino se gestiona desde el Dashboard.
"""

import json
import asyncio
import threading
import time
import shutil
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, UploadFile, File, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

import serial
import serial.tools.list_ports

from database import init_db, save_reading, get_history, get_latest
from auth import (
    pwd_context, load_users, save_users, create_access_token,
    get_current_user, require_admin
)

app = FastAPI(title="Sistema Meteorológico Dashboard")

# --- Rutas ---
BASE_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = BASE_DIR / "dashboard"
ABOUT_FILE = DASHBOARD_DIR / "config" / "about.json"
IMG_DIR = DASHBOARD_DIR / "img"

# --- Estado global ---
latest_data: dict = {}
serial_connection: serial.Serial = None
serial_thread: threading.Thread = None
serial_running: bool = False
connected_clients: list = []
test_mode: bool = False
test_timer: asyncio.Task = None


def serial_reader_thread():
    """Hilo dedicado a leer del puerto serial."""
    global latest_data, serial_connection, serial_running
    while serial_running and serial_connection and serial_connection.is_open:
        try:
            line = serial_connection.readline().decode("utf-8", errors="ignore").strip()
            if line:
                try:
                    data = json.loads(line)
                    latest_data = data
                    save_reading(data)
                except json.JSONDecodeError:
                    pass
        except (serial.SerialException, OSError):
            break
        except Exception:
            break
    serial_running = False


def send_command(cmd: str):
    if serial_connection and serial_connection.is_open:
        serial_connection.write((cmd + "\n").encode("utf-8"))


async def broadcast(data: dict):
    payload = json.dumps(data)
    disconnected = []
    for ws in connected_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        connected_clients.remove(ws)


@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(broadcast_loop())


# --- REST API: Autenticación ---
@app.post("/api/login")
async def api_login(data: dict):
    users = load_users()
    username = data.get("username", "")
    password = data.get("password", "")
    user = users.get(username)
    if not user or not pwd_context.verify(password, user["password_hash"]):
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    token = create_access_token({"sub": username, "role": user["role"], "name": user["name"]})
    return {"token": token, "user": {"username": username, "role": user["role"], "name": user["name"]}}


@app.get("/api/me")
def api_me(user: dict = Depends(get_current_user)):
    return {"username": user["sub"], "role": user["role"], "name": user["name"]}


# --- REST API: Puertos Serial (admin) ---
@app.get("/api/ports")
def api_list_ports():
    """Lista los puertos COM disponibles."""
    ports = []
    for p in serial.tools.list_ports.comports():
        ports.append({
            "device": p.device,
            "description": p.description,
            "hwid": p.hwid
        })
    return {"ports": ports, "connected": serial_running, "active_port": serial_connection.port if serial_connection else None}


@app.post("/api/connect")
def api_connect(port: str = Query(...), baud: int = Query(9600), user: dict = Depends(require_admin)):
    """Conecta al puerto Serial especificado."""
    global serial_connection, serial_thread, serial_running
    if serial_running:
        raise HTTPException(400, "Ya hay una conexión activa. Desconecta primero.")

    try:
        serial_connection = serial.Serial(port, baud, timeout=1)
        time.sleep(1.5)
        serial_running = True
        serial_thread = threading.Thread(target=serial_reader_thread, daemon=True)
        serial_thread.start()
        return {"status": "connected", "port": port, "baud": baud}
    except Exception as e:
        raise HTTPException(500, f"No se pudo conectar a {port}: {str(e)}")


@app.post("/api/disconnect")
def api_disconnect(user: dict = Depends(require_admin)):
    """Desconecta el puerto Serial."""
    global serial_connection, serial_running, latest_data
    if serial_connection and serial_connection.is_open:
        serial_running = False
        serial_connection.close()
    latest_data = {}
    return {"status": "disconnected"}


# --- REST API: Datos ---
@app.get("/api/latest")
def api_latest():
    row = get_latest()
    return row or latest_data


@app.get("/api/history")
def api_history(hours: int = Query(default=24, ge=1, le=168)):
    return get_history(hours)


@app.post("/api/command")
def api_command(cmd: str = Query(...), user: dict = Depends(require_admin)):
    if not serial_connection or not serial_connection.is_open:
        raise HTTPException(400, "No hay conexión Serial activa.")
    send_command(cmd)
    return {"status": "ok", "command": cmd}


@app.get("/api/status")
def api_status():
    return {
        "connected": serial_running,
        "port": serial_connection.port if serial_connection else None,
        "clients": len(connected_clients)
    }


# --- REST API: Acerca de / Identificación ---
def load_about():
    if ABOUT_FILE.exists():
        with open(ABOUT_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    return {"project": {}, "logo": "", "team": []}


def save_about(data: dict):
    ABOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ABOUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.get("/api/about")
def api_get_about():
    return load_about()


@app.post("/api/about")
async def api_save_about(data: dict, user: dict = Depends(require_admin)):
    save_about(data)
    return {"status": "saved"}


@app.post("/api/upload-logo")
async def api_upload_logo(file: UploadFile = File(...), user: dict = Depends(require_admin)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Solo se permiten imágenes.")
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix or ".png"
    safe_name = f"colelogo_{int(time.time())}{ext.lower()}"
    dest = IMG_DIR / safe_name
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "uploaded", "path": f"img/{safe_name}"}


@app.post("/api/upload-avatar/{member_index}")
async def api_upload_avatar(member_index: int, file: UploadFile = File(...), user: dict = Depends(require_admin)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Solo se permiten imagenes.")
    AVATARS_DIR = IMG_DIR / "avatars"
    AVATARS_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix or ".png"
    safe_name = f"member_{member_index}{ext}"
    dest = AVATARS_DIR / safe_name
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "uploaded", "path": f"img/avatars/{safe_name}"}


# --- REST API: Modo Test (servidor) ---
@app.post("/api/test-mode")
async def api_test_mode(user: dict = Depends(require_admin)):
    global test_mode, test_timer, latest_data
    test_mode = not test_mode
    if test_mode:
        test_timer = asyncio.create_task(run_test_data())
        return {"status": "test_mode_on"}
    else:
        if test_timer:
            test_timer.cancel()
            test_timer = None
        latest_data = {}
        # Notificar a todos los clientes que limpien widgets
        if connected_clients:
            clear_msg = json.dumps({"type": "clear_widgets"})
            await broadcast_raw(clear_msg)
        return {"status": "test_mode_off"}


@app.post("/api/clear-history")
def api_clear_history(user: dict = Depends(require_admin)):
    import sqlite3
    conn = sqlite3.connect("weather_data.db")
    conn.execute("DELETE FROM readings")
    conn.commit()
    conn.close()
    # Notificar a todos los clientes
    async def _notify():
        if connected_clients:
            msg = json.dumps({"type": "history_cleared"})
            await broadcast_raw(msg)
    asyncio.create_task(_notify())
    return {"status": "cleared"}


async def run_test_data():
    global latest_data
    import random
    base_temp = 24 + random.random() * 6
    base_hum = 55 + random.random() * 15
    base_pres = 101300 + random.random() * 500
    print("[TEST] Modo Test iniciado - datos cada 1s")
    while test_mode:
        try:
            base_temp += (random.random() - 0.5) * 0.8
            base_hum += (random.random() - 0.5) * 2
            base_pres += (random.random() - 0.5) * 40
            data = {
                "t": round(base_temp, 1),
                "h": round(min(100, max(0, base_hum)), 1),
                "p": round(base_pres),
                "a": round(100 + random.random() * 50, 1),
                "l": random.randint(100, 900),
                "ir": 0 if random.random() > 0.7 else 1,
                "ax": round((random.random() - 0.5) * 0.4, 2),
                "ay": round((random.random() - 0.5) * 0.4, 2),
                "az": round(9.8 + (random.random() - 0.5) * 0.2, 2),
                "gx": round((random.random() - 0.5) * 2, 2),
                "gy": round((random.random() - 0.5) * 2, 2),
                "gz": round((random.random() - 0.5) * 2, 2),
                "tb": round(base_temp, 1)
            }
            latest_data = data
            save_reading(data)
            if connected_clients:
                payload = json.dumps({"type": "reading", "data": data, "ts": datetime.now().isoformat()})
                await broadcast_raw(payload)
                print(f"[TEST] Enviado: t={data['t']} h={data['h']} a {len(connected_clients)} clientes")
            else:
                print(f"[TEST] Sin clientes conectados, dato guardado en BD")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[TEST] Error: {e}")
            await asyncio.sleep(1)
    print("[TEST] Modo Test detenido")


async def broadcast_raw(payload: str):
    disconnected = []
    for ws in connected_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        connected_clients.remove(ws)
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        while True:
            msg = await ws.receive_text()
            data = json.loads(msg)
            if "cmd" in data:
                send_command(data["cmd"])
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)


# --- Servir dashboard ---
DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"

if DASHBOARD_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR)), name="static")

    @app.get("/")
    async def serve_dashboard():
        return FileResponse(str(DASHBOARD_DIR / "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "Dashboard no encontrado. Coloca los archivos en /dashboard"}


# --- Broadcast loop ---
async def broadcast_loop():
    """Broadcast de datos reales del Arduino cuando NO esta en modo test."""
    while True:
        if latest_data and connected_clients and not test_mode:
            payload = {
                "type": "reading",
                "data": latest_data,
                "ts": datetime.now().isoformat()
            }
            await broadcast(payload)
        await asyncio.sleep(1)


if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print("=" * 55)
    print("  SISTEMA METEOROLOGICO - BACKEND")
    print("  Dashboard  : http://localhost:8000")
    print("  API Docs   : http://localhost:8000/docs")
    print(f"  Red local  : http://{local_ip}:8000")
    print("  Conecta el Arduino desde el Dashboard")
    print("  Dispositivos externos: conectate a la misma WiFi")
    print("  o crea un hotspot en esta PC (Zona movil)")
    print("=" * 55)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
