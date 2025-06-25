import os, uuid, hashlib, shutil, time
from datetime import datetime
import streamlit as st
#uuid benzersiz ID üretme, hashlib veri hash’leme (şifre gibi), shutil	kopyalama & silme gibi dosya işlemleri.

from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
#Langchain: Belgeyi bölme, vektörleştirme, ve LLM ile etkileşim kurma için.

from database import get_db, Chat, Message, Feedback, Document
#Veritabanı işlemleri için modeller ve bağlantı fonksiyonu.


UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)
#Belgelerin yükleneceği klasör. Yoksa oluşturur.


# --Chat Interface--
def chat_interface():
    for k, v in [
        ("current_chat", None),
        ("messages", []),
        ("editing_chat", None),
        ("show_comment_form", False),
        ("feedback_message_id", None),
        ("chat_retrievers", {}),
        ("processed_file_id", None),
    ]:
        st.session_state.setdefault(k, v)


        '''Anahtar (k)	        Açıklama
        current_chat	        Kullanıcının şu anda açık olan sohbetin ID’si
        messages	            Geçmiş sohbet mesajlarını tutan liste
        editing_chat	        Kullanıcının başlığını düzenlediği sohbetin ID’si
        show_comment_form	    Geri bildirim formu gösterilsin mi? (True/False)
        feedback_message_id	    Geri bildirim verilecek mesajın ID’si
        chat_retrievers	        Her sohbet için vektör tabanlı bilgi alma objesi (retriever)
        processed_file_id	    İşlenmiş belgeyi tanımlamak için benzersiz anahtar (aynı dosya tekrar yüklenmesin diye)'''
    #setdefault():
    '''
    Eğer k oturum değişkenlerinde yoksa, ona v değerini atar.
    Eğer zaten varsa, hiçbir şey yapmaz.
    Bu sayede, ilk çalıştırmada gerekli tüm oturum verileri sıfırdan ayarlanmış olur. Tek tek if ... not in session_state: yazmaya gerek kalmaz.'''


    # --Sidebar--
    with st.sidebar:
        st.title("Chat History")

        if st.button("+ New Chat"):
            _reset_chat_state()

        for chat in load_previous_chats(st.session_state.user_id):
            #Kullanıcının daha önce yaptığı tüm sohbetleri veritabanından alır ve döngüyle listeler.

            #Her sohbet satırı 3 parçaya ayrılır
            col1, col2, col3 = st.columns([3, 1, 1])
            # Başlık / seç-düzenle / sil
            with col1:
                if st.session_state.editing_chat == chat.id:
                    new_title = st.text_input("New title", value=chat.title, key=f"edit_{chat.id}")
                    if st.button("Save", key=f"save_{chat.id}") and update_chat_title(chat.id, new_title):
                        st.session_state.editing_chat = None
                        st.rerun()
                else:
                    if st.button(chat.title, key=f"chat_{chat.id}"):
                        _load_chat(chat.id)
            with col2:
                if st.button("✏️", key=f"edit_btn_{chat.id}"):
                    st.session_state.editing_chat = chat.id
                    st.rerun()
            with col3:
                if st.button("🗑️", key=f"del_{chat.id}") and delete_chat(chat.id):
                    if st.session_state.current_chat == chat.id:
                        _reset_chat_state()
                    st.rerun()

    # --Main--
    st.title("Chat with your document")

    #Dinamik widget key sayesinde yeni sohbette önceki dosya görünmez.Eğer bir sohbet açık ise o sohbetin ID’siyle bir key oluşturur
    uploader_key = f"uploader_{st.session_state.current_chat or 'new'}"
    file = st.file_uploader(
        "Upload a document (PDF, DOCX, or TXT)",
        type=["pdf", "docx", "txt"],
        key=uploader_key,
    )

    if file:
        file_hash = hashlib.sha1(file.getvalue()).hexdigest()
        file_key  = f"{file.name}_{file.size}_{file_hash}"
        #Dosyanın Eşsiz Anahtarını Üret -- Aynı dosya tekrar tekrar işlenmesin.

        already_done = (
            st.session_state.processed_file_id == file_key
            and st.session_state.current_chat in st.session_state.chat_retrievers
        )

        if not already_done:
            with st.spinner("Processing document..."):
                docs = process_uploaded_file(file)
                #Yüklenen belgeyi oku, içeriği parçala (chunk'lara böl).
                if docs:
                    if not st.session_state.current_chat:
                        st.session_state.current_chat = _create_empty_chat()
                        #Eğer henüz sohbet başlatılmadıysa, bir sohbet oluşturulur.

                    #Vektör Veritabanı Kurulumu
                    retr = (
                        setup_vector_store(docs, st.session_state.current_chat)
                        .as_retriever(search_type="similarity", search_kwargs={"k": 10})
                    )
                    #Belgelerden embedding (vektör) çıkarılır.
                    #Chroma veritabanı oluşturulur.
                    #Bu veritabanı "retriever" haline getirilir (LLM’in belgeye dayalı cevap verebilmesi için).

                    st.session_state.chat_retrievers[st.session_state.current_chat] = retr
                    st.session_state.processed_file_id = file_key
                    #Bu sohbete ait retriever saklanır.
                    #İşlenen dosyanın anahtarı oturuma kaydedilir.
                    st.success("Document processed successfully!")

#retriever, belgeler arasından soruya en uygun bilgileri seçen yapıdır.
#chunk = Belgenin küçük parçalara bölünmüş hali. Bir belgeyi doğrudan LLM'e veremezsin çünkü çok uzun olabilir.

    # Geçmiş mesajlar
    for i, m in enumerate(st.session_state.messages):
        #st.session_state.messages: Kullanıcının şu ana kadar gönderdiği ve aldığı tüm mesajları tutan bir liste.
        #enumerate() → Hem mesajın içeriğini (m), hem de dizideki sırasını (i) verir.
        with st.chat_message(m["role"]):
            #Her mesajı sohbet kutusunda gösterir.
            st.write(m["content"])
            #Mesaj balonunun içine mesaj içeriğini (content) yazdırır.
            if m["role"] == "assistant" and "message_id" in m:
                _feedback_ui(i, m["message_id"])
                #i: Bu mesajın kaçıncı sırada olduğunu belirtir (butonlar için key olarak kullanılır).
                #m["message_id"]: Bu mesaja ait veritabanı ID'si, geri bildirimle ilişkilendirmek için kullanılır.

    # Kullanıcı sorusu
    if prompt := st.chat_input("What would you like to know?"):
        #st.chat_input(...): Sayfanın altına bir sohbet kutusu yerleştirir.

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                retr = st.session_state.chat_retrievers.get(st.session_state.current_chat)
            #Şu anki sohbet ID’sine ait retriever varsa onu alır.Yani: Hangi belge yüklüyse, onun vektör verisini bul.
                answer = (
                    _generate_answer(prompt, retr)
                    if retr
                    else "Please upload a document first."
                )
            st.write(answer)
            mid = save_chat_to_db(prompt, answer)
            #Kullanıcının sorusu ve asistanın cevabı veritabanına kaydedilir.
            #mid → Asistan mesajına ait veritabanı ID’si (geri bildirimde kullanılacak).
            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "message_id": mid}
            )
            st.rerun()

# ───────────────────────── Helper Functions ───────────────────────
def _reset_chat_state():
    st.session_state.current_chat      = None
    st.session_state.messages          = []
    st.session_state.editing_chat      = None
    st.session_state.chat_retrievers   = {}
    st.session_state.processed_file_id = None

def _load_chat(cid):
    _reset_chat_state()
    st.session_state.current_chat = cid
    for m in load_chat_messages(cid):
        st.session_state.messages.append(
            {"role": m.role, "content": m.content, "message_id": m.id}
        )
    st.rerun()

def _create_empty_chat():
    db = get_db()
    try:
        chat = Chat(user_id=st.session_state.user_id, title="Untitled chat")
        db.add(chat)
        db.commit()
        return chat.id
    finally:
        db.close()

def _generate_answer(q, retr):
    llm = ChatGoogleGenerativeAI(
        model="models/gemini-2.5-flash-preview-04-17",
        temperature=0.3,
        max_tokens=500,
        convert_system_message_to_human=True,
    )
    sys_prompt = (
        "You are an assistant for question‑answering tasks. "
        "Answer in at most three sentences using the provided context."
    )
    prompt = ChatPromptTemplate.from_messages(
        [("system", sys_prompt), ("human", "Context: {context}\n\nQuestion: {input}")]
    )
    chain = create_retrieval_chain(retr, create_stuff_documents_chain(llm, prompt))
    #LangChain zinciri kurulur
    #Retriever → bağlamı bulur
    #Prompt + LLM → cevabı üretir
    return chain.invoke({"input": q})["answer"]

def _feedback_ui(idx, mid):
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        if st.button("👍 Doğru", key=f"yes_{idx}") and save_feedback(mid, True):
            st.toast("Teşekkürler!", icon="✅")
    with col2:
        if st.button("👎 Yanlış", key=f"no_{idx}"):
            st.session_state.feedback_message_id = mid
            st.session_state.show_comment_form = True
            st.rerun()
    if st.session_state.show_comment_form and st.session_state.feedback_message_id == mid:
        with col3:
            c = st.text_input("Neden yanlış?", key=f"com_{mid}")
            if st.button("Gönder", key=f"send_{mid}"):
                save_feedback(mid, False, c)
                st.session_state.show_comment_form = False
                st.session_state.feedback_message_id = None
                st.toast("Teşekkürler!", icon="✅")
                time.sleep(2)
                st.rerun()


# ───────────────────── DB Helpers ───────────────────────
def save_chat_to_db(umsg, amsg):
    db = get_db()
    try:
        if not st.session_state.current_chat:
            st.session_state.current_chat = _create_empty_chat()
        cid = st.session_state.current_chat
        db.add(Message(chat_id=cid, role="user", content=umsg))
        assistant = Message(chat_id=cid, role="assistant", content=amsg)
        db.add(assistant)
        db.commit()
        return assistant.id
    finally:
        db.close()

def save_feedback(mid, ok, comment=None):
    db = get_db()
    try:
        fb = db.query(Feedback).filter(Feedback.message_id == mid).first()
        #Daha önce bu mesaja geri bildirim verildi mi kontrol
        if fb:
            fb.is_helpful = ok
            fb.comment = comment or fb.comment
            #Eğer geri bildirim varsa güncellenir
        else:
            db.add(Feedback(message_id=mid, is_helpful=ok, comment=comment))
        db.commit()
        return True
    finally:
        db.close()

def delete_chat(cid):
    db = get_db()
    try:
        # SQL verileri silinir
        db.query(Message).filter(Message.chat_id == cid).delete()
        docs = db.query(Document).filter(Document.chat_id == cid).all()
        for d in docs:
            try:
                os.remove(d.file_path)
            except FileNotFoundError:
                pass
        db.query(Document).filter(Document.chat_id == cid).delete()
        db.query(Chat).filter(Chat.id == cid).delete()
        db.commit()
    finally:
        db.close()

    # Chroma klasörlerini temizle
    for d in os.listdir("./chroma_db"):
        if d.startswith(f"chat_{cid}_"):
            shutil.rmtree(os.path.join("./chroma_db", d), ignore_errors=True)
    st.session_state.chat_retrievers.pop(cid, None)
    return True

def update_chat_title(cid, title):
    db = get_db()
    try:
        chat = db.query(Chat).filter(Chat.id == cid).first()
        if chat:
            chat.title = title
            db.commit()
            return True
        return False
    finally:
        db.close()

def load_previous_chats(uid):
    db = get_db()
    try:
        return (
            db.query(Chat)
            .filter(Chat.user_id == uid)
            .order_by(Chat.created_at.desc())
            .all()
        )
    finally:
        db.close()

def load_chat_messages(cid):
    db = get_db()
    try:
        return db.query(Message).filter(Message.chat_id == cid).order_by(
            Message.created_at
        ).all()
    finally:
        db.close()

# ───────────────────── File → Vector store ────────────────────
def process_uploaded_file(file):
    if file.size > 200 * 1024 * 1024:
        st.error("Max 200 MB."); return None

    ext = os.path.splitext(file.name)[1].lower()
    #Dosyanın uzantısı alınır (.pdf, .docx, .txt gibi)
    file_hash = hashlib.sha1(file.getvalue()).hexdigest()
    #Dosyanın içeriğinden SHA1 hash üretilir → eşsiz kimlik
    permanent_path = os.path.join(UPLOAD_DIR, f"{file_hash}{ext}")
    #Kalıcı dosya yolu oluşturulur

    if not os.path.exists(permanent_path):
        with open(permanent_path, "wb") as f:
            f.write(file.getvalue())
            #Aynı dosya daha önce yüklenmediyse, diske yazılır.

    if st.session_state.current_chat:
        db = get_db()
        try:
            if not db.query(Document).filter(
                Document.chat_id == st.session_state.current_chat,
                Document.file_path == permanent_path
                #Aynı belge daha önce eklenmiş mi kontrol edilir.
            ).first():
                db.add(Document(
                    chat_id=st.session_state.current_chat,
                    file_name=file.name,
                    file_path=permanent_path,
                    #Eklenmemişse belge bilgisi veritabanına kaydedilir.
                ))
                db.commit()
        finally:
            db.close()

    loader = (
        PyPDFLoader(permanent_path) if ext == ".pdf"
        else Docx2txtLoader(permanent_path) if ext == ".docx"
        else TextLoader(permanent_path, encoding="utf-8") if ext == ".txt"
        else None
        #Dosya uzantısına göre uygun Loader seç
    )
    if loader is None:
        st.error("Unsupported format"); return None

    docs = loader.load()
    return RecursiveCharacterTextSplitter(chunk_size=1000).split_documents(docs)
    #Metin, 1000 karakterlik parçalara (chunk) bölünür ve döndürülür.


#Bu fonksiyon, yukarıda parçalanmış belgelerden bir vektör veri tabanı (vector store) oluşturur.Retriever sistemi için hazırlanır.
def setup_vector_store(docs, cid):
    directory = f"./chroma_db/chat_{cid}_{uuid.uuid4().hex[:8]}"
    os.makedirs(directory, exist_ok=True)
    #Her sohbete özel klasör açılır (benzersiz UUID ile)
    emb = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    #Her chunk için embedding (vektör) üretmek üzere Gemini embedding modeli çağrılır.
    return Chroma.from_documents(docs, emb, persist_directory=directory)
#Tüm belge parçaları embedding'e dönüştürülür.
#Bu embedding’ler Chroma’ya kaydedilir.
#Geriye bir Chroma nesnesi döner (retriever gibi kullanılacak).