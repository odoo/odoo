# PLAN FINAL — Work Location Otomatis (Attendance & Pengajuan Time Off/Permission)

**Status:** Final — kebijakan sudah dikunci, siap eksekusi.
**Database/modul:** `odoo` / `presenly` 19.0.13.6.0
**File terkait:**
- `custom_addons/presenly/models/hr_employee.py` — resolver lokasi
- `custom_addons/presenly/models/presenly_schedule.py` — model slot (order field)
- `custom_addons/presenly/controllers/leave.py`, `controllers/permission.py` — `_work_location`, creator
- Docs: `MOBILE_API.md`, `MOBILE_TIMEOFF_API.md`, `MOBILE_APPROVAL_API.md`

---

## 0. Keputusan Bisnis (TERKUNCI)

| # | Keputusan | Pilihan final |
|---|---|---|
| K1 | Periode pengajuan mencakup **2+ lokasi berbeda** (lintas hari) | **TOLAK**, kembalikan daftar lokasi per tanggal agar mobile menampilkan pilihan |
| K2 | **Satu hari** punya **2+ lokasi** (slot beda jam) | **PILIH YANG PERTAMA** untuk sementara (slot paling awal; bukan konflik) |
| K2b | **Mode `hours`** (parsial) satu hari | **PILIH SLOT YANG BERIRISAN DENGAN JAM IZIN**; bila tak ada/tidak unik → fall back ke slot pertama |
| K3 | Endpoint `location-options` | **Ya, dibuka** untuk preview per tanggal sebelum submit |
| K4 | Scope | Time Off **dan** Permission serentak (helper bersama) |

### Definisi "pertama" (dari kode, bukan asumsi)

`presenly.work.location.schedule` punya `_order = 'employee_id, schedule_type desc, schedule_date, weekday, week_type, hour_from, id'`, dan slot dalam satu hari **dilarang overlap** (constraint `_check_schedule`). Maka untuk satu tanggal:

- **Slot pertama = `hour_from` terkecil** (jam mulai paling awal), tiebreak `id` terkecil.
- Lokasi hari itu = `work_location_id` milik slot tersebut.

### Aturan spesifik mode `hours` (K2b)

`presenly.permission` mode `hours` = parsial jam pada **satu tanggal**, dengan `hour_from`/`hour_to` wajib (0–24, `date_from == date_to`).

Untuk mode ini, lokasi dipilih berdasarkan **irisan slot dengan rentang jam izin**:

```text
slot_cocok = slot2 hari tsb yang:
    slot.hour_from <= hour_to  DAN  slot.hour_to >= hour_from   # overlap rentang
```

- Bila **persis satu** slot cocok → pakai slot itu.
- Bila **tidak ada** yang cocok (mis. user izin di luar jam kerja / jam kosong) → **fall back ke slot pertama** (K2).
- Bila **lebih dari satu** cocok (dua slot beda lokasi, jam saling tumpang tindih di tepi) → pakai **slot pertama yang cocok** (order `hour_from`, id) sebagai determinisme.

> Alasan: mode `hours` memilih lokasi yang relevan dengan waktu izin, bukan sekadar slot paling awal hari itu. Ini lebih akurat untuk skenario "izin jam 10:00–12:00 di lokasi siang" dan tidak memerlukan perubahan schema.

---

## 1. Pengertian Ringkas "Otomatis dari apa"

Resolver lokasi Presenly (`hr_employee.py`) memakai rantai prioritas **per tanggal**:

1. Presenly **Specific-Date Schedule** (`schedule_type='date'`)
2. Presenly **Weekly Schedule** (`schedule_type='weekly'`, window jam valid)
3. Native **Exceptional Location** per tanggal (`hr.employee.location`)
4. Native **Daily Location** per hari (`monday_location_id` … `sunday_location_id`)
5. Employee **Primary Work Location** (fallback)

Oleh karena **schema request (hr.leave / presenly.permission) hanya punya 1 kolom lokasi**, otomatisasi membutuhkan **reduksi ke satu lokasi per request** sesuai keputusan K1/K2:

```text
resolve(date_from..date_to, hour_from=None, hour_to=None):
  per_date = {}                      # {tanggal: lokasi}
  for tgl in range(date_from..date_to):
      slots = slot aktif tanggal tsb (date → weekly, urut hour_from)
      if slots:
          if hour_from is not None:                    # K2b: mode hours
              cocok = [s for s in slots
                       if s.hour_from <= hour_to and s.hour_to >= hour_from]
              per_date[tgl] = (cocok[0] if cocok else slots[0]).work_location_id
          else:                                         # K2: full_day
              per_date[tgl] = slots[0].work_location_id
      elif exception/tgl:
          per_date[tgl] = exception.work_location_id
      elif daily[tgl.weekday()]:
          per_date[tgl] = daily
      elif primary:
          per_date[tgl] = primary
      else:
          return error "tidak ada lokasi pada tgl X"

  unique = set(per_date.values())
  if len(unique) == 1:
      return unique_single_location        # otomatis isi, lanjut submit
  else:
      raise ValidationError(
          "Periode mencakup lebih dari satu Work Location."   # K1: tolak
          + daftar per tanggal
      )
```

---

## 2. Perubahan Per File

### 2.1 Model — helper bersama (baru)

**`hr_employee.py`** — tambah method:

```python
def _presenly_resolve_period_location(self, date_from, date_to, hour_from=None, hour_to=None):
    """Return (location_or_False, by_date dict) for the period.

    - 'first' slot policy: when several slots exist on one day, the first
      (earliest hour_from) wins (K2).
    - For partial-hours requests (K2b), when hour_from/hour_to are provided,
      prefer the slot overlapping that time range; fall back to the first
      slot when no such slot exists.
    - Multi-location across days raises nothing here; returns location False
      and the full by_date map so the caller can reject with details (K1).
    """
```

Catatan tambahan:
- Memakai ulang logika `_presenly_work_locations_for_period` yang sudah ada; yang baru adalah **mengumpulkan `by_date`**, **menerapkan K2** (hanya slot pertama tiap hari), dan **K2b** (irisan jam bila `hour_from/hour_to` diberikan).
- Tetap `sudo()` + filter active/company, konsisten dengan resolver saat ini.
- Tambahkan flag `ambiguous` di return: `True` bila `len(unique) > 1`.

### 2.2 Attendance — rekomendasi + auto yang diekspos

**`controllers/attendance.py`**:
- Helper kecil `_presenly_recommended_location_now(employee)`:
  - `locations, schedules = employee._presenly_locations_at()`.
  - Bila `len(locations) == 1` → id tsb.
  - Bila `len(locations) > 1` → `False` + `ambiguous=True` (biarkan GPS memilih deterministik; tandai agar mobile tampilkan picker).
  - Bila kosong → `False`.
- **`/attendance/status`** tambah field (additive, tidak mengubah lama):
  - `recommended_work_location_id`
  - `auto_selection_supported` (`bool` — ada lokasi geofence-ready terjadwal)
  - `ambiguous` (`bool`)
- Perilaku auto **tetap**: mobile yang tidak mengirim `work_location_id` → `_location_for_employee` pilih by GPS. Tidak ada perubahan perilaku transaksi.

### 2.3 Time Off & Permission — `work_location_id` opsional + reject lintas-hari

**`controllers/leave.py` `create_leave`** & **`controllers/permission.py` `create`**:
- `work_location_id` **tidak wajib lagi**.
- Bila tidak dikirim:
  - `location, by_date = employee._presenly_resolve_period_location(
        date_from, date_to, hour_from, hour_to)`.
    - Time Off: `hour_from/hour_to` tidak dikirim → K2 (slot pertama).
    - Permission mode `hours`: kirim `hour_from/hour_to` → K2b (slot beririsan).
    - Permission mode `full_day`: `hour_from/hour_to` tidak dikirim → K2.
  - `location` terisi (unik) → pakai, lanjut validasi+submit seperti biasa.
  - `location` False + `ambiguous` → **tolak** dgn pesan berisi daftar per tanggal (K1).
- Bila dikirim → tetap divalidasi `_work_location()` (lokasi wajib termasuk `_presenly_work_locations_for_period`) — **tidak ada bypass**.
- `_work_location()` dipertahankan sebagai validasi akhir (server safety net).

### 2.4 Endpoint baru — `location-options`

**`leave.py`** dan **`permission.py`**: `POST /api/presenly/v1/leaves/location-options` dan `POST /api/presenly/v1/permissions/location-options`.

Request:
```json
{ "jsonrpc": "2.0", "method": "call",
  "params": { "date_from": "2026-09-10", "date_to": "2026-09-12" }, "id": 13 }
```

Response (konsisten dengan `_presenly_resolve_period_location`):
```json
{
  "success": true,
  "data": {
    "unique": true,
    "location_id": 7,
    "locations": [ { "id": 7, "name": "Kantor Gresik" } ],
    "by_date": {
      "2026-09-10": { "id": 7, "name": "Kantor Gresik" },
      "2026-09-11": { "id": 7, "name": "Kantor Gresik" },
      "2026-09-12": { "id": 7, "name": "Kantor Gresik" }
    }
  }
}
```

- `unique=false` → `location_id: false`, `locations` berisi daftar lokasi berbeda urut tanggal.

### 2.5 Test (baru)

**`tests/test_api_leave.py`** (+ `test_api_permission.py`):
1. Create **tanpa** `work_location_id`, periode 1 hari 1 lokasi → sukses, `location_id` terisi otomatis.
2. Create tanpa lokasi, **satu hari 2 slot beda lokasi** (full_day) → sukses, terisi lokasi **slot pertama** (K2).
3. Create tanpa lokasi, **2 hari lokasi beda** → `ValidationError` berisi daftar per tanggal (K1).
4. `location-options` mengembalikan `unique`/`by_date` benar utk periode lintas lokasi.
5. Create **dengan** lokasi eksplisit di luar periode → tetap ditolak (safety net).
6. Permission **mode `hours`** tanpa lokasi, hari dengan 2 slot: izin jam beririsan slot B → terisi lokasi B (K2b); izin di luar semua slot → fall back slot pertama.
7. Attendance: `/attendance/status` mengembalikan 3 field baru; auto check-in tanpa `work_location_id` tetap berhasil (regresi).

---

## 3. Acceptance Criteria (per fase)

### Fase 1 — Model resolver + endpoint options
- [ ] `_presenly_resolve_period_location` benar utk: 1 hari 1 lokasi; 1 hari 2 slot (pilih pertama); mode `hours` beririsan slot B; mode `hours` di luar semua slot (fall back pertama); 2 hari beda lokasi (ambiguous); hari tanpa lokasi (error).
- [ ] `location-options` (leaves & permissions) mengembalikan `unique`, `location_id`, `locations`, `by_date`; untuk mode `hours` ikut menerima `hour_from/hour_to`.
- [ ] Tidak merusak `_presenly_work_locations_for_period` (bentuk ulang internal aman).

### Fase 2 — Controller auto-fill + reject
- [ ] Create Time Off & Permission tanpa `work_location_id` saat unik → sukses + `location_id` terisi.
- [ ] Create saat ambiguous lintas hari → tolak + daftar per tanggal.
- [ ] Create dgn lokasi eksplisit tak valid → tetap tolak.
- [ ] Semua test lulus di clone (48+ test, 0 error).

### Fase 3 — Attendance status + regresi
- [ ] `/attendance/status` menambah `recommended_work_location_id`, `auto_selection_supported`, `ambiguous` (additive).
- [ ] Auto check-in tanpa `work_location_id` tetap lulus (tidak ada perubahan perilaku).
- [ ] Clone upgrade: `-u presenly` 0 error/warning view.

### Fase 4 — Rollout & dokumentasi
- [ ] Backup `backups/presenly-migration/odoo-before-auto-location-<ts>.dump`.
- [ ] Upgrade produksi + restart server.
- [ ] Update `MOBILE_TIMEOFF_API.md` & `MOBILE_APPROVAL_API.md`: `work_location_id` opsional, endpoint `location-options`, perilaku K1/K2, dan petunjuk mobile (auto-fill bila unik; picker bila ambiguous).
- [ ] Update index `MOBILE_API.md` link.

---

## 4. Ringkasan Perilaku Final (untuk mobile)

| Situasi | Perilaku server | Mobile |
|---|---|---|
| Attendance, 1 lokasi terjadwal | Auto by GPS; `recommended_work_location_id` terisi | Tidak perlu picker |
| Attendance, geofence overlap | Pilih deterministik (id terkecil), `ambiguous: true` | Tampilkan picker |
| Pengajuan, periode 1 lokasi | `work_location_id` opsional; auto-isi | Tidak perlu pilih |
| Pengajuan, 1 hari 2 slot (`full_day`) | **Pilih slot pertama** (K2), auto-isi | Tidak perlu pilih |
| Permission mode `hours`, 1 hari 2 slot | **Pilih slot beririsan jam izin** (K2b); fall back slot pertama | Tidak perlu pilih |
| Pengajuan, periode lintas lokasi | **TOLAK** + daftar per tanggal (K1) | Tampilkan pilihan/ubah tanggal |
| Pengajuan, kirim lokasi eksplisit | Tetap divalidasi thd periode | Opsional override |

---

## 5. Risiko & Catatan

- **Schema**: request tetap 1 lokasi — strategi K2/K2b (slot pertama / slot beririsan jam) adalah kompromi sementara; bila nanti butuh multi-lokasi per request, itu perubahan schema besar dan di luar plan ini.
- **Backward compatibility**: `work_location_id` menjadi opsional; client lama yang mengirim tetap diterima. Tidak ada breaking change.
- **Keamanan**: validasi akhir `_work_location()` tidak dilewati; auto-fill hanya memakai resolver yang sudah di-scope ke employee+company.
- **Determinisme**: K2 memakai `hour_from` asc, id asc — konsisten dengan `_order` model schedule; K2b memakai urutan yang sama untuk slot yang beririsan.