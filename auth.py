import bcrypt #Şifreleri güvenli şekilde hash'lemek (şifrelemek) ve doğrulamak için kullanılır.
from database import get_db, User


def login(username: str, password: str):
    db = get_db()
    try:
        user = db.query(User).filter(User.username == username).first()
        #Veritabanından verilen kullanıcı adına sahip ilk kullanıcı sorgulanır.

        if user and bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return user
        #Eğer kullanıcı varsa ve verilen şifre, veritabanındaki şifre hash’i ile uyuşuyorsa kullanıcı nesnesi döndürülür.

        return None
    finally:
        db.close()


def register(username: str, password: str) -> bool:
    db = get_db()
    try:
        if db.query(User).filter(User.username == username).first():
            return False
        #Eğer bu kullanıcı adına sahip biri zaten varsa kayıt yapılmaz ve False döndürülür.

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        #Verilen şifre hash’lenir (şifrelenir). gensalt(), her kullanıcı için rastgele bir tuz oluşturur.
        #Tuz (salt), bir şifreyi hash’lemeden önce o şifreye eklenen rastgele bir veri parçasıdır. Amacı, aynı şifreyi kullanan iki farklı kullanıcı için bile farklı hash’ler üretmektir.

        db.add(User(username=username, password_hash=hashed))
        db.commit()
        #Değişiklikler veritabanına kalıcı olarak kaydedilir.

        return True
    finally:
        db.close()
        