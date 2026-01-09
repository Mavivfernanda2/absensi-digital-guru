import streamlit as st
import pandas as pd
from datetime import datetime, date
from geopy.distance import geodesic
import os
import qrcode

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
    st.components.v1.html("""
    <script>
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            window.parent.postMessage({
                lat: pos.coords.latitude,
                lon: pos.coords.longitude
            }, "*");
        }
    );
    </script>
    """, height=0)

# ================== LOGIN ==================
def login_page():
    st.title("🔐 Login Guru")

    with st.form("login_form"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        df = pd.read_csv(GURU_FILE)
        user = df[(df.username == u) & (df.password == p)]
        if not user.empty:
            st.session_state.login = True
            st.session_state.user = user.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Username / Password salah")

# ================== LOGOUT ==================
def logout():
    st.session_state.clear()
    st.rerun()

# ================== ABSENSI GURU ==================
def absensi_page():
    st.title("📍 ABSENSI QR + GPS")

    get_location()

    if st.session_state.location is None:
        st.warning("📡 Mengambil lokasi GPS...")
        st.stop()

    lokasi = pd.read_csv(LOKASI_FILE).iloc[0]
    sekolah_pos = (lokasi.lat, lokasi.lon)
    user_pos = (st.session_state.location["lat"], st.session_state.location["lon"])

    jarak = geodesic(user_pos, sekolah_pos).meters
    st.info(f"📏 Jarak ke sekolah: {int(jarak)} meter")

    if jarak > lokasi.radius:
        st.error("❌ Di luar radius absensi")
        st.stop()

    guru = st.session_state.user
    today = date.today().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M:%S")

    df = pd.read_csv(ABSEN_FILE)
    row = df[(df.id == guru["id"]) & (df.tanggal == today)]

    col1, col2 = st.columns(2)

    if row.empty:
        if col1.button("✅ ABSEN MASUK"):
            df.loc[len(df)] = [
                guru["id"], guru["nama"], today, now, ""
            ]
            df.to_csv(ABSEN_FILE, index=False)
            st.success("Absen masuk berhasil")
            st.rerun()
    else:
        if row.iloc[0]["jam_pulang"] == "":
            if col2.button("🚪 ABSEN PULANG"):
                df.loc[row.index, "jam_pulang"] = now
                df.to_csv(ABSEN_FILE, index=False)
                st.success("Absen pulang berhasil")
                st.rerun()
        else:
            st.success("✔ Absensi hari ini sudah lengkap")

    st.subheader("📋 Absensi Hari Ini")
    st.dataframe(df[df.tanggal == today], use_container_width=True)

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
if not st.session_state.login:
    login_page()
else:
    st.sidebar.success(f"Login: {st.session_state.user['nama']}")
    if st.sidebar.button("Logout"):
        logout()

    role = st.session_state.user["role"]

    menu = st.sidebar.radio(
        "Menu",
        ["Absensi", "Admin Panel", "Manajemen Guru"]
        if role == "admin" else ["Absensi"]
    )

    if menu == "Absensi":
        absensi_page()
    elif menu == "Admin Panel":
        admin_page()
    else:
        guru_admin()
