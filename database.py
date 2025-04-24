from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
) #SQLAlchemy’nin temel veritabanı araçları. Veritabanı motoru oluşturma, kolon türleri, ilişkiler vs.

from sqlalchemy.orm import declarative_base, relationship, sessionmaker
#declarative_base: Model sınıflarının temeli
#relationship: Tablolar arası ilişkiler
#sessionmaker: Veritabanı oturumu oluşturma

Base = declarative_base()
#Bütün model sınıflarının miras alacağı temel sınıf. SQLAlchemy bunu kullanarak tabloları yönetir.


# -- Tables --
class User(Base):
    __tablename__ = "users"
    id           = Column(Integer, primary_key=True)
    username     = Column(String(50), unique=True, nullable=False)
    password_hash= Column(String(128), nullable=False)

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
#Bu kullanıcıya ait tüm sohbetler.Kullanıcı silinirse, sohbetleri de silinir.



class Chat(Base):
    __tablename__ = "chats"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
    #Her sohbet, bir kullanıcıya (user_id) bağlıdır.
    title      = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    user       = relationship("User", back_populates="chats")
    messages   = relationship("Message",  back_populates="chat", cascade="all, delete-orphan")
    documents  = relationship("Document", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    id         = Column(Integer, primary_key=True)
    chat_id    = Column(Integer, ForeignKey("chats.id"))
    role       = Column(String(10))  # 'user' | 'assistant'
    content    = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    #Mesaj: Bir sohbete bağlıdır (chat_id), kullanıcıdan mı asistandan mı geldiğini role belirler.

    chat     = relationship("Chat",     back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedback"
    id          = Column(Integer, primary_key=True)
    message_id  = Column(Integer, ForeignKey("messages.id"))
    is_helpful  = Column(Boolean)
    #is_helpful: True (doğru) veya False (yanlış).
    comment     = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="feedback")


class Document(Base):
    __tablename__ = "documents"
    id          = Column(Integer, primary_key=True)
    chat_id     = Column(Integer, ForeignKey("chats.id"))
    #Bir belge, bir sohbete (chat_id) bağlıdır.
    file_name   = Column(String(255))
    file_path   = Column(String(500))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="documents")

# -- Helpers --
def init_db():
    engine = create_engine("sqlite:///chatbot.db", echo=False)
    Base.metadata.create_all(engine)
    #Yukarıda tanımlanan tüm tabloları veritabanında oluşturur.
    return engine


def get_db():
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()
#Veritabanına bağlı bir SQLAlchemy oturumu (session) oluşturur. Veritabanı işlemlerinin yapılacağı bağlantıdır.
