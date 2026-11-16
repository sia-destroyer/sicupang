import pandas as pd
import streamlit as st

from COA import KAS_BANK, KAS_TANGAN, semua_akun
from akuntansi import (filter_periode, hitung_laba, laporan_buku_besar, laporan_jurnal_umum,
                       laporan_laba_rugi, laporan_neraca, laporan_neraca_saldo, saldo_per_akun,
                       tanpa_penutup)
from supports import judul_halaman, pilih_periode, rp, tombol_excel, format_uang
from database import muat_jurnal

def halaman_akses_cepat():
    judul_halaman("Akses Cepat", "Jurnal umum, buku besar, dan neraca saldo. Laba rugi dan neraca ada di menu sendiri.")
    df = muat_jurnal()

    # Filter tanggal untuk semua laporan
    awal, akhir = pilih_periode("aq", "Tahun ini")
    df_p = filter_periode(df, awal, akhir)        # data dalam periode
    df_sd = filter_periode(df, None, akhir)       # data sampai tanggal akhir

    # Siapkan semua laporan (juga dipakai untuk Excel)
    jurnal = laporan_jurnal_umum(df_p)
    laba_rugi = laporan_laba_rugi(df_p)
    neraca_saldo = laporan_neraca_saldo(df_sd)
    neraca = laporan_neraca(df_sd)[0]
    akun = semua_akun()
    buku_besar_semua = pd.concat(
        [laporan_buku_besar(df_sd, k).assign(Akun=f"{k} - {akun[k]['nama']}") for k in akun],
        ignore_index=True)

    # Ringkasan singkat periode
    laba = hitung_laba(tanpa_penutup(df_p))[2]
    s_sd = saldo_per_akun(df_sd)
    m = st.columns(4)
    m[0].metric("Laba (Rugi) periode", rp(laba), border=True)
    m[1].metric("Jumlah transaksi", f"{df_p[df_p['jenis'] != 'saldo_awal']['bukti'].nunique()}", border=True)
    m[2].metric("Kas", rp(s_sd[KAS_TANGAN]), border=True)
    m[3].metric("Kas di Bank", rp(s_sd[KAS_BANK]), border=True)

    # Unduh semua laporan
    with st.container(border=True):
        teks, tombol = st.columns([3, 1], vertical_alignment="center")
        teks.markdown("**Unduh laporan lengkap**")
        teks.caption("Jurnal umum, buku besar, neraca saldo, laba rugi, dan neraca dalam satu file Excel.")
        with tombol:
            tombol_excel("⬇️ Unduh SEMUA laporan ke Excel",
                         {"Jurnal Umum": jurnal, "Buku Besar": buku_besar_semua,
                          "Neraca Saldo": neraca_saldo, "Laba Rugi": laba_rugi, "Neraca": neraca},
                         "laporan_akuntansi.xlsx", "xl_semua")

    tab1, tab2, tab4 = st.tabs(["Jurnal Umum", "Buku Besar", "Neraca Saldo"])

    with tab1:
        st.dataframe(format_uang(jurnal, ["Debit", "Kredit"]), hide_index=True)
        tombol_excel("⬇️ Excel", {"Jurnal Umum": jurnal}, "jurnal_umum.xlsx", "xl_jurnal")

    with tab2:
        # format_func = cara menampilkan pilihan (nilai aslinya tetap kode akun)
        kode = st.selectbox("Pilih akun", list(akun), key="bb_akun",
                            format_func=lambda k: f"{k} - {akun[k]['nama']}")
        bb = laporan_buku_besar(df_sd, kode)
        st.caption(f"Saldo normal: {'Debit' if akun[kode]['normal'] == 'D' else 'Kredit'}")
        st.dataframe(format_uang(bb, ["Debit", "Kredit", "Saldo"]), hide_index=True)
        tombol_excel("⬇️ Excel", {akun[kode]["nama"]: bb}, f"buku_besar_{kode}.xlsx", "xl_bb")

    with tab4:
        st.dataframe(format_uang(neraca_saldo, ["Debit", "Kredit"]), hide_index=True)
        total = neraca_saldo.iloc[-1]                  # baris terakhir = TOTAL
        if total["Debit"] == total["Kredit"]:
            st.success("Seimbang ✅ (total Debit = total Kredit)")
        else:
            st.error("Tidak seimbang ❌ — periksa jurnal")
        tombol_excel("⬇️ Excel", {"Neraca Saldo": neraca_saldo}, "neraca_saldo.xlsx", "xl_ns")
