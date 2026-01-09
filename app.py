import streamlit as st
import pandas as pd
import datetime, os, math
from PIL import Image
from pyzbar.pyzbar import decode
import qrcode
import streamlit.components.v1 as components

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

# ================= GPS AUTO =================
def auto_gps():
    components.html("""
    <script>
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            window.parent.postMessage(
                {
                    lat: pos.coords.latitude,
                    lon: pos.coords.longitude
                },
                "*"
            );
        },
        () => {
            window.parent.postMessage({error: true}, "*");
        }
    );
    </script>
    """, height=0)

# ================= HELPERS =================
def load_users(): return pd.read_csv(USER_FILE)
def load_config(): return pd.read_csv(CONFIG_FILE)
def load_lokasi():
    d = pd.read_csv(LOKASI_FILE)
    return d.iloc[0]["latitude"], d.iloc[0]["longitude"], d.iloc[0]["radius"]

def hitung_jarak(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ================= PAGE =================
st.set_page_config("Absensi Guru", layout="centered")

if "login" not in st.session_state:
    st.session_state.update({
        "login": False,
        "user": "",
        "role": "",
        "lat": None,
        "lon": None
    })

# ================= LOGIN =================
def login_page():
    st.title("🔐 Login Absensi Guru")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        users = load_users()
        data = users[(users.username == u) & (users.password == p)]
        if not data.empty:
            st.session_state.update({
                "login": True,
                "user": u,
                "role": data.iloc[0]["role"]
            })
            st.rerun()
        else:
            st.error("❌ Login gagal")

def logout():
    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()

# ================= ADMIN =================
def admin_page():
    st.header("🧑‍💼 Admin Panel")

    # ---- LOKASI SEKOLAH ----
    st.subheader("📍 Lokasi Sekolah")
    lat, lon, rad = load_lokasi()
    nlat = st.number_input("Latitude", value=float(lat), format="%.6f")
    nlon = st.number_input("Longitude", value=float(lon), format="%.6f")
    nrad = st.number_input("Radius (meter)", 10, 1000, int(rad))

    if st.button("💾 Simpan Lokasi"):
        pd.DataFrame({
            "latitude":[nlat],
            "longitude":[nlon],
            "radius":[nrad]
        }).to_csv(LOKASI_FILE, index=False)
        st.success("Lokasi sekolah disimpan")

    # ---- JAM MASUK ----
    st.subheader("⏰ Jam Masuk")
    jam = st.time_input(
        "Jam Masuk",
        datetime.datetime.strptime(load_config().iloc[0]["jam_masuk"], "%H:%M").time()
    )
    if st.button("💾 Simpan Jam"):
        pd.DataFrame({"jam_masuk":[jam.strftime("%H:%M")]}).to_csv(CONFIG_FILE, index=False)
        st.success("Jam masuk disimpan")

    # ---- QR ----
    st.subheader("📎 QR Hari Ini")
    kode = f"ABSEN_GURU_{datetime.date.today()}"
    qrcode.make(kode).save(QR_PATH)
    st.image(QR_PATH)

    # ---- DATA ABSENSI ----
    st.subheader("📊 Data Absensi")
    if os.path.exists(ABSEN_FILE):
        df = pd.read_csv(ABSEN_FILE)
        st.dataframe(df, use_container_width=True)

        if st.button("🔥 Hapus Semua Absensi"):
            os.remove(ABSEN_FILE)
            st.warning("Semua data absensi dihapus")
            st.rerun()

# ================= GURU =================
def guru_page():
    st.header("👨‍🏫 Absensi Guru (AUTO GPS)")

    st.info("📍 Mengambil lokasi otomatis dari perangkat...")
    auto_gps()

    lat = st.session_state.lat
    lon = st.session_state.lon

    if lat is None or lon is None:
        st.warning("⏳ Menunggu izin lokasi...")
        return

    lat_s, lon_s, radius = load_lokasi()
    jarak = hitung_jarak(lat, lon, lat_s, lon_s)
    st.info(f"📏 Jarak ke sekolah: **{int(jarak)} meter**")

    if jarak > radius:
        st.error("❌ Kamu berada di luar radius sekolah")
        return

    img = st.camera_input("📸 Scan QR")
    if not img:
        return

    qr = decode(Image.open(img))
    if not qr or qr[0].data.decode() != f"ABSEN_GURU_{datetime.date.today()}":
        st.error("❌ QR tidak valid")
        return

    now = datetime.datetime.now()
    batas = datetime.datetime.strptime(load_config().iloc[0]["jam_masuk"], "%H:%M").time()
    status = "HADIR" if now.time() <= batas else "TERLAMBAT"

    df = pd.read_csv(ABSEN_FILE) if os.path.exists(ABSEN_FILE) else pd.DataFrame(columns=COLUMNS)
    mask = (df["tanggal"] == str(datetime.date.today())) & (df["guru"] == st.session_state.user)

    if not mask.any():
        df.loc[len(df)] = [
            str(datetime.date.today()),
            st.session_state.user,
            now.strftime("%H:%M:%S"),
            "",
            status
        ]
        st.success("✅ Absen MASUK berhasil")
    else:
        idx = df[mask].index[0]
        if df.loc[idx, "jam_pulang"] == "":
            df.loc[idx, "jam_pulang"] = now.strftime("%H:%M:%S")
            st.success("✅ Absen PULANG berhasil")
        else:
            st.warning("⚠️ Absensi sudah lengkap")

    df.to_csv(ABSEN_FILE, index=False)
    st.subheader("📋 Absensi Hari Ini")
    st.dataframe(df[df["tanggal"] == str(datetime.date.today())])

# ================= MAIN =================
if not st.session_state.login:
    login_page()
else:
    logout()
    st.markdown(f"👤 Login sebagai **{st.session_state.user}**")
    admin_page() if st.session_state.role == "admin" else guru_page()
