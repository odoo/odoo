# Plan: Rapikan Menu Attendances + Akses HR Officer ke Time Off

> **Status:** Plan — belum implementasi.
> **Tujuan:**
> 1. Jelaskan & rapikan grouping menu (Dashboard / Management / Reporting / Time Off)
>    agar tidak dobel seperti native + Presenly.
> 2. Memberi **HR Officer** akses melihat & mengelola **semua** Time Off (plus
>    Permission/Overtime/Evidence yang sudah ada), sehingga "tidak ada data" hilang.

---

## 1. Kondisi Saat Ini (verified dari kode)

### 1.1 Pohon menu yang tampil sekarang

**Aplikasi Time Off native (`hr_holidays`) — masih UTUH & duplikat dgn Presenly**
```
Time Off (menu_hr_holidays_root, base.group_user)
├─ My Time          (menu_hr_holidays_my_leaves)
│  ├─ New Request
│  ├─ My (action hr_leave_action_my)
│  └─ My Allocations
├─ Overview         (action hr_holidays_dashboard)
├─ Management       (group_hr_holidays_responsible)
│  ├─ Time Off      (action hr_leave_action_action_approve_department = "All Time Off")
│  └─ Allocations
├─ Reporting        (group_hr_holidays_user)
│  ├─ by Employee   (action_hr_available_holidays_report)
│  ├─ by Type
│  └─ Balance       (manager)
└─ Configuration    (manager)
```
> Ada **dua** "Time Off": aplikasi native (menu Time Off) + bawaan pada
> Attendances. User biasa melihat keduanya → terasa tidak dikelompokkan.

**Aplikasi Attendances (`hr_attendance`) + Presenly**
```
Attendances (menu_hr_attendance_root → presenly.group_presenly_employee)
├─ [Overview] (menu_hr_attendance_overview → presenly employee)
│  ├─ Dashboard            (native; skrg group officer — fix kemarin)
│  ├─ Employees            (native; officer)
│  ├─ My Attendances       (Presenly; employee)
│  ├─ My Permissions/Disp  (Presenly; employee)
│  ├─ My Time Off          (Presenly → hr_leave_action_my; employee)
│  └─ My Overtime          (Presenly; employee)   ← ada di view overtime
├─ Approvals               (Presenly; approver; **active=False**)
├─ [Reporting] (menu_hr_attendance_reporting → presenly.group_presenly_hr)
│  ├─ Attendance Evidence  (Presenly; hr)
│  ├─ Permissions / Disp   (Presenly; hr)
│  ├─ Time Off             (Presenly → action_hr_available_holidays_report; hr)
│  └─ (native Attendances Reporting) (skrg gated officer — fix kemarin)
├─ Management (native; skrg gated officer — fix kemarin)
└─ [Configuration] (presenly manager)
   ├─ Companies / Work Locations / Work Location Schedules / Permission Types
   └─ (native Overtime Rulesets di-hide)
```

### 1.2 Gap akses HR → Time Off (akar "tidak ada data")

| Grup | implied (dari `presenly_groups.xml`) | Akses `hr.leave` |
|---|---|---|
| `presenly.group_presenly_hr` | `approver` + `hr_attendance.group_hr_attendance_user` | ❌ Hanya milik sendiri + leave_manager (rule `hr_leave_rule_user_read` butuh `group_hr_holidays_user`) |
| `presenly.group_presenly_manager` | `presenly_hr` + `hr.group_hr_user` | ❌ Sama (kecuali root/admin punya `group_hr_holidays_manager` via XML `user_ids`) |

**Rantai rule native** (dari `addons/hr_holidays/security/hr_holidays_security.xml`):
```xml
hr_leave_rule_user_read  → groups = hr_holidays.group_hr_holidays_user; domain (1,'=',1)  # FULL baca
hr_leave_rule_responsible_read → groups = group_hr_holidays_responsible; domain leave_manager_id = user  # terbatas
```
Tanpa `group_hr_holidays_user`, HR Officer TIDAK melihat semua cuti → menu Reporting > Time Off tampak kosong.

---

## 2. Keputusan Struktur Menu (target)

Prinsip: **satu pintu per fitur**, grouping per peran jelas, tidak dobel.

### 2.1 App "Attendances" = satu-satunya app operasional (per README Presenly)
- **Sembunyikan aplikasi "Time Off" native** untuk non-officer (`active=False` pada
  `menu_hr_holidays_root` di `presenly_menus.xml`) — employee memakai
  "My Time Off" di Overview (sudah ada), officer memakai menu HR (di bawah).
- App Time Off native tetap tampil **hanya untuk officer/manager** (group
  `hr_holidays.group_hr_holidays_user,group_hr_holidays_manager`) supaya akses
  Management/Reporting/Configuration dedupe & terkelompok — alternatif bila tidak
  mau sembunyikan total.

### 2.2 Pohon target (role-based)

```
Attendances
├─ Overview (employee+)
│  ├─ Dashboard               (officer+; native grouped overview)
│  ├─ My Attendances          (employee)
│  ├─ My Permissions/Disp     (employee)
│  ├─ My Time Off             (employee)
│  └─ My Overtime             (employee)
│
├─ [HUMAN RESOURCES]  (parent baru; officer+ [presenly_hr / hr_attendance_officer])
│  ├─ All Attendances        → hr_attendance_management_action (Management native; list semua)
│  ├─ Permissions / Disp     → action_presenly_permission_reporting (semua)
│  ├─ Overtime / Lembur      → action_presenly_overtime_reporting (semua)
│  ├─ Time Off               → hr_holidays.hr_leave_action_action_approve_department ("All Time Off")
│  └─ Attendance Evidence    → action_presenly_attendance_event
│
├─ [Reporting]  (officer+/hr)
│  ├─ Attendance Evidence    (Presenly; hr)
│  ├─ Permissions / Disp     (Presenly; hr)
│  ├─ Overtime               (Presenly; hr)  ← tambahkan bila belum
│  └─ Time Off by Employee   (native; hr)
│
├─ [Configuration] (manager)
└─ (Management native lama → ganti jadi di bawah "Human Resources")
```

> Catatan: `menu_hr_attendance_view_attendances_management` native (Management)
> tetap retain (officer) tapi kami **re-parent/re-nama** ke bawah "Human Resources"
> agar grouping jelas; alih-alih menghapus, kita pindahkan posisi/kelompok.

---

## 3. Rencana Perubahan (per file)

### 3.1 `security/presenly_groups.xml` — beri HR akses Time Off
Menambah implied `hr_holidays.group_hr_holidays_user` ke `group_presenly_hr`:

```xml
<record id="group_presenly_hr" model="res.groups">
    <field name="name">HR Officer</field>
    <field name="sequence">30</field>
    <field name="privilege_id" ref="presenly.res_groups_privilege_presenly"/>
    <field name="implied_ids" eval="[
        (4, ref('presenly.group_presenly_approver')),
        (4, ref('hr_attendance.group_hr_attendance_user')),
        (4, ref('hr_holidays.group_hr_holidays_user')),
    ]"/>
</record>
```

Efek:
- `group_hr_holidays_user` → implies `group_hr_holidays_responsible` + `hr.group_hr_user`.
- Record rule `hr_leave_rule_user_read` → HR bisa baca **semua** `hr.leave` (semua company/employee).
- Access to multi-request management (approve flow native bila relevan), reporting, dsb.

> Catatan keamanan: `group_hr_holidays_user` juga meng-implied `hr.group_hr_user`
> (akses officer HR ke employee). Ini wajar untuk HR Officer. Bila ingin lebih
> ketat (hanya baca cuti, tanpa mengelola allocation), opsi alternatif:
> `group_hr_holidays_responsible` saja — tapi itu **terbatas** ke leave_manager,
> tidak semua. Untuk "melihat semua request", wajib `group_hr_holidays_user`.

### 3.2 `views/presenly_menus.xml` — rapikan grouping

1. **Sembunyikan app Time Off native untuk non-officer** (hindari dobel):
```xml
<record id="hr_holidays.menu_hr_holidays_root" model="ir.ui.menu">
    <field name="active" eval="False"/>
</record>
```
   atau (lebih aman) ganti group → officer:
```xml
<record id="hr_holidays.menu_hr_holidays_root" model="ir.ui.menu">
    <field name="groups_id" eval="[(6,0,[
        ref('hr_holidays.group_hr_holidays_user'),
        ref('hr_holidays.group_hr_holidays_manager')])]"/>
</record>
```

2. **Parent baru "Human Resources"** (id `menu_presenly_hr`) di bawah root
   (`menu_hr_attendance_root`), `groups="presenly.group_presenly_hr` (+ officer)".
   Pindahkan:
   - Management native → `menu_presenly_hr_management` (re-parent ke parent ini)
   - Permissions / Disp (reporting action) → di sini
   - Overtime (reporting) → di sini
   - Time Off (All) → `hr_leave_action_action_approve_department`
   - Attendance Evidence → di sini

3. **Reporting** tetap untuk hr (sudah), tapi hapus duplikasi Time Off native
   bila app Time Off di-hide (§3.2.1). Tambahkan **Overtime** ke Reporting bila
   belum (sudah ada `menu_presenly_overtime_reporting` — pastikan tetap).

4. Hapus/arsipkan duplikat "My Approvals" disabled (boleh dibiarkan `active=False`,
   cuma housekeeping).

### 3.3 (Opsional) Action "All Time Off" untuk HR
- `hr_holidays.hr_leave_action_action_approve_department` tidak punya `group_ids`
  sendiri (default via menu). Dengan `group_hr_holidays_user` implied, HR bisa
  membukanya dari parent HR.
- Konteks-nya `search_default_waiting_for_me` — cocok untuk antrean approver HR;
  untuk list semua, boleh buat action Presenly baru yang hanya set default filter:
```python
# di server action / XML action baru (opsional)
action = self.env.ref('hr_holidays.hr_leave_action_action_approve_department').sudo().read()[0]
action['domain'] = [('employee_id.company_id', 'in', allowed_company_ids)]
```
  Atau cukup pakai native (tanpa perubahan) karena rule user_read sudah memberi
  semua.

---

## 4. Matriks Akses Peran (target setelah plan)

| Data | Employee | Approver | HR Officer | Administrator |
|---|---|---|---|---|
| Attendance (sendiri) | ✅ My Attendances | ✅ | ✅ | ✅ |
| Attendance (semua) | ❌ | ❌ | ✅ via HR > All Attendances | ✅ |
| Attendance Evidence | ✅ milik sendiri | ✅ milik sendiri | ✅ semua | ✅ |
| Permission (sendiri) | ✅ | – | ✅ | ✅ |
| Permission (semua) | ❌ owner | pending/history miliknya | ✅ | ✅ |
| Time Off (sendiri) | ✅ My Time Off | ✅ | ✅ | ✅ |
| **Time Off (semua)** | ❌ | pending/history miliknya | ✅ **baru** (group_hr_holidays_user) | ✅ |
| Overtime (sendiri) | ✅ My Overtime | pending/history | ✅ semua | ✅ |
| Overtime (semua) | ❌ | pending | ✅ | ✅ |
| Konfigurasi | ❌ | ❌ | ❌ (read-only) | ✅ |

---

## 5. Test Plan

1. **Implied group:** user dgn `presenly.group_presenly_hr` →
   `has_group('hr_holidays.group_hr_holidays_user')` True;
   `hr_leave_rule_user_read` memungkinkan baca `hr.leave` milik employee lain.
2. **Lihat semua cuti:** buat 2 hr.leave (employee A, B). Login HR →
   search `hr.leave` (domain semua company) → muncul 2 record (sebelumnya 0).
3. **Menu grouping:** `menu_hr_holidays_root` non-officer hidden (atau group
   officer); parent `menu_presenly_hr` tampil utk HR; employee tidak melihatnya.
   Tidak ada duplikasi Time Off di kedua app utk employee.
4. **Reporting Time Off:** action native `action_hr_available_holidays_report`
   utk HR menampilkan data (bukan kosong).
5. **Regresi:** suite `/presenly,/presenly_payroll` hijau (kecuali pre-existing
   `test_api_overtime` rule leftover).
6. **Security:** employee tetap TIDAK bisa akses menu/hr_leave milik orang lain
   (rule native masih berlaku utk non-holidays-user).

---

## 6. Checklist Pengerjaan

- [ ] 1. `security/presenly_groups.xml`: tambah implied
      `hr_holidays.group_hr_holidays_user` ke `group_presenly_hr`.
- [ ] 2. `views/presenly_menus.xml`:
      - (opsi) hide/gate `menu_hr_holidays_root`.
      - Tambah parent `menu_presenly_hr` (group hr) + re-parent Management,
        Permissions, Overtime, Time Off (All), Evidence.
      - Pastikan Reporting (hr) tidak duplikat.
- [ ] 3. (Opsional) action "All Time Off" utk HR bila native dirasa kurang.
- [ ] 4. Test baru `tests/test_hr_timeoff_access.py` (implied + baca semua cuti).
- [ ] 5. Bump versi `presenly` (contoh `19.0.14.1.0`).
- [ ] 6. Validasi: `-u presenly --test-tags /presenly` + riwayat DB tetap.

---

## 7. Catatan / Risiko

- **Menambah `group_hr_holidays_user`** memberi HR akses *manage* cuti (bukan cuma
  baca): bisa approve/refuse semua (via native bila di-enable) + implied
  `hr.group_hr_user`. Untuk Presenly, approval jalan tetap lewat
  Presenly Approval Journey (native `action_approve` di-block oleh
  `HrLeavePresenly`), jadi turunannya aman; tapi allocation/type/accrual tetap
  bisa dilihat HR bila menu di Manager — timbalkan mana yang perlu.
- Bila hanya ingin **baca saja** (read-only time off untuk HR) tanpa implied
  `hr.group_hr_user` berat, opsi: buat rule Presenly khusus `hr.leave` read-all
  utk `group_presenly_hr` (tanpa group_hr_holidays_user) — drop-in read-only.
  Rekomendasi: pakai `group_hr_holidays_user` (paling sederhana & konsisten),
  kecuali HR/legal menghendaki read-only ketat.
- Menu "Management" native & "Dashboard" tetap ada (officer) — tidak dihapus,
  hanya dikelompokkan ulang di bawah "Human Resources".

---

## 8. Keputusan yang Perlu Konfirmasi

1. HR Officer: full manage (implied `group_hr_holidays_user`) **atau** read-only
   time off via rule khusus? → rekomendasi full manage.
2. App "Time Off" native: **sembunyikan total** utk non-officer, atau **tetap
   tampil utk officer** (sebagai grup terpisah)? → rekomendasi tampil utk officer.
3. Apakah tambah parent "Human Resources" (baru) atau cukup pakai Reporting
   (lama) + Management native yang digabung? → rekomendasi parent baru agar
   jelas.