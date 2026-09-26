# PLAN — Dokumentasi Full Semua Fitur Presenly (satu file .md)

**Status:** Draft plan — menunggu persetujuan sebelum menulis dokumen final.
**Modul:** `custom_addons/presenly` 19.0.13.6.0 (Odoo 19)
**Tujuan:** Satu dokumen `.md` komprehensif yang merangkum **semua fitur** produk Presenly — dari konsep, konfigurasi, penggunaan UI, hingga API mobile — sebagai acuan single-source untuk admin, HR, approver, employee, dan developer mobile.

---

## 1. Tujuan & Karakter Dokumen

- **Satu file**: `custom_addons/presenly/docs/PRESENLY_FULL_GUIDE.md`
- **Bahasa**: Indonesia (konsisten dengan PRD & docs yang ada).
- **Audience**: 4 peran — Employee, Approver, HR/Admin, Developer Mobile.
- **Sumber data**: kode aktif modulo + dokumen existing (jangan langsung menyalin postcheck lama yang sudah obsolete).
- **Prinsip**: setiap bagian menyebut **di mana settingnya** dan **endpoint mana** (bila ada), agar mudah ditindaklanjuti.
- Memanfaatkan dokumen existing sebagai referensi silang (link), bukan menduplikasi panjang-lebar.

---

## 2. Inventaris Fitur (cek-silang akurasi sebelum ditulis)

| # | Fitur | File sumber utama | Status |
|---|---|---|---|
| 1 | Attendance mobile (check-in/out, GPS/geofence, selfie, device hash) | `controllers/attendance.py`, `presenly_attendance.py` | Aktif |
| 2 | Work From Anywhere (WFA) | `controllers/attendance.py` (`mode='wfa'`) | Aktif |
| 3 | Work Location & Work Location Schedule (weekly/date, 2-mingguan, gap/conflict) | `hr_employee.py`, `presenly_schedule.py` | Aktif |
| 4 | Auto-resolve Work Location (K1 tolak multi-lokasi, K2 slot pertama, K2b jam) | `hr_employee._presenly_resolve_period_location` | Aktif |
| 5 | Time Off native + approval Presenly single-path | `presenly_approval.py` (`HrLeavePresenly`), `presenly_leave_views.xml` | Aktif |
| 6 | Permission/dispensation (full_day/hours, attachment, overlap) | `presenly_permission.py` | Aktif |
| 7 | Overtime/Lembur (date + jam 24H, durasi server, bukti attendance, 1/hari) | `presenly_overtime.py`, `controllers/overtime.py` | Aktif |
| 8 | Approval Journey multilevel (rule/request/step/log, My Approvals) | `presenly_approval.py` | Aktif |
| 9 | Guard anti-bypass & read-only history | `presenly_attendance.py`, `presenly_approval.py` | Aktif |
| 10 | Native disable (kiosk, systray, native overtime ruleset, Extra Hours) | `native_attendance.py`, `_update_overtime`, views | Aktif |
| 11 | Mobile API (jalur approval & pengajuan) | `controllers/leave.py`, `permission.py`, `overtime.py` | Aktif |
| 12 | Multi-company & record rules | `security/presenly_rules.xml` | Aktif |

> Sebelum menulis final: verifikasi ulang `__manifest__.py` (depends, data, assets, test) + versi terakhir; jangan menulis fitur yang tidak ada di kode.

---

## 3. Struktur Dokumen yang Diusulkan

### Bagian A — Ringkasan Eksekutif (1 halaman)
- Apa itu Presenly, di mana berjalan (Attendances shell), sasaran (multi-company/multi-lokasi).
- Peta peran: Employee / Approver / HR / Administrator.
- Tabel cepat: request apa yang ada (Time Off, Permission, Overtime), status alur singkat.

### Bagian B — Arsitektur & Model Inti
- Tabel model → sumber data (seperti PRD §3.1): `hr.attendance`, `hr.leave`, `presenly.permission`, `presenly.overtime.request`, `presenly.approval.*`.
- Single-path Approval Journey: konsep snapshot level/approver, immutability, `presenly.approval.log`.
- Kebijakan auth: session cookie Odoo, prefix `/api/presenly/v1`, JSON-RPC.

### Bagian C — Setup & Konfigurasi (Admin)
1. **Company & Allowed Companies** (menu Settings → Users).
2. **Employee**: Related User, Working Hours, Primary Work Location, role Presenly.
3. **Work Location**: coords, geofence radius, accuracy limit, selfie policy, Location Manager.
4. **Work Location Schedule**: weekly/date slot, valid-from/to, 2-mingguan, generator dari Working Hours, status coverage/gap/conflict.
5. **Permission Type**: allowed duration, attachment, affects attendance, paid policy.
6. **Approval Routes**: cara membuat step (Order 10/20/30, approver source), scope company/location, **Overtime Route** (`is_overtime_route`), syarat is_complete.
7. **Time Off**: tipe + allocation (native), Work Location pada request.
8. **Uang makan**: **TIDAK ADA** (sudah di-revert). Tidak ditulis.

### Bagian D — Alur Request per User
Draft→Submit→Level-by-level→Final. Tabel per tipe request:
| Request | Field utama | Bukti wajib | Aturan khusus |
|---|---|---|---|
| Time Off | work_location, date_from/to | lokasi terjadwal | final → native `validate` |
| Permission | mode full_day/hours, reason, attachment | lokasi terjadwal | overlap dicek |
| Overtime | date, hour_from/to (24H) | attendance hari itu | 1/hari; self-only |

### Bagian E — UI Web (menu per peran)
- Menu tree aktual (Overview → My Time Off/My Permissions/My Overtime; Approvals → Overtime Approvals; Reporting; Configuration).
- Yang **didisable**: Kiosk, systray, native Overtime Rulesets, tombol Approve/Refuse Extra Hours, blok settings "Extra Hours", field ruleset employee.

### Bagian F — Mobile API (referensi cepat + tautan)
- Tabel endpoint per modul (attendance, timeoff, permission, overtime) — singkat, link detail ke `MOBILE_*.md`.
- Format JSON-RPC + error handling umum (ringkas).
- Yang **tidak ada**: meal-allowance (revert), cancel Time Off API (belum), balance (backlog).

### Bagian G — Keamanan & Audit
- Record rules multi-company, own-record, approver scope.
- Guard anti-bypass: `_action_validate` guard, write protection, native approve/refuse di-block.
- Approval log, evidence, failed-attempt attendance.

### Bagian H — Troublehooting & Batasan
- Error umum: "tidak ada bukti attendance", "multi-lokasi", "route belum lengkap", "bukan approver".
- Backlog/limitation: tidak ada payroll, offline, cancellable Time Off via API, dsb (mirip PRD §18, ringkas).

### Lampiran
- Daftar dokumen terkait (link ke seluruh `docs/MOBILE_*.md`, `PLAN_*.md`, PRD).
- Glosarium singkat (Work Location, Schedule, Journey, dst).

---

## 4. Sumber Data per Bagian (agar akurat & tidak bloat)

| Bagian | Sumber utama | Strategi |
|---|---|---|
| A–B | `presenly-prd.md` (ringkas), `models/*.py` | Rangkum, bukan salin |
| C | `presenly_schedule_views.xml`, `presenly_location_views.xml`, settings | Tulis langkah menu + field penting |
| D | `test_api_*.py`, `presenly_leave_views.xml`, `presenly_overtime_views.xml` | Skema alur per tipe |
| E | `presenly_menus.xml`, `hr_attendance_integration_views.xml` | Tree menu + apa yang di-hide |
| F | `controllers/*.py` + `docs/MOBILE_*.md` | Tabel endpoint + link, tidak duplikasi detail |
| G | `security/*.xml`, `models/presenly_approval.py` | Paragraf ringkas |
| H | PRD §18 + experience debugging | Tabel error/backlog |

---

## 5. Definition of Done (DoD)

1. Satu file `docs/PRESENLY_FULL_GUIDE.md`.
2. Semua fitur aktif di kode tercakup; tidak ada fitur yang di-claim tapi tidak ada.
3. Tidak menyebut **uang makan** sebagai fitur (sudah revert).
4. Setiap peran (employee/approver/hr/admin/mobile) menemukan bagiannya.
5. Link ke dokumen detail (`MOBILE_*.md`, `PLAN_*.md`) benar dan valid.
6. Panjang terkendali (target ~350–500 baris + tabel); info detail cukup dirujuk, tidak diduplikasi.
7. Update index: tambahkan `PRESENLY_FULL_GUIDE.md` ke `docs/README` (atau `MOBILE_API.md` referensi induk) bila ada.
8. Tidak perlu upgrade module (dokumen murni) — verifikasi hanya dengan baca file.

---

## 6. Urutan Pengerjaan (bila disetujui)

1. **Fase 0**: Review inventaris (Baca `__manifest__.py`, daftar `docs/`, pastikan versi & status fitur).
2. **Fase 1**: Tulis Bagian A–B (eksekutif + arsitektur).
3. **Fase 2**: Tulis Bagian C–E (setup admin + alur request + UI menu).
4. **Fase 3**: Tulis Bagian F–H (mobile ringkas + security + troubleshooting) + lampiran.
5. **Fase 4**: DOI — cek link valid, cek tidak-blank, cek konsisten dgn kode; update index.

---

## 7. Pertanyaan Sebelum Eksekusi

1. **Lokasi & nama file**: `docs/PRESENLY_FULL_GUIDE.md` — oke?
2. **Bahasa**: full Bahasa Indonesia (judul bisa tetap Inggris untuk brand) — oke?
3. **Kedalaman**: ringkas-dengan-link (rekomendasi) vs benar-benar semua detail di satu file (file jadi sangat panjang)? Rekomendasi: ringkas + link.
4. **API mobile**: cukup tabel + link ke `MOBILE_*.md`, atau mau contoh JSON juga di file ini (duplikat)?
5. **Perlu update index** (`MOBILE_API.md` / README docs) untuk menautkan file baru ini?