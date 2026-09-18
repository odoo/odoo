# Akun UAT PPL

Dokumen ini mencatat akun dummy untuk pengujian modul **SIFNEXT PPL** pada lingkungan lokal/UAT. Akun dibuat oleh `data/ppl_uat_users.xml` ketika modul dipasang atau di-upgrade.

> **Peringatan:** jangan memuat fixture akun ini pada production. Password di bawah bersifat publik dan hanya cocok untuk lokal/UAT. Ganti password setelah login pertama bila database dapat diakses oleh pihak lain, lalu nonaktifkan akun setelah pengujian selesai.

## Akses login

- URL lokal: <http://localhost:8069/web/login>
- Database Docker bawaan: `odoo`
- Company: `My Company`/company utama database
- Unit: `Unit UAT PPL` (`UAT`)

| Pengguna | Login | Password awal | Role/grup PPL | Tanggung jawab utama |
|---|---|---|---|---|
| PPL UAT - Pegawai | `ppl_user` | `ppl_user` | Internal User | Membuat dan mengajukan PPL sendiri |
| PPL UAT - Keuangan | `ppl_finance` | `ppl_finance` | Keuangan | Mengisi COA, verifikasi, mencatat pembayaran, dan menyelesaikan PPL |
| PPL UAT - Direktur | `ppl_director` | `ppl_director` | Direktur | Menyetujui PPL yang sudah diverifikasi |

Saat ini **Finance Verifier** dan **Finance Payment** belum dipisahkan menjadi dua grup. Keduanya dijalankan oleh role dan akun `ppl_finance`.

## Matriks hak workflow

| Aksi | Pegawai | Keuangan | Direktur |
|---|:---:|:---:|:---:|
| Buat PPL | Ya | Ya | Sesuai akses internal |
| Ajukan PPL | Ya | Ya; pengajuan sendiri langsung terverifikasi jika COA lengkap | Tidak menjadi tugas utama |
| Melihat seluruh PPL dalam company | Tidak; hanya milik sendiri | Ya | Ya |
| Mengisi COA | Tidak | Ya | Tidak |
| Verifikasi | Tidak | Ya | Tidak |
| Setujui | Tidak | Tidak | Ya |
| Konfirmasi pembayaran | Tidak | Ya | Tidak |
| Selesaikan | Tidak | Ya | Tidak |

## Skenario smoke test

1. Login sebagai `ppl_user`, buka **SIFNEXT Keuangan → PPL**, buat PPL dengan minimal satu detail, lalu klik **Ajukan**.
2. Login sebagai `ppl_finance`, buka pengajuan tersebut, isi COA pada setiap detail, lalu klik **Verifikasi**.
3. Login sebagai `ppl_director`, buka PPL berstatus **Verified**, lalu klik **Setujui**.
4. Login kembali sebagai `ppl_finance`, isi metode, **sumber dana (Kas/Bank)**, tanggal, dan referensi pembayaran, klik **Konfirmasi Pembayaran**, lalu **Selesaikan**.
5. Periksa tab **Audit** dan pastikan user serta timestamp setiap tahap terisi.
6. Login kembali sebagai `ppl_user` dan pastikan pengajuan milik pegawai lain tidak terlihat.

## Pengelolaan akun

- Password dalam XML berada di blok `noupdate="1"`; upgrade modul berikutnya tidak mengembalikan password yang sudah diubah.
- Ganti password melalui **Settings → Users & Companies → Users** menggunakan akun administrator.
- Setelah UAT, nonaktifkan akun dari form user dengan menonaktifkan status **Active**.
- Untuk production, keluarkan `data/ppl_uat_users.xml` dari daftar `data` manifest sebelum deployment, atau kelola akun pengujian melalui mekanisme provisioning khusus lingkungan.
- `admin_passwd` pada `docker/odoo.conf` adalah master password pengelolaan database, bukan kredensial login Administrator.
