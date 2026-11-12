# Employee Experience (Portal) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่ม "อารมณ์ร่วม" ให้หน้า `/employee-portal` ของ Odoo 19 ด้วย 3 ธีม (Personal Touch / Daily Companion / Recognition & Belonging) โดยไม่รื้อของเดิมและไม่แตะ Odoo core

**Architecture:** ปรับ `od19_website` (ธีม 1 + ธีม 3) และสร้างโมดูลใหม่ `od19_recognition` (ธีม 2) แบบ **additive** — `od19_recognition` แทรกบล็อกเข้า `od19_website.od19_employee_portal` ผ่าน anchor `<div id="od19-recognition-anchor"/>` ด้วย `xpath`; ถอนโมดูลออกแล้วหน้ายังทำงานปกติ ข้อมูลหนักโหลดแบบ lazy JSON + cache ต่อผู้ใช้ TTL 60s ตามแพตเทิร์น `/my/approvals/summary`

**Tech Stack:** Odoo 19 CE · Python 3 (models/controllers) · QWeb + Bootstrap 5 · vanilla JS (fetch) · CSS ต่อท้าย `od19_website.css` · `run-tests.ps1` (PowerShell 7)

---

**อ้างอิง (อ่านก่อนลงมือ):**
- Spec: [`docs/superpowers/specs/2026-11-11-od19-employee-experience-design.md`](file:///c:/odoo-dev/od19-emp-exp/docs/superpowers/specs/2026-11-11-od19-employee-experience-design.md)
- กฎ repo: [`AGENTS.md`](file:///c:/odoo-dev/od19-emp-exp/AGENTS.md) (r2 — Resource-Scoped Lease)
- แม่แบบแผน: [`2026-11-10-od19-ai-assistant-coverage.md`](file:///c:/odoo-dev/od19-emp-exp/docs/superpowers/plans/2026-11-10-od19-ai-assistant-coverage.md)
- แม่แบบ release note: [`v19.0.5.md`](file:///c:/odoo-dev/od19-emp-exp/deployment/releases/v19.0.5.md)

---

## File Structure

| ไฟล์ | บทบาท | การเปลี่ยนแปลง |
|---|---|---|
| `custom_addons/od19_website/controllers/main.py` | คอนโทรลเลอร์ portal + helper | เพิ่ม constant `ME_SUMMARY_CACHE` / helper `_od19_greeting`, `_od19_initials`, `_od19_today_attendance`, `_od19_approvals_kpi`, `_od19_leave_remaining`, `_od19_unread_announcements`, `_od19_my_schedule` + route `/employee-portal/me-summary`; เพิ่มคีย์ใน render dict ของ `employee_portal` |
| `custom_addons/od19_website/views/employee_portal.xml` | โครงหน้า portal | แทน Hero (บล็อก [A]) + แทรก [B] My Day + [C] My Schedule + anchor ก่อน [E] + จัดกลุ่ม Quick Access ([G]) |
| `custom_addons/od19_website/static/src/css/od19_website.css` | CSS แบรนด์ + คลาสใหม่ | ต่อท้ายไฟล์: avatar / day-card / panel / schedule / shortcut / group title |
| `custom_addons/od19_website/static/src/js/od19_my_day.js` | lazy fetch me-summary | สร้างใหม่ |
| `custom_addons/od19_website/__manifest__.py` | asset + version | เพิ่ม JS ใหม่ใน `web.assets_frontend`; bump version → `19.0.1.1.0` |
| `custom_addons/od19_website/tests/__init__.py` | รวมเทสต์ | เพิ่ม import 2 ไฟล์ใหม่ |
| `custom_addons/od19_website/tests/test_me_summary.py` | เทสต์ me-summary | สร้างใหม่ |
| `custom_addons/od19_website/tests/test_employee_experience.py` | เทสต์ Hero/บล็อกหน้า | สร้างใหม่ |
| `custom_addons/od19_recognition/__manifest__.py` | manifest โมดูลใหม่ | สร้างใหม่ |
| `custom_addons/od19_recognition/__init__.py` | โหลด models/controllers | สร้างใหม่ |
| `custom_addons/od19_recognition/models/__init__.py` | โหลดโมเดล | สร้างใหม่ |
| `custom_addons/od19_recognition/models/od19_recognition.py` | โมเดล Kudos | สร้างใหม่ |
| `custom_addons/od19_recognition/models/od19_recognition_badge.py` | โมเดลป้าย | สร้างใหม่ |
| `custom_addons/od19_recognition/security/od19_recognition_security.xml` | groups + ir.rule | สร้างใหม่ |
| `custom_addons/od19_recognition/security/ir.model.access.csv` | model access | สร้างใหม่ |
| `custom_addons/od19_recognition/data/od19_recognition_badge_data.xml` | ป้ายเริ่มต้น | สร้างใหม่ |
| `custom_addons/od19_recognition/controllers/portal.py` | routes Kudos | สร้างใหม่ |
| `custom_addons/od19_recognition/views/portal_templates.xml` | บล็อก Team Wall + หน้าเต็ม + ฟอร์ม | สร้างใหม่ |
| `custom_addons/od19_recognition/views/od19_recognition_views.xml` | backend views/models | สร้างใหม่ |
| `custom_addons/od19_recognition/views/menus.xml` | เมนู backend | สร้างใหม่ |
| `custom_addons/od19_recognition/static/src/css/od19_recognition.css` | CSS บล็อก Kudos | สร้างใหม่ |
| `custom_addons/od19_recognition/tests/__init__.py` | โหลดเทสต์ | สร้างใหม่ |
| `custom_addons/od19_recognition/tests/test_recognition.py` | เทสต์โมเดล + route | สร้างใหม่ |
| `deployment/releases/v19.0.7.md` | release note | สร้างใหม่ (v19.0.6 ถูกใช้ไปแล้วโดย PR #28) |

---

## Decisions (locked — อย่าเปลี่ยนระหว่างลงมือ)

1. **ไม่แตะ Odoo core** (`odoo/`, `addons/`) — แก้เฉพาะ `custom_addons/` (AGENTS.md §7)
2. **OD19_* ไม่มี** — ใช้ `custom_addons` เป็น addons_path ของโปรเจกต์; **ห้ามรันพอร์ต 8070**; ใช้ DB ทดสอบส่วนตัว `od19_t_trae-od19_emp_exp` + พอร์ต 8075 (default ของ `run-tests.ps1`)
3. **Additive เท่านั้น** — ธีม 2 อยู่โมดูล `od19_recognition`; ถอนได้โดยหน้า portal ไม่พัง (R7)
4. **โทนแบรนด์เดิม** — `#9E2424` (primary), `#f39200` (secondary), `#7A1B1B`, `#6b1515`, `#2a1a1a`; ฟอนต์ Sarabun; **ไม่เพิ่มชุดสีใหม่** (R9)
5. **Performance** — หน้าแรกเรนเดอร์ด้วยข้อมูลเบา; ส่วนหนัก (me-summary / recognition) โหลดหลังเรนเดอร์ด้วย `fetch()`; JSON endpoint ใช้ in-process dict cache ต่อผู้ใช้ TTL 60s (R3)
6. **Defensive** — ทุกจุดที่อ้างโมดูลทางเลือก (`hr.attendance`, `hr_holidays`, `announcement`, `od19.approval.source`) ต้องเช็ค `"<model>" in request.env` ก่อนเสมอ
7. **ความปลอดภัย** — ทุก route `auth="user"` + `website=True`; POST มี CSRF; บังคับ `author_id`/`company_id` ที่ฝั่ง server; อ่าน Kudos เฉพาะ `is_public = True` หรือเป็นผู้เกี่ยวข้อง; แก้/ลบเฉพาะเจ้าของ (R11, §11)
8. **ไม่มี action อนุมัติ/จ่ายเงินบน portal** (Zero Trust)
9. **Privacy HR** — วันเกิดแสดงเฉพาะเมื่อ `birthday_public_display = True` (ใช้ `birthday_public_display_string != "hidden"`); วันครบรอบใช้ `contract_date_start`/`date_start` (group hr manager → ใช้ `sudo()` และจำกัดเฉพาะภายในบริษัท)
10. **ห้าม `git add -A`/`git add .`** — `git add -- <path>` เท่านั้น; 1 commit = 1 โดเมน; commit/push เฉพาะ branch ตัวเอง `feature/od19_website-employee-experience`

---

## Test-Run Convention

- รัน Unit Test ของโมดูล: `.\run-tests.ps1 -Module od19_website` → เป้าหมาย **0 failed / 0 error(s)**
- รัน Unit Test ของโมดูลใหม่: `.\run-tests.ps1 -Module od19_recognition` → เป้าหมาย **0 failed / 0 error(s)**
- ตรวจไวยากรณ์เร็วระหว่างทาง: `venv19\Scripts\python.exe -m py_compile <path>` → ไม่มี output
- ตรวจ XML well-formed: `venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('<path>')"` → ไม่มี output
- **ห้าม commit จนกว่าเทสต์ทั้งโมดูลจะผ่าน** (AGENTS.md §4)
- หมายเหตุ: `run-tests.ps1` รันด้วย `-u <module>` — **ถ้าโมดูลใหม่ยังไม่ถูกติดตั้งใน DB ทดสอบ ต้อง `-i` ก่อน** (ดู Task 0)

---

### Task 0: เตรียมสภาพแวดล้อมทดสอบ (worktree `c:\odoo-dev\od19-emp-exp`)

**Files:**
- Create: `c:\odoo-dev\od19-emp-exp\odoo.conf` (ถูก gitignore — `/odoo.conf` ที่ `.gitignore:28` → ปลอดภัย ไม่ commit)
- Create (junction): `c:\odoo-dev\od19-emp-exp\venv19` → `c:\odoo-dev\odoo19\venv19`
- Create (DB): `od19_t_trae-od19_emp_exp`

- [ ] **Step 1: ยืนยันว่า worktree สะอาดและ branch ถูกต้อง**

Run:
```powershell
git -C c:\odoo-dev\od19-emp-exp status -sb
git -C c:\odoo-dev\od19-emp-exp log -1 --oneline
```
Expected: branch `feature/od19_website-employee-experience` และไม่มีไฟล์ของ agent อื่นค้าง (working tree สะอาด)

- [ ] **Step 2: สร้าง `odoo.conf` ของ worktree**

สร้างไฟล์ `c:\odoo-dev\od19-emp-exp\odoo.conf` โดย **คัดลอกค่า addons_path จาก `C:\odoo-dev\odoo19\odoo.conf` แต่เปลี่ยน 3 ตัวแรกให้ชี้ worktree** และ **OCA ยังชี้ main repo** (เพราะ `c:\odoo-dev\od19-emp-exp\third_party\oca` ว่างเปล่า):

```ini
[options]
addons_path = c:\odoo-dev\od19-emp-exp\addons,c:\odoo-dev\od19-emp-exp\odoo\addons,c:\odoo-dev\od19-emp-exp\custom_addons,C:\odoo-dev\odoo19\third_party\oca\l10n-thailand,C:\odoo-dev\odoo19\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\third_party\oca\server-backend,C:\odoo-dev\odoo19\third_party\oca\server-tools,C:\odoo-dev\odoo19\third_party\oca\server-ux,C:\odoo-dev\odoo19\third_party\oca\helpdesk,C:\odoo-dev\odoo19\third_party\oca\account-financial-tools,C:\odoo-dev\odoo19\third_party\oca\purchase-workflow,C:\odoo-dev\odoo19\third_party\oca\tier-validation,C:\odoo-dev\odoo19\third_party\oca\reporting-engine,C:\odoo-dev\odoo19\third_party\oca\knowledge,C:\odoo-dev\odoo19\third_party\oca\website,C:\odoo-dev\odoo19\third_party\oca\currency,C:\odoo-dev\odoo19\third_party\oca\stock-logistics-request,C:\odoo-dev\odoo19\third_party\oca\account-invoicing,C:\odoo-dev\odoo19\third_party\oca\account-financial-reporting,C:\odoo-dev\odoo19\third_party\oca\account-reconcile,C:\odoo-dev\odoo19\third_party\oca\mis-builder,C:\odoo-dev\odoo19\third_party\oca\account-analytic,C:\odoo-dev\odoo19\third_party\oca\product-attribute,C:\odoo-dev\odoo19\third_party\oca\contract
db_host = localhost
db_port = 5432
db_user = odoo
db_password = <คัดลอกค่าจริงจาก C:\odoo-dev\odoo19\odoo.conf (ห้าม commit ค่านี้ — ไฟล์ odoo.conf ถูก gitignore แล้ว)>
dbfilter = ^od19_t_trae-od19_emp_exp$
db_name = od19_t_trae-od19_emp_exp
data_dir = C:\odoo-dev\odoo19\data
http_port = 8081
workers = 0
bin_path = C:\odoo-dev\odoo19\wkhtmltopdf\bin
```

> **ห้ามใส่ `http_port = 8070`** (พอร์ตแชร์ — HARD LOCK AGENTS.md §1 Tier 3 ข้อ 7). `run-tests.ps1` จะ override ด้วย `--http-port 8075` อยู่แล้ว

- [ ] **Step 3: ผูก `venv19` เข้ากับ venv ของ main repo (junction)**

Run:
```powershell
New-Item -ItemType Junction -Path c:\odoo-dev\od19-emp-exp\venv19 -Target c:\odoo-dev\odoo19\venv19
Test-Path c:\odoo-dev\od19-emp-exp\venv19\Scripts\python.exe
```
Expected: `True`

- [ ] **Step 4: สร้างฐานข้อมูลทดสอบส่วนตัว**

Run:
```powershell
$srcConf = Get-Content -LiteralPath 'c:\odoo-dev\odoo19\odoo.conf'
$env:PGPASSWORD = ($srcConf | Select-String -Pattern '^\s*db_password\s*=\s*(.+)$').Matches.Groups[1].Value.Trim()
& 'C:\Program Files\PostgreSQL\16\bin\createdb.exe' -h localhost -p 5432 -U odoo od19_t_trae-od19_emp_exp
& 'C:\Program Files\PostgreSQL\16\bin\psql.exe' -h localhost -p 5432 -U odoo -l
```
Expected: สร้างสำเร็จ; เห็น `od19_t_trae-od19_emp_exp` ในรายการ DB

- [ ] **Step 5: ติดตั้งโมดูลที่ต้องใช้ลง DB ทดสอบ (ครั้้งเดียว)**

`run-tests.ps1` ใช้ `-u` ซึ่งไม่ติดตั้งโมดูลใหม่ ⇒ ต้อง `-i` ครั้งแรก (ติดตั้ง `od19_website` + `hr_attendance` + `hr_holidays` เพื่อทดสอบ me-summary ครบทุก branch):

Run:
```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& c:\odoo-dev\od19-emp-exp\venv19\Scripts\python.exe c:\odoo-dev\od19-emp-exp\odoo-bin `
  -c c:\odoo-dev\od19-emp-exp\odoo.conf `
  -i od19_website,hr_attendance,hr_holidays `
  --stop-after-init `
  --logfile c:\odoo-dev\od19-emp-exp\data_test_install.log
```
Expected: จบด้วย exit code 0; ตรวจ log: ไม่มี `ERROR` / `CRITICAL`
ตรวจซ้ำ:
```powershell
Select-String -LiteralPath c:\odoo-dev\od19-emp-exp\data_test_install.log -Pattern 'od19_website|hr_attendance|hr_holidays' | Select-Object -Last 10
```

- [ ] **Step 6: ตรวจว่า `run-tests.ps1` ทำงาน (smoke)**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
.\run-tests.ps1 -Module od19_website
```
Expected: ไม่มี exception; สรุปท้าย log ขึ้น `tests.result` (0 failed / 0 error(s) — ถ้ามี fail เดิมให้จดไว้ก่อนเริ่ม)

- [ ] **Step 7: บันทึก claim ในรายงาน + commit เฉพาะไฟล์ที่จำเป็น**

> ไม่มีไฟล์ใหม่ที่ต้อง commit ใน task นี้ (`odoo.conf`/`venv19` ถูก ignore). **ไม่ commit** — ไปต่อ Task 1

---

### Task 1: `/employee-portal/me-summary` (JSON + cache ต่อผู้ใช้)

**Files:**
- Modify: `custom_addons/od19_website/controllers/main.py` (เพิ่ม constant ~บรรทัด 46 + route/helper หลัง `od19_my_approvals_summary`)
- Create: `custom_addons/od19_website/tests/test_me_summary.py`
- Modify: `custom_addons/od19_website/tests/__init__.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน (failing test)**

สร้างไฟล์ `custom_addons/od19_website/tests/test_me_summary.py`:

```python
import datetime

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestMeSummary(HttpCase):
    def setUp(self):
        super().setUp()
        self.tester = self.env["res.users"].create(
            {
                "name": "Emp Exp Tester",
                "login": "emp_exp_tester",
                "password": "emp_exp_tester",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )

    def test_me_summary_returns_json_with_expected_keys(self):
        self.authenticate("emp_exp_tester", "emp_exp_tester")
        response = self.url_open("/employee-portal/me-summary")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        for key in (
            "attendance",
            "approvals",
            "next_booking",
            "leave",
            "unread_announcements",
            "schedule",
        ):
            self.assertIn(key, payload)
        self.assertIn("available", payload["attendance"])
        self.assertIn("pending_count", payload["approvals"])
        self.assertIsInstance(payload["schedule"], list)

    def test_me_summary_requires_login(self):
        response = self.url_open("/employee-portal/me-summary")
        self.assertIn(response.status_code, (302, 303, 401, 403))
```

แก้ `custom_addons/od19_website/tests/__init__.py` ให้เป็น:

```python
from . import test_employee_shortcut_menu
from . import test_website
from . import test_approval_portal
from . import test_me_summary
from . import test_employee_experience
```

สร้างไฟล์ `custom_addons/od19_website/tests/test_employee_experience.py` เป็น **placeholder ชั่วคราว** (จะเติมเทสต์จริงใน Task 2/3/4):

```python
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestEmployeeExperiencePlaceholder(TransactionCase):
    def test_placeholder(self):
        self.assertTrue(True)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
.\run-tests.ps1 -Module od19_website
```
Expected: FAIL — `test_me_summary_returns_json_with_expected_keys` (route `/employee-portal/me-summary` ยังไม่มี → 404)

- [ ] **Step 3: เพิ่ม constant cache**

ใน `custom_addons/od19_website/controllers/main.py` แทรก **ต่อจากบรรทัด `APPROVAL_SUMMARY_TTL = 60`** (ปัจจุบันบรรทัด 46):

```python
# Short-lived per-user cache for the "My Day" summary. Same trade-off as the
# approval badge: a 60s staleness window beats re-scanning attendance, leaves
# and announcements on every portal load.
ME_SUMMARY_CACHE = {}
ME_SUMMARY_TTL = 60
```

- [ ] **Step 4: เพิ่ม route + helpers**

ใน `custom_addons/od19_website/controllers/main.py` แทรก **ต่อจากเมธอด `od19_my_approvals_summary` (หลังบรรทัด 138)**:

```python
    # ------------------------------------------------------------------
    # Employee portal — "My Day" summary (lazy JSON)
    # ------------------------------------------------------------------
    @http.route(
        ["/employee-portal/me-summary"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def od19_employee_me_summary(self, **kwargs):
        """Light "my day" KPI payload for the portal strip (lazy, cached).

        Kept out of the portal page render so the page stays fast; the strip
        fetches it afterwards and fills placeholders in place.
        """
        user_id = request.env.user.id
        mono = time.monotonic()
        cached = ME_SUMMARY_CACHE.get(user_id)
        if cached and mono - cached[0] < ME_SUMMARY_TTL:
            return request.make_json_response(cached[1])
        payload = self._od19_me_summary_data()
        ME_SUMMARY_CACHE[user_id] = (mono, payload)
        return request.make_json_response(payload)

    def _od19_me_summary_data(self):
        """Aggregate the employee's own day, defensive against missing modules."""
        employee = request.env.user.employee_id
        today = datetime.date.today()
        upcoming = self._od19_my_upcoming_bookings()
        return {
            "attendance": self._od19_today_attendance(employee, today),
            "approvals": self._od19_approvals_kpi(),
            "next_booking": upcoming[0] if upcoming else None,
            "leave": self._od19_leave_remaining(employee),
            "unread_announcements": self._od19_unread_announcements(today),
            "schedule": self._od19_my_schedule(),
        }

    def _od19_today_attendance(self, employee, today):
        """Today's check-in / check-out / worked hours for the current employee."""
        if not employee or "hr.attendance" not in request.env:
            return {"available": False}
        tz = pytz.timezone(request.env.user.tz or "UTC")
        day_start = (
            tz.localize(datetime.datetime.combine(today, datetime.time.min))
            .astimezone(pytz.utc)
            .replace(tzinfo=None)
        )
        day_end = (
            tz.localize(datetime.datetime.combine(today, datetime.time.max))
            .astimezone(pytz.utc)
            .replace(tzinfo=None)
        )
        records = (
            request.env["hr.attendance"]
            .sudo()
            .search(
                [
                    ("employee_id", "=", employee.id),
                    ("check_in", ">=", day_start),
                    ("check_in", "<=", day_end),
                ],
                order="check_in asc",
            )
        )
        if not records:
            return {
                "available": True,
                "state": "none",
                "check_in": None,
                "check_out": None,
                "worked_hours": 0.0,
            }
        last = records[-1]
        return {
            "available": True,
            "state": "in" if not last.check_out else "out",
            "check_in": self._od19_local(records[0].check_in, "%H:%M"),
            "check_out": self._od19_local(last.check_out, "%H:%M")
            if last.check_out
            else None,
            "worked_hours": round(sum(records.mapped("worked_hours")), 2),
        }

    def _od19_approvals_kpi(self):
        """Reuse the existing approval KPI; never recompute the sources here."""
        if "od19.approval.source" not in request.env:
            return {"pending_count": 0, "max_age_days": 0, "over_sla_count": 0}
        sources = (
            request.env["od19.approval.source"].sudo().search([("active", "=", True)])
        )
        return sources._od19_approval_summary()

    def _od19_leave_remaining(self, employee):
        """Remaining time off, only when the field exists and is shareable."""
        if not employee or "allocation_remaining_display" not in employee._fields:
            return {"available": False}
        if "show_leaves" in employee._fields and not employee.show_leaves:
            return {"available": False}
        return {
            "available": True,
            "remaining_display": employee.allocation_remaining_display or "0",
        }

    def _od19_unread_announcements(self, today):
        """Announcements still live that the user has not opened yet."""
        if "announcement" not in request.env:
            return 0
        Announcement = request.env["announcement"].sudo()
        live = Announcement.search(
            [
                ("published", "=", True),
                "|",
                ("expiry_date", "=", False),
                ("expiry_date", ">=", today),
            ]
        )
        if not live:
            return 0
        if "announcement.read" not in request.env:
            return len(live)
        read = (
            request.env["announcement.read"]
            .sudo()
            .search(
                [
                    ("user_id", "=", request.env.user.id),
                    ("announcement_id", "in", live.ids),
                ]
            )
            .mapped("announcement_id")
        )
        return len(live - read)

    def _od19_my_schedule(self, days=7):
        """Merged upcoming timeline (bookings + approved leaves) for the strip."""
        env = request.env
        user = env.user
        now = fields.Datetime.now()
        until = datetime.datetime.now() + datetime.timedelta(days=days)
        items = []
        if "od19.meeting.room.booking" in env:
            bookings = (
                env["od19.meeting.room.booking"]
                .sudo()
                .search(
                    [
                        ("organizer_id", "=", user.id),
                        ("state", "in", ("booked", "in_use")),
                        ("start_datetime", ">=", now),
                        ("start_datetime", "<=", until),
                    ],
                    order="start_datetime asc",
                    limit=20,
                )
            )
            for booking in bookings:
                items.append(
                    {
                        "date": self._od19_local(booking.start_datetime, "%Y-%m-%d"),
                        "time": "%s–%s"
                        % (
                            self._od19_local(booking.start_datetime, "%H:%M"),
                            self._od19_local(booking.end_datetime, "%H:%M"),
                        ),
                        "kind": "booking",
                        "label": booking.name,
                        "detail": booking.room_id.name,
                        "url": "/web#action=od19_meeting_room_booking.action_meeting_room_booking&id=%s"
                        % booking.id,
                    }
                )
        if "hr.leave" in env and user.employee_id:
            leaves = (
                env["hr.leave"]
                .sudo()
                .search(
                    [
                        ("employee_id", "=", user.employee_id.id),
                        ("state", "=", "validate"),
                        ("date_to", ">=", now),
                        ("date_from", "<=", until),
                    ],
                    order="date_from asc",
                    limit=20,
                )
            )
            for leave in leaves:
                items.append(
                    {
                        "date": self._od19_local(leave.date_from, "%Y-%m-%d"),
                        "time": "%s–%s"
                        % (
                            self._od19_local(leave.date_from, "%d/%m"),
                            self._od19_local(leave.date_to, "%d/%m"),
                        ),
                        "kind": "leave",
                        "label": leave.name or leave.holiday_status_id.name,
                        "detail": leave.holiday_status_id.name,
                        "url": "/web#action=hr_holidays.hr_leave_action_my",
                    }
                )
        items.sort(key=lambda item: item["date"])
        return items[:10]
```

- [ ] **Step 5: ตรวจไวยากรณ์**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
venv19\Scripts\python.exe -m py_compile custom_addons\od19_website\controllers\main.py custom_addons\od19_website\tests\test_me_summary.py custom_addons\od19_website\tests\test_employee_experience.py
```
Expected: ไม่มี output

- [ ] **Step 6: รันเทสต์เพื่อยืนยันว่าผ่าน**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
.\run-tests.ps1 -Module od19_website
```
Expected: PASS — `test_me_summary_*` ผ่าน; สรุป 0 failed / 0 error(s)

- [ ] **Step 7: Commit**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
git add -- custom_addons/od19_website/controllers/main.py custom_addons/od19_website/tests/__init__.py custom_addons/od19_website/tests/test_me_summary.py custom_addons/od19_website/tests/test_employee_experience.py
git commit -m "feat(od19_website): add portal me-summary JSON endpoint with per-user cache"
```

---

### Task 2: Hero ตามช่วงเวลา + ตำแหน่ง/แผนก/อักษรย่อ

**Files:**
- Modify: `custom_addons/od19_website/controllers/main.py` (เพิ่ม helper `_od19_greeting`, `_od19_initials` + คีย์ใน render dict)
- Modify: `custom_addons/od19_website/views/employee_portal.xml` (บรรทัด 12–31 — บล็อก Hero)
- Modify: `custom_addons/od19_website/tests/test_employee_experience.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

แทนที่เนื้อหา `custom_addons/od19_website/tests/test_employee_experience.py` ด้วย:

```python
import datetime

from odoo import Command
from odoo.addons.od19_website.controllers.main import AutoInfoWebsite
from odoo.tests import HttpCase, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestGreetingHelper(TransactionCase):
    def test_greeting_buckets(self):
        controller = AutoInfoWebsite()
        self.assertEqual(controller._od19_greeting(9), "สวัสดีตอนเช้า")
        self.assertEqual(controller._od19_greeting(13), "สวัสดีตอนบ่าย")
        self.assertEqual(controller._od19_greeting(20), "สวัสดีตอนเย็น")

    def test_initials(self):
        controller = AutoInfoWebsite()
        self.assertEqual(controller._od19_initials("Somchai Jaidee"), "SJ")
        self.assertEqual(controller._od19_initials("Somchai"), "SO")
        self.assertEqual(controller._od19_initials(""), "?")


@tagged("post_install", "-at_install")
class TestPortalHeroHtml(HttpCase):
    def setUp(self):
        super().setUp()
        self.tester = self.env["res.users"].create(
            {
                "name": "Hero Tester",
                "login": "hero_tester",
                "password": "hero_tester",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )

    def test_portal_hero_uses_time_greeting(self):
        self.authenticate("hero_tester", "hero_tester")
        html = self.url_open("/employee-portal").text
        self.assertTrue(
            "สวัสดีตอนเช้า" in html
            or "สวัสดีตอนบ่าย" in html
            or "สวัสดีตอนเย็น" in html
        )
        self.assertIn('od19-avatar', html)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
.\run-tests.ps1 -Module od19_website
```
Expected: FAIL — `AttributeError: 'AutoInfoWebsite' object has no attribute '_od19_greeting'` และ HTML ไม่มี `od19-avatar`

- [ ] **Step 3: เพิ่ม helper ในคอนโทรลเลอร์**

ใน `custom_addons/od19_website/controllers/main.py` แทรก **ต่อจากเมธอด `_od19_my_schedule`**:

```python
    # ------------------------------------------------------------------
    # Employee portal — hero helpers
    # ------------------------------------------------------------------
    def _od19_greeting(self, hour=None):
        """Thai greeting keyed to the user's local time of day."""
        if hour is None:
            tz = pytz.timezone(request.env.user.tz or "UTC")
            hour = datetime.datetime.now(pytz.utc).astimezone(tz).hour
        if 5 <= hour < 12:
            return "สวัสดีตอนเช้า"
        if 12 <= hour < 17:
            return "สวัสดีตอนบ่าย"
        return "สวัสดีตอนเย็น"

    def _od19_initials(self, name):
        """Two-letter monogram used when the user has no picture."""
        parts = [part for part in (name or "").split() if part]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][:1] + parts[-1][:1]).upper()
```

- [ ] **Step 4: เพิ่มคีย์บริบทใน render dict ของ `employee_portal`**

ในเมธอด `employee_portal` แก้ dict ที่ส่งให้ `request.render` — แทรก 4 คีย์นี้ **ก่อนบรรทัด `"user": request.env.user,`**:

```python
                "greeting": self._od19_greeting(),
                "initials": self._od19_initials(request.env.user.name),
                "job_title": request.env.user.job_title or "",
                "department_name": request.env.user.employee_id.department_id.name
                or "",
```

- [ ] **Step 5: แทนบล็อก Hero ในเทมเพลต**

ใน `custom_addons/od19_website/views/employee_portal.xml` แทนที่ **บรรทัด 12–31** (คอมเมนต์ `<!-- Welcome Hero -->` ถึง `</section>`) ด้วย:

```xml
                <!-- [A] Welcome Hero — time-aware, personal -->
                <section class="od19-portal-hero">
                    <div class="container d-flex justify-content-between align-items-center flex-wrap gap-3">
                        <div class="d-flex align-items-center">
                            <div class="od19-avatar">
                                <t t-if="user.partner_id.avatar_128">
                                    <img t-att-src="image_data_uri(user.partner_id.avatar_128)" alt=""/>
                                </t>
                                <t t-else="">
                                    <span t-esc="initials"/>
                                </t>
                            </div>
                            <div class="ms-3">
                                <h2 class="mb-1">
                                    <span t-esc="greeting"/>, <span t-esc="user.name"/>
                                </h2>
                                <p class="mb-0" style="opacity:0.85;">
                                    <t t-if="job_title"><span t-esc="job_title"/></t>
                                    <t t-if="job_title and department_name"> · </t>
                                    <t t-if="department_name"><span t-esc="department_name"/></t>
                                    <t t-if="not job_title and not department_name">ยินดีต้อนรับสู่ Employee Portal ของ The Auto-Info</t>
                                </p>
                            </div>
                        </div>
                        <div class="text-end">
                            <small class="d-block mb-2" style="opacity:0.7;" t-esc="datetime.datetime.now().strftime('%A, %d %B %Y')"/>
                            <a href="/web" class="btn btn-sm od19-portal-back">
                                <i class="fa fa-th me-1"/>กลับหน้าหลังบ้าน
                            </a>
                        </div>
                    </div>
                </section>
```

- [ ] **Step 6: ตรวจ XML + รันเทสต์**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('custom_addons/od19_website/views/employee_portal.xml')"
venv19\Scripts\python.exe -m py_compile custom_addons\od19_website\controllers\main.py
.\run-tests.ps1 -Module od19_website
```
Expected: ไม่มี output จาก 2 คำสั่งแรก; `run-tests.ps1` 0 failed / 0 error(s)

- [ ] **Step 7: Commit**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
git add -- custom_addons/od19_website/controllers/main.py custom_addons/od19_website/views/employee_portal.xml custom_addons/od19_website/tests/test_employee_experience.py
git commit -m "feat(od19_website): time-aware portal hero with avatar, job title and department"
```

---

### Task 3: บล็อก [B] My Day Strip + [C] My Schedule + CSS + JS lazy fetch

**Files:**
- Modify: `custom_addons/od19_website/views/employee_portal.xml` (แทรกหลัง `<div class="container">`)
- Modify: `custom_addons/od19_website/static/src/css/od19_website.css` (ต่อท้าย)
- Create: `custom_addons/od19_website/static/src/js/od19_my_day.js`
- Modify: `custom_addons/od19_website/__manifest__.py`
- Modify: `custom_addons/od19_website/tests/test_employee_experience.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่มคลาสนี้ **ต่อท้าย** `custom_addons/od19_website/tests/test_employee_experience.py`:

```python
@tagged("post_install", "-at_install")
class TestPortalMyDayHtml(HttpCase):
    def setUp(self):
        super().setUp()
        self.tester = self.env["res.users"].create(
            {
                "name": "My Day Tester",
                "login": "my_day_tester",
                "password": "my_day_tester",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )

    def test_my_day_strip_present(self):
        self.authenticate("my_day_tester", "my_day_tester")
        html = self.url_open("/employee-portal").text
        self.assertIn('id="od19-my-day"', html)
        self.assertIn('data-od19-me-summary="/employee-portal/me-summary"', html)
        self.assertIn('data-od19-field="attendance"', html)
        self.assertIn('data-od19-field="approvals"', html)

    def test_my_schedule_and_anchor_present(self):
        self.authenticate("my_day_tester", "my_day_tester")
        html = self.url_open("/employee-portal").text
        self.assertIn('id="od19-my-schedule"', html)
        self.assertIn('id="od19-recognition-anchor"', html)

    def test_my_day_js_in_frontend_bundle(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_frontend")[0]
        urls = [asset["url"] for asset in assets]
        self.assertIn("/od19_website/static/src/js/od19_my_day.js", urls)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
.\run-tests.ps1 -Module od19_website
```
Expected: FAIL — ไม่พบ `id="od19-my-day"` และ JS ยังไม่อยู่ใน bundle

- [ ] **Step 3: แทรกบล็อก [B] + [C] + anchor ในเทมเพลต**

ใน `custom_addons/od19_website/views/employee_portal.xml` แทรก **ต่อจากบรรทัด `<div class="container">` (บรรทัด 33)**:

```xml
                    <!-- [B] My Day Strip (theme 1) — lazy, filled by od19_my_day.js -->
                    <div class="row g-3 mb-4" id="od19-my-day"
                         data-od19-me-summary="/employee-portal/me-summary">
                        <div class="col-6 col-lg-3">
                            <a class="od19-day-card" href="/web#action=hr_attendance.hr_attendance_action">
                                <div class="od19-day-icon"><i class="fa fa-clock-o"/></div>
                                <div class="od19-day-body">
                                    <div class="od19-day-value" data-od19-field="attendance">—</div>
                                    <div class="od19-day-label">ลงเวลาวันนี้</div>
                                </div>
                            </a>
                        </div>
                        <div class="col-6 col-lg-3">
                            <a class="od19-day-card" href="/my/approvals">
                                <div class="od19-day-icon"><i class="fa fa-check-square-o"/></div>
                                <div class="od19-day-body">
                                    <div class="od19-day-value" data-od19-field="approvals">—</div>
                                    <div class="od19-day-label">รออนุมัติ</div>
                                </div>
                            </a>
                        </div>
                        <div class="col-6 col-lg-3">
                            <a class="od19-day-card" href="/web#action=od19_meeting_room_booking.action_meeting_room_booking">
                                <div class="od19-day-icon"><i class="fa fa-calendar-check-o"/></div>
                                <div class="od19-day-body">
                                    <div class="od19-day-value" data-od19-field="next_booking">—</div>
                                    <div class="od19-day-label">นัดถัดไป</div>
                                </div>
                            </a>
                        </div>
                        <div class="col-6 col-lg-3">
                            <a class="od19-day-card" href="/web#action=hr_holidays.hr_leave_action_my">
                                <div class="od19-day-icon"><i class="fa fa-plane"/></div>
                                <div class="od19-day-body">
                                    <div class="od19-day-value" data-od19-field="leave">—</div>
                                    <div class="od19-day-label">วันลาคงเหลือ</div>
                                </div>
                            </a>
                        </div>
                    </div>

                    <!-- [C] My Schedule + frequent shortcuts (theme 3) -->
                    <div class="row g-3 mb-4">
                        <div class="col-lg-8">
                            <div class="od19-panel">
                                <h5 class="od19-panel-title">
                                    <i class="fa fa-calendar-o me-2" style="color:var(--od19-primary);"/>
                                    ตารางของฉัน (My Schedule)
                                </h5>
                                <div id="od19-my-schedule" data-od19-schedule>
                                    <p class="text-muted small mb-0">
                                        <i class="fa fa-spinner fa-spin me-1"/>กำลังโหลดตาราง…
                                    </p>
                                </div>
                            </div>
                        </div>
                        <div class="col-lg-4">
                            <div class="od19-panel">
                                <h5 class="od19-panel-title">
                                    <i class="fa fa-bolt me-2" style="color:var(--od19-secondary);"/>
                                    ใช้บ่อย (Shortcuts)
                                </h5>
                                <div class="od19-shortcut-grid">
                                    <a class="od19-shortcut" href="/web#action=hr_attendance.hr_attendance_action">
                                        <i class="fa fa-clock-o"/><span>ลงเวลา</span>
                                    </a>
                                    <a class="od19-shortcut" href="/my/approvals">
                                        <i class="fa fa-check-square-o"/><span>อนุมัติ</span>
                                    </a>
                                    <a class="od19-shortcut" href="/web#action=hr_expense.hr_expense_actions_my_all">
                                        <i class="fa fa-money"/><span>ค่าใช้จ่าย</span>
                                    </a>
                                    <a class="od19-shortcut" href="/web#action=od19_meeting_room_booking.action_meeting_room_booking">
                                        <i class="fa fa-calendar-check-o"/><span>จองห้อง</span>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Anchor: od19_recognition injects the Team Wall here (additive) -->
                    <div id="od19-recognition-anchor"/>
```

- [ ] **Step 4: สร้าง JS lazy fetch**

สร้างไฟล์ `custom_addons/od19_website/static/src/js/od19_my_day.js`:

```javascript
/* Employee portal — "My Day" strip + schedule (lazy JSON, no framework). */
(function () {
    'use strict';

    function escapeHtml(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function setText(root, field, value) {
        if (value === null || value === undefined || value === '') return;
        var node = root.querySelector('[data-od19-field="' + field + '"]');
        if (node) node.textContent = value;
    }

    function renderSchedule(root, items) {
        var container = root.querySelector('[data-od19-schedule]');
        if (!container) return;
        if (!items || !items.length) {
            container.innerHTML = '<p class="text-muted small mb-0">ไม่มีรายการในสัปดาห์นี้</p>';
            return;
        }
        var html = '';
        items.forEach(function (item) {
            html += '<div class="od19-schedule-item od19-schedule-' + escapeHtml(item.kind) + '">' +
                '<div class="od19-schedule-time">' + escapeHtml(item.time) + '</div>' +
                '<div class="od19-schedule-main">' +
                '<span class="od19-schedule-label">' + escapeHtml(item.label) + '</span>' +
                (item.detail ? '<span class="od19-schedule-detail"> · ' + escapeHtml(item.detail) + '</span>' : '') +
                '</div></div>';
        });
        container.innerHTML = html;
    }

    function render(root, data) {
        if (!data) return;
        var attendance = data.attendance || {};
        if (attendance.available) {
            setText(root, 'attendance',
                'เข้า ' + (attendance.check_in || '—') + ' · ออก ' + (attendance.check_out || '—'));
        }
        if (data.approvals) {
            setText(root, 'approvals', String(data.approvals.pending_count || 0) + ' รายการ');
        }
        if (data.next_booking) {
            setText(root, 'next_booking', data.next_booking.start + ' · ' + data.next_booking.room);
        }
        if (data.leave && data.leave.available) {
            setText(root, 'leave', 'เหลือ ' + data.leave.remaining_display + ' วัน');
        }
        renderSchedule(root, data.schedule);
    }

    function load() {
        var root = document.getElementById('od19-my-day');
        if (!root || root.dataset.loaded) return;
        root.dataset.loaded = '1';
        fetch(root.dataset.od19MeSummary, {
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
        })
            .then(function (response) {
                if (!response.ok) throw new Error('HTTP ' + response.status);
                return response.json();
            })
            .then(function (data) { render(root, data); })
            .catch(function () { /* keep the placeholders as-is */ });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', load);
    } else {
        load();
    }
})();
```

- [ ] **Step 5: ต่อ CSS**

ต่อท้ายไฟล์ `custom_addons/od19_website/static/src/css/od19_website.css`:

```css
/* ---------- Employee Portal — My Day / Schedule / Shortcuts ---------- */
.od19-avatar {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    overflow: hidden;
    background: rgba(255, 255, 255, 0.15);
    border: 2px solid rgba(255, 255, 255, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    font-weight: 700;
    flex: 0 0 auto;
}
.od19-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
.od19-day-card {
    display: flex;
    align-items: center;
    gap: 12px;
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
    padding: 16px;
    height: 100%;
    text-decoration: none;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.od19-day-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 18px rgba(158, 36, 36, 0.15);
}
.od19-day-icon {
    width: 44px;
    height: 44px;
    border-radius: 10px;
    background: var(--od19-primary);
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    flex: 0 0 auto;
}
.od19-day-value {
    font-weight: 700;
    color: var(--od19-dark);
    font-size: 1.05rem;
    line-height: 1.2;
}
.od19-day-label {
    color: var(--od19-gray);
    font-size: 0.82rem;
}
.od19-panel {
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
    padding: 20px;
    height: 100%;
}
.od19-panel-title {
    font-weight: 700;
    color: var(--od19-dark);
    margin-bottom: 16px;
    font-size: 1.05rem;
}
.od19-schedule-item {
    display: flex;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid #f1f1f1;
}
.od19-schedule-item:last-child {
    border-bottom: none;
}
.od19-schedule-time {
    font-weight: 600;
    color: var(--od19-primary);
    min-width: 92px;
    font-size: 0.85rem;
}
.od19-schedule-main {
    font-size: 0.9rem;
    color: var(--od19-dark);
}
.od19-schedule-detail {
    color: var(--od19-gray);
}
.od19-schedule-leave .od19-schedule-time {
    color: var(--od19-secondary);
}
.od19-shortcut-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
}
.od19-shortcut {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 16px 8px;
    border-radius: 10px;
    background: var(--od19-light);
    color: var(--od19-dark);
    text-decoration: none;
    font-size: 0.85rem;
    font-weight: 600;
    transition: background 0.2s ease, color 0.2s ease;
}
.od19-shortcut:hover {
    background: var(--od19-primary);
    color: #fff;
}
.od19-shortcut i {
    font-size: 1.3rem;
}
@media (max-width: 767.98px) {
    .od19-schedule-time {
        min-width: 74px;
    }
    .od19-avatar {
        width: 52px;
        height: 52px;
        font-size: 1.2rem;
    }
}
```

- [ ] **Step 6: เพิ่ม asset + bump version ใน manifest**

แก้ `custom_addons/od19_website/__manifest__.py`:
- เปลี่ยน `"version": "19.0.1.0.0",` → `"version": "19.0.1.1.0",`
- ใน `web.assets_frontend` **ต่อจากบรรทัด `"od19_website/static/src/js/od19_approval_badge.js",`** เพิ่ม:
```python
            "od19_website/static/src/js/od19_my_day.js",
```

- [ ] **Step 7: ตรวจ XML/CSS/JS + รันเทสต์**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('custom_addons/od19_website/views/employee_portal.xml')"
venv19\Scripts\python.exe -c "import json; json.load(open('custom_addons/od19_website/__manifest__.py')) if False else None"
venv19\Scripts\python.exe -m py_compile custom_addons/od19_website/__manifest__.py
.\run-tests.ps1 -Module od19_website
```
Expected: ไม่มี output จากคำสั่งแรกและที่สาม; `run-tests.ps1` 0 failed / 0 error(s)

- [ ] **Step 8: Commit**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
git add -- custom_addons/od19_website/views/employee_portal.xml custom_addons/od19_website/static/src/css/od19_website.css custom_addons/od19_website/static/src/js/od19_my_day.js custom_addons/od19_website/__manifest__.py custom_addons/od19_website/tests/test_employee_experience.py
git commit -m "feat(od19_website): add My Day strip and My Schedule blocks with lazy loader"
```

---

### Task 4: จัดกลุ่ม Quick Access ([G]) เป็น 3 กลุ่มตามหน้าที่

**Files:**
- Modify: `custom_addons/od19_website/views/employee_portal.xml` (บรรทัด Quick Access — `<!-- Quick Access -->` ถึง `</div>` ที่ปิด row)
- Modify: `custom_addons/od19_website/tests/test_employee_experience.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่มคลาสนี้ **ต่อท้าย** `custom_addons/od19_website/tests/test_employee_experience.py`:

```python
@tagged("post_install", "-at_install")
class TestPortalQuickAccessGroups(HttpCase):
    def setUp(self):
        super().setUp()
        self.tester = self.env["res.users"].create(
            {
                "name": "QA Tester",
                "login": "qa_tester",
                "password": "qa_tester",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )

    def test_quick_access_grouped_and_keeps_cards(self):
        self.authenticate("qa_tester", "qa_tester")
        html = self.url_open("/employee-portal").text
        self.assertEqual(html.count("od19-portal-group-title"), 3)
        self.assertGreaterEqual(html.count("od19-portal-card"), 11)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
.\run-tests.ps1 -Module od19_website
```
Expected: FAIL — `od19-portal-group-title` count = 0

- [ ] **Step 3: แทนบล็อก Quick Access ด้วย 3 กลุ่ม**

ใน `custom_addons/od19_website/views/employee_portal.xml` แทนที่บล็อก **`<!-- Quick Access -->`** ทั้งบล็อก (แถวที่มี `<h5>` "เมนูด่วน (Quick Access)" จนถึง `</div>` ที่ปิด row — เดิมยาวต่อเนื่องถึงก่อน `<!-- Quick Actions -->`) ด้วย:

```xml
                    <!-- [G] Quick Access — grouped by function (theme 3) -->
                    <div class="row mb-4">
                        <div class="col-12">
                            <h5 style="color:var(--od19-dark);font-weight:700;margin-bottom:20px;">
                                <i class="fa fa-th-large me-2" style="color:var(--od19-primary);"/>
                                เมนูด่วน (Quick Access)
                            </h5>
                        </div>

                        <div class="col-12">
                            <div class="od19-portal-group-title">งานของฉัน (My Work)</div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-check-square-o"/></div>
                                <h5>รายการอนุมัติ</h5>
                                <p>Approval Center</p>
                                <a href="/my/approvals">เปิดใช้งาน →</a>
                            </div>
                            <div class="od19-approval-badge d-none" data-od19-approval-summary="/my/approvals/summary">
                                <small class="text-danger d-block mt-1">
                                    <i class="fa fa-clock-o me-1"/>
                                    รออนุมัติ <span class="od19-approval-count">0</span> รายการ
                                    <span class="od19-approval-age d-none">
                                        (เก่าสุด <span class="od19-approval-max-age">0</span> วัน)
                                    </span>
                                </small>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-money"/></div>
                                <h5>ค่าใช้จ่าย</h5>
                                <p>HR Expense</p>
                                <a href="/web#action=hr_expense.hr_expense_actions_my_all">เปิดใช้งาน →</a>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-truck"/></div>
                                <h5>จัดซื้อ</h5>
                                <p>Purchase Requisition</p>
                                <a href="/web#action=purchase.purchase_form_action">เปิดใช้งาน →</a>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-calendar-check-o"/></div>
                                <h5>จองห้องประชุม</h5>
                                <p>Meeting Room Booking</p>
                                <a href="/web#action=od19_meeting_room_booking.action_meeting_room_booking">เปิดใช้งาน →</a>
                            </div>
                        </div>

                        <div class="col-12">
                            <div class="od19-portal-group-title">HR &amp; สวัสดิการ (HR &amp; Welfare)</div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-users"/></div>
                                <h5>ฝ่ายบุคคล</h5>
                                <p>Employee Directory</p>
                                <a href="/web#action=hr.open_view_employee_list_my">เปิดใช้งาน →</a>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-archive"/></div>
                                <h5>ยืมอุปกรณ์</h5>
                                <p>Asset &amp; Tool Loan</p>
                                <a href="/web#action=od19_asset_loan.asset_loan_action">เปิดใช้งาน →</a>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-bullhorn"/></div>
                                <h5>ประกาศ</h5>
                                <p>Announcements</p>
                                <a href="/web#action=od19_announcement.announcement_action">เปิดใช้งาน →</a>
                            </div>
                        </div>

                        <div class="col-12">
                            <div class="od19-portal-group-title">ความรู้ &amp; แจ้งปัญหา (Knowledge &amp; Support)</div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-book"/></div>
                                <h5>ฐานความรู้</h5>
                                <p>Knowledge Base</p>
                                <a href="/web#action=document_page.action_browse_all_content">เปิดใช้งาน →</a>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-ticket"/></div>
                                <h5>แจ้งปัญหาภายใน</h5>
                                <p>Internal Issue / Helpdesk</p>
                                <a href="/web#action=helpdesk_mgmt.helpdesk_ticket_action">เปิดใช้งาน →</a>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-bar-chart"/></div>
                                <h5>แดชบอร์ด</h5>
                                <p>My Dashboard</p>
                                <a href="/web">เปิดใช้งาน →</a>
                            </div>
                        </div>
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-book"/></div>
                                <h5>คู่มือการใช้งาน</h5>
                                <p>User Guide</p>
                                <a href="/web#action=web_tour.tour_action">เปิดใช้งาน →</a>
                            </div>
                        </div>
                    </div>
```

- [ ] **Step 4: เพิ่ม CSS ของหัวกลุ่ม**

ต่อท้ายไฟล์ `custom_addons/od19_website/static/src/css/od19_website.css`:

```css
.od19-portal-group-title {
    font-weight: 700;
    color: var(--od19-primary);
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-left: 4px solid var(--od19-secondary);
    padding-left: 10px;
    margin: 6px 0 14px;
}
```

- [ ] **Step 5: ตรวจ XML + รันเทสต์**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('custom_addons/od19_website/views/employee_portal.xml')"
.\run-tests.ps1 -Module od19_website
```
Expected: ไม่มี output; 0 failed / 0 error(s)

- [ ] **Step 6: Commit**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
git add -- custom_addons/od19_website/views/employee_portal.xml custom_addons/od19_website/static/src/css/od19_website.css custom_addons/od19_website/tests/test_employee_experience.py
git commit -m "feat(od19_website): group portal quick access into three functional clusters"
```

---

### Task 5: สร้างโมดูล `od19_recognition` — scaffold + models + security

**Files:**
- Create: `custom_addons/od19_recognition/__manifest__.py`, `__init__.py`
- Create: `custom_addons/od19_recognition/models/__init__.py`, `models/od19_recognition.py`, `models/od19_recognition_badge.py`
- Create: `custom_addons/od19_recognition/security/od19_recognition_security.xml`, `security/ir.model.access.csv`
- Create: `custom_addons/od19_recognition/data/od19_recognition_badge_data.xml`
- Create: `custom_addons/od19_recognition/tests/__init__.py`, `tests/test_recognition.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้าง `custom_addons/od19_recognition/tests/__init__.py`:

```python
from . import test_recognition
```

สร้าง `custom_addons/od19_recognition/tests/test_recognition.py`:

```python
from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRecognitionRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.badge = cls.env["od19.recognition.badge"].create({"name": "Thank You"})
        cls.user_a = cls.env["res.users"].create(
            {
                "name": "Kudos A",
                "login": "kudos_a",
                "group_ids": [
                    Command.link(cls.env.ref("base.group_user").id),
                    Command.link(
                        cls.env.ref("od19_recognition.group_recognition_user").id
                    ),
                ],
            }
        )
        cls.user_b = cls.env["res.users"].create(
            {
                "name": "Kudos B",
                "login": "kudos_b",
                "group_ids": [
                    Command.link(cls.env.ref("base.group_user").id),
                    Command.link(
                        cls.env.ref("od19_recognition.group_recognition_user").id
                    ),
                ],
            }
        )
        cls.emp_a = cls.env["hr.employee"].create(
            {"name": "Kudos A", "user_id": cls.user_a.id}
        )
        cls.emp_b = cls.env["hr.employee"].create(
            {"name": "Kudos B", "user_id": cls.user_b.id}
        )

    def test_create_forces_company(self):
        rec = (
            self.env["od19.recognition"]
            .with_user(self.user_a)
            .create(
                {
                    "author_id": self.emp_a.id,
                    "recipient_id": self.emp_b.id,
                    "badge_id": self.badge.id,
                    "message": "Great job!",
                }
            )
        )
        self.assertEqual(rec.company_id, self.user_a.company_id)

    def test_cannot_kudos_self(self):
        with self.assertRaises(ValidationError):
            self.env["od19.recognition"].create(
                {
                    "author_id": self.emp_a.id,
                    "recipient_id": self.emp_a.id,
                    "message": "Me",
                }
            )

    def test_message_length_limit(self):
        with self.assertRaises(ValidationError):
            self.env["od19.recognition"].create(
                {
                    "author_id": self.emp_a.id,
                    "recipient_id": self.emp_b.id,
                    "message": "x" * 501,
                }
            )

    def test_only_author_can_edit(self):
        rec = self.env["od19.recognition"].create(
            {
                "author_id": self.emp_a.id,
                "recipient_id": self.emp_b.id,
                "message": "Thanks",
            }
        )
        with self.assertRaises(AccessError):
            rec.with_user(self.user_b).write({"message": "hacked"})

    def test_private_kudos_hidden_from_others(self):
        private = self.env["od19.recognition"].create(
            {
                "author_id": self.emp_a.id,
                "recipient_id": self.emp_b.id,
                "message": "private note",
                "is_public": False,
            }
        )
        visible = (
            self.env["od19.recognition"].with_user(self.user_b).search([]).ids
        )
        self.assertNotIn(private.id, visible)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
$env:PYTHONDONTWRITEBYTECODE='1'
venv19\Scripts\python.exe odoo-bin -c odoo.conf -i od19_recognition --stop-after-init --logfile data_test_install.log
```
Expected: FAIL — ยังไม่มีโฟลเดอร์ `custom_addons/od19_recognition` → `ModuleNotFoundError` / module not found

- [ ] **Step 3: สร้าง manifest + `__init__.py`**

สร้าง `custom_addons/od19_recognition/__manifest__.py`:

```python
{
    "name": "Auto-Info Recognition & Belonging",
    "summary": "Kudos wall, birthdays and work anniversaries for the employee portal",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "The Auto-Info Co., Ltd.",
    "website": "https://www.auto-info.co.th",
    "license": "LGPL-3",
    "depends": [
        "od19_website",
        "hr",
        "mail",
        "portal",
    ],
    "data": [
        "security/od19_recognition_security.xml",
        "security/ir.model.access.csv",
        "data/od19_recognition_badge_data.xml",
        "views/od19_recognition_views.xml",
        "views/portal_templates.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "od19_recognition/static/src/css/od19_recognition.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
```

สร้าง `custom_addons/od19_recognition/__init__.py`:

```python
from . import models
from . import controllers
```

- [ ] **Step 4: สร้างโมเดล**

สร้าง `custom_addons/od19_recognition/models/__init__.py`:

```python
from . import od19_recognition_badge
from . import od19_recognition
```

สร้าง `custom_addons/od19_recognition/models/od19_recognition_badge.py`:

```python
from odoo import fields, models


class Od19RecognitionBadge(models.Model):
    _name = "od19.recognition.badge"
    _description = "Recognition Badge"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    icon = fields.Char(
        default="fa-star", help="Font Awesome class, e.g. fa-handshake-o"
    )
    color = fields.Char(default="#9E2424")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
```

สร้าง `custom_addons/od19_recognition/models/od19_recognition.py`:

```python
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

MESSAGE_MAX_LENGTH = 500


class Od19Recognition(models.Model):
    _name = "od19.recognition"
    _description = "Employee Recognition (Kudos)"
    _order = "published_date desc, id desc"
    _inherit = ["mail.thread"]

    author_id = fields.Many2one(
        "hr.employee",
        string="From",
        required=True,
        default=lambda self: self.env.user.employee_id,
        ondelete="cascade",
    )
    recipient_id = fields.Many2one(
        "hr.employee", string="To", required=True, ondelete="cascade"
    )
    badge_id = fields.Many2one("od19.recognition.badge", string="Badge")
    message = fields.Text(string="Message", required=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    published_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    is_public = fields.Boolean(default=True)

    @api.constrains("author_id", "recipient_id")
    def _check_not_self(self):
        for record in self:
            if record.author_id and record.author_id == record.recipient_id:
                raise ValidationError(_("You cannot give a Kudos to yourself."))

    @api.constrains("message")
    def _check_message_length(self):
        for record in self:
            if record.message and len(record.message) > MESSAGE_MAX_LENGTH:
                raise ValidationError(
                    _("Kudos message must be %s characters or fewer.")
                    % MESSAGE_MAX_LENGTH
                )
```

- [ ] **Step 5: สร้าง security**

สร้าง `custom_addons/od19_recognition/security/od19_recognition_security.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="res_groups_privilege_recognition" model="res.groups.privilege">
        <field name="name">Recognition</field>
        <field name="category_id" ref="base.module_category_human_resources"/>
        <field name="sequence">42</field>
    </record>

    <record id="group_recognition_user" model="res.groups">
        <field name="name">Recognition User</field>
        <field name="comment">Give Kudos and view the recognition wall.</field>
        <field name="privilege_id" ref="res_groups_privilege_recognition"/>
        <field name="implied_ids" eval="[Command.link(ref('base.group_user'))]"/>
    </record>

    <record id="group_recognition_manager" model="res.groups">
        <field name="name">Recognition Manager</field>
        <field name="comment">Moderate all Kudos and maintain the badge catalog.</field>
        <field name="privilege_id" ref="res_groups_privilege_recognition"/>
        <field name="implied_ids" eval="[Command.link(ref('group_recognition_user'))]"/>
    </record>

    <record id="base.group_system" model="res.groups">
        <field name="implied_ids" eval="[Command.link(ref('group_recognition_manager'))]"/>
    </record>

    <!-- Read: public Kudos, or anything I am part of, within my companies -->
    <record id="recognition_rule_read" model="ir.rule">
        <field name="name">Recognition: read public or mine</field>
        <field name="model_id" ref="model_od19_recognition"/>
        <field name="domain_force">[('company_id', 'in', company_ids), '|', '|', ('is_public', '=', True), ('author_id.user_id', '=', user.id), ('recipient_id.user_id', '=', user.id)]</field>
        <field name="groups" eval="[Command.link(ref('group_recognition_user'))]"/>
    </record>

    <!-- Write/unlink: only the author keeps control of their own Kudos -->
    <record id="recognition_rule_owner_write" model="ir.rule">
        <field name="name">Recognition: only author can edit</field>
        <field name="model_id" ref="model_od19_recognition"/>
        <field name="domain_force">[('author_id.user_id', '=', user.id)]</field>
        <field name="groups" eval="[Command.link(ref('group_recognition_user'))]"/>
        <field name="perm_read" eval="False"/>
        <field name="perm_create" eval="False"/>
        <field name="perm_write" eval="True"/>
        <field name="perm_unlink" eval="True"/>
    </record>

    <!-- Managers can moderate everything -->
    <record id="recognition_rule_manager" model="ir.rule">
        <field name="name">Recognition: managers can moderate all</field>
        <field name="model_id" ref="model_od19_recognition"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[Command.link(ref('group_recognition_manager'))]"/>
    </record>

    <record id="recognition_badge_rule_manager" model="ir.rule">
        <field name="name">Recognition badge: managers can maintain</field>
        <field name="model_id" ref="model_od19_recognition_badge"/>
        <field name="domain_force">[(1, '=', 1)]</field>
        <field name="groups" eval="[Command.link(ref('group_recognition_manager'))]"/>
    </record>
</odoo>
```

สร้าง `custom_addons/od19_recognition/security/ir.model.access.csv`:

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_od19_recognition_user,od19.recognition.user,model_od19_recognition,od19_recognition.group_recognition_user,1,1,1,0
access_od19_recognition_manager,od19.recognition.manager,model_od19_recognition,od19_recognition.group_recognition_manager,1,1,1,1
access_od19_recognition_badge_user,od19.recognition.badge.user,model_od19_recognition_badge,od19_recognition.group_recognition_user,1,0,0,0
access_od19_recognition_badge_manager,od19.recognition.badge.manager,model_od19_recognition_badge,od19_recognition.group_recognition_manager,1,1,1,1
```

- [ ] **Step 6: สร้างข้อมูลป้ายเริ่มต้น**

สร้าง `custom_addons/od19_recognition/data/od19_recognition_badge_data.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="badge_thank_you" model="od19.recognition.badge">
        <field name="name">ขอบคุณ (Thank You)</field>
        <field name="icon">fa-heart</field>
        <field name="color">#9E2424</field>
        <field name="sequence">10</field>
    </record>
    <record id="badge_teamwork" model="od19.recognition.badge">
        <field name="name">ทำงานเป็นทีม (Great Teamwork)</field>
        <field name="icon">fa-handshake-o</field>
        <field name="color">#f39200</field>
        <field name="sequence">20</field>
    </record>
    <record id="badge_above_beyond" model="od19.recognition.badge">
        <field name="name">เกินความคาดหวัง (Above &amp; Beyond)</field>
        <field name="icon">fa-star</field>
        <field name="color">#7A1B1B</field>
        <field name="sequence">30</field>
    </record>
    <record id="badge_birthday" model="od19.recognition.badge">
        <field name="name">สุขสันต์วันเกิด (Happy Birthday)</field>
        <field name="icon">fa-birthday-cake</field>
        <field name="color">#e91e63</field>
        <field name="sequence">40</field>
    </record>
    <record id="badge_anniversary" model="od19.recognition.badge">
        <field name="name">ครบรอบการทำงาน (Happy Anniversary)</field>
        <field name="icon">fa-trophy</field>
        <field name="color">#6b1515</field>
        <field name="sequence">50</field>
    </record>
</odoo>
```

- [ ] **Step 7: ติดตั้งโมดูลลง DB ทดสอบ แล้วรันเทสต์**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
$env:PYTHONDONTWRITEBYTECODE='1'
venv19\Scripts\python.exe odoo-bin -c odoo.conf -i od19_recognition --stop-after-init --logfile data_test_install.log
.\run-tests.ps1 -Module od19_recognition
```
Expected: ติดตั้งสำเร็จ; `run-tests.ps1` PASS 0 failed / 0 error(s)

- [ ] **Step 8: Commit**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
git add -- custom_addons/od19_recognition/__manifest__.py custom_addons/od19_recognition/__init__.py custom_addons/od19_recognition/models custom_addons/od19_recognition/security custom_addons/od19_recognition/data custom_addons/od19_recognition/tests
git commit -m "feat(od19_recognition): add Kudos models, security groups and badge data"
```

---

### Task 6: คอนโทรลเลอร์ของ `od19_recognition` (feed / give / summary)

**Files:**
- Create: `custom_addons/od19_recognition/controllers/__init__.py`, `controllers/portal.py`
- Modify: `custom_addons/od19_recognition/tests/test_recognition.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่มคลาสนี้ **ต่อท้าย** `custom_addons/od19_recognition/tests/test_recognition.py` (ต้องเพิ่ม `from odoo.tests import HttpCase` — รวม import ด้านบนให้เป็น `from odoo.tests import HttpCase, TransactionCase, tagged`):

```python
@tagged("post_install", "-at_install")
class TestRecognitionPortal(HttpCase):
    def setUp(self):
        super().setUp()
        self.giver = self.env["res.users"].create(
            {
                "name": "Feed Giver",
                "login": "feed_giver",
                "password": "feed_giver",
                "group_ids": [
                    Command.link(self.env.ref("base.group_user").id),
                    Command.link(
                        self.env.ref("od19_recognition.group_recognition_user").id
                    ),
                ],
            }
        )
        self.receiver = self.env["res.users"].create(
            {
                "name": "Feed Receiver",
                "login": "feed_receiver",
                "password": "feed_receiver",
                "group_ids": [
                    Command.link(self.env.ref("base.group_user").id),
                    Command.link(
                        self.env.ref("od19_recognition.group_recognition_user").id
                    ),
                ],
            }
        )
        self.emp_giver = self.env["hr.employee"].create(
            {"name": "Feed Giver", "user_id": self.giver.id}
        )
        self.emp_receiver = self.env["hr.employee"].create(
            {"name": "Feed Receiver", "user_id": self.receiver.id}
        )

    def test_summary_route_returns_json(self):
        self.authenticate("feed_giver", "feed_giver")
        response = self.url_open("/my/recognition/summary")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("feed", payload)
        self.assertIn("celebrations", payload)

    def test_give_route_creates_kudos_and_forces_author(self):
        self.authenticate("feed_giver", "feed_giver")
        self.url_open(
            "/my/recognition/give",
            data={
                "recipient_id": self.emp_receiver.id,
                "message": "Great work today",
            },
        )
        created = self.env["od19.recognition"].search(
            [("recipient_id", "=", self.emp_receiver.id)], limit=1
        )
        self.assertTrue(created)
        self.assertEqual(created.author_id, self.emp_giver)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
.\run-tests.ps1 -Module od19_recognition
```
Expected: FAIL — `/my/recognition/summary` คืน 404

- [ ] **Step 3: สร้างคอนโทรลเลอร์**

สร้าง `custom_addons/od19_recognition/controllers/__init__.py`:

```python
from . import portal
```

สร้าง `custom_addons/od19_recognition/controllers/portal.py`:

```python
import datetime
import time
from urllib.parse import quote as url_quote

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.http import request

# Per-user cache for the short recognition summary on the portal home page.
RECOGNITION_SUMMARY_CACHE = {}
RECOGNITION_SUMMARY_TTL = 60


class Od19RecognitionPortal(http.Controller):

    # ------------------------------------------------------------------
    # Full page
    # ------------------------------------------------------------------
    @http.route(
        ["/my/recognition"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my_recognition(self, given=None, error=None, **kwargs):
        return request.render(
            "od19_recognition.portal_recognition_page",
            self._od19_recognition_page_data(given=given, error=error),
        )

    # ------------------------------------------------------------------
    # Give Kudos (POST + CSRF)
    # ------------------------------------------------------------------
    @http.route(
        ["/my/recognition/give"],
        type="http",
        auth="user",
        website=True,
        methods=["POST"],
        sitemap=False,
        csrf=True,
    )
    def my_recognition_give(self, recipient_id=None, badge_id=None, message=None, **kwargs):
        error = None
        try:
            self._od19_create_kudos(recipient_id, badge_id, message)
        except (ValidationError, ValueError) as exc:
            error = str(exc)
        if error:
            return request.redirect("/my/recognition?error=%s" % url_quote(error))
        return request.redirect("/my/recognition?given=1")

    def _od19_create_kudos(self, recipient_id, badge_id, message):
        employee = request.env.user.employee_id
        recipient = int(recipient_id) if recipient_id else False
        badge = int(badge_id) if badge_id else False
        text = (message or "").strip()
        if not employee or not recipient:
            raise ValueError("Recipient is required.")
        if not text:
            raise ValueError("Message is required.")
        request.env["od19.recognition"].sudo().create(
            {
                "author_id": employee.id,
                "recipient_id": recipient,
                "badge_id": badge,
                "message": text,
                "company_id": request.env.company.id,
                "is_public": True,
            }
        )

    # ------------------------------------------------------------------
    # JSON summary for the portal home block
    # ------------------------------------------------------------------
    @http.route(
        ["/my/recognition/summary"],
        type="http",
        auth="user",
        website=True,
        sitemap=False,
    )
    def my_recognition_summary(self, **kwargs):
        user_id = request.env.user.id
        mono = time.monotonic()
        cached = RECOGNITION_SUMMARY_CACHE.get(user_id)
        if cached and mono - cached[0] < RECOGNITION_SUMMARY_TTL:
            return request.make_json_response(cached[1])
        payload = self._od19_summary_data()
        RECOGNITION_SUMMARY_CACHE[user_id] = (mono, payload)
        return request.make_json_response(payload)

    def _od19_summary_data(self):
        feed = self._od19_feed(limit=5)
        return {"feed": feed, "celebrations": self._od19_celebrations()}

    def _od19_page_data(self, given=None, error=None):
        return {
            "given": given,
            "error": error,
            "feed": self._od19_feed(limit=30),
            "celebrations": self._od19_celebrations(),
            "employees": request.env["hr.employee"]
            .sudo()
            .search([("user_id", "!=", False)], order="name"),
            "badges": request.env["od19.recognition.badge"].sudo().search([]),
            "datetime": datetime,
        }

    def _od19_feed(self, limit=5):
        records = (
            request.env["od19.recognition"]
            .sudo()
            .search([("is_public", "=", True)], order="published_date desc, id desc", limit=limit)
        )
        return [
            {
                "id": record.id,
                "author": record.author_id.name or "",
                "recipient": record.recipient_id.name or "",
                "message": record.message or "",
                "badge": record.badge_id.name or "",
                "badge_icon": record.badge_id.icon or "fa-star",
                "badge_color": record.badge_id.color or "#9E2424",
                "date": record.published_date
                and fields.Datetime.context_timestamp(
                    request.env.user, record.published_date
                ).strftime("%d/%m/%Y")
                or "",
            }
            for record in records
        ]

    def _od19_celebrations(self):
        """Birthdays (only if shared) and work anniversaries for this month."""
        today = fields.Date.context_today(request.env.user)
        brothers = request.env["hr.employee"].sudo().search(
            [("user_id", "!=", False), ("company_id", "in", request.env.companies.ids)]
        )
        birthdays = []
        anniversaries = []
        for employee in brothers:
            public_date = employee.birthday_public_display_string
            if (
                employee.birthday
                and public_date
                and public_date != "hidden"
                and employee.birthday.month == today.month
            ):
                birthdays.append(
                    {
                        "employee_id": employee.id,
                        "name": employee.name,
                        "day": employee.birthday.day,
                    }
                )
            start = employee.contract_date_start or employee.date_start
            if start and start.month == today.month and start.year < today.year:
                anniversaries.append(
                    {
                        "employee_id": employee.id,
                        "name": employee.name,
                        "day": start.day,
                        "years": today.year - start.year,
                    }
                )
        return {"birthdays": birthdays, "anniversaries": anniversaries}
```

- [ ] **Step 4: สร้าง CSS ของโมดูล (กัน asset หาไม่เจอ)**

สร้างโฟลเดอร์และไฟล์ `custom_addons/od19_recognition/static/src/css/od19_recognition.css` (เนื้อหาเต็มจะเติมใน Task 7):

```css
/* ---------- Recognition wall (loaded on the employee portal) ---------- */
.od19-recognition-panel {
    background: #fff;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.06);
    padding: 20px;
    margin-bottom: 24px;
}
.od19-recognition-panel h5 {
    font-weight: 700;
    color: var(--od19-dark);
}
```

- [ ] **Step 5: ติดตั้ง/อัปเดต แล้วรันเทสต์**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
$env:PYTHONDONTWRITEBYTECODE='1'
venv19\Scripts\python.exe odoo-bin -c odoo.conf -u od19_recognition --stop-after-init --logfile data_test_install.log
venv19\Scripts\python.exe -m py_compile custom_addons\od19_recognition\controllers\portal.py
.\run-tests.ps1 -Module od19_recognition
```
Expected: ไม่มี output จาก `py_compile`; `run-tests.ps1` 0 failed / 0 error(s)

- [ ] **Step 6: Commit**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
git add -- custom_addons/od19_recognition/controllers custom_addons/od19_recognition/static custom_addons/od19_recognition/tests/test_recognition.py
git commit -m "feat(od19_recognition): add portal controllers for feed, kudos and summary"
```

---

### Task 7: บล็อก Team Wall ([D]) + หน้าเต็ม + backend views + inject ผ่าน anchor

**Files:**
- Modify: `custom_addons/od19_recognition/views/portal_templates.xml` (สร้างใหม่)
- Create: `custom_addons/od19_recognition/views/od19_recognition_views.xml`, `views/menus.xml`
- Modify: `custom_addons/od19_recognition/static/src/css/od19_recognition.css`
- Modify: `custom_addons/od19_recognition/tests/test_recognition.py`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

เพิ่มคลาสนี้ **ต่อท้าย** `custom_addons/od19_recognition/tests/test_recognition.py`:

```python
@tagged("post_install", "-at_install")
class TestRecognitionInjection(HttpCase):
    def setUp(self):
        super().setUp()
        self.tester = self.env["res.users"].create(
            {
                "name": "Wall Tester",
                "login": "wall_tester",
                "password": "wall_tester",
                "group_ids": [
                    Command.link(self.env.ref("base.group_user").id),
                    Command.link(
                        self.env.ref("od19_recognition.group_recognition_user").id
                    ),
                ],
            }
        )

    def test_team_wall_injected_into_portal(self):
        self.authenticate("wall_tester", "wall_tester")
        html = self.url_open("/employee-portal").text
        self.assertIn("od19-team-wall", html)
        self.assertIn('data-od19-recognition-summary="/my/recognition/summary"', html)

    def test_recognition_full_page_opens(self):
        self.authenticate("wall_tester", "wall_tester")
        response = self.url_open("/my/recognition")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ให้ Kudos", response.text)
```

- [ ] **Step 2: รันเทสต์เพื่อยืนยันว่าล้มเหลว**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
.\run-tests.ps1 -Module od19_recognition
```
Expected: FAIL — ไม่พบ `od19-team-wall` (ยังไม่มีเทมเพลต/xpath)

- [ ] **Step 3: สร้างเทมเพลต portal (บล็อก Team Wall + หน้าเต็ม + ฟอร์ม)**

สร้าง `custom_addons/od19_recognition/views/portal_templates.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- Inject the Team Wall into the employee portal, right after the anchor -->
    <template id="portal_employee_wall" inherit_id="od19_website.od19_employee_portal">
        <xpath expr="//div[@id='od19-recognition-anchor']" position="after">
            <t t-call="od19_recognition.portal_wall_strip"/>
        </xpath>
    </template>

    <!-- Short block shown on the portal home page -->
    <template id="portal_wall_strip" name="Team Wall Strip">
        <div class="od19-recognition-panel od19-team-wall"
             data-od19-recognition-summary="/my/recognition/summary">
            <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap">
                <h5 class="mb-0">
                    <i class="fa fa-heart me-2" style="color:var(--od19-primary);"/>
                    ขอบคุณเพื่อนร่วมงาน (Team Wall)
                </h5>
                <a href="/my/recognition" class="btn btn-sm btn-outline-primary">ให้ Kudos / ดูทั้งหมด</a>
            </div>
            <div class="od19-kudos-feed">
                <p class="text-muted small mb-0">
                    <i class="fa fa-spinner fa-spin me-1"/>กำลังโหลด…
                </p>
            </div>
            <div class="od19-celebrations mt-3 d-none"></div>
        </div>
    </template>

    <!-- Full page -->
    <template id="portal_recognition_page" name="Recognition">
        <t t-call="portal.portal_layout">
            <t t-set="o_portal_fullwidth_alert" t-value="True"/>
            <div class="container mt-4">
                <t t-if="given">
                    <div class="alert alert-success py-2">
                        <i class="fa fa-check-circle me-1"/>ส่ง Kudos เรียบร้อยแล้ว ขอบคุณ!
                    </div>
                </t>
                <t t-if="error">
                    <div class="alert alert-danger py-2">
                        <i class="fa fa-exclamation-triangle me-1"/><span t-esc="error"/>
                    </div>
                </t>

                <h3 class="mb-3">
                    <i class="fa fa-heart me-2" style="color:var(--od19-primary);"/>
                    ขอบคุณเพื่อนร่วมงาน (Recognition)
                </h3>

                <div class="row g-4">
                    <div class="col-lg-5">
                        <div class="od19-recognition-panel">
                            <h5 class="mb-3">ให้ Kudos</h5>
                            <form action="/my/recognition/give" method="post" class="od19-kudos-form">
                                <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
                                <div class="mb-2">
                                    <label class="od19-field-label">เพื่อนร่วมงาน</label>
                                    <select name="recipient_id" class="form-control" required="required">
                                        <option value="">-- เลือกเพื่อนร่วมงาน --</option>
                                        <t t-foreach="employees" t-as="emp">
                                            <option t-att-value="emp.id" t-esc="emp.name"/>
                                        </t>
                                    </select>
                                </div>
                                <div class="mb-2">
                                    <label class="od19-field-label">ป้าย</label>
                                    <select name="badge_id" class="form-control">
                                        <option value="">-- ไม่ระบุ --</option>
                                        <t t-foreach="badges" t-as="badge">
                                            <option t-att-value="badge.id" t-esc="badge.name"/>
                                        </t>
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="od19-field-label">ข้อความขอบคุณ</label>
                                    <textarea name="message" class="form-control" rows="3"
                                              maxlength="500" required="required"
                                              placeholder="ขอบคุณสำหรับ..."></textarea>
                                </div>
                                <button type="submit" class="btn btn-primary w-100"
                                        style="background:var(--od19-primary);border:none;">
                                    <i class="fa fa-paper-plane me-1"/>ส่ง Kudos
                                </button>
                            </form>
                        </div>

                        <div class="od19-recognition-panel">
                            <h5 class="mb-3">
                                <i class="fa fa-birthday-cake me-2" style="color:var(--od19-secondary);"/>
                                เดือนนี้มีอะไร
                            </h5>
                            <t t-if="celebrations['birthdays']">
                                <div class="od19-celebration-title">วันเกิด</div>
                                <ul class="list-unstyled mb-2">
                                    <t t-foreach="celebrations['birthdays']" t-as="b">
                                        <li><i class="fa fa-birthday-cake me-1" style="color:#e91e63;"/><span t-esc="b['name']"/> · วันที่ <span t-esc="b['day']"/></li>
                                    </t>
                                </ul>
                            </t>
                            <t t-if="celebrations['anniversaries']">
                                <div class="od19-celebration-title">ครบรอบการทำงาน</div>
                                <ul class="list-unstyled mb-0">
                                    <t t-foreach="celebrations['anniversaries']" t-as="a">
                                        <li><i class="fa fa-trophy me-1" style="color:var(--od19-secondary);"/><span t-esc="a['name']"/> · <span t-esc="a['years']"/> ปี</li>
                                    </t>
                                </ul>
                            </t>
                            <t t-if="not celebrations['birthdays'] and not celebrations['anniversaries']">
                                <p class="text-muted small mb-0">ไม่มีวันสำคัญในเดือนนี้</p>
                            </t>
                        </div>
                    </div>

                    <div class="col-lg-7">
                        <div class="od19-recognition-panel">
                            <h5 class="mb-3">ฟีดล่าสุด</h5>
                            <t t-if="feed">
                                <t t-foreach="feed" t-as="item">
                                    <div class="od19-kudos-item mb-3 pb-3 border-bottom">
                                        <div class="d-flex align-items-center gap-2 mb-1">
                                            <span class="od19-kudos-badge" t-att-style="'background:%s;' % item['badge_color']">
                                                <i t-attf-class="fa #{item['badge_icon']}"/>
                                            </span>
                                            <strong t-esc="item['author']"/>
                                            <i class="fa fa-arrow-right text-muted"/>
                                            <strong t-esc="item['recipient']"/>
                                            <small class="text-muted ms-auto" t-esc="item['date']"/>
                                        </div>
                                        <div t-esc="item['message']"/>
                                    </div>
                                </t>
                            </t>
                            <t t-else="">
                                <p class="text-muted small mb-0">ยังไม่มี Kudos</p>
                            </t>
                        </div>
                    </div>
                </div>
            </div>
        </t>
    </template>

</odoo>
```

- [ ] **Step 4: สร้าง backend views + menus**

สร้าง `custom_addons/od19_recognition/views/od19_recognition_views.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_od19_recognition_tree" model="ir.ui.view">
        <field name="name">od19.recognition.tree</field>
        <field name="model">od19.recognition</field>
        <field name="arch" type="xml">
            <list string="Kudos">
                <field name="published_date"/>
                <field name="author_id"/>
                <field name="recipient_id"/>
                <field name="badge_id"/>
                <field name="message"/>
                <field name="is_public"/>
            </list>
        </field>
    </record>

    <record id="view_od19_recognition_form" model="ir.ui.view">
        <field name="name">od19.recognition.form</field>
        <field name="model">od19.recognition</field>
        <field name="arch" type="xml">
            <form string="Kudos">
                <sheet>
                    <group>
                        <group>
                            <field name="author_id"/>
                            <field name="recipient_id"/>
                            <field name="badge_id"/>
                        </group>
                        <group>
                            <field name="published_date"/>
                            <field name="company_id" groups="base.group_multi_company"/>
                            <field name="is_public"/>
                        </group>
                    </group>
                    <field name="message" placeholder="ขอบคุณสำหรับ..."/>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_od19_recognition" model="ir.actions.act_window">
        <field name="name">Kudos</field>
        <field name="res_model">od19.recognition</field>
        <field name="view_mode">list,form</field>
    </record>

    <record id="view_od19_recognition_badge_tree" model="ir.ui.view">
        <field name="name">od19.recognition.badge.tree</field>
        <field name="model">od19.recognition.badge</field>
        <field name="arch" type="xml">
            <list string="Badges" editable="bottom">
                <field name="sequence" widget="handle"/>
                <field name="name"/>
                <field name="icon"/>
                <field name="color" widget="color"/>
                <field name="active"/>
            </list>
        </field>
    </record>

    <record id="action_od19_recognition_badge" model="ir.actions.act_window">
        <field name="name">Badges</field>
        <field name="res_model">od19.recognition.badge</field>
        <field name="view_mode">list,form</field>
    </record>
</odoo>
```

สร้าง `custom_addons/od19_recognition/views/menus.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <menuitem id="menu_od19_recognition_root"
              name="Recognition"
              parent="hr.menu_hr_root"
              groups="od19_recognition.group_recognition_manager"
              sequence="95"/>
    <menuitem id="menu_od19_recognition_kudos"
              name="Kudos"
              parent="menu_od19_recognition_root"
              action="action_od19_recognition"
              sequence="10"/>
    <menuitem id="menu_od19_recognition_badges"
              name="Badges"
              parent="menu_od19_recognition_root"
              action="action_od19_recognition_badge"
              sequence="20"/>
</odoo>
```

- [ ] **Step 5: เติม CSS + JS ของบล็อก Team Wall**

ต่อท้าย `custom_addons/od19_recognition/static/src/css/od19_recognition.css`:

```css
.od19-kudos-item .od19-kudos-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    color: #fff;
    font-size: 0.85rem;
}
.od19-celebration-title {
    font-weight: 700;
    color: var(--od19-primary);
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin-bottom: 6px;
}
.od19-celebration-pill {
    display: inline-block;
    background: var(--od19-light);
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.8rem;
    margin: 0 6px 6px 0;
}
```

เพิ่ม JS ใหม่ `custom_addons/od19_recognition/static/src/js/od19_recognition_wall.js` **และลงทะเบียนใน manifest** (เพิ่มบรรทัดใน `assets["web.assets_frontend"]`):

```javascript
/* Employee portal — Team Wall strip (lazy JSON). */
(function () {
    'use strict';

    function esc(value) {
        if (value === null || value === undefined) return '';
        return String(value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function renderFeed(container, feed) {
        if (!feed || !feed.length) {
            container.innerHTML = '<p class="text-muted small mb-0">ยังไม่มี Kudos</p>';
            return;
        }
        container.innerHTML = feed.map(function (item) {
            return '<div class="od19-kudos-item mb-2">' +
                '<div class="d-flex align-items-center gap-2">' +
                '<span class="od19-kudos-badge" style="background:' + esc(item.badge_color) + '">' +
                '<i class="fa ' + esc(item.badge_icon) + '"></i></span>' +
                '<strong>' + esc(item.author) + '</strong>' +
                '<i class="fa fa-arrow-right text-muted" style="font-size:0.7rem;"></i>' +
                '<strong>' + esc(item.recipient) + '</strong>' +
                '<small class="text-muted ms-auto">' + esc(item.date) + '</small></div>' +
                '<div class="od19-kudos-msg">' + esc(item.message) + '</div></div>';
        }).join('');
    }

    function renderCelebrations(container, celebrations) {
        if (!container || !celebrations) return;
        var parts = [];
        (celebrations.birthdays || []).forEach(function (b) {
            parts.push('<span class="od19-celebration-pill"><i class="fa fa-birthday-cake me-1" style="color:#e91e63;"></i>' + esc(b.name) + '</span>');
        });
        (celebrations.anniversaries || []).forEach(function (a) {
            parts.push('<span class="od19-celebration-pill"><i class="fa fa-trophy me-1" style="color:#f39200;"></i>' + esc(a.name) + ' ' + esc(a.years) + ' ปี</span>');
        });
        if (parts.length) {
            container.innerHTML = '<div class="od19-celebration-title">เดือนนี้</div>' + parts.join('');
            container.classList.remove('d-none');
        }
    }

    function load() {
        var root = document.querySelector('.od19-team-wall');
        if (!root || root.dataset.loaded) return;
        root.dataset.loaded = '1';
        fetch(root.dataset.od19RecognitionSummary, {
            headers: { Accept: 'application/json' },
            credentials: 'same-origin',
        })
            .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
            .then(function (data) {
                renderFeed(root.querySelector('.od19-kudos-feed'), data.feed);
                renderCelebrations(root.querySelector('.od19-celebrations'), data.celebrations);
            })
            .catch(function () { /* keep placeholder */ });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', load);
    } else {
        load();
    }
})();
```

แก้ `custom_addons/od19_recognition/__manifest__.py` — ใน `assets["web.assets_frontend"]` เพิ่ม:
```python
            "od19_recognition/static/src/js/od19_recognition_wall.js",
```

- [ ] **Step 6: ตรวจ XML + อัปเดต + รันเทสต์**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('custom_addons/od19_recognition/views/portal_templates.xml')"
venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('custom_addons/od19_recognition/views/od19_recognition_views.xml')"
venv19\Scripts\python.exe -c "import xml.dom.minidom; xml.dom.minidom.parse('custom_addons/od19_recognition/views/menus.xml')"
$env:PYTHONDONTWRITEBYTECODE='1'
venv19\Scripts\python.exe odoo-bin -c odoo.conf -u od19_recognition --stop-after-init --logfile data_test_install.log
.\run-tests.ps1 -Module od19_recognition
```
Expected: ไม่มี output จาก 3 คำสั่งแรก; ติดตั้ง/อัปเดตสำเร็จ; `run-tests.ps1` 0 failed / 0 error(s)

- [ ] **Step 7: ตรวจ R7 — ถอนโมดูลแล้วหน้า portal ต้องไม่พัง**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
$env:PYTHONDONTWRITEBYTECODE='1'
venv19\Scripts\python.exe odoo-bin -c odoo.conf -u od19_website --stop-after-init --logfile data_test_recheck.log
```
Expected: ไม่มี `ERROR`/`CRITICAL` เรื่อง template inheritance (พิสูจน์ว่า `od19_website` render ได้โดยไม่ต้องพึ่ง `od19_recognition`)

- [ ] **Step 8: Commit**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
git add -- custom_addons/od19_recognition/views custom_addons/od19_recognition/static custom_addons/od19_recognition/__manifest__.py custom_addons/od19_recognition/tests/test_recognition.py
git commit -m "feat(od19_recognition): inject team wall into portal and add recognition page"
```

---

### Task 8: เก็บรายละเอียด (responsive / a11y) + release note

**Files:**
- Modify: `custom_addons/od19_website/static/src/css/od19_website.css` (media queries เพิ่มถ้าจำเป็น)
- Create: `deployment/releases/v19.0.7.md`

- [ ] **Step 1: ตรวจ responsive/mobile**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
.\run-tests.ps1 -Module od19_website
```
Expected: 0 failed / 0 error(s) — ยืนยันว่า media queries ที่ Task 3/4 เพิ่มไม่ทำให้เทสต์เดิมพัง

- [ ] **Step 2: เขียน release note**

สร้าง `deployment/releases/v19.0.7.md` (โครงตาม [`v19.0.5.md`](file:///c:/odoo-dev/od19-emp-exp/deployment/releases/v19.0.5.md)):

```markdown
# Release v19.0.7 — Employee Experience (Portal)

## ข้อมูล Release

| รายการ | ค่า |
|---|---|
| Tag | `v19.0.7` (รอออกหลัง merge เข้า `19.0`) |
| Code baseline | `feature/od19_website-employee-experience` (base `19.0` = `12d29d731b6`, รวม SP1 #27 แล้ว) |
| วันที่ | 2026-11-11 |
| แท็กก่อนหน้า | `v19.0.6` |
| Branch | `feature/od19_website-employee-experience` |

## โมดูลที่เปลี่ยน

| โมดูล | เวอร์ชัน | สาระ |
|---|---|---|
| `od19_website` | `19.0.1.0.0` → `19.0.1.1.0` | Hero ทักทายตามเวลา + My Day Strip (lazy JSON `/employee-portal/me-summary`) + ตารางของฉัน/ทางลัดใช้บ่อย + จัดกลุ่มเมนูด่วน 3 กลุ่ม + anchor สำหรับ recognition |
| `od19_recognition` | `19.0.1.0.0` (ใหม่) | โมเดล Kudos/ป้าย + ฟีด + ฟอร์มให้ Kudos (POST+CSRF) + อวยพรวันเกิด/วันครบรอบ + security (อ่านสาธารณะ, แก้/ลบเฉพาะเจ้าของ) |

## Migration / Upgrade

- ติดตั้งใหม่: `-i od19_recognition`
- อัปเดต: `-u od19_website,od19_recognition`
- ไม่มี migration สคริปต์; ไม่แตะข้อมูลเดิม

## Rollback

- ถอน `od19_recognition` → หน้า `/employee-portal` ยังทำงานปกติ (additive)
- `od19_website` ถอยเวอร์ชันกลับ `19.0.1.0.0` ได้ (ไม่มีการลบข้อมูล)

## สถานะ Release Checklist

- [ ] Unit test `od19_website` ผ่าน 0 failed / 0 error
- [ ] Unit test `od19_recognition` ผ่าน 0 failed / 0 error
- [ ] ทดสอบมือถือ (จอแรก) ผ่าน
- [ ] ตรวจ a11y พื้นฐาน (aria-label ปุ่ม, contrast)
- [ ] Merge เข้า `19.0` (ต้องได้รับอนุมัติจากผู้ใช้)
```

- [ ] **Step 3: Commit**

Run:
```powershell
cd c:\odoo-dev\od19-emp-exp
git add -- deployment/releases/v19.0.7.md
git commit -m "docs(release): add v19.0.7 employee experience release note"
```

---

## Self-Review

**1. Spec coverage**

| Spec | Task ที่รองรับ |
|---|---|
| R1 Hero ตามเวลา + ชื่อ + ตำแหน่ง/แผนก + อักษรย่อ | Task 2 |
| R2 My Day Strip (ลงเวลา/รออนุมัติ/นัดถัดไป/วันลา) | Task 1, Task 3 |
| R3 lazy JSON + cache ต่อผู้ใช้ TTL 60s | Task 1 (`ME_SUMMARY_CACHE`), Task 6 (`RECOGNITION_SUMMARY_CACHE`) |
| R4 ตารางของฉัน + ทางลัดใช้บ่อย + จัดกลุ่มเมนู | Task 3, Task 4 |
| R5 Kudos + ฟีดสาธารณะ | Task 5, Task 6, Task 7 |
| R6 วันเกิด/วันครบรอบ + อวยพร | Task 5, Task 6, Task 7 |
| R7 additive (ถอน `od19_recognition` ได้) | Task 3 (anchor), Task 7 (xpath + Step 7) |
| R8 ไม่แตะ core | ทุก Task (Decisions ข้อ 1) |
| R9 โทนแบรนด์เดิม + Sarabun | Task 3, Task 4, Task 7 (CSS ใช้ `--od19-*`) |
| R10 responsive | Task 3, Task 4, Task 8 |
| R11 ไม่มีอนุมัติ/จ่ายเงิน + author/company บังคับ server-side | Task 1, Task 6, Task 5 (Task 7) |
| R12 Unit test | ทุก Task ที่มี code |
| Acceptance: cache hit/miss | Task 1 (`_od19_me_summary_data` เรียกครั้งเดียวต่อ TTL) |
| Acceptance: privacy `is_public` / เจ้าของเท่านั้น | Task 5 (`test_private_kudos_hidden_from_others`, `test_only_author_can_edit`) |
| Risk #3 ชื่อฟิลด์ HR | Task 1 (attendance/leave), Task 6 (birthday/anniversary) — อ้างฟิลด์จริงที่ตรวจแล้ว |
| Risk #4 sudo() privacy | Decision ข้อ 9 + Task 6 (`birthday_public_display_string != "hidden"`) |

**2. Placeholder scan:** ไม่มี "TBD/TODO/implement later" — ทุก step มีโค้ด/คำสั่งจริง; `test_employee_experience.py` มี placeholder ชั่วคราวใน Task 1 Step 1 ซึ่งถูกแทนที่ครบใน Task 2/3/4 (ไม่เหลือ placeholder เมื่อจบแผน)

**3. Type consistency:**
- ชื่อ route ตรงกันทุกจุด: `/employee-portal/me-summary`, `/my/recognition`, `/my/recognition/give`, `/my/recognition/summary`
- คีย์ payload me-summary ตรงกับ JS: `attendance.available/check_in/check_out`, `approvals.pending_count`, `next_booking.start/room`, `leave.available/remaining_display`, `schedule[].time/label/detail/kind`
- คีย์ payload recognition ตรงกับ JS: `feed[].author/recipient/message/badge_icon/badge_color/date`, `celebrations.birthdays[].name/day`, `celebrations.anniversaries[].name/years`
- ชื่อโมเดล/กลุ่มตรงกัน: `od19.recognition`, `od19.recognition.badge`, `od19_recognition.group_recognition_user`, `od19_recognition.group_recognition_manager`
- anchor ตรงกัน: `od19_website` สร้าง `<div id="od19-recognition-anchor"/>`; `od19_recognition` ใช้ `//div[@id='od19-recognition-anchor']`
- `hr.leave.state` อนุมัติใช้ **`validate`** (ไม่ใช่ `approved`) ทุกจุด
- ฟิลด์ HR ที่ใช้: `employee.birthday`, `employee.birthday_public_display_string`, `employee.contract_date_start`, `employee.date_start`, `employee.allocation_remaining_display`, `employee.show_leaves` — ตรวจกับซอร์สจริงแล้ว

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-11-11-od19-employee-experience.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

> **สถานะประเด็น SP1 (แก้แล้ว):** `feature/od19_website-refresh-sp1` merge เข้า `19.0` แล้ว (PR #27 → `a24525b3238`) และ v19.0.6 (PR #28) ก็ merge แล้ว ⇒ worktree นี้ merge `origin/19.0` เข้ามาเรียบร้อย (merge commit `8dc5e9bd183`) ไม่มี conflict. **ยังคงต้องเลือกวิธีรัน (ข้อ 1 หรือ 2)**
