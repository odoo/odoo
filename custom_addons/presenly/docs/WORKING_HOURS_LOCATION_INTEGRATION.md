# Working Hours & Work Location Integration

## Konsep

Presenly memakai dua lapisan yang saling terintegrasi:

- **Working Hours** native Odoo (`resource.calendar` dan `resource.calendar.attendance`) menentukan kapan Employee bekerja.
- **Work Location Schedule** (`presenly.work.location.schedule`) menentukan lokasi fisik selama jam kerja tersebut.

Working Hours tetap menjadi sumber otoritatif untuk perhitungan jam kerja, Time Off, dan Attendance Odoo. Presenly tidak menduplikasi kalender kerja.

## UI terpadu pada Employee

Buka:

```text
Employees > Employees > pilih Employee > Working Hours & Locations
```

Tab menampilkan:

1. Working Hours aktif.
2. Primary/Fallback Work Location.
3. Status Location Coverage.
4. Jumlah Unassigned Periods.
5. Jumlah Conflicting Slots.
6. Editor Location Slots langsung pada Employee.
7. Tombol Open Working Hours.
8. Tombol Generate from Working Hours.
9. Tombol Open Full Schedule.

### Status coverage

| Status | Arti |
|---|---|
| Fully Assigned | Semua periode Working Hours reguler telah memiliki lokasi |
| Working Hours Have Gaps | Ada periode Working Hours yang belum diberi lokasi |
| Schedule Conflict | Ada slot lokasi di luar Working Hours aktif |
| Flexible Working Hours | Kalender fleksibel tidak memiliki periode jam tetap untuk dipetakan |
| No Working Hours | Employee belum memiliki Working Hours |

## Generate from Working Hours

Klik **Generate from Working Hours** pada tab Employee.

### Fill Unassigned Working Hours

Mode default dan paling aman. Wizard hanya membuat preview untuk bagian Working Hours yang belum mempunyai lokasi. Slot yang sudah ada tidak diubah.

Langkah:

1. Pilih Default Work Location bila diperlukan.
2. Periksa hari, Week 1/Week 2, dan jam pada preview.
3. Ubah Work Location per baris.
4. Bila satu periode dibagi ke dua sekolah, ubah End Time baris pertama lalu tambahkan baris kedua untuk sisa waktunya.
5. Tentukan Check-In Tolerance.
6. Klik **Generate Location Slots**.

Contoh Working Hours:

```text
Monday 07:00–11:00
Monday 13:00–16:00
```

Contoh preview lokasi:

```text
Monday 07:00–09:00  School A
Monday 09:00–11:00  School B
Monday 13:00–16:00  School B
```

### Replace All Weekly Location Slots

Mode ini menghapus seluruh slot lokasi **Weekly** Employee lalu membangunnya kembali dari preview. Specific Date tetap dipertahankan. Gunakan ketika Working Hours berubah besar atau jadwal lokasi reguler perlu dibangun ulang.

## Editor inline

Location Slots dapat diedit langsung pada tab Employee atau melalui:

```text
Attendances > Configuration > Work Location Schedules
```

Kolom penting:

- Schedule Type: Weekly atau Specific Date.
- Weekday.
- Calendar Week untuk kalender dua-mingguan.
- Specific Date.
- Start Time dan End Time.
- Work Location.
- Working Hours Status.
- Check-In Tolerance.
- Valid From/Until.

Form slot otomatis mengusulkan interval pertama yang sesuai saat Employee/hari/tanggal dipilih.

## Aturan validasi

1. Employee dan Work Location harus berada pada Company yang sama.
2. Slot aktif harus berada sepenuhnya di dalam satu periode Working Hours.
3. Slot Employee tidak boleh overlap pada scope jadwal yang sama.
4. Kalender dua-mingguan mewajibkan Week 1 atau Week 2.
5. Specific Date memakai Working Hours versi Employee yang berlaku pada tanggal tersebut.
6. Flexible Working Hours tidak mewajibkan containment jam tetap; gunakan lokasi native/fallback bila tidak membutuhkan slot.
7. Slot yang invalid akibat perubahan Working Hours tidak digunakan oleh attendance resolver.
8. Slot konflik tetap dapat diarsipkan agar admin dapat membersihkan konfigurasi.

## Perubahan Working Hours

Saat admin mengubah Working Hours native:

- Status coverage pada Employee dihitung ulang.
- Slot yang tidak lagi sesuai ditandai **Outside Working Hours**.
- Attendance resolver mengabaikan slot konflik.
- Admin dapat memperbaiki jam slot, mengarsipkannya, atau menggunakan Replace All Weekly Location Slots.

Presenly tidak mengubah/menghapus slot otomatis ketika kalender berubah agar histori konfigurasi tidak hilang tanpa tindakan admin.

## Resolver attendance

Hanya slot aktif dan sinkron dengan Working Hours yang dipertimbangkan. Prioritas tetap:

1. Specific Date slot.
2. Weekly slot sesuai Week 1/Week 2.
3. Exceptional Location native.
4. Native weekday location.
5. Primary Work Location.

Jika terdapat slot valid yang mengontrol hari tersebut tetapi waktu check-in berada di luar slot, fallback lokasi tidak digunakan dan check-in ditolak.

## Hak akses

- Presenly Administrator mewarisi native HR Officer agar dapat membuka Employee dan mengelola Working Hours.
- Employee hanya dapat membaca schedule miliknya.
- Presenly Administrator dapat membuat, mengubah, mengarsipkan, menghapus, dan generate Location Slots dalam allowed companies.
- Record rule multi-company tetap berlaku.

## Checklist admin

1. Pastikan Employee mempunyai Company yang benar.
2. Pilih Working Hours pada Employee.
3. Pilih Primary Work Location sebagai fallback.
4. Buka tab Working Hours & Locations.
5. Klik Generate from Working Hours.
6. Assign Work Location pada setiap preview.
7. Pastikan status berubah menjadi Fully Assigned.
8. Konfigurasikan koordinat/geofence setiap Work Location.
9. Uji check-in melalui API/mobile pada slot aktif.
