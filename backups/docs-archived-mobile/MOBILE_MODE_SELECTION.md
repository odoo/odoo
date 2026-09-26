# Presenly Mobile — Pemilihan Mode Attendance: On-Site dan WFA

Dokumen ini khusus membahas pemilihan mode attendance dari sisi aplikasi mobile: **On-Site** dan **Work From Anywhere (WFA)**. Autentikasi session, format JSON-RPC, GPS, selfie, dan aturan idempotensi mengacu pada [`MOBILE_API.md`](MOBILE_API.md).

Referensi API lengkap mode WFA ada di [`MOBILE_WFA_API.md`](MOBILE_WFA_API.md).

## 1. Ringkasan mode

| Mode | Kode API | Geofence | Work Location | Selfie | Approval |
|---|---|---|---|---|---|
| On-Site | `location` | Wajib | Wajib | Sesuai policy lokasi | Tidak untuk attendance |
| Work From Anywhere | `wfa` | Tidak | Tidak | Wajib | Tidak (sementara) |

WFA pada tahap ini bersifat **pencatatan saja**:

- tanpa batas lokasi/geofence;
- tanpa batas jarak atau posisi;
- tanpa approval;
- selfie check-in dan check-out tetap wajib sebagai bukti;
- hanya menandai attendance/evidence sebagai `wfa` agar HR tahu karyawan bekerja dari mana saja.

Ketentuan ini adalah default global dan dapat dikeraskan di versi berikutnya menjadi policy per company, per employee, atau per jadwal.

## 2. Endpoint daftar mode

Mobile memanggil endpoint ini untuk tahu mode yang tersedia dan policy WFA sebelum menampilkan pemilih mode.

```http
POST /api/presenly/v1/attendance/modes
```

Auth: session.

Request:

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 7
}
```

Response berhasil:

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

Aturan UI:

- Tampilkan `location` sebagai "On-Site" dan `wfa` sebagai "Work From Anywhere".
- Gunakan `default_mode` sebagai pilihan awal (`location`).
- Jika `wfa_policy.allowed` bernilai `false`, sembunyikan mode WFA.
- Aplikasi tetap harus memeriksa JSON-RPC `error` dan `result.success` seperti pada `MOBILE_API.md`.

## 3. Status dan pemilihan mode

Endpoint status juga mengembalikan field berikut setelah versi ini:

```json
{
  "attendance_mode": "wfa",
  "can_select_mode": true,
  "wfa_available": true
}
```

Interpretasi:

- `wfa_available`: apakah WFA dapat dipilih saat ini.
- `can_check_in`: sudah memperhitungkan WFA. Jadi `can_check_in=true` tetap bisa terjadi saat tidak ada lokasi terjadwal, selama WFA tersedia.
- `attendance_mode`: mode sesi aktif, atau `false` jika belum check-in.

Flow layar mode:

1. Panggil `status`.
2. Jika `can_check_in=true`, panggil `modes`.
3. Tampilkan pemilih On-Site / Work From Anywhere sesuai `available_modes`.
4. Setelah pengguna memilih, lanjut ke check-in:
   - On-Site: ambil GPS dan selfie sesuai policy lokasi.
   - WFA: GPS opsional, selfie check-in wajib.

## 4. Check-in On-Site

Tidak berubah dari `MOBILE_API.md`:

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

`attendance_mode` boleh dikosongkan untuk kompatibilitas lama; default server adalah `location`.

## 5. Check-in WFA

WFA tidak membutuhkan `work_location_id`, `latitude`, `longitude`, maupun `accuracy`. Selfie check-in **wajib**. Field minimal:

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

Request WFA dengan posisi opsional:

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

Aturan:

- Jika `latitude`, `longitude`, atau `accuracy` dikirim sebagian, ketiganya tetap divalidasi sebagai GPS (rentang valid dan `accuracy > 0`). Kosongkan semuanya agar benar-benar tanpa GPS.
- Selfie check-in wajib: raw base64 JPEG/PNG/WebP maksimum 5 MB.
- Server tetap menentukan `check_in` dan identity dari session; mobile tidak mengirim timestamp.

Response check-in WFA berhasil:

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

## 6. Check-out WFA

Check-out membaca mode dari sesi check-in aktif; mobile tidak perlu mengirim mode lagi, tetapi tetap diperbolehkan demi ketegasan audit. Selfie check-out **wajib**.

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

Response check-out WFA berhasil:

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

WFA check-out tidak memvalidasi sama-lokasi karena memang tidak ada Work Location snapshot.

## 7. Mode dalam evidence

Setiap `presenly.attendance.event` menyimpan `attendance_mode`:

- `location` untuk On-Site;
- `wfa` untuk Work From Anywhere.

HR dapat memfilter Attendance Evidence dengan filter **Work From Anywhere** dan melakukan grouping **Mode**.

## 8. Rule keamanan identitas dan waktu

Meskipun WFA longgar untuk lokasi/approval, aturan inti mobile tetap berlaku:

- Identity berasal dari session; `employee_id` tidak dapat dipilih client.
- `check_in` dan `check_out` selalu ditentukan server.
- Sesi baru ditolak bila masih ada sesi aktif.
- Checkout kedua ditolak bila tidak ada sesi aktif.
- WFA hanya mencatat `attendance_mode`; ia tidak membuat workflow izin/approval baru.

## 9. Checklist implementasi mobile mode

- [ ] Panggil `modes` setelah `status` untuk mendapatkan daftar mode.
- [ ] Render On-Site dan Work From Anywhere dari `available_modes`, bukan hardcode.
- [ ] Hormati `wfa_policy.allowed`.
- [ ] On-Site tetap meminta GPS dan selfie sesuai policy lokasi.
- [ ] WFA mengosongkan seluruh field GPS saat tanpa GPS, atau mengirim ketiganya lengkap jika ingin mencatat posisi.
- [ ] WFA selfie check-in dan check-out wajib; format raw base64 JPEG/PNG/WebP maksimum 5 MB.
- [ ] Kirim `attendance_mode` eksplisit pada check-in.
- [ ] Check-out mempercayakan mode pada sesi server, tetapi boleh mengirim `attendance_mode`.
- [ ] Timeout diselesaikan dengan `status` sebelum retry.
- [ ] Setelah check-in/out WFA selesai, panggil `status` untuk sinkronisasi UI.