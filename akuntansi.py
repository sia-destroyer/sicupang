"""Perhitungan akuntansi dan penyusunan laporan SiCupang."""

import pandas as pd

from COA import (semua_akun, HPP_AKUN, AKUN_PERSEDIAAN, PERLENGKAPAN, BEBAN_PERLENGKAPAN,
                 AKUM_PENYUSUTAN, BEBAN_PENYUSUTAN, IKHTISAR, MODAL, PRIVE,
                 KAS_TANGAN, KAS_BANK)

# =====================================================================
# 4. PERHITUNGAN AKUNTANSI
# =====================================================================
def saldo_per_akun(df):
    """Hitung saldo tiap akun. Saldo dihitung sesuai sisi normalnya:
       akun normal Debit  -> saldo = debit - kredit
       akun normal Kredit -> saldo = kredit - debit
    Hasil: {"1-101": 5000000, ...}"""
    g = df.groupby("kode_akun")[["debit", "kredit"]].sum()
    hasil = {}
    for kode, info in semua_akun().items():
        if kode in g.index:
            d, k = int(g.at[kode, "debit"]), int(g.at[kode, "kredit"])
        else:
            d = k = 0
        hasil[kode] = d - k if info["normal"] == "D" else k - d
    return hasil


def total_tipe(saldo, tipe):
    """Jumlahkan saldo semua akun bertipe tertentu (mis. 'Pendapatan')."""
    akun = semua_akun()
    return sum(s for kode, s in saldo.items() if akun[kode]["tipe"] == tipe)


def filter_periode(df, awal=None, akhir=None):
    """Ambil baris jurnal pada rentang tanggal tertentu."""
    if awal is not None:
        df = df[df["tanggal"] >= awal]
    if akhir is not None:
        df = df[df["tanggal"] <= akhir]
    return df


def tanpa_penutup(df):
    """Buang jurnal penutup. Dipakai untuk laporan laba rugi / dashboard, supaya
    pendapatan & beban tetap terlihat walau periodenya sudah ditutup."""
    return df[df["jenis"] != "penutup"]


def nilai_persediaan_iktisar(df):
    """Persediaan awal & akhir yang dipindahkan lewat Iktisar Laba Rugi saat penyesuaian.
    Debit iktisar = persediaan awal, Kredit iktisar = persediaan akhir."""
    ik = df[(df["kode_akun"] == IKHTISAR) & (df["jenis"] == "penyesuaian")]
    return int(ik["debit"].sum()), int(ik["kredit"].sum())


def hitung_laba(df):
    """(pendapatan, beban, laba). df = jurnal tanpa penutup. Beban sudah memperhitungkan
    persediaan awal dan akhir jika penyesuaian sudah dibuat."""
    s = saldo_per_akun(df)
    awal, akhir = nilai_persediaan_iktisar(df)
    pendapatan = total_tipe(s, "Pendapatan")
    beban = total_tipe(s, "Beban") + awal - akhir
    return pendapatan, beban, pendapatan - beban


# =====================================================================
# Laporan
# =====================================================================
def laporan_jurnal_umum(df):
    """Jurnal umum murni: tanpa saldo awal. Nama akun saja (tanpa kode),
    akun kredit dijorok ke kanan (aturan penulisan jurnal)."""
    df = df[df["jenis"] != "saldo_awal"]
    j = pd.DataFrame({
        "Tanggal": df["tanggal"],
        "Bukti": df["bukti"].str[:8],
        "Keterangan": df["keterangan"],
        "Akun": [("      " + a) if k > 0 else a for a, k in zip(df["nama_akun"], df["kredit"])],
        "Debit": df["debit"],
        "Kredit": df["kredit"],
    })
    return j.reset_index(drop=True)


def laporan_buku_besar(df, kode):
    """Buku besar satu akun + saldo berjalan."""
    d = df[df["kode_akun"] == kode].sort_values(["tanggal", "id"])
    normal = semua_akun()[kode]["normal"]
    saldo, baris = 0, []
    for _, r in d.iterrows():
        saldo += (r["debit"] - r["kredit"]) if normal == "D" else (r["kredit"] - r["debit"])
        baris.append({"Tanggal": r["tanggal"], "Keterangan": r["keterangan"],
                      "Debit": r["debit"], "Kredit": r["kredit"], "Saldo": saldo})
    return pd.DataFrame(baris, columns=["Tanggal", "Keterangan", "Debit", "Kredit", "Saldo"])


def laporan_neraca_saldo(df):
    """Neraca saldo (trial balance): saldo akhir tiap akun di kolom Debit ATAU Kredit.
    Total Debit harus sama dengan total Kredit."""
    baris = []
    for kode, info in semua_akun().items():
        d = int(df.loc[df["kode_akun"] == kode, "debit"].sum())
        k = int(df.loc[df["kode_akun"] == kode, "kredit"].sum())
        if d == 0 and k == 0:
            continue
        net = d - k
        baris.append({"Kode": kode, "Akun": info["nama"],
                      "Debit": net if net > 0 else 0,
                      "Kredit": -net if net < 0 else 0})
    t = pd.DataFrame(baris, columns=["Kode", "Akun", "Debit", "Kredit"])
    total = pd.DataFrame([{"Kode": "", "Akun": "TOTAL",
                           "Debit": t["Debit"].sum(), "Kredit": t["Kredit"].sum()}])
    return pd.concat([t, total], ignore_index=True)


def laporan_laba_rugi(df):
    """Laporan laba rugi. df = jurnal pada periode (jurnal penutup diabaikan).
    Susunan: Pendapatan - Harga Pokok Penjualan = Laba Kotor - Beban Operasional."""
    df = tanpa_penutup(df)
    akun = semua_akun()
    s = saldo_per_akun(df)
    awal, akhir = nilai_persediaan_iktisar(df)
    baris = []                                    # (keterangan, jumlah)

    baris.append(("PENDAPATAN", None))
    for kode, info in akun.items():
        if info["tipe"] == "Pendapatan" and s[kode] != 0:
            baris.append(("    " + info["nama"], s[kode]))
    pendapatan = total_tipe(s, "Pendapatan")
    baris.append(("Total Pendapatan", pendapatan))
    baris.append(("", None))

    hpp = 0
    akun_hpp = [k for k in HPP_AKUN if k in akun and s[k] != 0]
    if akun_hpp or awal or akhir:
        baris.append(("HARGA POKOK PENJUALAN", None))
        baris.append(("    Persediaan awal", awal))
        pembelian = 0
        for kode in akun_hpp:
            baris.append(("    " + akun[kode]["nama"], s[kode]))
            pembelian += s[kode]
        baris.append(("    Barang tersedia untuk dijual", awal + pembelian))
        baris.append(("    Persediaan akhir", -akhir))
        hpp = awal + pembelian - akhir
        baris.append(("Total Harga Pokok Penjualan", hpp))
        baris.append(("LABA KOTOR", pendapatan - hpp))
        baris.append(("", None))

    baris.append(("BEBAN OPERASIONAL", None))
    total_beban = 0
    for kode, info in akun.items():
        if info["tipe"] == "Beban" and kode not in HPP_AKUN and s[kode] != 0:
            baris.append(("    " + info["nama"], s[kode]))
            total_beban += s[kode]
    baris.append(("Total Beban Operasional", total_beban))
    baris.append(("", None))
    baris.append(("LABA (RUGI) BERSIH", pendapatan - hpp - total_beban))
    return pd.DataFrame(baris, columns=["Keterangan", "Jumlah"])


def laporan_neraca(df):
    """Neraca (laporan posisi keuangan) per tanggal. df = jurnal sampai tanggal itu.
    Return (tabel, total_aset, total_liabilitas_ekuitas)."""
    akun = semua_akun()
    s = saldo_per_akun(df)
    baris = []

    def seksi(judul, tipe):
        baris.append((judul, None))
        total = 0
        for kode, info in akun.items():
            if info["tipe"] != tipe or s[kode] == 0:
                continue
            # aset: sisi debit positif; liabilitas/ekuitas: sisi kredit positif
            sisi_positif = "D" if tipe == "Aset" else "K"
            nilai = s[kode] if info["normal"] == sisi_positif else -s[kode]
            baris.append(("    " + info["nama"], nilai))
            total += nilai
        return total

    aset = seksi("ASET", "Aset")
    baris.append(("TOTAL ASET", aset))
    baris.append(("", None))
    liabilitas = seksi("LIABILITAS", "Liabilitas")
    baris.append(("Total Liabilitas", liabilitas))
    baris.append(("", None))
    ekuitas = seksi("EKUITAS", "Ekuitas")
    # laba yang belum ditutup (jika penutupan belum dibuat) tetap masuk ekuitas
    laba_berjalan = total_tipe(s, "Pendapatan") - total_tipe(s, "Beban")
    if laba_berjalan != 0:
        baris.append(("    Laba (Rugi) Berjalan", laba_berjalan))
        ekuitas += laba_berjalan
    baris.append(("Total Ekuitas", ekuitas))
    baris.append(("", None))
    baris.append(("TOTAL LIABILITAS + EKUITAS", liabilitas + ekuitas))
    return pd.DataFrame(baris, columns=["Keterangan", "Jumlah"]), aset, liabilitas + ekuitas


# =====================================================================
# Penyesuaian & penutupan (metode Iktisar Laba Rugi)
# =====================================================================
def _df_baris(tanggal, jenis, entri):
    """DataFrame sementara dari daftar entri, untuk menghitung saldo sebelum disimpan."""
    return pd.DataFrame(
        [{"tanggal": tanggal, "jenis": jenis, "kode_akun": k, "debit": d, "kredit": c}
         for k, d, c in entri],
        columns=["tanggal", "jenis", "kode_akun", "debit", "kredit"])


def susun_penyesuaian(df, tanggal, persediaan_akhir, perlengkapan_sisa, penyusutan):
    """Susun jurnal penyesuaian + penutupan. df = jurnal sampai tanggal penyesuaian.
    persediaan_akhir = {"Ikan": nilai, "Pakan": ..., "Obat": ..., "Lainnya": ...} (hasil opname)
    Return: daftar (jenis, keterangan, entri), tiap entri = [(kode, debit, kredit), ...]
    dan tiap entri seimbang."""
    s = saldo_per_akun(df)
    daftar = []

    # 1) Persediaan: awal -> Iktisar (D), Persediaan (K).  Akhir -> Persediaan (D), Iktisar (K)
    entri = []
    for kat, kode in AKUN_PERSEDIAAN.items():
        if s[kode] > 0:
            entri += [(IKHTISAR, s[kode], 0), (kode, 0, s[kode])]
    for kat, kode in AKUN_PERSEDIAAN.items():
        akhir = int(persediaan_akhir.get(kat, 0))
        if akhir > 0:
            entri += [(kode, akhir, 0), (IKHTISAR, 0, akhir)]
    if entri:
        daftar.append(("penyesuaian", "Penyesuaian persediaan awal dan akhir", entri))

    # 2) Perlengkapan: saldo buku disesuaikan ke hasil hitung sisa. Selisihnya = beban.
    selisih = int(perlengkapan_sisa) - s[PERLENGKAPAN]
    if selisih < 0:
        daftar.append(("penyesuaian", "Penyesuaian perlengkapan terpakai",
                       [(BEBAN_PERLENGKAPAN, -selisih, 0), (PERLENGKAPAN, 0, -selisih)]))
    elif selisih > 0:
        daftar.append(("penyesuaian", "Penyesuaian perlengkapan (sisa lebih besar dari saldo)",
                       [(PERLENGKAPAN, selisih, 0), (BEBAN_PERLENGKAPAN, 0, selisih)]))

    # 3) Penyusutan peralatan
    if int(penyusutan) > 0:
        daftar.append(("penyesuaian", "Penyusutan peralatan",
                       [(BEBAN_PENYUSUTAN, int(penyusutan), 0), (AKUM_PENYUSUTAN, 0, int(penyusutan))]))

    # saldo setelah semua penyesuaian
    cur = df
    for jenis, _, entri in daftar:
        cur = pd.concat([cur, _df_baris(tanggal, jenis, entri)], ignore_index=True)

    # 4) Penutupan: pendapatan & beban -> Iktisar, Iktisar -> Modal, Prive -> Modal
    akun = semua_akun()
    for tipe, nama in (("Pendapatan", "Penutupan pendapatan ke Iktisar Laba Rugi"),
                       ("Beban", "Penutupan beban ke Iktisar Laba Rugi")):
        s2 = saldo_per_akun(cur)
        entri = []
        for kode, info in akun.items():
            if info["tipe"] != tipe or s2[kode] == 0:
                continue
            net = s2[kode] if info["normal"] == "D" else -s2[kode]     # debit - kredit
            if net > 0:       # saldo di debit -> dikreditkan, lawannya Iktisar di debit
                entri += [(IKHTISAR, net, 0), (kode, 0, net)]
            else:
                entri += [(kode, -net, 0), (IKHTISAR, 0, -net)]
        if entri:
            daftar.append(("penutup", nama, entri))
            cur = pd.concat([cur, _df_baris(tanggal, "penutup", entri)], ignore_index=True)

    s2 = saldo_per_akun(cur)
    laba = s2[IKHTISAR]                          # saldo kredit iktisar = laba
    if laba > 0:
        entri = [(IKHTISAR, laba, 0), (MODAL, 0, laba)]
        daftar.append(("penutup", "Penutupan Iktisar Laba Rugi ke Modal (laba)", entri))
    elif laba < 0:
        entri = [(MODAL, -laba, 0), (IKHTISAR, 0, -laba)]
        daftar.append(("penutup", "Penutupan Iktisar Laba Rugi ke Modal (rugi)", entri))
    if s2[PRIVE] > 0:
        daftar.append(("penutup", "Penutupan Prive ke Modal",
                       [(MODAL, s2[PRIVE], 0), (PRIVE, 0, s2[PRIVE])]))
    return daftar


# =====================================================================
# Penyusunan jurnal dan rincian saldo awal
# =====================================================================
def entri_saldo_awal(d):
    """Susun jurnal saldo awal:
       Debit  : kas, kas di bank, piutang, persediaan, perlengkapan, peralatan
       Kredit : utang bank, utang orang
       Modal  : selisihnya (aset - utang) supaya jurnal seimbang."""
    saldo = {}

    def tambah(kode, jumlah):
        if jumlah:
            saldo[kode] = saldo.get(kode, 0) + jumlah

    total = lambda daftar: sum(r["nominal"] for r in daftar)
    tambah(KAS_TANGAN, d.get("kas_tangan", 0))
    tambah(KAS_BANK, d["kas"])
    tambah("1-102", total(d["piutang"]))
    tambah("1-103", total(d["ikan"]))
    tambah("1-104", total(d["pakan"]))
    tambah("1-105", total(d["obat"]))
    tambah("1-106", total(d["lainnya"]))
    tambah("1-107", total(d["perlengkapan"]))
    tambah("1-108", total(d["peralatan"]))
    for r in d["utang"]:
        tambah("2-101" if r["pihak"] == "Bank" else "2-102", r["nominal"])

    akun = semua_akun()
    entri = []
    for kode, jml in saldo.items():
        if akun[kode]["normal"] == "D":
            entri.append((kode, jml, 0))
        else:
            entri.append((kode, 0, jml))
    selisih = sum(e[1] for e in entri) - sum(e[2] for e in entri)
    if selisih > 0:
        entri.append((MODAL, 0, selisih))
    elif selisih < 0:
        entri.append((MODAL, -selisih, 0))
    return entri


def item_saldo_awal(d):
    """Rincian saldo awal (jenis ikan, harga, umur pemakaian, dll) untuk tabel saldo_awal_item."""
    items = []
    if d.get("kas_tangan"):
        items.append({"kelompok": "kas_tangan", "pihak": None, "nama": "Kas",
                      "nominal": d["kas_tangan"], "umur_bulan": None})
    if d["kas"]:
        items.append({"kelompok": "kas_bank", "pihak": None, "nama": "Kas di bank",
                      "nominal": d["kas"], "umur_bulan": None})
    for kelompok in ("utang", "piutang", "ikan", "pakan", "obat", "lainnya",
                     "peralatan", "perlengkapan"):
        for r in d[kelompok]:
            items.append({"kelompok": kelompok, "pihak": r.get("pihak"), "nama": r["nama"],
                          "nominal": r["nominal"], "umur_bulan": r.get("umur")})
    return items
