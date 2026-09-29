# Perbandingan Perubahan dari `b421537` ke Kondisi Sekarang

Dokumen ini menjelaskan perubahan aplikasi dan dampak migrasi sejak commit dasar `b421537` sampai hasil merge pada branch `sif-main-19`. Cakupannya mencakup perubahan branch/departemen, update accounting/PPL dari rekan, resolusi konflik, migrasi, dan kondisi database lokal.

## 1. Snapshot Perbandingan

| Item | Kondisi |
|---|---|
| Commit dasar | `b4215375b876d354b214cdcb7d90123ba5b09692` — `fix(custom_payroll_generate): remove employee_ids field and update preview computation logic`, 23 September 2026 |
| Implementasi awal | `09f2981d743d` — `feat(pendapatan): add branch and department scoping` |
| Commit fitur lanjutan | `5b017c408d23` — `feat(org): apply branch department scope across SIF modules` |
| Update rekan yang digabung | `55a038c7fa27` — `Update accounting and aging report` |
| Branch target | `sif-main-19` |
| Status kode | Hasil merge branch fitur dan update rekan berada di `sif-main-19`; belum di-push |
| Database lokal | `db_sifnext` sudah di-upgrade setelah dump backup dibuat di `/tmp/opencode/db_sifnext_pre_multi_scope_20260928.dump` (5,9 MB) |

Perbandingan ini membandingkan baseline dengan hasil gabungan branch fitur dan update rekan. File lokal Docker/Graphify bukan bagian dari perubahan fitur.

## 2. Ringkasan Perubahan Utama

Pada `b421537`, struktur cabang/departemen belum menjadi dasar terpadu untuk transaksi SIF. Pendapatan, PPL, transfer bank, RKA, dan aset belum seluruhnya membawa dimensi company/departemen yang sama. Master unit khusus PPL (`sifnext.unit`) masih dipakai sebagai sumber departemen di beberapa alur.

Kondisi sekarang:

1. **`hr.department` menjadi master departemen SIF.** Departemen mendapat kode SIF, klasifikasi jurnal legacy, dan company pemilik. Penugasan default departemen pengguna disimpan pada `res.users.department_id`.
2. **Pendapatan dibatasi per company/cabang** dan memiliki `department_id`. Kategori bersifat company-specific, sedangkan department/category/company divalidasi di server.
3. **Jurnal keuangan membawa `company_id` dan `department_id`** bila sumber transaksinya menyediakan dimensi tersebut. Filter company diterapkan pada data baru; jurnal lama tanpa company tetap diperlakukan sebagai data legacy bersama.
4. **PPL dan integrasi payroll memakai department.** Batch payroll lintas department menghasilkan satu PPL per department; relasi ke batch tetap tersedia.
5. **Transfer bank, RKA, dan aset membawa company scope.** Department pada transfer/aset divalidasi terhadap company; RKA dibedakan per company, bukan per department.
6. **Finance pusat bersifat read-only** pada modul dalam scope, termasuk melalui pemeriksaan model/server-side, bukan hanya penyembunyian tombol.
7. **`sifnext.unit` tidak lagi menjadi model aktif.** Migrasi mencadangkan tabel dan relasi lama, memetakan referensi, lalu menghapus tabel lama setelah backup terverifikasi.


## 3. Perubahan per Area Fungsional

### 3.1 Organisasi dan Master Departemen — `sifnext_org`

**Sebelumnya:** belum ada modul fondasi organisasi SIF yang memperluas `hr.department` dan `res.users` untuk kebutuhan cabang/departemen lintas modul.

**Sekarang:**

- `res.company.department_ids` menyediakan daftar departemen pada company.
- `hr.department.sif_code` dibuat otomatis melalui sequence global `DEPT-00001`, dinormalisasi menjadi huruf besar, wajib tersedia, hanya menerima huruf/angka/tanda hubung, serta unik di dalam company. Kode yang sama tetap dapat dipakai oleh company lain.
- `hr.department.sif_journal_unit_dept` mempertahankan klasifikasi akuntansi legacy (TPA, SD, SMP, SMA, Universitas, Yayasan/Kantor Pusat). Field ini berbeda dari kode dan nama departemen.
- `res.users.department_id` menjadi department default pengguna. Domain UI dan constraint server membatasi pilihan pada company yang terdapat di `user.company_ids`.
- Form company mendapatkan tab **Departemen** untuk admin; form user menampilkan penugasan departemen.
- Pembuatan department dengan kode duplikat dicegah sebelum konflik database, lalu tetap dilindungi constraint/validasi model.


### 3.2 Pendapatan — `pendapatan`

**Sebelumnya:** `company_id` sudah ada, tetapi lokasi/unit kerja masih berupa teks bebas `unit_name`; daftar belum membawa relasi departemen dan belum memiliki batas record company yang cukup untuk struktur cabang.

**Sekarang:**

- Transaksi Pendapatan memiliki `company_id` dan `department_id`; department default berasal dari department pengguna jika cocok dengan company aktif.
- `create`, `write`, constraint, jalur external API, dan workflow memvalidasi company yang diizinkan serta kecocokan company–department–category.
- `unit_name` dipertahankan untuk histori/kompatibilitas, tetapi transaksi baru menggunakan department.
- Kategori tetap memiliki company, kode unik per company, domain COA berdasarkan tipe akun, dan proteksi server-side terhadap perubahan oleh Finance pusat.
- ACL dan record rule membatasi record menurut company yang diizinkan. Pendapatan User dapat melihat semua department dalam company yang boleh diakses; department bukan pembatas visibilitas user.
- Finance pusat dapat membaca lintas company yang diizinkan, tetapi tidak dapat create/write/unlink atau menjalankan approval/posting melalui model.
- Wizard laporan menerima company, department opsional, kategori, rentang tanggal, status, dan pengelompokan kategori/department/bulan.
- Posting Pendapatan meneruskan company, department, nama department sebagai teks legacy, dan klasifikasi jurnal ke jurnal keuangan.
- View list/form/search menampilkan company dan department, filter/group-by department, serta kategori yang difilter berdasarkan company.


**File utama:**

- `custom_addons/pendapatan/models/pendapatan.py`
- `custom_addons/pendapatan/models/pendapatan_category.py`
- `custom_addons/pendapatan/security/security_groups.xml`
- `custom_addons/pendapatan/security/ir.model.access.csv`
- `custom_addons/pendapatan/views/pendapatan_views.xml`
- `custom_addons/pendapatan/views/pendapatan_category_views.xml`
- `custom_addons/pendapatan/wizard/laporan_pendapatan_wizard.py`
- `custom_addons/pendapatan/wizard/laporan_pendapatan_wizard_views.xml`
- `custom_addons/pendapatan/tests/test_branch_department_scope.py`

### 3.3 Jurnal dan Laporan Keuangan — `sif_keuangan`

**Sekarang:**

- Header `sif.jurnal.entry` menyimpan `company_id` dan `department_id`; baris jurnal dan model Buku Besar mewarisi kedua dimensi tersebut.
- Jurnal Pendapatan diwajibkan memiliki department; department harus berasal dari company yang sama.
- Pembuatan jurnal PPL dan pembelian/penyusutan aset menerima company/department, dan klasifikasi jurnal legacy tetap dikirim bila tersedia.
- Jurnal dengan `company_id` kosong tetap termasuk dalam domain laporan sebagai data legacy bersama. Jurnal dengan company terisi hanya terlihat pada company yang diizinkan.
- Buku Besar mendukung filter company dan department terstruktur, sambil mempertahankan filter teks legacy `unit_name`.
- Neraca dan Laba Rugi mendapat company scope. Filter teks department/unit lama dipertahankan untuk kompatibilitas laporan historis.
- Controller export PDF/XLSX, wizard, dan komponen laporan menggunakan filter yang sama agar ekspor tidak melewati company scope.
- COA dan jurnal memiliki pemeriksaan Finance pusat read-only untuk create/write/unlink; ACL/record rule juga disesuaikan.
- Master COA mendapat relasi `child_ids`, input saldo awal untuk COA leaf, dan saldo awal terhitung rekursif untuk COA parent. Data seed COA diperbarui.
- Update seed COA rekan menghapus 21 XML ID lama. File `sif_coa_legacy_data.xml` mempertahankan akun-akun tersebut sebagai nonaktif agar referensi histori ke jurnal/RKA/aset/PPL tidak putus.
- Master Vendor baru (`sif.vendor`) menyimpan kode sequence, nama, telepon, email, alamat, dan status aktif.
- Laporan **Umur Utang Dagang** menghitung PPL berstatus approved dengan payment term jatuh tempo per company/vendor dan tanggal laporan; bucket umur: current, 1–30, 31–60, 61–90, 91–120, dan lebih tua.


### 3.4 PPL dan Integrasi Payroll — `sifnext_ppl`

**Sebelumnya:** PPL menggunakan `unit_id` ke `sifnext.unit`; `res.users.unit_id` menjadi default. PPL payroll memilih unit pertama yang ditemukan untuk company batch.

**Sekarang:**

- Header PPL memakai `department_id` ke `hr.department`, wajib cocok dengan `company_id`, dan default dari department pemohon.
- Nomor PPL dibuat dari kode department ditambah sequence PPL. Constraint nomor PPL dibuat company-aware.
- PPL juga dapat menunjuk master `sif.vendor` dan memiliki payment term Langsung/Jatuh Tempo. Jatuh Tempo wajib memiliki `due_date`, `batas_waktu` dihitung, dan pembayaran ditolak sebelum tanggal jatuh tempo.
- Detail payload integrasi membawa `applicant`, `vendor`, dan objek `department` (id/kode/nama); key `unit` tetap tersedia sementara dengan isi department untuk konsumen lama.
- PPL menyimpan `payroll_batch_id`; batch payroll menampilkan `ppl_ids` dan mempertahankan `ppl_id` sebagai alias/shortcut ke satu PPL.
- Proses batch yang sudah approved mengelompokkan slip bernilai positif berdasarkan `employee.department_id`; setiap kelompok menjadi satu PPL. Department kosong memakai fallback “Belum Diklasifikasikan” pada company batch; department lintas company ditolak.
- Form/list/search PPL menampilkan department. Form batch mendapat tombol **Buat PPL per Departemen** dan smart button untuk membuka PPL yang dihasilkan.
- Security PPL memakai department/company scope baru. Finance pusat dapat membaca lintas branch yang diizinkan, tetapi model menolak perubahan.
- Sesuai keputusan merge, pegawai biasa tetap hanya dapat membaca PPL milik sendiri; Finance/Direktur dapat membaca PPL sesuai role di company yang diizinkan. Perubahan remote yang memperluas rule pegawai menjadi company-wide tidak diadopsi.
- Model dan view `sifnext.unit` dihapus; kontrak API `unit` dipertahankan sementara, bukan sebagai master aktif.


### 3.5 Transfer Bank — `transaksi`

- Header transfer mengganti relasi unit dengan `department_id`, memakai `company_id`, dan default department dari pemohon.
- Pilihan/validasi department mengikuti company transfer. Jika transfer berasal dari satu atau beberapa PPL, company dan department diambil dari PPL; header tidak memaksakan satu department untuk beberapa PPL lintas department.
- Detail transfer menyediakan department turunan dari PPL atau header.
- Pembuatan transfer tunggal/kolektif dari PPL meneruskan company dan department.
- Record rule global membatasi company. Rule pemohon tetap membatasi dokumen sendiri; Finance/Direktur dapat melihat data sesuai role dalam company yang diizinkan.
- Finance pusat mendapat ACL baca saja, rule lintas company yang diizinkan, dan pemeriksaan server-side pada create/write/unlink.
- Migrasi mengisi department dari unit legacy atau PPL terkait; transaksi yang tidak punya mapping memakai fallback company. Header yang menggabungkan beberapa department tetap tidak diberi satu department yang salah.


### 3.6 Anggaran — `sif_rka`

- `sif.rka.budget` dan baris bulanan memiliki company; baris bulanan mengikuti company parent RKA.
- Unique key berubah dari `(account_id, tahun)` menjadi `(company_id, account_id, tahun)`, sehingga akun/tahun yang sama boleh dianggarkan terpisah per company.
- Create/write, pencarian parent, dashboard, report, detail bulanan, top-3 pengeluaran, realisasi, dan aksi membuka jurnal memakai company yang sama.
- Realisasi dari jurnal dipisahkan per company; hasil budget/realisasi satu cabang tidak mencampur data cabang lain.
- Record rule company dipasang untuk RKA tahunan dan bulanan.
- Finance pusat dapat membaca semua company yang diizinkan, tetapi pemeriksaan server-side menolak perubahan di RKA dan detail bulanan.
- View RKA menampilkan company dan filter company. Dashboard terintegrasi tidak lagi memakai tab: mode RKA Tahunan dan Top 3 tampil langsung dalam area masing-masing, tanpa daftar Data Bulanan.
- Dashboard tidak lagi memuat relasi `monthly_ids` atau mengambil data bulanan untuk ditampilkan. Daftar tahunan dan Top 3 tidak bisa dibuka lewat klik baris; akses detail per bulan hanya melalui tombol **Detail Bulanan**.
- Judul section **RKA Tahunan** dan **Top 3 Pengeluaran** memperjelas mode yang aktif. Menu navbar **Diagram Anggaran** dihapus; tombol diagram yang berada di dashboard tetap tersedia.
- Migrasi menghapus constraint global lama sebelum constraint baru dibuat; budget lama yang company-nya kosong ditempatkan pada `base.main_company`, dan company baris bulanan diselaraskan ke parent RKA.


### 3.7 Aset — `sifnext_asset`

- Aset memiliki `company_id` dan `owner_department_id`; `owner_unit` teks tetap disimpan sebagai nilai historis.
- Create/write/constraint menolak department pemilik yang bukan milik company aset; department default dapat berasal dari department pengguna.
- Kategori, aset, penyusutan, posting akuisisi, pembuatan jadwal, dan posting penyusutan dilindungi dari perubahan Finance pusat.
- Aset dan jadwal penyusutan memiliki record rule company. Penyusutan mewarisi company/department dari aset.
- Jurnal perolehan dan penyusutan menerima company, department, teks department legacy, serta klasifikasi jurnal.
- Migrasi mencoba pencocokan `owner_unit` ke nama department pada company yang sama secara case-insensitive; bila tidak ada satu kecocokan tunggal, aset masuk ke department fallback company. Company/department juga ditulis pada jadwal dan jurnal terkait.
- View aset/penyusutan menampilkan company dan department pemilik; teks `owner_unit` lama tetap tersedia untuk audit.


### 3.8 Dokumen Perencanaan

`doc/PLAN_MULTI_COMPANY_BRANCH_DEPARTMENT_PENDAPATAN.md` dibuat bersama perubahan awal, lalu diubah agar mencatat keputusan final, scope PPL/payroll/Transaksi/RKA/Aset, modul yang dikecualikan, hasil test, dan status upgrade database.

## 4. Detail Migrasi dan Dampak pada `db_sifnext`

### 4.1 Urutan migrasi

1. **`sifnext_org`** memberi kode ke department lama, menyalin isi tabel `sifnext_unit` dan relasi `unit_id` ke tabel backup, lalu membuat mapping unit → `hr.department` berdasarkan company/kode/nama. User lama hanya dipetakan jika company department termasuk dalam company yang diizinkan user.
2. **`sifnext_ppl`** memindahkan XML ID UAT ke department hasil mapping, membersihkan menu/view/rule/access unit lama sebelum model hilang, memetakan PPL/payroll, lalu menghapus kolom `unit_id` dari `res_users` dan `sifnext_ppl`.
3. **`transaksi`** memetakan header transfer dari backup unit atau PPL terkait; jika tidak dapat dipetakan memakai fallback company. Sesudah kolom `unit_id` dihapus, migrasi memastikan seluruh unit lama tercadangkan sebelum menjalankan `DROP TABLE sifnext_unit` tanpa `CASCADE`.
4. **`sifnext_asset`** memetakan nama pemilik lama atau membuat/menggunakan department fallback; company/department disalin ke jadwal penyusutan dan jurnal.
5. **`sif_rka`** menghapus constraint unik global lama sebelum pembentukan constraint baru dan mengisi company legacy yang kosong dengan main company.
6. **`pendapatan`** memetakan `unit_name` yang cocok ke department pada company yang sama; yang tidak cocok memakai “Belum Diklasifikasikan” pada company record. Jurnal terkait menerima company/department.
7. **Salinan kategori Pendapatan** berjalan terpisah: kode saat ini mencari child company dari `base.main_company`, lalu menyalin kategori dari main company ke child tersebut.
8. **Legacy COA** yang tidak lagi ada dalam seed baru dipertahankan dengan XML ID/kode lama tetapi dinonaktifkan; ini mencegah FK pada data RKA dan jurnal menghalangi update COA.

### 4.2 Hasil nyata di database lokal

| Pemeriksaan | Hasil setelah upgrade |
|---|---:|
| Unit lama pada tabel backup | 1 |
| Relasi user/PPL/transfer pada backup relasi | 35 |
| User yang mendapat department dari mapping | 4 |
| Master department saat ini | 4 di PT Konsulta Semen Gresik; 2 di PT Semen Indonesia Foundation; 0 di UISI, Politeknik Semen Indonesia, dan TK Semen |
| PPL yang dimigrasikan dari unit | 22 |
| Transfer bank | 11 total: 9 terpetakan, 2 memakai fallback company |
| Header transfer campuran department tanpa satu department header | 0 |
| Aset | 5; tidak ada nama owner yang cocok tunggal, sehingga memakai department fallback company |
| RKA lama tanpa company | 0 |
| Tabel aktif `sifnext_unit` setelah migrasi | Tidak ada |
| Kolom `unit_id` aktif pada `res_users`, PPL, dan transfer | Tidak ada |
| PPL tanpa department | 0 |
| Transfer tanpa department | 0 |
| Aset tanpa department pemilik | 0 |
| Pendapatan | 10 total: 9 memakai “Belum Diklasifikasikan”, 1 terpetakan ke Administration |
| Kategori Pendapatan | 5 di PT Konsulta Semen Gresik; 0 pada company/cabang lain |
| Jurnal lama tanpa company | 17; tetap dipertahankan sebagai data legacy bersama |

Struktur company lokal menjelaskan satu hasil yang perlu diperhatikan: `base.main_company` adalah **PT Konsulta Semen Gresik**, sedangkan **UISI**, **Politeknik Semen Indonesia**, dan **TK Semen** adalah anak dari **PT Semen Indonesia Foundation**, sebuah root company berbeda. Migrasi kategori mencari child dari `base.main_company`, sehingga log mencatat **0 kategori disalin ke 0 branch**. Database saat ini memang mempunyai 0 kategori pada company PT Semen Indonesia Foundation dan ketiga cabangnya.

Dengan demikian, kategori branch-specific dapat dibuat oleh pengguna melalui master kategori, tetapi kategori induk yang sekarang berada di PT Konsulta belum tersalin otomatis ke tree PT Semen Indonesia Foundation. Jika kategori PT Konsulta memang harus dipakai/copy ke cabang-cabang tersebut, sumber company untuk migrasi perlu dikonfirmasi dan disesuaikan; tidak dilakukan penyalinan lintas root secara otomatis.

### 4.3 Modul dan versi setelah upgrade

| Modul | Versi database |
|---|---|
| `pendapatan` | `19.0.2.0.0` |
| `sif_rka` | `19.0.2.5.0` |
| `sifnext_asset` | `19.0.3.0.0` |
| `sifnext_org` | `19.0.3.0.0` |
| `sifnext_ppl` | `19.0.3.0.0` |
| `transaksi` | `19.0.2.0.0` |

Versi tersebut mencatat upgrade scope organisasi sebelum merge update aging/vendor. Database utama `db_sifnext` belum di-upgrade untuk model Vendor, Aging Report, dan field payment-term yang datang dari commit rekan.

## 5. Halaman/Bagian UI yang Berubah

| Menu/form | Perubahan yang terlihat |
|---|---|
| `/odoo/companies` → buka company → tab **Departemen** | Admin melihat/mengelola department, kode SIF, klasifikasi jurnal legacy, dan parent department dalam company itu. |
| Users → buka user | Field department default terlihat dan dibatasi oleh company yang diizinkan untuk user. |
| **Pendapatan** → **Daftar Pendapatan** | Kolom company/department, filter dan group-by department, form memilih department sesuai company. |
| **Pendapatan** → **Laporan** → **Laporan Pendapatan** | Wizard filter company, kategori, department, tanggal, status, serta pengelompokan laporan. |
| **Pendapatan** → **Master Data** → **Kategori Pendapatan** | Kategori memiliki company dan kode unik per company. |
| **PPL** → **PPL** | List/form memperlihatkan department; payload tetap membawa key `unit` untuk kompatibilitas integrasi. |
| Payroll batch → form batch | Tombol **Buat PPL per Departemen** dan smart button untuk membuka satu atau beberapa PPL hasil batch. |
| **Transaksi** → **Mutasi Bank** → **Mutasi Antar Rekening** | Department dan company mengikuti PPL/transfer dan divalidasi pada server. |
| **RKA** → **RKA Tahunan** / dashboard | Company menjadi kolom/filter; dashboard menunjukkan judul mode RKA Tahunan atau Top 3, tanpa tab/data bulanan. Bulan hanya dibuka lewat tombol **Detail Bulanan**. |
| **Aset** → **Data Aset** / **Kategori Aset** | Company dan Department Pemilik tersedia; jadwal penyusutan juga menampilkan company/department. |
| **Keuangan** → Jurnal, Buku Besar, Neraca, Laba Rugi, COA | Company scope diterapkan; Buku Besar menerima filter department, sedangkan filter teks legacy tetap dipertahankan untuk data lama. |

Menu/view tersebut tercatat di database dan berhasil dimuat saat upgrade modul. Pemeriksaan visual browser belum dilakukan: environment ini tidak menyediakan `playwright-cli` maupun Node/npm, dan route lokal `/web/login?db=db_sifnext` mengalihkan kembali ke URL yang sama. Hal ini membatasi pemeriksaan interaksi visual, bukan validasi XML/view saat upgrade.

## 6. Verifikasi yang Sudah Dilakukan

- Upgrade clone `sifnext_full_scope_migration_test_fix` dari `db_sifnext` dengan modul `sifnext_org,sif_rka,sifnext_asset,sifnext_ppl,transaksi,pendapatan`.
- Jalankan post-tests dengan tag modul: `/sifnext_org,/pendapatan,/sifnext_ppl,/sif_rka,/sifnext_asset,/transaksi`.
- Hasil clone: **41 post-tests, 0 failed, 0 error**.
- Setelah merge, clone sementara `sifnext_merge_validation` diuji dengan upgrade `sif_keuangan,sifnext_ppl`; **27 post-tests PPL, 0 failed, 0 error**. Clone dan filestore sementara kemudian dihapus.
- Update COA pada clone awalnya tertahan karena 21 XML ID lama terhapus sementara masih direferensikan. Setelah akun legacy ditambahkan kembali sebagai nonaktif, upgrade dan test PPL berhasil.
- Buat dump database lokal sebelum upgrade: `/tmp/opencode/db_sifnext_pre_multi_scope_20260928.dump`.
- Upgrade `db_sifnext`; seluruh enam modul di tabel Bagian 4.3 berstatus installed pada versi target.
- Cek database sesudah migrasi: tabel/kolom unit lama tidak aktif, tabel backup ada, dan PPL/transfer/aset tidak punya department kosong.
- `python3 -m compileall` pada addon yang berubah dan `git diff --check` berhasil.

Test baru mencakup kode dan department user; visibilitas Pendapatan per cabang, kategori/jurnal dan Finance pusat; PPL serta batch payroll per department; constraint dan realisasi RKA per company; posting aset dan akses Finance pusat; dan validasi/visibilitas transfer bank per company.

## 7. Daftar File Perubahan

Daftar berikut merangkum file yang berubah antara commit dasar dan kondisi ini. **Baru** berarti ditambahkan sejak `b421537`; **Dihapus** berarti file baseline dihapus.

### Pendapatan

- `custom_addons/pendapatan/__manifest__.py`
- `custom_addons/pendapatan/migrations/19.0.1.1.0/post-migration.py`
- **Baru:** `custom_addons/pendapatan/migrations/19.0.2.0.0/post-copy_categories_to_branches.py`
- `custom_addons/pendapatan/models/pendapatan.py`
- `custom_addons/pendapatan/models/pendapatan_category.py`
- `custom_addons/pendapatan/security/ir.model.access.csv`
- `custom_addons/pendapatan/security/security_groups.xml`
- `custom_addons/pendapatan/tests/__init__.py`, `tests/test_branch_department_scope.py`
- `custom_addons/pendapatan/views/pendapatan_category_views.xml`, `views/pendapatan_views.xml`
- `custom_addons/pendapatan/wizard/laporan_pendapatan_wizard.py`, `wizard/laporan_pendapatan_wizard_views.xml`

### Keuangan

- `custom_addons/sif_keuangan/__manifest__.py`
- `custom_addons/sif_keuangan/data/sequence_data.xml`, `data/sif_coa_data.xml`, `data/sif_coa_legacy_data.xml`
- **Baru:** `custom_addons/sif_keuangan/data/sif_coa_legacy_data.xml`
- `custom_addons/sif_keuangan/controllers/balance_sheet_controller.py`, `general_ledger_controller.py`, `profit_loss_controller.py`
- `custom_addons/sif_keuangan/models/__init__.py`, `aging_report.py`, `balance_sheet.py`, `coa.py`, `general_ledger.py`, `jurnal.py`, `profit_loss.py`, `vendor.py`
- `custom_addons/sif_keuangan/reports/profit_loss_report.xml`
- `custom_addons/sif_keuangan/security/ir.model.access.csv`, `security/security_groups.xml`
- `custom_addons/sif_keuangan/views/aging_report_views.xml`, `views/coa_views.xml`, `views/menu_views.xml`, `views/vendor_views.xml`
- `custom_addons/sif_keuangan/static/src/balance_sheet/balance_sheet_view.xml`
- `custom_addons/sif_keuangan/static/src/general_ledger/general_ledger_view.xml`
- `custom_addons/sif_keuangan/static/src/profit_loss/profit_loss_view.xml`, `static/src/i18n.js`
- `custom_addons/sif_keuangan/views/jurnal_views.xml`

### Organisasi

- **Baru:** `custom_addons/sifnext_org/__init__.py`, `__manifest__.py`
- **Baru:** `custom_addons/sifnext_org/models/__init__.py`, `models/organization.py`
- **Baru:** `custom_addons/sifnext_org/data/sequence.xml`
- **Baru:** `custom_addons/sifnext_org/migrations/19.0.2.0.0/post-migration.py`
- **Baru:** `custom_addons/sifnext_org/migrations/19.0.3.0.0/pre-copy_legacy_units.py`, `post-migrate_departments.py`
- **Baru:** `custom_addons/sifnext_org/tests/__init__.py`, `tests/test_organization.py`
- **Baru:** `custom_addons/sifnext_org/views/res_company_views.xml`, `views/res_users_views.xml`

### PPL dan Payroll

- `custom_addons/sifnext_ppl/__manifest__.py`, `data/ir_sequence_data.xml`, `data/ppl_uat_users.xml`
- `custom_addons/sifnext_ppl/models/__init__.py`, `models/payroll_integration.py`, `models/ppl.py`
- **Dihapus:** `custom_addons/sifnext_ppl/models/unit.py`, `views/unit_views.xml`
- `custom_addons/sifnext_ppl/security/ir.model.access.csv`, `security/ppl_security.xml`
- `custom_addons/sifnext_ppl/tests/test_ppl_workflow.py`
- `custom_addons/sifnext_ppl/views/payroll_integration_views.xml`, `views/ppl_views.xml`
- **Baru:** `custom_addons/sifnext_ppl/migrations/19.0.3.0.0/pre-remap_uat_department.py`
- **Baru:** `custom_addons/sifnext_ppl/migrations/19.0.3.0.0/pre-remove_unit_ui.py`, `post-migrate_department_refs.py`

### Transaksi Bank

- `custom_addons/transaksi/__manifest__.py`
- `custom_addons/transaksi/models/ppl.py`, `models/transaction.py`, `models/transaction_line.py`
- `custom_addons/transaksi/security/ir.model.access.csv`, `security/security_groups.xml`
- `custom_addons/transaksi/views/transaction_views.xml`
- **Baru:** `custom_addons/transaksi/migrations/19.0.2.0.0/post-migration_department.py`
- **Baru:** `custom_addons/transaksi/tests/__init__.py`, `tests/test_department_scope.py`

### RKA

- `custom_addons/sif_rka/__manifest__.py`
- `custom_addons/sif_rka/controllers/dashboard_controller.py`
- `custom_addons/sif_rka/models/dashboard_models.py`, `models/rka_budget.py`
- `custom_addons/sif_rka/views/rka_budget_views.xml`
- **Baru:** `custom_addons/sif_rka/migrations/19.0.2.0.0/pre-drop-global-budget-constraint.py`, `post-assign-legacy-company.py`
- **Baru:** `custom_addons/sif_rka/migrations/19.0.2.1.0/post-remove_diagram_nav_menu.py`
- **Baru:** `custom_addons/sif_rka/security/rka_security.xml`
- **Baru:** `custom_addons/sif_rka/tests/__init__.py`, `tests/test_company_scope.py`

### Aset

- `custom_addons/sifnext_asset/__manifest__.py`
- `custom_addons/sifnext_asset/models/asset.py`, `models/asset_category.py`, `models/asset_depreciation.py`
- `custom_addons/sifnext_asset/views/asset_views.xml`, `views/asset_depreciation_views.xml`
- **Baru:** `custom_addons/sifnext_asset/migrations/19.0.3.0.0/post-migrate_departments.py`
- **Baru:** `custom_addons/sifnext_asset/security/sifnext_asset_security.xml`
- **Baru:** `custom_addons/sifnext_asset/tests/__init__.py`, `tests/test_asset_department_scope.py`

### Dokumen dan file lokal

- `doc/PLAN_MULTI_COMPANY_BRANCH_DEPARTMENT_PENDAPATAN.md` berubah dan mencatat rencana/keputusan/status terbaru.
- **Dokumen ini** menjelaskan perbandingan dari `b421537`.
- `custom_addons/.gitignore`, `docker-compose.local.yml`, dan `graphify-out/cache/stat-index.json` adalah file lokal/untracked, bukan perubahan fitur aplikasi pada diff commit. File cache Graphify adalah artefak hasil analisis.

## 8. Batas Interpretasi dan Tindak Lanjut yang Perlu Diketahui

1. Hasil penggabungan berasal dari commit fitur `5b017c4` dan update rekan `55a038c`; hasil merge tersimpan pada branch `sif-main-19` dan belum di-push.
2. Backup database hanya mencakup database PostgreSQL (`db_sifnext`); dump tersebut berada di `/tmp/opencode` dan tidak menjadi file repository.
3. Pada data lokal sekarang, tidak ada kategori Pendapatan pada company PT Semen Indonesia Foundation/UISI/Politeknik/TK Semen. Log migrasi kategori menyalin 0 record karena pencarian child memakai `base.main_company` PT Konsulta. Sumber kategori yang seharusnya dipakai untuk branch perlu dikonfirmasi bila kategori-kategori tersebut memang harus disalin.
4. Ada 17 jurnal legacy tanpa company. Kode mempertahankan record tersebut sebagai data bersama; tidak ada tebakan untuk memindahkannya ke branch tertentu.
5. Presenly, Absensi, dan Cuti bukan bagian dari perubahan ini.
