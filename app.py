# ===============================
# ABSENSI WEB GURU – FINAL READY
# Streamlit App (LOGIN • ADMIN • GURU • LOKASI • QR • RADIUS)
# ===============================

import streamlit as st
import pandas as pd
import os, datetime, math
import qrcode
from PIL import Image
from pyzbar.pyzbar import decode

# ===============================
# KONFIGURASI FILE
# ===============================
USER_FILE   = "users.csv"
ABSEN_FILE  = "absensi.csv"
CONFIG_FILE = "config.csv"
LOKASI_FILE = "lokasi.csv"
QR_PATH     = "qr_absen.png"

COLUMNS = ["tanggal","guru","jam_masuk","jam_pulang","status"]

# ===============================
# INIT FILE
# ===============================

def init_files():
    if not os.path.exists(USER_FILE):
        pd.DataFrame([
            {"username":"admin","password":"admin123","role":"admin"},
            {"username":"guru01","password":"guru123","role":"guru"}
        ]).to_csv(USER_FILE, index=False)

    if not os.path.exists(CONFIG_FILE):
        pd.DataFrame({"jam_masuk":["07:00"]}).to_csv(CONFIG_FILE, index=False)

    if not os.path.exists(LOKASI_FILE):
        pd.DataFrame({
            "latitude":[-7.446123],
            "longitude":[112.718456],
            "radius":[50]
        }).to_csv(LOKASI_FILE, index=False)

# ===============================
# UTIL
# ===============================

def load_config():
    return pd.read_csv(CONFIG_FILE)

def load_lokasi():
    df = pd.read_csv(LOKASI_FILE)
    return df.iloc[0]["latitude"], df.iloc[0]["longitude"], df.iloc[0]["radius"]

def hitung_jarak(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2-lat1)
    dlambda = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

# ===============================
# LOGIN
# ===============================

def login():
    st.title("🔐 Login Absensi Guru")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        df = pd.read_csv(USER_FILE)
        cek = df[(df.username==u) & (df.password==p)]
        if not cek.empty:
            st.session_state.user = u
            st.session_state.role = cek.iloc[0]["role"]
            st.success("Login berhasil")
            st.rerun()
        else:
            st.error("Username atau password salah")

# ===============================
# ADMIN PAGE
# ===============================

def admin_page():
    st.subheader("🧑‍💼 Admin Panel")

    # JAM MASUK
    st.divider()
    cfg = load_config()
    jam = datetime.datetime.strptime(cfg.iloc[0]["jam_masuk"], "%H:%M").time()
    jam_baru = st.time_input("⏰ Jam Masuk Sekolah", jam)

    if st.button("💾 Simpan Jam"):
        pd.DataFrame({"jam_masuk":[jam_baru.strftime("%H:%M")]}).to_csv(CONFIG_FILE, index=False)
        st.success("Jam masuk disimpan")

    # LOKASI SEKOLAH
    st.divider()
    st.subheader("📍 Lokasi Sekolah")
    lat, lon, radius = load_lokasi()

    new_lat = st.number_input("Latitude", value=float(lat), format="%.6f")
    new_lon = st.number_input("Longitude", value=float(lon), format="%.6f")
    new_radius = st.number_input("Radius (meter)", 10, 1000, int(radius))

    if st.button("💾 Simpan Lokasi"):
        pd.DataFrame({
            "latitude":[new_lat],
            "longitude":[new_lon],
            "radius":[new_radius]
        }).to_csv(LOKASI_FILE, index=False)
        st.success("Lokasi sekolah disimpan")

    # QR CODE
    st.divider()
    kode = f"ABSEN_GURU_{datetime.date.today()}"
    qrcode.make(kode).save(QR_PATH)
    st.image(QR_PATH, caption="QR Absen Hari Ini", use_container_width=True)

# ===============================
# GURU PAGE
# ===============================

def guru_page():
    st.subheader("👨‍🏫 Absensi Guru")

    lat_sekolah, lon_sekolah, radius = load_lokasi()

    lat = st.number_input("Latitude Anda", format="%.6f")
    lon = st.number_input("Longitude Anda", format="%.6f")

    jarak = hitung_jarak(lat, lon, lat_sekolah, lon_sekolah)
    st.info(f"📏 Jarak ke sekolah: {int(jarak)} meter")

    if jarak > radius:
        st.error("❌ Anda berada di luar radius sekolah")
        return

    img = st.camera_input("📸 Scan QR Absen")
    if not img:
        return

    decoded = decode(Image.open(img))
    if not decoded:
        st.error("QR tidak terbaca")
        return

    today = str(datetime.date.today())
    if decoded[0].data.decode() != f"ABSEN_GURU_{today}":
        st.error("QR tidak valid")
        return

    now = datetime.datetime.now()
    batas = datetime.datetime.strptime(load_config().iloc[0]["jam_masuk"], "%H:%M").time()
    status = "HADIR" if now.time() <= batas else "TERLAMBAT"

    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
    else:
        df = pd.DataFrame(columns=COLUMNS)

    mask = (df.tanggal==today) & (df.guru==st.session_state.user)

    if not mask.any():
        df.loc[len(df)] = [today, st.session_state.user, now.strftime("%H:%M:%S"), "", status]
        st.success("✅ Absen masuk berhasil")
    else:
        idx = df[mask].index[0]
        if df.loc[idx, "jam_pulang"] == "":
            df.loc[idx, "jam_pulang"] = now.strftime("%H:%M:%S")
            st.success("✅ Absen pulang berhasil")
        else:
            st.warning("Sudah absen lengkap")

    df.to_csv(ABSEN_FILE, index=False)

# ===============================
# MAIN
# ===============================

st.set_page_config(page_title="Absensi Guru", layout="centered")
init_files()

if "user" not in st.session_state:
    login()
else:
    st.sidebar.success(f"Login: {st.session_state.user}")
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.role == "admin":
        admin_page()
    else:
        guru_page()
