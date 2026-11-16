"""Daftar harga persediaan: nama barang + harga jual satuan. Dipakai halaman Penjualan."""

import streamlit as st

from COA import KATEGORI_BARANG
from database import muat_harga, simpan_harga
from supports import judul_halaman


def halaman_daftar_harga():
    judul_halaman("Daftar Harga", "Harga jual satuan tiap barang. Di halaman Penjualan Anda tinggal memilih barang dan mengisi jumlah.")
    harga = muat_harga()

    with st.container(border=True):
        st.caption("Klik baris kosong di bawah tabel untuk menambah barang. Pilih baris lalu tekan Delete untuk menghapus. "
                   "Perubahan baru tersimpan setelah menekan tombol Simpan.")
        edit = st.data_editor(
            harga, num_rows="dynamic", hide_index=True, key="editor_harga",
            column_config={
                "kategori": st.column_config.SelectboxColumn("Kategori", options=KATEGORI_BARANG, required=True),
                "nama": st.column_config.TextColumn("Nama barang", required=True),
                "satuan": st.column_config.TextColumn("Satuan (kg, ekor, sak, ...)", required=True),
                "harga_satuan": st.column_config.NumberColumn("Harga satuan (Rp)", min_value=1, step=500,
                                                              format="%d", required=True),
            })
        if st.button("Simpan daftar harga", type="primary"):
            d = edit.dropna(how="all").copy()
            d["nama"] = d["nama"].fillna("").astype(str).str.strip()
            d["satuan"] = d["satuan"].fillna("").astype(str).str.strip()
            if d[["kategori", "nama", "satuan", "harga_satuan"]].isna().any().any() \
                    or (d["nama"] == "").any() or (d["satuan"] == "").any():
                st.error("Setiap baris wajib diisi lengkap: kategori, nama, satuan, dan harga.")
            elif d.duplicated(["kategori", "nama"]).any():
                st.error("Ada barang dengan kategori dan nama yang sama.")
            else:
                d["harga_satuan"] = d["harga_satuan"].astype("int64")
                try:
                    simpan_harga(d)
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")
                else:
                    st.success("Daftar harga tersimpan.")
                    st.rerun()
