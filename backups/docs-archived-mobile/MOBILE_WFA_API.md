# Presenly Mobile API — Work From Anywhere (WFA)

Dokumen ini adalah referensi API khusus mode **Work From Anywhere (WFA)**. Untuk login, session, format JSON-RPC, GPS, selfie, idempotensi, dan penanganan error umum, lihat [`MOBILE_API.md`](MOBILE_API.md). Untuk pemilih mode On-Site vs WFA, lihat [`MOBILE_MODE_SELECTION.md`](MOBILE_MODE_SELECTION.md).

## 1. Konsep WFA

WFA adalah mode attendance yang mencatat bahwa karyawan bekerja dari lokasi bebas, bukan di Work Location terdaftar.

Pada versi ini WFA bersifat sementara dan **pencatatan saja**:

- tanpa geofence;
- tanpa batas lokasi, jarak, atau posisi;
- tanpa approval;
- Work Location tidak wajib;
- GPS opsional;
- **selfie check-in dan check-out tetap wajib** sebagai bukti.

WFA tetap memakai native `hr.attendance` sebagai sumber transaksi dan server sebagai pemilik identity serta waktu.

| Aspek | Ketentuan WFA |
|---|---|
| Geofence | Tidak digunakan |
| Work Location | Tidak wajib |
| Approval | Tidak |
| GPS (latitude/longitude/accuracy) | Opsional |
| Selfie check-in | Wajib |
| Selfie check-out | Wajib |
| Timestamp | Ditentukan server |
| Identitas Employee | Dari session, bukan dari client |

## 2. Endpoint

| Fungsi | Method | Endpoint | Auth |
|---|---|---|---|
| Daftar mode & policy | POST | `/api/presenly/v1/attendance/modes` | Session |
| Status presensi | POST | `/api/presenly/v1/attendance/status` | Session |
| Check-in WFA | POST | `/api/presenly/v1/attendance/check-in` | Session |
| Check-out WFA | POST | `/api/presenly/v1/attendance/check-out` | Session |

Semua endpoint menggunakan envelope JSON-RPC berikut:

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 1
}
```

Data diletakkan langsung pada object `params`, bukan dibungkus key `payload` atau `data`.

## 3. Response umum

Response bisnis berhasil:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": true,
    "data": { },
    "error": null
  }
}
```

Error validasi atau session dikirim pada properti JSON-RPC `error`. Client wajib memeriksa:

1. `error` tidak ada.
2. `result.success === true`.
3. Gunakan hanya `result.data`.

## 4. Daftar mode dan policy WFA

### Endpoint

```http
POST /api/presenly/v1/attendance/modes
```

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 7
}
```

### Response

```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "result": {
    "success": true,
    "data": {
      "employee_id": 42,
      "company_id": 6,
      "available_modes": [
        {
          "mode": "location",
          "label": "On-Site",
          "requires_gps": true,
          "requires_work_location": true,
          "requires_selfie": "per_location_policy"
        },
        {
          "mode": "wfa",
          "label": "Work From Anywhere",
          "requires_gps": false,
          "requires_work_location": false,
          "requires_selfie": true
        }
      ],
      "default_mode": "location",
      "wfa_policy": {
        "allowed": true,
        "approval_required": false,
        "geofence_required": false,
        "time_or_location_limit": false,
        "selfie_required": true
      }
    },
    "error": null
  }
}
```

Field WFA penting:

- `available_modes[].mode = "wfa"` menandakan mode tersedia.
- `wfa_policy.allowed` bernilai `true` bila WFA boleh dipilih.
- `wfa_policy.selfie_required` bernilai `true`; selfie check-in dan check-out wajib.
- `wfa_policy.geofence_required` bernilai `false`.
- `wfa_policy.approval_required` bernilai `false`.

## 5. Status WFA

### Endpoint

```http
POST /api/presenly/v1/attendance/status
```

### Response saat belum check-in dan WFA tersedia

```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "result": {
    "success": true,
    "data": {
      "state": "checked_out",
      "can_check_in": true,
      "can_check_out": false,
      "attendance_mode": false,
      "can_select_mode": true,
      "wfa_available": true,
      "available_work_locations": []
    },
    "error": null
  }
}
```

### Response saat sesi WFA aktif

```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "result": {
    "success": true,
    "data": {
      "state": "checked_in",
      "can_check_in": false,
      "can_check_out": true,
      "attendance_mode": "wfa",
      "attendance_id": 45,
      "check_in": "2026-09-06 08:15:20"
    },
    "error": null
  }
}
```

Interpretasi:

- `can_check_in` sudah memperhitungkan WFA; bisa `true` tanpa lokasi terjadwal.
- `attendance_mode` mengembalikan mode sesi aktif atau `false`.
- `wfa_available` menandakan WFA dapat dipilih saat ini.

## 6. Check-in WFA

### Endpoint

```http
POST /api/presenly/v1/attendance/check-in
```

### Request minimal (selfie wajib, tanpa GPS)

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "attendance_mode": "wfa",
    "selfie": "BASE64_IMAGE_WITHOUT_DATA_URL_PREFIX",
    "device_id": "OPTIONAL_STABLE_DEVICE_IDENTIFIER"
  },
  "id": 11
}
```

### Request dengan posisi opsional

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "attendance_mode": "wfa",
    "latitude": -7.16,
    "longitude": 112.64,
    "accuracy": 10.0,
    "selfie": "BASE64_IMAGE_WITHOUT_DATA_URL_PREFIX",
    "device_id": "OPTIONAL_STABLE_DEVICE_IDENTIFIER"
  },
  "id": 11
}
```

### Field request

| Field | Tipe | Wajib | Keterangan |
|---|---|---:|---|
| `attendance_mode` | string | Ya | Harus `"wfa"`. |
| `selfie` | string | Ya | Raw base64 JPEG/PNG/WebP, maksimum 5 MB. |
| `latitude` | number | Tidak | Kibarkan jika ingin mencatat posisi. |
| `longitude` | number | Tidak | Kibarkan jika ingin mencatat posisi. |
| `accuracy` | number | Tidak | Akurasi GPS dalam meter. |
| `device_id` | string | Tidak | 1–255 karakter; server hanya menyimpan SHA-256. |

Aturan kolom GPS:

- Jika seluruh `latitude`, `longitude`, `accuracy` kosong, GPS dianggap tidak tersedia.
- Jika hanya sebagian yang diisi, ketiganya wajib valid:
  - `latitude` antara `-90` dan `90`;
  - `longitude` antara `-180` dan `180`;
  - `accuracy > 0`.
- Selfie wajib meskipun WFA tidak menggunakan geofence.

### Response berhasil

```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "result": {
    "success": true,
    "data": {
      "attendance_id": 45,
      "event_id": 83,
      "state": "checked_in",
      "check_in": "2026-09-06 08:15:20",
      "company_id": 6,
      "attendance_mode": "wfa",
      "work_location_id": false,
      "work_location_name": false,
      "schedule_id": false,
      "validation": {
        "status": "success",
        "mode": "wfa",
        "geofence_valid": false,
        "distance_meters": false,
        "accuracy_meters": false,
        "selfie_received": true
      }
    },
    "error": null
  }
}
```

## 7. Check-out WFA

### Endpoint

```http
POST /api/presenly/v1/attendance/check-out
```

Mode check-out dibaca dari sesi check-in aktif. `attendance_mode` boleh dikirim ulang demi ketegasan audit, tetapi tidak mengganti mode server.

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "attendance_mode": "wfa",
    "selfie": "NEW_BASE64_IMAGE_WITHOUT_DATA_URL_PREFIX",
    "device_id": "OPTIONAL_STABLE_DEVICE_IDENTIFIER"
  },
  "id": 12
}
```

Selfie check-out wajib dan harus foto baru untuk event check-out.

### Response berhasil

```json
{
  "jsonrpc": "2.0",
  "id": 12,
  "result": {
    "success": true,
    "data": {
      "attendance_id": 45,
      "event_id": 84,
      "state": "checked_out",
      "check_in": "2026-09-06 08:15:20",
      "check_out": "2026-09-06 17:04:12",
      "worked_hours": 8.8156,
      "company_id": 6,
      "attendance_mode": "wfa",
      "work_location_id": false,
      "work_location_name": false,
      "schedule_id": false,
      "validation": {
        "status": "success",
        "mode": "wfa",
        "geofence_valid": false,
        "same_work_location": false,
        "distance_meters": false,
        "accuracy_meters": false,
        "selfie_received": true
      }
    },
    "error": null
  }
}
```

WFA check-out tidak memvalidasi geofence dan tidak memvalidasi Work Location yang sama.

## 8. Validasi dan pesan error

| Kondisi | Kode/ sumber | Perilaku mobile |
|---|---|---|
| Session expired | JSON-RPC `error` (session) | Hapus cookie dan kembali ke login. |
| Tidak ada Employee aktif | `error.data.message` | Instruksikan menghubungi Administrator. |
| `attendance_mode` bukan `location`/`wfa` | `error.data.message` | Kirim ulang nilai yang valid. |
| Selfie check-in WFA kosong | `error.data.message` | Buka kamera dan ambil foto baru. |
| Selfie check-out WFA kosong | `error.data.message` | Buka kamera dan ambil foto baru. |
| Selfie bukan base64/data URL/format salah | `error.data.message` | Encode ulang JPEG/PNG/WebP tanpa prefix data URL. |
| Selfie melebihi 5 MB | `error.data.message` | Kompres atau resize. |
| Sudah check-in | `error.data.message` | Panggil `status` dan tampilkan check-out. |
| Tidak ada check-in aktif | `error.data.message` | Panggil `status` dan tampilkan check-in. |
| Network timeout | — | Panggil `status` sebelum retry. |

Ambil pesan aman dari `error.data.message`, bukan `error.data.debug`.

## 9. Idempotensi dan retry

- Endpoint tidak menerima client timestamp dan tidak memiliki idempotency key.
- Disable tombol saat request berlangsung.
- Jangan mengirim request paralel.
- Setelah timeout, panggil `status`:
  - Jika `checked_in`, jangan ulang check-in.
  - Jika `checked_out`, jangan ulang check-out.
- Server menolak check-in kedua bila ada sesi aktif, dan check-out kedua bila tidak ada sesi aktif.

## 10. Contoh alur lengkap WFA

```text
1. POST /web/session/authenticate
2. POST /api/presenly/v1/attendance/status
3. POST /api/presenly/v1/attendance/modes
4. POST /api/presenly/v1/attendance/check-in
       { "attendance_mode": "wfa", "selfie": "<base64>" }
5. POST /api/presenly/v1/attendance/status
6. POST /api/presenly/v1/attendance/check-out
       { "attendance_mode": "wfa", "selfie": "<base64 baru>" }
7. POST /api/presenly/v1/attendance/status
8. POST /web/session/destroy
```

## 11. Checklist implementasi WFA

- [ ] Panggil `modes` untuk membaca policy `wfa_policy`.
- [ ] Hormati `wfa_policy.allowed`; sembunyikan WFA jika `false`.
- [ ] Minta selfie check-in dan check-out secara wajib.
- [ ] GPS boleh kosong, tetapi jika diisi sebagian harus lengkap dan valid.
- [ ] Kirim `attendance_mode: "wfa"` eksplisit pada check-in.
- [ ] Check-out menggunakan mode dari server; boleh kirim `attendance_mode` ulang.
- [ ] Periksa `error` dan `result.success` pada setiap response.
- [ ] Timeout diselesaikan dengan `status` sebelum retry.
- [ ] Logout menghapus cookie lokal.