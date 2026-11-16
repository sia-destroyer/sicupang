"""Penyesuaian & penutupan dengan metode Iktisar Laba Rugi."""

from datetime import date

import pandas as pd
import streamlit as st

from COA import AKUN_PERSEDIAAN, PERLENGKAPAN, PERALATAN, semua_akun
from akuntansi import filter_periode, hitung_laba, saldo_per_akun, susun_penyesuaian, tanpa_penutup
from database import muat_item_peralatan, muat_jurnal, simpan_banyak
from supports import format_uang, judul_halaman, rp


def halaman_penyesuaian():
    judul_halaman("Penyesuaian", "Stock opname, perlengkapan, penyusutan, lalu penutupan buku lewat Iktisar Laba Rugi.")
    df = muat_jurnal()
    if "flash_penyesuaian" in st.session_state:
        st.success(st.session_state.pop("flash_penyesuaian"))

    with st.container(border=True):
        tgl = st.date_input("Tanggal penyesuaian (akhir periode)", value=date.today(), key="adj_tgl")
        tutup_terakhir = df.loc[df["jenis"] == "penutup", "tanggal"].max() if (df["jenis"] == "penutup").any() else None
        if tutup_terakhir is not None:
            st.caption(f"Penutupan terakhir: {tutup_terakhir.strftime('%d/%m/%Y')}. Periode baru dimulai setelah tanggal itu.")
    d = filter_periode(df, None, tgl)
    s = saldo_per_akun(d)

    # ---------- 1. Persediaan akhir (stock opname) ----------
    with st.container(border=True):
        st.subheader("1. Stock opname: persediaan akhir")
        st.caption("Hitung stok fisik di akhir periode, lalu isi nilainya dalam rupiah (sebesar harga perolehan). "
                   "Persediaan awal diambil otomatis dari saldo buku.")
        akhir = {}
        cols = st.columns(len(AKUN_PERSEDIAAN))
        for c, (kat, kode) in zip(cols, AKUN_PERSEDIAAN.items()):
            c.metric(f"{kat}: awal", rp(s[kode]))
            akhir[kat] = c.number_input(f"{kat}: akhir (Rp)", min_value=0, step=10000, value=0,
                                        key=f"adj_akhir_{kat}")
            if akhir[kat] == 0 and s[kode] > 0:
                c.caption("⚠️ Akhir 0, pastikan stok memang habis.")

    # ---------- 2. Perlengkapan ----------
    with st.container(border=True):
        st.subheader("2. Perlengkapan")
        c1, c2 = st.columns(2)
        c1.metric("Saldo perlengkapan di buku", rp(s[PERLENGKAPAN]))
        sisa = c2.number_input("Perlengkapan yang masih tersisa (Rp)", min_value=0, step=10000, value=0,
                               key="adj_sisa",
                               help="Pembelian perlengkapan dicatat sebagai Beban Perlengkapan. Yang masih tersisa "
                                    "dikembalikan ke aset, sisanya tetap menjadi beban.")

    # ---------- 3. Penyusutan peralatan ----------
    with st.container(border=True):
        st.subheader("3. Penyusutan peralatan")
        try:
            item = muat_item_peralatan()
        except Exception:
            item = []
        per_bulan = sum(r["nominal"] / r["umur_bulan"] for r in item if r.get("umur_bulan"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Saldo peralatan", rp(s[PERALATAN]))
        bulan = c2.number_input("Jumlah bulan yang disusutkan", min_value=0, step=1, value=1, key="adj_bulan")
        saran = int(round(per_bulan * bulan))
        susut = c3.number_input("Beban penyusutan (Rp)", min_value=0, step=1000, value=saran,
                                key=f"adj_susut_{bulan}_{saran}",
                                help="Saran dihitung dari harga dan perkiraan pemakaian peralatan di saldo awal "
                                     "(garis lurus). Peralatan yang dibeli kemudian tidak punya umur pemakaian, "
                                     "tambahkan manual ke angka ini.")
        st.caption(f"Saran otomatis: {rp(per_bulan)} per bulan dari peralatan di saldo awal.")

    # ---------- Pratinjau ----------
    daftar = susun_penyesuaian(d, tgl, akhir, sisa, susut)
    akun = semua_akun()
    baris = []
    for jenis, ket, entri in daftar:
        for kode, deb, kre in entri:
            baris.append({"Jenis": jenis.capitalize(), "Keterangan": ket,
                          "Akun": ("      " if kre > 0 else "") + akun[kode]["nama"],
                          "Debit": deb, "Kredit": kre})
    with st.container(border=True):
        st.subheader("Pratinjau jurnal")
        if not baris:
            st.info("Belum ada jurnal yang akan dibuat.")
        else:
            st.dataframe(format_uang(pd.DataFrame(baris), ["Debit", "Kredit"]), hide_index=True)
            # laba setelah penyesuaian = laba dari jurnal sebelum penutup + jurnal penyesuaian
            pra = pd.concat(
                [tanpa_penutup(d)] + [pd.DataFrame(
                    [{"tanggal": tgl, "jenis": j, "kode_akun": k, "debit": a, "kredit": b}
                     for k, a, b in e]) for j, _, e in daftar if j == "penyesuaian"],
                ignore_index=True)
            pend, beban, laba = hitung_laba(pra)
            m = st.columns(3)
            m[0].metric("Pendapatan", rp(pend), border=True)
            m[1].metric("Beban + HPP", rp(beban), border=True)
            m[2].metric("Laba (Rugi) ditutup ke Modal", rp(laba), border=True)

    # ---------- Simpan ----------
    if st.button("Simpan penyesuaian dan penutupan", type="primary", disabled=not baris):
        if tutup_terakhir is not None and tgl <= tutup_terakhir:
            st.error("Tanggal harus setelah penutupan terakhir.")
        else:
            try:
                simpan_banyak(tgl, daftar)
            except Exception as e:
                st.error(f"Gagal menyimpan: {e}")
            else:
                for k in [k for k in st.session_state if str(k).startswith("adj_")]:
                    st.session_state.pop(k)
                st.session_state.flash_penyesuaian = ("Penyesuaian dan penutupan tersimpan. "
                                                      "Lihat hasilnya di Laporan Laba Rugi dan Laporan Neraca.")
                st.rerun()
