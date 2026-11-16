import streamlit as st

# =====================================================================
# 1. DAFTAR AKUN (Chart of Accounts)
# =====================================================================
# Format:  "kode": {"nama": ..., "tipe": ..., "normal": "D" atau "K"}
#   tipe   : Aset / Liabilitas / Ekuitas / Pendapatan / Beban
#   normal : sisi saldo normal akun. D = Debit, K = Kredit
# Akun di bawah ini adalah akun BAWAAN. Akun tambahan dari menu "Tambah COA"
# disimpan di database (tabel coa_custom) dan digabung lewat semua_akun().
AKUN_DASAR = {
    "1-100": {"nama": "Kas",                   "tipe": "Aset",       "normal": "D"},
    "1-101": {"nama": "Kas di Bank",           "tipe": "Aset",       "normal": "D"},
    "1-102": {"nama": "Piutang",               "tipe": "Aset",       "normal": "D"},
    "1-103": {"nama": "Persediaan Ikan",       "tipe": "Aset",       "normal": "D"},
    "1-104": {"nama": "Persediaan Pakan",      "tipe": "Aset",       "normal": "D"},
    "1-105": {"nama": "Persediaan Obat",       "tipe": "Aset",       "normal": "D"},
    "1-106": {"nama": "Persediaan Lainnya",    "tipe": "Aset",       "normal": "D"},
    "1-107": {"nama": "Perlengkapan",          "tipe": "Aset",       "normal": "D"},
    "1-108": {"nama": "Peralatan",             "tipe": "Aset",       "normal": "D"},
    "1-109": {"nama": "Akumulasi Penyusutan Peralatan", "tipe": "Aset", "normal": "K"},
    "2-101": {"nama": "Utang Bank",            "tipe": "Liabilitas", "normal": "K"},
    "2-102": {"nama": "Utang Orang",           "tipe": "Liabilitas", "normal": "K"},
    "3-101": {"nama": "Modal",                 "tipe": "Ekuitas",    "normal": "K"},
    "3-102": {"nama": "Iktisar Laba Rugi",     "tipe": "Ekuitas",    "normal": "K"},
    "3-103": {"nama": "Prive",                 "tipe": "Ekuitas",    "normal": "D"},
    "4-101": {"nama": "Penjualan",             "tipe": "Pendapatan", "normal": "K"},
    "4-102": {"nama": "Penjualan Lainnya",     "tipe": "Pendapatan", "normal": "K"},   # lama, tidak dipakai transaksi baru
    "5-101": {"nama": "Beban Pembelian Ikan",  "tipe": "Beban",      "normal": "D"},   # lama
    "5-102": {"nama": "Beban Pakan",           "tipe": "Beban",      "normal": "D"},   # lama
    "5-103": {"nama": "Beban Obat",            "tipe": "Beban",      "normal": "D"},   # lama
    "5-104": {"nama": "Beban Perlengkapan",    "tipe": "Beban",      "normal": "D"},
    "5-105": {"nama": "Beban Lain-lain",       "tipe": "Beban",      "normal": "D"},
    "5-106": {"nama": "Pembelian",             "tipe": "Beban",      "normal": "D"},
    "5-107": {"nama": "Beban Penyusutan Peralatan", "tipe": "Beban", "normal": "D"},
}

# Kode akun yang dipakai di kode program
KAS_TANGAN = "1-100"
KAS_BANK = "1-101"
KAS = KAS_BANK                      # nama lama, dipertahankan
PIUTANG = "1-102"
PERLENGKAPAN = "1-107"
PERALATAN = "1-108"
AKUM_PENYUSUTAN = "1-109"
MODAL = "3-101"
IKHTISAR = "3-102"
PRIVE = "3-103"
PENJUALAN = "4-101"
BEBAN_PERLENGKAPAN = "5-104"
PEMBELIAN = "5-106"
BEBAN_PENYUSUTAN = "5-107"

# Akun persediaan per kategori (untuk penyesuaian / stock opname)
AKUN_PERSEDIAAN = {"Ikan": "1-103", "Pakan": "1-104", "Obat": "1-105", "Lainnya": "1-106"}

# Akun yang ditampilkan sebagai Harga Pokok Penjualan di laporan laba rugi
HPP_AKUN = ("5-101", "5-102", "5-103", PEMBELIAN)

# Kategori barang yang dijual / dibeli sebagai persediaan
KATEGORI_BARANG = ["Ikan", "Pakan", "Obat"]

# Pilihan kas di form: "tulisan di layar": "kode akun"
KAS_PILIHAN = {"Kas": KAS_TANGAN, "Kas di Bank": KAS_BANK}

TIPE_AKUN = ["Aset", "Liabilitas", "Ekuitas", "Pendapatan", "Beban"]
NORMAL_BAWAAN = {"Aset": "D", "Beban": "D", "Liabilitas": "K", "Ekuitas": "K", "Pendapatan": "K"}
AWAL_KODE = {"Aset": "1", "Liabilitas": "2", "Ekuitas": "3", "Pendapatan": "4", "Beban": "5"}


def semua_akun():
    """Akun bawaan + akun tambahan milik user yang sedang login, urut menurut kode."""
    gabung = {**AKUN_DASAR, **st.session_state.get("akun_custom", {})}
    return dict(sorted(gabung.items()))


def pilihan_pembelian():
    """Dropdown halaman Pembelian: {"tulisan": "kode akun yang di-DEBIT"}.
    Ikan/Pakan/Obat -> akun Pembelian. Semua akun Beban (termasuk tambahan dari menu
    Tambah COA) otomatis ikut."""
    pilihan = {k: PEMBELIAN for k in KATEGORI_BARANG}
    pilihan["Perlengkapan"] = BEBAN_PERLENGKAPAN
    pilihan["Peralatan (dicatat sebagai aset)"] = PERALATAN
    dikecualikan = {PEMBELIAN, BEBAN_PERLENGKAPAN, BEBAN_PENYUSUTAN, "5-101", "5-102", "5-103"}
    for kode, info in semua_akun().items():
        if info["tipe"] == "Beban" and kode not in dikecualikan:
            pilihan[info["nama"]] = kode
    return pilihan
