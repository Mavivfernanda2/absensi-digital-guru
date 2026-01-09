import streamlit as st
import pandas as pd
from datetime import datetime, date
from geopy.distance import geodesic
import os

# ================== CONFIG ==================
st.set_page_config(
    page_title="ABSENSI GURU GPS",
    page_icon="📍",
    layout="wide"
)

DATA_DIR = "data"
GURU_FILE = f"{DATA_DIR}/guru.csv"
ABSEN_FILE = f"{DATA_DIR}/absensi.csv"
LOKASI_FILE = f"{DATA_DIR}/lokasi.csv"

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
        "lat": -7.4466,
        "lon": 112.7183,
        "radius": 100
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

# ================== LOGIN ==================
def login_page():
    st.title("🔐 Login Guru")

    with st.form("login_form"):  # ⬅️ GANTI DI SINI
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

    if submit:
        df = pd.read_csv(GURU_FILE)
        user = df[(df.username == u) & (df.password == p)]

        if user.empty:
            st.error("❌ Username / Password salah")
        else:
            data_user = user.iloc[0].to_dict()
            data_user.setdefault(
                "role",
                "admin" if data_user["username"] == "admin" else "guru"
            )
            st.session_state.user = data_user
            st.session_state.login = True
            st.rerun()

# ================== LOGOUT ==================
def logout():
    st.session_state.clear()
    st.rerun()

# ================== ABSENSI ==================
def absensi_page():
    st.title("📍 ABSENSI GURU")

    guru = st.session_state.user
    today = date.today().isoformat()
    now = datetime.now().strftime("%H:%M:%S")

    df = pd.read_csv(ABSEN_FILE)

    data_hari_ini = df[
        (df["id"] == guru["id"]) &
        (df["tanggal"] == today)
    ]

    col1, col2 = st.columns(2)

    if data_hari_ini.empty:
        if col1.button("✅ ABSEN MASUK"):
            df.loc[len(df)] = [
                guru["id"],
                guru["nama"],
                today,
                now,
                ""
            ]
            df.to_csv(ABSEN_FILE, index=False)
            st.success("Absen masuk berhasil")
            st.rerun()
    else:
        if data_hari_ini.iloc[0]["jam_pulang"] == "":
            if col2.button("🚪 ABSEN PULANG"):
                idx = data_hari_ini.index[0]
                df.loc[idx, "jam_pulang"] = now
                df.to_csv(ABSEN_FILE, index=False)
                st.success("Absen pulang berhasil")
                st.rerun()
        else:
            st.success("✔ Anda sudah absen masuk & pulang hari ini")

    st.subheader("📋 Absensi Hari Ini")
    st.dataframe(df[df["tanggal"] == today], use_container_width=True)

# ================== ADMIN PANEL ==================
def admin_page():
    st.title("🧑‍💼 ADMIN PANEL")

    st.subheader("📍 Pengaturan Lokasi Sekolah")
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

    st.subheader("📊 Rekap Absensi")
    st.dataframe(pd.read_csv(ABSEN_FILE), use_container_width=True)

# ================== MANAJEMEN GURU ==================
def guru_admin():
    st.title("👩‍🏫 Manajemen Guru")

    df = pd.read_csv(GURU_FILE)

    with st.form("add_guru"):
        nama = st.text_input("Nama Guru")
        user = st.text_input("Username")
        pw = st.text_input("Password")
        submit = st.form_submit_button("Tambah Guru")

    if submit:
        df.loc[len(df)] = [
            len(df) + 1, nama, user, pw, "guru"
        ]
        df.to_csv(GURU_FILE, index=False)
        st.success("Guru ditambahkan")
        st.rerun()

    st.dataframe(df, use_container_width=True)

# ================== ROUTER ==================
if not st.session_state.login:
    login_page()
else:
    user = st.session_state.user
    role = user.get("role", "guru")

    st.sidebar.success(f"Login: {user['nama']}")
    if st.sidebar.button("🚪 Logout"):
        logout()

    if role == "admin":
        menu = st.sidebar.radio(
            "Menu",
            ["Absensi", "Admin Panel", "Manajemen Guru"]
        )
    else:
        menu = st.sidebar.radio("Menu", ["Absensi"])

    if menu == "Absensi":
        absensi_page()
    elif menu == "Admin Panel":
        admin_page()
    elif menu == "Manajemen Guru":
        guru_admin()
