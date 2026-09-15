# Plan: Akses Penghapusan & Pengelolaan Data Presensi (Presenly)

> **Versi target:** 19.0.14.x (update modul `presenly`, tanpa migrasi schema)
> **Masalah:** Administrator (`presenly.group_presenly_manager`) tidak dapat menghapus
> data absensi (`hr.attendance`) dan sebagian besar data Presenly lainnya, meskipun
> ACL sudah memberikan `perm_unlink`. HR Officer juga belum punya jalur pengelolaan
> data presensi yang terkontrol (hanya baca/ubah, tidak bisa hapus sama sekali).

## 1. Diagnosis Akar Masalah

Penghapusan diblokir di **tiga lapis terpisah**:

| Lapis | Lokasi | Efek |
|---|---|---|
| 1. Python guard model | `models/presenly_attendance.py` `HrAttendance.unlink()` | `raise ValidationError` untuk **semua** user, termasuk `sudo`/Administrator |
| 1. Python guard model | `models/presenly_approval.py` `PresenlyApprovalRequest.unlink()` & `PresenlyApprovalStep.unlink()` | `raise UserError` tanpa pengecualian (immutable) |
| 2. UI/action context | `views/hr_attendance_integration_views.xml`, `views/presenly_*_views.xml`, `presenly_menus.xml` | `delete="0"` / `'delete': False` di view list/form & action |
| 3.a ACL | `security/ir.model.access.csv` | Sudah benar: `group_presenly_manager` = `perm_unlink 1` pada semua model custom (kecuali approval request/step hanya baca — sengaja) |
| 3.b Record rules | `security/presenly_rules.xml` | Sudah benar: HR/Manager melihat semua company; Admin tidak dibatasi |

Kesimpulan: **yang harus diubah adalah lapis 1 (guard model) dan lapis 2 (UI)**,
plus **ACL HR** untuk membuka jalur delete terbatas bagi `group_presenly_hr`.
`presenly.approval.request`/`step` TIDAK dibuka ke UI umum (cascade internal saja).

Celah penting: gap antara Admin (full) dan Employee (nol) saat ini kosong — HR tidak
punya wewenang penghapusan apa pun. Plan ini mengisi gap tersebut dengan kebijakan
HR berbatasan (lihat §2.4).

---

## 2. Matriks Data yang Bisa Dihapus (Kebijakan Usulan)

Legenda status lapis masalah:
- 🔒 Model-guard: diblokir di Python
- 🚫 UI: tombol hapus disembunyikan
- ✅ Aman: ACL memungkinkan, tidak ada blocker

### 2.1 Transaksional (pengajuan/request)

| Model | Data | Status sekarang | Kebijakan usulan Admin | Catatan konsekuensi |
|---|---|---|---|---|
| `hr.attendance` | Absensi resmi (check-in/out) | 🔒🚫 **tidak bisa** | **Bisa hapus** hanya via metode terkontrol (lihat §4.1). Prioritas: bersihkan `presenly.attendance.event` + selfie attachment, validasi tidak sedang dirujuk overtime request | Bukti kehadiran = data sensitif; hindari hapus massal via UI; rekomendasi soft-delete/archive untuk data lama |
| `presenly.attendance.event` | Bukti GPS/selfie (sukses & gagal) | 🚫 | **Bisa hapus** jika attendance dihapus (cascade oleh metode) atau manual oleh Admin (perbaikan data salah/GPS error) | `selfie_attachment_id` (private) ikut dihapus agar tidak yatim |
| `presenly.permission` | Izin/dispensasi | 🚫 (ACL manager=1) | **Bisa hapus** semua state oleh Admin; cascade hapus `presenly.approval.request`/`step` terkait + attachment + activity | Jika approved, lakukan setelah konfirmasi (dialog). Log approval **dipertahankan** sebagai audit trail |
| `presenly.overtime.request` | Lembur | 🚫 (ACL manager=1) | **Bisa hapus** semua state oleh Admin; cascade sama seperti permission | Approved yang sudah menjadi dasar klaim sebaiknya hanya di-cancel, bukan hard-delete |
| `hr.leave` (Time Off) | Cuti | 🚫 (view `delete=0`); native sudah mengizinkan manager | **Bisa hapus** oleh Admin mengikuti rule native (`group_hr_holidays_manager`): boleh hapus draft/refuse/cancel, non-cancel hanya administrator; **tambahkan** pembersihan `presenly.approval.request`/`step` terkait | Jangan hapus approved yang sudah memengaruhi allocation/work entries tanpa dialog konfirmasi |
| `presenly.approval.request` | Journey approval (snapshot) | 🔒🚫 **tidak bisa** | Jangan dibuka untuk delete manual dari UI journey; **hapus otomatis (cascade)** ketika target (permission/overtime/leave) dihapus | Snapshot immutable untuk audit; hapus hanya bersama target |
| `presenly.approval.step` | Step journey | 🔒🚫 | Sama: cascade bersama `approval.request` | `ondelete='cascade'` sudah ada |
| `presenly.approval.log` | Log keputusan | ✅ (tidak di-block, tanpa ACL khusus → hanya bisa via sudo/ORM) | **Pertahankan** (immutable audit). Opsional: hapus bersama target via metode `_presenly_delete_*` dengan param `keep_logs` | Jika ditambahkan ACL, beri `perm_unlink` hanya manager |

### 2.2 Master / Konfigurasi (sudah bisa dihapus Admin)

| Model | Data | Status sekarang | Kebijakan | Catatan |
|---|---|---|---|---|
| `presenly.approval.rule` | Step/rute approval | ✅ Bisa (ACL manager=1, view tanpa `delete=0`) | Tetap bisa hapus; rule yang dipakai journey lama aman karena journey menyimpan snapshot `source_rule_id` (`ondelete='set null'`) | Tidak ada perubahan |
| `presenly.permission.type` | Tipe izin | ✅ Bisa | Tetap bisa hapus oleh manager | Cek referensi `presenly.permission.permission_type_id` (ondelete default set null) |
| `presenly.work.location.schedule` | Slot jadwal lokasi | ✅ Bisa | Tetap bisa hapus; `hr.attendance.presenly_schedule_id` memakai `ondelete='set null'` | Tidak ada perubahan |
| `hr.work.location` (native + extend) | Lokasi kerja/geofence | ✅ Bisa (ACL manager=1) | Tetap bisa; waspadai FK `presenly.work.location.schedule` (`ondelete='restrict'`), attendance (`set null`), rule | Lokasi dengan schedule aktif tidak bisa dihapus — arsipkan dulu |

### 2.3 Data yang TIDAK Boleh Dihapus (tetap di-block)

| Model | Alasan |
|---|---|
| `res.company` (diperluas) | Legal entity; hapus via native, jangan dari menu Presenly |
| `presenly.approval.log` | Audit trail keputusan; **immutable** |
| Attachment private (selfie / dokumen izin) | Hanya dihapus sebagai bagian dari pembersihan record induknya; jangan dibuka hapus bebas |

### 2.4 Kebijakan HR Officer (usulan utama)

HR (`presenly.group_presenly_hr`) **perlu bisa mengelola data presensi**, bukan
hanya membaca. Usulan: **boleh hapus dengan 4 batasan** — (1) scope state, (2) age
window, (3) larangan data bernilai legal, (4) audit trail wajib.

| Model | HR BISA hapus | Batasan yang disarankan |
|---|---|---|
| `hr.attendance` | Ya, terbatas | Hanya dalam **jendela koreksi** (default `PRESENLY_CORRECTION_DAYS = 31` hari dari `check_in`). Hanya record yang **BUKAN** jadi dasar overtime request. Approved/valid yang berumur → dialog bantu saran **Archive** (soft delete), bukan hard delete |
| `presenly.attendance.event` | Ya, terbatas | Hanya event `validation_status == 'failed'` atau event milik attendance yang memang dihapus; **tidak boleh hapus event sukses** dari attendance valid (bukti kehadiran) kecuali Admin |
| `presenly.permission` | Ya, terbatas | Hanya state **`draft`, `rejected`, `cancelled`**. `approved`/`submitted` → hanya Admin (atau HR lewat alur Cancel) |
| `presenly.overtime.request` | Ya, terbatas | Hanya state **`draft`, `rejected`, `cancelled`**. `approved` → hanya Admin (approved = dasar klaim) |
| `hr.leave` (Time Off) | Ya, terbatas | Ikuti native: HR boleh hapus **draft/refuse/cancel**; approved non-cancel → hanya Admin (`group_hr_holidays_manager`) |
| `presenly.approval.request`/`.step` | Tidak langsung | Cascade internal saja saat induk dihapus |
| `presenly.approval.log` | Tidak | **Immutable** audit trail |
| Master (rule/type/schedule/location) | Tidak | Baca saja; konfigurasi kewenangan Admin (`group_presenly_manager`) |

**Alasan batasan:**
- Approved request → sudah berdampak legal/keuangan (alokasi cuti, klaim lembur);
  hard-delete oleh HR berisiko. Admin pun tetap harus konfirmasi eksplisit.
- Jendela koreksi 31 hari → HR cukup untuk memperbaiki kesalahan input/GPS tanpa
  memberi kemampuan mengubah histori lama yang rawan audit/perselisihan kerja.
- Event sukses vs gagal → bukti sukses adalah bukti kehadiran resmi; yang gagal
  hanya artefak percobaan, aman dibersihkan.
- Setiap penghapusan HR di-log (lihat §4.8 `presenly.deletion.log`).

---

## 3. Prinsip Desain Penghapusan Aman

1. **Role-aware bertingkat, bukan blanket block.** Guard model menjadi tiga tingkat:
   - `Administrator` (`presenly.group_presenly_manager`) → boleh hapus penuh (tetap via guard + konfirmasi untuk data bernilai).
   - `HR Officer` (`presenly.group_presenly_hr`) → boleh hapus **terbatas** (state window, age window, larangan data legal, audit log).
   - `Employee` / `Approver` → tetap diblokir total. `perm_unlink` ACL menjadi lapis pertama; guard Python lapis kedua.
2. **Cascade terkelola (managed cascade).** Menghapus request/attendance harus membersihkan turunannya secara eksplisit agar tidak ada: journey approval menggantung, event yatim, selfie attachment yatim, activity tersisa.
3. **Audit trail dipertahankan ganda.** `presenly.approval.log` TIDAK ikut terhapus; setiap penghapusan (terutama HR) dicatat ke `presenly.deletion.log` (who/what/when/snapshot).
4. **Konfirmasi untuk data bernilai.** Approved Permission/Overtime dan Time Off non-cancel mewajibkan konfirmasi (dialog/`confirm=`) karena berdampak allocation/work entries.
5. **Archive (soft delete) sebagai default untuk data lama.** Untuk `hr.attendance` di luar jendela koreksi, HR disarankan **Archive** (flag `presenly_archived`) bukan hard-delete; hard delete hanya Admin untuk record salah/test.
6. **Prinsip jendela koreksi.** Operasi destruktif HR dibatasi periode tertentu (31 hari) agar kesalahan diperbaiki cepat, bukan mengubah histori lama yang rawan audit/perselisihan kerja.

---

## 4. Rencana Implementasi (per file)

### 4.1 `models/presenly_attendance.py`

**Konstanta jendela koreksi** (bisa jadi parameter `ir.config_parameter` untuk fleksibilitas):

```python
PRESENLY_CORRECTION_DAYS = 31  # HR boleh hapus attendance hanya dalam 31 hari dari check_in
```

**a. Ubah `HrAttendance.unlink()`** menjadi role-aware bertingkat + cleanup:

```python
def unlink(self):
    if not self._presenly_hr_or_admin_can_delete():
        raise ValidationError(_(
            'Attendance history can only be deleted by a Presenly Administrator '
            'or HR Officer within the correction window.'
        ))
    for attendance in self:
        attendance._presenly_purge_children()
    return super().unlink()

def _presenly_hr_or_admin_can_delete(self):
    """Admin: apa pun. HR: hanya dalam jendela koreksi (~31 hari) dan BUKAN
    record yang menjadi dasar overtime request."""
    if self.env.su:
        return True
    user = self.env.user
    if user.has_group('presenly.group_presenly_manager'):
        return True
    if not user.has_group('presenly.group_presenly_hr'):
        return False
    now = fields.Datetime.now()
    for attendance in self:
        if attendance.presenly_has_overtime_evidence():
            return False
        if attendance.check_in and now - attendance.check_in > timedelta(days=PRESENLY_CORRECTION_DAYS):
            return False
    return True

def _presenly_purge_children(self):
    # Hapus evidence + selfie attachment privat agar tidak yatim.
    events = self.presenly_event_ids
    attachments = (events.mapped('selfie_attachment_id')
                   | self.presenly_selfie_in_attachment_id
                   | self.presenly_selfie_out_attachment_id)
    attachments.sudo().unlink()          # private attachment
    events.sudo().unlink()               # event log dilampirkan ke attendance
```

> Aturan native tetap berlaku: admin pun tidak bisa menghapus attendance milik
> employee di luar allowed company (record rules). HR dilindungi dari bukti overtime:

```python
def presenly_has_overtime_evidence(self):
    self.ensure_one()
    return bool(self.env['presenly.overtime.request'].sudo().search_count([
        ('employee_id', '=', self.employee_id.id),
        ('date', '=', self.check_in.date()),
        ('state', 'in', ('submitted', 'approved')),
    ], limit=1))
```

> Update test `test_manual_create_delete_and_native_toggle_are_blocked` di
> `tests/test_attendance.py` (baris 386-394): hapus hanya boleh untuk user
> Admin/HR dalam window; HR di luar window / dipakai overtime → ditolak.

**b. (Opsional / tahap lanjutan) Soft-delete arsip:**
Tambahkan field `presenly_archived = fields.Boolean(default=False)` pada
`hr.attendance` + action "Archive" untuk Admin, sehingga data lama tidak perlu
hard-delete. Dikecualikan dari resolusi laporan (filter default `not presenly_archived`).

### 4.2 `models/presenly_approval.py`

**a. Buka `PresenlyApprovalRequest.unlink()` dan `PresenlyApprovalStep.unlink()`**
agar bisa di-cascade oleh metode request (bukan open ke UI umum):

```python
def unlink(self):
    # Cascade internal dari _presenly_delete_* pada request induk.
    if not self.env.context.get('presenly_cascade_delete') and not self.env.su:
        raise UserError('Approval journeys cannot be deleted directly.')
    return super().unlink()
```

**b. Tambahkan helper cascade di `PresenlyApproval` (inherit `hr.leave`):**

```python
def _presenly_purge_approval(self, keep_logs=True):
    for record in self:
        approval = record.presenly_approval_request_id
        if approval:
            approval.with_context(presenly_cascade_delete=True).unlink()  # steps ikut ondelete cascade
            if not keep_logs:
                self.env['presenly.approval.log'].sudo().search([
                    ('request_model', '=', record._name),
                    ('request_res_id', '=', record.id),
                ]).unlink()
```

**c. Guard `HrLeavePresenly.unlink()`:** override untuk memanggil purge journey
sebelum `super().unlink()` (native `hr.leave.unlink()` mengurus resource leave
dan allocation), tetap mengikuti pembatasan state native:

```python
def unlink(self):
    self._presenly_purge_approval(keep_logs=True)
    return super().unlink()
```

### 4.3 `models/presenly_permission.py` — `PresenlyPermission`

**a. Unlink terkontrol** (Admin full, HR terbatas state):

```python
def unlink(self):
    if not (self.env.su or self.env.user.has_group('presenly.group_presenly_manager')):
        # HR: hanya draft/rejected/cancelled
        if not self.env.user.has_group('presenly.group_presenly_hr'):
            raise UserError('Only a Presenly Administrator or HR Officer can delete permission requests.')
        not_hr_ok = self.filtered(lambda p: p.state not in ('draft', 'rejected', 'cancelled'))
        if not_hr_ok:
            raise UserError('HR can only delete draft, rejected, or cancelled permission requests.')
    for permission in self:
        if permission.state == 'approved' and not self.env.context.get('presenly_confirm_delete'):
            raise UserError('Approved permission requests require explicit confirmation (use Delete with confirm context).')
        permission._presenly_purge_approval(keep_logs=True)   # journey + steps
        permission.activity_ids.sudo().unlink()                # mail activity
        permission.attachment_ids.sudo().unlink()              # dokumen izin privat
        # Hapus rel M2M approver agar FK bersih
    return super().unlink()
```

> Implementasi praktis: gunakan pola guard di `unlink` + method server
> `action_delete_with_confirm()` yang membungkus `with_context(presenly_confirm_delete=True).unlink()`
> untuk dipanggil tombol UI, sehingga konfirmasi dialog native tetap dipakai.

### 4.4 `models/presenly_overtime.py` — `PresenlyOvertimeRequest`

Pola identik dengan §4.3 (Admin full, HR terbatas state):

```python
def unlink(self):
    if not (self.env.su or self.env.user.has_group('presenly.group_presenly_manager')):
        if not self.env.user.has_group('presenly.group_presenly_hr'):
            raise UserError('Only a Presenly Administrator or HR Officer can delete overtime requests.')
        not_hr_ok = self.filtered(lambda o: o.state not in ('draft', 'rejected', 'cancelled'))
        if not_hr_ok:
            raise UserError('HR can only delete draft, rejected, or cancelled overtime requests.')
    for overtime in self:
        overtime._presenly_purge_approval(keep_logs=True)
        overtime.activity_ids.sudo().unlink()
    return super().unlink()
```

### 4.5 View / UI (`views/*.xml`)

Aktifkan kembali tombol hapus **berjenjang per role** (HR terbatas, Admin penuh):

| File | Perubahan |
|---|---|
| `views/hr_attendance_integration_views.xml` | Form `hr.attendance`: `delete="user has_group('presenly.group_presenly_hr') or user has_group('presenly.group_presenly_manager')"`; sama untuk list `view_hr_attendance_list_presenly` & `view_hr_attendance_management_list_presenly` |
| `views/presenly_attendance_views.xml` | `presenly.attendance.event` list&form: delete mengikuti HR/Manager |
| `views/presenly_permission_views.xml` | List permission (baris ~229): delete untuk HR/Manager; tombol `action_delete` (object) dengan `confirm=` untuk state approved hanya tampil utk Manager |
| `views/presenly_overtime_views.xml` | Sama seperti permission (baris ~82) |
| `views/presenly_leave_views.xml` | List `hr.leave` (baris ~108): `delete="user has_group('presenly.group_presenly_hr') or user has_group('presenly.group_presenly_manager')"` (native form sudah mendukung hapus utk manager; HR tetap dibatasi state native draft/refuse/cancel) |
| `presenly_menus.xml` | Action `hr_attendance.hr_attendance_action` & management: context `'delete': False` → `'delete': user_has_groups('presenly.group_presenly_hr') or user_has_groups('presenly.group_presenly_manager')` |

> Catatan teknis Odoo 19: pada atribut view gunakan
> `delete="user has_group('presenly.group_presenly_hr') or user has_group('presenly.group_presenly_manager')"`
> (expression di domain attribute view), atau gunakan `groups=` pada tombol.
> Batasan state/age tetap dilindungi server-side oleh guard Python (UI hanya
> menyembunyikan, server yang memutuskan).

### 4.6 `security/ir.model.access.csv`

**Wajib (untuk HR)** — buka `perm_unlink` terbatas bagi HR (guard Python tetap
melindungi state/age):

| Baris | Model | Group | Sebelum | Sesudah |
|---|---|---|---|---|
| `access_presenly_attendance_event_hr` | `presenly.attendance.event` | HR | `1,1,0,0` | `1,1,1,1` (failed event saja dibolehkan di guard — §4.7) |
| tambah baris | `presenly.permission` | HR | tidak ada | `access_presenly_permission_hr,presenly.permission hr,model_presenly_permission,presenly.group_presenly_hr,1,1,1,1` |
| `access_presenly_overtime_hr` | `presenly.overtime.request` | HR | `1,1,1,0` | `1,1,1,1` |
| `hr.work.location` | HR | (tidak ada baris HR; rule HR lihat semua) | tetap **read-only** untuk HR (no change) |
| `presenly.work.location.schedule` | HR | (tidak ada baris HR; rule HR lihat semua) | tetap **read-only** untuk HR (konfigurasi = Admin) |

> Karena `group_presenly_hr` meng-implied `group_presenly_approver` → `group_presenly_employee`,
> HR mendapat akses baca dari baris `_employee`; baris `_hr` yang baru inilah yang
> memberi write/unlink bagi HR. Guard model tetap menjadi penjaga kebijakan state/age.

**Tetap 0 / tidak dibuka:**
- `access_presenly_approval_request_manager` / `_approver` / `_user`: `perm_unlink` tetap 0 (journey hanya di-cascade internal via sudo).
- `access_presenly_approval_step_*`: tetap 0.
- `presenly.approval.log`: tidak ada baris hapus; tetap immutable.
- Master config (`approval.rule`, `permission.type`, `schedule`, `work.location`): HR tetap read-only (kewenangan Manager).

### 4.7 (Baru) Batasan event untuk HR — `models/presenly_attendance.py`

Di `PresenlyAttendanceEvent.unlink()`:

```python
def unlink(self):
    is_admin = self.env.su or self.env.user.has_group('presenly.group_presenly_manager')
    if not is_admin:
        if not self.env.user.has_group('presenly.group_presenly_hr'):
            raise UserError('Only a Presenly Administrator or HR Officer can delete attendance evidence.')
        forbidden = self.filtered(
            lambda e: e.validation_status == 'success'
            and e.attendance_id  # event sukses dari attendance valid
        )
        if forbidden:
            raise UserError(
                'HR can only delete failed evidence or evidence of a deleted '
                'attendance. Successful check-in/out evidence is kept; ask an '
                'Administrator to remove the attendance record instead.'
            )
    return super().unlink()
```

### 4.8 (Baru) Audit log penghapusan — `models/presenly_deletion_log.py`

Model baru untuk melacak siapa menghapus apa (wajib utk jalur HR):

```python
class PresenlyDeletionLog(models.Model):
    _name = 'presenly.deletion.log'
    _description = 'Presenly Deletion Audit Log'
    _order = 'create_date desc'

    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(index=True)
    res_name = fields.Char(string='Record Name')
    deleted_by_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', index=True)
    reason = fields.Char()
    deletion_date = fields.Datetime(default=fields.Datetime.now, required=True, index=True)

    def write(self, values):
        raise UserError('Deletion logs are append-only and cannot be modified.')

    def unlink(self):
        raise UserError('Deletion logs cannot be deleted.')
```

Daftarkan di manifest `data` setelah security (+ `views/presenly_deletion_log_views.xml`
untuk menu Reporting bagi Manager), dan panggil dari setiap guard `unlink` yang lolos:

```python
def _presenly_log_deletion(self, reason=''):
    for record in self:
        self.env['presenly.deletion.log'].sudo().create({
            'res_model': record._name,
            'res_id': record.id,
            'res_name': record.display_name,
            'deleted_by_id': self.env.user.id,
            'company_id': getattr(record, 'company_id', False).id or False,
            'reason': reason,
        })
```

### 4.9 `tests/` — update & tambah (termasuk skenario HR)

| File | Perubahan |
|---|---|
| `tests/test_attendance.py` | Ubah test baris 386: `unlink` diblokir untuk user non-Admin/HR; HR boleh dalam window 31 hari; HR **ditolak** di luar window; Admin boleh; cascade event & attachment ikut terhapus |
| `tests/test_approval.py` | Tambah: hapus permission approved (Admin) → journey ikut terhapus, log approval tetap ada; HR hapus approved → ditolak |
| `tests/test_permission.py` | Tambah: employee tidak bisa hapus; HR hanya bisa draft/rejected/cancelled; manager bisa semua state |
| `tests/test_api_*` | Pastikan tidak ada endpoint hapus baru terpapar ke mobile |
| `tests/` (baru, opsional) | `test_deletion_log.py`: HR hapus attendance dalam window → `presenly.deletion.log` tercatat; log tidak bisa diedit/dihapus |

---

## 5. Skenario Uji (Acceptance)

1. **Login sebagai Administrator** → Attendance list/form menampilkan tombol Delete;
   hapus 1 attendance → evidence + selfie attachments ikut terhapus; record absensi hilang.
2. **Login sebagai HR Officer** → tombol Delete muncul, tetapi: attendance hanya bisa
   dihapus **dalam 31 hari** dari `check_in` dan **bukan** dasar overtime;
   permission/overtime hanya state draft/rejected/cancelled; evidence hanya failed.
   Di luar batas → tombol hilang / RPC ditolak dengan pesan jelas.
3. **Login sebagai Employee** → tidak bisa hapus permission/overtime milik sendiri
   (tetap hanya Cancel), meskipun menulis RPC.
4. **Hapus permission approved (Admin)** → muncul konfirmasi; journey `approval.request`/`step`
   ikut terhapus; `approval.log` tetap tersimpan. HR hapus approved → ditolak.
5. **Hapus time off yang sedang pending approval** → journey ikut terhapus, state
   resource leave dibersihkan native, tidak ada FK menggantung.
6. **Hapus `hr.work.location` dengan schedule aktif** → tetap gagal (FK restrict)
   dengan pesan jelas: arsipkan schedule/lokasi dulu.
7. **Semua penghapusan (Admin & HR)** tercatat di `presenly.deletion.log`; log tidak
   bisa diedit/dihapus.
8. **Test suite** `--test-tags /presenly` hijau.

---

## 6. Urutan Pengerjaan (checklist)

- [ ] **1.** `models/presenly_attendance.py`: guard role-aware bertingkat (Admin full / HR window 31 hari + bukan dasar overtime) + `_presenly_purge_children`
- [ ] **2.** `models/presenly_approval.py`: buka cascade unlink dengan context guard
      + `_presenly_purge_approval` (inherit request/leave/permission/overtime helper)
- [ ] **3.** `models/presenly_permission.py`: unlink Admin full / HR terbatas state + cleanup + konfirmasi approved
- [ ] **4.** `models/presenly_overtime.py`: unlink Admin full / HR terbatas state + cleanup
- [ ] **5.** `models/presenly_attendance.py` (event): batasan HR hanya hapus event failed / milik attendance terhapus
- [ ] **6.** `models/presenly_deletion_log.py` (baru): audit log append-only + registrasi manifest + panggil dari guard unlink
- [ ] **7.** `security/ir.model.access.csv`: buka `perm_unlink` HR untuk `attendance.event`, `permission`, `overtime`
- [ ] **8.** Views: nyalakan delete utk HR/Manager (attendance, evidence, permission,
      overtime, leave, actions context)
- [ ] **9.** (Opsional) Soft-delete arsip attendance `presenly_archived`
- [ ] **10.** Update/tambah tests (termasuk skenario HR)
- [ ] **11.** Bump versi manifest `19.0.13.6.0` → `19.0.14.0.0`, jalankan
      `-u presenly` tanpa migrasi schema
- [ ] **12.** Validasi command:
      `./odoo-bin server -c odoo.conf -d odoo -u presenly --test-enable --test-tags /presenly --stop-after-init --http-port=18069 --http-interface=127.0.0.1 --max-cron-threads=0`

---

## 7. Keamanan / Catatan

- Jangan pernah buka hapus ke endpoint mobile API; hapus tetap operasi backend
  (metode leading-underscore `_presenly_delete_*` tidak bisa dipanggil via RPC publik).
- Batasan HR (state/age/event) dijamin **dua lapis**: UI menyembunyikan tombol, guard
  Python memutuskan — RPC `unlink()` langsung tetap ditolak bila di luar kebijakan.
- Semua penghapusan (Admin & HR) tercatat di `presenly.deletion.log` (append-only).
- `presenly.attendance.event` yang bersifat gagal (failed attempt) juga penting
  sebagai bukti investigasi — hapus manual oleh HR hanya bila jelas data salah.
- Jika perusahaan butuh **retensi minimal** (audit/perselisihan kerja), prioritaskan
  arsip (soft-delete) daripada hard-delete untuk data > 1 tahun; koordinasikan ke HR/legal.
- Parameter jendela koreksi (`31` hari) dan state yang boleh dihapus HR sebaiknya
  tetap sebagai konstanta sementara, lalu dipindahkan ke `ir.config_parameter`
  (per-company optional) setelah disepakati HR/legal.