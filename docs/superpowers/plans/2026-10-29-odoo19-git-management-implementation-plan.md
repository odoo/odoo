# Odoo 19 Git Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** จัดระเบียบ git ของ repo `odoo19ce-autoinfo` ให้ (1) อัปเวอร์ชันจาก Odoo original ได้ง่าย (2) ทีมพัฒนาและอัปเวอร์ชันได้ง่าย (3) ใช้เป็น source code ติดตั้งลงเซิร์ฟเวอร์อื่นได้ และ (4) มี release ที่อ้างอิงได้จริง

**Architecture (Decision A — Monorepo ที่มีวินัย):** คง repo เดียว (core อยู่ใน repo) แต่แยก "พื้นที่ของ upstream" (`odoo/`, `addons/`, `setup/`, `debian/`, `doc/`) ออกจาก "พื้นที่ของเรา" (`custom_addons/`, `docs/`, `deployment/`, `third_party/oca/`, สคริปต์) อย่างชัดเจน — trunk `19.0` = `upstream/19.0` + งานเรา และ merge `upstream/19.0` เข้า trunk โดย path ไม่ทับกันจึงแทบไม่ conflict

**Tech Stack:** Git, GitHub, PowerShell (Windows dev), Bash/systemd (Linux server), `gh` CLI (branch protection), OCA submodules

**Decisions ที่ยืนยันแล้ว:** D1 = Monorepo (ไม่แยก core ออก) · D2 = trunk ชื่อ `19.0` · D3 = version เป็น semver `v19.0.x` · D4 = core เก็บใน repo เหมือนเดิม · D5 = โฮสต์ GitHub (mirror เพิ่มได้ภายหลัง)

**เอกสารอ้างอิง:**
- [repository-and-addon-baseline.md](file:///c:/odoo-dev/odoo19/docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md)
- [environment-and-delivery-baseline.md](file:///c:/odoo-dev/odoo19/docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md)

---

## กติกาความปลอดภัย (บังคับทุก phase)

- **Phase 0 ต้องผ่านก่อน** — ห้ามเริ่ม Phase 1 ถ้ายังไม่มี `git bundle` สำรอง
- **ห้าม** `git push --force` ไปยัง `19.0` หรือ branch ที่ทีมใช้ร่วม
- **ห้าม** commit ลง `upstream/19.0` หรือแตะ path ของ Odoo core (`odoo/`, `addons/`, `setup/`, `debian/`, `doc/`)
- ทุกการเปลี่ยน gitlink ของ OCA = 1 commit ที่ review ได้
- ห้าม deploy จาก branch tip — deploy จาก **tag** เท่านั้น

## Test / Run Convention

- Repo: `c:\odoo-dev\odoo19`
- OCA init: `git submodule update --init --recursive`
- ตรวจความสะอาดก่อนทุก phase: `git status -sb` ต้องไม่มี uncommitted change ที่ไม่ตั้งใจ
- ตรวจ graph: `git log --graph --oneline --decorate -30 --all`

> **หมายเหตุ:** ช่วง execute ต้องมี terminal ที่ใช้งานได้ (ปัจจุบัน terminal error — ต้องแก้ก่อนเริ่ม Phase 0)

---

## File Structure

**สร้างใหม่**

| ไฟล์ | หน้าที่ |
|---|---|
| `.gitattributes` | บังคับ EOL (LF สำหรับ source, CRLF สำหรับ `.ps1`/`.bat`) ให้ Windows↔Linux ตรงกัน |
| `.github/CODEOWNERS` | กำหนดเจ้าของ `custom_addons/`, `docs/`, `deployment/` |
| `deployment/odoo.conf.template` | template คอนฟิกสำหรับ deploy เซิร์ฟเวอร์อื่น |
| `deployment/systemd/odoo19.service` | service template (Linux) |
| `deployment/install.sh` | bootstrap Linux: clone → submodule → venv → pip → start |
| `deployment/README.md` | ขั้นตอนติดตั้งลงเซิร์ฟเวอร์อื่น |
| `docs/superpowers/programs/odoo19-enterprise/foundation/git-and-release-baseline.md` | governance: โมเดลสาขา, version, release, rollback |
| `backups/odoo19-<date>.bundle` | สำรอง (`backups/` ถูก ignore แล้ว) |

**ปรับปรุง**

| ไฟล์ | การเปลี่ยน |
|---|---|
| `.gitmodules` | เอา `branch = 19.0` ออกให้ชัดว่า pin ด้วย SHA (ไม่ใช้ `--remote`) |
| `.gitignore` | ตรวจซ้ำว่า venv/pylibs/wkhtmltopdf/logs ไม่หลุดเข้า index |

---

# Phase 0 — Safety & Baseline Inventory (บังคับ)

### Task 0.1: สำรอง (⚠️ ปรับวิธี — ดูเหตุผล)

> **ผลตรวจจริง:** `git count-objects -vH` → `size-pack: 4.90 GiB` · `git bundle --all` จะได้ไฟล์ ~5GB (ช้า/หนัก) และ **commit ของเราเกือบทั้งหมดถูก push ไป `origin` แล้ว** (เหลือเฉพาะ tip `7182067` ที่ยังไม่ push) จึงเปลี่ยนไปใช้ **push-based backup** เป็นหลัก และทำ bundle เฉพาะเมื่อต้องการสำรองแบบ offline

- [x] สร้างโฟลเดอร์สำรอง + inventory (ทำแล้ว)

```powershell
Set-Location c:\odoo-dev\odoo19
New-Item -ItemType Directory -Force -Path .\backups | Out-Null
git for-each-ref --format='%(refname) %(objectname:short)'   | Out-File .\backups\refs-before.txt   -Encoding utf8
git branch -vv                                               | Out-File .\backups\branch-inventory.txt -Encoding utf8
git log --graph --oneline --decorate -60 --all               | Out-File .\backups\graph-before.txt  -Encoding utf8
git status -sb                                               | Out-File .\backups\status-before.txt -Encoding utf8
```

- [ ] **(ทางเลือก A — แนะนำ, ต้องอนุมัติ push)** สำรองด้วยการ push branch ที่ยังไม่ขึ้น origin

```powershell
git push origin 19.0:refs/heads/backup/19.0-2026-10-29   # push เป็น branch สำรอง ไม่ทับ 19.0
git push origin feat/od19-document-pull
git push origin feature/wave1-project-analytic-accounting
git push origin feature/wave1-customer-risk-credit-gate
git push origin feature/dashboard-formula-status-rules
git push origin codex/wave1-accounting-operational-closure
git push origin wave1-sales-contract-core
```

- [ ] **(ทางเลือก B — offline, ช้า ~5GB)** bundle เฉพาะเมื่อจำเป็น

```powershell
git bundle create ".\backups\odoo19-$(Get-Date -Format yyyyMMdd-HHmm).bundle" --branches --tags
git bundle verify ".\backups\<ไฟล์ที่สร้าง>.bundle"
```

### Task 0.2: เก็บ inventory ของ branch ปัจจุบัน
- [ ] บันทึก branch ทั้งหมด + upstream tracking + last commit

```powershell
git branch -vv | Out-File .\backups\branch-inventory.txt -Encoding utf8
git log --graph --oneline --decorate -40 --all | Out-File .\backups\graph-before.txt -Encoding utf8
```

- [ ] บันทึกความสัมพันธ์กับ upstream ที่ต้องรู้ (ผลลัพธ์ใช้ตัดสินใจ Phase 2)

```powershell
git rev-parse --short origin/19.0 upstream/19.0          # ควรเท่ากัน = mirror ตรง
git rev-parse --short 19.0                               # ปัจจุบัน diverge
git merge-base --is-ancestor origin/19.0 19.0; "19.0 descendant of origin/19.0? exit=$LASTEXITCODE"
git log --oneline origin/19.0..19.0 --no-merges | Measure-Object -Line   # กี่ commit ของเราบน 19.0
git log --oneline 19.0..feat/od19-wave2b-vat-compliance --no-merges | Measure-Object -Line
```

**Decision Gate 0 — ผลตรวจจริง (2026-10-29): เลือกเส้นทาง Rebuild-A**

| รายการ | ค่าที่พบ |
|---|---|
| `origin/19.0` | `3a50abd` — เป็น **mirror เก่าของ upstream ล้วน** (ahead upstream = 0, behind = 7) → มี unique commit 0 ตัว |
| `upstream/19.0` | `e5a4af1` (odoo/odoo ล่าสุด) |
| local `19.0` | `7182067` = upstream@`e4e2d65` + **460 commit ของเรา** (merge-base = `e4e2d65` "[I18N] *: fetch latest Weblate translations") |
| 19.0 ตามหลัง upstream | **274 commit** |
| ประวัติ | **เส้นตรง ไม่มี merge** — `19.0` → `feat/od19-wave2b-vat-compliance` → `feat/od19-wave3-corporate-income-tax` |
| Submodules | สะอาด ครบ 18 ตัว (ไม่มี `+`/`-`) |
| Working tree | **ไม่สะอาด** — 5 modified + 5 untracked (งาน WIP ของผู้ใช้) → ห้ามสลับ branch ก่อนเคลียร์ |

**ข้อสรุป:**
1. ใช้ **Rebuild-A** — local `19.0` เป็นลูกหลานของ upstream อยู่แล้ว path ของ core ไม่ทับกับงานเรา → merge `upstream/19.0` เข้า trunk ได้ปลอดภัย (ต้องทดสอบใน tmp branch ก่อนตาม Task 2.2-A)
2. `origin/19.0` ปัจจุบันเป็น mirror ที่ไร้ค่า (⊂ upstream) แต่ **ไม่ใช่ trunk ของเรา** → ต้องตัดสินใจว่าจะให้ `origin/19.0` เป็น trunk (= force-update ครั้งเดียว) หรือย้ายไปใช้ชื่ออื่น
3. **ห้ามสลับ/rebuild branch ขณะ working tree ไม่สะอาด** — ต้อง commit/stash งาน WIP ก่อนเข้า Phase 1-3

---

# Phase 1 — Branch Taxonomy (จัดชื่อให้เป็นระบบเดียว)

### Task 1.1: กำหนด naming contract
- [ ] ใช้ prefix เดียว **`feature/`** (เลิกใช้ `feat/`, `feature/`, `codex/` ปนกัน)
- [ ] รูปแบบ: `feature/od19-<domain>-<topic>`, `fix/od19-<topic>`, `hotfix/od19-<topic>`
- [ ] งานที่ merge แล้ว → ลบทิ้งทันที

### Task 1.2: ตรวจว่าอะไร merge เข้า trunk แล้ว
- [ ] เทียบแต่ละ branch กับ `19.0`

```powershell
foreach ($b in @('wave1-sales-contract-core','feature/dashboard-formula-status-rules',
  'feature/wave1-customer-risk-credit-gate','feature/wave1-project-analytic-accounting',
  'codex/wave1-accounting-operational-closure','feat/od19-document-pull')) {
  $n = (git log --oneline 19.0..$b --no-merges | Measure-Object -Line).Lines
  "$b : $n commit ยังไม่เข้า 19.0"
}
```

### Task 1.3: Rename / ลบ branch ที่ตกค้าง
- [ ] Rename ให้เข้า naming contract (เฉพาะที่ยังต้องใช้)

```powershell
git branch -m feat/od19-document-pull      feature/od19-document-pull
git branch -m feature/dashboard-formula-status-rules feature/od19-dashboard-formula-status-rules
# ...rename ตัวอื่นในทำนองเดียวกันตามผล Task 1.2
```

- [ ] ลบ branch ตาย/ซ้ำ (เฉพาะหลังยืนยันว่า merge แล้วใน Task 1.2)

```powershell
git branch -d wave1-sales-contract-core
git branch -D 19.0-rebuilt 19.0-original-broken-merge   # เก็บ bundle แล้วเท่านั้น
```

> ⚠️ ยัง**ไม่ลบ** `feat/od19-wave2b-vat-compliance` จนกว่าจะย้ายงานเข้า trunk เสร็จ (Phase 2)

---

# Phase 2 — Rebuild trunk `19.0` ให้ sync upstream ได้

### Task 2.1: ยืนยันงานปัจจุบัน commit ครบ
- [ ] บน branch `feat/od19-wave2b-vat-compliance`

```powershell
git status -sb          # ต้องสะอาด
git log --oneline -5
```

### Task 2.2-Rebuild-A (ใช้เมื่อ 19.0 เป็นลูกหลานตรงของ origin/19.0)
- [ ] ตั้ง trunk = 19.0 ปัจจุบัน (path ของ core ไม่ทับกับงานเรา จึง merge upstream ได้ปลอดภัย)
- [ ] ทดสอบ merge upstream เข้า trunk ในสาขาทดลองก่อน

```powershell
git fetch upstream --prune
git checkout -b tmp/upstream-merge-test 19.0
git merge --no-commit --no-ff upstream/19.0
git status               # ตรวจ conflict — คาดว่า conflict แค่ .gitignore/.gitmodules (ถ้ามี)
git merge --abort        # ยกเลิกการทดสอบ (ไม่ commit)
```

- [ ] ถ้าไม่มี conflict ที่ path ของเรา → merge จริงเข้า trunk ภายหลังตอนอัปเดตจริง (ไม่ต้องทำตอนนี้)

### Task 2.2-Rebuild-B (ใช้เมื่อ 19.0 ไม่ใช่ลูกหลานตรงของ upstream)
- [ ] สร้าง trunk ใหม่สะอาดจาก upstream แล้วย้ายงานเข้าเป็นชุด commit ที่จัดระเบียบ

```powershell
git fetch upstream --prune
git checkout -b 19.0-new upstream/19.0            # base สะอาดจาก original
git checkout feat/od19-wave2b-vat-compliance -- custom_addons docs deployment `
    requirements-od19.txt *.ps1 *.py term-health.ps1 .gitmodules .gitignore
git status                                        # ตรวจว่าได้ไฟล์ครบ เฉพาะพื้นที่ของเรา
git commit -m "feat(project): import customized addons, docs and deployment baseline"
```

- [ ] ตรวจว่าไม่มีไฟล์ core หลุดเข้ามา

```powershell
git show --stat --oneline HEAD | Select-String -Pattern '^(odoo|addons|setup|debian|doc)/'
# ต้องไม่พบผลลัพธ์ (ว่าง)
```

### Task 2.3: สลับ trunk
- [ ] (เฉพาะ Rebuild-B) แทนที่ `19.0` เดิม แล้วผลักขึ้น origin

```powershell
git branch -m 19.0 19.0-legacy-cherrypicks        # เก็บของเดิมไว้เป็นหลักฐาน
git branch -m 19.0-new 19.0
git push -u origin 19.0 --force-with-lease        # ต้องได้รับอนุมัติ + แจ้งทีมก่อน
```

- [ ] ตั้ง upstream tracking ของ trunk

```powershell
git branch --set-upstream-to=origin/19.0 19.0
```

---

# Phase 3 — Tag & Release (semver v19.0.x)

### Task 3.1: Tag release แรก
- [ ] สร้าง annotated tag พร้อม note

```powershell
git checkout 19.0
git tag -a v19.0.0 -m "Odoo 19 CE Enterprise baseline (Wave 2C complete)"
git push origin v19.0.0
```

### Task 3.2: ตั้งกติกาเวอร์ชัน
- [ ] `v19.0.<patch>`: patch = การแก้/เพิ่มงานเรา (ไม่เปลี่ยนเวอร์ชัน Core)
- [ ] ถ้าอัป Core เป็น 19.0 release ใหม่ → สร้าง tag `v19.0.<n>` ใหม่ + บันทึก commit ของ upstream ที่ใช้
- [ ] บันทึกใน release note: upstream SHA ที่ trunk อ้างอยู่ + OCA SHAs

### Task 3.3: Release note template
- [ ] สร้างโฟลเดอร์/ไฟล์ note ต่อ release (ภายหลังใน `deployment/releases/`)

```text
## v19.0.<n> — <วันที่>
- Upstream base: <sha ของ upstream/19.0>
- OCA: <repo>@<sha> ... (เฉพาะที่เปลี่ยน)
- โมดูลที่เปลี่ยน: <รายการ od19_*>
- Migration: <ต้อง -u โมดูลใด / มี data migration?>
- Rollback: git checkout v19.0.<n-1>
```

---

# Phase 4 — Repo Hygiene (.gitattributes / .gitignore / CODEOWNERS)

### Task 4.1: เพิ่ม `.gitattributes` (Windows↔Linux)
- [ ] สร้างไฟล์ `.gitattributes` ที่ root

```gitattributes
* text=auto eol=lf
*.ps1 text eol=crlf
*.bat text eol=crlf
*.cmd text eol=crlf
*.png binary
*.jpg binary
*.pdf binary
*.xlsx binary
*.po text eol=lf
```

- [ ] Normalize EOL ครั้งเดียว (จะแตะ index จำนวนมาก — ทำเป็น commit เดี่ยว)

```powershell
git add --renormalize .
git commit -m "chore(repo): enforce line-ending policy via .gitattributes"
```

### Task 4.2: ตรวจ `.gitignore`
- [ ] ยืนยันว่า artifact ต่อไปนี้ไม่ถูก track

```powershell
git check-ignore -v venv19 pylibs wkhtmltopdf backups odoo_local.conf zk_verify.log
# ต้องมีผลลัพธ์ทุกบรรทัด (ถูก ignore)
git ls-files | Select-String -Pattern '^(venv19|pylibs|wkhtmltopdf|backups)/' | Measure-Object -Line
# ต้องได้ 0
```

### Task 4.3: เพิ่ม `CODEOWNERS`
- [ ] สร้าง `.github/CODEOWNERS`

```text
# default
*                       @nattanonvs

# project-owned areas
/custom_addons/         @nattanonvs
/docs/                  @nattanonvs
/deployment/            @nattanonvs

# upstream-owned — ห้ามแก้โดยไม่ปรึกษา
/odoo/                  @nattanonvs
/addons/                @nattanonvs
```

- [ ] commit

---

# Phase 5 — Team Workflow (Branch protection + Checks)

### Task 5.1: ป้องกัน branch `19.0` บน GitHub
- [ ] ใช้ `gh` CLI ตั้ง protection (ห้าม push ตรง/force, บังคับ PR + review)

```powershell
gh api -X PUT repos/nattanonvs/odoo19ce-autoinfo/branches/19.0/protection `
  -f required_status_checks=null `
  -F enforce_admins=true `
  -F required_pull_request_reviews[required_approving_review_count]=1 `
  -F required_pull_request_reviews[dismiss_stale_reviews]=true `
  -F restrictions=null `
  -F allow_force_pushes=false `
  -F allow_deletions=false
```

### Task 5.2: Merge policy
- [ ] ใช้ **Squash merge** เป็นค่าเริ่มต้น (ประวัติ trunk อ่านง่าย)
- [ ] ปิด rebase/merge commit ถ้าไม่จำเป็น

### Task 5.3: ตั้ง Conventional Commits + checks
- [ ] บังคับรูปแบบ: `feat|fix|docs|chore|test|refactor(scope): ...`
- [ ] required checks: lint `ruff` + ติดตั้ง/อัปเกรดโมดูลที่แก้ (`-u <module> --stop-after-init`)
- [ ] (ออปชัน) GitHub Actions รัน `ruff check .` และ `odoo-bin -u <changed> --stop-after-init`

---

# Phase 6 — Deployment Package (ติดตั้งลงเซิร์ฟเวอร์อื่น)

### Task 6.1: สร้าง `deployment/`
- [x] `deployment/odoo.conf.template` — `addons_path` ชี้ core + OCA + custom (`addons_path` เป็น absolute path ตามเครื่องปลายทาง)

```ini
[options]
addons_path = ./odoo/addons,./addons,./third_party/oca/*,./custom_addons
db_host = localhost
db_port = 5432
db_user = odoo
db_password = __SET_ME__
proxy_mode = True
workers = 4
```

- [x] `deployment/systemd/odoo19.service` — service template
- [x] `deployment/install.sh` — ขั้นตอน clone → submodule → venv → pip → start (มี special case `signxml --no-deps`)

```bash
#!/usr/bin/env bash
set -euo pipefail
git clone --recurse-submodules <repo-url> odoo19 && cd odoo19
git checkout "${OD19_TAG:?set OD19_TAG}"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r requirements-od19.txt
cp deployment/odoo.conf.template odoo_local.conf   # แล้วแก้ค่า __SET_ME__
```

- [x] `deployment/README.md` — ขั้นตอนติดตั้ง + ค่า `addons_path` + วิธี checkout tag
- [ ] commit (รอ working tree สะอาด — commit รวมกับ Phase 4)

### Task 6.2: ตรวจ "ติดตั้งได้" จาก tag
- [ ] ทดสอบว่า checkout tag + submodule + start ผ่าน (บนเครื่อง Linux หรือ WSL)

```powershell
git clone --recurse-submodules c:\odoo-dev\odoo19 c:\odoo-dev\_install_test
Set-Location c:\odoo-dev\_install_test
git checkout v19.0.0
git submodule status    # ต้องมี SHA ครบทุกตัว
```

- [ ] ลบโฟลเดอร์ทดสอบเมื่อเสร็จ

---

# Phase 7 — Governance & Docs

### Task 7.1: สร้าง git-and-release-baseline
- [x] สร้าง `docs/superpowers/programs/odoo19-enterprise/foundation/git-and-release-baseline.md` บันทึก: โมเดลสาขา, naming, version scheme, tag/release process, rollback, OCA pinning, ข้อห้าม

### Task 7.2: อัปเดตเอกสารที่มีอยู่
- [ ] อัปเดต [repository-and-addon-baseline.md](file:///c:/odoo-dev/odoo19/docs/superpowers/programs/odoo19-enterprise/foundation/repository-and-addon-baseline.md) — เพิ่มพื้นที่ `deployment/` และ path ownership
- [ ] อัปเดต [environment-and-delivery-baseline.md](file:///c:/odoo-dev/odoo19/docs/superpowers/programs/odoo19-enterprise/foundation/environment-and-delivery-baseline.md) — ผูก promotion กับ tag/release
- [ ] commit ด้วย `docs(governance): ...`

---

## Verification (หลังจบทุก phase)

- [ ] `git status -sb` สะอาด และ `git log --graph --oneline --decorate -30` อ่านรู้เรื่อง
- [ ] `git rev-parse origin/19.0 upstream/19.0` ยังเท่ากัน (mirror ไม่ถูกแตะ)
- [ ] `git tag -l "v19.0.*"` มี tag และ `git show v19.0.0` แสดง note
- [ ] `git submodule status` ครบทุกตัว และ `.gitmodules` ไม่มี `branch=` แล้ว
- [ ] `git check-ignore` ยืนยันว่า venv/pylibs/wkhtmltopdf ไม่ถูก track
- [ ] clone ใหม่ + `checkout v19.0.x` + submodule ครบ → start Odoo ได้

## Rollback

- กู้จาก bundle: `git clone .\backups\odoo19-<date>.bundle odoo19-restore`
- คืน branch: `git checkout -B <branch> <sha จาก bundle>`
- ถ้า force-push trunk ไปแล้วและต้องย้อน: แจ้งทีม + `git push --force-with-lease origin <sha เดิม>` (ต้องอนุมัติ)

## Out of Scope (เฟสนี้ไม่ทำ)

- แยก core เป็น repo/submodule ภายนอก (Decision A ไม่ทำ — ทบทวนได้ในอนาคต)
- เขียน history ใหม่ (rebase/filter-repo) ของ branch ที่แชร์แล้ว
- GitLab mirror (Decision D5 — เพิ่มภายหลังได้)
