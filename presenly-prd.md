# PRD — Presenly Attendance Tools untuk Odoo 19

**Produk:** Presenly / SIDAC  
**Versi dokumen:** 2.0  
**Status:** Baseline implementasi aktif  
**Tanggal baseline:** 5 September 2026  
**Platform:** Odoo 19 Web dan backend API untuk mobile  
**Aplikasi utama:** Odoo Attendances (`hr_attendance`)  
**Addon teknis:** `custom_addons/presenly`

---

## 1. Tujuan Dokumen

Dokumen ini mendefinisikan produk Presenly berdasarkan arsitektur Odoo 19 yang aktif dan fitur yang sudah dibuat. PRD ini bukan rancangan backend terpisah dan tidak mengharuskan Presenly menduplikasi fitur yang sudah tersedia secara native di Odoo.

Prinsip pembacaan dokumen:

1. Model dan workflow native Odoo digunakan sebagai sumber data utama jika sudah sesuai kebutuhan.
2. Addon Presenly hanya menambah kebutuhan yang belum tersedia secara native, seperti geofence, selfie evidence, jadwal beberapa lokasi dalam satu hari, izin/dispensasi, dan approval bertingkat.
3. Attendances menjadi application shell. Presenly tidak memiliki launcher aplikasi terpisah.
4. Kebutuhan yang belum dibuat dicatat sebagai backlog, bukan dianggap sudah tersedia.
5. Kesiapan kode dan kesiapan operasional dibedakan. Fitur dapat selesai secara teknis tetapi belum dapat dipakai sebelum master data dikonfigurasi.

Dokumen historis sebelum migrasi tidak lagi menjadi sumber spesifikasi aktif. Penjelasan teknis rinci tetap tersedia di:

- `custom_addons/presenly/README.md`
- `custom_addons/presenly/docs/MOBILE_API_FULL.md`
- `custom_addons/presenly/docs/WORKING_HOURS_LOCATION_INTEGRATION.md`
- `custom_addons/presenly/docs/MIGRATION_TO_HR_ATTENDANCE.md`

---

## 2. Ringkasan Produk

Presenly memperluas Odoo Attendances agar employee dapat melakukan check-in dan check-out berdasarkan lokasi serta jadwal kerja yang sah. Sistem menyimpan GPS, jarak dari geofence, selfie bila diwajibkan, sumber transaksi, dan hasil validasi sebagai evidence.

Produk juga menyatukan akses operasional terhadap:

- Attendance native Odoo.
- Working Hours native Odoo.
- Work Location native Odoo.
- Time Off native Odoo.
- Permission/dispensation custom Presenly.
- Approval bertingkat untuk Time Off dan Permission.
- Session-based mobile API.

Target utamanya adalah organisasi yang memiliki banyak company, cabang, sekolah, atau lokasi kerja, termasuk employee yang bekerja pada beberapa lokasi dalam satu hari.

---

## 3. Keputusan Arsitektur Produk

### 3.1 Sumber data utama

| Konsep bisnis | Model sumber data |
|---|---|
| Legal entity/company internal | `res.company` |
| User web/mobile | `res.users` |
| Employee | `hr.employee` dan versi aktif `hr.version` |
| Struktur organisasi | `hr.department` |
| Sekolah, cabang, kantor, atau lokasi fisik | `hr.work.location` |
| Alamat dan koordinat lokasi | `res.partner` melalui Work Address |
| Jam dan hari kerja | `resource.calendar` |
| Periode jam kerja | `resource.calendar.attendance` |
| Lokasi reguler satu lokasi per hari | Field lokasi harian native Employee |
| Pengecualian lokasi pada tanggal tertentu | `hr.employee.location` |
| Beberapa lokasi per hari/per jam | `presenly.work.location.schedule` |
| Attendance resmi | `hr.attendance` |
| Evidence attendance | `presenly.attendance.event` |
| Time Off/cuti resmi | `hr.leave` |
| Tipe dan kuota Time Off | `hr.leave.type` dan `hr.leave.allocation` |
| Izin/dispensasi | `presenly.permission` |
| Tipe izin/dispensasi | `presenly.permission.type` |
| Konfigurasi approval bertingkat | `presenly.approval.rule` |
| Riwayat keputusan approval | `presenly.approval.log` |
| Dokumen dan selfie | `ir.attachment` private |

### 3.2 Batas tanggung jawab

- **Odoo menentukan kapan employee bekerja** melalui Working Hours.
- **Presenly menentukan di mana employee bekerja** melalui Work Location Schedule jika konfigurasi native satu lokasi per hari tidak mencukupi.
- `hr.attendance` tetap menjadi sumber kebenaran sesi kehadiran.
- `hr.leave` tetap menjadi sumber kebenaran Time Off.
- Permission tidak digabung ke Time Off karena dapat berupa dispensasi parsial, terlambat, pulang awal, atau izin lain yang tidak mengurangi saldo cuti.
- Company Employee selalu mengarah ke `res.company`, bukan Contact bertipe Company.

### 3.3 Keputusan autentikasi

Mobile API menggunakan autentikasi session resmi Odoo:

1. Login melalui `/web/session/authenticate`.
2. Client menyimpan cookie `session_id` secara aman.
3. Cookie dikirim ke endpoint `/api/presenly/v1/*`.
4. Logout melalui `/web/session/destroy`.

Tidak ada JWT custom dan tidak ada mode offline pada baseline ini.

### 3.4 Keputusan kompatibilitas API

- Prefix API tetap `/api/presenly/v1`.
- `work_location_id` adalah field kanonis.
- `unit_id` diterima sementara sebagai alias ID `hr.work.location` untuk kompatibilitas client lama.
- Alias tersebut tidak mengacu pada model Unit custom.

---

## 4. Ruang Lingkup Baseline

### 4.1 Sudah termasuk dalam produk

1. Integrasi UI ke aplikasi native Attendances.
2. Check-in dan check-out ke `hr.attendance`.
3. Validasi employee aktif dan Related User.
4. Validasi Working Hours dan Work Location yang berlaku.
5. Geofence per Work Location dengan radius yang dapat dikonfigurasi.
6. Validasi batas akurasi GPS.
7. Selfie check-in/check-out yang dapat diwajibkan per lokasi.
8. Evidence untuk transaksi berhasil dan percobaan gagal.
9. Snapshot Company, Work Location, dan Schedule pada Attendance.
10. Working Hours native dan jadwal lokasi beberapa slot dalam satu hari.
11. Weekly schedule, Specific Date schedule, validity period, dan kalender dua mingguan.
12. Deteksi gap dan konflik antara Working Hours dan Work Location Schedule.
13. Generator Work Location Schedule dari Working Hours.
14. Time Off menggunakan model dan perhitungan native Odoo.
15. Permission/dispensation full-day atau partial-hours.
16. Lampiran private pada Permission.
17. Single-path Approval Journey bertingkat untuk Time Off dan Permission.
18. Unified My Approvals queue, snapshot level/approver, rejection reason, activity, dan decision log.
19. Record rules multi-company dan pembatasan employee/approver.
20. Backend JSON-RPC untuk Attendance, Time Off, dan Permission.

### 4.2 Tidak termasuk dalam baseline

1. Payroll final atau pembayaran gaji.
2. Pengajuan dan perhitungan nilai lembur custom Presenly.
3. Attendance lembur yang terhubung ke request lembur.
4. Mobile client iOS/Android/Flutter/React Native.
5. Mode offline dan sinkronisasi offline.
6. JWT custom.
7. Integrasi fingerprint fisik.
8. Verifikasi wajah/DeepFace aktif.
9. Push notification provider tertentu.
10. Project-based attendance dan project-based authorization.
11. Workflow medical terpisah dari Time Off/Permission.
12. Custom OWL dashboard yang menggantikan dashboard native Odoo.

Fitur di luar baseline hanya dikerjakan setelah kebutuhan bisnis dan kebijakannya disetujui.

---

## 5. Aktor dan Hak Akses

| Aktor | Tanggung jawab |
|---|---|
| Employee | Melihat data milik sendiri, melakukan attendance melalui mobile, membuat dan melihat Permission/Time Off sesuai akses |
| Approver | Melihat request yang sedang/pernah ditugaskan, lalu approve atau reject pada level aktif |
| HR Officer | Mengelola request dan evidence dalam allowed companies sesuai ACL native dan Presenly |
| Presenly Administrator | Mengelola Work Location, Working Hours, Location Schedule, Permission Type, Approval Level, dan monitoring dalam allowed companies |
| Odoo Administrator | Administrasi sistem, user, company, modul, dan konfigurasi teknis |

Role Presenly:

- `group_presenly_employee`
- `group_presenly_approver`
- `group_presenly_hr`
- `group_presenly_manager`

Presenly Administrator mengimplikasikan akses HR Officer yang diperlukan untuk membuka Employee dan Working Hours. Allowed Companies pada `res.users` tetap menentukan company mana yang dapat dilihat dan dikelola.

---

## 6. Organisasi dan Multi-Company

### 6.1 Company

Company legal/operasional dibuat melalui **Settings > Users & Companies > Companies** dan disimpan sebagai `res.company`.

Setiap `res.company` mempunyai partner pendamping untuk nama, alamat, logo, telepon, dan data kontak. Membuat Contact dengan tipe Company hanya menghasilkan `res.partner`; hal itu tidak otomatis membuat company internal dan tidak membuatnya tersedia pada field Company Employee.

### 6.2 Allowed Companies

Pilihan Company pada Employee dibatasi oleh:

- Allowed Companies user.
- Company aktif pada session/context.
- Group multi-company.
- ACL dan record rules Odoo.

Administrator harus menambahkan company ke Allowed Companies user sebelum user dapat mengelola Employee, Work Location, schedule, atau transaksi pada company tersebut.

### 6.3 Work Location

Sekolah, cabang, kantor, dan tempat kerja fisik menggunakan `hr.work.location`. Work Location wajib berada pada Company yang sama dengan Employee untuk dapat digunakan oleh Presenly.

Work Location dapat mempunyai:

- Work Address.
- Latitude dan longitude dari address.
- Radius geofence; default 150 meter.
- Batas akurasi GPS; default 100 meter.
- Kebijakan selfie check-in dan check-out.
- Location Manager dan approver.
- Status Geofence Ready.

Koordinat valid harus berada pada rentang latitude `-90..90` dan longitude `-180..180`.

---

## 7. Working Hours dan Work Location Schedule

### 7.1 Working Hours

`resource.calendar` adalah sumber otoritatif kapan Employee bekerja. Presenly tidak menduplikasi kalender kerja.

Working Hours menentukan:

- Hari kerja.
- Jam mulai dan selesai.
- Periode istirahat berdasarkan attendance lines native.
- Flexible Hours.
- Kalender Week 1/Week 2.
- Kalender Employee yang berlaku berdasarkan versi Employee.

### 7.2 Pemilihan pendekatan lokasi

Gunakan konfigurasi paling native yang memenuhi kebutuhan:

1. Primary Work Location sebagai fallback.
2. Lokasi harian native untuk satu lokasi sepanjang hari.
3. Exceptional Location native untuk perubahan satu tanggal.
4. Work Location Schedule Presenly jika satu hari memiliki beberapa lokasi atau lokasi harus dibatasi per jam.

### 7.3 Aturan Work Location Schedule

- Schedule dapat berupa Weekly atau Specific Date.
- Slot aktif harus berada sepenuhnya di dalam Working Hours.
- Slot satu Employee tidak boleh overlap pada scope tanggal/hari yang sama.
- Weekly slot dapat mempunyai Valid From dan Valid Until.
- Kalender dua mingguan membedakan Week 1 dan Week 2.
- Specific Date menggunakan kalender/versi Employee yang berlaku pada tanggal tersebut.
- Specific Date menggantikan seluruh Weekly slot pada tanggal itu.
- Slot konflik akibat perubahan Working Hours dipertahankan agar dapat diperbaiki atau diarsipkan, tetapi diabaikan oleh resolver attendance.

### 7.4 Prioritas resolver lokasi

1. Specific Date slot yang cocok dengan tanggal dan waktu.
2. Weekly slot yang cocok dengan hari, Week 1/Week 2, dan waktu.
3. Exceptional Location native pada tanggal tersebut.
4. Lokasi harian native Employee.
5. Primary Work Location Employee.

Jika sebuah hari dikontrol oleh slot aktif tetapi waktu sekarang berada di luar seluruh slot, sistem tidak menggunakan fallback dan check-in ditolak.

### 7.5 Generator schedule

Pada tab **Working Hours & Locations**, administrator dapat:

- Melihat status Fully Assigned, Working Hours Have Gaps, Schedule Conflict, Flexible Working Hours, atau No Working Hours.
- Membuka kalender Working Hours native.
- Menghasilkan preview lokasi dari Working Hours.
- Mengisi hanya gap dengan mode **Fill Unassigned Working Hours**.
- Mengganti seluruh Weekly slot dengan mode **Replace All Weekly Location Slots**.
- Membagi satu periode Working Hours ke beberapa Work Location.

---

## 8. Attendance

### 8.1 Check-in

Employee dapat check-in apabila:

1. User aktif dan terhubung dengan Employee aktif.
2. Tidak ada attendance session yang masih terbuka.
3. Resolver menemukan Work Location yang berlaku.
4. Work Location aktif, satu company dengan Employee, dan Geofence Ready.
5. Latitude dan longitude request valid.
6. Akurasi GPS tidak melebihi batas lokasi.
7. Posisi berada dalam radius geofence.
8. Selfie tersedia jika diwajibkan oleh lokasi.

Saat berhasil, sistem membuat `hr.attendance` dan menyimpan:

- Employee.
- Server timestamp sebagai `check_in`.
- Operational Company snapshot.
- Work Location snapshot.
- Work Location Schedule snapshot jika digunakan.
- Latitude dan longitude.
- Jarak dari lokasi.
- Selfie attachment bila dikirim.
- Source `mobile`.

### 8.2 Check-out

Check-out hanya dapat dilakukan jika ada attendance session terbuka. Sistem mewajibkan:

- Work Location yang sama dengan snapshot saat check-in.
- Geofence lokasi tersebut masih terpenuhi.
- Akurasi GPS valid.
- Selfie tersedia jika diwajibkan.

Setelah check-out, Employee dapat check-in lagi pada slot/lokasi berikutnya. Beberapa sesi dalam satu hari diperbolehkan, tetapi sesi tidak boleh berjalan bersamaan.

### 8.3 Evidence

Setiap check-in/check-out yang berhasil membuat `presenly.attendance.event`. Percobaan yang gagal juga disimpan menggunakan transaksi terpisah agar tidak ikut rollback bersama transaksi bisnis.

Evidence mencakup:

- Event type dan waktu.
- Employee dan Attendance terkait.
- Company dan Work Location.
- Schedule.
- GPS, akurasi, dan jarak.
- Selfie attachment.
- Source.
- Validation status dan message.

Evidence tidak menggantikan `hr.attendance`; evidence adalah bukti dan audit teknis.

### 8.4 Attendance web

Form dan reporting native Attendance tetap digunakan. Presenly menambahkan metadata Company, Work Location, Schedule, distance, source, selfie, dan smart button Evidence.

Pembuatan atau perubahan Attendance oleh HR melalui UI native tetap mengikuti hak akses Odoo. Audit koreksi khusus dengan reason wajib dan snapshot before/after belum menjadi bagian baseline.

---

## 9. Time Off

### 9.1 Model dan konfigurasi

Time Off menggunakan:

- `hr.leave.type` untuk tipe.
- `hr.leave.allocation` untuk kuota.
- `hr.leave` untuk request.
- `resource.calendar` untuk hari/jam kerja.

Perhitungan durasi, validasi alokasi, kalender, dan work entries tetap ditangani oleh `hr_holidays`. Orkestrasi persetujuan request hanya menggunakan Presenly Approval Journey; approval native Time Off tidak menjadi jalur alternatif.

### 9.2 Integrasi Presenly

Presenly menambahkan:

- Work Location pada request.
- Approval Journey dan state Presenly.
- Snapshot seluruh level dan assigned approvers saat submission.
- Unified My Approvals queue untuk Permission dan Time Off.
- Pending approvers, approver history, rejection reason, activity, dan decision log.
- Guard server yang menolak bypass melalui approval/refusal native Time Off.
- Endpoint list, create, approval queue, approve, dan reject.

Work Location harus termasuk lokasi yang berlaku untuk Employee selama periode request. Final level Presenly memanggil engine validasi native Time Off; model `hr.leave` tetap menjadi sumber data final.

### 9.3 Aturan operasional

Sebelum Time Off dapat digunakan:

- Tipe Time Off harus aktif dan sesuai company/global policy.
- Allocation harus tersedia untuk tipe yang membutuhkan alokasi.
- Employee harus mempunyai Work Location yang berlaku selama periode request.
- Minimal satu Approval Level lengkap harus tersedia.
- Setiap assigned approver harus aktif, berada pada Allowed Company request, dan memiliki role Presenly Approver.

Pending Time Off dapat dibatalkan oleh owner/administrator dan journey ikut ditutup. Pembatalan Time Off yang sudah approved tetap memakai lifecycle pembatalan native Odoo dan status Presenly disinkronkan menjadi Cancelled.

---

## 10. Permission dan Dispensasi

### 10.1 Definisi

Permission/dispensation adalah request terkait kewajiban kehadiran yang tidak selalu merupakan Time Off dan tidak otomatis mengurangi saldo cuti. Contohnya:

- Datang terlambat dengan persetujuan.
- Pulang lebih awal.
- Izin sebagian jam.
- Izin sehari/rentang tanggal.
- Tugas atau keperluan tertentu sesuai kebijakan organisasi.

### 10.2 Permission Type

Setiap tipe mempunyai:

- Nama dan kode unik per Company.
- Allowed Duration: full day, partial hours, atau keduanya.
- Kewajiban attachment.
- Dampak terhadap attendance.
- Paid, unpaid, atau according to policy.
- Status aktif dan kelengkapan konfigurasi.

### 10.3 Request

Request menyimpan:

- Nomor referensi sequence.
- Employee, Company, dan Work Location.
- Permission Type.
- Mode durasi.
- Tanggal atau jam.
- Alasan.
- Attachment private.
- State dan approval level.
- Rejection reason.

Validasi submission mencakup:

- Field wajib.
- Tanggal dan jam yang valid.
- Mode sesuai Permission Type.
- Work Location berlaku pada periode request.
- Attachment tersedia bila diwajibkan.
- Tidak overlap dengan Permission submitted/approved lain milik Employee.
- Approval Level tersedia.

### 10.4 State

```text
draft -> submitted -> approved
draft -> submitted -> rejected
draft/submitted -> cancelled
```

Hanya draft yang dapat diedit. State tidak dapat diubah melalui write biasa; perubahan dilakukan melalui action workflow tervalidasi.

Approved Permission tersedia pada Attendance status, tetapi rekonsiliasi otomatis menjadi status harian terlambat/izin/sakit pada laporan attendance gabungan belum menjadi bagian baseline.

---

## 11. Approval Bertingkat

Approval Level dapat dikonfigurasi berdasarkan:

- Company.
- Work Location opsional.
- Permission Type atau Time Off Type.
- Sequence level.
- Approver type.

Approver type yang didukung:

- Specific User.
- Employee Manager.
- Work Location Manager.
- HR Officer.
- Odoo Group.

Aturan approval:

1. Presenly Approval Journey adalah satu-satunya jalur approval Permission dan Time Off.
2. Request tidak dapat disubmit jika flow tidak lengkap, ambigu, atau approver tidak valid.
3. Seluruh level dan assigned approvers disnapshot saat submission.
4. Hanya approver level aktif yang dapat memutuskan.
5. Approve memindahkan request ke level berikutnya.
6. Final approve menyelesaikan Permission atau memvalidasi Time Off melalui native Odoo.
7. Reject wajib memiliki alasan dan menghentikan workflow.
8. Setiap keputusan menyimpan level, approver, decision, note, dan timestamp.
9. Mail activity dibuat untuk approver aktif.
10. Unified My Approvals hanya menampilkan request pada level aktif user.
11. Direct write dan native Time Off approve/refuse/validate tidak dapat membypass journey.

Level location-specific menggantikan level company-wide dengan sequence yang sama. Delegasi approver, SLA, reminder, dan escalation otomatis belum tersedia. Extra Hours tetap menggunakan workflow native Attendances.

---

## 12. UI dan Navigasi

Presenly menggunakan aplikasi **Attendances** sebagai shell.

### 12.1 Employee

Form Employee mempunyai tab **Working Hours & Locations** untuk:

- Working Hours.
- Primary/Fallback Work Location.
- Status coverage.
- Gap dan conflict counters.
- Inline Location Slot editor.
- Open Working Hours.
- Generate from Working Hours.
- Open Full Schedule.

### 12.2 Attendances

Menu terintegrasi meliputi:

- **Overview:** My Permissions/Dispensations dan My Time Off.
- **Approvals:** My Approvals sebagai antrean terpadu Permission dan Time Off.
- **Reporting:** Attendance Evidence, Permissions, dan Time Off.
- **Configuration:** Companies, Work Locations, Work Location Schedules, Permission Types, dan Approval Levels.

Dashboard, kiosk, attendance list/form, dan reporting dasar tetap memakai fitur native Odoo.

---

## 13. Mobile API

> Referensi API mobile lengkap (attendance, WFA, Time Off, Permission, Overtime, approval): [`MOBILE_API_FULL.md`](custom_addons/presenly/docs/MOBILE_API_FULL.md)
> Roadmap penyempurnaan API approval: [`PLAN_APPROVAL_API.md`](custom_addons/presenly/docs/PLAN_APPROVAL_API.md)

### 13.1 Endpoint aktif

#### Attendance

```text
POST /api/presenly/v1/attendance/status
POST /api/presenly/v1/attendance/check-in
POST /api/presenly/v1/attendance/check-out
```

#### Time Off

```text
POST /api/presenly/v1/leave/types
POST /api/presenly/v1/leaves
GET  /api/presenly/v1/leaves
POST /api/presenly/v1/leaves/approval
POST /api/presenly/v1/leaves/{id}/approve
POST /api/presenly/v1/leaves/{id}/reject
```

#### Permission

```text
POST /api/presenly/v1/permissions/types
POST /api/presenly/v1/permissions
GET  /api/presenly/v1/permissions
POST /api/presenly/v1/permissions/approval
POST /api/presenly/v1/permissions/{id}/approve
POST /api/presenly/v1/permissions/{id}/reject
```

Semua route menggunakan `auth='user'` dan format JSON-RPC Odoo. Client harus memeriksa properti JSON-RPC `error` dan `result.success`, bukan hanya HTTP status.

### 13.2 Ketentuan client

- Production wajib menggunakan HTTPS.
- Session cookie diperlakukan sebagai secret.
- Password tidak disimpan dalam log atau dikirim ulang ke endpoint Presenly.
- Selfie dikirim sebagai base64 tanpa data-URL prefix.
- Client harus menangani session expired dengan kembali ke login.

Endpoint history lengkap, balance/quota, pagination, cancellation, unified approval, dan export belum tersedia sebagai API khusus Presenly.

---

## 14. Security dan Audit

### 14.1 Security aktif

- ACL berbasis Odoo groups.
- Record rules berdasarkan allowed companies.
- Employee dibatasi ke schedule, evidence, permission, dan log miliknya.
- Approver dibatasi ke request yang sedang/pernah ditugaskan.
- HR dan Administrator dibatasi oleh allowed companies.
- Selfie dan Permission attachment disimpan private.
- Workflow state dilindungi dari direct write.
- Failed attendance attempts tetap dicatat.
- Rejection reason wajib.
- Approval decision log menyimpan aktor dan waktu.

### 14.2 Batasan security baseline

- Permission attachment membatasi ukuran 10 MB dan memvalidasi base64, tetapi whitelist MIME/ekstensi belum ketat.
- Selfie memvalidasi base64 tetapi belum mempunyai limit ukuran eksplisit.
- Antivirus/file scanning belum tersedia.
- Device ID hash field tersedia tetapi belum dipopulasikan oleh controller.
- Retention dan purge policy untuk GPS, selfie, evidence, dan dokumen belum diotomatisasi.
- Audit login khusus Presenly tidak dibuat; gunakan audit/log Odoo dan deployment.

---

## 15. Non-Functional Requirements Baseline

### 15.1 Integritas data

- Attendance resmi harus selalu menggunakan `hr.attendance`.
- Time Off resmi harus selalu menggunakan `hr.leave`.
- Tidak boleh ada dua sesi attendance terbuka untuk Employee yang sama.
- Slot lokasi tidak boleh overlap.
- Company Employee, Work Location, schedule, dan request harus konsisten.
- Attendance menyimpan snapshot konteks saat check-in agar histori tidak berubah ketika konfigurasi Employee berubah.

### 15.2 Upgrade safety

- Core `addons/hr_attendance`, `addons/hr`, dan `addons/hr_holidays` tidak dimodifikasi.
- Integrasi dilakukan melalui `_inherit`, inherited views, controller, data, dan migration dalam addon Presenly.
- Cleanup schema legacy harus guarded dan idempotent.

### 15.3 Performa

Baseline sesuai untuk transaksi operasional normal Odoo. API list saat ini dibatasi maksimum 100 record. Pagination parameter, background export, dan benchmark volume besar masih backlog.

### 15.4 Reliability

- Waktu server Odoo menjadi timestamp transaksi utama.
- Failed attempt dicatat menggunakan cursor terpisah.
- Constraint database dan validasi server digunakan untuk schedule dan workflow.
- Kegagalan aktivitas/notifikasi tidak boleh dijadikan pengganti validasi hak approval.

---

## 16. Acceptance Criteria Baseline

### 16.1 Organization dan schedule

- [x] Company menggunakan `res.company`.
- [x] Sekolah/cabang menggunakan `hr.work.location`.
- [x] Working Hours native menjadi sumber periode kerja.
- [x] Satu Employee dapat mempunyai beberapa lokasi dalam satu hari melalui slot non-overlap.
- [x] Weekly, Specific Date, validity period, dan two-week calendar didukung.
- [x] Gap/conflict schedule terlihat pada Employee.
- [x] Slot dapat dihasilkan dari Working Hours.

### 16.2 Attendance

- [x] Check-in/out menghasilkan satu sumber data pada `hr.attendance`.
- [x] Check-in di luar geofence ditolak.
- [x] Akurasi GPS divalidasi.
- [x] Check-in ganda/sesi simultan ditolak.
- [x] Check-out harus menggunakan Work Location yang sama.
- [x] Selfie dapat diwajibkan per lokasi.
- [x] Evidence berhasil dan gagal tersimpan.
- [x] Company, Work Location, dan Schedule disnapshot.
- [ ] Status tepat waktu/telat dan `late_minutes` custom tersedia.
- [ ] Koreksi Attendance mewajibkan alasan dan menyimpan before/after snapshot.

### 16.3 Time Off

- [x] Menggunakan tipe, allocation, request, dan perhitungan native Odoo.
- [x] Work Location dan approval bertingkat terintegrasi.
- [x] Approve/reject menyimpan aktor, waktu, level, dan alasan reject.
- [ ] API balance/quota khusus mobile tersedia.
- [ ] Cancellation request custom untuk leave approved tersedia.

### 16.4 Permission

- [x] Full-day dan partial-hours tersedia.
- [x] Tipe dapat menentukan attachment, attendance impact, dan paid policy.
- [x] Overlap request divalidasi.
- [x] Approval bertingkat dan alasan reject tersedia.
- [x] Attachment disimpan private dan dibatasi 10 MB.
- [ ] Approved Permission direkonsiliasi otomatis menjadi status harian pada laporan gabungan.

### 16.5 Security/API

- [x] Odoo session authentication digunakan.
- [x] Record rules multi-company dan own-record tersedia.
- [x] API Attendance, Time Off, dan Permission tersedia.
- [x] Dokumentasi login/cookie/logout tersedia.
- [ ] Pagination, idempotency key, rate limiting, dan OpenAPI tersedia.
- [ ] MIME whitelist, selfie size limit, malware scan, dan retention cron tersedia.

---

## 17. Kesiapan Operasional Database Aktif

Status berikut adalah hasil audit konfigurasi pada tanggal baseline dan dapat berubah setelah administrator melengkapi master data:

- Modul Presenly `19.0.7.0.0` terpasang dengan single-path Approval Journey.
- Working Hours tersedia pada Employee aktif.
- Belum ada Work Location Schedule aktif.
- Belum ada Approval Level aktif.
- Belum ada Attendance, Time Off, Allocation, Permission, Evidence, atau Approval Log untuk UAT transaksi.
- Work Location yang ada belum berstatus Geofence Ready.
- Koordinat Work Location PT KONSULTA SEMEN GRESIK perlu diperbaiki ke format latitude/longitude yang valid.
- Feri dan Yusril belum mempunyai Related User aktif.
- Feri dan Maulana belum mempunyai Primary Work Location.
- Permission Type baru tersedia untuk YourCompany, belum untuk PT KONSULTA SEMEN GRESIK.
- User Maulana hanya mempunyai Allowed Company YourCompany.

Konsekuensinya, kelulusan automated test menunjukkan kode dapat bekerja pada fixture terisolasi, tetapi business UAT database aktif belum dapat diselesaikan sebelum konfigurasi di atas dilengkapi.

---

## 18. Backlog dan Kekurangan

### P0 — Wajib sebelum UAT operasional

1. Perbaiki Work Address dan koordinat seluruh Work Location sampai Geofence Ready.
2. Tetapkan radius, accuracy limit, selfie policy, dan Location Manager.
3. Hubungkan Related User ke setiap Employee mobile.
4. Berikan role Presenly yang sesuai dan Allowed Companies yang benar.
5. Tetapkan Primary Work Location/fallback Employee.
6. Generate dan lengkapi Work Location Schedule sampai coverage sesuai kebutuhan.
7. Buat Permission Type per Company yang menggunakan fitur.
8. Buat Approval Level untuk Time Off dan Permission.
9. Buat Time Off Allocation sesuai kebijakan.
10. Jalankan UAT nyata check-in, check-out, Time Off, Permission, dan multilevel approval.

### P1 — Gap fungsional utama

1. Perhitungan status tepat waktu/telat dan `late_minutes` berdasarkan Working Hours dan grace period.
2. Attendance correction request atau manual correction dengan reason wajib serta before/after audit snapshot.
3. API attendance history dan ringkasan mingguan/bulanan.
4. API Time Off balance/quota.
5. API detail, submit, cancel, dan pagination yang konsisten untuk request.
6. Workflow cancellation request untuk Time Off approved jika dibutuhkan kebijakan.
7. Rekonsiliasi Attendance, approved Time Off, dan approved Permission menjadi daily attendance status tanpa merusak histori.
8. Filter/report gabungan berdasarkan Employee, Company, Work Location, tanggal, dan status.
9. Export laporan terkontrol.

### P2 — Hardening keamanan dan reliabilitas

1. MIME dan extension whitelist untuk Permission attachment.
2. Limit ukuran selfie dan validasi tipe gambar aktual.
3. Antivirus/malware scanning untuk attachment.
4. Populate dan validasi `device_id_hash` jika kebijakan anti-fraud membutuhkannya.
5. Idempotency key untuk request mobile yang diulang.
6. Rate limiting pada login dan endpoint mobile di reverse proxy/aplikasi.
7. Retention policy dan purge cron untuk GPS, selfie, failed evidence, dan dokumen.
8. Structured security/audit log dan observability dashboard.
9. Test race condition untuk check-in dan approval paralel.
10. Security review khusus akses dokumen medis/sensitif.

### P3 — Workflow dan user experience

1. Reminder check-out.
2. SLA approval, reminder, delegation, dan escalation.
3. In-app/email notification lifecycle yang lebih lengkap.
4. Unified mobile approval queue.
5. Dashboard KPI operasional setelah definisi KPI disepakati.
6. OpenAPI/contract testing untuk mobile.
7. Lokalisasi pesan API dan UI.

### Future scope — Memerlukan PRD terpisah

1. Request dan approval lembur.
2. Perhitungan durasi, jenis hari, multiplier, upah per jam, dan estimasi nilai lembur.
3. Snapshot parameter perhitungan lembur.
4. Attendance lembur terhubung ke request.
5. Project/site assignment dan project-based reporting.
6. Workflow medical khusus beserta kontrol akses dokumen medis.
7. Face matching/DeepFace dan kebijakan biometric consent.
8. Mobile offline sync.
9. Integrasi payroll.

---

## 19. Urutan Go-Live yang Direkomendasikan

1. Finalisasi Company dan Allowed Companies.
2. Finalisasi Employee, Related User, role, department, manager, dan Working Hours.
3. Finalisasi Work Location dan geofence.
4. Finalisasi Primary/Daily/Specific Date/slot location schedule.
5. Finalisasi Time Off Type dan Allocation.
6. Finalisasi Permission Type.
7. Finalisasi Approval Levels dan approver.
8. Jalankan API smoke test untuk setiap user mobile.
9. Jalankan UAT satu lokasi satu hari.
10. Jalankan UAT beberapa lokasi dalam satu hari.
11. Jalankan UAT geofence gagal, GPS tidak akurat, selfie hilang, dan duplicate session.
12. Jalankan UAT Time Off dan Permission sampai final approve/reject.
13. Review evidence, approval log, record rules, dan laporan.
14. Baru aktifkan untuk pengguna produksi secara bertahap.

---

## 20. Definition of Done

Sebuah fitur Presenly dianggap selesai apabila:

1. Menggunakan model native Odoo sebagai sumber data jika tersedia.
2. Tidak memodifikasi source core Odoo.
3. Memiliki server-side validation dan access control.
4. Bekerja pada multi-company sesuai Allowed Companies.
5. Mempunyai audit/evidence yang sesuai tingkat risikonya.
6. Mempunyai automated test untuk alur utama dan penolakan penting.
7. Dokumentasi admin/mobile diperbarui.
8. Lulus upgrade module, test terisolasi, dan smoke test yang relevan.
9. Master data operasional telah dikonfigurasi dan business UAT lulus.
