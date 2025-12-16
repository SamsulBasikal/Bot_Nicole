import streamlit as st
import os
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import json
from datetime import datetime
import pytz

#up up
st.set_page_config(
    page_title="Nicole Orithyia", 
    page_icon="avatar.png", 
    layout="wide"
)

bot_icon = Image.open("avatar.png") 

#setup firebase
if not firebase_admin._apps:
    try:
        snapshot = os.getenv("FIREBASE_CREDENTIALS")
        
        if snapshot:
            key_dict = json.loads(snapshot)
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
        else:
            st.error("Variable FIREBASE_CREDENTIALS belum disetting di Railway!")
            st.stop()
            
    except Exception as e:
        st.error(f"Gagal Login Firebase: {e}")
        st.stop()

db = firestore.client()

#setup groq
api_key_groq = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key_groq)

#2.hard data code
def get_info_akademik():
    """
    Untuk umum/hardcode(don't use database)menyimpan informasi umum.
    """
    info = """
    PANDUAN AKADEMIK KAMPUS:
    1. CARA ISI KRS:
       - Login ke website 'student.amikompurwokerto.ac.id'.
       - Pilih menu 'Akademik' -> 'Pengajuan'.
       - Pilih mata kuliah yang ingin diambil.
       - Klik 'Simpan' dan tunggu teraktivitasi.
    2. Cara Validasi Kehadiran:
       - Login ke website 'student.amikompurwokerto.ac.id'.
       - Pilih menu 'Proses Pembelajaran' -> 'Kehadiran'.
       - Pilih Tahun ajaran,Semester,dan Mata kuliah.
       - Klik Logo atau ikon B dan validasi.
    """
    return info


#3.database firebase
def cari_mahasiswa(nama_panggilan):
    """doc doc mahasigma"""
    doc_ref = db.collection('mahasiswa').document(nama_panggilan)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        return f"Nama: {data.get('nama')}, Kelas: {data.get('kelas')}"
    return None

def cari_jadwal(hari):
    """jadwal mata kuliah"""
    doc_ref = db.collection('jadwal').document(hari)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        return f"Jadwal {hari.capitalize()}: {data.get('matkul')}"
    return None

#4.LLM PROCESSING
def tanya_ai(prompt_user, context_data):
    zona_wib = pytz.timezone('Asia/Jakarta')
    now = datetime.now(zona_wib)
    
    hari_dict = {
        "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
        "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
    }
    hari_ini = hari_dict[now.strftime("%A")]
    tanggal = now.strftime("%d %B %Y")
    jam = now.strftime("%H:%M")

    info_umum = get_info_akademik()
    
    #be carefull
    system_prompt = f"""
    Kamu adalah Asisten Kampus yang bernama Nicole Orithyia,kamu merupakan 
    asisten yang ramah dan sangat suka membantu.Selain itu kamu suka membalas pertanyaan dengan kalimat sastra yang indah.
    
    Kamu bisa memahami informasi waktu dan hari dengan mengambil data dari sistem:
    - Hari ini: {hari_ini}
    - Tanggal: {tanggal}
    - Jam: {jam} WIB

    SUMBER DATA KAMU:
    1. Data Database: {context_data}
    2. Panduan Kampus: {info_umum}
    
    INSTRUKSI:
    - Jawablah berdasarkan sumber data di atas.
    - Jika user tanya cara KRS/Website student bekerja,ambil dari 'Panduan Kampus'.
    - Jawab dengan kata kata sopan.
    - Jika user bercanda,kamu boleh bercanda juga.
    - Jika tidak tahu jawabannya,katakan 'Maaf saya tidak tahu.'
    - Gunakan bahasa Indonesia yang baik dan benar.
    - Jangan buat-buat informasi yang tidak ada di sumber data.
    - Jangan berikan saran medis, hukum, atau keuangan.
    - Jangan gunakan bahasa atau kata kata yang aneh dan susah dipahami.
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_user}
            ],
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Maaf,sedang error: {e}"

# 5. TAMPILAN
st.markdown("""
<style>
    .block-container {
        padding-bottom: 120px;
    }
    
    .stChatInput {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        padding: 20px;
        background-color: var(--background-color); 
        
        z-index: 999;
        border-top: 1px solid #333;
    }
      
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image(bot_icon, width=150) 
    st.title("Nicole Orithyia Siap Membantu!")
    st.info("Tips:Ketik 'Info mahasiswa' atau 'Jadwal Senin'.")
    
    st.markdown("---")
    if st.button("Bersihkan Chat"):
        st.session_state.messages = []
        st.rerun()

st.title("Nicole Orithyia")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo👋 Saya Nicole Orithyia. Ada yang bisa saya bantu?"}
    ]

#chat
for message in st.session_state.messages:
    if message["role"] == "user":
        role_label = "Mahasiswa"
        avatar_icon = "👤"
    else:
        role_label = "Nicole"
        avatar_icon = bot_icon
    
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.write(f"**{role_label}**") 
        st.markdown(message["content"])

prompt = st.chat_input("Ketik pesan di sini...")

if prompt:
    with st.chat_message("user", avatar="👤"):
        st.write("**Mahasiswa**")
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    pesan_lower = prompt.lower()
    context_data = ""

    # Logika Cek jadwal firebase
    if "jadwal" in pesan_lower:
        hari_list = ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu"]
        found_hari = next((h for h in hari_list if h in pesan_lower), None)
        context_data = f"Info Jadwal: {cari_jadwal(found_hari)}" if found_hari else "Sebutkan harinya."
        
    elif "info" in pesan_lower:
        # Logika Cek nama firebase info [nama]
        nama = pesan_lower.replace("info", "").strip()
        context_data = f"Info Mahasiswa: {cari_mahasiswa(nama)}"

    # 3. Kirim ke AI
    jawaban = tanya_ai(prompt, context_data)
    
    # Tampilkan Jawaban Bot
    with st.chat_message("assistant", avatar=bot_icon):
        st.write("**Nicole**")
        st.markdown(jawaban)
    st.session_state.messages.append({"role": "assistant", "content": jawaban})