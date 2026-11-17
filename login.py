"""Halaman login, logout, dan kartu akun pada sidebar."""

import streamlit as st

from database import get_client, bersihkan_cache

# =====================================================================
# 5. LOGIN & SIDEBAR AKUN  (akun di tabel `akun`, tanpa Supabase Auth)
# =====================================================================

def terapkan_css():
    st.markdown("""
    <style>
    /* Kartu di area utama: putih, sudut bulat, bayangan halus */
    .stMain [data-testid="stVerticalBlockBorderWrapper"] {
        background: #FFFFFF;
        border-radius: 1.25rem;
        box-shadow: 0 8px 28px rgba(11, 37, 69, 0.10);
    }
    /* Kotak form di dalam kartu: biru es tipis, tanpa bayangan */
    .stMain [data-testid="stForm"] {
        background: #F1F7FC;
        border: 1px solid #D3E5F2;
        border-radius: 1rem;
        box-shadow: none;
    }
    /* Kartu bersarang di dalam kartu: tanpa bayangan ganda */
    .stMain [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlockBorderWrapper"] {
        box-shadow: none;
    }
    </style>
    """, unsafe_allow_html=True)


def halaman_login():
    # Tiga kolom: kiri & kanan kosong, kartu login di tengah -> posisi di tengah layar
    _, tengah, _ = st.columns([1, 1.2, 1])
    with tengah:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.header("🐟 SiCupang")
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
            st.markdown("**🐟 SiCupang**")
            st.caption(f":material/account_circle: {st.session_state.user['nama']}")
            st.caption("Pembukuan cash basis")
            if st.button("Keluar", icon=":material/logout:", key="btn_keluar"):
                keluar()
