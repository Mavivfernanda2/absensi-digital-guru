import streamlit as st
from PIL import Image
from pyzbar.pyzbar import decode
import datetime

st.set_page_config(page_title="Absensi Guru", layout="centered")

st.title("📸 Absensi Guru - Scan QR")

img = st.camera_input("Scan QR Absensi")

if img:
    image = Image.open(img)
    decoded = decode(image)

    if decoded:
        qr_data = decoded[0].data.decode("utf-8")

        if qr_data.startswith("ABSEN_GURU"):
            waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.success("✅ Absensi Berhasil")
            st.write("🕒 Waktu:", waktu)
        else:
            st.error("❌ QR tidak valid")
