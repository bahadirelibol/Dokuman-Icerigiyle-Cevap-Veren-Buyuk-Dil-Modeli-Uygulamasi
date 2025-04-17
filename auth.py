import bcrypt
from database import get_db, User


def login(username: str, password: str):
    db = get_db()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user and bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return user
        return None
    finally:
        db.close()


def register(username: str, password: str) -> bool:
    db = get_db()
    try:
        if db.query(User).filter(User.username == username).first():
            return False
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db.add(User(username=username, password_hash=hashed))
        db.commit()
        return True
    finally:
        db.close()
