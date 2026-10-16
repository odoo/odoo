# Presenly Mobile API — Login dan Presensi

Dokumen ini membahas autentikasi session Odoo dan presensi mobile: status, check-in, check-out, GPS/geofence, selfie, dan validasi.

## 1. Ringkasan integrasi

Base URL lokal:

```text
http://127.0.0.1:8069
```

Production wajib memakai HTTPS.

Urutan aplikasi mobile:

1. Login melalui `POST /web/session/authenticate`.
2. Simpan cookie `session_id` secara aman.
3. Panggil `POST /api/presenly/v1/attendance/status`.
4. Jika `can_check_in=true`, ambil GPS dan foto selfie lalu kirim check-in.
5. Jika `can_check_out=true`, ambil GPS dan foto selfie baru lalu kirim check-out.
6. Panggil status lagi setelah transaksi untuk menyinkronkan UI.
7. Logout melalui `POST /web/session/destroy` dan hapus cookie lokal.

Presenly menggunakan session cookie native Odoo 19, bukan JWT custom. Semua waktu check-in/check-out ditentukan server. Mobile tidak boleh dan tidak dapat mengirim `employee_id`, `check_in`, atau `check_out`.

## 2. Endpoint yang digunakan

| Fungsi | Method | Endpoint | Auth |
|---|---|---|---|
| Login | POST | `/web/session/authenticate` | Public credentials |
| Cek session | POST | `/web/session/get_session_info` | Session |
| Daftar mode | POST | `/api/presenly/v1/attendance/modes` | Session |
| Status presensi | POST | `/api/presenly/v1/attendance/status` | Session |
| Check-in | POST | `/api/presenly/v1/attendance/check-in` | Session |
| Check-out | POST | `/api/presenly/v1/attendance/check-out` | Session |
| Logout | POST | `/web/session/destroy` | Session |

Tidak ada endpoint login custom Presenly. Login selalu menggunakan endpoint session resmi Odoo.

Pemilihan mode On-Site / Work From Anywhere dibahas khusus di [`MOBILE_MODE_SELECTION.md`](MOBILE_MODE_SELECTION.md).

Referensi API khusus Work From Anywhere ada di [`MOBILE_WFA_API.md`](MOBILE_WFA_API.md).

Referensi API Time Off / Cuti beserta approval leveling ada di [`MOBILE_TIMEOFF_API.md`](MOBILE_TIMEOFF_API.md).

Referensi approval (list antrean atasan, approve/reject, pengajuan Time Off & Permission) ada di [`MOBILE_APPROVAL_API.md`](MOBILE_APPROVAL_API.md). Kebijakan dan roadmap penyempurnaan API approval ada di [`PLAN_APPROVAL_API.md`](PLAN_APPROVAL_API.md).

Referensi API Overtime / Lembur (durasi server-side, jam 24H, approval, lokasi otomatis) ada di [`MOBILE_OVERTIME_API.md`](MOBILE_OVERTIME_API.md).

Pengertian & rencana otomatisasi Work Location (attendance & pengajuan) ada di [`PLAN_AUTO_WORK_LOCATION.md`](PLAN_AUTO_WORK_LOCATION.md).

## 3. Format JSON-RPC

Semua endpoint pada dokumen ini menggunakan HTTP `POST` dengan header:

```http
Content-Type: application/json
```

Envelope request:

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 1
}
```

Data endpoint wajib ditempatkan langsung di object `params`. Jangan membungkus lagi dengan key `payload` atau `data`.

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

Error autentikasi atau validasi Odoo dikirim pada properti JSON-RPC `error`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": 100,
    "message": "Odoo Session Expired",
    "data": {
      "name": "odoo.http.SessionExpiredException",
      "message": "Session expired"
    }
  }
}
```

HTTP 200 tidak selalu berarti transaksi berhasil. Client wajib memeriksa:

1. Jika response mempunyai `error`, transaksi gagal.
2. Jika tidak ada `error`, pastikan `result.success === true`.
3. Gunakan data hanya dari `result.data`.

Jangan menampilkan `error.data.debug` kepada pengguna production dan jangan mengirimnya ke analytics publik.

## 4. Login

### Endpoint

```http
POST /web/session/authenticate
```

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "db": "odoo",
    "login": "employee@example.com",
    "password": "USER_PASSWORD"
  },
  "id": 1
}
```

### Response login berhasil

Bagian penting response:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "uid": 12,
    "username": "employee@example.com",
    "db": "odoo"
  }
}
```

Login dianggap berhasil hanya jika:

- response tidak mempunyai `error`;
- `result.uid` berisi ID user;
- response membuat cookie `session_id`;
- user aktif dan mempunyai Employee aktif yang terhubung melalui Related User.

### Contoh curl login

```bash
BASE_URL=http://127.0.0.1:8069
DB=odoo
LOGIN=employee@example.com
PASSWORD='USER_PASSWORD'
COOKIE_JAR=/tmp/presenly-cookie.txt

curl --fail-with-body --silent --show-error \
  -c "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -X POST "$BASE_URL/web/session/authenticate" \
  --data "$(jq -n \
    --arg db "$DB" \
    --arg login "$LOGIN" \
    --arg password "$PASSWORD" \
    '{jsonrpc:"2.0",method:"call",params:{db:$db,login:$login,password:$password},id:1}')" \
  | jq
```

Untuk request berikutnya, kirim cookie dengan `-b "$COOKIE_JAR"` dan simpan pembaruan cookie dengan `-c "$COOKIE_JAR"`.

### Penyimpanan session

- Perlakukan `session_id` sebagai secret.
- Gunakan cookie jar yang mendukung `HttpOnly` dan `Secure`.
- Jangan simpan password setelah login.
- Jangan mencatat password, cookie, atau selfie pada log aplikasi.
- iOS: gunakan `HTTPCookieStorage`; jika perlu menyalin secret, gunakan Keychain.
- Android: gunakan cookie jar/`CookieManager`; jika perlu persistensi custom, gunakan encrypted storage.
- Flutter/React Native: gunakan cookie manager persisten yang terenkripsi dan mendukung cookie `HttpOnly`.

## 5. Cek session

### Endpoint native

```http
POST /web/session/get_session_info
```

Request:

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 2
}
```

Endpoint status Presenly juga dapat digunakan untuk memverifikasi session sekaligus relasi User–Employee.

Jika session expired:

1. Hapus cookie lokal.
2. Hapus state attendance lokal yang belum dikonfirmasi server.
3. Arahkan pengguna ke layar login.
4. Jangan mengulang check-in/out otomatis setelah login tanpa konfirmasi pengguna.

## 6. Status presensi

### Endpoint

```http
POST /api/presenly/v1/attendance/status
```

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 3
}
```

### Response ketika belum check-in dan lokasi siap

```json
{
  "jsonrpc": "2.0",
  "id": 3,
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
      "can_select_mode": true,
      "wfa_available": true,
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
      ]
    },
    "error": null
  }
}
```

### Response ketika sedang check-in

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
      "schedule_id": 15
    },
    "error": null
  }
}
```

Response nyata tetap menyertakan field identitas dan `available_work_locations` seperti contoh lengkap sebelumnya.

### Aturan UI berdasarkan status

| Kondisi | Tombol Check-In | Tombol Check-Out |
|---|---:|---:|
| `can_check_in=true` | Aktif | Nonaktif |
| `can_check_out=true` | Nonaktif | Aktif |
| Keduanya `false` | Nonaktif | Nonaktif |

Jangan menentukan state hanya dari cache mobile. Panggil endpoint status saat:

- aplikasi dibuka;
- login selesai;
- aplikasi kembali dari background;
- check-in/check-out selesai;
- request sebelumnya timeout dan hasil akhirnya belum diketahui.

Jika request mutasi timeout, panggil status lebih dulu. Jangan langsung mengulang request karena transaksi server mungkin sudah berhasil.

## 7. Mengambil GPS dan selfie

Sebelum check-in/check-out:

1. Minta izin kamera dan precise location.
2. Ambil koordinat terbaru, bukan cache lama.
3. Tunggu sampai `accuracy` tersedia dan positif.
4. Bandingkan accuracy dengan `gps_accuracy_limit_meters` dari status untuk memberi peringatan dini.
5. Ambil selfie baru untuk event tersebut.
6. Kompres foto bila perlu, tetapi pertahankan format JPEG, PNG, atau WebP.
7. Encode seluruh file menjadi base64 tanpa prefix data URL.
8. Kirim request hanya sekali dan tampilkan loading sampai response diterima.

Contoh benar:

```text
/9j/4AAQSkZJRgABAQAAAQABAAD...
```

Contoh salah:

```text
data:image/jpeg;base64,/9j/4AAQSkZJRg...
```

Ketentuan selfie:

- format: JPEG, PNG, atau WebP;
- maksimum: 5 MB setelah base64 didecode;
- base64 harus valid dan tidak kosong;
- file harus dapat didecode sebagai gambar aman;
- attachment disimpan privat di Odoo;
- selfie check-in dan check-out adalah dua foto terpisah;
- jangan menyimpan selfie pada log atau analytics;
- jangan kirim ulang selfie jika status server sudah menunjukkan transaksi berhasil.

## 8. Check-in

### Endpoint

```http
POST /api/presenly/v1/attendance/check-in
```

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
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

### Field request

| Field | Tipe | Wajib | Keterangan |
|---|---|---:|---|
| `work_location_id` | integer | Disarankan | ID lokasi dari `available_work_locations`. Jika kosong, server memilih lokasi aktif yang geofence-nya cocok. |
| `latitude` | number | Ya | Rentang `-90` sampai `90`. |
| `longitude` | number | Ya | Rentang `-180` sampai `180`. |
| `accuracy` | number | Ya | Akurasi GPS dalam meter, harus lebih besar dari `0`. |
| `selfie` | string | Sesuai policy | Raw base64 JPEG/PNG/WebP, maksimum 5 MB. Umumnya wajib. |
| `device_id` | string | Tidak | 1–255 karakter. Server hanya menyimpan SHA-256, bukan nilai mentah. |

`unit_id` masih diterima sementara sebagai alias lama untuk `work_location_id`, tetapi aplikasi baru harus memakai `work_location_id`.

### Response berhasil

```json
{
  "jsonrpc": "2.0",
  "id": 10,
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
      "validation": {
        "status": "success",
        "geofence_valid": true,
        "distance_meters": 12.34,
        "accuracy_meters": 8.5,
        "selfie_received": true
      }
    },
    "error": null
  }
}
```

Check-in berhasil hanya jika seluruh validasi berikut lulus:

- session valid;
- user mempunyai Employee aktif;
- company Employee terdapat pada Allowed Companies user;
- Employee belum mempunyai sesi attendance aktif;
- ada Work Location yang berlaku pada waktu server saat ini;
- lokasi yang dipilih sesuai jadwal;
- Work Location geofence-ready;
- koordinat berada dalam geofence;
- accuracy tidak melebihi policy lokasi;
- selfie tersedia jika diwajibkan dan file valid.

Server membuat:

1. satu record native `hr.attendance`;
2. snapshot Company, Work Location, dan Schedule;
3. satu `presenly.attendance.event` check-in;
4. attachment selfie privat jika dikirim;
5. jarak hasil validasi geofence.

### Contoh curl check-in

```bash
LAT=-7.1697742
LON=112.6495932
ACCURACY=8.5
LOCATION_ID=7
SELFIE_BASE64="$(base64 < selfie.jpg | tr -d '\n')"

curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -X POST "$BASE_URL/api/presenly/v1/attendance/check-in" \
  --data "$(jq -n \
    --argjson location "$LOCATION_ID" \
    --argjson latitude "$LAT" \
    --argjson longitude "$LON" \
    --argjson accuracy "$ACCURACY" \
    --arg selfie "$SELFIE_BASE64" \
    '{jsonrpc:"2.0",method:"call",params:{work_location_id:$location,latitude:$latitude,longitude:$longitude,accuracy:$accuracy,selfie:$selfie},id:10}')" \
  | jq
```

## 9. Check-out

### Endpoint

```http
POST /api/presenly/v1/attendance/check-out
```

### Request

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {
    "work_location_id": 7,
    "latitude": -7.1697750,
    "longitude": 112.6495940,
    "accuracy": 7.0,
    "selfie": "NEW_BASE64_IMAGE_WITHOUT_DATA_URL_PREFIX",
    "device_id": "OPTIONAL_STABLE_DEVICE_IDENTIFIER"
  },
  "id": 11
}
```

Field dan format sama dengan check-in. Selfie harus foto baru untuk check-out.

Check-out selalu menggunakan Work Location yang disnapshot saat check-in. Walaupun jadwal atau primary location berubah setelah check-in, employee harus check-out pada geofence lokasi sesi aktif tersebut.

### Response berhasil

```json
{
  "jsonrpc": "2.0",
  "id": 11,
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
      "validation": {
        "status": "success",
        "geofence_valid": true,
        "same_work_location": true,
        "distance_meters": 13.01,
        "accuracy_meters": 7.0,
        "selfie_received": true
      }
    },
    "error": null
  }
}
```

Check-out berhasil hanya jika:

- Employee mempunyai sesi check-in aktif;
- `work_location_id` sama dengan lokasi snapshot check-in;
- lokasi snapshot masih geofence-ready;
- GPS berada dalam geofence lokasi tersebut;
- accuracy memenuhi policy;
- selfie valid jika diwajibkan.

Setelah berhasil, panggil status. Hasil yang diharapkan:

```json
{
  "state": "checked_out",
  "can_check_in": true,
  "can_check_out": false,
  "attendance_id": false
}
```

`can_check_in` dapat tetap `false` jika waktu sekarang tidak mempunyai lokasi terjadwal atau lokasi belum geofence-ready.

## 10. Pemilihan Work Location

Resolver server mengikuti urutan:

1. Specific Date Work Location Schedule;
2. Weekly Work Location Schedule;
3. native exceptional Employee Work Location;
4. native weekday Employee Work Location;
5. Employee primary Work Location.

Aturan penting:

- Specific Date menggantikan seluruh Weekly schedule pada tanggal itu.
- Jika hari dikontrol time slot dan waktu sekarang berada di luar slot, check-in ditolak; server tidak fallback ke primary location.
- Beberapa lokasi dalam satu hari menggunakan slot non-overlap.
- Sesi lokasi sebelumnya harus di-check-out sebelum check-in di lokasi berikutnya.
- `work_location_id` dari mobile harus termasuk lokasi aktif pada waktu server.
- Check-out harus menggunakan lokasi snapshot check-in yang sama.

Jika status mengembalikan beberapa `available_work_locations`, mobile dapat:

- memilih lokasi berdasarkan pilihan pengguna; atau
- meminta server memilih dengan tidak mengirim `work_location_id`.

Disarankan menampilkan pilihan lokasi dan selalu mengirim ID yang dipilih agar UI dan audit eksplisit.

## 11. Validasi dan pesan error

Error bisnis muncul pada JSON-RPC `error.data.message`. Client sebaiknya memetakan pesan ke UX berikut.

| Kondisi | Perilaku mobile |
|---|---|
| Session expired | Hapus cookie dan kembali ke login. |
| User tidak mempunyai Employee aktif | Tampilkan instruksi menghubungi Administrator. |
| Company tidak ada di Allowed Companies | Tampilkan instruksi menghubungi Administrator. |
| Tidak ada lokasi terjadwal | Nonaktifkan check-in dan tampilkan pesan status. |
| Lokasi belum geofence-ready | Nonaktifkan check-in dan minta Administrator melengkapi koordinat/policy. |
| Lokasi berbeda dari jadwal | Refresh status dan gunakan lokasi dari server. |
| Di luar geofence | Tampilkan jarak/lokasi, minta pengguna berpindah dan ambil GPS ulang. |
| GPS accuracy terlalu buruk | Minta pengguna mengaktifkan precise location, berpindah ke area terbuka, lalu retry manual. |
| Selfie wajib | Buka kamera dan ambil foto baru. |
| Base64/file foto tidak valid | Encode ulang file JPEG/PNG/WebP tanpa data URL prefix. |
| Foto melebihi 5 MB | Kompres atau resize sebelum dikirim ulang. |
| Sudah check-in | Refresh status dan tampilkan tombol check-out. |
| Tidak ada check-in aktif | Refresh status dan tampilkan tombol check-in. |
| Check-out berbeda lokasi | Arahkan pengguna ke Work Location check-in. |
| Network timeout | Panggil status sebelum melakukan retry. |

Contoh mengambil pesan aman:

```javascript
function parsePresenlyResponse(body) {
  if (body.error) {
    const message = body.error?.data?.message || body.error.message || 'Request gagal';
    throw new Error(message);
  }
  if (!body.result?.success) {
    throw new Error(body.result?.error || 'Request gagal');
  }
  return body.result.data;
}
```

## 12. Idempotensi dan retry

Endpoint check-in/out tidak menerima client timestamp dan tidak mempunyai idempotency key. Gunakan aturan berikut:

- Disable tombol ketika request sedang berlangsung.
- Jangan mengirim request paralel.
- Setelah timeout, panggil status.
- Jika status sudah `checked_in`, jangan ulang check-in.
- Jika status sudah `checked_out`, jangan ulang check-out.
- Retry hanya setelah status membuktikan transaksi sebelumnya belum terjadi.

Backend juga melindungi state:

- check-in kedua ditolak bila sesi aktif masih ada;
- check-out kedua ditolak bila tidak ada sesi aktif;
- native `hr.attendance` mencegah sesi overlap.

## 13. Logout

### Endpoint

```http
POST /web/session/destroy
```

Request:

```json
{
  "jsonrpc": "2.0",
  "method": "call",
  "params": {},
  "id": 20
}
```

Contoh curl:

```bash
curl --fail-with-body --silent --show-error \
  -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -X POST "$BASE_URL/web/session/destroy" \
  --data '{"jsonrpc":"2.0","method":"call","params":{},"id":20}' \
  | jq
rm -f "$COOKIE_JAR"
```

Setelah logout:

- hapus cookie dan data profil lokal;
- jangan hapus bukti transaksi yang sudah dikonfirmasi server;
- request status dengan cookie lama harus menghasilkan authentication/session error.

## 14. Konfigurasi backend minimum

Sebelum mobile dapat digunakan, Administrator harus memastikan:

### User

```text
Settings
→ Users & Companies
→ Users
```

- user aktif;
- tipe Internal User;
- memiliki role Presenly Employee;
- Allowed Companies mencakup company Employee.

### Employee

```text
Employees
→ Employees
→ pilih Employee
→ Work Information
```

- Related User terhubung ke akun login;
- Company benar;
- Working Hours terisi;
- Work Location atau Work Location Schedule tersedia.

### Work Location

```text
Attendances
→ Configuration
→ Work Locations
```

- lokasi aktif;
- Company sama dengan Employee;
- Address tersedia;
- latitude dan longitude berbentuk desimal valid;
- Geofence Radius lebih dari 0;
- GPS Accuracy Limit lebih dari 0;
- status Geofence Ready aktif;
- policy selfie check-in/check-out sesuai kebutuhan.

Contoh koordinat valid:

```text
Latitude:  -7.1697742
Longitude: 112.6495932
```

Bukan integer tanpa titik desimal seperti `-71697741636479400`.

### Jadwal lokasi

```text
Employees
→ Employees
→ pilih Employee
→ Working Hours & Locations
```

Pastikan waktu kerja memiliki Work Location yang berlaku. Untuk beberapa lokasi dalam satu hari, buat slot non-overlap sesuai Working Hours.

## 15. Smoke test login dan status

Gunakan script repository:

```bash
BASE_URL=http://127.0.0.1:8069 \
DB=odoo \
LOGIN='employee@example.com' \
PASSWORD='USER_PASSWORD' \
./custom_addons/presenly/scripts/check_mobile_api.sh
```

Script memeriksa:

1. web server aktif;
2. login menghasilkan `uid` dan cookie `session_id`;
3. status Presenly mengenali Employee;
4. logout berhasil;
5. cookie yang dihancurkan tidak dapat mengakses status.

Script tidak melakukan check-in/check-out agar tidak membuat transaksi attendance tanpa koordinat dan selfie nyata.

## 16. Checklist implementasi mobile

- [ ] Base URL production memakai HTTPS.
- [ ] Request memakai JSON-RPC dan data berada langsung pada `params`.
- [ ] Cookie `session_id` dipertahankan antar-request.
- [ ] Login memeriksa `result.uid`, bukan hanya HTTP 200.
- [ ] Semua response memeriksa properti `error`.
- [ ] Status dipanggil saat startup, resume, dan setelah mutasi.
- [ ] Tombol mengikuti `can_check_in` dan `can_check_out`.
- [ ] GPS terbaru mempunyai `accuracy > 0`.
- [ ] Selfie berupa raw base64 JPEG/PNG/WebP maksimal 5 MB.
- [ ] Data URL prefix dihapus.
- [ ] Selfie, password, dan cookie tidak dicatat pada log.
- [ ] Tombol dinonaktifkan saat request berlangsung.
- [ ] Timeout diselesaikan dengan status check sebelum retry.
- [ ] Logout menghapus cookie lokal.
