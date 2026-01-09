import streamlit as st
import pandas as pd
import datetime, os, math
from PIL import Image
from pyzbar.pyzbar import decode
import qrcode

# ================= FILE =================
USER_FILE = "users.csv"
ABSEN_FILE = "absensi.csv"
CONFIG_FILE = "config.csv"
LOKASI_FILE = "lokasi.csv"
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

    if not os.path.exists(LOKASI_FILE):
        pd.DataFrame({
            "latitude":[-7.446123],
            "longitude":[112.718456],
            "radius":[100]
        }).to_csv(LOKASI_FILE, index=False)

init_files()

# ================= HELPERS =================
def load_users():
    return pd.read_csv(USER_FILE)

def load_config():
    return pd.read_csv(CONFIG_FILE)

def load_lokasi():
    df = pd.read_csv(LOKASI_FILE)
    return df.iloc[0]["latitude"], df.iloc[0]["longitude"], df.iloc[0]["radius"]

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
            st.error("❌ Username / Password salah")

def logout():
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# ================= ADMIN =================
def admin_page():
    st.subheader("🧑‍💼 Admin Panel")

    # ---- LOKASI ----
    st.divider()
    st.subheader("📍 Lokasi Sekolah")
    lat, lon, radius = load_lokasi()

    new_lat = st.number_input("Latitude", value=float(lat), format="%.6f")
    new_lon = st.number_input("Longitude", value=float(lon), format="%.6f")
    new_radius = st.number_input("Radius (meter)", min_value=10, max_value=1000, value=int(radius))

    if st.button("💾 Simpan Lokasi"):
        pd.DataFrame({
            "latitude":[new_lat],
            "longitude":[new_lon],
            "radius":[new_radius]
        }).to_csv(LOKASI_FILE, index=False)
        st.success("Lokasi disimpan")

    # ---- JAM MASUK ----
    st.divider()
    cfg = load_config()
    jam_default = cfg.iloc[0]["jam_masuk"]

    jam = st.time_input(
        "Jam Masuk",
        datetime.datetime.strptime(jam_default, "%H:%M").time()
    )

    if st.button("💾 Simpan Jam"):
        pd.DataFrame({"jam_masuk":[jam.strftime("%H:%M")]}).to_csv(CONFIG_FILE, index=False)
        st.success("Jam masuk disimpan")

    # ---- QR ----
    st.divider()
    today = datetime.date.today()
    kode = f"ABSEN_GURU_{today}"
    qrcode.make(kode).save(QR_PATH)
    st.image(QR_PATH, use_container_width=True)

    # ---- REKAP ----
    st.divider()
    st.subheader("📊 Rekap Absensi")

    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
        st.dataframe(df, use_container_width=True)
        df.to_excel("rekap_absensi.xlsx", index=False)
        with open("rekap_absensi.xlsx","rb") as f:
            st.download_button("⬇️ Download Excel", f)

    # ---- GURU ----
    st.divider()
    st.subheader("👥 Manajemen Guru")
    users = load_users()

    with st.expander("➕ Tambah Guru"):
        u = st.text_input("Username Guru")
        p = st.text_input("Password", type="password")
        if st.button("Tambah"):
            if u in users.username.values:
                st.error("Username sudah ada")
            else:
                users.loc[len(users)] = [u,p,"guru"]
                users.to_csv(USER_FILE, index=False)
                st.success("Guru ditambahkan")
                st.rerun()

    st.dataframe(users, use_container_width=True)

# ================= GURU =================
def guru_page():
    st.subheader("👨‍🏫 Absensi Guru")

    lat_s, lon_s, radius = load_lokasi()

    lat_u = st.number_input("Latitude Anda", format="%.6f")
    lon_u = st.number_input("Longitude Anda", format="%.6f")

    jarak = hitung_jarak(lat_u, lon_u, lat_s, lon_s)
    st.info(f"📏 Jarak ke sekolah: {int(jarak)} meter")

    if jarak > radius:
        st.error("❌ Di luar radius sekolah")
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
        st.error("QR tidak sesuai hari ini")
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
        if df.loc[idx,"jam_pulang"] == "":
            df.loc[idx,"jam_pulang"] = now.strftime("%H:%M:%S")
            st.success("✅ Absen pulang berhasil")
        else:
            st.warning("⚠️ Absensi sudah lengkap")

    df.to_csv(ABSEN_FILE, index=False)

    st.subheader("📋 Absensi Hari Ini")
    st.dataframe(df[df["tanggal"]==today], use_container_width=True)

# ================= MAIN =================
if not st.session_state.login:
    login_page()
else:
    logout()
    st.write(f"👤 Login sebagai: **{st.session_state.user}**")

    if st.session_state.role == "admin":
        admin_page()
    else:
        guru_page()
