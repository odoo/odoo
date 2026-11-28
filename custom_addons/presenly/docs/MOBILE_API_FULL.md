# Presenly Mobile API — Dokumentasi Lengkap

Dokumen ini adalah **satu-satunya acuan API mobile Presenly**, menggabungkan seluruh dokumentasi yang sebelumnya terpisah:

- `MOBILE_API.md` — login/session, attendance, GPS/geofence, selfie
- `MOBILE_MODE_SELECTION.md` — pemilihan mode On-Site vs Work From Anywhere
- `MOBILE_WFA_API.md` — Work From Anywhere (WFA)
- `MOBILE_TIMEOFF_API.md` — Time Off (Cuti)
- `MOBILE_APPROVAL_API.md` — Approval & pengajuan (Time Off + Permission)
- `MOBILE_OVERTIME_API.md` — Overtime / Lembur

> Dokumen asli tetap dipertahankan sebagai referensi; file ini kanonik. Semua endpoint menggunakan prefix `/api/presenly/v1`, auth session Odoo, format JSON-RPC, dan envelope `{success, data, error}`.

---

## Daftar Isi

1. [Ringkasan integrasi](#1-ringkasan-integrasi)
2. [Autentikasi & Session](#2-autentikasi--session)
3. [Format JSON-RPC & Error handling](#3-format-json-rpc--error-handling)
4. [Attendance](#4-attendance)
   - 4.1 Status presensi
   - 4.2 Pemilihan mode (On-Site / WFA)
   - 4.3 GPS & selfie
   - 4.4 Check-in On-Site
   - 4.5 Check-out On-Site
   - 4.6 Work Location resolver
5. [Work From Anywhere (WFA)](#5-work-from-anywhere-wfa)
   - 5.1 Daftar mode & policy
   - 5.2 Status WFA
   - 5.3 Check-in WFA
   - 5.4 Check-out WFA
   - 5.5 Mode dalam evidence
6. [Time Off (Cuti)](#6-time-off-cuti)
   - 6.1 Konsep & status
   - 6.2 Time Off Type
   - 6.3 Buat + submit
   - 6.4 List & antrean approval
   - 6.5 Approve / Reject
   - 6.6 Alur leveling approval
7. [Permission (Izin/Dispensasi)](#7-permission-izindispensasi)
   - 7.1 Permission Type
   - 7.2 Buat + submit
   - 7.3 List & antrean approval
   - 7.4 Approve / Reject
8. [Overtime (Lembur)](#8-overtime-lembur)
   - 8.1 Konsep
   - 8.2 Buat + submit
   - 8.3 List & antrean approval
   - 8.4 Approve / Reject / Cancel
9. [Kemampuan User (can-approve)](#9-kemampuan-user-can-approve)
10. [Work Location Otomatis](#10-work-location-otomatis)
11. [Validasi & Pesan Error Umum](#11-validasi--pesan-error-umum)
12. [Idempotensi & Retry](#12-idempotensi--retry)
13. [Konfigurasi Backend Minimum](#13-konfigurasi-backend-minimum)
14. [Daftar Endpoint Lengkap](#14-daftar-endpoint-lengkap)
15. [Contoh Alur & Checklist](#15-contoh-alur--checklist)

---

## 1. Ringkasan Integrasi

Base URL lokal: `http://127.0.0.1:8069` (production wajib HTTPS).

Urutan aplikasi mobile:

1. Login melalui `POST /web/session/authenticate`.
2. Simpan cookie `session_id` secara aman.
3. Panggil `POST /api/presenly/v1/attendance/status`.
4. Jika `can_check_in=true`, ambil GPS + selfie lalu check-in sesuai mode (`location` / `wfa`).
5. Jika `can_check_out=true`, ambil GPS + selfie baru lalu check-out.
6. Panggil status lagi setelah transaksi untuk menyinkronkan UI.
7. Logout melalui `POST /web/session/destroy` dan hapus cookie lokal.

Presenly memakai **session cookie native Odoo 19**, bukan JWT. Semua waktu check-in/out ditentukan server; mobile tidak mengirim `employee_id`, `check_in`, maupun `check_out`.

**Modul request yang didukung:**

| Request | Model | Approval |
|---|---|---|
| Time Off (Cuti) | `hr.leave` | Presenly Approval Journey |
| Permission / Dispensasi | `presenly.permission` | Presenly Approval Journey |
| Overtime / Lembur | `presenly.overtime.request` | Presenly Approval Journey |
| Attendance (check-in/out) | `hr.attendance` | Tidak (geofence/selfie sebagai bukti) |

---

## 2. Autentikasi & Session

### 2.1 Login

```http
POST /web/session/authenticate
```

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": { "db": "odoo", "login": "employee@example.com", "password": "USER_PASSWORD" },
  "id": 1
}
```

Login berhasil hanya jika: tidak ada `error`, `result.uid` terisi, dan cookie `session_id` dibuat.

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { "uid": 12, "username": "employee@example.com", "db": "odoo" }
}
```

Contoh curl:

```bash
BASE_URL=http://127.0.0.1:8069
DB=odoo
LOGIN=employee@example.com
PASSWORD='USER_PASSWORD'
COOKIE_JAR=/tmp/presenly-cookie.txt

curl --fail-with-body --silent --show-error \
  -c "$COOKIE_JAR" -H 'Content-Type: application/json' \
  -X POST "$BASE_URL/web/session/authenticate" \
  --data "$(jq -n --arg db "$DB" --arg login "$LOGIN" --arg password "$PASSWORD" \
    '{jsonrpc:"2.0",method:"call",params:{db:$db,login:$login,password:$password},id:1}')"
```

Untuk request berikutnya, kirim cookie dengan `-b "$COOKIE_JAR"` dan simpan pembaruan dengan `-c "$COOKIE_JAR"`.

### 2.2 Cek session

```http
POST /web/session/get_session_info
```

Jika session expired: hapus cookie lokal, hapus state attendance lokal yang belum dikonfirmasi, arahkan ke login; jangan retry otomatis tanpa konfirmasi user.

### 2.3 Logout

```http
POST /web/session/destroy
```

Setelah logout: hapus cookie & data profil lokal (jangan hapus bukti transaksi yang sudah dikonfirmasi server).

### Penyimpanan session

- Perlakukan `session_id` sebagai secret (HttpOnly + Secure di production).
- Jangan simpan password; jangan log password, cookie, atau selfie.
- iOS: `HTTPCookieStorage`; rahasia tambahan di Keychain.
- Android: `CookieManager`/cookie jar; Flutter/React Native: cookie manager persisten terenkripsi.

---

## 3. Format JSON-RPC & Error handling

Semua endpoint Presenly memakai HTTP `POST` dengan `Content-Type: application/json`.

Envelope request:

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 1
}
```

- Data endpoint diletakkan **langsung di `params`** — jangan bungkus dengan key `payload`/`data`.
- Endpoint `<id>/approve`, `<id>/reject`, `<id>/cancel` memakai path parameter.
- Semua endpoint Presenly **read-only** (selain mutasi) menerima `params: {}`.

Response bisnis berhasil:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { "success": true, "data": {}, "error": null }
}
```

Error dikirim pada properti JSON-RPC `error`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": 100,
    "message": "Odoo Session Expired",
    "data": { "name": "odoo.http.SessionExpiredException", "message": "Session expired" }
  }
}
```

Client wajib memeriksa: tidak ada `error` **dan** `result.success === true`; gunakan hanya `result.data`. Ambil pesan aman dari `error.data.message`; jangan tampilkan `error.data.debug`.

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

---

## 4. Attendance

### 4.1 Status presensi

```http
POST /api/presenly/v1/attendance/status
```

`params: {}`. Endpoint ini juga berguna untuk verifikasi session + relasi User–Employee.

Response (belum check-in, lokasi siap):

```json
{
  "result": {
    "success": true,
    "data": {
      "server_time": "2026-09-06 08:15:20",
      "employee_id": 42,
      "employee_name": "Feri",
      "company_id": 6,
      "company_name": "PT KONSULTA SEMEN GRESIK",
      "state": "checked_out",
      "can_check_in": true,
      "can_check_out": false,
      "message": "Employee is ready to check in.",
      "attendance_id": false,
      "check_in": false,
      "work_location_id": false,
      "work_location_name": false,
      "schedule_id": false,
      "attendance_mode": false,
      "available_work_locations": [
        {
          "id": 7,
          "name": "Kantor Gresik",
          "schedule_id": 15,
          "geofence_ready": true,
          "geofence_radius_meters": 150.0,
          "gps_accuracy_limit_meters": 50.0,
          "require_selfie_check_in": true,
          "require_selfie_check_out": true
        }
      ],
      "recommended_work_location_id": 7,
      "auto_selection_supported": true,
      "ambiguous": false,
      "can_select_mode": true,
      "wfa_available": true
    },
    "error": null
  }
}
```

Response saat sedang check-in:

```json
{
  "result": {
    "success": true,
    "data": {
      "state": "checked_in",
      "can_check_in": false,
      "can_check_out": true,
      "message": "Employee has an active attendance session.",
      "attendance_id": 44,
      "check_in": "2026-09-06 08:15:20",
      "work_location_id": 7,
      "work_location_name": "Kantor Gresik",
      "schedule_id": 15,
      "attendance_mode": "location"
    },
    "error": null
  }
}
```

Field penting:

- `state`: `checked_in` / `checked_out`.
- `can_check_in`/`can_check_out`: sumber truth untuk tombol.
- `available_work_locations`: lokasi terjadwal saat ini (untuk picker opsional).
- `recommended_work_location_id`: lokasi yang disarankan; `false` bila ambigu.
- `auto_selection_supported`: bila `true`, mobile boleh **tidak mengirim** `work_location_id` dan server otomatis memilih by GPS.
- `ambiguous`: `true` bila >1 lokasi valid → tampilkan picker.
- `wfa_available`: WFA dapat dipilih saat ini.

Panggil status saat: app dibuka, login selesai, resume dari background, setelah check-in/out, dan setelah timeout.

### 4.2 Pemilihan mode (On-Site / WFA)

```http
POST /api/presenly/v1/attendance/modes
```

`params: {}` →

```json
{
  "data": {
    "employee_id": 42,
    "company_id": 6,
    "available_modes": [
      { "mode": "location", "label": "On-Site", "requires_gps": true, "requires_work_location": true, "requires_selfie": "per_location_policy" },
      { "mode": "wfa", "label": "Work From Anywhere", "requires_gps": false, "requires_work_location": false, "requires_selfie": true }
    ],
    "default_mode": "location",
    "wfa_policy": { "allowed": true, "approval_required": false, "geofence_required": false, "time_or_location_limit": false, "selfie_required": true }
  }
}
```

Aturan UI:

- Render dari `available_modes`, bukan hardcode.
- `default_mode` = pilihan awal.
- Sembunyikan WFA bila `wfa_policy.allowed == false`.
- Flow: `status` → jika `can_check_in=true` → `modes` → user pilih → check-in.

### 4.3 GPS & selfie

Sebelum check-in/out:

1. Minta izin kamera & precise location.
2. Ambil koordinat terbaru (bukan cache), tunggu `accuracy > 0`.
3. Bandingkan accuracy dengan `gps_accuracy_limit_meters` utk peringatan dini.
4. Ambil selfie baru (jika diwajibkan), kompres bila perlu.
5. Encode **raw base64 tanpa prefix data URL** `data:...`:
   - ✅ benar: `/9j/4AAQSkZJRgABAQAAAQABAAD...`
   - ❌ salah: `data:image/jpeg;base64,/9j/4AAQSkZJRg...`

Ketentuan selfie:

- format JPEG/PNG/WebP;
- maksimum 5 MB setelah didecode;
- base64 valid, file dapat didecode sebagai gambar aman;
- disimpan privat di Odoo;
- check-in dan check-out = dua foto terpisah;
- jangan simpan selfie pada log/analytics.

### 4.4 Check-in On-Site

```http
POST /api/presenly/v1/attendance/check-in
```

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "attendance_mode": "location",
    "work_location_id": 7,
    "latitude": -7.1697742,
    "longitude": 112.6495932,
    "accuracy": 8.5,
    "selfie": "BASE64_IMAGE_WITHOUT_DATA_URL_PREFIX",
    "device_id": "OPTIONAL_STABLE_DEVICE_IDENTIFIER"
  },
  "id": 10
}
```

| Field | Tipe | Wajib | Keterangan |
|---|---|---:|---|
| `attendance_mode` | string | Tidak | `location`/`wfa`; default server `location`. |
| `work_location_id` | integer | Tidak | Lokasi terjadwal. Kosong → auto-pilih by GPS. |
| `latitude` | number | Ya (location) | -90..90. |
| `longitude` | number | Ya (location) | -180..180. |
| `accuracy` | number | Ya (location) | meter, > 0. |
| `selfie` | string | Sesuai policy | raw base64, max 5 MB. |
| `device_id` | string | Tidak | 1–255 karakter; server simpan SHA-256. |

`unit_id` masih diterima sebagai alias `work_location_id` (client baru pakai `work_location_id`).

Response berhasil:

```json
{
  "result": {
    "success": true,
    "data": {
      "attendance_id": 44,
      "event_id": 81,
      "state": "checked_in",
      "check_in": "2026-09-06 08:15:20",
      "company_id": 6,
      "work_location_id": 7,
      "work_location_name": "Kantor Gresik",
      "schedule_id": 15,
      "validation": { "status": "success", "geofence_valid": true, "distance_meters": 12.34, "accuracy_meters": 8.5, "selfie_received": true }
    },
    "error": null
  }
}
```

Server menolak bila: session invalid, tidak ada employee aktif, company tidak di allowed companies, sudah ada sesi aktif, tidak ada lokasi terjadwal, lokasi tidak geofence-ready, di luar geofence, accuracy melebihi limit, atau selfie wajib tidak valid.

Contoh curl:

```bash
LAT=-7.1697742; LON=112.6495932; ACCURACY=8.5; LOCATION_ID=7
SELFIE_BASE64="$(base64 < selfie.jpg | tr -d '\n')"
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" -c "$COOKIE_JAR" -H 'Content-Type: application/json' \
  -X POST "$BASE_URL/api/presenly/v1/attendance/check-in" \
  --data "$(jq -n --argjson location "$LOCATION_ID" --argjson latitude "$LAT" \
    --argjson longitude "$LON" --argjson accuracy "$ACCURACY" --arg selfie "$SELFIE_BASE64" \
    '{jsonrpc:"2.0",method:"call",params:{work_location_id:$location,latitude:$latitude,longitude:$longitude,accuracy:$accuracy,selfie:$selfie},id:10}')"
```

### 4.5 Check-out On-Site

```http
POST /api/presenly/v1/attendance/check-out
```

Field sama dengan check-in; **selfie harus foto baru**. Check-out selalu memakai Work Location yang disnapshot saat check-in (wajib sama):

```json
{
  "result": {
    "success": true,
    "data": {
      "attendance_id": 44,
      "event_id": 82,
      "state": "checked_out",
      "check_in": "2026-09-06 08:15:20",
      "check_out": "2026-09-06 17:04:12",
      "worked_hours": 8.8156,
      "company_id": 6,
      "work_location_id": 7,
      "work_location_name": "Kantor Gresik",
      "schedule_id": 15,
      "validation": { "status": "success", "same_work_location": true, "distance_meters": 13.01, "accuracy_meters": 7.0, "selfie_received": true }
    },
    "error": null
  }
}
```

Check-out berhasil hanya jika: ada sesi aktif, lokasi sama dengan snapshot, geofence masih berlaku, accuracy valid, selfie valid bila diwajibkan. Setelah berhasil panggil `status` → `state: checked_out`. `can_check_in` bisa tetap `false` bila tidak ada lokasi terjadwal saat itu.

### 4.6 Work Location resolver

Resolver server memilih lokasi dengan urutan:

1. Presenly Specific-Date Work Location Schedule;
2. Weekly Work Location Schedule (slots, jam valid, Week 1/2);
3. native Exceptional Employee Work Location;
4. native weekday Employee Work Location;
5. Employee primary Work Location.

Aturan penting:

- Specific-Date menggantikan seluruh Weekly schedule pada tanggal itu.
- Hari yang dikontrol slot → jika waktu di luar slot, check-in ditolak (tanpa fallback ke primary).
- Beberapa lokasi/hari = slot non-overlap; harus check-out dulu sebelum check-in lokasi berikutnya.
- `work_location_id` dari mobile harus termasuk lokasi aktif waktu server.
- **Tanpa** `work_location_id`, server otomatis memilih lokasi yang geofence-nya cocok dengan GPS (lihat bagian 10).

---

## 5. Work From Anywhere (WFA)

WFA adalah mode **pencatatan saja** (sementara): tanpa geofence, tanpa batas lokasi/jarak, tanpa approval; **selfie check-in & check-out wajib**; GPS opsional. Setiap evidence menandai `attendance_mode = wfa`.

| Aspek | WFA |
|---|---|
| Geofence / Work Location | Tidak |
| Approval | Tidak |
| GPS | Opsional |
| Selfie check-in/out | Wajib |
| Timestamp & identitas | Server / session |

### 5.1 Daftar mode & policy

`POST /api/presenly/v1/attendance/modes` (lihat 4.2). Field WFA kunci: `available_modes[].mode="wfa"`, `wfa_policy.allowed`, `wfa_policy.selfie_required=true`, `geofence_required=false`.

### 5.2 Status WFA

`POST /api/presenly/v1/attendance/status` mengembalikan `attendance_mode`, `can_select_mode`, `wfa_available`. `can_check_in=true` dapat terjadi tanpa lokasi terjadwal selama WFA tersedia.

### 5.3 Check-in WFA

```http
POST /api/presenly/v1/attendance/check-in
```

```json
{
  "params": {
    "attendance_mode": "wfa",
    "selfie": "BASE64_IMAGE_WITHOUT_DATA_URL_PREFIX",
    "device_id": "OPTIONAL_STABLE_DEVICE_IDENTIFIER"
  },
  "id": 11
}
```

GPS opsional — kirim ketiganya lengkap jika ingin mencatat posisi, atau kosongkan semua:

```json
{
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

Response:

```json
{
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
      "validation": { "status": "success", "mode": "wfa", "geofence_valid": false, "distance_meters": false, "accuracy_meters": false, "selfie_received": true }
    },
    "error": null
  }
}
```

### 5.4 Check-out WFA

```http
POST /api/presenly/v1/attendance/check-out
```

Mode dibaca dari sesi check-in; boleh kirim ulang demi ketegasan audit. Selfie check-out **wajib** dan harus foto baru. Tidak memvalidasi geofence/lokasi sama.

### 5.5 Mode dalam evidence

Setiap `presenly.attendance.event` menyimpan `attendance_mode` (`location`/`wfa`). HR dapat filter **Work From Anywhere** dan grouping **Mode** di laporan Attendance Evidence.

---

## 6. Time Off (Cuti)

### 6.1 Konsep & status

Time Off memakai native `hr.leave` sebagai mesin transaksi final (alokasi, kalender, durasi, work entry). Presenly menambah **Approval Journey** di atasnya. Native Time Off approval tidak dapat mem-bypass journey.

Field status dalam serialisasi:

| Field | Arti |
|---|---|
| `state` | Status native Odoo: `draft/confirm/validate/refuse/cancel` |
| `approval_state` | Journey Presenly: `not_started/pending/approved/rejected/cancelled` |
| `approval_level` | Level berjalan (0 = belum mulai) |
| `approval_progress` | Contoh `Level 1 of 3`, `Completed (3/3)` |
| `current_approvers` | Daftar user yang ditunggu keputusannya |
| `approval_steps` | Snapshot level + decision_by/date/note |
| `rejection_reason` | Alasan penolakan |

### 6.2 Daftar Time Off Type

```http
POST /api/presenly/v1/leave/types
```

`params: {}` → `data: [{id, name}]`. Hanya tipe `active` milik company/global.

### 6.3 Buat + Submit

```http
POST /api/presenly/v1/leaves
```

```json
{
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
| `leave_type_id` | integer | Ya | Dari `/leave/types`. |
| `work_location_id` | integer | Tidak | Lokasi terjadwal; kosong → auto-resolve (bagian 10). |
| `date_from` | date | Ya | Mulai. |
| `date_to` | date | Tidak | Selesai; default = `date_from`. |
| `reason` | string | Tidak | Alasan. |

`unit_id` alias `work_location_id`. `employee_id` tidak boleh dikirim.

Server: validasi employee/type/lokasi/route → buat `hr.leave` → `action_presenly_submit()` (state → `pending`). Response berisi serializer lengkap (contoh di bawah).

```json
{
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
        { "level": 1, "name": "Manager Review", "state": "pending", "approver_ids": [5], "decision_by": false, "decision_date": false, "decision_note": false }
      ],
      "rejection_reason": false
    },
    "error": null
  }
}
```

### 6.4 List & antrean approval

```http
POST /api/presenly/v1/leaves/list          # request milik saya (max 100)
POST /api/presenly/v1/leaves/approval      # antrean where current user is approver
```

`GET /api/presenly/v1/leaves` = alias legacy list.

### 6.5 Approve / Reject

```http
POST /api/presenly/v1/leaves/<leave_id>/approve   # params: {}
POST /api/presenly/v1/leaves/<leave_id>/reject    # params: { "reason": "..." } (wajib)
```

Approve level final → `state: validate`, `approval_state: approved`. Reject → `state: refuse`, `approval_state: rejected`, `rejection_reason` terisi.

### 6.6 Alur leveling approval

1. Route diambil per Company + Type + Work Location.
2. Step dinormalisasi berdasarkan `Order` (10, 20, 30…).
3. Step location-specific menggantikan company-wide pada Order yang sama.
4. Approver di-resolve sesuai `approver_type` (Employee Manager, Work Location Manager, HR Officer, Specific User, Odoo Group).
5. Journey menyimpan snapshot level/approver saat submit.
6. User memproses step aktif via `approve`/`reject`.
7. Native `_action_validate` hanya di level terakhir.

Mobile tidak perlu tahu aturan internal — cukup ikuti `approval_progress` dan `current_approvers`.

---

## 7. Permission (Izin/Dispensasi)

### 7.1 Daftar Permission Type

```http
POST /api/presenly/v1/permissions/types
```

`params: {}` → `data: [{id, name, code, requires_attachment}]`. Hanya tipe `active` + `is_complete` milik company.

### 7.2 Buat + Submit

```http
POST /api/presenly/v1/permissions
```

```json
{
  "params": {
    "permission_type_id": 3,
    "work_location_id": 7,
    "request_mode": "full_day",
    "date_from": "2026-09-11",
    "date_to": "2026-09-11",
    "hour_from": 0,
    "hour_to": 0,
    "reason": "Emergency errand",
    "attachments": [ { "name": "support.jpg", "data": "BASE64...", "mimetype": "image/jpeg" } ]
  },
  "id": 4
}
```

| Field | Tipe | Wajib | Keterangan |
|---|---|---:|---|
| `permission_type_id` | integer | Ya | Dari `/permissions/types`. |
| `work_location_id` | integer | Tidak | Kosong → auto-resolve (bagian 10). |
| `request_mode` | string | Tidak | `full_day` / `hours`; harus sesuai tipe (`full_day`/`hours`/`both`). |
| `date_from` / `date_to` | date | Ya / Tidak | Rentang; `hours` wajib `date_from == date_to`. |
| `hour_from` / `hour_to` | number | Jika hours | `0 <= from < to <= 24`. |
| `reason` | string | Ya | Alasan wajib. |
| `attachments` | array | Tergantung | Wajib bila `requires_attachment`; `{name, data(base64), mimetype?}`, max 10 MB/item, privat. |

Validasi server: field wajib, mode sesuai tipe, lokasi terjadwal, **tidak overlap** dengan permission lain (`submitted`/`approved`) dalam periode, route lengkap, lampiran bila diwajibkan.

Response serializer menambah `request_mode`, `hour_from`, `hour_to`, `permission_type`, `affects_attendance`, `paid_status`, `attachments` (metadata), `approval_steps`, `rejection_reason`.

### 7.3 List & antrean approval

```http
POST /api/presenly/v1/permissions/list        # request milik saya (kanonik, max 100)
POST /api/presenly/v1/permissions/approval    # antrean where current user is approver
```

`GET /api/presenly/v1/permissions` = alias legacy.

### 7.4 Approve / Reject

```http
POST /api/presenly/v1/permissions/<permission_id>/approve   # params: {}
POST /api/presenly/v1/permissions/<permission_id>/reject    # params: { "reason": "..." } (wajib)
```

Approve level final → `state: approved`. Reject → `state: rejected` + `rejection_reason`.

---

## 8. Overtime (Lembur)

### 8.1 Konsep

- **Satu periode per hari**: `date` + `hour_from`/`hour_to` (**jam 24 jam**; terima float/int `18`, `18.5`, atau string `"18:30"`).
- **Durasi dihitung server** (`duration_hours = hour_to - hour_from`); client tidak mengirim.
- **Wajib ada bukti attendance** (`hr.attendance`) pada `date`; tanpa itu submit ditolak.
- **Hanya 1 pengajuan per employee per hari**; duplicate ditolak.
- **Self-only**: `employee_id` selalu dari session (hanya HR/Administrator via web untuk orang lain).
- Work Location: wajib terjadwal; kosong → auto-resolve (bagian 10).
- Approval: Presenly Approval Journey dengan route `is_overtime_route`.
- **Tidak ada uang makan** (fitur di-revert).

### 8.2 Buat + Submit

```http
POST /api/presenly/v1/overtime/requests
```

```json
{
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
| `date` | date | Ya | Hari lembur (perlu attendance). |
| `hour_from` | number/string | Ya | Jam mulai 24H. |
| `hour_to` | number/string | Ya | Jam selesai 24H; `0 <= from < to <= 24`. |
| `work_location_id` | integer | Tidak | Kosong → auto-resolve. |
| `reason` | string | Tidak | Alasan. |

Server menolak bila: jam tidak valid, tidak ada attendance pada tanggal itu, sudah ada pengajuan hari sama, route overtime belum lengkap, lokasi tidak terjadwal. Response serializer:

```json
{
  "result": {
    "success": true,
    "data": {
      "id": 5, "name": "OT/2026/00005",
      "employee_id": 42, "company_id": 6, "work_location_id": 7,
      "date": "2026-09-10", "hour_from": 18.0, "hour_to": 22.0,
      "duration_hours": 4.0, "reason": "Server maintenance",
      "has_attendance_evidence": true,
      "state": "submitted", "approval_level": 0,
      "approval_progress": "Level 1 of 1",
      "current_approvers": [ { "id": 5, "name": "Manager User" } ],
      "approval_steps": [ { "level": 1, "name": "Overtime Review", "state": "pending", "approver_ids": [5], "decision_by": false, "decision_date": false, "decision_note": false } ],
      "rejection_reason": false
    },
    "error": null
  }
}
```

### 8.3 List & antrean approval

```http
POST /api/presenly/v1/overtime/requests/list        # request milik saya (max 100)
POST /api/presenly/v1/overtime/requests/approval    # antrean approver
```

### 8.4 Approve / Reject / Cancel

```http
POST /api/presenly/v1/overtime/requests/<id>/approve   # params: {}
POST /api/presenly/v1/overtime/requests/<id>/reject    # params: { "reason": "..." } (wajib)
POST /api/presenly/v1/overtime/requests/<id>/cancel    # params: {} (owner/HR, draft/submitted)
```

---

## 9. Kemampuan User (can-approve)

Read-only; untuk men-disable tombol Approve/Reject/Cancel di UI mobile sesuai hak user pada level aktif.

| Endpoint | Catatan |
|---|---|
| `POST /leaves/<id>/can-approve` | `data: {id, approval_state, approval_progress, current_approvers, can_approve, can_reject, can_cancel}` |
| `POST /leaves/can-approve/batch` | `params: {ids: [...]}` → `{items, unreadable_ids}` |
| `POST /permissions/<id>/can-approve` | `data: {id, state, ...}` |
| `POST /permissions/can-approve/batch` | `params: {ids: [...]}` |
| `POST /overtime/requests/<id>/can-approve` | `data: {id, state, ...}` |
| `POST /overtime/requests/can-approve/batch` | `params: {ids: [...]}` |

Aturan:

- `can_approve`/`can_reject` mengikuti **level approval aktif** (hanya approver level tersebut).
- `can_cancel` mengikuti owner/manager/HR pada state `draft`/`submitted`.
- Request final → ketiganya `false`.
- ID yang tidak dapat diakses user dimasukkan ke `unreadable_ids` (tidak error).

---

## 10. Work Location Otomatis

Policy umum (Time Off / Permission / Overtime) — lihat `PLAN_AUTO_WORK_LOCATION.md`:

- **Attendance**: tanpa `work_location_id`, server memilih lokasi yang geofence-nya cocok dengan GPS dari lokasi terjadwal saat itu. `status` mengembalikan `recommended_work_location_id`, `auto_selection_supported`, `ambiguous`.
- **Pengajuan** (Time Off/Permission/Overtime): bila `work_location_id` tidak dikirim, server memanggil `_presenly_resolve_period_location`:
  - 1 lokasi seluruh periode → auto-isi, lanjut.
  - Satu hari 2 slot beda jam → **slot pertama** (K2) untuk full-day; untuk Permission mode `hours` → **slot yang beririsan jam** (K2b).
  - Periode lintas lokasi (beda hari) → **TOLAK** dengan daftar per tanggal (K1).
- Kirim `work_location_id` eksplisit → divalidasi harus termasuk lokasi terjadwal (tidak ada bypass).

Endpoint preview lokasi:

| Endpoint | Params |
|---|---|
| `POST /leaves/location-options` | `{date_from, date_to}` |
| `POST /permissions/location-options` | `{date_from, date_to, request_mode?, hour_from?, hour_to?}` |
| `POST /overtime/requests/location-options` | `{date}` |

Contoh response:

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

## 11. Validasi & Pesan Error Umum

| Kondisi | Perilaku mobile |
|---|---|
| Session expired | Hapus cookie; kembali ke login. |
| Tidak ada Employee aktif | Notifikasi "hubungi Administrator". |
| Company tidak di Allowed Companies | Hubungi Administrator. |
| Tipe/Type tidak valid / beda company | Muat ulang type list. |
| Work Location tidak terjadwal | Muat ulang pilihan lokasi / auto-resolve. |
| Route approval kosong/ambigu | Hubungi Administrator melengkapi Approval Route. |
| Bukan approver level aktif / tidak pending | Refresh antrean; beri tahu tidak berwenang. |
| `reason` reject kosong | UI wajib minta alasan. |
| Attendance: di luar geofence | Tampilkan jarak/lokasi; minta pindah + GPS ulang. |
| GPS accuracy terlalu buruk | Minta precise location; retry manual. |
| Selfie wajib / base64 invalid / > 5 MB | Buka kamera / kompres / encode ulang tanpa prefix. |
| Sudah check-in / tidak ada check-in | Refresh `status`. |
| Check-out lokasi beda | Arahkan ke Work Location check-in. |
| Permission mode tidak sesuai tipe | Perbaiki mode/durasi. |
| Attachment wajib / > 10 MB / invalid | Validasi lokal sebelum kirim. |
| Overlap permission aktif | Beri tahu periode bentrok. |
| Overtime tanpa attendance hari tsb | Informasikan hari harus punya attendance. |
| Overtime duplicate hari yang sama | Buka pengajuan yang ada. |
| Overtime jam tidak valid 24H | Perbaiki jam (0–24, from < to). |
| Multi-lokasi periode pengajuan | Tampilkan pilihan via `location-options`. |

---

## 12. Idempotensi & Retry

- Endpoint mutasi tidak menerima client timestamp dan tidak punya idempotency key.
- Disable tombol saat request berjalan; jangan kirim paralel.
- Setelah timeout: panggil endpoint `status` (attendance) atau `list`/`approval` (pengajuan).
  - Jika state sudah berubah → jangan ulangi approve/reject/check-in/out.
  - Jika belum berubah → boleh retry sekali manual.
- Server melindungi state:
  - check-in kedua ditolak bila sesi aktif masih ada; check-out kedua ditolak bila tidak ada.
  - approve kedua pada request final ditolak.
  - create overtime/permission duplicate per hari/periode ditolak.

---

## 13. Konfigurasi Backend Minimum

### User

`Settings → Users & Companies → Users`:

- user aktif, tipe Internal User;
- role Presenly Employee;
- Allowed Companies mencakup company Employee;
- role Presenly Approver bila perlu approve.

### Employee

`Employees → Employees → pilih Employee`:

- Related User terhubung ke akun login;
- Company benar;
- Working Hours terisi;
- Primary/fallback Work Location terisi.

### Work Location

`Attendances → Configuration → Work Locations`:

- aktif, company sama, address ada;
- koordinat desimal valid (mis. `-7.1697742`, `112.6495932` — bukan integer panjang);
- Geofence Radius > 0, GPS Accuracy Limit > 0, Status Geofence Ready;
- policy selfie check-in/out.

### Jadwal lokasi

`Employees → Employees → pilih Employee → Working Hours & Locations`: Work Location Slots berada dalam Working Hours; slot tidak overlap; Specific-Date menggantikan Weekly.

### Approval Routes

`Attendances → Configuration → Approval Routes`:

- satu baris per step wajib, Order 10/20/30;
- target: Permission Type, Time Off Type, atau **Overtime Route** (`is_overtime_route`);
- approver source valid + role Presenly Approver;
- Work Location kosong = company default; isi = override di site tersebut.

---

## 14. Daftar Endpoint Lengkap

### Attendance

| Fungsi | Method | Endpoint |
|---|---|---|
| Daftar mode & policy | POST | `/api/presenly/v1/attendance/modes` |
| Status presensi | POST | `/api/presenly/v1/attendance/status` |
| Check-in | POST | `/api/presenly/v1/attendance/check-in` |
| Check-out | POST | `/api/presenly/v1/attendance/check-out` |

### Time Off

| Fungsi | Method | Endpoint |
|---|---|---|
| Daftar Time Off Type | POST | `/api/presenly/v1/leave/types` |
| Buat + submit | POST | `/api/presenly/v1/leaves` |
| Daftar milik saya | POST | `/api/presenly/v1/leaves/list` |
| List legacy | GET | `/api/presenly/v1/leaves` |
| Antrean approval | POST | `/api/presenly/v1/leaves/approval` |
| Approve | POST | `/api/presenly/v1/leaves/<id>/approve` |
| Reject | POST | `/api/presenly/v1/leaves/<id>/reject` |
| Can-approve | POST | `/api/presenly/v1/leaves/<id>/can-approve` |
| Can-approve batch | POST | `/api/presenly/v1/leaves/can-approve/batch` |
| Location options | POST | `/api/presenly/v1/leaves/location-options` |

### Permission

| Fungsi | Method | Endpoint |
|---|---|---|
| Daftar Permission Type | POST | `/api/presenly/v1/permissions/types` |
| Buat + submit | POST | `/api/presenly/v1/permissions` |
| Daftar milik saya | POST | `/api/presenly/v1/permissions/list` |
| List legacy | GET | `/api/presenly/v1/permissions` |
| Antrean approval | POST | `/api/presenly/v1/permissions/approval` |
| Approve | POST | `/api/presenly/v1/permissions/<id>/approve` |
| Reject | POST | `/api/presenly/v1/permissions/<id>/reject` |
| Can-approve | POST | `/api/presenly/v1/permissions/<id>/can-approve` |
| Can-approve batch | POST | `/api/presenly/v1/permissions/can-approve/batch` |
| Location options | POST | `/api/presenly/v1/permissions/location-options` |

### Overtime

| Fungsi | Method | Endpoint |
|---|---|---|
| Buat + submit | POST | `/api/presenly/v1/overtime/requests` |
| Daftar milik saya | POST | `/api/presenly/v1/overtime/requests/list` |
| Antrean approval | POST | `/api/presenly/v1/overtime/requests/approval` |
| Approve | POST | `/api/presenly/v1/overtime/requests/<id>/approve` |
| Reject | POST | `/api/presenly/v1/overtime/requests/<id>/reject` |
| Cancel | POST | `/api/presenly/v1/overtime/requests/<id>/cancel` |
| Can-approve | POST | `/api/presenly/v1/overtime/requests/<id>/can-approve` |
| Can-approve batch | POST | `/api/presenly/v1/overtime/requests/can-approve/batch` |
| Location options | POST | `/api/presenly/v1/overtime/requests/location-options` |

### Session (native Odoo)

| Fungsi | Method | Endpoint |
|---|---|---|
| Login | POST | `/web/session/authenticate` |
| Cek session | POST | `/web/session/get_session_info` |
| Logout | POST | `/web/session/destroy` |

---

## 15. Contoh Alur & Checklist

### 15.1 Alur employee (Time Off + lembur)

```text
1. POST /web/session/authenticate
2. POST /api/presenly/v1/leave/types
3. POST /api/presenly/v1/leaves            (submit cuti)
4. POST /api/presenly/v1/overtime/requests/{date, hour_from, hour_to, reason}
5. POST /api/presenly/v1/leaves/list       (cek status)
6. POST /api/presenly/v1/overtime/requests/list
7. POST /web/session/destroy
```

### 15.2 Alur approver

```text
1. POST /web/session/authenticate
2. POST /api/presenly/v1/leaves/approval
3. POST /api/presenly/v1/leaves/can-approve/batch  { ids: [...] }
4. POST /api/presenly/v1/leaves/<id>/approve
5. POST /api/presenly/v1/permissions/approval
6. POST /api/presenly/v1/permissions/<id>/reject   { reason: "..." }
7. POST /api/presenly/v1/overtime/requests/approval
8. POST /api/presenly/v1/overtime/requests/<id>/approve
9. POST /web/session/destroy
```

### 15.3 Checklist implementasi mobile

- [ ] Semua request JSON-RPC; data langsung di `params`.
- [ ] Login memeriksa `result.uid`; cookie `session_id` dipertahankan.
- [ ] `employee_id` tidak pernah dikirim client.
- [ ] Session expired → hapus cookie, kembali ke login.
- [ ] Setiap response memeriksa `error` dan `result.success`.
- [ ] Tombol follow `can_check_in`/`can_check_out` (attendance) dan `can-approve` (approval).
- [ ] GPS terbaru `accuracy > 0`; selfie raw base64 tanpa prefix, max 5 MB.
- [ ] Selfie check-in ≠ selfie check-out.
- [ ] `work_location_id` boleh kosong — baca `recommended_work_location_id` / `location-options`.
- [ ] Reject selalu menyertakan `reason`.
- [ ] Mutasi tidak dikirim paralel; timeout diselesaikan dengan cek ulang.
- [ ] Tidak log password, cookie, selfie, atau dokumen pribadi.

---

## Lampiran — Dokumen terkait

| Dokumen | Isi |
|---|---|
| `docs/MOBILE_API.md`, `MOBILE_MODE_SELECTION.md`, `MOBILE_WFA_API.md`, `MOBILE_TIMEOFF_API.md`, `MOBILE_APPROVAL_API.md`, `MOBILE_OVERTIME_API.md` | Dokumen sumber (dipertahankan sebagai referensi) |
| `docs/PLAN_APPROVAL_API.md` | Roadmap penyempurnaan approval API |
| `docs/PLAN_AUTO_WORK_LOCATION.md` | Kebijakan auto resolve Work Location (K1/K2/K2b) |
| `docs/PLAN_FULL_DOCUMENTATION.md` | Plan dokumentasi penuh |
| `presenly-prd.md` | PRD produk |