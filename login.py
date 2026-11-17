```python
"""Halaman login, logout, dan kartu akun pada sidebar."""

from pathlib import Path

import streamlit as st

from database import get_client, bersihkan_cache


# =====================================================================
# LOGO APLIKASI
# =====================================================================

FOLDER = Path(__file__).parent

LOGO = next(
    (FOLDER / n for n in ("logo.png", "logo .png") if (FOLDER / n).exists()),
    None
)


def tampilkan_logo(lebar):
    """Tampilkan logo sesuai ukuran yang ditentukan."""
    if LOGO is not None:
        st.image(str(LOGO), width=lebar)
    else:
        st.markdown("🐟")


# =====================================================================
# LOGIN
# =====================================================================

def halaman_login():

    # Membuat kartu login berada di tengah halaman
    _, tengah, _ = st.columns([1, 1.2, 1])

    with tengah:

        st.write("")
        st.write("")

        with st.container(border=True):

            # Logo dan nama aplikasi sejajar
            _, bagian_logo, bagian_teks, _ = st.columns(
                [0.7, 1.1, 2.3, 0.7],
                vertical_alignment="center",
                gap="small"
            )

            with bagian_logo:
                tampilkan_logo(100)

            with bagian_teks:
                st.markdown(
                    """
                    <h1 style="
                        margin: 0;
                        padding: 0;
                        color: #102A4C;
                        font-size: 38px;
                        font-weight: 700;
                        white-space: nowrap;
                    ">
                        SiCupang
                    </h1>
                    """,
                    unsafe_allow_html=True
                )

            # Deskripsi aplikasi
            st.markdown(
                """
                <div style="
                    text-align: center;
                    color: #64748b;
                    font-size: 14px;
                    margin-bottom: 12px;
                    margin-top: 25px;
                ">
                    Aplikasi akuntansi sederhana (cash basis)
                </div>
                """,
                unsafe_allow_html=True
            )

            # Form login
            with st.form("form_masuk"):

                username = st.text_input(
                    "Username",
                    placeholder="Masukkan username"
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Masukkan password"
                )

                kirim = st.form_submit_button(
                    "Masuk",
                    type="primary"
                )

        # Jika tombol belum ditekan
        if not kirim:
            return

        # Validasi input
        if not username.strip() or not password:
            st.error("Username dan password wajib diisi.")
            return

        try:
            # Memeriksa akun melalui database
            res = get_client().rpc(
                "masuk_akun",
                {
                    "p_username": username.strip(),
                    "p_password": password
                }
            ).execute()

        except Exception as e:
            st.error(f"Gagal terhubung ke database: {e}")
            return

        # Jika username atau password salah
        if not res.data:
            st.error("Username atau password salah.")
            return

        # Menyimpan data pengguna ke session
        akun = res.data[0]

        st.session_state.user = {
            "id": akun["id"],
            "nama": akun["nama"]
        }

        bersihkan_cache()

        # Muat ulang halaman
        st.rerun()


# =====================================================================
# LOGOUT
# =====================================================================

def keluar():
    """Logout: kosongkan semua memori sesi."""

    st.session_state.clear()
    st.rerun()


# =====================================================================
# SIDEBAR AKUN
# =================================================================
