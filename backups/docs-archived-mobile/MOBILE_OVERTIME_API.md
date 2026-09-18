# Presenly Mobile API — Overtime / Lembur

Dokumen ini adalah **referensi implementasi mobile** untuk pengajuan **Overtime / Lembur** (`presenly.overtime.request`) dengan jalur approval Presenly, setara dengan alur Time Off.

Autentikasi session, format JSON-RPC, login/logout, dan penanganan error umum: lihat [`MOBILE_API.md`](MOBILE_API.md).
Konsep approval & pengajuan Time Off/Permission: [`MOBILE_APPROVAL_API.md`](MOBILE_APPROVAL_API.md).

---

## 1. Konsep Overtime Presenly

- Employee mengajukan **satu periode lembur per hari** memakai: `date` (hari) + `hour_from` / `hour_to` (**jam 24 jam**).
- **Durasi dihitung server** (`duration_hours` = `hour_to - hour_from`), tidak dikirim client.
- **Wajib ada bukti attendance** (`hr.attendance`) pada hari lembur — tanpa itu submit ditolak.
- **Hanya 1 pengajuan per employee per hari**; pengajuan kedua ditolak.
- **Work Location wajib terjadwal** — otomatis di-resolve bila tidak dikirim (lihat bagian 6). Pada overtime (1 hari), bila ada 2 slot lokasi beda jam maka dipakai **slot pertama** (K2).
- **Employee hanya bisa mengajukan untuk dirinya sendiri** (`employee_id` selalu dari session). Hanya user dengan role Presenly **HR** atau **Administrator** yang boleh memilih employee lain (via web).
- Approval memakai **Presenly Approval Journey** yang sama (level berurutan, approver aktif, alasan reject wajib).

State Presenly: `draft → submitted → approved / rejected`, dan `cancelled` dari draft/submitted.

---

## 2. Daftar Endpoint

| Fungsi | Method | Endpoint |
|---|---|---|
| **Buat + submit pengajuan** | POST | `/api/presenly/v1/overtime/requests` |
| Daftar request milik saya | POST | `/api/presenly/v1/overtime/requests/list` |
| **Antrean approval saya** | POST | `/api/presenly/v1/overtime/requests/approval` |
| **Approve level aktif** | POST | `/api/presenly/v1/overtime/requests/<id>/approve` |
| **Reject level aktif** | POST | `/api/presenly/v1/overtime/requests/<id>/reject` |
| **Cancel request** | POST | `/api/presenly/v1/overtime/requests/<id>/cancel` |
| Check user bisa approve/reject/cancel | POST | `/api/presenly/v1/overtime/requests/<id>/can-approve` |
| Check batch (banyak request) | POST | `/api/presenly/v1/overtime/requests/can-approve/batch` |
| Preview lokasi otomatis hari itu | POST | `/api/presenly/v1/overtime/requests/location-options` |

Semua menggunakan JSON-RPC (data di `params`), auth session, dan envelope `{success, data, error}`.

---

## 3. Format JSON-RPC

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": { },
  "id": 1
}
```

Response bisnis berhasil:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { "success": true, "data": { }, "error": null }
}
```

Client wajib memeriksa: tidak ada `error` **dan** `result.success === true`; gunakan hanya `result.data`.

---

## 4. Buat + Submit Pengajuan

```http
POST /api/presenly/v1/overtime/requests
```

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "date": "2026-09-10",
    "hour_from": 18.0,
    "hour_to": 22.0,
    "work_location_id": 7,
    "reason": "Server maintenance"
  },
  "id": 20
}
```

| Field | Tipe | Wajib | Keterangan |
|---|---|---:|---|
| `date` | date `YYYY-MM-DD` | Ya | Hari lembur (harus ada attendance bukti hari itu). |
| `hour_from` | number/string | Ya | Jam mulai 24H: `18`, `18.5`, atau `"18:30"`. |
| `hour_to` | number/string | Ya | Jam selesai 24H; harus `0 <= from < to <= 24`. |
| `work_location_id` | integer | Tidak | Lokasi terjadwal. Kosong → auto-resolve. |
| `reason` | string | Tidak | Alasan. |

Catatan:
- `employee_id` **tidak boleh dikirim** — selalu dari session.
- `date_from` diterima sebagai alias `date` (legacy).
- `unit_id` diterima sebagai alias `work_location_id` (legacy).

Server menolak bila:
- `hour_from`/`hour_to` hilang, bukan angka/`HH:MM` valid, atau `hour_from >= hour_to` (atau di luar 0–24);
- tidak ada bukti `hr.attendance` pada `date`;
- sudah ada pengajuan lain pada `date` yang sama;
- tidak ada route approval overtime (`is_overtime_route`) lengkap;
- lokasi tidak terjadwal (atau ambiguous multi-lokasi, bila dikirim eksplisit harus valid).

### Response berhasil

```json
{
  "jsonrpc": "2.0",
  "id": 20,
  "result": {
    "success": true,
    "data": {
      "id": 5,
      "name": "OT/2026/00005",
      "employee_id": 42,
      "company_id": 6,
      "work_location_id": 7,
      "date": "2026-09-10",
      "hour_from": 18.0,
      "hour_to": 22.0,
      "duration_hours": 4.0,
      "reason": "Server maintenance",
      "has_attendance_evidence": true,
      "state": "submitted",
      "approval_level": 0,
      "approval_progress": "Level 1 of 1",
      "current_approvers": [ { "id": 5, "name": "Manager User" } ],
      "approval_steps": [
        {
          "level": 1,
          "name": "Overtime Review",
          "state": "pending",
          "approver_ids": [5],
          "decision_by": false,
          "decision_date": false,
          "decision_note": false
        }
      ],
      "rejection_reason": false
    },
    "error": null
  }
}
```

Catatan serializer:
- `duration_hours` dihitung server (`hour_to - hour_from`).
- `date`, `hour_from`, `hour_to` = input yang disimpan.
- `has_attendance_evidence` = apakah ada `hr.attendance` pada `date`.

---

## 5. List & Status

### 5.1 Daftar milik saya

```http
POST /api/presenly/v1/overtime/requests/list
```

`params: {}` → `data: [serialized requests]` milik employee login (max 100, `create_date desc`). Gunakan untuk layar "Riwayat/Status" dan konfirmasi setelah timeout.

### 5.2 Antrean approval

```http
POST /api/presenly/v1/overtime/requests/approval
```

`params: {}`. Hanya request `state == submitted` yang menempatkan user login pada level aktif yang muncul (max 100).

---

## 6. Approve / Reject / Cancel

### 6.1 Approve

```http
POST /api/presenly/v1/overtime/requests/<id>/approve
```

`params: {}`. Approver level aktif menyetujui. Level final → `state: approved`, `approval_progress: Completed (N/N)`, `current_approvers: []`.

### 6.2 Reject

```http
POST /api/presenly/v1/overtime/requests/<id>/reject
```

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": { "reason": "Melebihi batas jam lembur" },
  "id": 21
}
```

`reason` **wajib** — server menolak bila kosong. Hasil `state: rejected` + `rejection_reason`, seluruh journey dihentikan.

### 6.3 Cancel

```http
POST /api/presenly/v1/overtime/requests/<id>/cancel
```

`params: {}`. Owner/HR/Administrator dapat membatalkan saat `draft`/`submitted`; approval journey ikut ditutup (`cancelled`).

### 6.4 Aturan umum

- Hanya approver level aktif yang berwenang; lainnya menerima error validasi.
- Request yang sudah final / tidak `submitted` ditolak.
- Jangan mengulang approve/reject setelah status berubah (lihat Idempotensi).

---

## 7. Work Location Otomatis

Policy mengikuti `PLAN_AUTO_WORK_LOCATION.md` (sama dengan Time Off):

- Bila `work_location_id` tidak dikirim, server memakai `_presenly_resolve_period_location(date, date)`:
  - 1 lokasi terjadwal → auto-isi, lanjut.
  - >1 slot beda jam pada hari itu → **slot pertama** (K2) dipakai.
  - Tidak ada lokasi → tolak.
- Bila dikirim → divalidasi harus termasuk lokasi terjadwal pada `date`.
- `POST /overtime/requests/location-options` dengan `params: { "date": "2026-09-10" }` memberi preview:

```json
{
  "success": true,
  "data": {
    "unique": true,
    "location_id": 7,
    "locations": [ { "id": 7, "name": "Kantor Gresik" } ],
    "by_date": { "2026-09-10": { "id": 7, "name": "Kantor Gresik" } }
  }
}
```

---

## 8. Check Kemampuan (can-approve / can-reject / can-cancel)

- Single: `POST /overtime/requests/<id>/can-approve` → `data: { id, state, approval_progress, current_approvers, can_approve, can_reject, can_cancel }`.
- Batch: `POST /overtime/requests/can-approve/batch` dengan `params: { "ids": [5, 6] }` → `data: { items: [...], unreadable_ids: [...] }`.

`can_approve`/`can_reject` mengikuti level aktif; `can_cancel` mengikuti owner/HR/manager pada `draft`/`submitted`. Endpoint read-only, untuk men-disable tombol di UI mobile.

---

## 9. Validasi dan Pesan Error

| Kondisi | Perilaku mobile |
|---|---|
| Session expired | Hapus cookie; kembali ke login. |
| Tidak ada Employee aktif | Notifikasi "hubungi Administrator". |
| `date` hilang / tidak valid | Minta pilih hari. |
| `hour_from`/`hour_to` bukan 24H valid (0–24, from < to) | Perbaiki jam. |
| Tidak ada attendance pada hari tsb | Informasikan hari harus punya attendance. |
| Sudah ada pengajuan hari sama | Buka pengajuan yang sudah ada; blokir duplicate. |
| Route overtime belum dikonfigurasi | Notifikasi admin melengkapi Approval Route (Overtime Route). |
| Bukan approver level aktif / tidak pending | Refresh antrean; beri tahu tidak berwenang. |
| `reason` reject kosong | UI wajib minta alasan. |
| Work Location tidak terjadwal / ambiguous | Auto-resolve dulu; bila ambiguous tampilkan pilihan via `location-options`. |

Ambil pesan aman dari `error.data.message`; jangan tampilkan `error.data.debug`.

---

## 10. Idempotensi dan Retry

- Endpoint mutasi tidak menerima client timestamp / idempotency key.
- Disable tombol selama request berjalan; jangan kirim paralel.
- Setelah timeout: panggil `/overtime/requests/list` atau `/overtime/requests/approval`.
  - Jika `state` sudah berubah → jangan ulangi approve/reject.
  - Jika belum berubah → boleh retry sekali manual.
- Server melindungi state: approve kedua pada request final ditolak; create kedua pada hari sama ditolak.

---

## 11. Contoh Alur Lengkap

### A. Employee mengajukan lembur

```text
1. POST /web/session/authenticate                        (login employee)
2. POST /api/presenly/v1/overtime/requests/location-options   (opsional: cek lokasi)
       { date: "2026-09-10" }
3. POST /api/presenly/v1/overtime/requests
       { date, hour_from: 18, hour_to: 22, reason }
4. POST /api/presenly/v1/overtime/requests/list          (cek status: submitted)
5. POST /web/session/destroy
```

### B. Atasan menyetujui

```text
1. POST /web/session/authenticate                        (login approver)
2. POST /api/presenly/v1/overtime/requests/approval      (lihat antrean)
3. POST /api/presenly/v1/overtime/requests/can-approve/batch   { ids: [...] }
4. POST /api/presenly/v1/overtime/requests/<id>/approve  (setujui level aktif)
5. POST /api/presenly/v1/overtime/requests/<id>/reject   (atau tolak, selalu dgn reason)
       { reason: "..." }
6. POST /web/session/destroy
```

---

## 12. Checklist Implementasi Mobile

- [ ] Kirim `date` (`YYYY-MM-DD`) + `hour_from`/`hour_to` dalam **jam 24H** (float atau `HH:MM`).
- [ ] Jangan kirim `duration_hours` — selalu dihitung server.
- [ ] `work_location_id` boleh kosong — server auto-resolve; pakai `location-options` untuk preview.
- [ ] `employee_id` tidak pernah dikirim (selalu session).
- [ ] Blokir submit bila `has_attendance_evidence` false (server tetap memvalidasi).
- [ ] Cek `can-approve` sebelum menampilkan tombol Approve/Reject/Cancel.
- [ ] Reject selalu menyertakan `reason`.
- [ ] Periksa `error` dan `result.success` pada setiap response.
- [ ] Mutasi tidak dikirim paralel; timeout diselesaikan dengan cek ulang via `list`/`approval`.
- [ ] Tidak log password, cookie, selfie, atau data pribadi lainnya.