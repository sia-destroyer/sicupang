"""Wizard pengisian saldo awal tujuh langkah."""

from datetime import date

import pandas as pd
import streamlit as st

from akuntansi import entri_saldo_awal
from supports import rp
from database import simpan_saldo_awal

# =====================================================================
# 6. SALDO AWAL (wizard 7 langkah, pertama kali login)
# =====================================================================
TOTAL_LANGKAH = 7
OPSI = ["Tidak", "Ya"]

# Definisi tabel isian. Tiap kolom: (judul kolom, peran)
#   peran: pihak (Bank/Orang) | nama (teks) | nominal (rupiah) | umur (bulan)
# Ingin ubah judul kolom / tambah kolom? Ubah di sini.
TABEL = {
    "utang":        [("Pihak", "pihak"), ("Nama bank / orang", "nama"), ("Nominal (Rp)", "nominal")],
    "piutang":      [("Nama pihak", "nama"), ("Nominal (Rp)", "nominal")],
    "ikan":         [("Jenis ikan", "nama"), ("Harga (Rp)", "nominal")],
    "pakan":        [("Nama pakan", "nama"), ("Harga (Rp)", "nominal")],
    "obat":         [("Nama obat", "nama"), ("Harga (Rp)", "nominal")],
    "lainnya":      [("Nama barang", "nama"), ("Harga (Rp)", "nominal")],
    "peralatan":    [("Nama peralatan", "nama"), ("Harga (Rp)", "nominal"),
                     ("Perkiraan pemakaian (bulan)", "umur")],
    "perlengkapan": [("Nama perlengkapan", "nama"), ("Harga (Rp)", "nominal")],
}


def init_wizard():
    """Siapkan 'memori' wizard saat pertama dibuka."""
    if "sa" not in st.session_state:
        st.session_state.sa = {
            "langkah": 0,
            "kas_tangan": None,                      # wajib diisi (None = belum diisi)
            "kas_ada": "Tidak", "kas_nominal": 0,
            "utang_ada": "Tidak", "piutang_ada": "Tidak", "lain_ada": "Tidak",
            "tanggal": date.today(),
            "in": {},    # tabel awal yang ditampilkan editor
            "out": {},   # hasil editan terbaru dari editor
        }


def tanya(kunci, pertanyaan):
    """Pertanyaan Ya/Tidak. Jawaban disimpan di sa[kunci]. Return True jika 'Ya'."""
    sa = st.session_state.sa
    sa[kunci] = st.radio(pertanyaan, OPSI, index=OPSI.index(sa[kunci]),
                         horizontal=True, key=f"radio_{kunci}")
    return sa[kunci] == "Ya"


def editor(nama):
    """Tampilkan tabel isian yang bisa ditambah barisnya (klik baris kosong di bawah)."""
    sa = st.session_state.sa
    if nama not in sa["in"]:
        # tabel kosong dengan kolom sesuai TABEL (teks -> object, angka -> float)
        sa["in"][nama] = pd.DataFrame({
            kol: pd.Series(dtype="object" if peran in ("pihak", "nama") else "float64")
            for kol, peran in TABEL[nama]
        })
    config = {}                                       # pengaturan tampilan tiap kolom
    for kol, peran in TABEL[nama]:
        if peran == "pihak":
            config[kol] = st.column_config.SelectboxColumn(kol, options=["Bank", "Orang"])
        elif peran == "nominal":
            config[kol] = st.column_config.NumberColumn(kol, min_value=0, step=1000, format="%d")
        elif peran == "umur":
            config[kol] = st.column_config.NumberColumn(kol, min_value=0, step=1, format="%d")
    # num_rows="dynamic" = pengguna boleh menambah/menghapus baris
    sa["out"][nama] = st.data_editor(sa["in"][nama], num_rows="dynamic",
                                     column_config=config, key=f"editor_{nama}")


def bersih(nama):
    """Ambil isi tabel, buang baris kosong, cek kelengkapan.
    Return: list dict {'pihak','nama','nominal','umur'}. Raise ValueError jika ada yang salah."""
    df = st.session_state.sa["out"].get(nama)
    if df is None:
        return []
    hasil = []
    for no, (_, r) in enumerate(df.iterrows(), start=1):
        isi, kosong = {}, True
        for kol, peran in TABEL[nama]:
            v = r[kol]
            if peran in ("pihak", "nama"):
                v = "" if pd.isna(v) else str(v).strip()
            else:
                v = 0 if pd.isna(v) else int(v)
            if v:
                kosong = False
            isi[peran] = v
        if kosong:
            continue                                  # baris kosong dilewati
        for kol, peran in TABEL[nama]:
            if not isi[peran]:
                raise ValueError(f"Tabel {nama}, baris {no}: kolom '{kol}' belum diisi.")
        hasil.append(isi)
    return hasil


def kumpulkan():
    """Kumpulkan semua jawaban wizard menjadi satu dict data bersih."""
    sa = st.session_state.sa
    return {
        "kas_tangan": int(sa["kas_tangan"] or 0),
        "kas": int(sa["kas_nominal"]) if sa["kas_ada"] == "Ya" else 0,
        "utang": bersih("utang") if sa["utang_ada"] == "Ya" else [],
        "piutang": bersih("piutang") if sa["piutang_ada"] == "Ya" else [],
        "ikan": bersih("ikan"),
        "pakan": bersih("pakan"),
        "obat": bersih("obat"),
        "lainnya": bersih("lainnya") if sa["lain_ada"] == "Ya" else [],
        "peralatan": bersih("peralatan"),
        "perlengkapan": bersih("perlengkapan"),
    }


def validasi_langkah(l):
    """Cek isian langkah ke-l. Return teks error, atau None jika aman."""
    sa = st.session_state.sa
    try:
        if l == 1 and sa["kas_tangan"] is None:
            return "Kas (uang tunai di tangan) wajib diisi. Isi 0 jika tidak ada."
        if l == 1 and sa["kas_ada"] == "Ya" and sa["kas_nominal"] <= 0:
            return "Nominal kas di bank harus lebih dari 0."
        if l == 2 and sa["utang_ada"] == "Ya" and not bersih("utang"):
            return "Isi minimal satu utang, atau pilih 'Tidak'."
        if l == 3 and sa["piutang_ada"] == "Ya" and not bersih("piutang"):
            return "Isi minimal satu piutang, atau pilih 'Tidak'."
        if l == 4:
            for t in ("ikan", "pakan", "obat"):
                bersih(t)
            if sa["lain_ada"] == "Ya" and not bersih("lainnya"):
                return "Isi persediaan lainnya, atau pilih 'Tidak'."
        if l == 5:
            bersih("peralatan")
        if l == 6:
            bersih("perlengkapan")
    except ValueError as e:                           # pesan dari bersih()
        return str(e)
    return None


def pindah(n):
    """Pindah ke langkah n. Hasil editan disalin supaya tidak hilang saat kembali."""
    sa = st.session_state.sa
    sa["in"] = {k: v.copy() for k, v in sa["out"].items()}
    sa["langkah"] = n
    st.rerun()


NAMA_LANGKAH = ["Mulai", "Kas dan Bank", "Utang", "Piutang",
                "Persediaan", "Peralatan", "Perlengkapan"]


def halaman_saldo_awal():
    init_wizard()
    sa = st.session_state.sa
    l = sa["langkah"]

    # Kolom kiri & kanan kosong -> isi wizard berada di tengah, tidak melebar
    _, tengah, _ = st.columns([1, 3, 1])
    with tengah:
        st.title("Saldo Awal")
        st.progress((l + 1) / TOTAL_LANGKAH,
                    text=f"Langkah {l + 1} dari {TOTAL_LANGKAH}  ·  {NAMA_LANGKAH[l]}")

        with st.container(border=True):
            if l == 0:    # 1) pernyataan
                st.subheader("Anda harus memasukkan beberapa saldo untuk memulai❗")
                st.write("Semua isian berupa nominal uang, dipakai sebagai saldo awal pembukuan Anda.")

            elif l == 1:  # 2) kas (tangan) + kas di bank
                st.subheader("Kas dan Bank")
                sa["kas_tangan"] = st.number_input(
                    "Kas: uang tunai di tangan (Rp) — wajib diisi", min_value=0, step=100000,
                    value=sa["kas_tangan"], placeholder="Isi 0 jika tidak ada", key="num_kas_tangan")
                st.divider()
                if tanya("kas_ada", "Apakah Anda memiliki kas di bank?"):
                    sa["kas_nominal"] = st.number_input(
                        "Nominal kas di bank (Rp)", min_value=0, step=100000,
                        value=int(sa["kas_nominal"]), key="num_kas")

            elif l == 2:  # 3) utang
                st.subheader("Utang")
                if tanya("utang_ada", "Apakah Anda memiliki utang?"):
                    st.caption("Pilih Bank atau Orang, isi nama dan nominal. Klik baris kosong di bawah tabel untuk menambah.")
                    editor("utang")

            elif l == 3:  # 4) piutang
                st.subheader("Piutang")
                if tanya("piutang_ada", "Apakah Anda memiliki piutang?"):
                    st.caption("Klik baris kosong di bawah tabel untuk menambah.")
                    editor("piutang")

            elif l == 4:  # 5) persediaan
                st.subheader("Persediaan")
                st.caption("Kosongkan tabel jika tidak ada. Klik baris kosong di bawah tabel untuk menambah.")
                ada_lain = tanya("lain_ada", "Apakah ada persediaan lain selain ikan, pakan, dan obat?")
                st.markdown("**Ikan**")
                editor("ikan")
                st.markdown("**Pakan**")
                editor("pakan")
                st.markdown("**Obat**")
                editor("obat")
                if ada_lain:
                    st.markdown("**Persediaan lainnya**")
                    editor("lainnya")

            elif l == 5:  # 6) peralatan
                st.subheader("Peralatan")
                st.caption("Perkiraan pemakaian = berapa bulan alat diperkirakan bisa dipakai. Kosongkan jika tidak ada.")
                editor("peralatan")

            elif l == 6:  # 7) perlengkapan + ringkasan
                st.subheader("Perlengkapan")
                st.caption("Kosongkan jika tidak ada.")
                editor("perlengkapan")
                sa["tanggal"] = st.date_input("Tanggal saldo awal", value=sa["tanggal"])
                try:                                   # ringkasan sementara
                    entri = entri_saldo_awal(kumpulkan())
                    aset = sum(e[1] for e in entri if e[0].startswith("1-"))
                    utang = sum(e[2] for e in entri if e[0].startswith("2-"))
                    modal = sum(e[2] - e[1] for e in entri if e[0] == "3-101")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Aset", rp(aset), border=True)
                    c2.metric("Total Utang", rp(utang), border=True)
                    c3.metric("Modal", rp(modal), border=True)
                except ValueError as e:
                    st.warning(str(e))

        # ---- tombol navigasi ----
        kiri, kanan = st.columns(2)
        kembali = kiri.button("Kembali", icon=":material/arrow_back:", disabled=(l == 0))
        teks = "Oke" if l == 0 else ("Simpan" if l == TOTAL_LANGKAH - 1 else "Lanjut")
        lanjut = kanan.button(teks, type="primary")

        if kembali:
            pindah(l - 1)
        if lanjut:
            err = validasi_langkah(l)
            if err:
                st.error(err)
            elif l == TOTAL_LANGKAH - 1:
                try:
                    simpan_saldo_awal(kumpulkan(), sa["tanggal"])
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")
                else:
                    st.rerun()                         # masuk ke aplikasi utama
            else:
                pindah(l + 1)
