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

# ================= LOADERS =================
def load_users():
    return pd.read_csv(USER_FILE)

def save_users(df):
    df.to_csv(USER_FILE, index=False)

def load_config():
    return pd.read_csv(CONFIG_FILE)

def save_config(jam):
    pd.DataFrame({"jam_masuk":[jam]}).to_csv(CONFIG_FILE, index=False)

# ================= PAGE CONFIG =================
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

    # ================= JAM MASUK =================
    st.divider()
    st.subheader("⏰ Pengaturan Jam Masuk")

    cfg = load_config()
    jam_default = cfg.iloc[0]["jam_masuk"]

    jam_masuk = st.time_input(
        "Jam Masuk Sekolah",
        datetime.datetime.strptime(jam_default, "%H:%M").time()
    )

    if st.button("💾 Simpan Jam Masuk"):
        save_config(jam_masuk.strftime("%H:%M"))
        st.success("Jam masuk berhasil disimpan")

    # ================= REKAP =================
    st.divider()
    st.subheader("📊 Rekap Absensi")

    if os.path.exists(ABSEN_FILE):
        df_absen = pd.read_csv(ABSEN_FILE)
        st.dataframe(df_absen, use_container_width=True)

        df_absen.to_excel("rekap_absensi.xlsx", index=False)
        with open("rekap_absensi.xlsx", "rb") as f:
            st.download_button(
                "⬇️ Download Rekap Excel",
                f,
                file_name="rekap_absensi.xlsx"
            )
    else:
        st.info("Belum ada data absensi")

    # ================= MANAJEMEN GURU =================
    st.divider()
    st.subheader("👥 Manajemen Guru")

    users = load_users()

    # ===== TAMBAH GURU =====
    with st.expander("➕ Tambah Guru"):
        new_user = st.text_input("Username Guru Baru")
        new_pass = st.text_input("Password Guru", type="password")

        if st.button("Tambah Guru"):
            if new_user == "":
                st.warning("Username tidak boleh kosong")
            elif new_user in users.username.values:
                st.error("Username sudah ada")
            else:
                users.loc[len(users)] = [new_user, new_pass, "guru"]
                save_users(users)
                st.success("Guru berhasil ditambahkan")
                st.rerun()

    # ===== DAFTAR USER =====
    st.dataframe(users, use_container_width=True)

    # ===== EDIT / HAPUS =====
    guru_list = users[users.role == "guru"].username.tolist()

    if guru_list:
        selected = st.selectbox("Pilih Guru", guru_list)
        new_pw = st.text_input("Password Baru", type="password")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✏️ Update Password"):
                users.loc[users.username == selected, "password"] = new_pw
                save_users(users)
                st.success("Password guru diperbarui")
                st.rerun()

        with col2:
            if st.button("❌ Hapus Guru"):
                users = users[users.username != selected]
                save_users(users)
                st.warning("Guru berhasil dihapus")
                st.rerun()


    # === QR ===
    st.divider()
    today = datetime.date.today()
    kode = f"ABSEN_GURU_{today}"

    st.code(kode)
    qr = qrcode.make(kode)
    qr.save(QR_PATH)
    st.image(QR_PATH, use_container_width=True)

    # === REKAP ===
    st.divider()
    st.subheader("📊 Rekap Absensi")

    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
        st.dataframe(df, use_container_width=True)
        df.to_excel("rekap_absensi.xlsx", index=False)
        with open("rekap_absensi.xlsx","rb") as f:
            st.download_button("⬇️ Download Excel", f)
    else:
        st.info("Belum ada data")

    # === GURU ===
    st.divider()
    st.subheader("👥 Manajemen Guru")
    users = load_users()
    st.dataframe(users)

# ================= GURU =================
def guru_page():
    st.subheader("👨‍🏫 Absensi Guru")

    cfg = load_config()
    batas = datetime.datetime.strptime(cfg.iloc[0]["jam_masuk"],"%H:%M").time()

    img = st.camera_input("📸 Scan QR")

    if not img:
        return

    image = Image.open(img)
    decoded = decode(image)

    if not decoded:
        st.error("QR tidak terbaca")
        return

    today = str(datetime.date.today())
    now = datetime.datetime.now()
    now_str = now.strftime("%H:%M:%S")

    if decoded[0].data.decode() != f"ABSEN_GURU_{today}":
        st.error("QR tidak valid")
        return

    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
    else:
        df = pd.DataFrame(columns=COLUMNS)

    mask = (df["tanggal"]==today) & (df["guru"]==st.session_state.user)

    # ===== MASUK =====
    if now.time() <= batas:
        status = "HADIR"
        if mask.any():
            st.warning("Sudah absen masuk")
        else:
            df.loc[len(df)] = [today, st.session_state.user, now_str, "", status]
            st.success(f"✅ Absen Masuk ({status})")

    # ===== PULANG =====
    else:
        if not mask.any():
            st.warning("Belum absen masuk")
        else:
            idx = df[mask].index[0]
            if df.loc[idx,"jam_pulang"]=="" or pd.isna(df.loc[idx,"jam_pulang"]):
                df.loc[idx,"jam_pulang"] = now_str
                st.success("✅ Absen Pulang")
            else:
                st.warning("Sudah absen pulang")

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
