# Plan: Payroll Menerima Lembur HANYA dari Presenly Overtime Requests

> **Status:** Keputusan final — source tunggal.
> **Pengganti:** Draf multi-source (`PLAN_OVERTIME_PAYROLL.md` §3.3 — selector
> `overtime_source` dengan mode `attendance` **dibatalkan**).
> **Lingkup:** `presenly.overtime.request` (approved) → `custom.payroll.slip`.

---

## 1. Keputusan (final)

1. **Satu-satunya sumber lembur untuk payroll = `presenly.overtime.request`
   dengan `state == 'approved'`** dan `date` berada dalam periode payroll.
2. **Tidak ada** perhitungan lembur dari `hr.attendance.worked_hours` lagi.
   Native `hr.attendance.overtime.line` sudah nonaktif; jalur legacy dibuang.
3. **Satu-satunya pengecualian:** `overtime_override > 0` pada slip
   (manual correction oleh Payroll Admin) — tetap menang atas semua.
4. Tidak ada uang makan lembur (fitur sudah di-revert).
5. Rate default **flat 1.5×**; rate bertingkat PP 35/2021 menjadi opsi lanjutan
   (lihat §5) yang menunggu konfirmasi HR/Finance.

### Mengapa hanya Presenly saja (alasan)

| Sebelum (campur) | Sesudah (Presenly-only) |
|---|---|
| Payroll hitung `worked_hours - 8` dari attendance → salah bayar: lembur approved tidak dibayar, lembur tanpa approval malah dibayar | Hanya request **approved** yang masuk → semua jam yang dibayar sudah **disetujui** lewat approval journey |
| Dua sumber → risiko double-count & selisih interpretasi | Satu sumber → deterministik, audit trail jelas (siapa/apa yang disetujui) |
| Threshold 8 jam & rate flat di slip | Durasi eksplisit per request; jumlah = Σ durasi approved |

---

## 2. Kontrak Data: Request → Slip

| Atribut request `presenly.overtime.request` | Dipakai untuk |
|---|---|
| `state == 'approved'` | Filter utama (submitted/rejected/cancelled/draft **tidak** dihitung) |
| `date` | Dalam rentang periode payroll: `[tgl-1 .. akhir bulan periode]` |
| `duration_hours` (server-side, `hour_to - hour_from`) | Jam lembur yang dibayar |
| `employee_id` | Match dengan `custom.payroll.slip.employee_id` |
| `work_location_id` | Hanya untuk info; tidak mengubah kalkulasi |
| `reason` | Opsional, bisa tampil di deskripsi detail |

**Rumus:**
```
presenly_approved_hours = Σ duration_hours (request approved, date dalam periode)
jam_efektif            = overtime_override if overtime_override > 0 else presenly_approved_hours
hourly_rate            = total_gaji_pokok / 173
overtime_amount        = jam_efektif × hourly_rate × overtime_rate   # default rate 1.5
```

**Detail slip yang dibuat (component `lembur`):** 1 baris "Auto Overtime
(Presenly)" senilai `overtime_amount`, dengan `description` memuat ringkasan:
`"Auto Overtime: 3 request × 7 jam"`.

---

## 3. Implementasi — Modul Bridge `presenly_payroll`

`presenly` (backoffice attendance) dan `hr_payroll_custom` (payroll) tidak
saling depend. Buat modul jembatan agar integrasi menyala hanya bila keduanya
terpasang, tanpa mengubah dependensi inti.

```
custom_addons/presenly_payroll/
  __manifest__.py                          # depends: hr_payroll_custom, presenly; auto_install
  __init__.py
  models/__init__.py
  models/custom_payroll_slip.py            # extend slip: compute dari presenly approved
  views/custom_payroll_slip_views.xml      # page Overtime: ringkasan presenly + tombol refresh
  wizard/__init__.py
  wizard/custom_payroll_generate_wizard.py # default otomatis (bila perlu)
  tests/test_overtime_payroll.py           # skenario §6
```

### 3.1 `models/custom_payroll_slip.py` (extend)

```python
class CustomPayrollSlip(models.Model):
    _inherit = 'custom.payroll.slip'

    # --- Ringkasan sumber Presenly (computed live, bukan snapshot) ---
    presenly_approved_count = fields.Integer(
        compute='_compute_presenly_overtime', string='Approved Overtime Requests',
    )
    presenly_approved_hours = fields.Float(
        compute='_compute_presenly_overtime',
        string='Approved Overtime Hours (Presenly)',
    )
    presenly_approved_request_ids = fields.One2many(
        'presenly.overtime.request',
        compute='_compute_presenly_requests', string='Approved Requests',
    )

    @api.depends('payroll_batch_id.periode_bulan',
                 'payroll_batch_id.periode_tahun', 'employee_id')
    def _compute_presenly_requests(self):
        for rec in self:
            domain = self._presenly_overtime_domain()
            # compute hanya mengisi recordset; per-bulan dibatasi via domain
            rec.presenly_approved_request_ids = self.env[
                'presenly.overtime.request'].sudo().search(domain)

    def _presenly_overtime_domain(self):
        """Periode payroll: tgl-1 .. akhir bulan (calendar)."""
        year, month = self.payroll_batch_id.periode_tahun, int(self.payroll_batch_id.periode_bulan)
        start = f'{year}-{month:02d}-01'
        import calendar
        end_day = calendar.monthrange(year, month)[1]
        end = f'{year}-{month:02d}-{end_day:02d}'
        return [
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'approved'),
            ('date', '>=', start),
            ('date', '<=', end),
        ]

    @api.depends('presenly_approved_request_ids.duration_hours')
    def _compute_presenly_overtime(self):
        for rec in self:
            reqs = rec.presenly_approved_request_ids
            rec.presenly_approved_count = len(reqs)
            rec.presenly_approved_hours = sum(reqs.mapped('duration_hours'))

    @api.depends('presenly_approved_hours', 'overtime_override')
    def _compute_attendance_overtime(self):
        """Override: hours SELALU dari Presenly approved (atau manual override).
        Logika lama berbasis hr.attendance dihapus sepenuhnya."""
        for rec in self:
            rec.attendance_overtime_hours = (
                rec.overtime_override if rec.overtime_override and rec.overtime_override > 0
                else rec.presenly_approved_hours
            )
```

Catatan penting:
- **Field `attendance_overtime_hours` dipertahankan namanya** (backward-compat:
  view/laporan slip lama tidak perlu diubah), tetapi **maknanya diganti**:
  sekarang = jam dari Presenly approved (atau override). `overtime_amount`,
  `hourly_rate`, `overtime_rate` tetap dihitung seperti semula dari field ini.
- **`overtime_threshold_hours` menjadi tidak terpakai.** Sembunyikan di view
  dengan keterangan "digunakan pada versi lama (attendance extra hours); kini
  lembur hanya dari request Presenly yang disetujui".
- `presenly_approved_request_ids` dihitung live → jika request approved
  di-cancel/di-hapus setelah slip dibuat, slip **tidak otomatis berubah**;
  gunakan tombol Refresh (§4.2) yang ter-proteksi status.

### 3.2 Default saat generate slip (wizard)

`custom.payroll.generate.wizard` memanggil `custom.payroll.slip.create(...)` lalu
`_auto_populate_basic_salary_and_bpjs()`. Karena compute berbasis field slip,
tidak perlu ubah wizard — compute otomatis berjalan saat slip diakses/disimpan.

### 3.3 `views/custom_payroll_slip_views.xml` (extend page Overtime)

- Tambahkan (readonly):
  - `presenly_approved_count` — banyaknya request approved periode ini.
  - `presenly_approved_hours` — total jam.
  - `presenly_approved_request_ids` — list kecil (tanggal, jam, durasi, lokasi,
    approver last) untuk transparansi audit.
  - Tombol **Refresh Overtime** (`action_refresh_overtime`).
- Sembunyikan `overtime_threshold_hours` (legacy, tidak terpakai).
- Teks bantuan: *"Overtime on this slip comes from approved Presenly Overtime
  Requests within the payroll period. Manual Override (if >0) always wins.
  Paid/Cancelled slips are locked."*

---

## 4. Operasi

### 4.1 Pembersihan request (deletion guard — sudah ada dari pekerjaan sebelumnya)
- `presenly.overtime.request.unlink()` hanya boleh Admin / HR (state
  draft/rejected/cancelled); **approved** hanya Admin + konfirmasi.
- Setiap penghapusan tercatat di `presenly.deletion.log` (append-only).
- Implikasi: slip yang sudah pernah membaca request approved lalu request-nya
  dihapus → jalankan Refresh untuk memperbarui; slip paid tidak bisa.

### 4.2 Tombol Refresh Overtime
```python
def action_refresh_overtime(self):
    for rec in self:
        if rec.status in ('paid', 'cancelled'):
            raise UserError(_('Cannot refresh overtime on locked slips '
                              '(paid or cancelled).'))
    self.invalidate_recordset(['presenly_approved_hours',
                               'presenly_approved_count',
                               'attendance_overtime_hours', 'overtime_amount'])
    # re-create detail lembur "Auto Overtime" bila berubah
    self._sync_auto_overtime_detail()
```
- Hanya boleh dijalankan pada status **draft / confirmed**. Slip approved/paid
  terkunci agar nilai final tidak berubah diam-diam.

### 4.3 Anti double-count
Dengan source tunggal:
- Tidak ada hitungan dari `hr.attendance` sama sekali → tidak mungkin dobel.
- Native `hr.attendance.overtime.line` tetap nonaktif (di `presenly`).
- ≤1 request/employee/date (constraint existing) → durasi tidak tumpang-ganda
  antar request.
- `overtime_override > 0` menimpa total (manual correction, tidak menambah).

---

## 5. Opsi Lanjutan (menunggu keputusan HR/Finance)

### 5.1 Rate bertingkat PP 35/2021 (per hari)
```python
overtime_rate_mode = fields.Selection([
    ('flat', 'Flat (1.5× per jam)'),          # default
    ('pp35', 'Progressive (1.5× jam 1, 2× jam berikutnya)'),
], default='flat')
```
Perhitungan per **request** (punya `date` + `duration_hours`):
```
jam1 = min(duration, 1.0); sisa = max(duration - 1.0, 0.0)
amount_hari = jam1 * 1.5 * hourly + sisa * 2.0 * hourly
```
- Hanya bermakna dengan source Presenly (default). Flat tetap default sampai HR
  memutuskan.

### 5.2 (Backlog) Perketat bukti jam attendance
`_presenly_validate_submission` saat ini hanya cek "ada attendance pada `date`".
Usulan lanjutan: attendance pada tanggal itu **mencakup** rentang
`hour_from..hour_to` request (dengan toleransi configurable). Ini menutup celah
"request approved tapi attendance tidak mencakup jam lembur". Tidak masuk scope
saat ini agar kontrak API mobile tidak berubah mendadak.

---

## 6. Test Plan

1. **Slot dasar:** employee (wage 3.480.000 → hourly 20.000) punya 2 request
   approved bulan periode: 18:00–21:00 (3 jam) & 19:00–23:00 (4 jam).
   → `presenly_approved_hours=7`, `attendance_overtime_hours=7`,
   `overtime_amount=7×20.000×1.5=210.000`, detail `lembur` = 210.000.
2. **Tidak pakai attendance lagi:** tambah attendance `worked_hours=10` di bulan
   yang sama dengan **tanpa** request approved → `attendance_overtime_hours=0`
   (sebelumnya akan = 2 jam). Ini bukti "Presenly-only".
3. **Hanya approved:** request `submitted` / `rejected` / `cancelled` → 0 jam.
4. **Batas periode:** request `date` di luar bulan (sebelum tgl-1 / setelah akhir
   bulan) → tidak masuk.
5. **Override menang:** `overtime_override=5` → `attendance_overtime_hours=5`,
   amount mengikuti 5 jam.
6. **Refresh lock:** slip `paid`/`cancelled` menolak `action_refresh_overtime`;
   `draft`/`confirmed` sukses dan detail lembur tersinkron.
7. **Deletion trace:** hapus request approved (Admin + konfirmasi) → `deletion.log`
   tercatat; slip draft + Refresh → jam menurun.
8. **Auto-install:** kedua modul terpasang → `presenly_payroll` terpasang;
   uninstall `hr_payroll_custom` → bridge ikut uninstall, `presenly` tetap jalan.
9. **Rate bertingkat (opsional):** mode `pp35`, request 3 jam →
   `1×1.5×20.000 + 2×2×20.000 = 30.000 + 80.000 = 110.000`.

Validasi:
```bash
source odoo-venv/bin/activate
python -m compileall -q custom_addons/presenly_payroll
./odoo-bin server -c odoo.conf -d odoo -u presenly_payroll \
  --test-enable --test-tags /presenly_payroll --stop-after-init \
  --http-port=18080 --http-interface=127.0.0.1 --max-cron-threads=0
```

---

## 7. File yang Diubah / Dibuat

| File | Aksi |
|---|---|
| `custom_addons/presenly_payroll/__manifest__.py` | Buat (auto_install) |
| `custom_addons/presenly_payroll/__init__.py` | Buat |
| `custom_addons/presenly_payroll/models/__init__.py` | Buat |
| `custom_addons/presenly_payroll/models/custom_payroll_slip.py` | Buat |
| `custom_addons/presenly_payroll/views/custom_payroll_slip_views.xml` | Buat |
| `custom_addons/presenly_payroll/tests/test_overtime_payroll.py` | Buat |
| `custom_addons/presenly/docs/PLAN_OVERTIME_PAYROLL.md` | Update: tandai draf selector dibatalkan |
| `custom_addons/presenly/docs/MOBILE_API_FULL.md` §8 | Update dok: lembur approved diteruskan ke payroll |

---

## 8. Checklist Pengerjaan

- [ ] 1. Buat modul `presenly_payroll` (manifest + `__init__` + `auto_install`).
- [ ] 2. Extend `custom.payroll.slip`: `presenly_approved_count/hours/request_ids`
      + override `_compute_attendance_overtime` (Presenly-only + override manual).
- [ ] 3. Sembunyikan `overtime_threshold_hours` (legacy) di view; tambah ringkasan
      presenly + tombol Refresh + guard status.
- [ ] 4. Implement `action_refresh_overtime` + `_sync_auto_overtime_detail`.
- [ ] 5. (Opsional) `overtime_rate_mode` flat/pp35.
- [ ] 6. Test suite `presenly_payroll` (9 skenario §6).
- [ ] 7. Update docs (tandai selector lama dibatalkan; MOBILE_API_FULL §8).
- [ ] 8. Validasi perintah §6; pastikan suite `/presenly` tetap hijau; bump versi
      bila perlu (presenly → 19.0.14.x).

---

## 9. Konfirmasi yang Masih Dibutuhkan

1. ✅ Source default = **Presenly approved requests saja** (final, sesuai arahan).
2. Rate: flat 1.5× (default) atau bertingkat PP 35 — tunggu keputusan.
3. Slip paid/cancelled terkunci dari Refresh — setuju?
4. Perketat bukti jam attendance — backlog, bukan scope saat ini.
5. Uang makan tetap tidak ada.