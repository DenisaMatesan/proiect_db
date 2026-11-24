import hashlib
import binascii
import hmac
import json
import base64
import time
from core.database import DatabaseManager

class AuthService:
    SECRET_KEY = b"delice_patisserie_secret_auth_token_key_2026"
    SALT = b"laborator_delice_salt"

    @classmethod
    def hash_password(cls, password: str) -> str:
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), cls.SALT, 100000)
        return binascii.hexlify(pwdhash).decode('ascii')

    @classmethod
    def verify_password(cls, password: str, stored_hash: str) -> bool:
        return cls.hash_password(password) == stored_hash

    @classmethod
    def authenticate(cls, username: str, password: str):
        db = DatabaseManager.get_instance()
        user = db.query_one("SELECT * FROM UTILIZATORI WHERE nume = ?", (username.strip().lower(),))
        if not user:
            return None
        
        if cls.verify_password(password, user['parola']):
            token = cls.generate_session_token(user)
            return {
                "id_utilizator": user['id_utilizator'],
                "nume": user['nume'],
                "rol": user['rol'],
                "token": token
            }
        return None

    @classmethod
    def generate_session_token(cls, user: dict) -> str:
        payload = {
            "id": user['id_utilizator'],
            "nume": user['nume'],
            "rol": user['rol'],
            "exp": int(time.time()) + 86400 # 24h
        }
        raw = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        sig = hmac.new(cls.SECRET_KEY, raw, hashlib.sha256).hexdigest()
        token_str = base64.urlsafe_b64encode(raw).decode('ascii') + "." + sig
        return token_str

    @classmethod
    def verify_session_token(cls, token: str):
        if not token or "." not in token:
            return None
        try:
            b64_part, sig = token.split(".", 1)
            raw = base64.urlsafe_b64decode(b64_part.encode('ascii'))
            expected_sig = hmac.new(cls.SECRET_KEY, raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None
            payload = json.loads(raw.decode('utf-8'))
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except Exception:
            return None
