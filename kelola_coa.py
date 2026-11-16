"""Menu Tambah COA: menambah akun baru ke Chart of Accounts."""

import pandas as pd
import streamlit as st

from COA import AKUN_DASAR, AWAL_KODE, NORMAL_BAWAAN, TIPE_AKUN, semua_akun
from database import hapus_akun, muat_jurnal, tambah_akun
from supports import judul_halaman


def saran_kode(tipe):
    """Kode berikutnya untuk tipe akun, mis. Beban -> '5-108'."""
    awal = AWAL_KODE[tipe]
    angka = []
    for kode in semua_akun():
        depan, _, belakang = kode.partition("-")
        if depan == awal and belakang.isdigit():
            angka.append(int(belakang))
    return f"{awal}-{(max(angka) if angka else 100) + 1}"


def halaman_coa():
    judul_halaman("Tambah COA", "Tambah akun baru. Akun bertipe Beban otomatis muncul di pilihan Kategori pada halaman Pembelian.")
    kiri, kanan = st.columns([2, 3], gap="large")

    with kiri:
        with st.container(border=True):
            st.subheader("Akun baru")
            tipe = st.selectbox("Tipe akun", TIPE_AKUN, index=TIPE_AKUN.index("Beban"), key="coa_tipe")
            kode = st.text_input("Kode akun", value=saran_kode(tipe), key=f"coa_kode_{tipe}")
            nama = st.text_input("Nama akun", placeholder="mis. Beban Listrik", key="coa_nama")
            normal = st.radio("Saldo normal", ["D", "K"], horizontal=True, key=f"coa_normal_{tipe}",
                              index=["D", "K"].index(NORMAL_BAWAAN[tipe]),
                              format_func=lambda x: "Debit" if x == "D" else "Kredit",
                              help="Biasanya otomatis sesuai tipe. Ubah hanya untuk akun lawan (kontra).")
            if st.button("Tambah akun", type="primary"):
                akun = semua_akun()
                kode, nama = kode.strip(), nama.strip()
                if not kode or not nama:
                    st.error("Kode dan nama akun wajib diisi.")
                elif kode in akun:
                    st.error(f"Kode {kode} sudah dipakai oleh '{akun[kode]['nama']}'.")
                elif nama.lower() in (a["nama"].lower() for a in akun.values()):
                    st.error("Nama akun sudah ada.")
                else:
                    try:
                        tambah_akun(kode, nama, tipe, normal)
                    except Exception as e:
                        st.error(f"Gagal menyimpan: {e}")
                    else:
                        st.success(f"Akun {kode} - {nama} ditambahkan.")
                        st.rerun()

        custom = st.session_state.get("akun_custom", {})
        if custom:
            with st.container(border=True):
                st.subheader("Hapus akun tambahan")
                dipakai = set(muat_jurnal()["kode_akun"])
                bisa = [k for k in custom if k not in dipakai]
                if not bisa:
                    st.caption("Semua akun tambahan sudah punya transaksi, jadi tidak bisa dihapus.")
                else:
                    pilih = st.selectbox("Akun (hanya yang belum punya transaksi)", bisa,
                                         format_func=lambda k: f"{k} - {custom[k]['nama']}")
                    if st.button("Hapus akun"):
                        try:
                            hapus_akun(pilih)
                        except Exception as e:
                            st.error(f"Gagal menghapus: {e}")
                        else:
                            st.rerun()

    with kanan:
        with st.container(border=True):
            st.subheader("Daftar akun")
            tabel = pd.DataFrame([
                {"Kode": k, "Nama": a["nama"], "Tipe": a["tipe"],
                 "Saldo normal": "Debit" if a["normal"] == "D" else "Kredit",
                 "Sumber": "Bawaan" if k in AKUN_DASAR else "Tambahan"}
                for k, a in semua_akun().items()])
            st.dataframe(tabel, hide_index=True, height=520)
