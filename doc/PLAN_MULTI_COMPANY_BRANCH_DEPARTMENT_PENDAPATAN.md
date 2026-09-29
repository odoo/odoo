# Rencana Multi-Company, Cabang, Departemen, dan Pendapatan

**Status:** Scope lanjutan diterapkan dan `db_sifnext` berhasil di-upgrade; clone migrasi lulus 41 test
**Tanggal:** 28 September 2026
**Ruang lingkup:** Master cabang/departemen dan penerapannya pada Pendapatan, jurnal, PPL/payroll, Transaksi, RKA, dan Aset. Presenly, Absensi, dan Cuti dikecualikan.

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
- Finance pusat dapat membaca seluruh cabang, tanpa hak membuat, mengubah, menyetujui, atau mem-posting transaksi pada modul dalam scope.

Rekomendasi kode wajib per departemen dan satu PPL payroll per departemen telah disetujui dan diterapkan. Implementasi master menggunakan `hr.department`; model aktif `sifnext.unit` diganti, dengan backup legacy dan pemetaan relasi pada migrasi.

## 2. Temuan baseline sebelum implementasi

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

Tabel di bawah mencatat baseline sebelum perubahan dan kaitan antarmodul. Scope yang disetujui serta modul yang dikecualikan dicatat pada Bagian 9.

| Modul | Kondisi sekarang | Dampak yang perlu direncanakan |
|---|---|---|
| `sifnext_ppl` | PPL memakai `unit_id` ke `sifnext.unit`; user memiliki `unit_id`; validasi memastikan unit dan company sama. Payload integrasi mengekspor `unit`. | Ganti referensi bisnis ke departemen, migrasikan unit lama, pertahankan kontrak payload `unit` sementara, dan tambahkan department ke kontrak baru. Pertahankan aturan PPL “milik sendiri” serta Finance/Director, dengan batas company tetap berlaku. |
| `transaksi` | `transaksi.transaction.unit_id` menunjuk `sifnext.unit` dan default dari user. Pembuatan PPL meneruskan `unit_id`. | Ganti form, domain, validasi, dan payload agar memakai department serta company cabang yang sama. |
| `sif_keuangan` | `sif.jurnal.entry.unit_name` adalah teks; buku besar, laba-rugi, neraca, wizard, dan export memakai filter teks `unit_name`. Header jurnal belum memiliki dimensi departemen terstruktur. | Tambahkan dimensi company dan department pada jurnal, lalu migrasikan filter dan laporan ke relasi. Simpan nilai teks lama sebagai kompatibilitas/histori sampai rekonsiliasi selesai. |
| `sif_rka` | `sif.rka.budget` saat ini tidak mempunyai dimensi company atau department; constraint uniknya `(account_id, tahun)`. PPL mencari RKA hanya berdasarkan COA dan tahun. | Keputusan pengguna: RKA dibedakan per cabang, bukan departemen. Tambahkan `company_id` dan ubah pencarian/constraint agar RKA dan realisasi tidak tercampur antar-cabang; department tidak menjadi dimensi RKA. |
| `sifnext_asset` | Aset menyimpan `owner_unit` sebagai teks dan mengirim `unit_name` ke jurnal. | Ganti master owner menjadi department; pastikan company/departemen aset dan jurnal konsisten. |
| `hr_payroll_custom` | Slip sudah memiliki `department_id` terkait ke departemen pegawai dan payroll batch memiliki company. | Pertahankan relasi standar; validasi company dan departemen pegawai. Integrasi payroll ke PPL saat ini memilih unit pertama di company; rekomendasinya satu batch menghasilkan satu PPL per departemen yang ada di batch tersebut. |
| `sifnext_operational` | Peminjaman membaca `hr.employee.department_id` untuk menampilkan departemen peminjam. | Pertahankan sebagai sumber data departemen pegawai; tinjau filter company pada record operasional. |

## 3. Model data target

### 3.1 Cabang

1. Perusahaan induk tetap berupa `res.company` root.
2. Setiap cabang dibuat sebagai `res.company` dengan `parent_id` menunjuk perusahaan induk.
3. Gunakan tab **Branches** bawaan pada form perusahaan. Tambahkan akses yang jelas dari form cabang ke daftar departemen, misalnya tab atau smart button “Departemen” yang membuka `hr.department` dengan filter cabang tersebut.
4. Jangan gunakan `hr.work.location` sebagai pengganti company branch. Satu cabang dapat mempunyai lebih dari satu lokasi fisik.

### 3.2 Departemen

1. Gunakan `hr.department` sebagai satu-satunya master departemen.
2. Setiap departemen operasional wajib mempunyai `company_id` yang menunjuk cabang pemiliknya. Departemen induk/anak, bila dipakai, harus tetap berada di cabang yang sama.
3. Tambahkan field kode SIF wajib (`sif_code`) pada setiap department operasional untuk mempertahankan prefix nomor PPL, integrasi, dan pelaporan. Kode unik di dalam cabang, dinormalisasi konsisten, dan tidak dicampur dengan `journal_unit_dept`.
4. Simpan klasifikasi akuntansi lama pada `hr.department.sif_journal_unit_dept` dan pada tabel backup unit legacy untuk audit; klasifikasi ini bukan kode atau nama department.

### 3.3 Pengguna

1. Gunakan `res.users.department_id` sebagai default Pendapatan dan `hr.employee.department_id` sebagai sumber department payroll. Keduanya tidak disinkronkan otomatis.
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

## 4. Kebijakan akses yang diterapkan

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
- API PPL/Transaksi mempertahankan `unit` sebagai alias kompatibilitas; `department` menjadi relasi otoritatif. Penghapusan alias dilakukan setelah konsumen terverifikasi.

## 5. Urutan implementasi

### Fase 0 — Keputusan dan inventarisasi

1. Keputusan telah ditetapkan: kode departemen wajib dan unik per cabang; satu PPL payroll per departemen; Finance pusat read-only; RKA per company, bukan department; fallback tidak boleh menebak cabang.
2. Inventarisasi company, departemen, kode/unit lama, pengguna, PPL/payroll, Pendapatan/jurnal, RKA, aset, dan transaksi bank.
3. Jalankan upgrade pada clone database dengan backup tabel legacy dan validasi mapping sebelum menyentuh database kerja.

### Fase 1 — Fondasi master organisasi

1. Modul `sifnext_org` memperluas `hr.department` dengan kode SIF, penugasan departemen pengguna, klasifikasi jurnal legacy, dan tampilan administrasi.
2. Kode dinormalisasi dan unik dalam company; validasi server mencegah kode duplikat dan department pengguna lintas company yang diizinkan.
3. Cabang tetap menggunakan `res.company` dan departemen dibuat dari administrasi HR/company.

### Fase 2 — Migrasi master dan pengguna

1. Pastikan parent-child `res.company` sesuai struktur cabang dan department memiliki company yang benar.
2. Backup unit lama dan relasi user/PPL/Transaksi; pindahkan referensi bisnis ke `hr.department`.
3. Backfill relasi PPL, payroll batch, transfer bank, aset, dan pengguna tanpa mengubah histori nominal/workflow.
4. Setelah semua relasi dimigrasikan dan backup diperiksa, hapus model/tabel aktif `sifnext.unit`; simpan backup legacy untuk audit.

### Fase 3 — Pendapatan dan keamanan

1. Pendapatan memakai company/department terstruktur, kategori per cabang, company record rules, dan validasi pada UI/API/workflow.
2. PPL dan Transaksi memakai `department_id`, validasi company/department, migrasi data lama, dan kontrak `unit` kompatibilitas yang dibutuhkan.
3. Payroll menghasilkan satu PPL per department pegawai pada batch; hubungan ke batch tetap disimpan.
4. RKA menggunakan `company_id` untuk pemisahan anggaran dan realisasi antarcabang.
5. Aset menggunakan company/department owner dan meneruskan dimensi tersebut ke jurnal.

### Fase 4 — Jurnal dan laporan keuangan

1. Jurnal dari Pendapatan, PPL, dan aset membawa company/department; jurnal legacy tetap menyimpan nilai teks untuk audit.
2. Terapkan Finance pusat read-only secara server-side pada model dan operasi workflow, selain ACL/menu.
3. Pertahankan alias payload `unit` selama masa kompatibilitas; gunakan `department` sebagai field relasi otoritatif.

### Fase 5 — Integrasi dan kompatibilitas

PPL, payroll, Transaksi, Aset, dan RKA termasuk dalam scope implementasi yang disetujui. Alias payload `unit` dipertahankan selama masa kompatibilitas; `hr.department` menjadi relasi bisnis aktif. Presenly, Absensi, dan Cuti tetap di luar scope.

### Fase 6 — Penghapusan legacy dan rilis

1. Jalankan migrasi pada clone database, cocokkan jumlah record/dimensi sebelum dan sesudah, serta pastikan tabel backup legacy tersedia.
2. Jalankan test otomatis dan UAT lintas cabang; test scope lanjutan terakhir lulus 41/41.
3. Pertahankan nilai teks/alias integrasi legacy yang masih diperlukan; jangan gunakan `sifnext.unit` sebagai master aktif.

## 6. Strategi migrasi data

1. Buat backup penuh database dan filestore sebelum upgrade.
2. Salin unit lama dan relasi `res.users`, PPL, serta Transaksi ke tabel backup migrasi sebelum field legacy dihapus.
3. Migrasikan master ke `hr.department`, kemudian backfill company/department pada Pendapatan, PPL, payroll, jurnal, RKA, aset, dan transfer.
4. Gunakan company yang tercatat dan mapping eksplisit. Jika department tidak dapat dipetakan, gunakan “Belum Diklasifikasikan” pada company tersebut; jangan menebak cabang.
5. Simpan nilai teks `unit_name`/owner dan payload kompatibilitas untuk audit/integrasi lama.
6. Bandingkan jumlah record, company, department, nominal, status, dan jurnal sebelum/sesudah migrasi.

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
- PPL, payroll, Transaksi, dan Aset mempertahankan company/department konsisten; batch payroll lintas department membuat satu PPL per department.
- RKA dan realisasi terpisah per company, tanpa department sebagai dimensi anggaran.
- Finance pusat dapat membaca cabang yang diizinkan dan ditolak saat mencoba create/write/unlink atau menjalankan workflow mutation.

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

5. Finance pusat memiliki akses baca ke seluruh cabang pada modul dalam scope, tanpa hak perubahan atau approval/posting.

### 8.2 Rekomendasi yang disetujui

1. **Kode department wajib dan unik per cabang.** Master lama `sifnext.unit` sudah mempunyai `code`, dan nomor PPL menggunakan kode tersebut. Kode department yang stabil mempermudah migrasi, integrasi, serta identifikasi saat nama department berubah atau sama di cabang lain. Kode yang sama boleh digunakan di cabang berbeda; uniqueness dijaga di dalam company/cabang.
2. **Payroll batch lintas department menghasilkan satu PPL per department.** Model PPL menaruh satu department pada header. Memecah batch mempertahankan struktur satu PPL = satu department, membuat jurnal/laporan mudah ditelusuri, dan menghindari penetapan department yang keliru. Satu batch dapat menghasilkan beberapa PPL, approval, dan jurnal; setiap PPL ditautkan ke batch asal.

   Alternatifnya adalah satu PPL gabungan per batch. Agar department tidak hilang, perlu menambah department di setiap baris PPL, mengubah integrasi payroll, membuat jurnal mempertahankan department per baris, dan mengadaptasi laporan. Efek positifnya lebih sedikit dokumen dan satu approval; implementasinya lebih luas dan tidak cocok dengan desain PPL header tunggal yang ada. Karena RKA tidak dibedakan per department, pemisahan ini untuk jejak audit/pelaporan, bukan pembatasan budget.
3. **Sumber department pengguna.** `res.users.department_id` menjadi default untuk Pendapatan; payroll-to-PPL menggunakan `hr.employee.department_id`. Keduanya tidak disinkronkan secara otomatis.

## 9. Scope implementasi dan pengecualian

### 9.1 Modul dalam scope

1. **`sifnext_org`** — master `hr.department`, kode unik, penugasan departemen pengguna, klasifikasi jurnal legacy, backup/migrasi dari `sifnext.unit`; cabang tetap memakai `res.company`.
2. **`pendapatan`** — department terstruktur, kategori per cabang, company record rules, validasi company/department, dan jalur Finance pusat read-only.
3. **`sif_keuangan`** — dimensi company/department pada jurnal, laporan terkait, kompatibilitas `unit_name`, dan pemeriksaan read-only Finance pusat.
4. **`sifnext_ppl` dan payroll integration** — PPL memakai department, migrasi referensi user/PPL, satu PPL per department payroll, dan relasi ke batch payroll.
5. **`transaksi`** — department/company pada transfer, validasi PPL, aturan cabang dan akses Finance pusat read-only.
6. **`sif_rka`** — RKA dan realisasi dipisahkan per company/cabang, tidak per department.
7. **`sifnext_asset`** — company/department owner, migrasi asset, serta dimensi journal pembelian/penyusutan.

Pada clone `sifnext_full_scope_migration_test_fix`, upgrade selesai dan 41/41 test lulus. Migrasi memetakan 1 unit legacy ke department, menetapkan department pada 4 user, memigrasikan 22 referensi PPL dan 9 transaksi bank; 2 transaksi memakai department fallback company. Lima aset memakai fallback company karena tidak ada nama owner yang cocok. Tabel aktif `sifnext_unit` dihapus setelah backup dan relasi lama diverifikasi. `db_sifnext` kemudian di-upgrade dengan hasil mapping yang sama setelah backup database ke `/tmp/opencode/db_sifnext_pre_multi_scope_20260928.dump`.

### 9.2 Modul yang dikecualikan

| Modul | Mengapa mungkin perlu penyesuaian di masa depan | Status saat ini |
|---|---|---|
| **Presenly** | Perlu perubahan hanya bila perusahaan ingin aturan presensi/API/approval mengikuti struktur cabang atau department baru. Saat ini Presenly memakai `hr.work.location` untuk lokasi kerja fisik/geofence; lokasi ini tidak boleh otomatis diubah menjadi department atau company branch. | Tidak diubah. Tidak menjadi dependensi Pendapatan. |
| **Cuti** | Jika user ingin daftar cuti, approval, atau laporan cuti dibatasi/dikelompokkan per cabang atau department, aturan HR dan data pegawai perlu ditinjau. Kebutuhan itu belum ditetapkan. | Tidak diubah. |
| **Absensi** | Jika data kehadiran harus mengikuti batas akses cabang atau dilaporkan per department, employee/company, work location, dan record rules perlu ditinjau bersama Presenly. | Tidak diubah. |

Presenly, Cuti, dan Absensi tetap tidak berubah. Modul dalam scope memakai company/department untuk validasi dan visibilitas sesuai role; jurnal lama yang belum memiliki dimensi tetap mempertahankan data teks legacy untuk audit.

## 10. Status implementasi dan batas dokumen

Dokumen ini menjadi audit trail keputusan dan status implementasi. Branch `feat/multi-company-branch-department-pendapatan` mencakup seluruh modul pada Bagian 9.1. Clone database `sifnext_full_scope_migration_test_fix` berhasil di-upgrade dan seluruh 41 test scope lulus; `db_sifnext` juga berhasil di-upgrade setelah backup. Presenly, Cuti, dan Absensi tidak diubah.
