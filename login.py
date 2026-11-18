"""Halaman login, logout, dan kartu akun pada sidebar."""

from pathlib import Path

import streamlit as st

from database import get_client, bersihkan_cache

# Lokasi logo: dicari di folder yang sama dengan file ini. Dicoba dua nama file:
# "logo.png" (disarankan) lalu "logo .png" (nama lama dengan spasi).
FOLDER = Path(__file__).parent
LOGO = next((FOLDER / n for n in ("logo.png", "logo .png") if (FOLDER / n).exists()), None)


def tampilkan_logo(lebar):
    """Tampilkan gambar logo. Jika file tidak ditemukan, tampilkan emoji supaya aplikasi tidak error."""
    if LOGO is not None:
        st.image(str(LOGO), width=180)
    else:
        st.markdown("🐟")


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
            # Logo + nama dikelompokkan di tengah kartu: dua kolom kosong di tepi sebagai pengapit
            _, c_logo, c_teks, _ = st.columns([0.5, 1.2, 2.2, 0.5],
                                              vertical_alignment="center", gap="small")
            with c_logo:
                tampilkan_logo(110)
            c_teks.header("SiCupang")
            # Keterangan dibuat rata tengah supaya seimbang dengan logo + nama di atasnya
            st.markdown(
                "<div style='text-align:center; color:#64748b; font-size:14px; "
                "margin-bottom:12px;'>Aplikasi akuntansi sederhana (cash basis)</div>",
                unsafe_allow_html=True)
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
            c_logo, c_teks = st.columns([1, 1.6], vertical_alignment="center", gap="small")
            with c_logo:
                tampilkan_logo(60)
            c_teks.markdown("**SiCupang**")
            st.caption(f":material/account_circle: {st.session_state.user['nama']}")
            st.caption("Pembukuan cash basis")
            if st.button("Keluar", icon=":material/logout:", key="btn_keluar"):
                keluar()
