"""Halaman login, logout, dan kartu akun pada sidebar."""

from pathlib import Path

import streamlit as st

from database import get_client, bersihkan_cache

# Lokasi logo: dicari di folder yang sama dengan file ini, jadi aman dari mana pun
# aplikasi dijalankan. Nama file harus persis "logo.png" (tanpa spasi).
LOGO = Path(__file__).parent / "logo .png"


def tampilkan_logo(lebar):
    """Tampilkan gambar logo. Jika file tidak ditemukan, tampilkan emoji supaya aplikasi tidak error."""
    if LOGO.exists():
        st.image(str(LOGO), width=lebar)
    else:
        st.image("logo. png", width=160)


# =====================================================================
# 5. LOGIN & SIDEBAR AKUN  (akun di tabel `akun`, tanpa Supabase Auth)
# =====================================================================
def halaman_login():
    # Tiga kolom: kiri & kanan kosong, kartu login di tengah -> posisi di tengah layar
    _, tengah, _ = st.columns([1, 1.2, 1])
    with tengah:
        st.write("")
        st.write("")
        with st.container(border=True):
            c_logo, c_teks = st.columns([1, 3], vertical_alignment="center")
            with c_logo:
                tampilkan_logo(170)                        # logo di kiri
            c_teks.header("SiCupang")                     # tulisan di samping logo
            st.caption("Aplikasi akuntansi sederhana (cash basis)")
            with st.form("form_masuk"):                   # form = kirim sekali saat tombol ditekan
                username = st.text_input("Username", placeholder="Masukkan username")
                password = st.text_input("Password", type="password", placeholder="Masukkan password")
                kirim = st.form_submit_button("Masuk", type="primary")
        if not kirim:
            return
        if not username.strip() or not password:
            st.error("Username dan password wajib diisi.")
            return
        try:
            # panggil fungsi database masuk_akun(); hasil: [] jika salah, [{id, nama}] jika benar
            res = get_client().rpc("masuk_akun", {"p_username": username.strip(),
                                                  "p_password": password}).execute()
        except Exception as e:
            st.error(f"Gagal terhubung ke database: {e}")
            return
        if not res.data:
            st.error("Username atau password salah.")
            return
        akun = res.data[0]
        st.session_state.user = {"id": akun["id"], "nama": akun["nama"]}
        bersihkan_cache()
        st.rerun()                                        # muat ulang halaman


def keluar():
    """Logout: kosongkan semua memori sesi."""
    st.session_state.clear()
    st.rerun()


def sidebar_akun():
    """Kartu akun di bagian bawah sidebar (di bawah menu): nama, info, tombol keluar."""
    with st.sidebar:
        st.divider()
        with st.container(border=True):
            c_logo, c_teks = st.columns([1, 2], vertical_alignment="center")
            with c_logo:
                tampilkan_logo(45)                        # logo di kiri
            c_teks.markdown("**SiCupang**")               # tulisan di samping logo
            st.caption(f":material/account_circle: {st.session_state.user['nama']}")
            st.caption("Pembukuan cash basis")
            if st.button("Keluar", icon=":material/logout:", key="btn_keluar"):
                keluar()
