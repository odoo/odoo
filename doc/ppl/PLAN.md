# Software Requirements Specification (SRS)
## ERP SIFNEXT — MVP (Minimum Viable Product)

**Versi:** 1.0
**Tanggal:** 4 September 2026
**Status:** Final untuk Sprint MVP (4-8 September 2026)
**Tugas Tim Saya Adalah Bagian Feature 3.3.4 PPL (Permintaan Pembayaran Langsung)**
---

Jika sudah membaca halaman ini pergilah ke halaman berikutnya:
- D:\projects\odoo\doc\ppl\PPL_IMPLEMENTATION_PLAN.md

## 1. Pendahuluan

### 1.1 Tujuan Dokumen
Dokumen ini berisi spesifikasi kebutuhan perangkat lunak (SRS) untuk pengembangan MVP ERP SIFNEXT. Dokumen ini menjadi acuan tunggal (roadmap.md) bagi seluruh tim pengembang (Human Capital, Operasional, dan Keuangan) dalam mengimplementasikan fitur-fitur yang ditargetkan selesai pada 8 September 2026.

### 1.2 Ruang Lingkup
Ruang lingkup SRS ini mencakup **12 modul MVP** yang terbagi dalam 3 squad pengembangan:

1.  **Squad Human Capital (HC):** Presensi, Cuti, Dispensasi, Lembur, Payroll (dengan 6 sub-modul).
2.  **Squad Operasional:** Peminjaman Ruangan dan Peminjaman Kendaraan Dinas.
3.  **Squad Keuangan:** RKA, Jurnal Besar, Aset, dan PPL.

Modul di luar daftar ini (seperti Dashboard Keuangan Tahunan, Administrasi Kemahasiswaan, dan fitur lanjutan lainnya) **TIDAK** termasuk dalam cakupan MVP dan akan dikembangkan pada Fase 2.

### 1.3 Teknologi dan Integrasi
- **Platform:** Odoo (dengan memanfaatkan modul-modul standar dan kustomisasi).
- **Integrasi Eksternal:** Aplikasi absensi **Presenly** (untuk data check-in/out, jam kerja, dan jatah cuti).

---

## 2. Arsitektur Solusi dan Pendekatan Pengembangan

### 2.1 Prinsip Pengembangan
1.  **API-First:** Semua modul dibangun dengan mempertimbangkan ketersediaan API untuk integrasi.
2.  **Integrasi Progresif:** Integrasi antar modul (HC -> Payroll, Payroll -> PPL) menjadi fokus utama di akhir sprint.
3.  **Validasi Berkelanjutan:** Setiap modul divalidasi silang oleh tim lain segera setelah selesai, bukan menunggu akhir sprint.

### 2.2 Pendekatan Integrasi Presenly
- **Metode:** Pull data via API Presenly.
- **Data yang Ditarik:**
    - Data Karyawan (Nama, NIK, Unit, Divisi, Jenis Kepegawaian).
    - Data Absensi Harian (Check-in, Check-out, Status Hadir/Terlambat).
    - Data Cuti (Sisa Jatah Cuti).
- **Sinkronisasi:** Data ditarik secara manual atau via cron job sederhana untuk keperluan payroll.

---

## 3. Spesifikasi Kebutuhan Fungsional per Modul

### 3.1 Modul Human Capital (HC)

#### 3.1.1 Presensi
- **Fungsi:**
    - Mengintegrasikan data check-in/out dari Presenly ke dalam sistem Odoo.
    - Menampilkan data presensi harian karyawan (Hadir, Terlambat, Izin, Cuti).
    - Mencegah duplikasi check-in dalam sehari.
- **Data Master:** Data Karyawan (sinkron dari Presenly).
- **Kriteria Penerimaan (DoD - Definition of Done):**
    - Data presensi hari ini dapat dilihat oleh karyawan dan HR.
    - Status "Hadir" atau "Terlambat" ditentukan secara otomatis berdasarkan jam kerja yang berlaku.
    - Rekap presensi tersedia sebagai sumber data untuk modul Payroll.

#### 3.1.2 Cuti
- **Fungsi:**
    - Karyawan dapat mengajukan cuti (tanggal, jenis cuti, alasan).
    - Sistem otomatis mengecek sisa jatah cuti (data dari Presenly).
    - Alur persetujuan (Approval) oleh Atasan/HR.
    - Jika disetujui, sisa jatah cuti otomatis berkurang dan status cuti tercatat di sistem.
- **Kriteria Penerimaan (DoD):**
    - Pengajuan cuti tidak dapat dilakukan jika sisa jatah cuti 0.
    - Status cuti (Draft, Diajukan, Disetujui, Ditolak) tercatat.
    - Data cuti yang disetujui menjadi salah satu sumber data untuk perhitungan payroll.

#### 3.1.3 Dispensasi
- **Fungsi:**
    - Karyawan dapat mengajukan izin/dispensasi (tanggal, alasan, upload lampiran pendukung).
    - Alur persetujuan (Approval) oleh Atasan/HR .
    - Data dispensasi yang disetujui tersimpan sebagai data kehadiran.
- **Kriteria Penerimaan (DoD):**
    - Formulir pengajuan memiliki field tanggal, alasan, dan upload file lampiran.
    - Status pengajuan tercatat dan dapat dilacak.

#### 3.1.4 Lembur
- **Fungsi:**
    - Karyawan mengajukan lembur dengan mengisi detail durasi lembur.
    - Sistem mengecek ketersediaan anggaran dasar (RKA) dari modul Keuangan.
    - Jika anggaran tersedia, pengajuan dilanjutkan ke proses Approval Atasan.
    - Setelah approval, lembur dapat direalisasikan (check-out lembur).
    - Sistem menghitung otomatis komponen uang makan jika durasi lembur > 3 jam.
- **Data Master:** Anggaran RKA (dari modul Keuangan).
- **Kriteria Penerimaan (DoD):**
    - Lembur tidak dapat diajukan jika anggaran tidak tersedia.
    - Komponen uang makan ditambahkan secara otomatis jika durasi > 3 jam.
    - Data lembur yang sudah direalisasi menjadi sumber data untuk payroll.

#### 3.1.5 Payroll (Sub-modul)
Modul ini merupakan integrasi dari 6 sub-modul yang saling terhubung.

- **3.1.5.1 Payroll - Pusat Sinkronisasi**
    - Menarik dan mengonsolidasi data dari Presensi, Cuti, dan Lembur sebagai sumber data perhitungan gaji.
- **3.1.5.2 Payroll - Data Gaji**
    - Menghitung gaji pokok + tunjangan - potongan per karyawan.
    - Menampilkan rincian komponen gaji.
- **3.1.5.3 Payroll - Potongan Tetap**
    - Mengelola master data potongan rutin per karyawan (misal: cicilan koperasi, dll) dengan nilai tetap.
- **3.1.5.4 Payroll - Kalkulasi BPJS**
    - Mengkonfigurasi rate BPJS Kesehatan dan Ketenagakerjaan.
    - Menghitung potongan iuran BPJS dari gaji karyawan secara otomatis.
- **3.1.5.5 Payroll - Approval Gaji**
    - Menyediakan alur approval 1 tingkat untuk finalisasi payroll.
- **3.1.5.6 Payroll - Data Gaji Diproses / Slip Gaji**
    - Menghasilkan dan menampilkan slip gaji dasar per karyawan per periode.
    - Menyimpan riwayat batch gaji yang sudah diproses.

**Kriteria Penerimaan Payroll (DoD):**
- Perhitungan gaji terintegrasi dengan data presensi, cuti, dan lembur.
- Slip gaji dapat diakses oleh karyawan (dalam format pdf atau tampilan web).
- Data payroll final siap untuk dikirim ke modul PPL (Permintaan Pembayaran).

---

### 3.2 Modul Operasional

#### 3.2.1 Peminjaman Ruangan
- **Fungsi:**
    - Pengguna mengajukan peminjaman ruangan (tanggal, jam, durasi, kapasitas).
    - Sistem mengecek ketersediaan ruangan di jadwal yang diminta.
    - Alur approval oleh Admin/Operasional (1 level).
    - Jika disetujui, ruangan dibooking dan jadwal tercatat.
- **Kriteria Penerimaan (DoD):**
    - Tidak ada double-booking untuk ruangan yang sama di jam yang sama.
    - Status peminjaman (Draft, Diajukan, Disetujui, Ditolak) tercatat.

#### 3.2.2 Peminjaman Kendaraan Dinas
- **Fungsi:**
    - Pengguna mengajukan peminjaman kendaraan (tanggal, jam, durasi, tujuan).
    - Sistem mengecek ketersediaan kendaraan.
    - Alur approval oleh Admin/Operasional (1 level).
    - Jika disetujui, kendaraan dibooking dan jadwal tercatat.
- **Kriteria Penerimaan (DoD):**
    - Tidak ada double-booking untuk kendaraan yang sama di jam yang sama.
    - Status peminjaman tercatat.

---

### 3.3 Modul Keuangan

#### 3.3.1 RKA (Rencana Kerja & Anggaran)
- **Fungsi:**
    - Menginput dan mengelola anggaran per unit/departemen (struktur flat, satu tingkat).
    - Menampilkan total anggaran tahunan, realisasi, dan sisa anggaran per unit.
- **Kriteria Penerimaan (DoD):**
    - Data RKA terlihat di dashboard anggaran.
    - Modul Lembur dan PPL dapat mengakses data RKA untuk pengecekan anggaran.

#### 3.3.2 Jurnal Besar
- **Fungsi:**
    - Menginput jurnal transaksi keuangan secara manual.
    - Menampilkan buku besar dengan filter periode bulanan sederhana.
- **Kriteria Penerimaan (DoD):**
    - Transaksi dari PPL secara otomatis tercatat ke dalam jurnal.
    - Laporan buku besar dapat difilter per bulan.

#### 3.3.3 Aset
- **Fungsi:**
    - Menginput data aset dasar: kode aset, nama, kategori, unit pemilik, tanggal & nilai perolehan.
- **Kriteria Penerimaan (DoD):**
    - Daftar aset dapat dilihat dan dicari per unit atau kategori. (Fitur penyusutan dan kapitalisasi otomatis TIDAK termasuk dalam MVP).

#### 3.3.4 PPL (Permintaan Pembayaran Langsung)
- **Fungsi:**
    - Membuat permintaan pembayaran (PPL) untuk berbagai keperluan.
    - **Use-case Prioritas:** Pengajuan pembayaran gaji dari hasil payroll final.
    - Setiap item/detail PPL dapat memiliki beberapa lampiran bukti pendukung.
    - Lampiran item bersifat opsional dan hanya dapat ditambah, diubah, atau dihapus saat PPL berstatus Draft.
    - Nomor PPL dibuat otomatis dengan format sederhana (`[Unit]/PPL/[MM]/[YYYY]/[No-Urut]`) dan terkunci.
    - Sistem menampilkan total anggaran, realisasi, dan sisa anggaran dari RKA.
    - Alur approval/verifikasi PPL oleh Tim Keuangan atau Direktur.
- **Kriteria Penerimaan (DoD):**
    - PPL dapat dibuat langsung dari data payroll final.
    - Nomor PPL tidak dapat diubah oleh user.
    - Status PPL (Draft, Diajukan, Diverifikasi, Disetujui, Dibayar, Selesai) tercatat.
    - PPL yang sudah disetujui otomatis memicu pembuatan jurnal transaksi melalui kontrak integrasi Jurnal Besar.
    - Integrasi wajib idempotent dan kegagalan pencatatan jurnal membatalkan perubahan status pembayaran.

---

## 4. Spesifikasi Kebutuhan Non-Fungsional

### 4.1 Keamanan dan Akses
- **Hak Akses:** Implementasi hak akses berbasis peran (Role-Based Access Control - RBAC).
    - **Karyawan:** Akses ke Presensi, Cuti, Izin, Lembur, dan Slip Gaji.
    - **Atasan/HR:** Akses Approval untuk Cuti, Izin, Lembur, dan Payroll.
    - **Admin GA:** Akses Approval Peminjaman Ruangan & Kendaraan.
    - **Tim Keuangan:** Akses Approval PPL, RKA, Jurnal, dan Aset.
- **Notifikasi:** Notifikasi pop-up/browser untuk setiap permintaan approval yang masuk ke pengguna terkait.

### 4.2 Performa dan Skalabilitas
- Sistem harus responsif untuk penggunaan simultan oleh minimal 500 user.
- Proses perhitungan payroll (lebih dari 100 karyawan) harus selesai dalam waktu < 5 detik.

### 4.3 Audit Trail
- **Semua modul** harus mencatat setiap perubahan status data (Created, Updated, Approved, Rejected) beserta timestamp dan user yang melakukan.

---


## 5. Definisi Selesai (Definition of Done - DoD)

Sebuah modul atau fitur dianggap selesai ketika memenuhi kriteria berikut:

1.  **Kode:** Kode telah ditulis, direview, dan di-commit ke branch utama.
2.  **Testing:** Unit test dan integration test dasar telah dilakukan dan lulus.
3.  **Dokumentasi:** API endpoint dan fungsi utama telah didokumentasikan.
4.  **UAT:** Fitur telah divalidasi oleh Product Owner atau perwakilan pengguna (UAT).
5.  **Integrasi:** Fitur berhasil terintegrasi dengan modul upstream/downstream yang relevan (sesuai alur).

---

## 6. Daftar Item untuk Fase 2 (Di Luar MVP)

Fitur-fitur berikut TIDAK termasuk dalam cakupan sprint 4-8 September dan akan dikembangkan setelah MVP stable.

1.  **Human Capital:**
    - Aturan jatah cuti spesifik per jenis kepegawaian.
    - Template ekspor Coretax untuk PPh 21.
    - Approval berlapis (multi-level) untuk cuti dan payroll.
    - Penggajian lintas unit penuh.
    - Otomatisasi reminder dan notifikasi lanjutan.

2.  **Keuangan:**
    - Dashboard Keuangan Tahunan.
    - Struktur RKA berjenjang (induk-child).
    - Kapitalisasi dan penyusutan aset otomatis.
    - Subledger untuk Customer & Vendor.
    - Integrasi Host-to-Host dengan Bank.
    - Penguncian periode transaksi.

3.  **Operasional:**
    - Sinkronisasi kalender dan notifikasi reminder.
    - Pelacakan pemakaian kendaraan (maintenance).

4.  **Dashboard Manajemen:**
    - Monitoring real-time untuk Direksi.
