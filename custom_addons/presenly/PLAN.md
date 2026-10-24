# Plan Implementasi Presenly untuk Odoo 19

> **Dokumen historis:** konsep multi-unit di bawah telah digantikan oleh arsitektur multi-company + native `hr.work.location`. Gunakan `README.md` sebagai spesifikasi aktif.

**Status:** Rencana sebelum implementasi  
**Sumber kebutuhan:** `presenly-prd.md`  
**Fokus tahap awal:** Absensi, cuti, izin/dispensasi  
**Platform:** Odoo 19, web dashboard, mobile client melalui API  

## 1. Keputusan Produk

### 1.1 Fokus MVP

Fitur lembur dari PRD sumber belum dikerjakan pada tahap ini. MVP berfokus pada:

1. Absensi check-in/check-out.
2. Validasi lokasi kerja berbasis GPS/geofence.
3. Penyimpanan foto selfie sebagai bukti absensi.
4. Cuti menggunakan workflow dan model HR Odoo.
5. Izin/dispensasi sebagai pengajuan terpisah dari cuti.
6. Approval bertingkat.
7. Multi-unit kerja.
8. REST API yang menggunakan autentikasi Odoo yang sudah tersedia, bukan JWT custom.

Mode offline mobile tidak didukung pada tahap awal.

### 1.2 Multi-unit kerja

Istilah unit pada Presenly diperlakukan sebagai unit operasional/lokasi kerja, bukan otomatis sebagai database atau company baru. Implementasi harus tetap kompatibel dengan multi-company Odoo.

Hasil inspeksi repository menunjukkan Odoo core dan addon lokal saat ini belum menyediakan model `operating.unit`/`operating_unit`. Karena itu, Presenly akan menggunakan model custom `presenly.unit`. Model ini berisi identitas unit, company, manager/approver, departemen yang tercakup, lokasi kerja, dan status aktif. Unit bukan pengganti `res.company`; satu company dapat memiliki banyak unit.

Setiap employee dapat memiliki satu atau beberapa penugasan unit aktif dalam periode yang sama. Penugasan memiliki prioritas/unit utama opsional dan dapat menentukan lokasi kerja yang diizinkan. Lokasi kerja terhubung ke unit. Akses data dibatasi berdasarkan company, unit, dan relasi approval.

## 2. Pemetaan ke Odoo

| Kebutuhan | Implementasi Odoo |
|---|---|
| Karyawan | `hr.employee` |
| User mobile/web | `res.users` |
| Absensi resmi | `hr.attendance` |
| Cuti | `hr.leave` |
| Alokasi/kuota cuti | `hr.leave.allocation` |
| Jenis cuti | `hr.leave.type` |
| Unit kerja | model custom `presenly.unit` atau perluasan struktur operating unit yang sudah ada |
| Lokasi/geofence | `presenly.work.location` |
| Bukti selfie/GPS | `presenly.attendance.event` |
| Izin/dispensasi | `presenly.permission` |
| Approval bertingkat | konfigurasi `presenly.approval.rule` dan approval log; tetap memanfaatkan activity/chatter Odoo |
| Lampiran | `ir.attachment` |
| Audit perubahan | chatter/activity dan model audit custom bila diperlukan |

Prinsip utama: record resmi absensi tetap dibuat pada `hr.attendance`, dan record cuti tetap menggunakan `hr.leave`. Model custom hanya menyimpan kebutuhan Presenly yang belum tersedia di Odoo.

## 3. Definisi Izin dan Dispensasi

Dispensasi diperlakukan sebagai **izin khusus terkait kehadiran atau pelaksanaan kewajiban kerja**, bukan sebagai saldo cuti. Contohnya:

- Datang terlambat dengan alasan yang disetujui.
- Pulang lebih awal.
- Tidak hadir sebagian hari untuk urusan tertentu.
- Tugas/keperluan kedinasan di luar lokasi kerja.
- Kegiatan pendidikan, organisasi, keagamaan, keluarga, atau kondisi mendesak sesuai kebijakan perusahaan.
- Keperluan lain yang disetujui perusahaan dan tidak dikategorikan sebagai cuti.

Secara hukum ketenagakerjaan Indonesia, istilah dan hak "dispensasi" dapat berbeda menurut alasan, perjanjian kerja, peraturan perusahaan, PKB, dan peraturan perundang-undangan yang relevan. Karena itu, Presenly tidak mengasumsikan semua dispensasi sebagai hak normatif atau otomatis dibayar. Setiap tipe dispensasi harus memiliki konfigurasi:

- Apakah dibayar atau tidak dibayar.
- Apakah mengurangi jam kerja atau tidak.
- Apakah memengaruhi rekap kehadiran.
- Apakah membutuhkan dokumen.
- Siapa approver-nya.
- Batas pengajuan dan durasinya.

HR/legal perlu memvalidasi kebijakan final terhadap peraturan yang berlaku, termasuk UU Ketenagakerjaan beserta perubahan, PP 35/2021 bila relevan, dan peraturan perusahaan/PKB. Modul hanya menyediakan engine konfigurasi dan pencatatan keputusan.

## 4. Alur Bisnis Utama

### 4.1 Check-in/check-out

1. User terautentikasi memanggil endpoint absensi.
2. Sistem mendapatkan employee terkait dari `res.users`.
3. Sistem menentukan unit, shift, dan lokasi kerja yang aktif.
4. Sistem memvalidasi latitude/longitude terhadap geofence unit/lokasi dengan radius default 150 meter atau radius custom lokasi.
5. Sistem menyimpan bukti selfie dan metadata GPS ke event audit.
6. Sistem menolak transaksi ganda atau transaksi di luar kebijakan.
7. Untuk check-out, sistem mewajibkan unit/lokasi yang sama dengan check-in dan memvalidasi kembali geofence lokasi tersebut.
7. Sistem membuat atau menutup `hr.attendance`.
8. Sistem menghitung status tepat waktu/telat berdasarkan kalender/resource calendar Odoo.

Foto selfie wajib dikirim pada check-in dan check-out, lalu disimpan sebagai bukti pada attachment privat. Integrasi DeepFace disiapkan melalui abstraction/service boundary agar dapat diaktifkan kemudian; kegagalan atau belum tersedianya DeepFace tidak mengubah kontrak penyimpanan bukti pada tahap MVP, kecuali kebijakan perusahaan nantinya mewajibkan hasil verifikasi wajah untuk menerima transaksi.

### 4.2 Pengajuan cuti

1. Employee memilih jenis cuti dari `hr.leave.type`.
2. Sistem memvalidasi tanggal, kalender kerja, alokasi, dan benturan.
3. Pengajuan dibuat pada `hr.leave`.
4. Approval bertingkat dijalankan berdasarkan unit, departemen, manager, dan konfigurasi rule.
5. Setiap keputusan menyimpan approver, timestamp, catatan, dan urutan level.
6. Status Odoo menjadi sumber kebenaran untuk cuti.

### 4.3 Pengajuan izin/dispensasi

1. Employee memilih tipe dari master `presenly.permission.type`.
2. Employee mengisi tanggal/jam, alasan, unit, dan lampiran bila wajib.
3. Sistem memvalidasi benturan dengan absensi/cuti/izin lain.
4. Pengajuan masuk ke approval level pertama.
5. Setiap level dapat approve/reject; reject wajib menyertakan alasan.
6. Setelah seluruh level disetujui, sistem membuat dampak ke rekap kehadiran tanpa menghapus atau mengubah histori absensi secara destruktif.
7. Pembatalan dilakukan melalui workflow dan audit trail.

## 5. Model Custom yang Direncanakan

### 5.1 `presenly.unit`

Field minimum:

- `name`
- `code`
- `company_id`
- `manager_id`
- `active`
- `allowed_department_ids`

### 5.2 `presenly.work.location`

Field minimum:

- `name`
- `unit_id`
- `company_id`
- `latitude`
- `longitude`
- `radius_meters` (wajib, default 150 meter, dapat dikonfigurasi per lokasi/unit)
- `gps_accuracy_limit_meters` (batas akurasi GPS yang diterima, dapat dikonfigurasi)
- `active`
- `check_in_required`
- `check_out_required`
- `require_selfie_check_in`
- `require_selfie_check_out`

### 5.3 `presenly.employee.assignment`

Untuk menghubungkan employee dengan unit/lokasi yang berlaku:

- `employee_id`
- `unit_id`
- `work_location_id`
- `date_start`
- `date_end`
- `is_primary`
- `priority`
- `active`

Constraint hanya melarang duplikasi assignment employee-unit-lokasi pada periode yang sama. Beberapa unit aktif diperbolehkan.

### 5.4 `presenly.attendance.event`

Untuk audit bukti request mobile:

- `employee_id`
- `attendance_id`
- `event_type`
- `event_time`
- `latitude`
- `longitude`
- `accuracy`
- `distance_from_location`
- `work_location_id`
- `selfie_attachment_id`
- `source`
- `device_id_hash`
- `validation_status`
- `validation_message`

### 5.5 `presenly.permission`

Field minimum:

- `name` / reference
- `employee_id`
- `unit_id`
- `permission_type_id`
- `date_from`, `date_to`
- `hour_from`, `hour_to`
- `reason`
- `attachment_ids`
- `state`
- `affects_attendance`
- `paid_status`
- `approval_level`
- `rejection_reason`

### 5.6 Approval configuration

Model approval harus mendukung:

- Beberapa level yang dapat dikonfigurasi per company, unit, jenis cuti, dan tipe dispensasi.
- Approver spesifik, manager employee, manager unit, HR, atau group Odoo.
- Urutan level dan jumlah level.
- Company/unit scope.
- Delegasi approver bila diperlukan.
- Hanya level aktif yang dapat memproses pengajuan.
- Pengajuan berpindah ke level berikutnya setelah level berjalan disetujui.
- Satu penolakan pada level mana pun menghentikan workflow.
- Log keputusan yang immutable.

## 6. Security dan Akses Data

Security mengikuti mekanisme Odoo:

- `res.groups` untuk role Employee, Unit Approver, HR Officer, HR Manager, dan Administrator.
- `ir.model.access.csv` untuk hak CRUD model.
- Record rules untuk company, unit, employee, dan relasi approver.
- Attachment selfie dibatasi agar tidak dapat diakses oleh user umum.
- Dokumen izin sakit/medis memiliki rule lebih ketat daripada dokumen izin biasa.
- User tidak dapat mengubah status pengajuan secara langsung melalui write biasa.
- Semua approve/reject/correction menggunakan method server yang tervalidasi.

Autentikasi menggunakan username dan password Odoo melalui mekanisme standar Odoo. Tidak membuat JWT custom. Untuk client mobile, login dilakukan melalui endpoint/session authentication Odoo (`/web/session/authenticate`) atau mekanisme RPC standar yang sesuai deployment, lalu request berikutnya menggunakan session cookie yang diterbitkan Odoo. Password tidak dikirim ulang pada setiap request dan tidak disimpan oleh module Presenly. Seluruh endpoint custom tetap memvalidasi user, company, unit, dan access rights di server.

## 7. API Tahap Awal

Prefix yang digunakan:

```text
/api/presenly/v1
```

Endpoint yang direncanakan:

```text
GET  /attendance/status
POST /attendance/check-in
POST /attendance/check-out
GET  /attendance/history

GET  /leave/types
GET  /leave/balance
GET  /leaves
POST /leaves
POST /leaves/{id}/submit
POST /leaves/{id}/cancel

GET  /permissions/types
GET  /permissions
POST /permissions
GET  /permissions/{id}
POST /permissions/{id}/submit
POST /permissions/{id}/cancel

GET  /approvals/pending
POST /approvals/{id}/approve
POST /approvals/{id}/reject
```

Upload selfie/lampiran menggunakan multipart request atau attachment endpoint terproteksi. Response API harus konsisten dan tidak mengekspos traceback Odoo.

## 8. Tahapan Implementasi

### Fase 0 — Validasi dan discovery

- Konfirmasi modul Odoo yang terpasang: `hr`, `hr_attendance`, `hr_holidays`, `mail`.
- Inspeksi apakah sudah ada konsep operating unit/unit pada addon lain.
- Finalisasi definisi unit, lokasi, shift, dan approval.
- Finalisasi master jenis dispensasi bersama HR/legal.
- Menetapkan kebijakan retensi foto, GPS, dan dokumen.

**Output:** technical decision record dan model final.

### Fase 1 — Struktur addon dan security

- Manifest dan dependency.
- Models dasar unit, assignment, work location, permission type.
- Groups, access CSV, record rules.
- Sequence reference.
- Menyiapkan data demo dan test fixtures.

### Fase 2 — Absensi

- Integrasi `hr.attendance`.
- Check-in/check-out melalui web/API.
- GPS geofence dan validasi akurasi.
- Penyimpanan selfie event.
- Perhitungan telat dari resource calendar.
- Audit gagal/berhasil dan koreksi berwenang.

### Fase 3 — Cuti

- Konfigurasi `hr.leave.type`.
- Tampilan dan API saldo/pengajuan.
- Approval bertingkat untuk cuti.
- Attachment dan notifikasi.
- Record rules multi-company/multi-unit.

### Fase 4 — Izin/dispensasi

- Master tipe dispensasi.
- Model pengajuan dan workflow.
- Approval bertingkat.
- Dampak ke rekap kehadiran.
- Aturan berbayar/tidak berbayar sebagai data kebijakan, tanpa payroll calculation.

### Fase 5 — API dan mobile contract

- Controller JSON Odoo.
- Authentication dan authorization.
- Multipart attachment.
- Pagination, idempotency, dan error format.
- Dokumentasi OpenAPI bila kontrak endpoint sudah stabil.

### Fase 6 — QA dan hardening

- Unit test model/constraint.
- HTTP/controller test.
- Test multi-company dan multi-unit.
- Test approval race condition dan duplicate request.
- Test geofence dengan batas radius.
- Security review attachment dan record rules.

## 9. Acceptance Criteria untuk MVP

### Absensi

- Employee hanya dapat check-in pada unit/lokasi yang aktif dan diizinkan.
- Radius default geofence adalah 150 meter dan dapat dioverride per lokasi.
- Request di luar radius ditolak dengan pesan yang jelas.
- Check-in/check-out ganda ditolak secara atomik.
- Check-out hanya diterima pada unit/lokasi yang sama dengan check-in.
- Waktu server Odoo menjadi waktu transaksi utama.
- Selfie dan GPS tersimpan sebagai event audit.
- `hr.attendance` tetap menjadi record absensi resmi.

### Cuti

- Employee dapat melihat saldo dan jenis cuti yang diizinkan.
- Pengajuan menggunakan `hr.leave`.
- Sistem memvalidasi benturan dan alokasi.
- Approval dapat berjalan lebih dari satu level.
- Approver hanya melihat transaksi dalam scope-nya.
- Penolakan membutuhkan alasan.

### Izin/dispensasi

- Dispensasi tidak mengurangi saldo cuti.
- Tipe dispensasi dapat dikonfigurasi per company/unit.
- Tipe dapat menentukan apakah lampiran wajib dan apakah memengaruhi kehadiran.
- Approval bertingkat dan audit keputusan tersedia.
- Persetujuan tidak menghapus histori absensi.
- Dokumen sensitif hanya dapat diakses role yang berwenang.

## 10. Hal yang Tidak Dikerjakan pada Plan Ini

- Payroll dan perhitungan upah lembur.
- Mode offline.
- Integrasi fingerprint.
- Verifikasi biometrik DeepFace secara aktif.
- Push notification provider tertentu.
- JWT custom.
- Penghapusan data biometrik tanpa kebijakan retensi yang disetujui.

## 11. Keputusan yang Masih Dibutuhkan Sebelum Coding

1. Model unit menggunakan `presenly.unit` karena tidak ditemukan model operating unit pada repository saat ini.
2. Employee dapat memiliki beberapa assignment unit aktif dalam periode yang sama.
3. Check-out wajib dilakukan pada unit/lokasi kerja yang sama dengan check-in.
4. Radius default geofence adalah 150 meter dan dapat dikonfigurasi per lokasi/unit.
5. Selfie wajib untuk check-in dan check-out.
6. Approval cuti dan dispensasi menggunakan feature leveling approval yang dapat dikonfigurasi.
7. Apakah cuti mengikuti hari kerja dari `resource.calendar` Odoo?
8. Retensi data dibuat sesingkat mungkin untuk performa melalui purge terjadwal, tetapi durasi final tetap harus disahkan HR/legal karena kewajiban audit, perselisihan kerja, dan perlindungan data dapat menentukan minimum retensi.
9. Mobile menggunakan autentikasi username/password standar Odoo dan session cookie Odoo; tidak ada JWT custom.
10. Apakah dokumen `presenly-prd.md` dianggap target jangka panjang, sementara lembur tetap ditunda dari MVP?
