"""Akses database Supabase dan fungsi penyimpanan data SiCupang."""

# ---------- IMPORT (memanggil library yang dipakai) ----------
import uuid                     # membuat kode unik untuk bukti jurnal

import pandas as pd
import streamlit as st
from supabase import create_client

from COA import semua_akun
from akuntansi import entri_saldo_awal, item_saldo_awal

# ---------- Koneksi Supabase ----------
@st.cache_resource          # dibuat sekali lalu dipakai ulang (tidak membuat koneksi baru tiap klik)
def _buat_client(url, key):
    return create_client(url, key)


def get_client():
    """Ambil koneksi Supabase (pakai service_role key dari secrets.toml)."""
    try:
        return _buat_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception:
        st.error("Isi SUPABASE_URL dan SUPABASE_SERVICE_KEY di .streamlit/secrets.toml")
        st.stop()                      # hentikan program di sini


def uid():
    """ID akun yang sedang login. Dipakai di SEMUA query supaya data antar akun tidak tercampur."""
    return st.session_state.user["id"]

# =====================================================================
# 3. DATABASE: ambil & simpan jurnal
# =====================================================================
KOLOM_JURNAL = ["id", "bukti", "tanggal", "keterangan", "jenis", "kode_akun", "debit", "kredit"]


def ambil_semua(tabel):
    """Ambil semua baris tabel. Supabase membatasi 1000 baris per permintaan,
    jadi kita ambil bertahap (halaman demi halaman)."""
    hasil, mulai = [], 0
    while True:
        res = get_client().table(tabel).select("*").eq("user_id", uid()).order("id").range(mulai, mulai + 999).execute()
        hasil += res.data
        if len(res.data) < 1000:
            break
        mulai += 1000
    return hasil


def muat_jurnal():
    """Ambil seluruh jurnal user sebagai DataFrame. Disimpan sementara (cache)
    di session_state supaya tidak query berulang tiap klik."""
    if "jurnal_df" not in st.session_state:
        df = pd.DataFrame(ambil_semua("jurnal"), columns=KOLOM_JURNAL)
        df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date
        df[["debit", "kredit"]] = df[["debit", "kredit"]].astype("int64")
        akun = semua_akun()
        df["nama_akun"] = df["kode_akun"].map(lambda k: akun.get(k, {"nama": k})["nama"])
        df["akun"] = df["kode_akun"].map(lambda k: f"{k} - {akun.get(k, {'nama': k})['nama']}")
        st.session_state.jurnal_df = df.sort_values(["tanggal", "id"]).reset_index(drop=True)
    return st.session_state.jurnal_df


def bersihkan_cache():
    """Hapus cache jurnal -> data diambil ulang dari database di pemuatan berikutnya."""
    st.session_state.pop("jurnal_df", None)


def baris_jurnal(tanggal, keterangan, jenis, entri):
    """Bentuk baris jurnal siap simpan.
    entri = daftar (kode_akun, debit, kredit). Wajib seimbang!"""
    total_d = sum(e[1] for e in entri)
    total_k = sum(e[2] for e in entri)
    if total_d != total_k:
        raise ValueError(f"Jurnal tidak seimbang: debit {total_d} != kredit {total_k}")
    bukti = str(uuid.uuid4())   # satu kode untuk semua baris dalam satu transaksi
    # 'for kode, d, k in entri' = membongkar tiap tuple (kode, debit, kredit)
    return [
        {"user_id": uid(), "bukti": bukti, "tanggal": tanggal.isoformat(), "keterangan": keterangan,
         "jenis": jenis, "kode_akun": kode, "debit": int(d), "kredit": int(k)}
        for kode, d, k in entri
    ]


def simpan_transaksi(tanggal, keterangan, jenis, entri):
    """Simpan satu transaksi (beberapa baris jurnal sekaligus) ke Supabase."""
    get_client().table("jurnal").insert(baris_jurnal(tanggal, keterangan, jenis, entri)).execute()
    bersihkan_cache()


def simpan_banyak(tanggal, daftar):
    """Simpan beberapa jurnal sekaligus dalam SATU insert (semua berhasil atau semua gagal).
    daftar = [(jenis, keterangan, entri), ...]"""
    baris = []
    for jenis, keterangan, entri in daftar:
        baris += baris_jurnal(tanggal, keterangan, jenis, entri)
    if baris:
        get_client().table("jurnal").insert(baris).execute()
    bersihkan_cache()


# =====================================================================
# COA tambahan (tabel coa_custom)
# =====================================================================
def muat_coa():
    """Ambil akun tambahan milik user ke session_state (sekali per sesi)."""
    if "akun_custom" in st.session_state:
        return
    try:
        res = (get_client().table("coa_custom").select("*").eq("user_id", uid()).execute())
        st.session_state.akun_custom = {
            r["kode"]: {"nama": r["nama"], "tipe": r["tipe"], "normal": r["normal"]}
            for r in res.data}
    except Exception as e:
        st.session_state.akun_custom = {}
        st.warning(f"Tabel coa_custom belum bisa dibaca (sudah menjalankan schema_update.sql?): {e}")


def tambah_akun(kode, nama, tipe, normal):
    get_client().table("coa_custom").insert(
        {"user_id": uid(), "kode": kode, "nama": nama, "tipe": tipe, "normal": normal}).execute()
    st.session_state.akun_custom[kode] = {"nama": nama, "tipe": tipe, "normal": normal}
    bersihkan_cache()          # nama akun di jurnal dibaca ulang


def hapus_akun(kode):
    get_client().table("coa_custom").delete().eq("user_id", uid()).eq("kode", kode).execute()
    st.session_state.akun_custom.pop(kode, None)
    bersihkan_cache()


# =====================================================================
# Daftar harga persediaan (tabel daftar_persediaan)
# =====================================================================
KOLOM_HARGA = ["kategori", "nama", "satuan", "harga_satuan"]


def muat_harga():
    """Daftar barang + harga jual satuan sebagai DataFrame."""
    if "harga_df" not in st.session_state:
        res = (get_client().table("daftar_persediaan").select("*")
               .eq("user_id", uid()).order("kategori").order("nama").execute())
        df = pd.DataFrame(res.data, columns=KOLOM_HARGA + ["id"]).drop(columns="id")
        df["harga_satuan"] = df["harga_satuan"].astype("int64")
        st.session_state.harga_df = df
    return st.session_state.harga_df


def simpan_harga(df):
    """Ganti seluruh daftar harga user dengan isi df (kolom: kategori, nama, satuan, harga_satuan)."""
    sb, u = get_client(), uid()
    baris = [{"user_id": u, **{k: r[k] for k in KOLOM_HARGA}} for r in df.to_dict("records")]
    sb.table("daftar_persediaan").delete().eq("user_id", u).execute()
    if baris:
        sb.table("daftar_persediaan").insert(baris).execute()
    st.session_state.pop("harga_df", None)


def muat_item_peralatan():
    """Rincian peralatan dari saldo awal (nama, nominal, umur_bulan) untuk saran penyusutan."""
    res = (get_client().table("saldo_awal_item").select("*")
           .eq("user_id", uid()).eq("kelompok", "peralatan").execute())
    return res.data

# ---------- Status saldo awal ----------
def saldo_awal_selesai():
    """Cek di database: apakah akun ini sudah menyelesaikan saldo awal?"""
    res = (get_client().table("profil").select("saldo_awal_selesai")
           .eq("user_id", uid()).execute())
    return bool(res.data and res.data[0]["saldo_awal_selesai"])

# ---------- Penyimpanan saldo awal ----------
def simpan_saldo_awal(d, tanggal):
    """Simpan saldo awal ke Supabase: jurnal + rincian + tanda 'selesai'."""
    sb = get_client()
    u = uid()
    entri = entri_saldo_awal(d)
    # hapus sisa percobaan sebelumnya milik akun ini (jika sempat gagal di tengah jalan)
    sb.table("jurnal").delete().eq("user_id", u).eq("jenis", "saldo_awal").execute()
    sb.table("saldo_awal_item").delete().eq("user_id", u).execute()
    if entri:
        sb.table("jurnal").insert(
            baris_jurnal(tanggal, "Saldo awal", "saldo_awal", entri)).execute()
    items = [{**it, "user_id": u} for it in item_saldo_awal(d)]   # tambahkan user_id ke tiap baris
    if items:
        sb.table("saldo_awal_item").insert(items).execute()
    # terakhir: tandai selesai (upsert = insert, atau update jika sudah ada)
    sb.table("profil").upsert({"user_id": u, "saldo_awal_selesai": True}).execute()
    bersihkan_cache()
    st.session_state.sa_selesai = True
    st.session_state.pop("sa", None)
