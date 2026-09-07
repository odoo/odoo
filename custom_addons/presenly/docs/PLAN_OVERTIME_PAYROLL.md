# Plan: Integrasi Overtime Presenly → Payroll (hr_payroll_custom)

> **Status:** Investigasi selesai — belum implementasi.
> **Lingkup:** Modul `presenly` (request lembur) dengan `hr_payroll_custom`
> (Custom Payroll — `custom.payroll.slip`).
> **Masalah:** Hasil lembur yang disetujui di Presenly **tidak masuk** ke payroll
> `custom.payroll.slip` sama sekali; payroll menghitung lembur dari sumber lain.

---

## 1. Temuan Investigasi — Lembur Sumber-Demi-Sumber

Ada **tiga mekanisme lembur** dalam sistem, dan ketiganya **tidak saling terhubung**:

### 1.1 `presenly.overtime.request` (Lembur Presenly) — AKTIF
- Model: `presenly.overtime.request` (`custom_addons/presenly/models/presenly_overtime.py`)
- Field: `date`, `hour_from`, `hour_to` (jam 24H), `duration_hours` (float,
  server-side), `reason`, `work_location_id`, `has_attendance_evidence`,
  `state` (draft → submitted → approved / rejected / cancelled).
- Approval via **Presenly Approval Journey** (`presenly.approval.rule`
  `is_overtime_route` = True).
- Syarat submit: wajib ada `hr.attendance` pada tanggal itu (hanya cek "ada
  attendance", bukan cek jam lembur tercakup), maksimal 1 request/hari,
  route approval lengkap, lokasi terjadwal.
- **Uang makan TIDAK ada** (fitur meal allowance sudah di-revert —
  `docs/MOBILE_API_FULL.md` §8.1).
- ✅ **Tidak ada referensi payroll mana pun**: tidak ada `hr.payslip`,
  `custom.payroll.slip`, `contract_wage`, rate, ataupun amount. **Lembur yang
  disetujui berhenti di status `approved` saja.**

### 1.2 Native Overtime `hr.attendance.overtime.line` (Extra Hours Odoo) — NONAKTIF
- `presenly/models/presenly_attendance.py`:
  - `_update_overtime(...)` di-override → `return True` (native engine yang
    menurunkan `hr.attendance.overtime.line` dari check-in/out **dimatikan**).
  - `action_approve_overtime` / `action_refuse_overtime` → `raise ValidationError`
    (approval Extra Hours native **dilarang**; "Overtime is managed by Presenly
    Overtime requests").
  - View menyembunyikan kolom overtime & tombol approve/refuse native.
- Kesimpulan: native extra-hours **tidak dipakai dan tidak bisa dipakai** untuk
  jalur baru (sudah sengaja dimatikan oleh desain Presenly).

### 1.3 `custom.payroll.slip` (Payroll Kustom) — HITUNG SENDIRI, SALAH SUMBER
- `custom_addons/hr_payroll_custom/models/custom_payroll_slip.py`:
  - `attendance_overtime_hours` (compute, store): sum `(worked_hours -
    overtime_threshold_hours)` per hari, dari **`hr.attendance`** pada rentang
    periode payroll. Threshold default **8 jam**.
  - `hourly_rate = total_gaji_pokok / 173`; `overtime_rate` default **1.5**;
    `overtime_amount = hours × hourly_rate × overtime_rate`.
  - `overtime_override` (manual override) jika > 0 menang.
  - Page **Overtime** di view slip menampilkan threshold/rate/override.
  - `_auto_populate_basic_salary_and_bpjs()` membuat detail `lembur` "Auto
    Overtime" senilai `overtime_amount`.
- ✅ **Tidak pernah membaca `presenly.overtime.request`.**

---

## 2. Diagnosis Akar Masalah

| # | Masalah | Efek |
|---|---|---|
| 1 | `presenly.overtime.request` approved **tidak** terhubung ke `custom.payroll.slip` | Lembur yang disetujui HR **tidak dibayar** (data berhenti di status approved). |
| 2 | Payroll menghitung lembur dari `hr.attendance.worked_hours > 8 jam` (sumber legacy) | Dua konsekuensi salah: (a) employee yang lembur lewat request Presenly (mis. 18:00–22:00) setelah shift reguler 7 jam → `worked_hours` = 7 → **tidak dihitung padahal ada request approved**; (b) employee yang bekerja >8 jam tanpa request → payroll **menghitung lembur padahal tidak pernah disetujui** (salah bayar). |
| 3 | `has_attendance_evidence` hanya cek "ada attendance" di tanggal itu, bukan apakah jam lembur tercakup dalam attendance | Bukti lembur lemah: request bisa lolos meski attendance tidak mencakup jam request. (Opsional diperketat.) |
| 4 | Belum ada konsep **rate bertingkat UU** (jam 1 = 1.5×, jam berikutnya = 2×, PP 35/2021 Pasal 31) | Payroll hanya flat 1.5×; tidak sesuai regula si umum bila perusahaan memilih skema tersebut. (Opsional.) |
| 5 | Tidak ada mekanisme **refresh otomatis** saat request approved setelah slip dibuat | Slip yang sudah dibuat sebelum approval lembur tidak ikut ter-update sampai di-recompute. |

---

## 3. Keputusan Arsitektur

### 3.1 Sumber kebenaran lembur untuk payroll
**`presenly.overtime.request` dengan `state = 'approved'`** adalah satu-satunya
sumber yang disetujui (approval journey) dan sesuai desain Presenly (native
extra-hours dimatikan). Payroll harus membaca sumber ini.

### 3.2 Cara mengintegrasikan (tanpa mengubah dependensi dua modul besar)
Dua modul saat ini tidak saling depend (`presenly` depend `hr*`; `hr_payroll_custom`
depend `hr`, `mail`). Agar tidak memaksa `presenly` (backoffice attendance)
men-depend modul payroll dan sebaliknya, buat **modul bridge**:

```
custom_addons/presenly_payroll/   (baru)
  __manifest__.py  → depends: ['presenly', 'hr_payroll_custom'], auto_install
  models/custom_payroll_slip.py   → ext. slip (source + compute override)
  views/custom_payroll_slip_views.xml → page Overtime tambahan
  __init__.py
```

- `auto_install = True` → otomatis terpasang bila kedua modul terpasang.
- Jika payroll di-uninstall, `presenly` tetap berjalan (tanpa integrasi).
- Tanpa perubahan besar di `hr_payroll_custom` yang terpasang di produksi.

### 3.3 Pemilihan sumber per slip (anti double-count)
Tambahkan selector `overtime_source` pada `custom.payroll.slip`:

| Value | Label | Sumber jam lembur |
|---|---|---|
| `presenly` *(default)* | Presenly Overtime Requests | `sum(duration_hours)` request **approved**, `date` dalam periode payroll |
| `attendance` *(legacy)* | Attendance Extra Hours | perilaku lama: `sum(worked_hours > threshold)` dari `hr.attendance` |
| `manual` | Manual Override | `overtime_override` (>.0 menang) |

Hanya **satu** sumber yang dihitung → tidak ada double-count. `overtime_override`
tetap menang di semua mode (prinsip "human override").

---

## 4. Detail Implementasi

### 4.1 `custom_addons/presenly_payroll/__manifest__.py`
```python
{
    'name': 'Presenly → Payroll Bridge',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Bridges approved Presenly overtime requests into Custom Payroll slips',
    'depends': ['hr_payroll_custom', 'presenly'],
    'data': ['views/custom_payroll_slip_views.xml'],
    'auto_install': True,
    'license': 'LGPL-3',
}
```

### 4.2 `models/custom_payroll_slip.py` (extend `custom.payroll.slip`)
```python
from odoo import api, fields, models

class CustomPayrollSlip(models.Model):
    _inherit = 'custom.payroll.slip'

    overtime_source = fields.Selection([
        ('presenly', 'Presenly Overtime Requests (approved)'),
        ('attendance', 'Attendance Extra Hours (legacy)'),
        ('manual', 'Manual Override'),
    ], string='Overtime Source', default='presenly', required=True)

    presenly_approved_overtime_hours = fields.Float(compute='_compute_presenly_overtime')
    presenly_approved_count = fields.Integer(compute='_compute_presenly_overtime')

    @api.depends('payroll_batch_id.periode_bulan', 'payroll_batch_id.periode_tahun', 'employee_id')
    def _compute_presenly_overtime(self):
        Overtime = self.env['presenly.overtime.request'].sudo()
        for rec in self:
            if not (rec.employee_id and rec.payroll_batch_id.periode_bulan
                    and rec.payroll_batch_id.periode_tahun):
                rec.presenly_approved_overtime_hours = 0.0
                rec.presenly_approved_count = 0
                continue
            req = Overtime.search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved'),
                ('date', '>=', f'{rec.payroll_batch_id.periode_tahun}-{int(rec.payroll_batch_id.periode_bulan):02d}-01'),
                # batas akhir bulan dihitung via calendar (sama dgn existing code)
            ])
            rec.presenly_approved_overtime_hours = sum(req.mapped('duration_hours'))
            rec.presenly_approved_count = len(req)

    @api.depends('overtime_source', 'presenly_approved_overtime_hours',
                 'attendance_overtime_hours', 'overtime_override', 'overtime_threshold_hours')
    def _compute_attendance_overtime(self):
        """Override compute: pilih sumber sesuai overtime_source."""
        for rec in self:
            if rec.overtime_override and rec.overtime_override > 0:
                rec.attendance_overtime_hours = rec.overtime_override
                continue
            if rec.overtime_source == 'presenly':
                # pastikan _compute_presenly_overtime sudah jalan
                rec._compute_presenly_overtime()
                rec.attendance_overtime_hours = rec.presenly_approved_overtime_hours
            elif rec.overtime_source == 'attendance':
                # perilaku lama: hitung dari hr.attendance
                ... (pindahkan logika lama ke helper _compute_attendance_extra_hours)
            # manual tanpa override -> 0 via branch pertama? jika override 0 & manual, set 0
            else:
                rec.attendance_overtime_hours = 0.0
```

> Catatan: pindahkan logika lama perhitungan dari `hr.attendance` ke helper
> tersendiri agar mudah dipakai mode `attendance` dan tidak mengubah perilaku bila
> user memilih legacy. Field `attendance_overtime_hours` dipertahankan namanya
> (backward-compat untuk view & detail 'Auto Overtime') tetapi isinya kini
> mengikuti `overtime_source`.

### 4.3 `wizard/custom_payroll_generate_wizard.py` (extend)
Default `overtime_source` = `presenly` saat membuat slip via wizard Generate:
```python
slip = self.env['custom.payroll.slip'].create({
    ...
    'overtime_source': 'presenly',
})
```

### 4.4 View — `custom_addons/presenly_payroll/views/custom_payroll_slip_views.xml`
Di page **Overtime** (inherit `hr_payroll_custom.custom_payroll_slip_view_form`),
tambahkan:
```xml
<field name="overtime_source"/>
<field name="presenly_approved_count" readonly="1"/>
<field name="presenly_approved_overtime_hours" readonly="1"/>
```
+ update teks bantuan: "Hours come from approved Presenly Overtime Requests
(default) or legacy Attendance Extra Hours; Manual Override wins."

### 4.5 (Opsional, rekomendasi) Rate lembur bertingkat UU — PP 35/2021 Pasal 31
Tambahkan di slip:
```python
overtime_rate_mode = fields.Selection([
    ('flat', 'Flat Rate (1.5× per jam)'),
    ('pp35', 'Progressive (1.5× jam pertama, 2× jam berikutnya)'),
], default='flat')
```
Perhitungan per **hari** (agar "jam pertama" dihitung per hari, bukan per bulan):
```python
# untuk setiap request approved (punya date + duration):
#   jam_pertama = min(duration, 1.0); sisa = duration - 1.0
#   amount_hari = jam_pertama * 1.5 * hourly + sisa * 2.0 * hourly
```
- Mode `pp35` hanya bermakna bila `overtime_source == 'presenly'` (sebab butuh
  breakdown per request per hari); bila source `attendance`, jatuh ke flat.
- Default tetap flat agar tidak mengubah perilaku eksisting.

### 4.6 (Opsional) Ketatkan bukti attendance §1.2 masalah #3
Di `presenly.overtime.request._presenly_validate_submission`, perketat
`has_attendance_evidence` dari "ada attendance di tanggal itu" menjadi
"attendance pada tanggal itu **mencakup rentang jam** request
(atau jarak wajar ±toleransi, configurable)". Ini mencegah request yang
tidak tercermin realitas absensi. **Bersifat opsional** — jangan ubah dulu di
plan ini agar tidak mengganggu API/contract mobile; dokumentasikan sebagai
backlog.

---

## 5. Anti Double-Count & Konsistensi

1. `overtime_source` dipilih **per slip**; hanya satu sumber dihitung.
2. Saat `presenly` dipilih, **jangan** menambahkan komponen dari attendance
   extra-hours (mode `attendance` saja yang berisi itu).
3. Native `hr.attendance.overtime.line` tetap nonaktif (`_update_overtime`
   return True) — tidak ada jalur lain.
4. `overtime_override > 0` selalu menang (manual correction).
5. Slip yang sudah dibuat sebelum approval lembur: beri tombol/aksi
   `action_refresh_overtime()` (recompute `attendance_overtime_hours`) dan
   catat bahwa **slip hanya boleh di-refresh saat status draft/confirmed**,
   agar nilai approved/paid tidak berubah diam-diam:
   ```python
   def action_refresh_overtime(self):
       for rec in self:
           if rec.status in ('paid', 'cancelled'):
               raise UserError(_('Cannot refresh overtime on locked slips.'))
       self.invalidate_recordset(['attendance_overtime_hours', 'overtime_amount'])
   ```

---

## 6. File yang Akan Diubah / Dibuat

| File | Aksi | Keterangan |
|---|---|---|
| `custom_addons/presenly_payroll/__manifest__.py` | **Buat** | Modul bridge, `auto_install` |
| `custom_addons/presenly_payroll/__init__.py` | **Buat** | Import models |
| `custom_addons/presenly_payroll/models/__init__.py` | **Buat** | — |
| `custom_addons/presenly_payroll/models/custom_payroll_slip.py` | **Buat** | Extend slip: `overtime_source`, compute override, rate mode, `action_refresh_overtime` |
| `custom_addons/presenly_payroll/views/custom_payroll_slip_views.xml` | **Buat** | Page Overtime tambahan |
| `custom_addons/presenly_payroll/wizard/custom_payroll_generate_wizard.py` | **Buat** (opsional) | Default source `presenly` di wizard |
| `custom_addons/presenly/tests/test_api_overtime.py` | **Tidak diubah** | — |
| `docs/MOBILE_API_FULL.md` §8 | **Update dok** | Catatan: lembur approved kini diteruskan ke payroll |
| `docs/PLAN_OVERTIME_PAYROLL.md` (file ini) | — | Ringkasan |

Opsi lanjutan (bila disetujui):
- `custom_addons/presenly/models/presenly_overtime.py`: perketat bukti jam
  attendance (backlog).
- `custom_addons/presenly/data/presenly_data.xml`: tambah `ir.config_parameter`
  untuk toleransi jam bukti (backlog).

---

## 7. Test Plan (`presenly_payroll/tests/`)

1. Beri employee: contract wage 3.480.000 (hourly = 20.000) + 2 request overtime
   approved (18:00–21:00 = 3 jam, 19:00–23:00 = 4 jam) dalam bulan periode.
   - Generate slip → `overtime_source=presenly` → `attendance_overtime_hours=7`,
     `overtime_amount = 7 × 20.000 × 1.5 = 210.000`; detail `lembur` terisi.
2. **Double-count guard:** tambah attendance dengan `worked_hours=10` pada bulan
   yang sama → mode `presenly` TIDAK menambah extra-hours; jumlah tetap 7 jam.
3. **Legacy mode:** `overtime_source=attendance` → gunakan perilaku lama
   (threshold 8 jam), hasil sesuai hitungan lama.
4. **Manual override:** `overtime_override=5` → menang di mode mana pun.
5. **Approved-only:** request `submitted`/`rejected`/`cancelled` **tidak**
   dihitung; request approved di luar bulan tidak masuk.
6. **Rate bertingkat (opsional):** `overtime_rate_mode=pp35` → request 3 jam
   = 1×1.5×20.000 + 2×2×20.000 = 30.000 + 80.000 = 110.000.
7. **Refresh lock:** slip `paid`/`cancelled` menolak `action_refresh_overtime`.
8. **Auto-install:** dengan kedua modul terpasang, `presenly_payroll` terpasang;
   uninstall `hr_payroll_custom` → bridge ikut uninstall, `presenly` jalan.

Validasi:
```bash
source odoo-venv/bin/activate
python -m compileall -q custom_addons/presenly_payroll
./odoo-bin server -c odoo.conf -d odoo -u presenly_payroll \
  --test-enable --test-tags /presenly_payroll --stop-after-init \
  --http-port=18080 --http-interface=127.0.0.1 --max-cron-threads=0
```

---

## 8. Checklist Pengerjaan

- [ ] **1.** Buat struktur modul `presenly_payroll` (manifest + `__init__`).
- [ ] **2.** Extend `custom.payroll.slip`: field `overtime_source` + compute override
      (source presenly/attendance/manual) + helper `_compute_presenly_overtime`.
- [ ] **3.** Pindahkan logika lama `hr.attendance` ke helper mode `attendance`.
- [ ] **4.** Default `overtime_source='presenly'` di wizard Generate.
- [ ] **5.** View page Overtime: `overtime_source`, `presenly_approved_count`,
      `presenly_approved_overtime_hours`, tombol Refresh.
- [ ] **6.** `action_refresh_overtime` + guard status lock.
- [ ] **7.** (Opsional) `overtime_rate_mode` flat vs `pp35` per-hari.
- [ ] **8.** Test suite `presenly_payroll` (7 skenario di atas).
- [ ] **9.** Bump versi `presenly` → `19.0.14.x` bila ada perubahan kecil + update
      `docs/MOBILE_API_FULL.md` §8.
- [ ] **10.** Validasi perintah di §7; pastikan suite penuh `/presenly` tetap hijau.

---

## 9. Keputusan yang Perlu Konfirmasi HR/Finance

1. Source default lembur = **Presenly approved requests** (setuju? atau tetap
   attendance extra-hours legacy?).
2. Rate: **flat 1.5×** (status quo) atau **bertingkat PP 35**: jam 1 = 1.5×,
   jam berikutnya = 2× (default tetap flat bila belum diputuskan).
3. Batas refresh slip (draft/confirmed saja) — setuju?
4. Perketat bukti attendance supaya jam request tercakup attendance
   (opsional / backlog).
5. Tidak ada uang makan lembur (fitur sudah di-revert) — konfirmasi tetap.