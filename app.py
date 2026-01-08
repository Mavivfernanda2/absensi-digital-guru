import streamlit as st
from PIL import Image
from pyzbar.pyzbar import decode
import qrcode
import pandas as pd
import datetime
import os

# ================= CONFIG =================
st.set_page_config("Absensi Guru", layout="centered")

USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "guru1": {"password": "guru123", "role": "guru"},
    "guru2": {"password": "guru123", "role": "guru"},
}

ABSEN_FILE = "absensi.csv"

# ================= SESSION =================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.user = ""
    st.session_state.role = ""

# ================= LOGIN =================
def login_page():
    st.title("🔐 Login Absensi Guru")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u in USERS and USERS[u]["password"] == p:
            st.session_state.login = True
            st.session_state.user = u
            st.session_state.role = USERS[u]["role"]
            st.rerun()
        else:
            st.error("Username / Password salah")

# ================= LOGOUT =================
def logout():
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# ================= ADMIN =================
def admin_page():
    st.subheader("🧑‍💼 Admin Panel")

    today = datetime.date.today()
    kode = f"ABSEN_GURU_{today}"

    st.success("Kode QR Hari Ini")
    st.code(kode)

    qr = qrcode.make(kode)
    st.image(qr, caption="QR Absensi Hari Ini")

# ================= GURU =================
def guru_page():
    st.subheader("👨‍🏫 Absensi Guru")
    st.info("Scan QR absensi")

    img = st.camera_input("Scan QR di sini")

    if img:
        image = Image.open(img)
        decoded = decode(image)

        if decoded:
            qr_data = decoded[0].data.decode("utf-8")
            today = str(datetime.date.today())

            if qr_data == f"ABSEN_GURU_{today}":
                waktu = datetime.datetime.now().strftime("%H:%M:%S")

                data = {
                    "tanggal": today,
                    "waktu": waktu,
                    "guru": st.session_state.user
                }

                df = pd.DataFrame([data])

                if os.path.exists(ABSEN_FILE):
                    df.to_csv(ABSEN_FILE, mode="a", header=False, index=False)
                else:
                    df.to_csv(ABSEN_FILE, index=False)

                st.success("✅ Absensi Berhasil")
                st.write(data)
            else:
                st.error("❌ QR tidak valid")
        else:
            st.error("QR tidak terbaca")

# ================= MAIN =================
if not st.session_state.login:
    login_page()
else:
    col1, col2 = st.columns([6,1])
    with col2:
        logout()

    st.markdown(f"**Login sebagai:** `{st.session_state.user.upper()}`")

    if st.session_state.role == "admin":
        admin_page()
    else:
        guru_page()
