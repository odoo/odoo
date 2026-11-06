# HR Expense Phase 2 — Employee UX (Wizard backend + Mileage + Vehicle Book) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ทำให้พนักงานยื่นใบเบิกได้ง่าย (≤ 4 ขั้น) ผ่าน wizard ฝั่ง backend พร้อมรองรับ **Mileage** (ค่าเดินทางตามระยะทาง) และ **สมุดรถพนักงาน** (`od19.employee.vehicle`) ที่จดจำรถและเติมอัตโนมัติในครั้งถัดไป

**Architecture:**
- **Mileage + สมุดรถ** อยู่ในโมดูลเดิม `od19_hr_expense_enhanced` (ไม่มี dependency ใหม่) — ใช้กลไก `hr.expense` core: UoM = กม., `quantity` = ระยะทาง (กม.), `total_amount` = ระยะทาง × อัตรา/กม. (ฟิลด์ที่ตั้งค่าได้) → core คำนวณ `price_unit` ให้เอง (ดู §กลไกที่ยืนยันจากโค้ดจริง)
- **Wizard + Kanban สถานะ** อยู่ในโมดูลใหม่ `od19_hr_expense_portal` (ตามสเปก §5) — Phase 2 ทำเฉพาะฝั่ง backend; portal/template เป็น Phase 3
- อัตรา Mileage ตั้งค่าที่ระดับบริษัท (`res.company.od19_mileage_rate`) ตามแบบแผนเดียวกับเบี้ยเลี้ยง ม.42(3)
- **ไม่แตะ Odoo core** และไม่เปลี่ยนโครงสร้างข้อมูล core

**Tech Stack:** Odoo 19 CE · Python 3 · Odoo `TransactionCase` / `Form` tests · XML data & views

**ข้อกำหนดอ้างอิง (บังคับ):**
- ตาม [AGENTS.md](file:///c:/odoo-dev/odoo19/AGENTS.md): ห้ามแก้ Odoo core · commit ได้เองใน `custom_addons/` + `docs/` หลังผ่าน Pre-flight · Conventional Commits · **ห้าม `git add -A`** · Single-writer
- ฐานข้อมูลที่ใช้ทดสอบ: `odoo19_pdev`
- **ห้ามรัน Unit Test แทนผู้ใช้** — ระบุคำสั่งไว้ให้ผู้ใช้รันเอง
- branch งาน: `feature/od19-hr-expense-ux` (base `origin/19.0`)
- สเปกอ้างอิง: `docs/superpowers/specs/2026-11-06-od19-hr-expense-reimbursement-design.md` (§6.2, §6.5, §6.6, §9.1, §11 Phase 2, §12 T9–T11)

---

## Known Constraints (ตัดสินใจไว้ล่วงหน้า)

| # | เรื่อง | แนวทาง |
|---|---|---|
| C1 | **การแสดง "รอใคร" (tier approver)** ต้องอาศัยฟิลด์ `review_ids`/`validation_status` ซึ่งมาจาก Phase 1 (ยังไม่ merge เข้า branch นี้) | implement ด้วย runtime guard: อ่าน `review_ids` เมื่อมีฟิลด์จริงในโมเดล (`'review_ids' in self.env['hr.expense']._fields`) มิฉะนั้น fallback เป็นป้ายตาม `state` |
| C2 | **โมดูล `od19_hr_expense_portal` ตั้งชื่อตามสเปก** แม้ Phase 2 จะยังไม่มี portal template | Phase 2 ใส่เฉพาะ wizard/Kanban (backend); Phase 3 เติม controller/templates |
| C3 | **Mileage ไม่มี VAT / ไม่หัก WHT** | บังคับ `tax_ids` ว่างเมื่อ `od19_is_mileage` (แบบเดียวกับ payment certificate ของเดิม) |
| C4 | **นิยาม "รถล่าสุด"** | เรียง `od19_last_used_date desc, id desc` (สเปก §K9) |
| C5 | **สำเนาข้อมูลรถ ณ เวลาที่เบิก** | เก็บ `od19_mileage_vehicle_type` + `od19_mileage_plate` เป็น Char snapshot บน `hr.expense` |
| C6 | **กลไก Mileage กับ `hr.expense` core** | `price_unit` เป็น readonly+computed เขียนทับไม่ได้ → ตั้ง `quantity = กม.` + `total_amount = กม. × อัตรา` (core คำนวณ `price_unit` ให้เองเฉพาะสินค้าไม่มีต้นทุน — กรณีหมวด Mileage) |
| C7 | **ตัวกำหนดว่าเป็น Mileage** | ใช้ **ธงที่หมวดค่าใช้จ่าย**: เพิ่ม `od19_is_mileage_category` (Boolean) บน `product.template` ใน `od19_hr_expense_enhanced`; wizard ใช้ `compute` (read-only) อ่านค่าจากหมวดที่เลือก |
| C8 | **หมวด Mileage ต้องเป็นสินค้าไม่มีต้นทุน** | `product_has_cost = not is_zero(standard_price)` → ต้องมีสินค้าหมวด **`standard_price = 0`** + UoM = กม. (สินค้า core `expense_product_mileage` มี `standard_price = 1.0` จึงใช้ไม่ได้) → สร้างสินค้าใหม่ใน `data/od19_expense_category_data.xml` |

---

## File Structure

| ไฟล์ | บทบาท | การเปลี่ยนแปลง |
|---|---|---|
| `custom_addons/od19_hr_expense_enhanced/models/od19_employee_vehicle.py` | โมเดลสมุดรถ `od19.employee.vehicle` | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_enhanced/models/product_template.py` | ธง `od19_is_mileage_category` บนสินค้า/หมวดค่าใช้จ่าย | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_enhanced/views/product_template_views.xml` | ช่องติ๊กธงในฟอร์มสินค้า | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_enhanced/data/od19_expense_category_data.xml` | สินค้าหมวด "ค่าเดินทางตามระยะทาง" (ราคาทุน 0, หน่วย กม.) | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_enhanced/models/hr_expense.py` | ฟิลด์/ลอจิก Mileage + autofill รถ | แก้ |
| `custom_addons/od19_hr_expense_enhanced/models/res_company.py` | `od19_mileage_rate` | แก้ |
| `custom_addons/od19_hr_expense_enhanced/models/__init__.py` | import โมเดลใหม่ | แก้ |
| `custom_addons/od19_hr_expense_enhanced/security/ir.model.access.csv` | ACL `od19.employee.vehicle` | แก้ |
| `custom_addons/od19_hr_expense_enhanced/security/hr_expense_security.xml` | ir.rule เห็นเฉพาะรถตัวเอง | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_enhanced/views/od19_employee_vehicle_views.xml` | list/form + เมนู "รถของฉัน" | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_enhanced/views/hr_expense_views.xml` | กลุ่มฟิลด์ Mileage + รถ | แก้ |
| `custom_addons/od19_hr_expense_enhanced/views/res_company_views.xml` | ช่องอัตรา Mileage | แก้ |
| `custom_addons/od19_hr_expense_enhanced/__manifest__.py` | data + version | แก้ |
| `custom_addons/od19_hr_expense_enhanced/tests/test_mileage.py` | เทสต์ T9/T10 | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_enhanced/tests/test_vehicle_book.py` | เทสต์ T11 | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_enhanced/tests/__init__.py` | import เทสต์ใหม่ (**ห้ามทับบรรทัดเดิม**) | แก้ |
| `custom_addons/od19_hr_expense_portal/__manifest__.py` | โมดูลใหม่ | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/__init__.py` + `models/__init__.py` | bootstrap | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/models/od19_expense_quick_create.py` | wizard ยื่นเบิก 4 ขั้น | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/models/hr_expense.py` | Kanban helper (สถานะ/รอใคร) | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/views/hr_expense_quick_create_views.xml` | ฟอร์ม wizard | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/views/hr_expense_kanban_views.xml` | Kanban "ใบเบิกของฉัน" + action + menu | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/security/ir.model.access.csv` | ACL wizard | **สร้างใหม่** |
| `custom_addons/od19_hr_expense_portal/tests/test_quick_create.py` | เทสต์ wizard | **สร้างใหม่** |

---

## กลไกที่ยืนยันจากโค้ดจริง (ใช้อ้างอิงตอน implement)

- `hr.expense` core (Odoo 19): `price_unit` เป็น **readonly + computed** (`_compute_price_unit`) → **เขียนทับไม่ได้** (ค่าจะถูกคำนวณใหม่ทับ)
- `total_amount` = `compute='_compute_total_amount', inverse='_inverse_total_amount', precompute=True, store=True, readonly=False` → **เป็นฟิลด์ที่ผู้ใช้ตั้งค่าได้** (source of truth ฝั่ง UI)
- สินค้าที่ไม่มีต้นทุน (`product_has_cost = False` ซึ่งเป็นกรณีหมวด Mileage): `_compute_total_amount_currency` ถูก skip → `total_amount_currency`/`total_amount` เก็บค่าที่ป้อน; core ตั้ง `price_unit = round(total_amount / quantity)` เอง (บรรทัด `_compute_price_unit` else-branch)
- **Mileage จึงต้องตั้ง `quantity = ระยะทาง (กม.)` + `total_amount = ระยะทาง × อัตรา`** (ไม่ใช่ `price_unit`) แล้ว core จะได้ `price_unit = อัตรา/กม.` ให้เอง
- `hr.expense.product_id` → core เติม `account_id` (บัญชีค่าใช้จ่าย) และ `_compute_tax_ids` ของ enhanced เติม `tax_ids` จาก `product.supplier_taxes_id`
- `od19_hr_expense_enhanced` มีแบบแผน `_compute_od19_per_diem` + `@api.constrains` + `res.company._od19_per_diem_rate()` เป็นต้นแบบสำหรับ Mileage
- `od19_hr_expense_enhanced/models/hr_expense.py::create` เติม `first_approver_id` จากแผนก — ใช้แพตเทิร์นเดียวกันในการเติมรถล่าสุด
- `hr.employee` มี `department_id`, `user_id` (ใช้ผูกสมุดรถกับพนักงานและตรวจสิทธิ์)

---

## Task 0: Pre-flight (บังคับตาม AGENTS.md §2)

- [ ] รัน `git log -1 --oneline` จดค่า HEAD
- [ ] รัน `git status -sb` — ต้องไม่มีไฟล์ที่ agent อื่นกำลังแก้ (ยกเว้น `third_party/oca/reporting-engine` และ `migration/cleanup/remap_accounts_round3.py` ซึ่งเป็นของ process อื่น **ห้ามแตะ/ห้าม stage**)
- [ ] ตรวจไม่มี `.git/index.lock`
- [ ] ยืนยันอยู่ branch `feature/od19-hr-expense-ux`
- [ ] ถ้าข้อใดไม่ผ่าน → หยุดและรายงานผู้ใช้

---

## Task 1: Mileage — ฟิลด์/ลอจิก + อัตราที่บริษัท (`od19_hr_expense_enhanced`)

**Files:**
- Modify: `custom_addons/od19_hr_expense_enhanced/models/res_company.py`
- Modify: `custom_addons/od19_hr_expense_enhanced/models/hr_expense.py`
- Modify: `custom_addons/od19_hr_expense_enhanced/views/res_company_views.xml`
- Modify: `custom_addons/od19_hr_expense_enhanced/views/hr_expense_views.xml`

- [ ] **Step 1: เพิ่มอัตรา Mileage ที่บริษัท**
  ใน `models/res_company.py` เพิ่ม:
  ```python
  od19_mileage_rate = fields.Monetary(
      string='Mileage Rate / km / อัตราค่าเดินทางต่อ กม.',
      currency_field='currency_id',
      help='Standard reimbursement rate per kilometre for own-vehicle travel.',
  )
  ```
  และใน `views/res_company_views.xml` เพิ่ม `<page string="ค่าเดินทาง / Mileage" name="od19_mileage">` พร้อม `<field name="od19_mileage_rate"/>` (วางต่อจากหน้า Per Diem)

- [ ] **Step 2: เพิ่มฟิลด์ Mileage บน `hr.expense`**
  ใน `models/hr_expense.py` เพิ่มกลุ่มฟิลด์:
  ```python
  od19_is_mileage = fields.Boolean(string='Mileage / ค่าเดินทางตามระยะทาง', tracking=True)
  od19_mileage_distance_km = fields.Float(string='Distance (km) / ระยะทาง (กม.)')
  od19_mileage_vehicle_id = fields.Many2one('od19.employee.vehicle', string='Vehicle / รถของฉัน')
  od19_mileage_vehicle_type = fields.Char(string='Vehicle Type (snapshot) / ประเภทยานพาหนะ')
  od19_mileage_plate = fields.Char(string='Plate (snapshot) / ป้ายทะเบียน')
  od19_mileage_origin = fields.Char(string='Origin / ต้นทาง')
  od19_mileage_destination = fields.Char(string='Destination / ปลายทาง')
  od19_mileage_date = fields.Date(string='Travel Date / วันที่เดินทาง')
  od19_mileage_rate = fields.Monetary(
      string='Rate / km / อัตราต่อ กม.', compute='_compute_od19_mileage',
      store=True, currency_field='currency_id')
  ```
  > หมายเหตุ: `od19_mileage_vehicle_id` จะ compile ได้หลัง Task 2 สร้างโมเดล — ทำ Task 2 ก่อนหรือพร้อมกัน

- [ ] **Step 3: ลอจิกคำนวณ + บังคับไม่มี VAT**
  ```python
  @api.depends('od19_is_mileage', 'company_id')
  def _compute_od19_mileage(self):
      for expense in self:
          expense.od19_mileage_rate = (
              expense.company_id.od19_mileage_rate if expense.od19_is_mileage else 0.0)

  @api.onchange('od19_is_mileage', 'od19_mileage_distance_km', 'od19_mileage_rate')
  def _onchange_od19_mileage_amount(self):
      if self.od19_is_mileage:
          distance = self.od19_mileage_distance_km or 0.0
          rate = self.od19_mileage_rate or 0.0
          self.quantity = distance
          # ⚠️ price_unit เป็น readonly+computed ใน core → ตั้ง total_amount แทน
          # core จะคำนวณ price_unit = round(total_amount / quantity) = rate ให้เอง
          self.total_amount = distance * rate

  @api.constrains('od19_is_mileage', 'tax_ids')
  def _check_od19_mileage_has_no_tax(self):
      for expense in self:
          if expense.od19_is_mileage and expense.tax_ids:
              raise ValidationError(_(
                  'Mileage reimbursement cannot carry VAT. Please remove the taxes.'))
  ```
  และปรับ `_compute_tax_ids` ให้ `tax_ids = False` เมื่อ `od19_is_mileage` (เพิ่มเงื่อนไขคู่กับ payment certificate)

- [ ] **Step 4: เพิ่มกลุ่มฟิลด์ในฟอร์มใบเบิก**
  ใน `views/hr_expense_views.xml` ใต้ `<xpath expr="//sheet" position="inside">` เพิ่ม:
  ```xml
  <group string="ค่าเดินทาง / Mileage" col="4" invisible="not od19_is_mileage">
      <field name="od19_mileage_distance_km"/>
      <field name="od19_mileage_rate"/>
      <field name="od19_mileage_vehicle_id"/>
      <field name="od19_mileage_origin"/>
      <field name="od19_mileage_destination"/>
      <field name="od19_mileage_date"/>
      <field name="od19_mileage_vehicle_type" readonly="1"/>
      <field name="od19_mileage_plate" readonly="1"/>
  </group>
  ```
  และวาง `<field name="od19_is_mileage"/>` ไว้ในกลุ่มหลักของ sheet (ให้ติ๊กได้)

- [ ] **Step 5: ตรวจสอบ static**
  รัน: `python -m py_compile custom_addons/od19_hr_expense_enhanced/models/hr_expense.py custom_addons/od19_hr_expense_enhanced/models/res_company.py`
  Expected: exit 0

---

## Task 2: สมุดรถพนักงาน `od19.employee.vehicle` (`od19_hr_expense_enhanced`)

**Files:**
- Create: `custom_addons/od19_hr_expense_enhanced/models/od19_employee_vehicle.py`
- Create: `custom_addons/od19_hr_expense_enhanced/security/hr_expense_security.xml`
- Create: `custom_addons/od19_hr_expense_enhanced/views/od19_employee_vehicle_views.xml`
- Modify: `models/__init__.py`, `security/ir.model.access.csv`, `__manifest__.py`, `models/hr_expense.py`

- [ ] **Step 1: สร้างโมเดล**
  ```python
  class Od19EmployeeVehicle(models.Model):
      _name = 'od19.employee.vehicle'
      _description = 'Employee Vehicle Book'
      _order = 'od19_last_used_date desc, id desc'

      employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade',
                                    index=True, default=lambda s: s.env.user.employee_id)
      od19_vehicle_type = fields.Selection(
          [('car', 'Car / รถยนต์'), ('pickup', 'Pickup / กระบะ'),
           ('van', 'Van / ตู้'), ('motorcycle', 'Motorcycle / จักรยานยนต์'),
           ('other', 'Other / อื่น ๆ')], required=True, default='car')
      od19_plate_number = fields.Char(required=True)
      od19_last_used_date = fields.Date()
      active = fields.Boolean(default=True)

      _sql_constraints = [
          ('od19_vehicle_plate_uniq', 'unique(employee_id, od19_plate_number)',
           'This plate is already in the employee vehicle book.'),
      ]

      def name_get(self):
          return [(v.id, f"{v.od19_plate_number} ({dict(v._fields['od19_vehicle_type'].selection)[v.od19_vehicle_type]})") for v in self]
  ```

- [ ] **Step 2: เพิ่ม import + security + views + manifest**
  - `models/__init__.py`: เพิ่ม `from . import od19_employee_vehicle`
  - `security/ir.model.access.csv`: เพิ่ม ACL (`base.group_user` read/write/create/unlink) — ปลอดภัยขึ้นด้วย ir.rule
  - `security/hr_expense_security.xml` (ใหม่): ir.rule พนักงานเห็น/แก้เฉพาะรถที่ `employee_id` เป็นของตัวเอง (ใช้ `employee_id.user_id = user` หรือ `employee_id = user.employee_id`); ให้กลุ่ม HR/บัญชี (`hr_expense.group_hr_expense_manager`, `account.group_account_manager`) อ่านได้
  - `views/od19_employee_vehicle_views.xml` (ใหม่): list + form + `ir.actions.act_window` + `menuitem` "รถของฉัน"
  - `__manifest__.py`: เพิ่ม 2 ไฟล์เข้า `data` (security ก่อน views) และ bump version `19.0.1.2.0` → `19.0.1.3.0`

- [ ] **Step 3: autofill รถล่าสุด + snapshot**
  ใน `models/hr_expense.py`:
  ```python
  @api.onchange('od19_is_mileage', 'employee_id')
  def _onchange_od19_mileage_vehicle(self):
      for expense in self:
          if expense.od19_is_mileage and not expense.od19_mileage_vehicle_id and expense.employee_id:
              last = self.env['od19.employee.vehicle'].search(
                  [('employee_id', '=', expense.employee_id.id)], limit=1)
              expense.od19_mileage_vehicle_id = last

  @api.onchange('od19_mileage_vehicle_id')
  def _onchange_od19_mileage_vehicle_snapshot(self):
      for expense in self:
          v = expense.od19_mileage_vehicle_id
          expense.od19_mileage_vehicle_type = dict(v._fields['od19_vehicle_type'].selection).get(v.od19_vehicle_type) if v else False
          expense.od19_mileage_plate = v.od19_plate_number if v else False
  ```
  และใน `create()` เพิ่ม: ถ้า `od19_is_mileage` และมี `od19_mileage_vehicle_id` → อัปเดต `od19_last_used_date = od19_mileage_date or today` ของรถคันนั้น

- [ ] **Step 4: ตรวจสอบ static**
  รัน: `python -m py_compile custom_addons/od19_hr_expense_enhanced/models/od19_employee_vehicle.py custom_addons/od19_hr_expense_enhanced/models/hr_expense.py`
  Expected: exit 0
  ตรวจ XML well-formed ของไฟล์ views/security ใหม่

---

## Task 2B: หมวดค่าใช้จ่าย Mileage (`od19_hr_expense_enhanced`)

**เหตุผล:** wizard รู้ว่าเป็น Mileage จาก **ธงบนหมวดค่าใช้จ่าย** (C7) และกลไกคำนวณต้องใช้สินค้า **ไม่มีต้นทุน** (C8)

**Files:**
- Create: `models/product_template.py`, `views/product_template_views.xml`, `data/od19_expense_category_data.xml`
- Modify: `models/__init__.py`, `__manifest__.py`

- [ ] **Step 1: ธงบนสินค้า**
  ```python
  class ProductTemplate(models.Model):
      _inherit = 'product.template'

      od19_is_mileage_category = fields.Boolean(
          string='Mileage Category / หมวดค่าเดินทางตามระยะทาง',
          help='Tick when expenses of this category are reimbursed per kilometre.',
      )
  ```

- [ ] **Step 2: ช่องติ๊กในฟอร์มสินค้า**
  `views/product_template_views.xml` inherit `hr_expense.view_product_hr_expense_form` แล้ววาง `<field name="od19_is_mileage_category"/>` ต่อจาก `can_be_expensed` (ให้ติ๊กเฉพาะเมื่อ `can_be_expensed`)

- [ ] **Step 3: สินค้าหมวด Mileage (ราคาทุน 0)**
  `data/od19_expense_category_data.xml` (`noupdate="1"`) สร้าง `product.product`:
  ```xml
  <record id="od19_expense_product_mileage" model="product.product">
      <field name="name">ค่าเดินทางตามระยะทาง / Mileage</field>
      <field name="type">service</field>
      <field name="standard_price">0.0</field>
      <field name="uom_id" ref="uom.product_uom_km"/>
      <field name="default_code">MIL-KM</field>
      <field name="can_be_expensed" eval="True"/>
      <field name="od19_is_mileage_category" eval="True"/>
      <field name="sale_ok" eval="False"/>
      <field name="purchase_ok" eval="True"/>
      <field name="categ_id" ref="product.product_category_expenses"/>
  </record>
  ```

- [ ] **Step 4: bootstrap + static**
  - `models/__init__.py`: เพิ่ม `from . import product_template`
  - `__manifest__.py`: เพิ่ม `views/product_template_views.xml` (หลัง views อื่น) + `data/od19_expense_category_data.xml` (ท้ายสุด) และ bump version `19.0.1.3.0` → `19.0.1.4.0`
  - `python -m py_compile` + ตรวจ XML well-formed

---

## Task 3: โมดูลใหม่ `od19_hr_expense_portal` + Wizard ยื่นเบิก

**Files:**
- Create: `custom_addons/od19_hr_expense_portal/__manifest__.py`, `__init__.py`, `models/__init__.py`
- Create: `custom_addons/od19_hr_expense_portal/models/od19_expense_quick_create.py`
- Create: `custom_addons/od19_hr_expense_portal/views/hr_expense_quick_create_views.xml`
- Create: `custom_addons/od19_hr_expense_portal/security/ir.model.access.csv`

- [ ] **Step 1: manifest + bootstrap**
  `__manifest__.py`: `depends = ['hr_expense', 'od19_hr_expense_thai', 'mail']`, `version '19.0.1.0.0'`, `data` เรียง security → views; `application=False`
  `__init__.py`: `from . import models`; `models/__init__.py`: import wizard + hr_expense helper

- [ ] **Step 2: wizard (TransientModel) 4 ขั้น**
  ```python
  class Od19ExpenseQuickCreate(models.TransientModel):
      _name = 'od19.expense.quick.create'
      _description = 'Quick Expense Submission Wizard'

      expense_category_id = fields.Many2one('product.product', required=True,
          domain="[('can_be_expensed','=',True)]", string='Category / หมวดค่าใช้จ่าย')
      employee_id = fields.Many2one('hr.employee', required=True,
          default=lambda s: s.env.user.employee_id)
      expense_date = fields.Date(default=fields.Date.context_today, required=True)
      description = fields.Char()
      currency_id = fields.Many2one('res.currency', default=lambda s: s.env.company.currency_id.id)
      od19_is_mileage = fields.Boolean(compute='_compute_od19_is_mileage')   # C7: read-only from category
      amount = fields.Monetary(currency_field='currency_id')
      distance_km = fields.Float()
      vehicle_id = fields.Many2one('od19.employee.vehicle')
      origin = fields.Char(); destination = fields.Char()
      submit_now = fields.Boolean(default=True)

      @api.depends('expense_category_id')
      def _compute_od19_is_mileage(self):
          for wiz in self:
              wiz.od19_is_mileage = wiz.expense_category_id.od19_is_mileage_category

      def action_create_expense(self):
          # สร้าง hr.expense (draft): ตั้ง product_id/date/employee/description
          # - ถ้า Mileage: od19_is_mileage=True + ระยะทาง/รถ/ต้นทาง-ปลายทาง + quantity=กม. + total_amount=กม.×อัตรา (C6)
          # - ถ้าไม่ใช่: total_amount = amount
          # แล้ว submit ตาม submit_now (เรียก hr.expense.action_submit) และคืน action เปิดใบที่สร้าง
  ```
  > ⚠️ ใช้ `compute` (ไม่ใช่ `related`) เพื่อกันไม่ให้ wizard เขียนค่ากลับไปที่สินค้า; การแมปค่าลง `hr.expense` ทำใน `action_create_expense()` โดยอ้างผลลัพธ์เดียวกับ Task 1 (อย่าซ้ำลอจิกคำนวณ — ตั้ง `quantity`/`total_amount` แล้วให้ core คำนวณ `price_unit` เอง)

- [ ] **Step 3: views (ฟอร์ม wizard) + menu**
  ฟอร์ม 4 กลุ่ม: (1) หมวด/พนักงาน/วันที่ (2) จำนวนเงิน หรือ ระยะทาง+รถ (invisible ตาม `od19_is_mileage`) (3) ต้นทาง/ปลายทาง + รายละเอียด (4) `submit_now`
  เพิ่ม `ir.actions.act_window` (target=new) + `menuitem` "ยื่นใบเบิกค่าใช้จ่าย" ใต้เมนู HR Expense

- [ ] **Step 4: security**
  `security/ir.model.access.csv`: ให้ `base.group_user` read/write/create/unlink บน `od19.expense.quick.create`

- [ ] **Step 5: ตรวจสอบ static**
  รัน: `python -m py_compile` ทุกไฟล์ `.py` ใหม่; ตรวจ XML well-formed

---

## Task 4: Kanban "ใบเบิกของฉัน" (สถานะ + รอใคร)

**Files:**
- Create: `custom_addons/od19_hr_expense_portal/models/hr_expense.py`
- Create: `custom_addons/od19_hr_expense_portal/views/hr_expense_kanban_views.xml`
- Modify: `__manifest__.py` (เพิ่มไฟล์)

- [ ] **Step 1: helper ข้อความ "รอใคร" (guarded ตาม C1)**
  ```python
  class HrExpense(models.Model):
      _inherit = 'hr.expense'

      od19_approval_hint = fields.Char(compute='_compute_od19_approval_hint')

      @api.depends('state')
      def _compute_od19_approval_hint(self):
          has_tier = 'review_ids' in self.env['hr.expense']._fields
          for expense in self:
              if expense.state == 'submitted' and has_tier:
                  pending = expense.review_ids.filtered(lambda r: r.status == 'pending')
                  expense.od19_approval_hint = pending[:1].name or _('Waiting approval')
              else:
                  expense.od19_approval_hint = dict(expense._fields['state'].selection).get(expense.state, '')
  ```
  > ป้ายนี้จะสมบูรณ์เมื่อ Phase 1 merge (ฟิลด์ `review_ids` ปรากฏ) — ก่อนหน้านั้น fallback ตาม `state`

- [ ] **Step 2: Kanban view + action + menu**
  Kanban จัดกลุ่มตาม `state`, การ์ดแสดง `name`, `total_amount`, `employee_id`, `od19_approval_hint`
  `ir.actions.act_window`: `domain="[('employee_id.user_id','=',uid)]"`, `view_mode="kanban,list,form"`, context `{'search_default_my_expenses': 1}`
  `menuitem` "ใบเบิกของฉัน"

- [ ] **Step 3: ตรวจสอบ static**
  `python -m py_compile` + ตรวจ XML

---

## Task 5: เทสต์ (T9, T10, T11 + wizard)

**Files:**
- Create: `custom_addons/od19_hr_expense_enhanced/tests/test_mileage.py`
- Create: `custom_addons/od19_hr_expense_enhanced/tests/test_vehicle_book.py`
- Create: `custom_addons/od19_hr_expense_portal/tests/test_quick_create.py`
- Modify: `tests/__init__.py` ของทั้ง 2 โมดูล (**ห้ามทับ import เดิม**)

- [x] **Step 1: T9 Mileage amount (ใช้ `Form` เพื่อกระตุ้น onchange จริง)**
  company `od19_mileage_rate = 5.0`; เปิด `Form(self.env['hr.expense'])` ตั้ง `od19_is_mileage=True` แล้ว `od19_mileage_distance_km=20` → assert `quantity == 20`, `total_amount == 100.0`, `price_unit == 5.0`; แก้ระยะทางเป็น 30 → assert `total_amount == 150.0`
- [x] **Step 2: T10 Mileage ไม่มี VAT**
  assert `tax_ids` ว่างเมื่อ `od19_is_mileage`; และ `@constrains` โยน `ValidationError` ถ้าใส่ `tax_ids`
- [x] **Step 3: T11 สมุดรถ**
  สร้างรถ 2 คันของพนักงานคนเดียว (คันหนึ่ง `od19_last_used_date` ใหม่กว่า) → เปิดใบเบิก Mileage ใหม่ → `od19_mileage_vehicle_id` = คันล่าสุด; สร้างรถใหม่ผ่านใบเบิก → บันทึกเข้าสมุดรถ; ir.rule: พนักงานอื่นมองไม่เห็นรถเรา
- [x] **Step 4: wizard test**
  สร้างผ่าน wizard → ได้ `hr.expense` 1 ใบ, `state` ตาม `submit_now`, ค่ารวมถูกต้อง
- [ ] **Step 5: ให้ผู้ใช้รันเทสต์**
  ```powershell
  .\run-tests.ps1 -Module od19_hr_expense_enhanced
  .\run-tests.ps1 -Module od19_hr_expense_portal
  ```

---

## Task 6: อัปเดตเอกสาร/รีจิสทรี

- [x] อัปเดตสเปก §11 หากมีการเบี่ยงจากแผน (เช่น ชื่อฟิลด์จริง)
  → เพิ่มหัวข้อ **§11.1 บันทึก as-built (Phase 2)** และแก้กลไก Mileage ใน §15 (ใช้ `quantity` + `total_amount`; core คำนวณ `price_unit`)
- [x] หากมี tour/registry ที่อ้าง HR Expense อยู่ ให้ปรับข้อความให้ตรง (ถ้าเกี่ยวข้อง)
  → ตรวจแล้ว: `od19_user_guide_tours/.../hr_expense_tour.js` อ้าง flow อนุมัติ 2 ชั้นเดิม (`action_approve_first/second`) ซึ่งเป็นขอบเขตของ Phase 1 (คนละ branch) — **ไม่แก้ใน branch นี้** เพื่อไม่ให้ปนโดเมนงาน

---

## Final Verification

> **ผู้ใช้รันเอง** (AGENTS.md §6 ห้าม agent รัน Unit Test แทน)

1. รันเทสต์:
   ```powershell
   .\run-tests.ps1 -Module od19_hr_expense_enhanced
   .\run-tests.ps1 -Module od19_hr_expense_portal
   ```
2. Upgrade DB `odoo19_pdev`:
   ```powershell
   .\start-odoo19.bat
   # หรือ
   odoo-bin -u od19_hr_expense_enhanced,od19_hr_expense_portal --stop-after-init -c odoo.conf
   ```
3. ทดสอบมือผ่านหน้าเว็บ:
   - ตั้งค่าอัตรา Mileage ที่ Company → เปิด "ยื่นใบเบิกค่าใช้จ่าย" → เลือกหมวด Mileage → กรอกระยะทาง + เลือกรถ → ยอด = กม. × อัตรา
   - เพิ่มรถคันใหม่ → เปิดใบเบิกใหม่ → รถถูกเติมอัตโนมัติ (คันล่าสุด)
   - ตรวจ Kanban "ใบเบิกของฉัน" แสดงสถานะ
4. รายงานตาม AGENTS.md §7 (commit SHA, ไฟล์ที่แตะ, คำสั่งที่รัน, ผลจริง)

---

## Out of Scope (เฟสถัดไป)

- Phase 3: Portal `/my/expenses` (controller + QWeb + responsive), ir.rule ของ portal, timeline การอนุมัติ
- Phase 4: ปุ่มคำนวณระยะทางจากแผนที่ (optional), เก็บร่างกันเน็ตหลุด (offline-tolerant), รายงาน, i18n (`i18n/th.po`)
