# UI/UX Implementation Plan — Presenly Odoo 19

**Status:** Implemented; historical sections below retain the original planning context.  

> **Update 2026-09-05:** Working Hours native Odoo dan Work Location Schedule Presenly sekarang terintegrasi pada tab Employee **Working Hours & Locations**. UI menyediakan status coverage/gap/conflict, editor inline, generator preview dari Working Hours, split beberapa sekolah, kalender dua-mingguan, dan validasi slot terhadap jam kerja. Detail operasional: [`WORKING_HOURS_LOCATION_INTEGRATION.md`](WORKING_HOURS_LOCATION_INTEGRATION.md).
>
> **Update single-path approval:** Permission dan Time Off sekarang memakai satu Presenly Approval Journey. Menu final adalah **Attendances > Approvals > My Approvals**. Form request menampilkan progress, current approvers, dan snapshot setiap level. Tombol approval native Time Off disembunyikan dan method server native dijaga agar tidak dapat membypass journey.
**Acuan utama:** UI native Odoo 19, khususnya `hr_holidays`, `hr_attendance`, mail activity, chatter, search/list/calendar/form views  
**Prinsip:** Utamakan komponen native Odoo; hindari custom JavaScript/OWL dan CSS selama kebutuhan dapat dipenuhi oleh standard view/widget.

## 1. Tujuan

1. Membuat pengajuan izin/dispensasi terasa konsisten dengan pengajuan cuti Odoo.
2. Memisahkan pengalaman Employee, Approver, HR, dan Administrator.
3. Menampilkan aksi hanya ketika user memiliki hak dan record berada pada state yang benar.
4. Menyediakan navigasi, filter, grouping, calendar, activity, dan chatter sesuai behavior Odoo.
5. Menjaga UI responsif tanpa membuat frontend custom yang sulit dipelihara.

## 2. Masalah UI Saat Ini

- Form dispensasi hanya menggunakan satu `<group>` panjang.
- Tombol Approve/Reject muncul berdasarkan state saja, belum berdasarkan kewenangan approver.
- Employee dapat melihat affordance approval yang seharusnya tidak tersedia.
- Belum ada search view, filter My Requests, Pending, Approved, Rejected, unit, dan periode.
- Belum ada calendar view untuk pengajuan dispensasi.
- Belum ada tampilan khusus antrean approval.
- Belum ada ribbon Approved/Rejected/Cancelled.
- Chatter dan timeline activity belum tampil pada form dispensasi.
- Pemilihan tanggal dan jam belum mengikuti pola full-day/partial-hours seperti Time Off.
- Konfigurasi Unit, Location, Permission Type, dan Approval Level masih berupa form/list minimal.
- Attendance Evidence belum memiliki search/filter dan visual status yang memadai.

## 3. Information Architecture dan Menu

Menu target:

```text
Attendances
├── Overview
│   ├── My Permissions / Dispensations
│   └── My Time Off
├── Approvals
│   └── My Approvals
├── Reporting
│   ├── Attendance Evidence
│   ├── Permissions / Dispensations
│   └── Time Off
└── Configuration
    ├── Units
    ├── Work Locations
    ├── Employee Assignments
    ├── Permission Types
    └── Approval Levels
```

Aturan menu:

- Employee hanya melihat data miliknya.
- Approver melihat menu approval dan record pada level aktif yang menjadi kewenangannya.
- HR melihat reporting dan data dalam company/unit yang diizinkan.
- Administrator melihat seluruh configuration.
- Action employee menggunakan context/default dan domain, bukan menu yang membuka seluruh record.

## 4. Penerapan Per Fitur

### Fitur 1 — Fondasi behavior dan authorization UI

Sebelum mempercantik form, model harus menyediakan flag UI yang aman:

```text
can_submit
can_approve
can_reject
can_cancel
can_edit_request
is_request_owner
current_approver_ids
approval_progress_display
```

Behavior:

- Flag dihitung dari state, owner, rule aktif, company, unit, dan user.
- Tombol hanya tampil jika flag terkait bernilai benar.
- Method server tetap memvalidasi ulang hak akses; invisible button bukan security boundary.
- Record approved/rejected/cancelled menjadi readonly untuk field transaksi.
- Employee tidak dapat mengganti `employee_id` dari form My Requests.
- HR/Administrator menggunakan manager form yang mengizinkan pemilihan employee sesuai hak akses.

**Acceptance criteria:**

- Employee tidak melihat Approve/Reject.
- Approver yang tidak berada pada level aktif tidak melihat dan tidak dapat menjalankan approval.
- Approved/rejected request tidak dapat diedit langsung.
- Semua method tetap menolak pemanggilan RPC ilegal.

### Fitur 2 — Form pengajuan izin/dispensasi seperti Time Off

Form utama menggunakan struktur native:

```xml
<form duplicate="false">
  <header>buttons + statusbar</header>
  <sheet>
    ribbons
    employee/type/unit
    date range or partial hour
    reason
    attachment
    approval information
  </sheet>
  <chatter/>
</form>
```

Komponen:

- `employee_id` memakai `many2one_avatar_employee` pada manager form.
- `permission_type_id` berada di posisi utama seperti `holiday_status_id` pada cuti.
- `date_from` memakai `daterange` dengan `date_to` sebagai end date.
- Tambahkan mode durasi pada permission type/request:
  - Full day/range.
  - Partial hours.
- Untuk partial hours, gunakan `float_time` atau `float_time_selection` sesuai dukungan Odoo 19.
- `reason` menjadi text area utama dengan placeholder yang jelas.
- `attachment_ids` memakai `many2many_binary` dan hanya editable pada draft.
- Chatter menampilkan message, activity, attachment, dan perubahan state.
- Ribbon:
  - Approved: hijau.
  - Rejected: merah.
  - Cancelled: abu-abu/merah.
- Alert ditampilkan ketika tipe izin mewajibkan lampiran.
- Informasi approval menunjukkan level berjalan dan approver aktif tanpa membuka konfigurasi internal kepada employee.

Header behavior:

```text
Draft: Submit, Cancel
Submitted + active approver: Approve, Reject
Submitted + owner: Cancel (sesuai policy)
Approved: Cancel Request bila policy mengizinkan
Rejected/Cancelled: tidak ada aksi perubahan
```

**Acceptance criteria:**

- Pengajuan full-day dan partial-hours mudah dibedakan.
- Tanggal menggunakan daterange native.
- Attachment hanya editable pada draft.
- Alasan reject menggunakan modal wizard.
- Form menampilkan chatter dan activity.
- Layout nyaman pada desktop dan mobile web tanpa CSS khusus.

### Fitur 3 — List, search, filter, dan grouping dispensasi

Buat search view dengan:

- My Requests.
- To Approve.
- Draft.
- Submitted.
- Approved.
- Rejected.
- Cancelled.
- Today.
- This Month.
- Date range/search date.
- Employee, Permission Type, Unit, Company.

Group By:

- Status.
- Employee.
- Unit.
- Permission Type.
- Company.
- Month.

List view:

- Employee avatar pada manager/approval list.
- Tipe izin.
- Unit.
- Tanggal mulai/selesai.
- Jam parsial bila relevan.
- Approval level.
- Status dengan `badge` dan decorations:
  - Draft: muted.
  - Submitted: info/warning.
  - Approved: success.
  - Rejected: danger.
  - Cancelled: muted.
- Optional columns untuk company dan paid status.
- `multi_edit` tidak digunakan untuk transaksi approval.

Action:

- My Permissions: domain employee user saat ini.
- My Approvals: unified queue untuk Permission dan Time Off pada level aktif user.
- All Permissions: HR scope.

Queue lama Permission Approvals dan Time Off Approvals dipertahankan sebagai XML-ID kompatibilitas, tetapi menu-nya nonaktif.

**Acceptance criteria:**

- Default employee action hanya menampilkan miliknya.
- Approval action hanya menampilkan antrean relevan.
- Filter dan group dapat digunakan tanpa custom JS.

### Fitur 4 — Calendar dispensasi

Buat calendar view native:

```text
date_start = date_from
date_stop = date_to
color = permission_type_id
quick_create = false
event_open_popup = true
```

Calendar employee dan manager dapat menggunakan form/action context berbeda bila dibutuhkan.

Visual:

- Filter berdasarkan permission type dan employee.
- Rejected/cancelled tetap dapat dibedakan melalui state field dan decoration yang didukung.
- Klik event membuka form, bukan quick-create minimal.

**Acceptance criteria:**

- Pengajuan rentang hari tampil sebagai rentang calendar.
- Calendar menghormati record rules.
- Tidak ada quick create yang melewati validasi bisnis.

### Fitur 5 — Approval experience

Approval queue menggunakan list + activity behavior native.

Detail approval harus menampilkan:

- Employee dan avatar.
- Unit dan manager.
- Jenis izin.
- Tanggal/jam.
- Alasan.
- Lampiran.
- Level berjalan.
- Riwayat keputusan sebelumnya.

Smart button opsional:

```text
Approval History (count)
```

Implementasi riwayat:

- `presenly.approval.log` tetap immutable.
- Tambahkan action untuk membuka log terfilter berdasarkan model dan `res_id`.
- Employee hanya melihat riwayat pengajuannya.
- Approver/HR melihat sesuai scope.

Notifikasi/activity:

- Submit membuat activity untuk approver level aktif.
- Approve menyelesaikan activity user dan membuat activity level berikutnya.
- Reject menyelesaikan activity aktif.
- Final approval menyelesaikan seluruh pending activity terkait.

**Acceptance criteria:**

- Tidak ada activity approval lama yang tertinggal setelah pindah level.
- Approver dapat memproses record dari form dan list selection yang aman.
- Penolakan selalu memakai wizard alasan.

### Fitur 6 — UI cuti Presenly pada `hr.leave`

Jangan menduplikasi seluruh UI Time Off. Extend form native secara minimal:

- Unit Presenly ditempatkan dekat employee/type.
- Approval state dan level ditempatkan pada group teknis/approval.
- Tombol Presenly mengikuti `can_*` computed flag.
- Approval History smart button.
- Hindari menampilkan tombol native Odoo yang bertabrakan ketika workflow Presenly aktif.
- Untuk leave type tanpa workflow Presenly, behavior native Odoo tetap berjalan.

Tambahkan action approval cuti Presenly dengan filter active approver, tanpa mengganti dashboard Time Off bawaan.

**Acceptance criteria:**

- Cuti native tetap dapat digunakan.
- Tidak ada dua tombol approval aktif untuk workflow yang sama.
- Final approval Presenly menghasilkan state resmi `validate`.

### Fitur 7 — UI attendance dan evidence

Attendance employee:

- Gunakan menu/action bawaan `hr.attendance` sejauh mungkin.
- Tambahkan field Unit, Work Location, source, dan distance pada inherited view.
- Bukti selfie tidak ditampilkan sebagai URL publik.

Attendance Evidence:

- Form readonly.
- List dengan decoration success/danger.
- Search/filter:
  - Check-in/check-out.
  - Success/failed.
  - Today/this month.
  - Employee, unit, location.
- Group By employee, unit, location, status, event type, month.
- Smart button dari `hr.attendance` ke event terkait.
- GPS dapat menyediakan tombol/link Google Maps melalui computed URL/action, bukan HTML mentah.

**Acceptance criteria:**

- HR dapat menelusuri attendance ke bukti check-in/check-out.
- Employee tidak dapat membaca bukti employee lain.
- Event audit tidak dapat diedit dari UI.

### Fitur 8 — UI Unit dan Employee Assignment

Unit form:

- Title area dengan name/code.
- Header archive/unarchive menggunakan `active` behavior native.
- Manager dengan avatar user.
- Notebook:
  - General.
  - Work Locations.
  - Employee Assignments.
  - Approvers/Departments.
- Smart buttons:
  - Locations count.
  - Employees count.
  - Pending approvals count bila query tetap efisien.

Employee Assignment:

- Tambahkan list/form/search terpisah.
- Date range memakai daterange.
- `is_primary`, priority, status aktif.
- Filter Active, Expired, Upcoming, Unit, Employee.

**Acceptance criteria:**

- Admin dapat memahami unit dan assignment tanpa berpindah banyak layar.
- Multiple active assignments tetap didukung.
- Company/unit domain konsisten.

### Fitur 9 — UI Work Location/geofence

Form dibagi menjadi:

- Identity: name, unit, company, active.
- Coordinates: latitude, longitude.
- Geofence policy: radius, GPS accuracy.
- Attendance policy: selfie check-in/out.

Tambahkan:

- Help text untuk radius dan GPS accuracy.
- Button `Open in Maps`.
- Default radius 150 m terlihat jelas.
- Search/filter unit, company, active/archive.
- List menampilkan radius dan policy selfie secara opsional.

Custom map widget tidak dibuat pada tahap pertama. Bila kebutuhan map interaktif dikonfirmasi, implementasikan sebagai fitur terpisah agar tidak menambah JavaScript sebelum diperlukan.

### Fitur 10 — UI Permission Type

Form permission type mengikuti pola konfigurasi Time Off Type:

- Title/name.
- Code dan sequence.
- Request policy:
  - Full-day/partial-hours/both.
  - Attachment required.
  - Affects attendance.
  - Paid/unpaid/policy.
- Company.
- Archive/unarchive.
- Approval rule smart button atau inline relation terfilter.

List:

- Drag handle untuk sequence.
- Name/code.
- Request mode.
- Attachment required.
- Attendance impact.
- Paid status.
- Company.

### Fitur 11 — UI Approval Levels

List:

- Drag handle/sequence untuk urutan.
- Scope: company, Work Location, Time Off Type/Permission Type.
- Approver type dan target.
- Complete dan active.
- Semua level yang dikonfigurasi bersifat wajib.

Form behavior:

- `approver_user_id` hanya tampil untuk `approver_type = user`.
- `approver_group_id` hanya tampil untuk `approver_type = group`.
- Leave Type dan Permission Type bersifat mutual exclusive.
- Jelaskan bahwa level Work Location-specific menggantikan level company-wide dengan sequence sama.
- Domain company/location/type konsisten.
- Constraint mencegah satu rule mengarah ke Time Off dan Permission sekaligus.
- Sequence duplikat pada scope yang sama ditolak.
- Submission ditolak jika approver tidak aktif, tidak berada pada company request, atau belum memiliki role Presenly Approver.

**Acceptance criteria:**

- Admin dapat membaca urutan approval dari list tanpa membuka record.
- Field yang tidak relevan disembunyikan.
- Konfigurasi ambigu ditolak server-side.
- Approval Journey menyimpan snapshot level dan assigned approvers saat submission.
- Form Permission dan Time Off menampilkan Waiting/Pending/Approved/Rejected/Cancelled per level tanpa custom JavaScript.

### Fitur 12 — Reporting native

Tahap awal menggunakan view native:

- Pivot permission berdasarkan status/type/unit/employee/month.
- Graph pengajuan per bulan dan status.
- Calendar untuk jadwal izin.
- Pivot attendance evidence berdasarkan event/status/unit.

Tidak membuat dashboard OWL custom sebelum kebutuhan KPI final disepakati.

## 5. Urutan Implementasi

### Iterasi UI-1 — Security behavior dan dispensasi employee

1. Tambah computed `can_*` dan field durasi/mode request.
2. Refactor form dispensasi seperti Time Off.
3. Tambah chatter, ribbon, attachment behavior.
4. Tambah My Permissions action/menu.
5. Validasi employee tidak melihat approval actions.

### Iterasi UI-2 — Approval workflow UI

1. Approval queue action/menu.
2. Search/list manager view.
3. Wizard reject.
4. Approval history smart button/view.
5. Perbaikan lifecycle mail activities.

### Iterasi UI-3 — Calendar dan reporting dispensasi

1. Calendar view.
2. Pivot/graph.
3. Reporting menus.
4. Filter/grouping lengkap.

### Iterasi UI-4 — Cuti dan attendance

1. Rapikan inherited `hr.leave` view.
2. Cegah konflik tombol native/Presenly.
3. Inherit `hr.attendance` views.
4. Evidence search/read-only form/smart button.

### Iterasi UI-5 — Configuration UX

1. Unit + assignment notebook/actions.
2. Work location form/search/maps action.
3. Permission type policy form.
4. Approval level dynamic fields/constraints.
5. Menu dan action contexts final.

## 6. Validasi Per Iterasi

Setiap iterasi wajib menjalankan:

```bash
source /Users/ferisetyawan/Project/Website/odoo-19/odoo-venv/bin/activate
python -m compileall -q custom_addons/presenly
./odoo-bin -c odoo.conf -d odoo -u presenly --stop-after-init --no-http
```

Tambahan validasi:

- XML/view parsing tanpa error.
- Login sebagai Employee, Approver, HR, Administrator.
- Verifikasi menu/action/domain tiap role.
- Verifikasi button visibility dan server authorization.
- Verifikasi desktop dan viewport mobile web.
- Test workflow draft → submit → multilevel approve/reject/cancel.
- Test record rules multi-company dan multi-unit.

## 7. Definition of Done UI/UX

- UI dispensasi konsisten dengan Time Off Odoo.
- Tidak ada tombol approval yang terlihat untuk user tidak berwenang.
- Employee memiliki menu My Requests yang terfilter otomatis.
- Approver memiliki antrean terpusat.
- Form memakai widget native untuk avatar, date range, time, attachment, statusbar, ribbon, activity, dan chatter.
- List/search/calendar/pivot tersedia sesuai role.
- Konfigurasi unit, lokasi, tipe izin, dan approval mudah dipahami.
- Tidak ada custom JS/CSS kecuali kebutuhan yang tidak dapat diselesaikan dengan view native.
- Module dapat di-update tanpa warning/error view baru.
