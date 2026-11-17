import streamlit as st

st.set_page_config(page_title="SiCupang Akuntansi", page_icon="🐟", layout="wide",
                   initial_sidebar_state="expanded")

from akses_cepat import halaman_akses_cepat
from daftar_harga import halaman_daftar_harga
from kelola_coa import halaman_coa
from laporan import halaman_laba_rugi, halaman_neraca
from penyesuaian import halaman_penyesuaian
from supports import halaman_dashboard
from database import muat_coa, saldo_awal_selesai
from login import halaman_login, sidebar_akun, terapkan_css
from saldo_awal import halaman_saldo_awal
from transaksi import halaman_pembelian, halaman_penjualan, halaman_tarik_uang

def main():
    terapkan_css()   # kartu putih + bayangan (lihat login.py)
    # 1) Belum login -> tampilkan halaman login (tanpa sidebar)
    if "user" not in st.session_state:
        halaman_login()
        return

    # 2) Sudah login, tapi saldo awal belum diisi -> wizard
    if "sa_selesai" not in st.session_state:
        st.session_state.sa_selesai = saldo_awal_selesai()
    if not st.session_state.sa_selesai:
        sidebar_akun()
        halaman_saldo_awal()
        return

    muat_coa()      # akun tambahan (menu Tambah COA) dimuat sekali per sesi

    # 3) Aplikasi utama: menu sidebar dikelompokkan per bagian (st.navigation)
    halaman = st.navigation({
        "Ringkasan": [
            st.Page(halaman_dashboard, title="Dashboard", icon=":material/dashboard:",
                    url_path="dashboard", default=True),
        ],
        "Transaksi": [
            st.Page(halaman_pembelian, title="Pembelian", icon=":material/shopping_cart:",
                    url_path="pembelian"),
            st.Page(halaman_penjualan, title="Penjualan", icon=":material/sell:",
                    url_path="penjualan"),
            st.Page(halaman_daftar_harga, title="Daftar Harga", icon=":material/price_change:",
                    url_path="daftar-harga"),
            st.Page(halaman_penyesuaian, title="Penyesuaian", icon=":material/tune:",
                    url_path="penyesuaian"),
            st.Page(halaman_tarik_uang, title="Tarik Uang", icon=":material/payments:",
                    url_path="tarik-uang"),
        ],
        "Laporan": [
            st.Page(halaman_akses_cepat, title="Akses Cepat", icon=":material/receipt_long:",
                    url_path="akses-cepat"),
            st.Page(halaman_coa, title="Tambah COA", icon=":material/library_add:",
                    url_path="tambah-coa"),
            st.Page(halaman_laba_rugi, title="Laporan Laba Rugi", icon=":material/trending_up:",
                    url_path="laba-rugi"),
            st.Page(halaman_neraca, title="Laporan Neraca", icon=":material/balance:",
                    url_path="neraca"),
        ],
    })
    sidebar_akun()          # kartu akun muncul di bawah menu
    halaman.run()


# Streamlit menjalankan file ini sebagai "__main__", jadi main() otomatis dipanggil
if __name__ == "__main__":
    main()
