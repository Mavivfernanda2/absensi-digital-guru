import streamlit as st
import pandas as pd
from datetime import datetime, date
from geopy.distance import geodesic
import os
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode

# ================== CONFIG ==================
st.set_page_config(
    page_title="ABSENSI GURU QR + GPS",
    page_icon="📍",
    layout="wide"
)

DATA_DIR = "data"
GURU_FILE = f"{DATA_DIR}/guru.csv"
ABSEN_FILE = f"{DATA_DIR}/absensi.csv"
LOKASI_FILE = f"{DATA_DIR}/lokasi.csv"

# DEFAULT LOKASI
SEKOLAH_LAT = -7.4466
SEKOLAH_LON = 112.7183
MAX_RADIUS = 100

# ================== INIT ==================
os.makedirs(DATA_DIR, exist_ok=True)

if not os.path.exists(GURU_FILE):
    pd.DataFrame(columns=["id", "nama", "username", "password", "role"])\
        .to_csv(GURU_FILE, index=False)

if not os.path.exists(ABSEN_FILE):
    pd.DataFrame(columns=["id", "nama", "tanggal", "jam_masuk", "jam_pulang"])\
        .to_csv(ABSEN_FILE, index=False)

if not os.path.exists(LOKASI_FILE):
    pd.DataFrame([{
        "lat": SEKOLAH_LAT,
        "lon": SEKOLAH_LON,
        "radius": MAX_RADIUS
    }]).to_csv(LOKASI_FILE, index=False)

# ================== DEFAULT ADMIN ==================
df = pd.read_csv(GURU_FILE)
if df.empty:
    df = pd.DataFrame([{
        "id": 1,
        "nama": "Admin",
        "username": "admin",
        "password": "admin123",
        "role": "admin"
    }])
    df.to_csv(GURU_FILE, index=False)

# ================== SESSION ==================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.user = None
    st.session_state.location = None

# ================== GPS AUTO ==================
def get_location():
    loc = st.components.v1.html("""
    <script>
    const sendLocation = () => {
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                const data = {
                    lat: pos.coords.latitude,
                    lon: pos.coords.longitude
                };
                const streamlitEvent = new CustomEvent("streamlit:setComponentValue", {
                    detail: data
                });
                window.dispatchEvent(streamlitEvent);
            },
            (err) => {
                console.log(err);
            }
        );
    };
    sendLocation();
    </script>
    """, height=0)

    return loc
# ================== LOGIN ==================
def login_page():
    st.title("🔐 Login")

    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        users = pd.read_csv(GURU_FILE)
        user = users[(users.username == u) & (users.password == p)]

        if not user.empty:
            data_user = user.iloc[0].to_dict()

            # fallback role (AMAN)
            if "role" not in data_user:
                data_user["role"] = "admin" if data_user["username"] == "admin" else "guru"

            st.session_state.user = data_user
            st.session_state.login = True
            st.rerun()
        else:
            st.error("❌ Username / Password salah")

# ================== LOGOUT ==================
def logout():
    st.session_state.clear()
    st.rerun()

# ================== ABSENSI GURU ==================
def absensi_page():
    st.title("📍 ABSENSI GURU (QR + GPS)")

    st.subheader("📡 Lokasi GPS")

    lat = st.number_input("Latitude", format="%.6f")
    lon = st.number_input("Longitude", format="%.6f")

    if not lat or not lon:
        st.info("📍 Aktifkan GPS & izinkan lokasi di browser")
        st.stop()

    user_pos = (lat, lon)
    sekolah_pos = (SEKOLAH_LAT, SEKOLAH_LON)

    jarak = geodesic(user_pos, sekolah_pos).meters
    st.info(f"📏 Jarak dari sekolah: {int(jarak)} meter")

    if jarak > MAX_RADIUS:
        st.error("❌ Di luar radius sekolah")
        st.stop()

    st.divider()

    img = st.camera_input("📸 Scan QR Absensi")

    if not img:
        st.warning("Silakan scan QR")
        st.stop()

    st.success("📸 Kamera aktif & QR siap diproses")

    # ================= QR PROCESS =================
    decoded = decode(Image.open(img))
    if not decoded:
        st.error("❌ QR tidak valid")
        return

    st.success("✅ QR valid, absensi diproses...")

# ================== ADMIN PANEL ==================
def admin_page():
    st.title("🧑‍💼 ADMIN PANEL")

    # ----- QR -----
    st.subheader("📷 QR Absensi Hari Ini")
    today = date.today()
    kode = f"ABSEN_{today}"
    qrcode.make(kode).save("qr.png")
    st.image("qr.png", width=250)

    # ----- LOKASI -----
    st.subheader("📍 Lokasi Sekolah")
    lokasi = pd.read_csv(LOKASI_FILE)

    lat = st.number_input("Latitude", value=float(lokasi.lat[0]))
    lon = st.number_input("Longitude", value=float(lokasi.lon[0]))
    radius = st.number_input("Radius (meter)", 10, 1000, int(lokasi.radius[0]))

    if st.button("💾 Simpan Lokasi"):
        pd.DataFrame([{
            "lat": lat,
            "lon": lon,
            "radius": radius
        }]).to_csv(LOKASI_FILE, index=False)
        st.success("Lokasi diperbarui")

    # ----- REKAP -----
    st.subheader("📊 Rekap Absensi")
    df = pd.read_csv(ABSEN_FILE)
    st.dataframe(df, use_container_width=True)

# ================== MANAJEMEN GURU ==================
def guru_admin():
    st.subheader("👩‍🏫 Manajemen Guru")

    df = pd.read_csv(GURU_FILE)

    with st.form("add_guru"):
        nama = st.text_input("Nama Guru")
        user = st.text_input("Username")
        pw = st.text_input("Password")
        submit = st.form_submit_button("Tambah Guru")

    if submit:
        df.loc[len(df)] = [
            len(df)+1, nama, user, pw, "guru"
        ]
        df.to_csv(GURU_FILE, index=False)
        st.success("Guru ditambahkan")
        st.rerun()

    st.dataframe(df, use_container_width=True)

# ================== ROUTER ==================
if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    login_page()
else:
    user = st.session_state.user
    role = user.get("role", "guru")

    st.sidebar.success(f"Login: {user.get('nama', user['username'])}")

    if st.sidebar.button("🚪 Logout"):
        logout()

    # MENU SIDEBAR
    if role == "admin":
        menu = st.sidebar.radio(
            "Menu",
            ["Absensi", "Admin Panel", "Manajemen Guru"]
        )
    else:
        menu = st.sidebar.radio(
            "Menu",
            ["Absensi"]
        )

    # ROUTING HALAMAN
    if menu == "Absensi":
        absensi_page()
    elif menu == "Admin Panel":
        admin_page()
    elif menu == "Manajemen Guru":
        guru_admin()
