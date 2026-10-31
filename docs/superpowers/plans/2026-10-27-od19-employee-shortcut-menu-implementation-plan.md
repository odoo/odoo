# Employee Shortcut Menu (Systray + Portal Card) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** เพิ่มจุดเข้าใช้งานที่ "กด klik ได้จาก UI" ให้พนักงาน 2 จุด — ไอคอนเมนูลัดบน systray (หลังบ้าน) และการ์ด "คู่มือการใช้งาน" ในกริด Quick Access บนหน้า Employee Portal — โดยคงคีย์ลัด `Alt+P` เดิมไว้

**Architecture:** ขยายโมดูลเดิม `od19_website` (ไม่สร้างโมดูลใหม่) ตามกฎ OCA/Odoo 19 · ฝั่งหลังบ้านใช้ OWL component ที่ขึ้นทะเบียนผ่าน `registry.category("systray")` และใช้ `Dropdown`/`DropdownItem` จาก `@web/core/dropdown` · ฝั่งหน้าเว็บเป็นการเพิ่มการ์ด QWeb ในเทมเพลตเดิม · เทสต์เป็น **Python HttpCase** (ไม่ใช้ JS QUnit เพราะ `custom_addons` ไม่มี infra `web.assets_unit_tests`)

**Tech Stack:** Odoo 19, Python (HttpCase), OWL 2, QWeb, PowerShell (Windows)

**อ้างอิง:** spec อนุมัติแล้วที่ [2026-10-27-od19-employee-shortcut-menu-design.md](file:///c:/odoo-dev/odoo19/docs/superpowers/specs/2026-10-27-od19-employee-shortcut-menu-design.md)

---

## ข้อเท็จจริงของสภาพแวดล้อม (ตรวจสอบแล้ว)

| หัวข้อ | ค่าจริง |
|---|---|
| Root repo | `c:\odoo-dev\odoo19` (branch ปัจจุบัน `feat/od19-wave3-corporate-income-tax`) |
| Branch ปลายทาง | `19.0` (tip `7182067bfcd`) |
| commit ของ spec | `ed81204a884` (อยู่บน branch Wave3 ยังไม่อยู่บน `19.0`) |
| venv | `c:\odoo-dev\odoo19\venv19\Scripts\python.exe` |
| DB | `odoo19_pdev` (พอร์ต HTTP ปกติ 8070) |
| อุปสรรค | working tree มีไฟล์แก้ค้างจากเซสชันอื่น 3 ไฟล์ที่เนื้อหาต่างกันระหว่าง `19.0` กับ HEAD ⇒ `git checkout` ไป `19.0` ในโฟลเดอร์เดิม **ไม่ผ่าน** |
| ทางออก | ใช้ **git worktree** แยกโฟลเดอร์ `c:\odoo-dev\odoo19-shortcut` (ไม่แตะงานค้างของเซสชันอื่น) |

---

## File Structure

**สร้างใหม่ (ใน worktree):**
| ไฟล์ | ความรับผิดชอบ |
|---|---|
| `custom_addons/od19_website/static/src/js/od19_shortcut_menu.js` | OWL component + การขึ้นทะเบียน systray (รวม inline template) |
| `custom_addons/od19_website/tests/test_employee_shortcut_menu.py` | เทสต์ Python: asset ผูกใน bundle + การ์ดบน Portal |

**แก้ไข (ใน worktree):**
| ไฟล์ | การเปลี่ยนแปลง |
|---|---|
| `custom_addons/od19_website/__manifest__.py` | เพิ่ม dependency `web_tour` + เพิ่ม asset ใน `web.assets_backend` |
| `custom_addons/od19_website/views/employee_portal.xml` | เพิ่มการ์ด "คู่มือการใช้งาน" (9 → 10 ใบ) |
| `custom_addons/od19_website/tests/__init__.py` | เพิ่ม import เทสต์ใหม่ |
| `docs/superpowers/specs/2026-10-27-od19-employee-shortcut-menu-design.md` | ปรับถ้อยคำจาก JS QUnit → Python HttpCase ให้ตรงกับที่ผู้ใช้อนุมัติ |

**ไม่แตะ:** ไฟล์ Odoo core ทุกไฟล์, `od19_portal_hotkey.js` (คีย์ลัด `Alt+P`), การ์ด Quick Access 9 ใบเดิม

---

## Task 0: เตรียม worktree + branch แยก (isolated)

**Files:**
- Create (worktree): `c:\odoo-dev\odoo19-shortcut\` (ทั้งโฟลเดอร์)

- [ ] **Step 1: สร้าง worktree จาก `19.0` และ branch ใหม่**

รันที่ `c:\odoo-dev\odoo19`:

```powershell
git worktree add C:\odoo-dev\odoo19-shortcut -b feat/od19-employee-shortcut-menu 19.0
```

Expected: `Preparing worktree (new branch 'feat/od19-employee-shortcut-menu')` แล้วสร้างโฟลเดอร์สำเร็จ

- [ ] **Step 2: cherry-pick commit ของ spec เข้า branch ใหม่**

```powershell
git -C C:\odoo-dev\odoo19-shortcut cherry-pick ed81204a884
```

Expected: `[feat/od19-employee-shortcut-menu xxxxxxx] docs(od19_website): design spec for employee shortcut menu and portal guide card` — ไม่มี conflict (commit นี้เพิ่มไฟล์ `.md` ใหม่ไฟล์เดียว)

- [ ] **Step 3: ยืนยันว่า branch ตั้งต้นถูกต้อง**

```powershell
git -C C:\odoo-dev\odoo19-shortcut log --oneline -3
git -C C:\odoo-dev\odoo19-shortcut status --short
```

Expected: มี 2 commit (spec อยู่บนสุด, `7182067bfcd` เป็นฐาน) และ working tree สะอาด

- [ ] **Step 4: ย้ายไฟล์แผนนี้เข้า worktree และ commit**

```powershell
Move-Item "C:\odoo-dev\odoo19\docs\superpowers\plans\2026-10-27-od19-employee-shortcut-menu-implementation-plan.md" "C:\odoo-dev\odoo19-shortcut\docs\superpowers\plans\2026-10-27-od19-employee-shortcut-menu-implementation-plan.md"
git -C C:\odoo-dev\odoo19-shortcut add docs/superpowers/plans/2026-10-27-od19-employee-shortcut-menu-implementation-plan.md
git -C C:\odoo-dev\odoo19-shortcut commit -m "docs(od19_website): implementation plan for employee shortcut menu"
```

Expected: commit สำเร็จ · โฟลเดอร์หลัก `c:\odoo-dev\odoo19` ไม่มีไฟล์แผนนี้ค้างอยู่

- [ ] **Step 5: หยุด dev server เพื่อไม่ให้แย่ง DB ตอนรันเทสต์**

ปิด Odoo ที่รันด้วย `STEP-3-Start-Odoo19.ps1` (ถ้ารันอยู่) ก่อนไป Task ถัดไป — เทสต์จะ `-u od19_website` กับ DB `odoo19_pdev` โดยตรง

---

## Task 1: ปรับ spec ให้ตรงกับแนวทางเทสต์ที่อนุมัติ (Python HttpCase)

**Files:**
- Modify: `c:\odoo-dev\odoo19-shortcut\docs\superpowers\specs\2026-10-27-od19-employee-shortcut-menu-design.md`

- [ ] **Step 1: แก้แถวที่ 3 ของตาราง §3.1**

แทนที่บรรทัด:

```markdown
| 3 | เทสต์ JS (QUnit) ตรวจการลงทะเบียน systray และการเปิด dropdown | `static/tests/` |
```

ด้วย:

```markdown
| 3 | เทสต์ Python (HttpCase) ตรวจการผูก asset ใน bundle และการ์ดบน Portal | `tests/` |
```

- [ ] **Step 2: แก้ตารางไฟล์ §4.3**

แทนที่บรรทัด:

```markdown
| `custom_addons/od19_website/static/tests/od19_shortcut_menu_tests.js` | **เพิ่ม** — เทสต์ JS |
```

ด้วย:

```markdown
| `custom_addons/od19_website/tests/test_employee_shortcut_menu.py` | **เพิ่ม** — เทสต์ Python (HttpCase) |
| `custom_addons/od19_website/tests/__init__.py` | **แก้** — เพิ่ม import เทสต์ใหม่ |
```

- [ ] **Step 3: แก้ตาราง §6**

แทนที่บรรทัด:

```markdown
| JS unit (QUnit) | ตรวจว่า systray registry มี key ของเรา และเมื่อ mount แล้วมีรายการครบ 4 รายการ + เปิด dropdown ได้ |
```

ด้วย:

```markdown
| Python HttpCase | ตรวจว่าไฟล์ `od19_shortcut_menu.js` ถูกผูกเข้า bundle `web.assets_backend` จริง และหน้า `/employee-portal` มีการ์ด "คู่มือการใช้งาน" รวมทั้งสิ้น 10 ใบ |
```

- [ ] **Step 4: commit**

```powershell
git -C C:\odoo-dev\odoo19-shortcut add docs/superpowers/specs/2026-10-27-od19-employee-shortcut-menu-design.md
git -C C:\odoo-dev\odoo19-shortcut commit -m "docs(od19_website): switch shortcut menu test approach to Python HttpCase"
```

---

## Task 2: การ์ด "คู่มือการใช้งาน" บน Employee Portal (TDD)

**Files:**
- Create: `c:\odoo-dev\odoo19-shortcut\custom_addons\od19_website\tests\test_employee_shortcut_menu.py`
- Modify: `c:\odoo-dev\odoo19-shortcut\custom_addons\od19_website\tests\__init__.py`
- Modify: `c:\odoo-dev\odoo19-shortcut\custom_addons\od19_website\views\employee_portal.xml:366-374`

- [ ] **Step 1: เขียนเทสต์ที่ยังไม่ผ่าน**

สร้างไฟล์ `custom_addons/od19_website/tests/test_employee_shortcut_menu.py`:

```python
from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged("post_install", "-at_install")
class TestShortcutMenuAsset(HttpCase):
    """The systray shortcut menu must be wired into the backend bundle."""

    def test_shortcut_menu_in_backend_bundle(self):
        assets = self.env["ir.qweb"]._get_asset_content("web.assets_backend")[0]
        urls = [asset["url"] for asset in assets]
        self.assertIn(
            "od19_website/static/src/js/od19_shortcut_menu.js",
            urls,
        )


@tagged("post_install", "-at_install")
class TestEmployeePortalGuideCard(HttpCase):
    """The Quick Access grid must expose the user-guide shortcut card."""

    def test_quick_access_has_user_guide_card(self):
        thai = self.env["res.lang"]._activate_lang("th_TH")
        website = self.env["website"].get_current_website()
        website.language_ids = website.language_ids | thai

        tester = self.env["res.users"].create({
            "name": "Shortcut Tester",
            "login": "od19_shortcut_tester",
            "email": "od19.shortcut.tester@example.com",
            "group_ids": [Command.link(self.env.ref("base.group_user").id)],
        })
        # HttpCase patches the credential check, so only the login must exist.
        self.authenticate(tester.login, "test")

        html = self.url_open("/employee-portal").text

        self.assertIn("คู่มือการใช้งาน", html)
        self.assertIn("/web#action=web_tour.tour_action", html)
        # The guide card joins the nine existing Quick Access cards.
        self.assertGreaterEqual(html.count("od19-portal-card"), 10)
```

- [ ] **Step 2: ลงทะเบียนไฟล์เทสต์**

แก้ `custom_addons/od19_website/tests/__init__.py` ให้เป็น:

```python
from . import test_employee_shortcut_menu
from . import test_website
```

- [ ] **Step 3: รันเทสต์เพื่อยืนยันว่าล้มเหลว (RED)**

```powershell
$py  = "C:\odoo-dev\odoo19\venv19\Scripts\python.exe"
$bin = "C:\odoo-dev\odoo19-shortcut\odoo-bin"
$addons = "C:\odoo-dev\odoo19-shortcut\addons,C:\odoo-dev\odoo19-shortcut\odoo\addons,C:\odoo-dev\odoo19-shortcut\custom_addons,C:\odoo-dev\odoo19\third_party\oca\l10n-thailand,C:\odoo-dev\odoo19\third_party\oca\sale-blanket,C:\odoo-dev\odoo19\third_party\oca\sale-workflow,C:\odoo-dev\odoo19\third_party\oca\server-backend,C:\odoo-dev\odoo19\third_party\oca\server-tools,C:\odoo-dev\odoo19\third_party\oca\server-ux,C:\odoo-dev\odoo19\third_party\oca\helpdesk,C:\odoo-dev\odoo19\third_party\oca\account-financial-tools,C:\odoo-dev\odoo19\third_party\oca\purchase-workflow,C:\odoo-dev\odoo19\third_party\oca\tier-validation,C:\odoo-dev\odoo19\third_party\oca\reporting-engine,C:\odoo-dev\odoo19\third_party\oca\knowledge,C:\odoo-dev\odoo19\third_party\oca\website,C:\odoo-dev\odoo19\third_party\oca\currency,C:\odoo-dev\odoo19\third_party\oca\stock-logistics-request,C:\odoo-dev\odoo19\third_party\oca\account-invoicing,C:\odoo-dev\odoo19\third_party\oca\account-financial-reporting,C:\odoo-dev\odoo19\third_party\oca\account-reconcile"
& $py $bin -c "C:\odoo-dev\odoo19\odoo.conf" --addons-path $addons -d odoo19_pdev -u od19_website --test-enable --test-tags /od19_website --http-port 8071 --stop-after-init
```

Expected: FAIL 2 เคส —
`TestEmployeePortalGuideCard` ล้มที่ `assertIn("คู่มือการใช้งาน", html)` และ `TestShortcutMenuAsset` ล้มที่ `assertIn(...od19_shortcut_menu.js...)`
(หมายเหตุ: การรันครั้งนี้ยังไม่มีการ์ดและยังไม่มีการเพิ่ม asset — เป็น RED ที่ถูกต้อง)

- [ ] **Step 4: เพิ่มการ์ด "คู่มือการใช้งาน"**

ใน `custom_addons/od19_website/views/employee_portal.xml` แทรกการ์ดใหม่ **ก่อน** บรรทัด `</div>` ปิดกริด Quick Access (หลังการ์ด "แดชบอร์ด" ที่ลงท้ายด้วย `href="/web"`):

```xml
                        <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                            <div class="od19-portal-card">
                                <div class="od19-portal-icon"><i class="fa fa-book"/></div>
                                <h5>คู่มือการใช้งาน</h5>
                                <p>User Guide</p>
                                <a href="/web#action=web_tour.tour_action">เปิดใช้งาน →</a>
                            </div>
                        </div>
```

- [ ] **Step 5: รันเทสต์เฉพาะการ์ด เพื่อยืนยันว่าผ่าน (GREEN ครึ่งแรก)**

```powershell
& $py $bin -c "C:\odoo-dev\odoo19\odoo.conf" --addons-path $addons -d odoo19_pdev -u od19_website --test-enable --test-tags /od19_website:TestEmployeePortalGuideCard --http-port 8071 --stop-after-init
```

Expected: PASS 1 เคส (`TestEmployeePortalGuideCard`) · `TestShortcutMenuAsset` ยัง FAIL (จะแก้ใน Task 3)

- [ ] **Step 6: commit**

```powershell
git -C C:\odoo-dev\odoo19-shortcut add custom_addons/od19_website/views/employee_portal.xml custom_addons/od19_website/tests/__init__.py custom_addons/od19_website/tests/test_employee_shortcut_menu.py
git -C C:\odoo-dev\odoo19-shortcut commit -m "feat(od19_website): add user-guide card to employee portal quick access"
```

---

## Task 3: ไอคอนเมนูลัดบน systray (TDD)

**Files:**
- Create: `c:\odoo-dev\odoo19-shortcut\custom_addons\od19_website\static\src\js\od19_shortcut_menu.js`
- Modify: `c:\odoo-dev\odoo19-shortcut\custom_addons\od19_website\__manifest__.py:9-19` และ `:45-47`

- [ ] **Step 1: เทสต์ asset ยังล้มเหลว (ยืนยัน RED ของ Task 3)**

```powershell
& $py $bin -c "C:\odoo-dev\odoo19\odoo.conf" --addons-path $addons -d odoo19_pdev -u od19_website --test-enable --test-tags /od19_website:TestShortcutMenuAsset --http-port 8071 --stop-after-init
```

Expected: FAIL — `od19_website/static/src/js/od19_shortcut_menu.js` ยังไม่อยู่ใน bundle

- [ ] **Step 2: สร้าง OWL component ของ systray**

สร้างไฟล์ `custom_addons/od19_website/static/src/js/od19_shortcut_menu.js`:

```javascript
/** Auto-Info Employee Shortcut Menu — one-click employee links in the systray. */
import { Component, xml } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ShortcutMenu extends Component {
    static template = xml`
        <Dropdown position="'bottom-end'" bottomSheet="false">
            <button title="เมนูลัดพนักงาน">
                <i class="fa fa-lg fa-bolt"/>
            </button>
            <t t-set-slot="content">
                <DropdownItem onSelected="() => this.openPortal()">
                    <i class="fa fa-user-circle me-2"/>Employee Portal
                </DropdownItem>
                <DropdownItem onSelected="() => this.openAction('od19_meeting_room_booking.action_meeting_room_booking')">
                    <i class="fa fa-calendar-check-o me-2"/>จองห้องประชุม
                </DropdownItem>
                <DropdownItem onSelected="() => this.openAction('od19_announcement.announcement_action')">
                    <i class="fa fa-bullhorn me-2"/>ประกาศ
                </DropdownItem>
                <DropdownItem onSelected="() => this.openAction('web_tour.tour_action')">
                    <i class="fa fa-book me-2"/>คู่มือการใช้งาน
                </DropdownItem>
            </t>
        </Dropdown>
    `;
    static components = { Dropdown, DropdownItem };
    static props = [];

    setup() {
        super.setup();
        this.action = useService("action");
    }

    openPortal() {
        this.action.doAction({
            type: "ir.actions.act_url",
            url: "/employee-portal",
            target: "self",
        });
    }

    openAction(xmlid) {
        try {
            this.action.doAction(xmlid);
        } catch (error) {
            // A missing target (e.g. its module is not installed) must never
            // break the systray or the current screen.
            console.warn("[od19_website] shortcut target unavailable:", xmlid, error);
        }
    }
}

registry.category("systray").add(
    "od19_website.shortcut_menu",
    { Component: ShortcutMenu },
    { sequence: 30 }
);
```

- [ ] **Step 3: เพิ่ม dependency `web_tour`**

ใน `custom_addons/od19_website/__manifest__.py` แก้ `depends` ให้เป็น:

```python
    "depends": [
        "website",
        "website_blog",
        "website_crm",
        "website_hr_recruitment",
        "portal",
        "mail",
        "web_tour",
        "od19_announcement",
        "od19_meeting_room_booking",
        "od19_knowledge_enhanced",
    ],
```

- [ ] **Step 4: เพิ่ม asset เข้า `web.assets_backend`**

ในไฟล์เดียวกัน แก้ `assets` ให้เป็น:

```python
    "assets": {
        "web.assets_frontend": [
            "od19_website/static/src/css/od19_website.css",
            "od19_website/static/src/js/od19_products.js",
            "od19_website/static/src/js/od19_portal_rooms.js",
        ],
        "web.assets_backend": [
            "od19_website/static/src/js/od19_portal_hotkey.js",
            "od19_website/static/src/js/od19_shortcut_menu.js",
        ],
    },
```

- [ ] **Step 5: รันเทสต์ทั้งโมดูล เพื่อยืนยันว่าผ่านทั้งหมด (GREEN)**

```powershell
& $py $bin -c "C:\odoo-dev\odoo19\odoo.conf" --addons-path $addons -d odoo19_pdev -u od19_website --test-enable --test-tags /od19_website --http-port 8071 --stop-after-init
```

Expected: PASS ทุกเคส รวม `TestShortcutMenuAsset` และ `TestEmployeePortalGuideCard` · log ไม่มี `ERROR`/`CRITICAL` ในโมดูล `od19_website`

- [ ] **Step 6: commit**

```powershell
git -C C:\odoo-dev\odoo19-shortcut add custom_addons/od19_website/static/src/js/od19_shortcut_menu.js custom_addons/od19_website/__manifest__.py
git -C C:\odoo-dev\odoo19-shortcut commit -m "feat(od19_website): add employee shortcut menu systray icon"
```

---

## Task 4: ตรวจสอบด้วยมือ (Manual verification)

- [ ] **Step 1: รันเซิร์ฟเวอร์บน worktree เพื่อตรวจสายตา**

```powershell
$py  = "C:\odoo-dev\odoo19\venv19\Scripts\python.exe"
& $py "C:\odoo-dev\odoo19-shortcut\odoo-bin" -c "C:\odoo-dev\odoo19\odoo.conf" --addons-path $addons -d odoo19_pdev --http-port 8071
```

จากนั้นเปิด `http://localhost:8071/odoo` แล้วไล่ตรวจตามข้อ 1–6 ของ §7 เกณฑ์ยอมรับ:

- [ ] ไอคอน `fa-bolt` โผล่บน systray มุมขวาบน ทุกหน้า
- [ ] กดแล้วเปิด dropdown เห็น 4 รายการ label ภาษาไทยครบ
- [ ] Employee Portal → ไป `/employee-portal`
- [ ] จองห้องประชุม → เปิด action ของ `od19_meeting_room_booking`
- [ ] ประกาศ → เปิด action ของ `od19_announcement`
- [ ] คู่มือการใช้งาน → เปิด Tour (`web_tour.tour_action`)
- [ ] หน้า `/employee-portal` มีการ์ด "คู่มือการใช้งาน" รวม 10 ใบ
- [ ] กด `Alt+P` ยังพากลับ `/employee-portal` เหมือนเดิม

- [ ] **Step 2: ปิดเซิร์ฟเวอร์ตรวจสอบ แล้วรีสตาร์ท dev server หลักตามปกติ (STEP-3)**

---

## Task 5: Merge เข้า `19.0` และ push

**Files:** ไม่มีไฟล์ (งาน git)

- [ ] **Step 1: ตรวจว่า branch พร้อม merge**

```powershell
git -C C:\odoo-dev\odoo19-shortcut log --oneline 19.0..feat/od19-employee-shortcut-menu
```

Expected: เห็น 5 commit ของงานนี้ (spec, plan, test-approach docs, portal card, systray) และไม่มี commit อื่นปน

- [ ] **Step 2: Fast-forward merge เข้า `19.0` (ตรงตามกลยุทธ์โปรเจกต์)**

```powershell
git -C C:\odoo-dev\odoo19-shortcut checkout 19.0
git -C C:\odoo-dev\odoo19-shortcut merge --ff-only feat/od19-employee-shortcut-menu
```

Expected: `Fast-forward` สำเร็จ · ไม่มี merge commit (ประวัติเส้นตรง)

- [ ] **Step 3: ตรวจผลลัพธ์**

```powershell
git -C C:\odoo-dev\odoo19-shortcut log --oneline -6
git -C C:\odoo-dev\odoo19-shortcut status --short
```

Expected: `19.0` ชี้ที่ commit สุดท้ายของงานนี้ · working tree สะอาด

- [ ] **Step 4: ลบ worktree ชั่วคราว**

```powershell
git -C C:\odoo-dev\odoo19 worktree remove C:\odoo-dev\odoo19-shortcut
git worktree list
```

Expected: เหลือเฉพาะ `C:/odoo-dev/odoo19` · ลบโฟลเดอร์ `odoo19-shortcut` แล้ว

- [ ] **Step 5: push ขึ้น origin**

```powershell
git -C C:\odoo-dev\odoo19 log --oneline origin/19.0..19.0
git -C C:\odoo-dev\odoo19 push origin 19.0
```

Expected: แสดง commit ที่จะ push แล้ว push สำเร็จ
(ถ้า push ถูกปฏิเสธ ให้ใช้ `git pull --rebase` แล้ว push ใหม่ — **ห้าม** force push)

---

## Self-Review (ผู้เขียนแผนตรวจเอง)

- **ครอบคลุม spec:** R1–R6 (§2.2) → Task 3 (systray คลิกได้) · Task 2 (การ์ด) · Task 3 Step 3 (dependency) · ทั้งงานอยู่แต่ใน `od19_website` (ไม่แตะ core) · label ไทยครบ · Task 4 ตรวจว่า `Alt+P` ไม่เสีย ✅
- **เกณฑ์ยอมรับ §7:** ข้อ 1–3, 5, 6 ตรวจด้วย Task 4 · ข้อ 4 (การ์ด 9→10) ตรวจด้วยเทสต์ `TestEmployeePortalGuideCard` และ Task 4 ✅
- **TDD:** ทุกฟีเจอร์มี RED → GREEN (Task 2 Step 3, Task 3 Step 1) ✅
- **ไม่มี placeholder:** ทุก step มีคำสั่ง/โค้ดจริง ✅
- **ความเสี่ยง:** ถ้า `-u od19_website` แล้วมี OCA module ที่ DB ติดตั้งไว้แต่หาไม่เจอ ให้ตรวจว่า `--addons-path` ใน Task 2 Step 3 ครบตาม `odoo.conf` (คัดลอกมาจากไฟล์จริงแล้ว) — ถ้า base ของ branch เปลี่ยน script `$addons` ต้องอัปเดตคู่กัน
