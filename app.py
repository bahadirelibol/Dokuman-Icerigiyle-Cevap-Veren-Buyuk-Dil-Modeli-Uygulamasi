import streamlit as st
from dotenv import load_dotenv

from database import init_db
from auth import login, register
from chat import chat_interface

load_dotenv()          # .env dosyasındaki ayarları yükler.
init_db()              # SQLite + tablolar


def login_register_page():
    st.markdown(
        """
        <style>
        .container{display:flex;flex-direction:column;align-items:center;
                   padding:2em;max-width:400px;margin:0 auto;background:#fff;
                   border-radius:10px;box-shadow:0 4px 12px rgba(0,0,0,.05)}
        .title{font-size:2rem;margin-bottom:1rem;color:#1f77b4;text-align:center}
        .subtitle{font-size:1rem;color:#888;margin-bottom:2rem;text-align:center}
        </style>
        """,
        unsafe_allow_html=True,
    )
    #unsafe_allow_html=True: Streamlit’in HTML kodlarını doğrudan sayfada çalıştırmasına izin veren bir parametredir.

    st.markdown("<div class='title'>📄Document Chat Assistant - 📚TOGU</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='subtitle'>Login or register to start chatting with your documents</div>",
        unsafe_allow_html=True,
    )

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    #use_container_width=True: Bu parametre, bir butonun veya bileşenin genişliğini bulunduğu konteynerin (örneğin bir column, sidebar, vs.) genişliğine tamamen yayılacak şekilde ayarlar.
    # Login 
    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if username and password:
                user = login(username, password)
                if user:
                    st.session_state.user_id = user.id
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please fill in all fields")

    # Register 
    with tab2:
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        if st.button("Register", use_container_width=True):
            if new_username and new_password and confirm_password:
                if new_password == confirm_password:
                    if register(new_username, new_password):
                        st.success("Registration successful! Please log in.")
                    else:
                        st.error("Username already exists")
                else:
                    st.error("Passwords do not match")
            else:
                st.warning("Please fill in all fields")
    st.markdown("</div>", unsafe_allow_html=True)



def main():
    st.set_page_config(
        page_title="Document Chat Assistant",
        page_icon="🤖",
        layout="centered",
    )

    if "user_id" not in st.session_state:
        st.session_state.user_id = None
        #Kullanıcı oturumu başlatılmamışsa None olarak atanır.

    if st.session_state.user_id is None:
        login_register_page()
        #Oturum yoksa giriş/kayıt ekranı gösterilir.
        
    else:
        with st.sidebar:
            if st.button("Logout"):
                st.session_state.clear()
                st.rerun()
        chat_interface()
        #Oturum varsa sohbet arayüzü (chat_interface) gösterilir. Yan menüde "Logout" ile çıkış yapılabilir.




if __name__ == "__main__":
    main()