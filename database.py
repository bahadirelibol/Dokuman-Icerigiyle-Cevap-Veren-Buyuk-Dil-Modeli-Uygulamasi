from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

# ─── Tables ──────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id           = Column(Integer, primary_key=True)
    username     = Column(String(50), unique=True, nullable=False)
    password_hash= Column(String(128), nullable=False)

    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"))
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

    chat     = relationship("Chat",     back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedback"
    id          = Column(Integer, primary_key=True)
    message_id  = Column(Integer, ForeignKey("messages.id"))
    is_helpful  = Column(Boolean)
    comment     = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="feedback")


class Document(Base):
    __tablename__ = "documents"
    id          = Column(Integer, primary_key=True)
    chat_id     = Column(Integer, ForeignKey("chats.id"))
    file_name   = Column(String(255))
    file_path   = Column(String(500))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="documents")

# ─── Helpers ─────────────────────────────────────────────────────────
def init_db():
    engine = create_engine("sqlite:///chatbot.db", echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_db():
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()
