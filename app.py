import streamlit as st
import pandas as pd
from datetime import datetime
from geopy.distance import geodesic
import os

# ================== CONFIG ==================
st.set_page_config(
    page_title="ABSENSI GURU QR + GPS",
    page_icon="📍",
    layout="wide"
)

DATA_DIR = "data"
GURU_FILE = f"{DATA_DIR}/guru.csv"
id,nama,username,password
1,Admin Guru,admin,admin123

ABSEN_FILE = f"{DATA_DIR}/absensi.csv"

SEKOLAH_LAT = -7.4466   # LAT SEKOLAH
SEKOLAH_LON = 112.7183  # LON SEKOLAH
MAX_RADIUS = 100        # meter

# ================== INIT ==================
os.makedirs(DATA_DIR, exist_ok=True)

if not os.path.exists(GURU_FILE):
    pd.DataFrame(columns=["id", "nama", "username", "password"]).to_csv(GURU_FILE, index=False)

if not os.path.exists(ABSEN_FILE):
    pd.DataFrame(columns=["id", "nama", "tanggal", "jam_masuk", "jam_pulang"]).to_csv(ABSEN_FILE, index=False)

# ================== SESSION ==================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.user = None

# ================== GPS AUTO ==================
def get_location():
    st.components.v1.html("""
    <script>
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const lat = pos.coords.latitude;
            const lon = pos.coords.longitude;
            window.parent.postMessage(
                {lat: lat, lon: lon},
                "*"
            );
        }
    );
    </script>
    """, height=0)

    loc = st.session_state.get("location")
    return loc

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
    st.session_state.login = False
    st.session_state.user = None
    st.rerun()

# ================== ABSENSI ==================
def absensi_page():
    st.title("📍 ABSENSI QR + GPS")

    get_location()
    location = st.session_state.get("location")

    if not location:
        st.warning("Mengambil lokasi GPS...")
        st.stop()

    user_pos = (location["lat"], location["lon"])
    sekolah_pos = (SEKOLAH_LAT, SEKOLAH_LON)

    jarak = geodesic(user_pos, sekolah_pos).meters

    st.info(f"📏 Jarak dari sekolah: {int(jarak)} meter")

    if jarak > MAX_RADIUS:
        st.error("❌ Anda di luar area absensi")
        st.stop()

    guru = st.session_state.user
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M:%S")

    df = pd.read_csv(ABSEN_FILE)
    row = df[(df.id == guru["id"]) & (df.tanggal == today)]

    col1, col2 = st.columns(2)

    if row.empty:
        if col1.button("✅ ABSEN MASUK"):
            new = {
                "id": guru["id"],
                "nama": guru["nama"],
                "tanggal": today,
                "jam_masuk": now,
                "jam_pulang": ""
            }
            df = pd.concat([df, pd.DataFrame([new])])
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
            st.success("✔ Anda sudah absen lengkap hari ini")

    st.subheader("📋 TABEL ABSENSI HARI INI")
    st.dataframe(df[df.tanggal == today], use_container_width=True)

# ================== ADMIN GURU ==================
def guru_admin():
    st.title("👩‍🏫 Manajemen Guru")

    df = pd.read_csv(GURU_FILE)

    with st.form("add_guru"):
        nama = st.text_input("Nama Guru")
        user = st.text_input("Username")
        pw = st.text_input("Password")
        add = st.form_submit_button("Tambah Guru")

    if add:
        new = {
            "id": len(df) + 1,
            "nama": nama,
            "username": user,
            "password": pw
        }
        df = pd.concat([df, pd.DataFrame([new])])
        df.to_csv(GURU_FILE, index=False)
        st.success("Guru ditambahkan")
        st.rerun()

    st.subheader("📋 Data Guru")
    st.dataframe(df)

    del_id = st.number_input("ID Guru yang dihapus", step=1)
    if st.button("🗑 Hapus Guru"):
        df = df[df.id != del_id]
        df.to_csv(GURU_FILE, index=False)
        st.success("Guru dihapus")
        st.rerun()

# ================== ROUTER ==================
if not st.session_state.login:
    login_page()
else:
    st.sidebar.success(f"Login: {st.session_state.user['nama']}")
    if st.sidebar.button("Logout"):
        logout()

    menu = st.sidebar.radio("Menu", ["Absensi", "Manajemen Guru"])

    if menu == "Absensi":
        absensi_page()
    else:
        guru_admin()
