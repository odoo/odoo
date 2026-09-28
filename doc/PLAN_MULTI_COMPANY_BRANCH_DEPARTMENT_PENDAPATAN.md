# Rencana Multi-Company, Cabang, Departemen, dan Pendapatan

**Status:** Rencana untuk ditinjau — belum ada perubahan kode
**Tanggal:** 28 September 2026
**Ruang lingkup:** Master cabang dan departemen, pembatasan data Pendapatan, serta penyesuaian integrasi ke modul keuangan dan operasional.

## 1. Ringkasan

Gunakan hierarki multi-company bawaan Odoo untuk merepresentasikan cabang, lalu gunakan master `hr.department` sebagai departemen milik cabang tersebut. Hindari membuat model cabang atau master departemen kedua yang menduplikasi kemampuan Odoo.

Rencana struktur:

```text
Perusahaan induk: PT Semen Indonesia Foundation (res.company)
├── Cabang: Universitas Internasional Semen Indonesia (res.company)
│   ├── Manajemen (hr.department)
│   ├── Teknik Informatika (hr.department)
│   └── Sistem Informasi (hr.department)
├── Cabang: Politeknik Semen Indonesia (res.company)
│   ├── Agroteknologi (hr.department)
│   ├── Teknologi Komputer (hr.department)
│   └── Sistem Informasi (hr.department)
└── Cabang lain (res.company)
```

Setiap transaksi Pendapatan akan memiliki perusahaan/cabang dan departemen yang eksplisit. Pemisahan data wajib ditegakkan di server melalui record rule dan validasi model, bukan hanya domain pada dropdown atau menu. Nama “unit” pada fitur baru diganti menjadi “departemen”; data lama `sifnext.unit` dan `unit_name` tetap dipetakan selama migrasi agar histori serta integrasi tidak terputus.

### Keputusan pengguna (28 September 2026)

- Pendapatan User dapat melihat semua departemen di cabang yang diizinkan; departemen tetap wajib dicatat sebagai klasifikasi transaksi, tetapi bukan batas visibilitas user.
- Kategori Pendapatan dikelola per cabang, bukan global.
- RKA dipisahkan per cabang/company, tetapi tidak sampai tingkat departemen.
- Record lama yang tidak dapat dipetakan boleh memakai departemen khusus “Belum Diklasifikasikan” pada company/cabang yang saat ini tercatat. Jika company yang tercatat adalah perusahaan induk, jangan memindahkannya ke cabang tanpa mapping yang disetujui. Nilainya tetap dilaporkan agar dapat ditinjau.
- Finance pusat dapat membaca seluruh cabang, tanpa hak membuat, mengubah, menyetujui, atau mem-posting transaksi Pendapatan.

Rekomendasi yang masih menunggu persetujuan: kode wajib per departemen dan PPL payroll terpisah per departemen. Alasannya serta dampaknya dijelaskan pada Bagian 8.

## 2. Temuan kondisi saat ini

### 2.1 Perusahaan dan cabang

- Odoo sudah menyediakan relasi hierarki cabang pada `res.company`: `parent_id`, `child_ids`, dan `all_child_ids` (`odoo/addons/base/models/res_company.py`).
- Form perusahaan bawaan memiliki tab **Branches** yang menampilkan `child_ids` (`odoo/addons/base/views/res_company_views.xml`). Dengan demikian, cabang dapat tetap dikelola melalui `/odoo/companies` tanpa model cabang kustom.
- Hak akses multi-company Odoo menggunakan perusahaan yang diizinkan untuk pengguna. Pengguna yang diberi akses ke beberapa cabang secara wajar dapat berpindah ke dan melihat cabang-cabang tersebut.

### 2.2 Departemen dan master “unit” lama

- Odoo menyediakan `hr.department` dengan `company_id`, `parent_id`, dan `child_ids` (`addons/hr/models/hr_department.py`). Perusahaan departemen dihitung dari induk departemen bila struktur departemen dibuat bertingkat.
- Saat ini `sifnext_ppl/models/unit.py` mendefinisikan `sifnext.unit` dengan `name`, `code`, `company_id`, `active`, dan `journal_unit_dept`, serta menambahkan `res.users.unit_id`.
- `journal_unit_dept` bukan kode departemen bebas; nilainya adalah klasifikasi keuangan tetap seperti TPA, SD, SMP, SMA, Universitas, dan Kantor Pusat. Nilai ini tidak boleh dipaksakan menjadi nama departemen baru.
- Beberapa fitur sudah memakai `hr.department`, khususnya payroll dan tampilan peminjam operasional. Presenly memakai `hr.work.location` untuk lokasi kerja fisik/geofence; lokasi fisik tersebut berbeda konsep dengan cabang organisasi dan departemen.

### 2.3 Modul Pendapatan

- Model `pendapatan.pendapatan` (`custom_addons/pendapatan/models/pendapatan.py`) sudah mempunyai `company_id` wajib dengan default perusahaan aktif, tetapi belum mempunyai relasi departemen.
- Lokasi kerja masih berupa `unit_name` teks bebas dengan default `KANTOR`. Nilai teks bebas tidak cukup untuk domain, validasi, laporan, dan keamanan per cabang/departemen.
- Kategori sudah mempunyai `company_id` dan constraint kode kategori unik per perusahaan (`pendapatan_category.py`), sehingga dapat dibuat per cabang.
- Daftar Pendapatan saat ini menampilkan Nomor, Tanggal, Kategori, Label Periode, Unit Kerja, Nominal, dan Status. Kolom Perusahaan belum terlihat dan Departemen belum tersedia (`views/pendapatan_views.xml`).
- ACL ada di `security/ir.model.access.csv`; belum ditemukan record rule Pendapatan di `pendapatan/security`. ACL menentukan operasi model, bukan cabang mana yang boleh dilihat.
- `create_pendapatan_from_external()` menggunakan `sudo()` untuk membuat dan mem-posting transaksi. Jalur RPC/integrasi ini harus tetap memvalidasi company dan department agar tidak menjadi jalan pintas melewati pembatasan akses.
- Posting Pendapatan membuat `sif.jurnal.entry` dengan `unit_name`, tetapi belum meneruskan relasi perusahaan/departemen.

### 2.4 Modul yang terhubung

Tabel di bawah memetakan dampak jangka panjang, bukan berarti semua modul diubah pada tahap pertama. Batas aktual tahap pertama dan alasan penundaan dijelaskan di Bagian 9.

| Modul | Kondisi sekarang | Dampak yang perlu direncanakan |
|---|---|---|
| `sifnext_ppl` | PPL memakai `unit_id` ke `sifnext.unit`; user memiliki `unit_id`; validasi memastikan unit dan company sama. Payload integrasi mengekspor `unit`. | Ganti referensi bisnis ke departemen, migrasikan unit lama, pertahankan kontrak payload `unit` sementara, dan tambahkan department ke kontrak baru. Pertahankan aturan PPL “milik sendiri” serta Finance/Director, dengan batas company tetap berlaku. |
| `transaksi` | `transaksi.transaction.unit_id` menunjuk `sifnext.unit` dan default dari user. Pembuatan PPL meneruskan `unit_id`. | Ganti form, domain, validasi, dan payload agar memakai department serta company cabang yang sama. |
| `sif_keuangan` | `sif.jurnal.entry.unit_name` adalah teks; buku besar, laba-rugi, neraca, wizard, dan export memakai filter teks `unit_name`. Header jurnal belum memiliki dimensi departemen terstruktur. | Tambahkan dimensi company dan department pada jurnal, lalu migrasikan filter dan laporan ke relasi. Simpan nilai teks lama sebagai kompatibilitas/histori sampai rekonsiliasi selesai. |
| `sif_rka` | `sif.rka.budget` saat ini tidak mempunyai dimensi company atau department; constraint uniknya `(account_id, tahun)`. PPL mencari RKA hanya berdasarkan COA dan tahun. | Keputusan pengguna: RKA dibedakan per cabang, bukan departemen. Tambahkan `company_id` dan ubah pencarian/constraint agar RKA dan realisasi tidak tercampur antar-cabang; department tidak menjadi dimensi RKA. |
| `sifnext_asset` | Aset menyimpan `owner_unit` sebagai teks dan mengirim `unit_name` ke jurnal. | Ganti master owner menjadi department; pastikan company/departemen aset dan jurnal konsisten. |
| `hr_payroll_custom` | Slip sudah memiliki `department_id` terkait ke departemen pegawai dan payroll batch memiliki company. | Pertahankan relasi standar; validasi company dan departemen pegawai. Integrasi payroll ke PPL saat ini memilih unit pertama di company; rekomendasinya satu batch menghasilkan satu PPL per departemen yang ada di batch tersebut. |
| `sifnext_operational` | Peminjaman membaca `hr.employee.department_id` untuk menampilkan departemen peminjam. | Pertahankan sebagai sumber data departemen pegawai; tinjau filter company pada record operasional. |

## 3. Model data yang diusulkan

### 3.1 Cabang

1. Perusahaan induk tetap berupa `res.company` root.
2. Setiap cabang dibuat sebagai `res.company` dengan `parent_id` menunjuk perusahaan induk.
3. Gunakan tab **Branches** bawaan pada form perusahaan. Tambahkan akses yang jelas dari form cabang ke daftar departemen, misalnya tab atau smart button “Departemen” yang membuka `hr.department` dengan filter cabang tersebut.
4. Jangan gunakan `hr.work.location` sebagai pengganti company branch. Satu cabang dapat mempunyai lebih dari satu lokasi fisik.

### 3.2 Departemen

1. Gunakan `hr.department` sebagai satu-satunya master departemen.
2. Setiap departemen operasional wajib mempunyai `company_id` yang menunjuk cabang pemiliknya. Departemen induk/anak, bila dipakai, harus tetap berada di cabang yang sama.
3. Rekomendasi: tambahkan field kode SIF wajib (misalnya `sif_code`) pada setiap department operasional untuk mempertahankan prefix nomor PPL, integrasi, dan pelaporan. Kode harus unik di dalam cabang, dinormalisasi konsisten, dan tidak dicampur dengan `journal_unit_dept`; rekomendasi ini menunggu persetujuan pengguna.
4. Pertahankan `journal_unit_dept` sementara sebagai atribut pemetaan akuntansi lama, atau buat tabel pemetaan yang eksplisit. Tentukan pemilik dan aturan nilainya sebelum menghapus `sifnext.unit`.

### 3.3 Pengguna

1. Berikan satu departemen penugasan melalui `res.users.department_id` sebagai sumber default dan otoritatif untuk Pendapatan tahap pertama. Sinkronisasi dengan `hr.employee.department_id` ditunda bersama payroll agar modul yang dikecualikan tidak ikut berubah.
2. Department pengguna harus berasal dari salah satu company/cabang yang diizinkan pengguna. Domain UI hanya bantuan; validasi server juga wajib.
3. Konfigurasikan `company_ids` pengguna sesuai cabang yang benar-benar boleh diakses. Contoh: pengguna UISI hanya diberi cabang UISI; Finance pusat dapat diberi beberapa cabang sesuai mandatnya.
4. Department penugasan menjadi default dan identitas organisasi, bukan filter visibilitas Pendapatan. Sesuai keputusan pengguna, semua department dalam cabang yang diizinkan terlihat oleh Pendapatan User.

### 3.4 Pendapatan

Model `pendapatan.pendapatan` ditargetkan mempunyai:

| Label layar | Field teknis (rencana) | Ketentuan |
|---|---|---|
| Nomor | `name` | Sequence tidak ambigu antar cabang; pertimbangkan sequence company-specific dan prefix kode departemen jika memang dibutuhkan. |
| Tanggal | `tanggal` | Tetap seperti sekarang. |
| Kategori | `category_id` | Kategori harus shared secara eksplisit atau milik cabang yang sama. |
| Label Periode | `period_label` | Tetap seperti sekarang. |
| Perusahaan | `company_id` | Company yang dipilih adalah cabang tempat pendapatan terjadi; default dari cabang aktif. Ditampilkan di list. |
| Departemen | `department_id` | Relasi wajib ke `hr.department`; default dari penugasan pengguna; harus berasal dari company yang sama. |
| Nominal | `amount` | Tetap seperti sekarang. |
| Status | `state` | Workflow Draft → Diajukan → Disetujui → Diposting tetap dipertahankan. |

Tambahan teknis: pertahankan `currency_id` sebagai field pendukung; aktifkan pemeriksaan company pada relasi yang relevan; lakukan constraint untuk memastikan `department_id.company_id == company_id` dan category tidak lintas company. Ganti `unit_name` untuk transaksi baru dengan relasi departemen. Nilai teks lama tidak dihapus sebelum data historis berhasil dipetakan.

## 4. Kebijakan akses yang direncanakan

### 4.1 Batas cabang

- Terapkan record rule company pada Pendapatan dan kategori dengan company yang termasuk daftar company yang diizinkan pengguna; ikuti pola multi-company yang telah dipakai `sifnext_ppl/security/ppl_security.xml`.
- Company pada record harus berupa cabang transaksi, bukan selalu perusahaan induk. Dengan demikian, Pendapatan UISI dan Politeknik tersimpan di company branch yang berbeda.
- Pendapatan User dapat membaca seluruh departemen dalam cabang yang diizinkan. Department tidak digunakan sebagai record rule untuk membatasi user biasa.
- Finance/Manager cabang dapat melakukan tindakan sesuai role atas semua department di cabang yang diizinkan, tetapi tidak boleh mengabaikan batas company.
- Finance pusat diberi akses baca untuk semua cabang, dengan akses tulis/create/unlink serta tombol approval/posting dinonaktifkan. Berikan seluruh company branches yang relevan pada `company_ids`-nya dan pastikan hak read-only ini tidak menambah izin tulis melalui group lain.
- Domain pada company/departemen/kategori di form bukan kontrol keamanan. Uji akses juga melalui RPC, import/export, search, action, dan metode workflow.

### 4.2 Batas departemen

Keputusan akses:

- **Pendapatan User:** dapat membaca dan mengelola transaksi seluruh departemen pada cabang yang diizinkan; department dari user tetap menjadi default transaksi baru.
- **Pendapatan Manager/Finance cabang:** dapat melihat seluruh department di cabang yang diizinkan dan menjalankan approval/posting sesuai role.
- **Finance pusat:** dapat membaca Pendapatan dari seluruh cabang, tetapi tidak dapat membuat, mengubah, menghapus, menyetujui, atau mem-posting.

Pemisahan kerahasiaan dilakukan pada company/cabang. Record rule department tidak ditambahkan untuk Pendapatan User kecuali kebijakan ini berubah di kemudian hari.

### 4.3 Jalur integrasi

- Audit `create_pendapatan_from_external()` dan semua pemanggilnya. Hindari `sudo()` tanpa pemeriksaan eksplisit bahwa caller berhak membuat pada company/departemen tersebut.
- Posting ke jurnal harus membawa `company_id` dan `department_id`; pastikan `sudo()` yang dibutuhkan untuk integrasi jurnal tidak mengubah dimensi organisasi atau melewati validasi.
- API PPL/Transaksi sementara dapat menerima `unit_id` sebagai alias kompatibilitas, tetapi kontrak baru harus mengirim identitas departemen secara eksplisit dan memiliki rencana penghapusan alias.

## 5. Urutan implementasi yang disarankan

### Fase 0 — Keputusan dan inventarisasi

1. Konfirmasi rekomendasi kode departemen dan skenario PPL payroll pada Bagian 8; keputusan akses, kategori, RKA, histori, dan Finance pusat sudah dicatat.
2. Inventarisasi company parent-child yang akan menjadi cabang, company yang saat ini dipakai record, seluruh `sifnext.unit`, pengguna, PPL, Pendapatan, jurnal, RKA, aset, dan payroll batch.
3. Siapkan backup database dan tabel pemetaan lama → baru. Jangan menebak mapping hanya dari kemiripan nama.

### Fase 1 — Fondasi master organisasi

1. Buat modul fondasi bersama (nama sementara `sifnext_org`) yang bergantung pada `hr`.
2. Jika rekomendasi kode disetujui, tambahkan kode SIF ke `hr.department`; lanjutkan dengan validasi keunikan per company, penugasan departemen pengguna, aturan company, dan tampilan departemen pada form company branch.
3. Uji pembuatan departemen dari halaman cabang, termasuk departemen anak dan validasi agar tidak lintas cabang.

### Fase 2 — Migrasi master dan pengguna

1. Buat/pastikan record `res.company` cabang mempunyai induk yang benar.
2. Buat master `hr.department` baru untuk masing-masing cabang.
3. Konfigurasikan penugasan departemen pengguna khusus untuk Pendapatan. Jangan menyalin atau mengubah `res.users.unit_id` pada tahap ini; field tersebut masih dipakai PPL.
4. Migrasi `sifnext.unit` dan pemetaan `res.users.unit_id` ke master departemen ditunda sampai PPL serta modul yang terhubung disetujui untuk diubah.

### Fase 3 — Pendapatan dan keamanan

1. Tambahkan `department_id`, tampilkan `company_id`, ganti `unit_name` pada form/list/search/group-by dengan Departemen.
2. Default company dari cabang aktif dan department dari penugasan pengguna; batasi pilihan kategori dan departemen ke company tersebut.
3. Tambahkan record rules company dan department, validasi create/write, serta validasi pada seluruh tombol workflow dan RPC.
4. Ubah sequence agar aman untuk beberapa cabang dan hindari nomor ganda sesuai kebijakan nomor yang disetujui.
5. Backfill record Pendapatan lama memakai tabel pemetaan eksplisit dari `unit_name`/company. Tinjau dan setujui record yang tidak dapat dipetakan sebelum menjadikannya wajib.

### Fase 4 — Jurnal dan laporan keuangan

1. Tambahkan company/departemen terstruktur pada `sif.jurnal.entry` untuk jurnal yang berasal dari Pendapatan; pastikan baris jurnal konsisten dengan header.
2. Ubah laporan, wizard, dan export `sif_keuangan` agar jurnal Pendapatan dapat difilter per branch/company dan department. Pertahankan `unit_name` dan perilaku laporan lama untuk jurnal yang belum mempunyai dimensi baru.
3. Pada tahap ini hanya posting Pendapatan yang mengirim kedua dimensi secara eksplisit. PPL, aset, dan sumber jurnal lain tetap memakai kontrak lama.
4. Backfill histori jurnal Pendapatan hanya berdasarkan mapping yang disetujui; jangan menebak company atau department jurnal dari modul yang ditunda.

### Tahap lanjutan — PPL, payroll, transaksi, aset, dan RKA (ditunda)

1. Setelah mendapat persetujuan terpisah, migrasikan PPL dan detailnya dari `unit_id` ke departemen; perbarui domain, constraint, nomor, view, access rules, payload integrasi, dan test.
2. Dalam perubahan yang sama dengan PPL, ubah `transaksi.transaction` dan pembentukan PPL agar department/company tetap sama. Jangan mengubah Transaksi sebelum kontrak PPL siap.
3. Setelah ruang lingkup aset disetujui, ubah `sifnext.asset.owner_unit` menjadi relasi departemen dan bawa company/department ke jurnal aset.
4. Payroll tetap memakai `hr.employee.department_id` yang ada. Penyesuaian payroll-to-PPL hanya dilakukan setelah keputusan batch multi-departemen dan perubahan PPL disetujui.
5. Walaupun anggaran tidak dibagi per department, RKA tetap perlu dimensi company/cabang sesuai keputusan pengguna. Tambahkan company ke RKA dan detail bulan, ubah constraint `(account_id, tahun)` menjadi `(account_id, company_id, tahun)`, dan ubah pencarian budget/realisasi setelah modul RKA disetujui untuk disentuh.
6. Pertahankan kompatibilitas API dengan versi payload baru yang menyertakan `department`; hapus field/alias `unit` hanya setelah konsumen internal dan eksternal tervalidasi.

### Fase 6 — Penghapusan legacy dan rilis

1. Jalankan migrasi pada salinan database, cocokkan jumlah record dan nominal sebelum/sesudah.
2. Jalankan test otomatis, upgrade modul secara berurutan, kemudian UAT lintas cabang.
3. Setelah semua record dan integrasi terverifikasi, hentikan penulisan `sifnext.unit`/`unit_name` dan baru kemudian hapus kompatibilitas legacy pada rilis terpisah.

## 6. Strategi migrasi data

1. Buat backup penuh database dan filestore sebelum upgrade.
2. Siapkan mapping untuk Pendapatan lama dengan minimal kolom: company/cabang lama, nilai `unit_name`, department baru, kode department, dan keputusan mapping. Jangan migrasikan `sifnext.unit` atau `res.users.unit_id` pada tahap ini.
3. Migrasikan master sebelum transaksi agar foreign key departemen tersedia.
4. Backfill record Pendapatan menggunakan company yang sudah tercatat dan mapping yang disetujui. Jangan mengubah histori workflow atau nominal.
5. Record historis yang tidak bisa dipetakan dimasukkan ke department “Belum Diklasifikasikan” pada company yang tercatat, sesuai persetujuan pengguna. Laporkan jumlah dan nilai nominalnya; tetap sediakan daftar untuk ditinjau dan dipindahkan ke department/cabang sebenarnya bila mapping ditemukan.
6. Bandingkan jumlah Pendapatan, total nominal per company/periode/status, dan jurnal yang dibuat dari Pendapatan sebelum/sesudah migrasi. RKA, PPL, payroll, aset, dan transaksi tidak dimigrasikan atau diubah pada tahap ini.
7. Simpan nilai `unit_name` lama untuk audit sampai validasi UAT dan rekonsiliasi selesai.

## 7. Kriteria penerimaan dan pengujian

### Master dan form

- Admin dapat membuat cabang di tab Branches bawaan pada perusahaan induk.
- Admin dapat membuka sebuah cabang dan membuat beberapa departemen di cabang itu.
- Departemen UISI tidak dapat dipilih pada transaksi cabang Politeknik, termasuk melalui RPC/import.
- Kode departemen unik dalam satu cabang; kode yang sama boleh dipakai di cabang lain bila kebijakan kode menyetujui.
- User dengan department/employee berbeda mendapat penolakan validasi atau koreksi yang eksplisit, bukan default diam-diam.

### Pendapatan

- List menampilkan kolom sesuai urutan: Nomor, Tanggal, Kategori, Label Periode, Perusahaan, Departemen, Nominal, Status.
- User UISI dapat membaca semua department UISI, tetapi tidak dapat membaca, mencari, mengekspor, mengubah, atau mem-posting Pendapatan Politeknik; uji dengan user biasa dan API/RPC.
- Dua user dengan department berbeda di cabang yang sama tetap dapat melihat Pendapatan seluruh department cabang tersebut.
- User multi-cabang hanya dapat melihat company yang memang ada pada `company_ids`-nya.
- Finance pusat dapat membaca seluruh cabang namun gagal pada create/write/unlink, approval, posting, serta jalur RPC yang mengubah data.
- Kategori, company, dan department transaksi selalu cocok; user tidak bisa memalsukan `company_id`/`department_id` lewat context atau RPC.
- Workflow draft/submitted/approved/posted/cancelled tetap berjalan; posting membuat jurnal dengan company dan department yang sama.

### Modul terintegrasi

- Jurnal Pendapatan dan laporan akuntansinya dapat difilter per company dan department tanpa mengubah total jurnal Pendapatan.
- Pemilihan department/company pada Pendapatan tidak mengubah kontrak PPL, payroll, aset, atau transaksi lama.
- Uji regresi memastikan alur PPL/payroll/aset yang tidak disentuh tetap dapat berjalan menggunakan field dan kontrak lama.
- Pemisahan RKA per cabang, migrasi PPL/payroll, serta dimensi department pada aset dan Transaksi adalah kriteria penerimaan tahap lanjutan, bukan tahap pertama.

### Migrasi

- Jumlah record dan nominal historis cocok sebelum/sesudah migrasi.
- Setiap record legacy memiliki mapping atau tercatat di daftar pengecualian yang disetujui.
- Tidak ada akses lintas cabang melalui menu, report, wizard, export, controller, atau metode `sudo()`.

## 8. Keputusan dan rekomendasi

### 8.1 Keputusan pengguna

1. Pendapatan User melihat semua department pada cabang yang diizinkan, bukan hanya department penugasannya.
2. Kategori Pendapatan dikelola per cabang.
3. RKA dipisahkan per company/cabang, tetapi tidak per department.

4. Record lama yang tidak dapat dipetakan boleh ditempatkan di department “Belum Diklasifikasikan” pada company/cabang yang tercatat. Nilainya tetap dilaporkan dan bisa ditinjau kemudian.

5. Finance pusat memiliki akses baca ke seluruh cabang, tanpa hak perubahan atau approval/posting.

### 8.2 Rekomendasi yang menunggu persetujuan

1. **Kode department — rekomendasi: wajib dan unik per cabang.** Master lama `sifnext.unit` sudah mempunyai `code`, dan nomor PPL saat ini diawali kode tersebut (`unit.code/sequence`). Kode department yang stabil mempermudah migrasi, integrasi, serta identifikasi saat nama department berubah atau sama di cabang lain. Efeknya, semua department baru harus diberi kode sebelum digunakan dan setiap kode lama harus dipetakan. Kode yang sama boleh digunakan di cabang berbeda; uniqueness dijaga di dalam company/cabang. Jika kode tidak diwajibkan, sequence PPL perlu beralih ke nomor tingkat cabang dan tidak lagi menunjukkan department.
2. **Payroll batch lintas department — rekomendasi: satu PPL per department.** Model PPL saat ini menaruh satu `unit_id` pada header, bukan per baris. Memecah batch menjadi beberapa PPL mempertahankan struktur satu PPL = satu department, membuat jurnal/laporan mudah ditelusuri per department, dan menghindari penetapan department yang keliru pada header. Efeknya satu payroll batch dapat menghasilkan beberapa PPL, approval, dan jurnal. PPL-PPL itu tetap dapat ditautkan ke batch asal; proses pembayaran bisa dikelompokkan hanya jika alur Transaksi mendukungnya.

   Alternatifnya adalah satu PPL gabungan per batch. Agar department tidak hilang, perlu menambah department di setiap baris PPL, mengubah integrasi payroll, membuat jurnal mempertahankan department per baris, dan mengadaptasi laporan. Efek positifnya lebih sedikit dokumen dan satu approval; implementasinya lebih luas dan tidak cocok dengan desain PPL header tunggal yang ada. Karena RKA tidak dibedakan per department, pemisahan ini untuk jejak audit/pelaporan, bukan pembatasan budget.
3. **Sumber department pengguna tahap pertama.** Implementasi memakai `res.users.department_id` sebagai sumber default Pendapatan. Tidak ada sinkronisasi ke `hr.employee.department_id` pada tahap ini; pemetaan keduanya ditinjau kembali saat payroll dibuka.

## 9. Batas scope tahap pertama dan modul yang ditunda

### 9.1 Modul yang akan diubah pada tahap pertama

1. **`sifnext_org` (modul baru)** — fondasi departemen bersama berbasis `hr.department`, penugasan departemen untuk kebutuhan Pendapatan, dan akses daftar departemen dari form cabang. Kode departemen ditambahkan bila rekomendasi pada Bagian 8 disetujui. Cabang tetap memakai `res.company` bawaan; tidak dibuat model cabang baru. Modul ini tidak memigrasikan atau mengganti `sifnext.unit`/`res.users.unit_id` yang masih dipakai PPL.
2. **`pendapatan`** — menambah relasi department, menampilkan Perusahaan dan Departemen, mengelola kategori per cabang, menerapkan record rule company agar user hanya melihat cabang yang diizinkan, dan menegakkan konsistensi company-department pada UI, create/write, workflow, serta RPC. User di cabang yang sama melihat semua department di cabang tersebut.
3. **`sif_keuangan` (perubahan terbatas)** — menyimpan `company_id` dan `department_id` pada jurnal yang dibuat dari Pendapatan, meneruskan dua dimensi itu saat posting, dan membatasi filter/laporan pada company yang diizinkan. `unit_name` serta alur jurnal PPL/aset lama dipertahankan; Finance pusat read-only juga dibatasi dari perubahan jurnal/COA melalui server-side checks.

Migrasi tahap pertama hanya mencakup transaksi Pendapatan dan jurnal asal Pendapatan. Master lama PPL, payroll, aset, dan transaksi lain tidak dimigrasikan. Pada database lokal `db_sifnext`, 10 record Pendapatan lama tidak cocok dengan nama department yang tersedia; semuanya diberi department “Belum Diklasifikasikan” pada company lama `PT Konsulta Semen Gresik`. Nilai unit lama tidak cukup untuk memindahkan record tersebut ke cabang UISI atau Politeknik secara aman, jadi tidak ada tebakan mapping.

### 9.2 Modul yang sengaja tidak disentuh sekarang

| Modul | Mengapa mungkin perlu penyesuaian di masa depan | Batas untuk tahap pertama |
|---|---|---|
| **Presenly** | Perlu perubahan hanya bila perusahaan ingin aturan presensi/API/approval mengikuti struktur cabang atau department baru. Saat ini Presenly memakai `hr.work.location` untuk lokasi kerja fisik/geofence; lokasi ini tidak boleh otomatis diubah menjadi department atau company branch. | Tidak diubah. Tidak menjadi dependensi Pendapatan. |
| **Cuti** | Jika user ingin daftar cuti, approval, atau laporan cuti dibatasi/dikelompokkan per cabang atau department, aturan HR dan data pegawai perlu ditinjau. Kebutuhan itu belum ditetapkan. | Tidak diubah. |
| **Absensi** | Jika data kehadiran harus mengikuti batas akses cabang atau dilaporkan per department, employee/company, work location, dan record rules perlu ditinjau bersama Presenly. | Tidak diubah. |
| **RKA** | Keputusan saat ini adalah RKA terpisah per cabang tetapi tidak per department. Model sekarang belum memiliki `company_id` dan unik hanya per COA/tahun; tanpa perubahan kelak, RKA lintas cabang dapat tercampur. Validasi PPL yang membaca RKA juga perlu diselaraskan. | Tidak diubah pada tahap pertama atas permintaan pengguna. Tidak ada klaim bahwa validasi RKA sudah branch-isolated setelah tahap pertama. |
| **Aset** | `owner_unit` dan dimensi jurnal aset masih berupa teks. Relasi ke department/company diperlukan bila daftar aset, penyusutan, atau laporan aset harus dibatasi per cabang/departemen. | Tidak diubah; data dan posting aset tetap dengan perilaku lama. |
| **PPL** | PPL memakai `sifnext.unit`, `res.users.unit_id`, satu `unit_id` pada header, serta kode unit untuk nomor/integrasi. Migrasi department memengaruhi transaksi lama, nomor, security rules, payroll integration, dan jurnal. | Tidak diubah; master dan API lama tetap berjalan. Department baru tidak menggantikannya dulu. |
| **Payroll** | Slip sudah memiliki `hr.employee.department_id`, tetapi pembentukan PPL saat ini memilih unit pertama per company. Perubahan baru diperlukan setelah diputuskan bagaimana batch lintas department menjadi PPL. | Tidak diubah; integrasi payroll-ke-PPL tetap memakai kontrak lama. |
| **Transaksi** | `transaksi.transaction` masih memakai `sifnext.unit` dan mengirim `unit_id` ke PPL. Mengubahnya sebelum PPL akan membuat payload tidak cocok dengan penerima. | Ditunda bersama PPL walau tidak disebut dalam daftar pengecualian; ubah bersamaan saat kontrak PPL disepakati. |

Dengan batas ini, hasil tahap pertama adalah master department dan Pendapatan yang terisolasi per cabang, serta jurnal Pendapatan yang membawa dimensinya. Jurnal lama tanpa `company_id` diperlakukan sebagai data bersama dan tetap terlihat sesuai perilaku sebelumnya sampai ada pemetaan khusus. Batas ini **belum** mengubah keamanan atau laporan cabang untuk Presenly, Cuti, Absensi, RKA, Aset, PPL, Payroll, maupun Transaksi.

## 10. Status implementasi dan batas dokumen

Dokumen ini menjadi rencana dan audit trail keputusan. Implementasi tahap pertama berada di branch `feat/multi-company-branch-department-pendapatan` dan mencakup `sifnext_org`, `pendapatan`, serta dimensi jurnal/laporan yang diperlukan dari `sif_keuangan`. Modul di Bagian 9.2 tetap tidak disentuh. Database lokal `db_sifnext` sudah di-upgrade; migrasi mengisi department fallback untuk 10 record Pendapatan lama pada company yang tercatat.
