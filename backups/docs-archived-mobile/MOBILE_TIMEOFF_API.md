# Presenly Mobile API — Time Off (Cuti)

Dokumen ini adalah referensi API mobile untuk **Time Off (`hr.leave`)** dengan jalur approval Presenly. Untuk autentikasi session, format JSON-RPC, login, logout, dan penanganan error umum, lihat [`MOBILE_API.md`](MOBILE_API.md).

## 1. Konsep Time Off Presenly

Time Off tetap memakai model native Odoo 19 `hr.leave` sebagai mesin transaksi final (alokasi, entri kalender sumber daya, durasi, work entry).

Presenly mengatur **jalur approval** di atasnya:

- Setiap submission membuat immutable **Approval Journey** snapshot.
- Approval berjalan **level-per-level** menggunakan konfigurasi **Approval Routes** Presenly.
- Native validation (`_action_validate`) hanya dipanggil ketika **level final selesai di-approve**.
- Sebelum journey selesai, native `state` hanya berubah ke status workflow internal, bukan `validate`.

Aturan inti:

- Identitas employee berasal dari session; `employee_id` tidak boleh dikirim client.
- Server menentukan status dan snapshot approval; client hanya mengirim data request.
- Native Time Off approval tidak dapat mem-bypass Presenly.

## 2. Endpoint

| Fungsi | Method | Endpoint | Auth |
|---|---|---|---|
| Daftar Time Off Type | POST | `/api/presenly/v1/leave/types` | Session |
| Buat + submit request | POST | `/api/presenly/v1/leaves` | Session |
| Daftar request milik saya | POST | `/api/presenly/v1/leaves/list` | Session |
| Antrean approval saya | POST | `/api/presenly/v1/leaves/approval` | Session |
| Approve level aktif | POST | `/api/presenly/v1/leaves/<id>/approve` | Session |
| Reject level aktif | POST | `/api/presenly/v1/leaves/<id>/reject` | Session |

Semua endpoint kecuali `approve`/`reject` boleh dipanggil tanpa body tambahan. Endpoint `approve`/`reject` memakai path parameter untuk `leave_id` dan body `params` untuk data tambahan.

## 3. Format JSON-RPC

Request standar:

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 1
}
```

Data request diletakkan langsung di object `params`. Jangan dibungkus key `payload` atau `data`.

Response bisnis berhasil:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": true,
    "data": {},
    "error": null
  }
}
```

Error dikirim pada properti JSON-RPC `error`. Client wajib memeriksa:

1. `error` tidak ada.
2. `result.success === true`.
3. Gunakan hanya `result.data`.

## 4. Daftar Time Off Type

### Endpoint

```http
POST /api/presenly/v1/leave/types
```

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 2
}
```

### Response

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "success": true,
    "data": [
      { "id": 1, "name": "Paid Time Off" },
      { "id": 2, "name": "Sick Time Off" }
    ],
    "error": null
  }
}
```

Type yang dikembalikan hanya:

- `company_id == False` (global); atau
- `company_id` sama dengan perusahaan employee;
- dan `active == True`.

## 5. Buat dan submit request Time Off

### Endpoint

```http
POST /api/presenly/v1/leaves
```

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "leave_type_id": 1,
    "work_location_id": 7,
    "date_from": "2026-09-10",
    "date_to": "2026-09-10",
    "reason": "Family event"
  },
  "id": 3
}
```

### Field request

| Field | Tipe | Wajib | Keterangan |
|---|---|---:|---|
| `leave_type_id` | integer | Ya | ID dari `/leave/types`. |
| `work_location_id` | integer | Ya | Work Location yang terjadwal untuk employee pada periode request. |
| `date_from` | date string | Ya | Tanggal mulai dalam format `YYYY-MM-DD`. |
| `date_to` | date string | Tidak | Tanggal selesai. Default sama dengan `date_from`. |
| `reason` | string | Tidak | Nama/alasan request. |

`unit_id` masih diterima sementara sebagai alias lama untuk `work_location_id`, tetapi client baru harus memakai `work_location_id`.

### Validasi sebelum submit

Server akan menolak bila:

- employee tidak aktif;
- Type tidak valid atau beda perusahaan;
- `work_location_id` tidak terjadwal untuk employee pada periode tersebut;
- tidak ada Approval Route lengkap untuk type/lokasi tersebut.

Setelah validasi lulus, server:

1. Membuat `hr.leave` dengan state awal.
2. Menjalankan `action_presenly_submit()`.
3. Membuat Approval Journey snapshot dan membekukan level/approver.

### Response berhasil

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "success": true,
    "data": {
      "id": 44,
      "name": "Family event",
      "employee_id": 42,
      "company_id": 6,
      "leave_type_id": 1,
      "leave_type": "Paid Time Off",
      "work_location_id": 7,
      "unit_id": 7,
      "date_from": "2026-09-10",
      "date_to": "2026-09-10",
      "number_of_days": 1.0,
      "state": "confirm",
      "approval_state": "pending",
      "approval_level": 0,
      "approval_progress": "Level 1 of 1",
      "current_approvers": [
        { "id": 5, "name": "Manager User" }
      ],
      "approval_steps": [
        {
          "level": 1,
          "name": "Manager Review",
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

Catatan field status:

- `state` adalah status native `hr.leave` (`confirm`, `validate`, `refuse`, `cancel`).
- `approval_state` adalah status workflow Presenly (`not_started`, `pending`, `approved`, `rejected`, `cancelled`).
- `approval_progress` menunjukkan level berjalan, misalnya `Level 1 of 3`.

## 6. Daftar request milik saya

### Endpoint

```http
POST /api/presenly/v1/leaves/list
```

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 4
}
```

### Response

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "success": true,
    "data": [ { "...same serialized leave..." } ],
    "error": null
  }
}
```

Mengembalikan maksimum 100 request milik employee yang sedang login.

## 7. Antrean approval saya

### Endpoint

```http
POST /api/presenly/v1/leaves/approval
```

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 5
}
```

### Response

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "result": {
    "success": true,
    "data": [ { "...pending request where current user is approver..." } ],
    "error": null
  }
}
```

Hanya request `presenly_approval_state == pending` yang menempatkan user login sebagai `current_approver` yang muncul.

## 8. Approve level aktif

### Endpoint

```http
POST /api/presenly/v1/leaves/<leave_id>/approve
```

Path `<leave_id>` adalah ID request.

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 6
}
```

### Behavior

- Hanya approver pada level aktif yang bisa memproses.
- Jika masih ada level berikutnya, request pindah ke level berikutnya.
- Jika ini level final, `approval_state` menjadi `approved` dan native `state` menjadi `validate`.

### Response saat pindah ke level berikutnya

```json
{
  "result": {
    "success": true,
    "data": {
      "id": 44,
      "state": "confirm",
      "approval_state": "pending",
      "approval_level": 1,
      "approval_progress": "Level 2 of 3",
      "current_approvers": [ { "id": 6, "name": "HR Approver" } ]
    },
    "error": null
  }
}
```

### Response saat final

```json
{
  "result": {
    "success": true,
    "data": {
      "id": 44,
      "state": "validate",
      "approval_state": "approved",
      "approval_level": 3,
      "approval_progress": "Completed (3/3)",
      "current_approvers": []
    },
    "error": null
  }
}
```

## 9. Reject level aktif

### Endpoint

```http
POST /api/presenly/v1/leaves/<leave_id>/reject
```

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "reason": "Needs rescheduling"
  },
  "id": 7
}
```

`reason` wajib diisi; jika kosong server menolak.

### Response

```json
{
  "result": {
    "success": true,
    "data": {
      "id": 44,
      "state": "refuse",
      "approval_state": "rejected",
      "rejection_reason": "Needs rescheduling"
    },
    "error": null
  }
}
```

## 10. Alur leveling approval Presenly

Urutan eksekusi approval ditentukan oleh **Approval Routes** (`presenly.approval.rule`):

1. Route diambil per Company + Type (Time Off Type) + Work Location.
2. Step dinormalisasi berdasarkan `Order` (10, 20, 30, …).
3. Step location-specific menggantikan step company-wide pada Order yang sama.
4. Masing-masing step menghasilkan `approvers` sesuai `approver_type`:
   - Employee Manager
   - Work Location Manager
   - HR Officer
   - Specific User
   - Odoo Group
5. Approval Journey menyimpan snapshot step dan assigned users pada waktu submit.
6. User memproses step aktif lewat `approve` atau `reject`.
7. Native `_action_validate` hanya dieksekusi saat step terakhir selesai.

Jadi route Presenly memutuskan siapa yang menyetujui dan berapa level. Mobile tidak perlu tahu aturan internal; cukup ikuti `approval_progress` dan `current_approvers`.

## 11. Validasi dan pesan error

| Kondisi | Perilaku mobile |
|---|---|
| Session expired | Hapus cookie, kembali ke login. |
| Tidak ada Employee aktif | Instruksikan menghubungi Administrator. |
| Type tidak valid / beda company | Refresh type list dan gunakan ID yang benar. |
| Work Location tidak terjadwal | Refresh dan pilih lokasi dari periode tersebut. |
| Approval Route kosong/incomplete | Hubungi Administrator untuk melengkapi Approval Routes. |
| Approver tidak punya role Presenly Approver | Konfigurasi server; hubungi Administrator. |
| Bukan approver level aktif | Tampilkan bahwa user tidak berwenang. |
| `reason` reject kosong | Minta alasan wajib. |
| Request sudah diproses / tidak pending | Refresh antrean. |

Pesan aman diambil dari `error.data.message`.

## 12. Idempotensi dan retry

- Disable tombol saat request berlangsung.
- Jangan kirim request paralel.
- Setelah timeout, panggil `/api/presenly/v1/leaves/list` atau `/api/presenly/v1/leaves/approval` untuk cek status.
- Jangan mengulang `approve`/`reject` jika status sudah berubah.

## 13. Contoh alur lengkap

```text
1. POST /web/session/authenticate
2. POST /api/presenly/v1/leave/types
3. POST /api/presenly/v1/leaves            (employee submit)
4. POST /api/presenly/v1/leaves/approval   (approver cek antrean)
5. POST /api/presenly/v1/leaves/<id>/approve  (approver proses level)
6. POST /api/presenly/v1/leaves/list       (employee cek status)
7. POST /web/session/destroy
```

## 14. Checklist implementasi mobile

- [ ] Semua request memakai JSON-RPC dan data pada `params`.
- [ ] Login memeriksa `result.uid`.
- [ ] Type list diambil dari `/leave/types`.
- [ ] Submit mengirim `leave_type_id`, `work_location_id`, `date_from`, `date_to`, `reason`.
- [ ] Daftar milik saya memakai `/leaves/list`.
- [ ] Antrean approval memakai `/leaves/approval`.
- [ ] Approve/reject memakai path `leave_id`.
- [ ] Reject selalu menyertakan `reason`.
- [ ] UI menampilkan `approval_progress` dan `current_approvers`.
- [ ] Periksa `error` dan `result.success` pada setiap response.
- [ ] Timeout diselesaikan dengan cek ulang, bukan retry membabi buta.