import streamlit as st
import pandas as pd
import datetime, os, math
from PIL import Image
from pyzbar.pyzbar import decode
import qrcode

# ================= CONFIG LOKASI =================
SEKOLAH_LAT = -7.446123     # GANTI
SEKOLAH_LON = 112.718456    # GANTI
RADIUS_METER = 50

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
        ]).to_csv(USER_FILE, index=False)

    if not os.path.exists(CONFIG_FILE):
        pd.DataFrame({"jam_masuk":["07:00"]}).to_csv(CONFIG_FILE, index=False)

init_files()

# ================= HELPERS =================
def load_users():
    return pd.read_csv(USER_FILE)

def load_config():
    return pd.read_csv(CONFIG_FILE)

def hitung_jarak(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ================= PAGE CONFIG =================
st.set_page_config("Absensi Guru", layout="centered")

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
        data = users[(users.username==u) & (users.password==p)]
        if not data.empty:
            st.session_state.login = True
            st.session_state.user = u
            st.session_state.role = data.iloc[0]["role"]
            st.rerun()
        else:
            st.error("❌ Login gagal")

def logout():
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# ================= ADMIN =================
def admin_page():
    st.subheader("🧑‍💼 Admin Panel")

    jam = st.time_input(
        "⏰ Jam Masuk",
        datetime.datetime.strptime(load_config().iloc[0]["jam_masuk"], "%H:%M").time()
    )

    if st.button("💾 Simpan Jam"):
        pd.DataFrame({"jam_masuk":[jam.strftime("%H:%M")]}).to_csv(CONFIG_FILE, index=False)
        st.success("Jam disimpan")

    today = datetime.date.today()
    kode = f"ABSEN_GURU_{today}"
    qrcode.make(kode).save(QR_PATH)
    st.image(QR_PATH)

    if os.path.exists(ABSEN_FILE):
        st.dataframe(pd.read_csv(ABSEN_FILE))

# ================= GURU =================
def guru_page():
    st.subheader("👨‍🏫 Absensi Guru (QR + Lokasi)")

    lat = st.number_input("Latitude", format="%.6f")
    lon = st.number_input("Longitude", format="%.6f")

    jarak = hitung_jarak(lat, lon, SEKOLAH_LAT, SEKOLAH_LON)
    st.info(f"📏 Jarak ke sekolah: {int(jarak)} meter")

    if jarak > RADIUS_METER:
        st.error("❌ Di luar radius absensi")
        return

    img = st.camera_input("📸 Scan QR")

    if not img:
        return

    decoded = decode(Image.open(img))
    if not decoded:
        st.error("QR tidak valid")
        return

    today = str(datetime.date.today())
    if decoded[0].data.decode() != f"ABSEN_GURU_{today}":
        st.error("QR salah")
        return

    now = datetime.datetime.now()
    batas = datetime.datetime.strptime(load_config().iloc[0]["jam_masuk"], "%H:%M").time()
    status = "HADIR" if now.time() <= batas else "TERLAMBAT"

    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
    else:
        df = pd.DataFrame(columns=COLUMNS)

    mask = (df["tanggal"]==today) & (df["guru"]==st.session_state.user)

    if not mask.any():
        df.loc[len(df)] = [today, st.session_state.user, now.strftime("%H:%M:%S"), "", status]
        st.success("✅ Absen masuk berhasil")
    else:
        idx = df[mask].index[0]
        if df.loc[idx,"jam_pulang"]=="":
            df.loc[idx,"jam_pulang"] = now.strftime("%H:%M:%S")
            st.success("✅ Absen pulang")
        else:
            st.warning("Sudah absen lengkap")

    df.to_csv(ABSEN_FILE, index=False)

# ================= MAIN =================
if not st.session_state.login:
    login_page()
else:
    logout()
    st.markdown(f"**Login:** `{st.session_state.user}`")

    if st.session_state.role == "admin":
        admin_page()
    else:
        guru_page()
