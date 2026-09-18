# Presenly Mobile API — Approval & Pengajuan (Time Off + Permission)

Dokumen ini adalah **referensi implementasi mobile** untuk:

- List approval untuk **atasan/approver** (antrean keputusan pada level aktif).
- Endpoint **approve / reject**.
- **Pengajuan Time Off** (`hr.leave`) dan **Permission** (`presenly.permission`).

Autentikasi session, format JSON-RPC, login/logout, dan penanganan error umum: lihat [`MOBILE_API.md`](MOBILE_API.md).
Dokumentasi khusus detail field Time Off: [`MOBILE_TIMEOFF_API.md`](MOBILE_TIMEOFF_API.md).

> Catatan versi: kontrak di bawah mencerminkan **kode saat ini di `presenly` 19.0.13.6.0**, termasuk endpoint **can-approve** (check kemampuan user untuk approve/reject/cancel) yang aktif sejak 2026-09-06. Rencana perluasan lanjutan (detail per-ID, cancel, balance, unified queue) ada di [`PLAN_APPROVAL_API.md`](PLAN_APPROVAL_API.md).

---

## 1. Konsep Approval Presenly

- Semua request melewati **satu Approval Journey** (`presenly.approval.request`) berisi langkah berurutan (`presenly.approval.step`).
- Saat submit, seluruh level + assigned approvers **disnapshot** dan menjadi immutable.
- Hanya **approver pada level aktif** yang bisa approve/reject.
- **Approve** memindahkan ke level berikutnya; approve level **final** menyelesaikan request:
  - Time Off → native `state` menjadi `validate`.
  - Permission → `state` menjadi `approved`.
- **Reject wajib alasan** dan menghentikan seluruh journey.
- Field status penting dalam setiap serialisasi:

| Field | Arti |
|---|---|
| `state` | Status native Odoo: `draft/confirm/validate/refuse/cancel` (Time Off), `draft/submitted/approved/rejected/cancelled` (Permission) |
| `approval_state` | Status journey Presenly: `not_started/pending/approved/rejected/cancelled` (Time Off) |
| `approval_level` | Level yang sedang/sudah berjalan (0 = belum mulai) |
| `approval_progress` | Teks human-readable, contoh `Level 1 of 3`, `Completed (3/3)` |
| `current_approvers` | Daftar user yang sedang ditunggu keputusannya |
| `approval_steps` | Snapshot seluruh level dengan decision_by/date/note |

---

## 2. Daftar Endpoint

### 2.1 Time Off (`hr.leave`)

| Fungsi | Method | Endpoint |
|---|---|---|
| Daftar Time Off Type | POST | `/api/presenly/v1/leave/types` |
| **Buat + submit pengajuan Time Off** | POST | `/api/presenly/v1/leaves` |
| Daftar request milik saya | POST | `/api/presenly/v1/leaves/list` |
| **Antrean approval saya** | POST | `/api/presenly/v1/leaves/approval` |
| **Approve level aktif** | POST | `/api/presenly/v1/leaves/<id>/approve` |
| **Reject level aktif** | POST | `/api/presenly/v1/leaves/<id>/reject` |
| **Check user bisa approve/reject/cancel** | POST | `/api/presenly/v1/leaves/<id>/can-approve` |
| **Check batch (banyak request)** | POST | `/api/presenly/v1/leaves/can-approve/batch` |

### 2.2 Permission (`presenly.permission`)

| Fungsi | Method | Endpoint |
|---|---|---|
| Daftar Permission Type | POST | `/api/presenly/v1/permissions/types` |
| **Buat + submit pengajuan Permission** | POST | `/api/presenly/v1/permissions` |
| Daftar request milik saya (kanonik) | POST | `/api/presenly/v1/permissions/list` |
| Daftar request milik saya (alias) | GET | `/api/presenly/v1/permissions` |
| **Antrean approval saya** | POST | `/api/presenly/v1/permissions/approval` |
| **Approve level aktif** | POST | `/api/presenly/v1/permissions/<id>/approve` |
| **Reject level aktif** | POST | `/api/presenly/v1/permissions/<id>/reject` |
| **Check user bisa approve/reject/cancel** | POST | `/api/presenly/v1/permissions/<id>/can-approve` |
| **Check batch (banyak request)** | POST | `/api/presenly/v1/permissions/can-approve/batch` |

---

## 3. Format JSON-RPC (ringkas)

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": { },
  "id": 1
}
```

- Data request diletakkan **langsung** di `params` (tanpa key `payload`/`data`).
- Endpoint `<id>/approve` dan `<id>/reject` memakai path parameter; body hanya dipakai reject untuk `reason`.
- Endpoint `<id>/can-approve` dan `can-approve/batch` adalah **read-only** (tidak ada mutasi); untuk batch, kirim daftar ID pada `params.ids`.
- Response bisnis:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { "success": true, "data": { }, "error": null }
}
```

Client wajib memeriksa: tidak ada `error` **dan** `result.success === true`; gunakan hanya `result.data`.

---

## 4. Pengajuan Time Off

### 4.1 Daftar Time Off Type

```http
POST /api/presenly/v1/leave/types
```

`params: {}` → `data: [{id, name}]`. Hanya tipe `active` dan berlaku untuk company employee (global atau company yang sama).

### 4.2 Membuat pengajuan (create + submit otomatis)

```http
POST /api/presenly/v1/leaves
```

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

| Field | Tipe | Wajib | Keterangan |
|---|---|---:|---|
| `leave_type_id` | integer | Ya | ID dari `/leave/types`. |
| `work_location_id` | integer | Ya | Work Location yang **terjadwal** untuk employee pada periode request. |
| `date_from` | date `YYYY-MM-DD` | Ya | Tanggal mulai. |
| `date_to` | date | Tidak | Tanggal selesai; default = `date_from`. |
| `reason` | string | Tidak | Alasan/nama request. |

`unit_id` masih diterima sebagai alias `work_location_id` (client baru wajib memakai `work_location_id`).

Server melakukan:

1. Validasi employee aktif, type valid untuk company, work location terjadwal pada periode, route approval lengkap.
2. Membuat `hr.leave` (state awal).
3. `action_presenly_submit()` → membuat Approval Journey dan langsung `presenly_approval_state = pending`.

`employee_id` **tidak boleh dikirim** client — selalu berasal dari session.

Response berhasil (contoh):

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
      "current_approvers": [ { "id": 5, "name": "Manager User" } ],
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

---

## 5. Pengajuan Permission

### 5.1 Daftar Permission Type

```http
POST /api/presenly/v1/permissions/types
```

`params: {}` → `data: [{id, name, code, requires_attachment}]`. Hanya tipe aktif dan `is_complete` untuk company employee.

### 5.2 Membuat pengajuan (create + submit otomatis)

```http
POST /api/presenly/v1/permissions
```

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "permission_type_id": 3,
    "work_location_id": 7,
    "request_mode": "full_day",
    "date_from": "2026-09-11",
    "date_to": "2026-09-11",
    "hour_from": 0,
    "hour_to": 0,
    "reason": "Emergency errand",
    "attachments": [
      { "name": "support.jpg", "data": "BASE64...", "mimetype": "image/jpeg" }
    ]
  },
  "id": 4
}
```

| Field | Tipe | Wajib | Keterangan |
|---|---|---:|---|
| `permission_type_id` | integer | Ya | ID dari `/permissions/types`. |
| `work_location_id` | integer | Ya | Work Location terjadwal pada periode. |
| `request_mode` | string | Tidak | `full_day` atau `hours`; harus sesuai tipe (`full_day`/`hours`/`both`). |
| `date_from` | date | Ya | Tanggal mulai. |
| `date_to` | date | Tidak | Tanggal selesai; default = `date_from`. |
| `hour_from` | number | Tergantung | Wajib valid bila `request_mode = hours` (`0 <= hour_from < hour_to <= 24`). |
| `hour_to` | number | Tergantung | Lihat di atas. |
| `reason` | string | Ya | Alasan wajib. |
| `attachments` | array | Tergantung | Wajib bila tipe `requires_attachment`. Tiap item `{name, data(base64), mimetype?}`, max 10 MB/item, disimpan private. |

Validasi server mencakup: kelengkapan field, mode sesuai tipe, work location terjadwal, tidak overlap dengan permission lain (`submitted`/`approved`) dalam periode, route approval lengkap, dan lampiran bila diwajibkan.

Response berhasil mengembalikan serializer permission termasuk `permission_type`, `hour_from/to`, `reason`, `affects_attendance`, `paid_status`, `attachments` (metadata), `approval_steps`, `rejection_reason`.

---

## 6. List Approval Untuk Atasan

### 6.1 Antrean Time Off

```http
POST /api/presenly/v1/leaves/approval
```

`params: {}` → `data: [serialized leaves]`.

Hanya request dengan:
- `presenly_approval_state == pending`;
- **user login termasuk `current_approvers`** pada level aktif;

yang muncul. Maksimum 100, urut `create_date desc`.

### 6.2 Antrean Permission

```http
POST /api/presenly/v1/permissions/approval
```

`params: {}` → `data: [serialized permissions]`.

Hanya request dengan:
- `state == submitted`;
- user login termasuk `_presenly_pending_approver_users()` pada level aktif;

yang muncul. Maksimum 100, urut `create_date desc`.

### 6.3 Antrean milik saya (non-approval)

- Time Off: `POST /leaves/list`
- Permission: `POST /permissions/list` (kanonik); `GET /permissions` tetap berfungsi sebagai alias untuk kompatibilitas client lama

Keduanya mengembalikan maksimum 100 request milik employee login, urut `create_date desc`. Gunakan untuk layar "Riwayat/Status" dan untuk konfirmasi status setelah timeout.

---

## 7. Approve / Reject

### 7.1 Approve Time Off

```http
POST /api/presenly/v1/leaves/<leave_id>/approve
```

`params: {}`. Server memvalidasi user adalah approver level aktif; jika level final, native Time Off divalidasi (`state: validate`, `approval_state: approved`).

```json
{
  "result": {
    "success": true,
    "data": {
      "id": 44,
      "state": "validate",
      "approval_state": "approved",
      "approval_level": 1,
      "approval_progress": "Completed (1/1)",
      "current_approvers": []
    },
    "error": null
  }
}
```

### 7.2 Reject Time Off

```http
POST /api/presenly/v1/leaves/<leave_id>/reject
```

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": { "reason": "Needs rescheduling" },
  "id": 7
}
```

`reason` **wajib** — server menolak bila kosong. Hasil `state: refuse`, `approval_state: rejected`, `rejection_reason` terisi; seluruh journey dihentikan.

### 7.3 Approve Permission

```http
POST /api/presenly/v1/permissions/<permission_id>/approve
```

`params: {}`. Level aktif di-approve; level final menjadikan `state: approved` dengan `current_approvers` kosong.

### 7.4 Reject Permission

```http
POST /api/presenly/v1/permissions/<permission_id>/reject
```

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": { "reason": "Missing attachment" },
  "id": 8
}
```

`reason` wajib. Hasil `state: rejected`, `rejection_reason` terisi, journey dihentikan.

### 7.5 Aturan umum

- Hanya approver level aktif yang berwenang; lainnya menerima error validasi.
- Request yang sudah diproses / tidak pending ditolak.
- Jangan mengulang approve/reject setelah status berubah (lihat Idempotensi).

---

## 8. Check Kemampuan User (can-approve / can-reject / can-cancel)

Digunakan oleh **menu mobile** untuk menampilkan / men-disable tombol **Approve**, **Reject**, dan **Cancel** sesuai hak user login pada request tersebut — tanpa perlu mencoba mutasi dulu.

- **Read-only**: tidak mengubah state apa pun.
- `can_approve` / `can_reject` mengikuti **level approval yang aktif**: hanya `true` bila user login termasuk approver pada level tersebut.
- `can_cancel` mengikuti kepemilikan/manager: employee pemilik (atau manager) dapat cancel saat request belum final. Khusus Time Off, cancel hanya `true` saat `presenly_approval_state` adalah `not_started`/`pending`.
- Bila request sudah final (approved/rejected/cancelled), ketiganya `false` — tombol dinonaktifkan.
- ID yang tidak dapat diakses user (di luar allowed company / record rules) **tidak** ditampilkan pada `items`; dimasukkan ke `unreadable_ids`.

### 8.1 Cek satu Time Off

```http
POST /api/presenly/v1/leaves/<leave_id>/can-approve
```

`params: {}`

Contoh response saat user adalah approver level aktif:

```json
{
  "jsonrpc": "2.0",
  "id": 9,
  "result": {
    "success": true,
    "data": {
      "id": 44,
      "approval_state": "pending",
      "approval_progress": "Level 1 of 2",
      "current_approvers": [ { "id": 5, "name": "Manager User" } ],
      "can_approve": true,
      "can_reject": true,
      "can_cancel": false
    },
    "error": null
  }
}
```

### 8.2 Cek satu Permission

```http
POST /api/presenly/v1/permissions/<permission_id>/can-approve
```

`params: {}`

Contoh response saat user adalah **pemilik** request (bukan approver):

```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "success": true,
    "data": {
      "id": 77,
      "state": "submitted",
      "approval_progress": "Level 1 of 1",
      "current_approvers": [ { "id": 5, "name": "Manager User" } ],
      "can_approve": false,
      "can_reject": false,
      "can_cancel": true
    },
    "error": null
  }
}
```

### 8.3 Cek batch Time Off

```http
POST /api/presenly/v1/leaves/can-approve/batch
```

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": { "ids": [44, 45] },
  "id": 11
}
```

Contoh response:

```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "result": {
    "success": true,
    "data": {
      "items": [
        {
          "id": 44,
          "approval_state": "pending",
          "approval_progress": "Level 1 of 2",
          "current_approvers": [ { "id": 5, "name": "Manager User" } ],
          "can_approve": true,
          "can_reject": true,
          "can_cancel": false
        }
      ],
      "unreadable_ids": [45]
    },
    "error": null
  }
}
```

`ids` wajib berupa array non-kosong berisi integer. Nilai non-numerik ditolak dengan error validasi.

### 8.4 Cek batch Permission

```http
POST /api/presenly/v1/permissions/can-approve/batch
```

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": { "ids": [77, 78] },
  "id": 12
}
```

Response serupa dengan Time Off (field `state` menggantikan `approval_state`), plus array `unreadable_ids`.

---

## 9. Status dan Approval Journey (panduan UI)

Untuk setiap item pada antrean/list, tampilkan:

- `approval_progress` → teks progress.
- `current_approvers` → siapa yang sedang ditunggu (untuk employee: menampilkan; untuk approver: verifikasi diri sendiri).
- `approval_steps[]` → snapshot level dengan `state` tiap langkah (`waiting/pending/approved/rejected/cancelled`), `decision_by`, `decision_date`, `decision_note`.
- `rejection_reason` → tampilkan bila ada.

Mapping UI yang disarankan:

| `approval_state` / `state` | Gaya |
|---|---|
| `not_started` / `draft` | Draft / belum submit |
| `pending` / `submitted` | Menunggu approval |
| `approved` / `validate`–`approved` | Disetujui |
| `rejected` / `refuse`–`rejected` | Ditolak (tampilkan alasan) |
| `cancelled` / `cancel`–`cancelled` | Dibatalkan |

---

## 10. Validasi dan Pesan Error

Error bisnis muncul di JSON-RPC `error.data.message`.

| Kondisi | Perilaku mobile |
|---|---|
| Session expired | Hapus cookie; kembali ke login. |
| Tidak ada Employee aktif | Notifikasi "hubungi Administrator". |
| Type/Tipe tidak valid atau beda company | Muat ulang type list. |
| Work Location tidak terjadwal pada periode | Muat ulang pilihan lokasi. |
| Route approval kosong/ambigu | Notifikasi admin perlu melengkapi route. |
| Approver tidak punya role Presenly Approver | Notifikasi admin (server menolak submit). |
| Bukan approver level aktif / request tidak pending | Refresh antrean; beri tahu tidak berwenang. |
| `reason` reject kosong | UI wajib minta alasan. |
| Permission mode tidak sesuai tipe | Perbaiki mode siang sebelum submit. |
| Attachment wajib tidak ada / > 10 MB / base64 invalid | Validasi lokal sebelum kirim. |
| Overlap permission aktif | Beri tahu periode bentrok. |

Contoh parser respons:

```javascript
function parsePresenlyResponse(body) {
  if (body.error) {
    throw new Error(body.error?.data?.message || body.error.message || 'Request gagal');
  }
  if (!body.result?.success) {
    throw new Error(body.result?.error || 'Request gagal');
  }
  return body.result.data;
}
```

Jangan menampilkan `error.data.debug` ke pengguna.

---

## 11. Idempotensi dan Retry

- Endpoint mutasi tidak menerima client timestamp dan belum punya idempotency key.
- Disable tombol selama request berjalan; jangan kirim paralel.
- Setelah timeout: panggil endpoint list (`/leaves/list`, `/permissions`, atau antrean approval).
  - Jika `approval_state`/`state` sudah berubah → jangan ulangi approve/reject.
  - Jika belum berubah → boleh retry sekali manual.
- Server melindungi state sendiri: approve kedua pada request yang sudah final ditolak.
- Untuk layar yang menampilkan tombol berdasarkan hak, panggil ulang endpoint `can-approve` (single/batch, read-only) — tidak perlu menebak dari cache.

---

## 12. Contoh Alur Lengkap

### A. Employee mengajukan Time Off lalu mengecek status

```text
1. POST /web/session/authenticate                     (login employee)
2. POST /api/presenly/v1/leave/types                  (pilih tipe)
3. POST /api/presenly/v1/leaves                       (submit pengajuan)
       { leave_type_id, work_location_id, date_from, date_to, reason }
4. POST /api/presenly/v1/leaves/list                  (cek status: pending)
5. POST /web/session/destroy
```

### B. Atasan menyetujui antrean

```text
1. POST /web/session/authenticate                     (login approver)
2. POST /api/presenly/v1/leaves/approval              (lihat antrean Time Off)
3. POST /api/presenly/v1/leaves/can-approve/batch     (opsional: cek tombol per-item) { ids: [...] }
4. POST /api/presenly/v1/leaves/<id>/approve          (setujui level aktif)
5. (ulang dari langkah 2 bila masih ada level berikutnya / request lain)
6. POST /api/presenly/v1/permissions/approval         (lihat antrean Permission)
7. POST /api/presenly/v1/permissions/<id>/reject      (contoh: tolak dengan alasan)
       { reason: "..." }
8. POST /web/session/destroy
```

---

## 13. Checklist Implementasi Mobile

- [ ] Semua request JSON-RPC, data langsung di `params`.
- [ ] Login memeriksa `result.uid`; cookie `session_id` dipakai pada semua request.
- [ ] Submission:
  - Time Off: `leave_type_id`, `work_location_id`, `date_from`, `date_to`, `reason`.
  - Permission: `permission_type_id`, `work_location_id`, `request_mode`, tanggal/jam, `reason`, `attachments` bila diperlukan.
- [ ] `employee_id` tidak pernah dikirim client.
- [ ] Antrean approver memakai `/leaves/approval` dan `/permissions/approval`.
- [ ] Approve/reject memakai path `id`; reject selalu menyertakan `reason`.
- [ ] Hak tombol diverifikasi via `<id>/can-approve` (atau `can-approve/batch`) sebelum menampilkan/enable Approve/Reject/Cancel.
- [ ] UI menampilkan `approval_progress`, `current_approvers`, dan alasan reject.
- [ ] Setiap response memeriksa `error` dan `result.success`.
- [ ] Mutasi tidak dikirim paralel; timeout diselesaikan dengan cek ulang.
- [ ] Attachment base64 tanpa prefix data URL, max 10 MB per item.
- [ ] Tidak log password, cookie, selfie, atau data attachment pribadi.