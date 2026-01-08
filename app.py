import streamlit as st
from PIL import Image
from pyzbar.pyzbar import decode
import qrcode
import pandas as pd
import datetime
import os

# ================= FILE =================
USER_FILE = "users.csv"
ABSEN_FILE = "absensi.csv"
CONFIG_FILE = "config.csv"
QR_PATH = "qr_absen.png"

COLUMNS = ["tanggal", "guru", "jam_masuk", "jam_pulang", "status"]

# ================= INIT =================
def init_files():
    if not os.path.exists(USER_FILE):
        pd.DataFrame([
            {"username":"admin","password":"admin123","role":"admin"},
            {"username":"guru01","password":"guru123","role":"guru"},
            {"username":"guru02","password":"guru123","role":"guru"},
        ]).to_csv(USER_FILE, index=False)

    if not os.path.exists(CONFIG_FILE):
        pd.DataFrame({"jam_masuk":["07:00"]}).to_csv(CONFIG_FILE, index=False)

init_files()

# ================= HELPERS =================
def load_users():
    return pd.read_csv(USER_FILE)

def save_users(df):
    df.to_csv(USER_FILE, index=False)

def load_config():
    return pd.read_csv(CONFIG_FILE)

def save_config(jam):
    pd.DataFrame({"jam_masuk":[jam]}).to_csv(CONFIG_FILE, index=False)

# ================= PAGE =================
st.set_page_config("Absensi Digital Guru", layout="centered")

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
        users = load_users()
        user = users[(users.username==u) & (users.password==p)]
        if not user.empty:
            st.session_state.login = True
            st.session_state.user = u
            st.session_state.role = user.iloc[0]["role"]
            st.rerun()
        else:
            st.error("❌ Username / Password salah")

def logout():
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# ================= ADMIN =================
def admin_page():
    st.subheader("🧑‍💼 Admin Panel")

    # ===== JAM MASUK =====
    st.divider()
    st.subheader("⏰ Pengaturan Jam Masuk")

    cfg = load_config()
    jam_default = cfg.iloc[0]["jam_masuk"]
    jam_masuk = st.time_input(
        "Jam Masuk Sekolah",
        datetime.datetime.strptime(jam_default, "%H:%M").time()
    )

    if st.button("💾 Simpan Jam"):
        save_config(jam_masuk.strftime("%H:%M"))
        st.success("Jam masuk disimpan")

    # ===== QR =====
    st.divider()
    today = datetime.date.today()
    kode = f"ABSEN_GURU_{today}"
    st.code(kode)

    qr = qrcode.make(kode)
    qr.save(QR_PATH)
    st.image(QR_PATH, use_container_width=True)

    # ===== REKAP =====
    st.divider()
    st.subheader("📊 Rekap Absensi")

    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
        if list(df.columns) != COLUMNS:
            df = pd.DataFrame(columns=COLUMNS)

        st.dataframe(df, use_container_width=True)
        df.to_excel("rekap_absensi.xlsx", index=False)

        with open("rekap_absensi.xlsx","rb") as f:
            st.download_button("⬇️ Download Excel", f)
    else:
        st.info("Belum ada data")

    # ===== MANAJEMEN GURU =====
    st.divider()
    st.subheader("👥 Manajemen Guru")

    users = load_users()

    with st.expander("➕ Tambah Guru"):
        u = st.text_input("Username Guru Baru")
        p = st.text_input("Password Guru", type="password")
        if st.button("Tambah Guru"):
            if u == "":
                st.warning("Username kosong")
            elif u in users.username.values:
                st.error("Username sudah ada")
            else:
                users.loc[len(users)] = [u, p, "guru"]
                save_users(users)
                st.success("Guru ditambahkan")
                st.rerun()

    st.dataframe(users, use_container_width=True)

    guru_list = users[users.role=="guru"].username.tolist()
    if guru_list:
        g = st.selectbox("Pilih Guru", guru_list)
        new_pw = st.text_input("Password Baru", type="password")

        col1,col2 = st.columns(2)
        with col1:
            if st.button("✏️ Update Password"):
                users.loc[users.username==g,"password"] = new_pw
                save_users(users)
                st.success("Password diperbarui")
                st.rerun()
        with col2:
            if st.button("❌ Hapus Guru"):
                users = users[users.username!=g]
                save_users(users)
                st.warning("Guru dihapus")
                st.rerun()

# ================= GURU =================
def guru_page():
    st.subheader("👨‍🏫 Absensi Guru")

    batas = datetime.datetime.strptime(
        load_config().iloc[0]["jam_masuk"], "%H:%M"
    ).time()

    img = st.camera_input("📸 Scan QR")

    if not img:
        return

    decoded = decode(Image.open(img))
    if not decoded:
        st.error("❌ QR tidak terbaca")
        return

    today = str(datetime.date.today())
    now = datetime.datetime.now()
    now_str = now.strftime("%H:%M:%S")

    if decoded[0].data.decode() != f"ABSEN_GURU_{today}":
        st.error("❌ QR tidak valid")
        return

    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
        if list(df.columns) != COLUMNS:
            df = pd.DataFrame(columns=COLUMNS)
    else:
        df = pd.DataFrame(columns=COLUMNS)

    mask = (df["tanggal"]==today) & (df["guru"]==st.session_state.user)

    # ===== MASUK =====
    if not mask.any():
        status = "HADIR" if now.time() <= batas else "TERLAMBAT"
        df.loc[len(df)] = [today, st.session_state.user, now_str, "", status]
        st.success(f"✅ Absen MASUK ({status})")

    # ===== PULANG =====
    else:
        idx = df[mask].index[0]
        if df.loc[idx,"jam_pulang"] in ["", None] or pd.isna(df.loc[idx,"jam_pulang"]):
            df.loc[idx,"jam_pulang"] = now_str
            st.success("✅ Absen PULANG")
        else:
            st.warning("⚠️ Kamu sudah absen masuk & pulang")

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
