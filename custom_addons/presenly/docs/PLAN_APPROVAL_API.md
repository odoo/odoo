# PLAN — API Approval Lengkap Presenly (Mobile)

**Status dokumen:** Draft plan — untuk direview sebelum eksekusi.
**Database/modul:** `odoo` / `presenly` 19.0.13.6.0
**Referensi yang sudah ada:**
- Backend: `custom_addons/presenly/controllers/leave.py`, `controllers/permission.py`, `models/presenly_approval.py`
- Docs mobile: `docs/MOBILE_API.md`, `docs/MOBILE_TIMEOFF_API.md`, `docs/MOBILE_WFA_API.md`
- PRD: `presenly-prd.md` §13 (Mobile API), §16 (Acceptance), §18 (Backlog)

---

## 1. Tujuan

Menyusun rencana kerja untuk menyempurnakan **API approval mobile** hingga lengkap, mencakup:

1. **List approval untuk atasan** (antrean request yang menunggu keputusan user login pada level aktif).
2. **Endpoint approve / reject** untuk Time Off dan Permission.
3. **Pengajuan Time Off** (dan Permission) dari mobile.
4. Dokumentasi API mobile yang menjadi acuan implementasi client.

Tahap pertama adalah menginventarisasi yang **sudah dikerjakan** (bagian 2), lalu memetakan **gap** (bagian 3), **desain target** (bagian 4), dan **fase eksekusi + acceptance criteria** (bagian 5).

---

## 2. Yang SUDAH DIKERJAKAN (inventaris hasil pengecekan kode)

### 2.1 Endpoint aktif (13 route, semua `auth='user'` JSON-RPC)

| No | Fungsi | Method | Endpoint | File |
|---|---|---|---|---|
| 1 | Daftar Time Off Type | POST | `/api/presenly/v1/leave/types` | `controllers/leave.py` |
| 2 | **Buat + submit Time Off** | POST | `/api/presenly/v1/leaves` | `controllers/leave.py` |
| 3 | List Time Off milik saya | POST | `/api/presenly/v1/leaves/list` | `controllers/leave.py` |
| 4 | Alias lama list Time Off | GET | `/api/presenly/v1/leaves` | `controllers/leave.py` |
| 5 | **Antrean approval Time Off** | POST | `/api/presenly/v1/leaves/approval` | `controllers/leave.py` |
| 6 | **Approve Time Off** | POST | `/api/presenly/v1/leaves/<id>/approve` | `controllers/leave.py` |
| 7 | **Reject Time Off** | POST | `/api/presenly/v1/leaves/<id>/reject` | `controllers/leave.py` |
| 8 | Daftar Permission Type | POST | `/api/presenly/v1/permissions/types` | `controllers/permission.py` |
| 9 | Buat + submit Permission | POST | `/api/presenly/v1/permissions` | `controllers/permission.py` |
| 10 | List Permission milik saya | GET | `/api/presenly/v1/permissions` | `controllers/permission.py` |
| 11 | **Antrean approval Permission** | POST | `/api/presenly/v1/permissions/approval` | `controllers/permission.py` |
| 12 | **Approve Permission** | POST | `/api/presenly/v1/permissions/<id>/approve` | `controllers/permission.py` |
| 13 | **Reject Permission** | POST | `/api/presenly/v1/permissions/<id>/reject` | `controllers/permission.py` |

### 2.2 Yang sudah benar di backend

- **Single-path Approval Journey** (`presenly.approval.request` / `presenly.approval.step`): snapshot level + approver saat submit, immutable, level-per-level, `presenly.approval.log` menyimpan aktor/keputusan/waktu.
- **Otorisasi approver**: hanya approver pada `current_step_id.assigned_user_ids` yang boleh approve/reject; guard `_presenly_check_approver` + lock row `FOR UPDATE` anti race.
- **List approval atasan terfilter benar**: query state pending + `user in _presenly_pending_approver_users()` (bukan sekadar state), limit 100.
- **Reject wajib alasan** untuk Time Off maupun Permission.
- **Guard bypass**: file `write()` menolak perubahan field workflow, `action_approve`/`action_refuse` native Time Off dilempar, final level ke `_action_validate` native.
- **Serializer kaya**: `approval_progress`, `current_approvers`, `approval_steps` (level, state, approver_ids, decision_by/date/note), `rejection_reason`; kompatibilitas `unit_id` alias `work_location_id`.
- **Attachment Permission** sudah didukung API: `attachments: [{name, data(base64), mimetype}]`, private, max 10 MB, wajib bila tipe mewajibkan.
- **Data mobile didorong dari session** (`employee_id` selalu dari server, tidak diterima dari client).

### 2.3 Test otomatis yang sudah ada

| File | Cakupan |
|---|---|
| `tests/test_api_leave.py` | Alur lengkap Time Off: types → create → list → queue approver → approve → native `validate`; reject tanpa reason ditolak; reject dengan reason → `refuse`. |
| `tests/test_api_session.py` | Session, attendance status/check-in/out, selfie, WFA, kiosk/systray native dinonaktifkan, GPS/selfie invalid ditolak. |
| `tests/test_approval.py`, `tests/test_permission.py` | Uji model journey/leveling (selain HTTP). |
| `tests/test_attendance.py` | Attendance/evidence. |

### 2.4 Dokumentasi yang sudah ada

- `docs/MOBILE_API.md` — login, session, JSON-RPC, attendance, selfie, error handling, checklist.
- `docs/MOBILE_TIMEOFF_API.md` — Time Off + approval leveling (`approval_state`, `approval_steps`, approve/reject per level).
- `docs/MOBILE_WFA_API.md`, `docs/MOBILE_MODE_SELECTION.md` — mode WFA.

> **Kesimpulan bagian 2:** fondasi approval API (list atasan, approve/reject, pengajuan Time Off & Permission) **sudah berfungsi dan teruji**. Yang belum lengkap adalah beberapa endpoint pelengkap dan konsistensi (bagian 3).

---

## 3. Gap vs "API approval lengkap"

Urut dari yang paling berdampak ke mobile:

| # | Gap | Detail | Referensi PRD |
|---|---|---|---|
| G1 | **Detail request per-ID** | Belum ada `GET/POST /leaves/<id>` & `/permissions/<id>`; mobile hanya dapat data detail via list/queue atau respons approve/reject. | 13.2 (detail belum ada) |
| G2 | **Unified approval queue** | Antrean Time Off dan Permission terpisah; PRD meminta "Unified mobile approval queue". | 18 P3 #4 |
| G3 | **Cancel via API** | Tombol Cancel ada di UI (`action_presenly_cancel`/`action_cancel`) tetapi tidak ada route API. | 18 P1 #5 |
| G4 | **Balance/quota Time Off** | Belum ada endpoint saldo; sulit mencegah pengajuan melebihi kuota dari mobile. | 13.2, 16.3, 18 P1 #4 |
| G5 | **Pagination & filter** | Semua list hardcode `limit=100`, tanpa `offset`/`status` filter. | 15.3, 18 P1 #5 |
| G6 | **Approval history / decision log** | `presenly.approval.log` ada tapi tidak diekspos API. | 11, 14.1 |
| G7 | **Attachment Time Off dari API** | Permission sudah terima `attachments`; Time Off belum (native `supported_attachment_ids` ada di form). | 13.2 |
| G8 | **Download attachment** | Serializer permission hanya metadata (id/name/mimetype); tidak ada endpoint unduh aman. | 14.1 |
| G9 | **Catatan saat approve (opsional)** | Model `_approve_current(note=...)` mendukung note, tetapi kedua controller approve tidak melewatkannya. | 11 |
| G10 | **Konsistensi contract** | `leave` login payload via `**params`, `permission` via `request.get_json_data()`; list Time Off POST vs Permission GET; error tanpa kode terstruktur. | 13.1 |
| G11 | **Cakupan test API** | Tidak ada test HTTP untuk permission endpoints dan multi-level journey via API. | 16 |
| G12 | **Hardening** | Idempotency key, rate limiting, OpenAPI — semua belum ada. | 18 P2 #5,6; P3 #6 |

---

## 4. Desain Target (usulan, menunggu keputusan)

### 4.1 Prinsip

- Tetap **JSON-RPC + session cookie Odoo** (konsisten dengan seluruh API Presenly; tidak pindah REST).
- Tetap prefix `/api/presenly/v1`, `work_location_id` kanonis, `unit_id` alias.
- `approve`/`reject` tetap **per-module** (`leaves`/`permissions`) — dipertahankan.
- Uniform list: semua list menerima `params: {offset, limit, status}` (default `limit 100`, `status` opsional).
- Envelope respons bisnis tetap `{success, data, error}`; error tetap JSON-RPC `error.data.message`.

### 4.2 Endpoint baru yang diusulkan

| Fungsi | Method | Endpoint | Prioritas |
|---|---|---|---|
| Detail Time Off | POST | `/api/presenly/v1/leaves/<id>` | P0 |
| Detail Permission | POST | `/api/presenly/v1/permissions/<id>` | P0 |
| Cancel Time Off | POST | `/api/presenly/v1/leaves/<id>/cancel` | P0 |
| Cancel Permission | POST | `/api/presenly/v1/permissions/<id>/cancel` | P0 |
| Balance Time Off | POST | `/api/presenly/v1/leave/balance` | P0 |
| Approval history | POST | `/api/presenly/v1/leaves/<id>/history` + `/permissions/<id>/history` | P1 |
| Unified queue | POST | `/api/presenly/v1/approvals` (travel `request_type`: `leave`/`permission`) | P1 |
| Attachment unduh | GET | `/api/presenly/v1/permissions/<id>/attachments/<attachment_id>` (dan Time Off) | P1 |

### 4.3 Keputusan yang perlu disepakati

1. **Unified queue**: satu list campuran ber-label `request_type` vs pertahankan dua queue terpisah + endpoint count badge. *(Disarankan: satu endpoint `/approvals` + pertahankan yang lama sebagai kompatibilitas.)*
2. **Approve dengan note**: izinkan `params: {note}` opsional di approve? Model sudah mendukung.
3. **Filter status default**: biarkan route lama (tanpa filter) stabil, tambah param baru tanpa mengubah kontrak lama.
4. **Attachment Time Off**: ikut pola permission (`attachments` di create) dan batas 10 MB private.
5. **Scope G12** masuk rencana ini atau sprint hardening terpisah.

---

## 5. Fase Eksekusi + Acceptance Criteria

### Fase 0 — Baseline (✅ sudah selesai)
Endpoint list/approve/reject/submit berfungsi, test & docs Time Off ada.

**AC:** Tidak berubah apa pun; menjalankan regression test sebagai dasar.

### Fase 1 — Detail, Cancel, Balance (P0)
1. Tambah route detail `leaves/<id>` & `permissions/<id>` menggunakan serializer yang sama (+ `approval_history` ringan bila murah).
2. Tambah route cancel yang memanggil `action_presenly_cancel` (Time Off) dan `action_cancel` (Permission) — patroli `presenly_can_cancel`.
3. Tambah `POST /leave/balance` → daftar `hr.leave.type` + sisa kuota (via `leave_type._get_allocation_remaining` yang tersedia di `hr_holidays`; pastikan ACL aman).
4. Update serializer: tambahan konteks tanpa mengubah field lama (additive only).

**AC:**
- [ ] `tests/test_api_leave.py` + file baru `tests/test_api_permission.py` menutup: detail, cancel (owner & non-owner), balance.
- [ ] Cancel request pending menutup journey (`presenly_approval_state=cancelled`, step selesai `cancelled`).
- [ ] Balance mengembalikan tipe + `remaining` yang konsisten dengan perhitungan native.
- [ ] Upgrade module di clone test: `0 error, 0 warning` view; regression 42+ test stats lulus.

### Fase 2 — Unified queue, History, Attachment (P1)
1. `POST /approvals`: hasil gabungan Time Off + Permission milik user pada level aktif, masing-masing ber-label `request_type`, `request_id`, `summary` (display_name), `approval_progress`, `current_approvers`, `created`.
2. History: expose `presenly.approval.log` terfilter model+res_id (immutable, urut decision_date desc).
3. Attachment Time Off pada create (`attachments` payload, pola `create_api_attachments` milik permission) + endpoint unduh aman ber-ACL.

**AC:**
- [ ] `/approvals` hanya menampilkan level aktif user — hasil identik dengan gabungan dua queue lama.
- [ ] Detail/history menampilkan seluruh snapshot level tanpa membocorkan data antar-company.
- [ ] Attachment Time Off tersimpan private dan diunduh hanya oleh owner/approver/hak yang tepat.
- [ ] Test: permission full flow HTTP (create → queue → approve/reject), multi-level journey via API.

### Fase 3 — Konsistensi & Hardening (P1–P2)
1. Uniform list param `{offset, limit, status}` pada semua list (backward compatible).
2. Seragamkan cara baca payload controller (`_payload(params)`), hapus ketergantungan `request.get_json_data` yang tidak wajib.
3. Tambahkan kode error terstruktur ringan pada envelope bila diperlukan client (opsional).
4. Idempotency key pada mutasi mobile + dokumentasi retry (P2 backlog; putuskan satu langkah di sini atau sprint terpisah).

**AC:**
- [ ] Semua list menerima `offset/limit/status`; nilai default tetap 100 tanpa filter (konsumen lama tidak rusak).
- [ ] Satu pola payload di seluruh controller.
- [ ] Dokumen `MOBILE_APPROVAL_API.md` mencantumkan limit, retry, dan kontrak stabil.

### Fase 4 — Dokumentasi & regresi
1. File `docs/MOBILE_APPROVAL_API.md` (keluar bersama plan ini sebagai draft acuan client).
2. Update `docs/MOBILE_API.md` index link dan `presenly-prd.md` §13 bila endpoint baru dirilis.
3. Jalankan validasi lengkap:

```bash
source /Users/ferisetyawan/Project/Website/odoo-19/odoo-venv/bin/activate
python -m compileall -q custom_addons/presenly

# upgrade + test di clone test (bukan db produksi aktif)
./odoo-bin -c odoo.conf -d <clone_test> -u presenly --stop-after-init --no-http --test-enable
```

**AC:**
- [ ] 100% endpoint yang didokumentasikan ada di kode (tidak ada doc dream).
- [ ] Regresi: 0 failed, 0 error.
- [ ] Backup sebelum rollout: pola `backups/presenly-migration/odoo-before-approval-api-<timestamp>.dump`.

---

## 6. Ringkasan Rekomendasi

1. **Jangan ubah kontrak yang sudah hidup** (13 route eksisting) — semua penambahan bersifat additive.
2. **Kerjakan Fase 1 dulu** (detail, cancel, balance) karena menyentuh alur inti mobile tanpa risiko breaking.
3. **Fase 2 (unified queue)** menjawab permintaan PRD dan UX approver — nilai paling terlihat user.
4. **Fase 3–4** konsistensi, hardening ringan, dan dokumentasi terbit menyusul.
5. Setiap fase: clone test → update module → test-enable → smoke test login/queue/approve → baru rollout db produksi dengan backup.