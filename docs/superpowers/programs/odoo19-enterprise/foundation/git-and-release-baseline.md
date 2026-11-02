# Git and Release Baseline

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 CE Enterprise |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/foundation/git-and-release-baseline.md` |
| Artifact owner | Program engineering lead |
| Required reviewers | Architecture lead, delivery lead |
| Artifact status | Active baseline |
| Review cadence | Reconfirm when branch model, version scheme, or repository structure changes |
| Last updated | 2026-10-29 |

## Purpose

กำหนดโมเดลสาขา, กติกาเวอร์ชัน/แท็ก, วิธีอัปเดตจาก Odoo original, และวิธี deploy/release ให้ทุกคนทำงานบน git เดียวกันอย่างไม่สับสน

## Scope

- ครอบคลุม repo `odoo19ce-autoinfo` (monorepo: Odoo core + `custom_addons/` + `third_party/oca/` + `docs/` + `deployment/`)
- ทำงานคู่กับ `repository-and-addon-baseline.md` (ที่วางไฟล์/addon) และ `environment-and-delivery-baseline.md` (promotion ระหว่าง environment)

## Decisions (ยืนยันแล้ว 2026-10-29)

| # | Decision |
|---|---|
| D1 | **Monorepo** — คง Odoo core ไว้ใน repo เดียว ไม่แยกออกเป็น dependency ภายนอก |
| D2 | **trunk = `19.0`** — สาขาหลักสำหรับพัฒนาและปล่อย release |
| D3 | **Version = semver `v19.0.<n>`** (patch เพิ่มตามงานของเรา ไม่ผูกกับเวอร์ชัน Core) |
| D4 | **Core อยู่ใน repo** เหมือนเดิม |
| D5 | **โฮสต์ GitHub** (`origin` = fork, `upstream` = odoo/odoo); mirror เพิ่มได้ภายหลัง |

## Remote Model

| Remote | URL | บทบาท | กติกา |
|---|---|---|---|
| `upstream` | `https://github.com/odoo/odoo.git` | ต้นทาง Odoo original | **fetch เท่านั้น — ห้าม commit/push** |
| `origin` | `https://github.com/nattanonvs/odoo19ce-autoinfo.git` | repo ของเรา | พื้นที่ push ของทีม |

## Branch Model

| Branch | บทบาท | อายุ | กติกา |
|---|---|---|---|
| `upstream/19.0` | mirror ของ Odoo original | ถาวร | ห้าม commit |
| `19.0` | **trunk** = upstream + งานเรา | ถาวร | protected · ห้าม push ตรง · merge ผ่าน PR |
| `feature/od19-<domain>-<topic>` | งานใหม่ | อายุสั้น | แตกจาก `19.0` · ลบเมื่อ merge |
| `fix/od19-<topic>` | แก้บั๊ก | อายุสั้น | แตกจาก `19.0` |
| `hotfix/od19-<topic>` | แก้ฉุกเฉินบน production | อายุสั้น | แตกจาก tag ที่ deploy อยู่ |
| `backup/*` | สำรองชั่วคราว | ลบได้ | ใช้เพื่อ backup เท่านั้น |

**Naming contract:** ใช้ prefix เดียว `feature/` (ไม่ใช้ `feat/`, `codex/`, หรือชื่อเปล่า)

## Versioning & Tag

- Tag แบบ **annotated**: `git tag -a v19.0.<n> -m "<release note>"`
- `n` เพิ่มทุกครั้งที่ปล่อยงานของเรา (เรียงตามเวลา · error ไม่ใช้ semver เต็มสำหรับ core)
- ทุก tag ต้องบันทึก: **upstream SHA** ที่ trunk อ้างอยู่ + **OCA SHAs** ที่เปลี่ยน + รายการโมดูลที่แก้ + migration + rollback tag
- **ห้าม deploy จาก branch tip** — deploy จาก tag เท่านั้น

## Upstream Sync

- `git fetch upstream --prune` แล้ว `git merge upstream/19.0` เข้า `19.0`
- ปลอดภัยเพราะ path ของ core (`odoo/`, `addons/`, `setup/`, `debian/`, `doc/`) ไม่ทับกับพื้นที่ของเรา
- ถ้ามี conflict ให้เกิดเฉพาะไฟล์ขอบ (`/.gitignore`, `/.gitmodules`) — แก้ด้วยมือและ review
- หลัง merge ต้องทดสอบติดตั้ง/อัปเกรดโมดูลก่อน tag

## OCA (Submodules)

- pin ด้วย **commit SHA** เท่านั้น — `.gitmodules` **ห้ามมี `branch =`**
- ห้ามใช้ `git submodule update --remote`
- ทุกการขยับ OCA = 1 commit ที่ review ได้ + บันทึกเหตุผล
- เครื่องปลายทางต้อง `git submodule update --init --recursive`

## Khoảng cấm (Prohibited)

- ห้าม commit/push ไป `upstream/*`
- ห้าม `git push --force` ไป `19.0` หรือ branch ที่ทีมใช้
- ห้าม deploy จาก branch tip
- ห้ามฝัง secret (DB password, admin_passwd, Sentry DSN) ในไฟล์ที่ commit
- ห้ามแก้ path ของ Odoo core ในงานปกติ

## Release Checklist

- [ ] merge งานเข้า `19.0` ผ่าน PR + review
- [ ] ติดตั้ง/อัปเกรดโมดูลที่แก้ผ่าน (`-u <module> --stop-after-init`)
- [ ] `git submodule status` สะอาด
- [ ] สร้าง tag `v19.0.<n>` + เขียน release note
- [ ] push `19.0` + tag ขึ้น `origin`
- [ ] ตรวจว่า checkout tag บนเครื่องทดสอบแล้ว start ได้

## Rollback

- ระดับ release: `git checkout v19.0.<n-1>` + `git submodule update --init --recursive` + restart
- ระดับ ref: กู้จาก branch `backup/*` หรือ bundle ใน `backups/`

## Review Cadence

- ทบทวนเมื่อเปลี่ยนโมเดลสาขา/โฮสต์/รูปแบบเวอร์ชัน
- ทบทวนหลังเกิด incident จากการ deploy ผิด ref หรือ merge upstream ไม่ผ่าน
