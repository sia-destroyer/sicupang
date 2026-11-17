"""Fungsi tampilan bersama dan halaman dashboard SiCupang."""

from datetime import date, timedelta
import io

import pandas as pd
import streamlit as st
from openpyxl.utils import get_column_letter

from COA import semua_akun, KAS_TANGAN, KAS_BANK, KATEGORI_BARANG
from akuntansi import filter_periode, hitung_laba, saldo_per_akun, tanpa_penutup, total_tipe
from database import muat_jurnal

# =====================================================================
# 2. FUNGSI BANTU TAMPILAN
# =====================================================================
def rp(angka):
    """Ubah angka jadi teks rupiah: 1500000 -> 'Rp 1.500.000'."""
    angka = int(angka)
    # f"{x:,}" memberi koma ribuan (1,500,000), lalu koma kita ganti jadi titik
    teks = f"{abs(angka):,}".replace(",", ".")
    return f"-Rp {teks}" if angka < 0 else f"Rp {teks}"

def ke_excel(sheets):
    """Buat file Excel (bytes). sheets = {"Nama Sheet": DataFrame, ...}"""
    buf = io.BytesIO()                                   # 'file' sementara di memori
    with pd.ExcelWriter(buf, engine="openpyxl") as w:    # 'with' = otomatis tutup file
        for nama, df in sheets.items():
            nama = nama[:31]                             # batas nama sheet Excel: 31 huruf
            df.to_excel(w, sheet_name=nama, index=False)
            ws = w.sheets[nama]
            # atur lebar tiap kolom sesuai isi
            for i, kol in enumerate(df.columns, start=1):
                isi = [len(str(kol))] + [len(str(x)) for x in df[kol].head(200)]
                ws.column_dimensions[get_column_letter(i)].width = min(max(isi) + 2, 50)
    return buf.getvalue()


def tombol_excel(label, sheets, nama_file, kunci):
    """Tombol unduh Excel. 'kunci' harus unik per tombol."""
    st.download_button(
        label, data=ke_excel(sheets), file_name=nama_file, key=kunci,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

def tombol_keluar():
    """Menampilkan tombol keluar di bagian kanan atas halaman."""
    kiri, kanan = st.columns([8, 1])

    with kanan:
        if st.button("Keluar", key="tombol_keluar"):
            st.session_state.clear()
            st.rerun()

def format_uang(df, kolom):
    """Salinan DataFrame dengan kolom uang diformat 'Rp ...' (untuk tampilan saja)."""
    d = df.copy()
    for k in kolom:
        # lambda = fungsi mini. Kosong (NaN) ditampilkan kosong, selain itu diformat rupiah
        d[k] = d[k].map(lambda v: "" if pd.isna(v) else rp(v))
    return d

def judul_halaman(judul, deskripsi):
    """Kepala halaman dengan tombol keluar di kanan atas."""

    st.title(judul)
    st.caption(deskripsi)
    
# =====================================================================
# 7. HALAMAN DASHBOARD
# =====================================================================
PERIODE = ["Bulan ini", "30 hari", "Tahun ini", "Kustom"]


def pilih_periode(kunci, bawaan):
    """Bar filter periode: tombol cepat (Bulan ini / 30 hari / Tahun ini) atau Kustom.
    'kunci' harus unik per halaman. Return (tanggal_awal, tanggal_akhir)."""
    hari = date.today()
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 1.5, 1.5], vertical_alignment="bottom")
        pilih = c1.segmented_control("Periode", PERIODE, default=bawaan,
                                     key=f"{kunci}_periode") or bawaan
        if pilih == "Kustom":
            awal = c2.date_input("Dari tanggal", value=hari.replace(day=1), key=f"{kunci}_awal")
            akhir = c3.date_input("Sampai tanggal", value=hari, key=f"{kunci}_akhir")
        else:
            awal = {"Bulan ini": hari.replace(day=1),
                    "30 hari": hari - timedelta(days=29),
                    "Tahun ini": date(hari.year, 1, 1)}[pilih]
            akhir = hari
            c2.caption(f"Dari {awal.strftime('%d/%m/%Y')}")
            c3.caption(f"Sampai {akhir.strftime('%d/%m/%Y')}")
    if awal > akhir:
        st.error("Tanggal awal tidak boleh setelah tanggal akhir.")
        st.stop()
    return awal, akhir


def delta_rp(sekarang, sebelum):
    """Teks selisih untuk st.metric. Negatif -> diawali '-' (otomatis merah). Nol -> tanpa delta."""
    selisih = sekarang - sebelum
    return None if selisih == 0 else rp(selisih)


def data_grafik(df, awal, akhir):
    """Pendapatan vs Beban per hari (periode pendek) atau per bulan (periode panjang).
    Return DataFrame berindeks 'Periode' dengan kolom Pendapatan & Beban, atau None jika kosong."""
    d = filter_periode(df, awal, akhir)
    akun = semua_akun()
    tipe = d["kode_akun"].map(lambda k: akun[k]["tipe"])
    d = d[tipe.isin(["Pendapatan", "Beban"])].copy()
    if d.empty:
        return None
    tipe = d["kode_akun"].map(lambda k: akun[k]["tipe"])
    d["Pendapatan"] = (d["kredit"] - d["debit"]).where(tipe == "Pendapatan", 0)
    d["Beban"] = (d["debit"] - d["kredit"]).where(tipe == "Beban", 0)
    format_waktu = "%Y-%m-%d" if (akhir - awal).days <= 62 else "%Y-%m"
    d["Periode"] = pd.to_datetime(d["tanggal"]).dt.strftime(format_waktu)
    return d.groupby("Periode")[["Pendapatan", "Beban"]].sum().sort_index()


def tabel_transaksi(df, jenis=None):
    """Daftar transaksi pembelian / penjualan (satu baris per transaksi), terbaru di atas.
    jenis=None -> gabungan keduanya (ada kolom 'Jenis')."""
    m_beli = (df["jenis"] == "pembelian") & (df["debit"] > 0)     # sisi beban/aset
    m_jual = (df["jenis"] == "penjualan") & (df["kredit"] > 0)    # sisi pendapatan
    if jenis == "pembelian":
        t = df[m_beli]
    elif jenis == "penjualan":
        t = df[m_jual]
    else:
        t = df[m_beli | m_jual]
    t = t.sort_values(["tanggal", "id"], ascending=False)
    akun = semua_akun()

    def pisah(ket, kode):
        """Keterangan 'Ikan: Nila 10 kg' -> kategori 'Ikan', keterangan 'Nila 10 kg'."""
        for kat in KATEGORI_BARANG:
            if ket.startswith(kat + ": "):
                return kat, ket[len(kat) + 2:]
        return akun.get(kode, {"nama": kode})["nama"], ket

    pasangan = [pisah(k, c) for k, c in zip(t["keterangan"], t["kode_akun"])]
    tabel = pd.DataFrame({
        "Tanggal": t["tanggal"],
        "Jenis": t["jenis"].astype(str).str.capitalize(),
        "Kategori": [p[0] for p in pasangan],
        "Keterangan": [p[1] for p in pasangan],
        "Nominal": t["debit"] + t["kredit"],
    })
    return tabel.drop(columns="Jenis") if jenis else tabel


def halaman_dashboard():
    judul_halaman("Dashboard", f"Ringkasan keuangan  ·  {st.session_state.user['nama']}")
    df = tanpa_penutup(muat_jurnal())      # jurnal penutup tidak ikut, supaya pendapatan/beban tetap terlihat
    awal, akhir = pilih_periode("dash", "Bulan ini")

    # Periode pembanding = periode sebelumnya dengan jumlah hari yang sama
    panjang = (akhir - awal).days + 1
    akhir_lalu = awal - timedelta(days=1)
    awal_lalu = akhir_lalu - timedelta(days=panjang - 1)

    # Laba/pendapatan/beban = hanya dalam periode.  Kas/utang/piutang = saldo sampai tanggal akhir.
    s_akhir = saldo_per_akun(filter_periode(df, None, akhir))
    s_awal = saldo_per_akun(filter_periode(df, None, akhir_lalu))

    pendapatan, beban, laba = hitung_laba(filter_periode(df, awal, akhir))
    pend_lalu, beban_lalu, laba_lalu = hitung_laba(filter_periode(df, awal_lalu, akhir_lalu))
    kas, bank, piutang = s_akhir[KAS_TANGAN], s_akhir[KAS_BANK], s_akhir["1-102"]
    utang_bank, utang_orang = s_akhir["2-101"], s_akhir["2-102"]

    # ---- Baris 1: 4 kartu angka utama ----
    k = st.columns(5)
    banding = "Dibanding periode sebelumnya (jumlah hari sama)"
    k[0].metric("Pendapatan", rp(pendapatan), delta_rp(pendapatan, pend_lalu),
                border=True, help=banding)
    k[1].metric("Beban", rp(beban), delta_rp(beban, beban_lalu), delta_color="inverse",
                border=True, help=banding)
    k[2].metric("Laba (Rugi)", rp(laba), delta_rp(laba, laba_lalu),
                border=True, help=banding)
    k[3].metric("Kas", rp(kas), delta_rp(kas, s_awal[KAS_TANGAN]),
                border=True, help="Perubahan dibanding saldo kas di awal periode")
    k[4].metric("Kas di Bank", rp(bank), delta_rp(bank, s_awal[KAS_BANK]),
                border=True, help="Perubahan dibanding saldo bank di awal periode")

    # ---- Baris 2: grafik (kiri, lebar) + utang/piutang (kanan) ----
    kiri, kanan = st.columns([2, 1], gap="medium")
    with kiri:
        with st.container(border=True):
            st.subheader("Pendapatan vs Beban")
            grafik = data_grafik(df, awal, akhir)
            if grafik is None:
                st.info("Belum ada pendapatan atau beban pada periode ini.")
            else:
                st.bar_chart(grafik, color=["#16a34a", "#dc2626"], stack=False)
    with kanan:
        with st.container(border=True):
            st.subheader("Utang / Piutang")
            st.metric("Piutang", rp(piutang))
            st.metric("Total Utang", rp(utang_bank + utang_orang))
            st.caption(f"Utang Bank: {rp(utang_bank)}  |  Utang Orang: {rp(utang_orang)}")
            st.divider()
            st.metric("Piutang - Utang", rp(piutang - utang_bank - utang_orang))

    # ---- Baris 3: transaksi terbaru ----
    with st.container(border=True):
        st.subheader("Transaksi Terbaru")
        terbaru = tabel_transaksi(df).head(8)
        if terbaru.empty:
            st.info("Belum ada transaksi. Mulai dari menu Pembelian atau Penjualan.")
        else:
            st.dataframe(format_uang(terbaru, ["Nominal"]), hide_index=True)
