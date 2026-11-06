# AGENTS.md — กฎการทำงานของ AI Agent (Odoo 19 CE · AutoInfo)

- **ผลบังคับใช้**: AI agent ทุกตัวที่ทำงานใน repository นี้ (Codex, Claude Code, Trae, Gemini ฯลฯ)
- **สถานะ**: LOCKED — ห้าม agent แก้ไขไฟล์นี้เอง ต้องได้รับอนุมัติจากผู้ใช้เป็นรายครั้ง
- Repository: `nattanonvs/odoo19ce-autoinfo` · branch หลัก: `19.0` · ฐานข้อมูลที่ใช้: `odoo19_pdev`

---

## 1. ระดับความเสี่ยง และสิทธิ์การอนุมัติ

### 1.1 ปลอดภัย — ทำได้เลย ไม่ต้องรออนุมัติ

งานต่อไปนี้ agent ดำเนินการได้เองทันที โดยยังต้องปฏิบัติตามกฎข้ออื่น ๆ ครบถ้วน:

| ประเภท | ตัวอย่าง |
|---|---|
| อ่าน / ค้นหา / ตรวจสอบ (read-only) | อ่านไฟล์, grep, glob, `git status` / `log` / `diff` / `show` / `fsck` / `branch -a` |
| แก้ไข / สร้างไฟล์ในขอบเขตที่อนุญาต | ไฟล์ภายใต้ `custom_addons/`, `docs/` และ config ของโปรเจกต์ |
| ตรวจสอบแบบ static (ไม่แตะ DB) | `py_compile`, ตรวจ XML well-formed, linter |
| จัดการ staging / branch ท้องถิ่น | `git add <path>`, `git restore --staged`, สร้าง branch `feature/*`, `codex/*` |
| เก็บงานชั่วคราวแบบไม่ลบ | `git stash push` |
| **รัน Unit Test / Integration Test** | `run-tests.ps1` หรือ `odoo-bin --test-enable` บน DB ทดสอบ — รันเองได้ และต้องผ่านก่อน commit/push ทุกครั้ง |
| **`git push` (branch งานตัวเอง)** | push เข้า `feature/*`, `codex/*` ของตัวเองขึ้น remote ได้เอง ไม่ต้องรออนุมัติ |
| **`git commit` (local)** | commit บนเครื่อง หลังผ่าน Pre-flight (ข้อ 2) และทำตามข้อ 3 |

> **`git commit` (local) ปลดการรออนุมัติ** เพราะย้อนกลับได้ง่ายด้วย `git reset` / `git revert` และมี Pre-flight (ข้อ 2) คอยกันการชนกันของหลาย agent
> ⚠️ ต้อง **ผ่าน Pre-flight ทุกครั้ง** ก่อน commit เสมอ

### 1.2 HARD LOCK — ต้องอนุมัติจากผู้ใช้เป็นรายครั้งเสมอ

| # | การกระทำที่ห้าม | เหตุผล |
|---|---|---|
| 1 | `git push --force` / `--force-with-lease` | เขียนประวัติทับของจริง |
| 2 | push เข้า `19.0` / `main` / `master` โดยตรง | branch หลักต้องผ่านการรีวิว |
| 3 | `git commit --amend` / `rebase` / `squash` / `reset --hard` / history rewrite | เขียนประวัติใหม่ = SHA เปลี่ยนทั้งหมด |
| 4 | `git config` แก้ค่าใด ๆ (รวม `core.hooksPath`) | เปลี่ยนสภาพแวดล้อมของเครื่อง |
| 5 | `git stash drop` / `git clean -fdx` | ลบงานที่ยังไม่ได้ commit |
| 6 | ติดตั้ง / แก้ไข / ลบ ไฟล์ใน `.git/hooks/` | กระทบทุก agent บนเครื่องนี้ |

ข้อยกเว้นของข้อ 1–2: ผู้ใช้สั่งอนุมัติเป็นรายครั้ง แล้วตั้งค่า `OD19_PUSH_APPROVED=1` ก่อนสั่ง push

## 2. Single-writer — ทำงานได้ทีละ agent เท่านั้น

ก่อนเริ่มงานทุกครั้ง ต้องผ่าน Pre-flight ทั้ง 4 ข้อ:

1. `git log -1 --oneline` → จดค่า HEAD ไว้
2. `git status -sb` → ต้องไม่มีไฟล์ที่ agent อื่นกำลังแก้ค้างอยู่
3. ต้องไม่มีไฟล์ `.git/index.lock`
4. HEAD ต้องไม่เปลี่ยนภายใน 2 นาที

ถ้าข้อใดไม่ผ่าน → **หยุดทันที** และรายงานผู้ใช้ ห้ามฝืนทำงานต่อ

## 3. กฎการ commit (ทำได้เองหลังผ่าน Pre-flight — ไม่ต้องรออนุมัติ)

- **ต้องรัน Unit Test ให้ผ่านก่อน commit/push** (0 failed / 0 error) — ถ้าไม่ผ่าน ห้าม commit และห้าม push
- รูปแบบ Conventional Commits: `<type>(<scope>): <description>`
  - type: `feat` `fix` `docs` `style` `refactor` `perf` `test` `build` `ci` `chore` `revert`
- 1 commit = 1 โดเมนงาน ห้ามรวมหลายโดเมนใน commit เดียว
- บรรทัดแรกใช้ present tense / imperative mood และยาวไม่เกิน 72 ตัวอักษร
- ระบุไฟล์เป็นรายชื่อชัดเจน (`git add <path>` หรือ `git commit -- <path>`) **ห้าม** `git add -A` หรือ `git add .`
- ห้าม commit ไฟล์ที่ `.gitignore` ครอบไว้ — ตรวจก่อนด้วย `git check-ignore -v --no-index <path>`

## 4. กฎการ push (branch งานตัวเอง — ทำได้เอง ไม่ต้องรออนุมัติ)

- push ได้เฉพาะ branch งานของตัวเอง (`feature/*`, `codex/*`)
- ห้าม push ตรงเข้า `19.0` / `main` / `master`
- หลัง push ต้องรายงาน URL ของ commit/PR ให้ผู้ใช้ทราบ
- ถ้า push ถูก reject เพราะ remote ใหม่กว่า → หยุดและรายงาน ห้ามใช้ force

## 5. ความปลอดภัยของข้อมูลลับ (Security)

ห้าม commit ไฟล์เหล่านี้เด็ดขาด:

- `odoo.conf` (มี `db_password`) — ถูก ignore ที่ `.gitignore:28` แล้ว
- `.env`, `*.key`, `*.pem`, `*.p12`, `id_rsa*`, `credentials*.json`
- `backups/` (ข้อมูลจริง) — ignore ที่ `.gitignore:69`
- `data/`, `venv19/`, `pylibs/`, `wkhtmltopdf/bin/`

ก่อน commit ทุกครั้ง ให้ตรวจ `git diff --cached --name-only` ว่าไม่มีไฟล์ตามรายการข้างต้น

## 6. กฎทั่วไปของโปรเจกต์

- ห้ามแก้ไฟล์ core ของ Odoo (`odoo/`, `addons/`) — แก้ได้เฉพาะ `custom_addons/` และ config ของโปรเจกต์
- ห้ามฝัง credential ลงในคำสั่ง/สคริปต์ ให้อ่านค่าจาก `odoo.conf` ตอนรัน
- รัน Unit Test ได้เองบน DB `odoo19_pdev` (เช่นผ่าน `run-tests.ps1` หรือ `odoo-bin --test-enable --test-tags`) — ต้องผ่านก่อน commit/push ทุกครั้ง
- ใช้ฐานข้อมูล `odoo19_pdev` เท่านั้น

## 7. ก่อนรายงานผลทุกครั้ง

ระบุให้ครบ: commit SHA (ถ้ามี), ไฟล์ที่แตะ, คำสั่งที่รันจริง, ผลลัพธ์จริง — ห้ามอ้างผลที่ยังไม่ได้รัน
