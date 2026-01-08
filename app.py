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
QR_PATH = "qr_absen.png"

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

# ================= ADMIN PAGE =================
def admin_page():
    st.subheader("🧑‍💼 Admin Panel")

    today = datetime.date.today()
    kode = f"ABSEN_GURU_{today}"

    st.success("QR Absensi Hari Ini")
    st.code(kode)

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(kode)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    img_qr.save(QR_PATH)

    st.image(QR_PATH, use_container_width=True)

    # ===== REKAP =====
    st.divider()
    st.subheader("📊 Rekap Absensi")

    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
        st.dataframe(df, use_container_width=True)

        excel_file = "rekap_absensi.xlsx"
        df.to_excel(excel_file, index=False)

        with open(excel_file, "rb") as f:
            st.download_button(
                "⬇️ Download Rekap Excel",
                f,
                file_name="rekap_absensi.xlsx"
            )
    else:
        st.info("Belum ada data absensi")

# ================= GURU PAGE =================
def guru_page():
    st.subheader("👨‍🏫 Absensi Guru")
    st.info("Scan QR untuk absen masuk / pulang")

    img = st.camera_input("📸 Scan QR di sini")

    if img:
        image = Image.open(img)
        decoded = decode(image)

        if not decoded:
            st.error("QR tidak terbaca")
            return

        qr_data = decoded[0].data.decode("utf-8")
        today = str(datetime.date.today())
        now = datetime.datetime.now().strftime("%H:%M:%S")

        if qr_data != f"ABSEN_GURU_{today}":
            st.error("QR tidak valid")
            return

        # Load / create CSV
        if os.path.exists(ABSEN_FILE):
            df = pd.read_csv(ABSEN_FILE)
        else:
            df = pd.DataFrame(columns=["tanggal", "guru", "jam_masuk", "jam_pulang"])

        # Cek data hari ini
        mask = (df["tanggal"] == today) & (df["guru"] == st.session_state.user)

        if not mask.any():
            # JAM MASUK
            df.loc[len(df)] = [today, st.session_state.user, now, ""]
            st.success(f"✅ Absen MASUK berhasil ({now})")

        else:
            idx = df[mask].index[0]
            if df.loc[idx, "jam_pulang"] == "" or pd.isna(df.loc[idx, "jam_pulang"]):
                # JAM PULANG
                df.loc[idx, "jam_pulang"] = now
                st.success(f"✅ Absen PULANG berhasil ({now})")
            else:
                st.warning("⚠️ Kamu sudah absen masuk & pulang hari ini")

        df.to_csv(ABSEN_FILE, index=False)
        st.dataframe(df[mask])

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
