# Dokumentasi Modul SIFNEXT Keuangan (`sif_keuangan`)

Branch: `feature/rev-jurnal-sif`  
Basis: Odoo 19 Community

---

## 1. Tampilan Siskeu SIF & Laporan

* **Buku Besar (`sif.jurnal.line`):** Tampil mendatar (*flat list*, tanpa lipatan *accordion*).
  * Kolom: `Tanggal`, `Unit Kerja`, `Bukti / Nomer` (JYYMMxxxx), `Kwitansi`, `Keterangan`, `Account`, `Nama Account`, `Debet`, `Kredit` (dilengkapi baris total di bawah).
* **Filter Periode Tanggal (`sif.buku.besar.wizard`):**
  * Pop-up dialog otomatis saat menu Buku Besar diklik (input Tanggal Awal & Tanggal Akhir).
  * Tersedia tombol **"Ganti Periode Tanggal"** di header tabel.

---

## 2. Integrasi PPL (`sifnext_ppl`)

* **Method RPC:** `create_journal_from_ppl(vals)` (menerima payload *dictionary* maupun *recordset* PPL).
* **Aturan PPN:** PPN Masukan masuk kelompok **Aset Lancar** (Debit), bukan Beban atau Liabilitas.
* **Struktur Baris Jurnal:**
  * **Debit:** Beban Belanja (DPP) + PPN Masukan (Akun Aset).
  * **Kredit:** Kas / Bank Pembayar (Total uang keluar).
* **Output:** Me-return objek jurnal (`return entry`) agar ID/nomor jurnal tersimpan di riwayat PPL.
* **Kwitansi:** Menampung nomor bukti pembayaran fisik dari PPL ke kolom `kwitansi_ref`.

---

## 3. Integrasi Modul Aset

* **Perolehan Aset:** `create_asset_purchase_journal(...)`  
  * Debit: Akun Aset Tetap | Kredit: Kas / Hutang Usaha.
* **Penyusutan Bulanan:** `create_asset_depreciation_journal(...)`  
  * Debit: Beban Penyusutan | Kredit: Akumulasi Penyusutan (Akun Kontra 24007).

---