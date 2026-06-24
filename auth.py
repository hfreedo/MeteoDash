"""
Autenticación JWT — Roles: admin / visitor
"""

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# --- Config ---
SECRET_KEY = "meteodash-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

USERS_FILE = Path(__file__).resolve().parent / "users.json"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def load_users():
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    # Default admin
    default = {
        "admin": {
            "username": "admin",
            "password_hash": pwd_context.hash("admin123"),
            "role": "admin",
            "name": "Administrador"
        },
        "visitor": {
            "username": "visitante",
            "password_hash": pwd_context.hash("visitante123"),
            "role": "visitor",
            "name": "Visitante"
        }
    }
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(default, f, ensure_ascii=False, indent=2)
    return default


def save_users(users: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def create_access_token(data: dict):
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = data.copy()
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalido o expirado")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return verify_token(credentials.credentials)


def require_role(role: str):
    """Dependencia que exige un rol específico."""
    def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") != role and user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Acceso denegado: requiere rol " + role)
        return user
    return role_checker


def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores")
    return user
