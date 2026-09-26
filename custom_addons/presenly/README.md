# Presenly Attendance Tools

Presenly adalah addon teknis Odoo 19 yang memperluas aplikasi native **Attendances** dengan geofence, selfie evidence, jadwal lokasi per jam, permission/dispensation, mobile API, dan approval bertingkat. Seluruh UI operasional berada di aplikasi Attendances.

## Arsitektur organisasi

| Konsep | Model |
|---|---|
| Legal entity | `res.company` |
| Sekolah, cabang, kantor, atau tempat fisik | `hr.work.location` |
| Struktur organisasi | `hr.department` |
| Lokasi utama/fallback employee | `hr.employee.work_location_id` |
| Lokasi reguler per hari | Field lokasi Senin–Minggu native Odoo |
| Lokasi khusus satu tanggal | `hr.employee.location` native Odoo |
| Beberapa lokasi dalam satu hari | `presenly.work.location.schedule` |
| Absensi resmi | `hr.attendance` |
| Cuti resmi | `hr.leave` |

`presenly.employee.assignment` telah dihentikan dan tidak lagi tersedia pada workflow atau UI. Guru yang mengajar di beberapa sekolah pada hari yang sama dikonfigurasi menggunakan beberapa **Work Location Schedule** berdasarkan jam.

Contoh Senin:

```text
07:00–11:00  Sekolah A
13:00–16:00  Sekolah B
```

Setiap sesi menghasilkan record `hr.attendance` terpisah. Guru harus check-out dari sesi pertama sebelum check-in ke sesi berikutnya.

## Integrasi Working Hours dan Work Location

Working Hours native Odoo (`resource.calendar`) adalah sumber otoritatif **kapan** Employee bekerja. Work Location Schedule Presenly menentukan **di mana** Employee bekerja di dalam periode tersebut.

Pada form Employee tersedia tab **Working Hours & Locations** dengan:

- Working Hours dan Primary/Fallback Work Location dalam satu layar.
- Status coverage: Fully Assigned, Working Hours Have Gaps, Schedule Conflict, Flexible Working Hours, atau No Working Hours.
- Jumlah periode yang belum diberi lokasi dan slot yang konflik.
- Editor Location Slot inline dengan indikator sinkronisasi berwarna.
- Tombol **Open Working Hours** untuk kalender native Odoo.
- Tombol **Generate from Working Hours** untuk membuat preview slot lokasi tanpa mengetik ulang hari/jam.
- Mode **Fill Unassigned Working Hours** dan **Replace All Weekly Location Slots**.
- Preview dapat dipecah menjadi beberapa sekolah dalam satu periode kerja.

Slot aktif baru wajib berada sepenuhnya di dalam Working Hours. Jika Working Hours berubah sehingga slot lama menjadi invalid, slot ditandai Conflict, diabaikan oleh resolver attendance, dan tetap dapat diarsipkan/diperbaiki. Kalender dua-mingguan didukung melalui Week 1/Week 2. Specific Date divalidasi terhadap Working Hours yang berlaku pada tanggal tersebut.

## Prioritas penentuan lokasi

1. Slot **Specific Date** untuk tanggal dan jam saat ini.
2. Slot **Weekly** untuk hari dan jam saat ini.
3. Exceptional Location native Odoo untuk tanggal tersebut.
4. Lokasi native berdasarkan hari Senin–Minggu.
5. Work Location utama Employee sebagai fallback.

Jika ada jadwal slot untuk hari tersebut tetapi waktu saat ini berada di luar semua slot, check-in ditolak. Specific Date menggantikan seluruh slot Weekly pada tanggal itu.

## Fitur

- Check-in/check-out menggunakan `hr.attendance`.
- Geofence dengan radius default 150 meter per `hr.work.location`.
- Koordinat berasal dari Work Address (`res.partner`).
- Check-out harus memakai Work Location yang sama dengan check-in.
- Selfie check-in/check-out dapat diwajibkan per Work Location.
- Attendance menyimpan snapshot Company, Work Location, dan Schedule.
- Slot seorang employee tidak boleh tumpang tindih.
- Evidence berhasil dan percobaan gagal disimpan privat.
- Cuti menggunakan `hr.leave`; izin/dispensasi menggunakan `presenly.permission`.
- Presenly Approval Routes adalah satu-satunya jalur approval untuk Permission dan Time Off.
- Rantai approval disnapshot saat submission sehingga perubahan rule/manager tidak mengubah request berjalan.
- Final Time Off approval tetap memanggil engine native Odoo untuk allocation, kalender, durasi, dan work entries.
- Approval dapat berlaku company-wide atau spesifik Work Location.
- API `/api/presenly/v1` menggunakan session authentication standar Odoo.

## Dependency

```text
hr
hr_attendance
hr_holidays
hr_homeworking
mail
```

## Lokasi UI

- **Attendances > Overview**: My Permissions / Dispensations dan My Time Off.
- **Attendances > Approvals > My Approvals**: antrean terpadu Permission dan Time Off untuk level aktif user.
- **Attendances > Reporting**: Attendance Evidence, Permissions, dan Time Off.
- **Attendances > Configuration > Companies**: legal entity.
- **Attendances > Configuration > Work Locations**: sekolah/cabang dan kebijakan geofence.
- **Attendances > Configuration > Work Location Schedules**: jadwal sekolah berdasarkan hari/tanggal dan jam.
- **Attendances > Configuration > Permission Types / Approval Routes**: workflow izin dan cuti. Mulai konfigurasi dari smart button Approval Steps pada jenis request.
- Form Employee memiliki smart button **Location Schedules**.
- Form Attendance menampilkan Company, Work Location, Schedule, source, jarak, dan Evidence.

## Konfigurasi minimum

1. Buat/pilih Company.
2. Buat Work Location, pilih Work Address, dan isi koordinat address.
3. Atur radius, batas akurasi GPS, selfie policy, dan Location Manager.
4. Set Work Location utama pada Employee sebagai fallback.
5. Gunakan lokasi per hari native jika hanya ada satu lokasi per hari.
6. Buat **Work Location Schedules** jika satu hari memiliki beberapa lokasi atau membutuhkan batas jam.
7. Buka setiap Permission Type dan Time Off Type, lalu susun Approval Steps melalui smart button. Gunakan menu Approval Routes hanya untuk overview lintas jenis request.
8. Pastikan setiap user yang terpilih sebagai approver mempunyai role **Presenly Approver** dan Allowed Company yang sesuai.

## Single-path Approval Journey

Semua Permission dan Time Off request masuk melalui Presenly Approval Routes. Tombol dan method approval native Time Off tidak dapat membypass journey. Setiap submission membuat snapshot step dan assigned approvers; perubahan konfigurasi hanya berlaku pada request berikutnya.

Alur:

```text
Draft → Submit → Level 1 → ... → Level N → Approved/Rejected
```

- Permission selesai sebagai `presenly.permission.state = approved`.
- Time Off level terakhir memvalidasi `hr.leave` melalui engine native Odoo.
- Reject wajib memiliki alasan.
- Request tanpa flow lengkap atau approver ber-role Presenly Approver ditolak saat submission.
- Extra Hours tetap menggunakan approval native Attendances dan tidak termasuk journey ini.

## Mobile API login dan presensi

Kontrak mobile aktif difokuskan pada autentikasi dan presensi. Presenly menggunakan session authentication standar Odoo 19:

1. Login melalui `POST /web/session/authenticate`.
2. Simpan cookie `session_id` secara aman.
3. Baca status melalui `POST /api/presenly/v1/attendance/status`.
4. Kirim GPS dan selfie melalui endpoint check-in/check-out.
5. Logout melalui `POST /web/session/destroy`.

Dokumentasi lengkap API mobile (login, session, format JSON-RPC, error handling, attendance, WFA, Time Off, Permission, Overtime, approval) tersedia dalam satu file kanonik: [`docs/MOBILE_API_FULL.md`](docs/MOBILE_API_FULL.md). Pemeriksaan login/session/status dapat dijalankan dengan:

```bash
BASE_URL=http://127.0.0.1:8069 \
DB=odoo \
LOGIN='employee@example.com' \
PASSWORD='USER_PASSWORD' \
./custom_addons/presenly/scripts/check_mobile_api.sh
```

## API compatibility

`work_location_id` adalah field kanonis. Selama masa transisi kontrak API, `unit_id` tetap diterima sebagai alias untuk ID `hr.work.location`. Alias tersebut tidak menunjuk model Unit custom; model dan tabel Unit/Location legacy telah dihentikan.

## Security

Employee hanya dapat membaca jadwal, evidence, permission, dan approval log miliknya. HR/Manager dibatasi oleh allowed companies. Approver hanya melihat request yang sedang atau pernah ditugaskan kepadanya. Attachment selfie dan dokumen izin bersifat private.

## Validasi

```bash
source odoo-venv/bin/activate
python -m compileall -q custom_addons/presenly
./odoo-bin server -c odoo.conf -d odoo -u presenly \
  --test-enable --test-tags /presenly --stop-after-init \
  --http-port=18069 --http-interface=127.0.0.1 --max-cron-threads=0
```

## Cleanup schema legacy

Upgrade `19.0.5.0.0` menghapus model, field, ACL, rule, action, menu, dan tabel Unit/Location legacy. Migration bersifat idempotent dan guarded: tabel hanya dijatuhkan ketika lokasi legacy kosong dan seluruh foreign key legacy tidak berisi nilai. Database lain yang masih mempunyai data legacy akan mempertahankan schema dan mencatat warning untuk migrasi manual—data tidak dibuang diam-diam.

Alias `unit_id` pada API tetap tersedia sebagai alias `work_location_id` sehingga cleanup database tidak memutus kontrak mobile sementara.

## Batasan

- DeepFace belum diaktifkan.
- Payroll/lembur dan offline mobile belum termasuk.
- Mobile client bukan bagian addon ini; addon menyediakan backend JSON-RPC, session auth, geofence, evidence, dan workflow.
