from datetime import date

import pandas as pd
import streamlit as st

from COA import (KAS_PILIHAN, KATEGORI_BARANG, KAS_TANGAN, KAS_BANK, PENJUALAN, PRIVE,
                 pilihan_pembelian, semua_akun)
from akuntansi import saldo_per_akun
from supports import judul_halaman, rp, tombol_excel, format_uang, tabel_transaksi
from database import muat_harga, muat_jurnal, simpan_transaksi

NAMA_KAS = {kode: nama for nama, kode in KAS_PILIHAN.items()}


def ringkasan_transaksi(judul, jenis):
    """3 kartu angka di atas halaman: total bulan ini, jumlah transaksi, saldo kas & bank."""
    df = muat_jurnal()
    tabel = tabel_transaksi(df, jenis)
    bulan_ini = tabel[tabel["Tanggal"] >= date.today().replace(day=1)]
    s = saldo_per_akun(df)
    m = st.columns(4)
    m[0].metric(f"Total {judul} bulan ini", rp(bulan_ini["Nominal"].sum()), border=True)
    m[1].metric("Jumlah transaksi bulan ini", f"{len(bulan_ini)}", border=True)
    m[2].metric("Kas", rp(s[KAS_TANGAN]), border=True)
    m[3].metric("Kas di Bank", rp(s[KAS_BANK]), border=True)


def riwayat(judul, jenis):
    """10 transaksi terbaru + tombol unduh Excel."""
    with st.container(border=True):
        st.subheader(f"10 {judul} Terbaru")
        tabel = tabel_transaksi(muat_jurnal(), jenis)
        if tabel.empty:
            st.info("Belum ada data.")
        else:
            st.dataframe(format_uang(tabel.head(10), ["Nominal"]), hide_index=True)
            tombol_excel("⬇️ Unduh semua ke Excel", {judul: tabel},
                         f"{jenis}.xlsx", f"xl_{jenis}")


# =====================================================================
# PEMBELIAN
#   Ikan / Pakan / Obat -> Debit Pembelian, Kredit Kas (atau Kas di Bank)
#   Lainnya (beban, perlengkapan, peralatan) -> Debit akunnya, Kredit Kas
# =====================================================================
def halaman_pembelian():
    judul_halaman("Pembelian", "Catat pembelian baru di kiri, riwayat terbaru ada di kanan.")
    ringkasan = st.container()       # diisi paling akhir supaya sudah memuat transaksi baru
    kiri, kanan = st.columns([2, 3], gap="large")

    with kiri:
        with st.container(border=True):
            st.subheader("Input Pembelian")
            pilihan = pilihan_pembelian()      # beban dari menu Tambah COA otomatis ikut
            with st.form("form_pembelian", clear_on_submit=True):
                c1, c2 = st.columns(2)
                tgl = c1.date_input("Tanggal", value=date.today())
                kategori = c2.selectbox("Kategori", list(pilihan.keys()))
                kas_label = st.selectbox("Dibayar dari", list(KAS_PILIHAN.keys()))
                ket = st.text_input("Keterangan (nama barang / penjual)")
                nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000, value=0)
                kirim = st.form_submit_button("Submit", type="primary")

            if kirim:
                kode, kas = pilihan[kategori], KAS_PILIHAN[kas_label]
                saldo_kas = saldo_per_akun(muat_jurnal())[kas]
                if nominal <= 0:
                    st.error("Nominal harus lebih dari 0.")
                elif not ket.strip():
                    st.error("Keterangan wajib diisi.")
                elif nominal > saldo_kas:
                    st.error(f"Saldo {kas_label} tidak cukup ({rp(saldo_kas)}).")
                else:
                    # Ikan/Pakan/Obat: kategori disimpan di depan keterangan agar tetap terbaca
                    teks = f"{kategori}: {ket.strip()}" if kategori in KATEGORI_BARANG else ket.strip()
                    try:
                        simpan_transaksi(tgl, teks, "pembelian",
                                         [(kode, nominal, 0), (kas, 0, nominal)])
                    except Exception as e:
                        st.error(f"Gagal menyimpan: {e}")
                    else:
                        st.success(f"Tersimpan: {kategori} {rp(nominal)}")
    with kanan:
        riwayat("Pembelian", "pembelian")
    with ringkasan:
        ringkasan_transaksi("Pembelian", "pembelian")


# =====================================================================
# PENJUALAN
#   Pilih barang dari Daftar Harga, isi jumlah -> total = jumlah x harga satuan
#   Debit Kas (atau Kas di Bank), Kredit Penjualan
# =====================================================================
def halaman_penjualan():
    judul_halaman("Penjualan", "Pilih barang, isi jumlah. Harga mengikuti menu Daftar Harga.")
    ringkasan = st.container()
    kiri, kanan = st.columns([2, 3], gap="large")
    # 'ver' dinaikkan setelah submit -> semua isian kembali kosong
    ver = st.session_state.setdefault("ver_jual", 0)

    with kiri:
        with st.container(border=True):
            st.subheader("Input Penjualan")
            if "flash_jual" in st.session_state:
                st.success(st.session_state.pop("flash_jual"))
            harga = muat_harga()

            c1, c2 = st.columns(2)
            tgl = c1.date_input("Tanggal", value=date.today(), key=f"jual_tgl_{ver}")
            kategori = c2.selectbox("Kategori", KATEGORI_BARANG, key=f"jual_kat_{ver}")
            barang = harga[harga["kategori"] == kategori].reset_index(drop=True)

            if barang.empty:
                st.info(f"Belum ada barang kategori {kategori}. Isi dulu di menu Daftar Harga.")
            else:
                idx = st.selectbox(
                    "Barang", range(len(barang)), key=f"jual_brg_{ver}",
                    format_func=lambda i: f"{barang.at[i, 'nama']}  ({rp(barang.at[i, 'harga_satuan'])} / {barang.at[i, 'satuan']})")
                b = barang.loc[idx]
                jumlah = st.number_input(f"Jumlah ({b['satuan']})", min_value=0.0, step=1.0,
                                         value=0.0, format="%g", key=f"jual_jml_{ver}")
                kas_label = st.selectbox("Diterima di", list(KAS_PILIHAN.keys()), key=f"jual_kas_{ver}")
                ket = st.text_input("Pembeli (opsional)", key=f"jual_ket_{ver}")
                total = int(round(jumlah * int(b["harga_satuan"])))
                st.metric("Total", rp(total), border=True,
                          help=f"{jumlah:g} x {rp(b['harga_satuan'])}")

                if st.button("Submit", type="primary", key=f"jual_kirim_{ver}"):
                    if total <= 0:
                        st.error("Jumlah harus lebih dari 0.")
                    else:
                        teks = f"{kategori}: {b['nama']} {jumlah:g} {b['satuan']} x {rp(b['harga_satuan'])}"
                        if ket.strip():
                            teks += f" - {ket.strip()}"
                        try:
                            simpan_transaksi(tgl, teks, "penjualan",
                                             [(KAS_PILIHAN[kas_label], total, 0), (PENJUALAN, 0, total)])
                        except Exception as e:
                            st.error(f"Gagal menyimpan: {e}")
                        else:
                            st.session_state.ver_jual = ver + 1
                            st.session_state.flash_jual = f"Tersimpan: {b['nama']} {rp(total)}"
                            st.rerun()
    with kanan:
        riwayat("Penjualan", "penjualan")
    with ringkasan:
        ringkasan_transaksi("Penjualan", "penjualan")


# =====================================================================
# TARIK UANG (prive)  ->  Debit Prive, Kredit Kas / Kas di Bank
# =====================================================================
def halaman_tarik_uang():
    judul_halaman("Tarik Uang", "Pengambilan uang untuk keperluan pribadi (prive). Mengurangi kas atau bank yang dipilih.")
    df = muat_jurnal()
    s = saldo_per_akun(df)
    if "flash_prive" in st.session_state:
        st.success(st.session_state.pop("flash_prive"))
    m = st.columns(2)
    m[0].metric("Kas", rp(s[KAS_TANGAN]), border=True)
    m[1].metric("Kas di Bank", rp(s[KAS_BANK]), border=True)

    kiri, kanan = st.columns([2, 3], gap="large")
    with kiri:
        with st.container(border=True):
            st.subheader("Tarik Uang")
            with st.form("form_prive", clear_on_submit=True):
                sumber_label = st.radio("Ambil dari mana?", list(KAS_PILIHAN.keys()), horizontal=True)
                c1, c2 = st.columns(2)
                tgl = c1.date_input("Tanggal", value=date.today())
                nominal = c2.number_input("Nominal (Rp)", min_value=0, step=10000, value=0)
                ket = st.text_input("Keterangan (opsional)")
                kirim = st.form_submit_button("Submit", type="primary")
            if kirim:
                sumber = KAS_PILIHAN[sumber_label]
                if nominal <= 0:
                    st.error("Nominal harus lebih dari 0.")
                elif nominal > s[sumber]:
                    st.error(f"Saldo {sumber_label} tidak cukup ({rp(s[sumber])}).")
                else:
                    teks = f"Prive dari {sumber_label}" + (f" - {ket.strip()}" if ket.strip() else "")
                    try:
                        simpan_transaksi(tgl, teks, "prive", [(PRIVE, nominal, 0), (sumber, 0, nominal)])
                    except Exception as e:
                        st.error(f"Gagal menyimpan: {e}")
                    else:
                        st.session_state.flash_prive = f"Tersimpan: tarik {rp(nominal)} dari {sumber_label}"
                        st.rerun()
    with kanan:
        with st.container(border=True):
            st.subheader("Riwayat Penarikan")
            p = df[(df["jenis"] == "prive") & (df["debit"] > 0)].sort_values(["tanggal", "id"], ascending=False)
            if p.empty:
                st.info("Belum ada penarikan.")
            else:
                akun_kas = df[(df["jenis"] == "prive") & (df["kredit"] > 0)].set_index("bukti")["kode_akun"]
                tabel = pd.DataFrame({
                    "Tanggal": p["tanggal"],
                    "Sumber": p["bukti"].map(lambda b: NAMA_KAS.get(akun_kas.get(b), "")),
                    "Keterangan": p["keterangan"],
                    "Nominal": p["debit"],
                })
                st.dataframe(format_uang(tabel.head(15), ["Nominal"]), hide_index=True)
                tombol_excel("⬇️ Unduh ke Excel", {"Tarik Uang": tabel}, "tarik_uang.xlsx", "xl_prive")
