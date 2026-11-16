"""Halaman Laporan Laba Rugi dan Laporan Neraca."""

from datetime import date

import streamlit as st

from akuntansi import filter_periode, laporan_laba_rugi, laporan_neraca
from database import muat_jurnal
from supports import format_uang, judul_halaman, pilih_periode, rp, tombol_excel


def halaman_laba_rugi():
    judul_halaman("Laporan Laba Rugi", "Pendapatan, harga pokok penjualan, dan beban pada periode yang dipilih.")
    df = muat_jurnal()
    awal, akhir = pilih_periode("lr", "Tahun ini")
    d = filter_periode(df, awal, akhir)
    lr = laporan_laba_rugi(d)

    pend = lr.loc[lr["Keterangan"] == "Total Pendapatan", "Jumlah"].iloc[0]
    laba = lr.loc[lr["Keterangan"] == "LABA (RUGI) BERSIH", "Jumlah"].iloc[0]
    m = st.columns(3)
    m[0].metric("Pendapatan", rp(pend), border=True)
    m[1].metric("Beban + HPP", rp(pend - laba), border=True)
    m[2].metric("Laba (Rugi) Bersih", rp(laba), border=True)

    if not (d["jenis"] == "penyesuaian").any():
        st.info("Belum ada penyesuaian pada periode ini. Persediaan akhir belum dihitung, "
                "jadi laba bisa terlalu kecil. Lakukan di menu Penyesuaian.")
    with st.container(border=True):
        st.dataframe(format_uang(lr, ["Jumlah"]), hide_index=True, height=620)
        tombol_excel("⬇️ Excel", {"Laba Rugi": lr}, "laporan_laba_rugi.xlsx", "xl_lap_lr")


def halaman_neraca():
    judul_halaman("Laporan Neraca", "Posisi aset, liabilitas, dan ekuitas pada tanggal yang dipilih.")
    df = muat_jurnal()
    with st.container(border=True):
        tgl = st.date_input("Per tanggal", value=date.today(), key="neraca_tgl")
    neraca, aset, le = laporan_neraca(filter_periode(df, None, tgl))

    m = st.columns(2)
    m[0].metric("Total Aset", rp(aset), border=True)
    m[1].metric("Total Liabilitas + Ekuitas", rp(le), border=True)
    with st.container(border=True):
        st.dataframe(format_uang(neraca, ["Jumlah"]), hide_index=True, height=620)
        if aset == le:
            st.success("Seimbang ✅ (Aset = Liabilitas + Ekuitas)")
        else:
            st.error(f"Tidak seimbang ❌ — selisih {rp(aset - le)}")
        tombol_excel("⬇️ Excel", {"Neraca": neraca}, "laporan_neraca.xlsx", "xl_lap_neraca")
