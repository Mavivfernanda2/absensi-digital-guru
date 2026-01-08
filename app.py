import streamlit as st
from PIL import Image
from pyzbar.pyzbar import decode
import qrcode
import pandas as pd
import datetime
import os

# ================= CONFIG =================
st.set_page_config("Absensi Digital Guru", layout="centered")

USER_FILE = "users.csv"
ABSEN_FILE = "absensi.csv"
QR_PATH = "qr_absen.png"
COLUMNS = ["tanggal", "guru", "jam_masuk", "jam_pulang"]

# ================= INIT FILE =================
def init_users():
    if not os.path.exists(USER_FILE):
        df = pd.DataFrame([
            {"username":"admin","password":"admin123","role":"admin"},
            {"username":"guru01","password":"guru123","role":"guru"},
            {"username":"guru02","password":"guru123","role":"guru"},
        ])
        df.to_csv(USER_FILE, index=False)

def load_users():
    return pd.read_csv(USER_FILE)

def save_users(df):
    df.to_csv(USER_FILE, index=False)

init_users()

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
        df = load_users()
        user = df[(df.username == u) & (df.password == p)]

        if not user.empty:
            st.session_state.login = True
            st.session_state.user = u
            st.session_state.role = user.iloc[0]["role"]
            st.rerun()
        else:
            st.error("❌ Username atau Password salah")

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

    st.success("📌 QR Absensi Hari Ini")
    st.code(kode)

    qr = qrcode.make(kode)
    qr.save(QR_PATH)
    st.image(QR_PATH, use_container_width=True)

    # ===== REKAP =====
    st.divider()
    st.subheader("📊 Rekap Absensi")

    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
        st.dataframe(df, use_container_width=True)

        df.to_excel("rekap_absensi.xlsx", index=False)
        with open("rekap_absensi.xlsx","rb") as f:
            st.download_button(
                "⬇️ Download Excel",
                f,
                file_name="rekap_absensi.xlsx"
            )
    else:
        st.info("Belum ada data absensi")

    # ===== MANAJEMEN GURU =====
    st.divider()
    st.subheader("👥 Manajemen Guru")

    users = load_users()

    with st.expander("➕ Tambah Guru"):
        u = st.text_input("Username Guru Baru")
        p = st.text_input("Password", type="password")

        if st.button("Tambah Guru"):
            if u in users.username.values:
                st.error("Username sudah ada")
            else:
                users.loc[len(users)] = [u, p, "guru"]
                save_users(users)
                st.success("Guru berhasil ditambahkan")
                st.rerun()

    st.dataframe(users)

    guru_list = users[users.role=="guru"].username.tolist()
    if guru_list:
        selected = st.selectbox("Pilih Guru", guru_list)
        new_pw = st.text_input("Password Baru")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✏️ Update Password"):
                users.loc[users.username==selected,"password"] = new_pw
                save_users(users)
                st.success("Password diperbarui")
                st.rerun()

        with col2:
            if st.button("❌ Hapus Guru"):
                users = users[users.username!=selected]
                save_users(users)
                st.warning("Guru dihapus")
                st.rerun()

# ================= GURU PAGE =================
def guru_page():
    st.subheader("👨‍🏫 Absensi Guru")
    st.info("Scan QR untuk absensi")

    img = st.camera_input("📸 Scan QR")

    if not img:
        return

    image = Image.open(img)
    decoded = decode(image)

    if not decoded:
        st.error("❌ QR tidak terbaca")
        return

    qr_data = decoded[0].data.decode()
    today = str(datetime.date.today())
    now_time = datetime.datetime.now()
    now_str = now_time.strftime("%H:%M:%S")

    # Validasi QR
    if qr_data != f"ABSEN_GURU_{today}":
        st.error("❌ QR tidak valid / bukan hari ini")
        return

    # Load / init CSV
    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
    else:
        df = pd.DataFrame(columns=COLUMNS)

    mask = (df["tanggal"] == today) & (df["guru"] == st.session_state.user)

    # ================= LOGIKA JAM =================
    if now_time.hour < 8:
        # ===== JAM MASUK =====
        if mask.any():
            st.warning("⚠️ Kamu sudah absen masuk hari ini")
        else:
            df.loc[len(df)] = [today, st.session_state.user, now_str, ""]
            st.success(f"✅ Absen MASUK berhasil ({now_str})")

    else:
        # ===== JAM PULANG =====
        if not mask.any():
            st.warning("⚠️ Kamu belum absen masuk hari ini")
        else:
            idx = df[mask].index[0]
            if df.loc[idx, "jam_pulang"] == "" or pd.isna(df.loc[idx, "jam_pulang"]):
                df.loc[idx, "jam_pulang"] = now_str
                st.success(f"✅ Absen PULANG berhasil ({now_str})")
            else:
                st.warning("⚠️ Kamu sudah absen pulang hari ini")

    df.to_csv(ABSEN_FILE, index=False)
    st.dataframe(df[mask])

# ================= MAIN =================
if not st.session_state.login:
    login_page()
else:
    col1,col2 = st.columns([6,1])
    with col2:
        logout()

    st.markdown(f"**Login sebagai:** `{st.session_state.user.upper()}`")

    if st.session_state.role=="admin":
        admin_page()
    else:
        guru_page()
