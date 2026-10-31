# Migration Plan — Presenly sebagai Extension HR Attendances

> **Catatan arsitektur 2026-09-05:** bagian yang menyebut `presenly.unit`, `presenly.work.location`, `presenly.employee.assignment`, atau multi-unit adalah catatan historis. Arsitektur aktif memakai `res.company`, native `hr.work.location`, lokasi harian native Odoo, dan `presenly.work.location.schedule` untuk beberapa lokasi dalam satu hari. Permission dan Time Off kini memakai satu Presenly Approval Journey melalui **Attendances > Approvals > My Approvals**; antrean terpisah di bagian historis berikut bukan UI aktif. Lihat `README.md` dan `docs/MOBILE_API.md`.

**Target:** Odoo 19  
**Status:** Plan sebelum implementasi  
**Aplikasi utama:** Odoo Attendances (`hr_attendance`)  
**Addon teknis:** `presenly`  

## 1. Tujuan Migrasi

Mengubah Presenly dari aplikasi Odoo mandiri menjadi addon teknis yang memperluas aplikasi native **Attendances**.

Hasil akhir:

- Tidak ada app/root menu Presenly terpisah pada launcher Odoo.
- Pengguna masuk melalui aplikasi **Attendances**.
- Seluruh menu Presenly berada dalam hierarki menu Attendances.
- Absensi resmi tetap menggunakan `hr.attendance`.
- Cuti resmi tetap menggunakan `hr.leave` dan engine `hr_holidays`.
- Izin/dispensasi tetap menggunakan `presenly.permission` karena tidak identik dengan cuti.
- Geofence, selfie, multi-unit, API mobile, evidence, dan approval leveling tetap disediakan addon `presenly`.
- Source core `addons/hr_attendance` tidak dimodifikasi langsung.
- Upgrade Odoo tetap aman karena seluruh extension berada di `custom_addons/presenly`.

## 2. Keputusan Arsitektur

### 2.1 Yang dimaksud “migrasi ke HR Attendance”

Migrasi adalah perubahan kepemilikan UI dan navigasi, bukan memindahkan semua model ke satu tabel atau menyalin source ke addon core.

```text
Attendances App (UI shell)
├── Native hr.attendance
├── Presenly attendance metadata/evidence
├── Presenly units and geofence
├── Presenly permission/dispensation
├── Presenly approval queues
└── Shortcuts/integration to hr.leave
```

### 2.2 Presenly tetap addon terpisah

`presenly` tetap dibutuhkan untuk:

- Python model extensions.
- Controllers/API mobile.
- Security dan record rules.
- Views yang meng-inherit HR Attendance.
- Work unit/location/assignment.
- Attendance evidence.
- Permission/dispensation workflow.
- Multilevel approval.
- Integrasi DeepFace di masa depan.

Addon berubah menjadi technical extension:

```python
'application': False
```

Nama/summary dapat diperbarui menjadi:

```text
Presenly Attendance Tools
Attendance geofence, evidence, permissions and multilevel approvals
```

### 2.3 Tidak mengubah core Odoo

Dilarang memindahkan file Presenly ke:

```text
addons/hr_attendance/
```

Alasan:

- Perubahan dapat tertimpa saat upgrade Odoo.
- Sulit membedakan core dan customization.
- Uninstall/rollback menjadi berbahaya.
- Menambah risiko konflik dengan patch Odoo.

Semua integrasi dilakukan melalui:

- `_inherit` pada model.
- Inherited XML views.
- Menu dengan parent XML ID milik `hr_attendance`.
- Security implied groups.
- Action/window terpisah yang ditempatkan di Attendances.

## 3. Target Struktur Menu

```text
Attendances
├── Overview
│   ├── Dashboard                    [native]
│   ├── Employees                    [native]
│   ├── My Attendances               [native/extended]
│   └── My Permissions               [Presenly]
├── Management                       [native]
├── Approvals                        [Presenly]
│   └── My Approvals                 [Permission + Time Off]
├── Reporting                        [native]
│   ├── Attendances                  [native]
│   ├── Attendance Evidence          [Presenly]
│   ├── Permissions / Dispensations  [Presenly]
│   └── Time Off                     [shortcut/integration]
└── Configuration                    [native]
    ├── Settings                     [native]
    ├── Units                        [Presenly]
    ├── Work Locations               [Presenly]
    ├── Employee Assignments         [Presenly]
    ├── Permission Types             [Presenly]
    └── Approval Levels              [Presenly]
```

### 3.1 Parent menu native yang digunakan

| Kebutuhan | Parent native |
|---|---|
| Dashboard/employee shortcuts | `hr_attendance.menu_hr_attendance_overview` |
| Management | `hr_attendance.menu_hr_attendance_root` atau submenu baru |
| Reporting | `hr_attendance.menu_hr_attendance_reporting` |
| Configuration | `hr_attendance.menu_hr_attendance_configuration` |
| Root app | `hr_attendance.menu_hr_attendance_root` |

### 3.2 Menu baru yang perlu dibuat

- `menu_hr_attendance_presenly_approvals`
- `menu_hr_attendance_my_permissions`
- `menu_hr_attendance_permission_approvals`
- `menu_hr_attendance_leave_approvals`
- `menu_hr_attendance_evidence_reporting`
- `menu_hr_attendance_permission_reporting`
- Menu configuration Presenly dengan parent native.

### 3.3 Root menu Presenly lama

XML ID lama:

```text
presenly.menu_presenly_root
```

Tidak langsung dihapus pada migrasi pertama. Strategi aman:

1. Hilangkan groups/access sehingga tidak tampil, atau set `active=False` melalui data upgrade jika field tersedia.
2. Pindahkan child menu ke parent Attendances.
3. Pertahankan XML ID satu release agar bookmark/action lama tidak rusak mendadak.
4. Hapus record obsolete hanya setelah satu siklus stabilisasi.

## 4. Pemetaan Fitur

## 4.1 Native Attendance Dashboard

### Kondisi saat ini

Presenly memiliki data tambahan pada `hr.attendance`, tetapi belum sepenuhnya menyatu dengan dashboard/form native.

### Target

Extend view `hr.attendance` native dengan:

- Unit.
- Work location.
- Source.
- Check-in distance.
- Check-out distance.
- Evidence count smart button.
- Link ke Attendance Evidence.

Behavior:

- Dashboard native tidak diganti.
- Check-in/out native tetap tersedia sesuai policy company.
- Mobile Presenly menciptakan record pada `hr.attendance` yang sama.
- HR dapat membuka evidence dari attendance terkait.

### Acceptance criteria

- Satu record attendance menjadi sumber kebenaran.
- Tidak ada dashboard attendance Presenly terpisah.
- Attendance mobile dan native muncul di reporting yang sama.

## 4.2 Check-in/Check-out Mobile

### Tetap di addon Presenly

Controller:

```text
/api/presenly/v1/attendance/*
```

Tidak perlu dipindahkan ke core. Endpoint tetap kompatibel untuk mobile.

### Integrasi ke Attendances

- Output resmi tetap `hr.attendance`.
- Metadata evidence tetap `presenly.attendance.event`.
- Konfigurasi policy dapat ditampilkan pada Attendances > Configuration.
- Future enhancement: settings Presenly dapat di-inherit ke `res.config.settings` Attendances.

### Kompatibilitas API

Jangan mengganti route existing pada migrasi UI. Jika ingin route baru:

```text
/api/hr-attendance/v1/*
```

maka route lama harus tetap menjadi alias minimal satu versi mobile.

Rekomendasi: pertahankan `/api/presenly/v1` karena Presenly adalah nama kontrak integrasi, meskipun bukan aplikasi launcher.

## 4.3 Attendance Evidence

### Target menu

```text
Attendances > Reporting > Attendance Evidence
```

### Behavior

- List/search/form yang sudah dibuat tetap dipakai.
- Form menggunakan Edit, Save, dan Discard native.
- HR dapat koreksi field yang aman.
- Employee readonly.
- Evidence tidak dapat dibuat dari UI.
- Manual correction menghasilkan chatter audit.

### Integrasi tambahan

Tambahkan smart button pada `hr.attendance`:

```text
Evidence (2)
```

Domain:

```text
attendance_id = current attendance
```

## 4.4 Unit, Work Location, Assignment

### Target menu

```text
Attendances > Configuration
```

### Model tetap

- `presenly.unit`
- `presenly.work.location`
- `presenly.employee.assignment`

Tidak digabung ke `res.company`, `hr.department`, atau `hr.work.location` tanpa analisis migrasi terpisah.

### Integrasi employee

Extend form `hr.employee` dengan:

- Unit aktif.
- Assignment history smart button.
- Allowed work locations.

### Integrasi attendance

Hanya assignment dan location dengan:

```text
active = True
is_complete = True
```

yang boleh dipakai check-in/out.

## 4.5 Permission/Dispensation

### Target menu employee

```text
Attendances > Overview > My Permissions
```

### Target menu HR

```text
Attendances > Reporting > Permissions / Dispensations
```

### Model tetap

```text
presenly.permission
```

Alasan tidak dipindahkan ke `hr.attendance`:

- Permission adalah request/workflow, bukan sesi waktu hadir.
- Satu permission dapat berhubungan dengan tanggal atau jam tanpa attendance.
- Approval dan attachment memiliki lifecycle berbeda.
- Menggabungkannya ke `hr.attendance` merusak semantik data dan reporting.

### Integrasi

- Approved permission muncul pada attendance status/day summary.
- Attendance reporting dapat menampilkan indikator permission.
- Tidak mengubah histori `hr.attendance` secara destruktif.

## 4.6 Time Off/Cuti

### Model tetap native

```text
hr.leave
hr.leave.type
hr.leave.allocation
```

### Target UI

Cuti tidak diduplikasi menjadi model Presenly.

Dua opsi menu:

1. **Recommended:** Attendances menyediakan shortcut/action approval/reporting, sedangkan employee request tetap menggunakan aplikasi Time Off native.
2. Attendances menyediakan action `hr.leave` terfilter untuk request/approval tanpa mengganti view native.

### Approval Presenly

- Approval leveling tetap extension pada `hr.leave`.
- Final approval memanggil engine validasi `hr_holidays`.
- Tombol native dan Presenly tidak boleh aktif bersamaan untuk leave type yang memakai workflow Presenly.

### Catatan dependency

`presenly` tetap bergantung pada `hr_holidays`. Attendances app hanya menjadi entry point UI; ownership data tetap Time Off.

## 4.7 Multilevel Approval

### Target menu

```text
Attendances > Approvals
Attendances > Configuration > Approval Levels
```

### Approval queue

Gunakan satu action **My Approvals** berbasis snapshot `presenly.approval.request` dan `presenly.approval.step`. Detail request tetap dibuka pada form Permission atau native Time Off. Action lama Permission Approvals dan Time Off Approvals hanya dipertahankan sebagai compatibility XML IDs dengan menu nonaktif.

Domain UI hanya initial filter. Security final tetap pada method/server, assigned approver snapshot, dan record rules.

### Activity lifecycle

- Submit: create activity untuk current approver.
- Approve: close current activity, move level, create next activity.
- Reject: close activity dan simpan alasan.
- Final approve: close semua approval activity terkait.

## 4.8 Reporting

### Native attendance reporting

Extend pivot/search `hr.attendance` dengan optional dimensions:

- Unit.
- Work location.
- Source.
- Has approved permission.
- Evidence validation status, jika query efisien.

### Presenly reporting actions

Tetap model-specific tetapi ditempatkan di Attendances > Reporting:

- Attendance Evidence.
- Permission/Dispensation pivot/graph/calendar.
- Time Off shortcut.

Jangan membuat dashboard OWL custom sebelum KPI final tersedia.

## 4.9 Mobile API dan Dokumentasi

API tetap bagian addon Presenly karena `hr_attendance` core tidak seharusnya mengetahui kontrak aplikasi mobile custom.

Dokumentasi target:

- Nama produk: Presenly Mobile API.
- Backend app: Odoo Attendances.
- Technical provider: Presenly addon.
- Authentication tetap Odoo session.
- Endpoint backward compatible.

Update dokumen:

```text
docs/MOBILE_API_FULL.md (kanonik API mobile)
README.md
```

## 5. Mapping Security Groups

## 5.1 Kondisi saat ini

Presenly memiliki:

- `group_presenly_employee`
- `group_presenly_approver`
- `group_presenly_hr`
- `group_presenly_manager`

Attendances memiliki:

- `group_hr_attendance_own_reader`
- `group_hr_attendance_officer`
- `group_hr_attendance_user`
- `group_hr_attendance_manager`

## 5.2 Target mapping

| Presenly role | Native implied/target |
|---|---|
| Employee | internal user + attendance own reader |
| Approver | attendance officer, jika perlu akses attendance tim |
| HR Officer | attendance user/officer sesuai scope |
| Presenly Administrator | attendance manager |

## 5.3 Strategi aman

Jangan langsung menghapus Presenly groups. Gunakan sebagai feature permission dan map melalui `implied_ids`.

Contoh arah mapping:

```text
group_presenly_manager
  implies group_presenly_hr
  and/or requires hr_attendance.group_hr_attendance_manager
```

Perlu hati-hati terhadap privilege escalation. Group Presenly Approver tidak otomatis diberi akses semua attendance jika hanya perlu approval dispensasi.

Rekomendasi final:

- Native attendance groups menentukan akses attendance.
- Presenly groups menentukan fitur tambahan.
- Menu memakai kombinasi group native + Presenly sesuai kebutuhan.

## 6. Perubahan Manifest

Target `__manifest__.py`:

```python
{
    'name': 'Presenly Attendance Tools',
    'category': 'Human Resources/Attendances',
    'depends': ['hr', 'hr_attendance', 'hr_holidays', 'mail'],
    'application': False,
    'installable': True,
}
```

Data loading order yang disarankan:

```text
security groups
security access CSV
security record rules
data/sequences
wizard views
native inherited attendance views
time off inherited views
permission views
reporting views
configuration views
menus (terakhir)
```

## 7. Refactor File Views

Target struktur agar ownership jelas:

```text
views/
├── hr_attendance_views.xml          # inherit native attendance
├── hr_employee_views.xml            # unit/assignment smart buttons
├── hr_leave_views.xml               # Presenly approval extension
├── attendance_evidence_views.xml
├── permission_views.xml
├── permission_reporting_views.xml
├── presenly_unit_views.xml
├── presenly_location_views.xml
├── presenly_assignment_views.xml
├── presenly_approval_views.xml
└── hr_attendance_menus.xml          # all menus under native app
```

XML IDs lama dipertahankan bila memungkinkan agar upgrade database tidak menghasilkan duplicate action/view.

## 8. Strategi Migrasi Data

Migrasi UI tidak memerlukan pemindahan tabel.

### Data yang tetap di tempat

- `hr_attendance`
- `hr_leave`
- `presenly_attendance_event`
- `presenly_permission`
- `presenly.unit`
- `presenly.work.location`
- `presenly.employee.assignment`
- `presenly.approval.rule`
- `presenly.approval.log`

### Data migration yang mungkin diperlukan

- Menonaktifkan root menu lama.
- Membersihkan user-menu favorites/bookmarks bila diperlukan.
- Mapping group user Presenly ke visibility Attendances.
- Memastikan employee user yang membutuhkan menu memiliki group native yang tepat.
- Menandai konfigurasi incomplete agar tidak dipakai workflow.

### Tidak diperlukan

- Copy attendance.
- Copy leave.
- Rename database table.
- Recreate attachment.
- Regenerate evidence.

## 9. Rencana Implementasi Per Fase

## Fase M0 — Baseline dan backup

1. Dump database sebelum migration.
2. Catat module state/version.
3. Export daftar user dan groups.
4. Hitung record per model Presenly.
5. Simpan screenshot/menu matrix saat ini.
6. Jalankan seluruh smoke test existing.

Output:

- Baseline report.
- Database backup.
- Rollback point.

## Fase M1 — Ubah Presenly menjadi technical addon

1. Set `application=False`.
2. Ubah name/summary module.
3. Jangan hapus model/data.
4. Update README tentang ownership Attendances.
5. Pertahankan installability dan API.

Validation:

- Presenly tidak muncul sebagai app mandiri setelah Apps refresh.
- Module tetap terlihat jika filter Apps dinonaktifkan.
- Registry dan controllers tetap aktif.

## Fase M2 — Pindahkan menu configuration/reporting

1. Buat file menu integrasi Attendances.
2. Parent configuration ke `hr_attendance.menu_hr_attendance_configuration`.
3. Parent evidence/report ke `hr_attendance.menu_hr_attendance_reporting`.
4. Parent employee shortcut ke overview.
5. Buat submenu Approvals di root Attendances.
6. Pindahkan child menu menggunakan XML ID existing.
7. Sembunyikan root menu Presenly lama.

Validation:

- Tidak ada duplicate app/menu.
- Semua menu bisa dibuka sesuai group.
- Bookmark action lama tetap bekerja jika action ID dipertahankan.

## Fase M3 — Integrasi native `hr.attendance`

1. Inherit form/list/search native.
2. Tambah Unit, Location, Source, Distance.
3. Tambah smart button Evidence.
4. Tambah evidence count/action.
5. Extend reporting dimensions secara bertahap.
6. Pastikan native attendance correction tetap berjalan.

Validation:

- Existing attendance UI tidak rusak.
- Mobile attendance muncul di native list/report.
- Evidence terbuka dari attendance yang benar.

## Fase M4 — Integrasi employee dan configuration

1. Add assignment smart button pada employee.
2. Tampilkan unit aktif secara readonly/computed.
3. Tempatkan Units, Locations, Assignments di Attendance Configuration.
4. Finalisasi incomplete-record behavior.
5. Tambah settings bila policy perlu company-level defaults.

Validation:

- Multi-company domains benar.
- Multiple active unit assignments tetap didukung.
- Assignment incomplete tidak dipakai geofence.

## Fase M5 — Permission/Dispensation integration

1. Pindahkan My Permissions ke Attendance Overview.
2. Buat All Permissions/Reporting action untuk HR.
3. Buat Permission Approval queue.
4. Tambahkan pivot/graph/calendar jika sudah siap.
5. Integrasikan approved permission ke attendance day status.

Validation:

- Employee hanya melihat request sendiri.
- Approver hanya memproses current level.
- HR reporting berada di Attendances.

## Fase M6 — Time Off integration

1. Pertahankan native Time Off form/model.
2. Buat Attendance shortcut untuk approvals/report jika dibutuhkan.
3. Tambahkan smart links antara attendance day dan approved leave.
4. Selesaikan konflik tombol approval native/Presenly.
5. Jangan menduplikasi leave menu employee bila membingungkan.

Validation:

- Native allocations/balance tetap benar.
- Final approval menghasilkan `state=validate`.
- Tidak ada double approval button.

## Fase M7 — Security consolidation

1. Audit ACL tiap model.
2. Audit global/group record rules.
3. Map Presenly feature groups ke native Attendance roles.
4. Test Employee, Approver, HR, Manager, Admin.
5. Test multi-company dan multi-unit.
6. Hilangkan privilege yang tidak diperlukan.

Validation:

- Employee tidak membaca data employee lain.
- Approver tidak mendapat akses attendance global tanpa kebutuhan.
- HR hanya mengakses allowed companies.

## Fase M8 — API, tests, documentation

1. Pertahankan route existing.
2. Update docs bahwa Attendances adalah backend UI.
3. Tambah HTTP/controller tests.
4. Test session auth dan expired session.
5. Update endpoint examples jika response berubah.
6. Update module README dan admin guide.

## Status Eksekusi 2026-09-05

- **M0–M2 selesai**: backup, technical addon, dan pemindahan menu ke Attendances.
- **M3 selesai**: inherited form/list/search `hr.attendance`, metadata Presenly, dan smart button Evidence.
- **M4 selesai**: unit aktif dan smart button Assignment pada Employee native.
- **M5 selesai**: approval queue dinamis dan reporting Permission / Dispensation.
- **M6 selesai**: shortcut dan reporting Time Off native di Attendances.
- **M7 selesai**: ownership/company record rules, snapshot pending approver, approver history, dan smoke test role-based.
- **M8 selesai**: API route tetap kompatibel, dokumentasi diperbarui, constraint dimigrasikan ke `models.Constraint`, dan fresh-install suite lulus 10/10 termasuk valid/anonymous/destroyed session.
- **M9 ditunda** sampai satu release stabil; compatibility XML ID root lama tetap ada tetapi nonaktif.

Detail hasil tersimpan di `MIGRATION_BASELINE_20260905.txt` dan `MIGRATION_POSTCHECK_20260905.txt`.

## Fase M9 — Cleanup menu lama

Dilakukan setelah satu release stabil:

1. Hapus XML root menu Presenly obsolete.
2. Hapus compatibility alias yang tidak lagi dipakai.
3. Bersihkan action/menu orphan.
4. Naikkan module version.
5. Jalankan migration script idempotent.

## 10. Sequence Implementasi yang Direkomendasikan

Urutan paling aman:

```text
M0 Baseline
→ M1 Technical addon
→ M2 Menu migration
→ M3 Native attendance integration
→ M4 Employee/config integration
→ M5 Permission integration
→ M7 Security audit
→ M6 Time Off integration
→ M8 Tests/docs
→ Stabilization
→ M9 Cleanup
```

Security audit awal dilakukan sesudah menu permission, lalu diulang setelah Time Off integration.

## 11. Test Matrix

## 11.1 Module/update

```bash
source odoo-venv/bin/activate
python -m compileall -q custom_addons/presenly
./odoo-bin -c odoo.conf -d odoo -u presenly --stop-after-init --no-http
```

## 11.2 Role matrix

| Scenario | Employee | Approver | HR | Manager |
|---|---:|---:|---:|---:|
| Open Attendances app | sesuai access | Ya | Ya | Ya |
| Own attendance | Ya | Ya | Ya | Ya |
| All attendance | Tidak | sesuai scope | sesuai scope | Ya |
| My permissions | Ya | Ya | Ya | Ya |
| Approval queue | Tidak | current scope | Ya | Ya |
| Evidence edit | Tidak | Tidak/default | Ya | Ya |
| Configuration | Tidak | Tidak | sesuai policy | Ya |

## 11.3 Workflow tests

- Check-in within geofence.
- Check-in outside geofence.
- Check-out same location.
- Check-out different location.
- Evidence Save/Discard.
- Draft permission autosave.
- Multilevel approve/reject.
- Approved leave attendance status.
- Approved permission attendance status.
- Multiple active unit assignments.

## 11.4 Upgrade tests

- Install fresh database.
- Upgrade existing installed Presenly.
- Upgrade with existing menu favorites.
- Upgrade with incomplete config records.
- Uninstall/reinstall only on disposable database.

## 12. Risiko dan Mitigasi

| Risiko | Mitigasi |
|---|---|
| Attendances root tidak terlihat untuk employee | Jangan membuka seluruh app tanpa analisis; map group/menu secara spesifik atau gunakan native attendance reader role |
| Privilege escalation melalui implied groups | Pisahkan native attendance access dan Presenly feature access |
| Menu duplikat | Reparent XML ID existing, jangan create action/view duplicate |
| Bookmark lama rusak | Pertahankan action XML IDs dan compatibility period |
| Cuti membingungkan karena tampil di dua app | Gunakan shortcut approval/reporting saja; request utama tetap Time Off |
| Modifikasi core tertimpa upgrade | Semua perubahan melalui custom addon inheritance |
| API mobile rusak | Pertahankan route `/api/presenly/v1` dan response contract |
| Reporting lambat | Tambah related stored/indexed field hanya setelah profiling |
| Uninstall menghapus data custom | Backup; pertimbangkan uninstall policy/guard sebelum production |

## 13. Rollback Plan

Rollback per fase harus reversibel.

### Menu rollback

- Kembalikan parent menu ke root Presenly.
- Set `application=True` kembali.
- Update module.

### View rollback

- Nonaktifkan inherited view baru atau kembalikan arch sebelumnya.
- Tidak perlu memulihkan tabel karena data tidak dipindah.

### Group rollback

- Restore export group membership baseline.
- Hapus implied group baru jika menambah privilege.

### Full rollback

- Restore database dump M0.
- Checkout code sebelum migration.
- Restart Odoo dan clear assets/browser cache.

## 14. Definition of Done

Migrasi dianggap selesai jika:

- Presenly tidak muncul sebagai aplikasi launcher mandiri.
- Attendances menjadi satu-satunya entry point UI untuk fitur Presenly.
- Seluruh configuration/reporting/approval tersedia di hierarki Attendances.
- Native `hr.attendance` menjadi sumber kebenaran absensi.
- Native `hr.leave` tetap menjadi sumber kebenaran cuti.
- Permission tetap model request terpisah tetapi tampil di Attendances.
- Semua endpoint mobile tetap kompatibel.
- Tidak ada perubahan langsung pada source core `hr_attendance`.
- Role matrix dan multi-company tests lulus.
- Upgrade existing database lulus tanpa kehilangan data.
- Root menu lama dan compatibility layer dibersihkan setelah stabilisasi.
