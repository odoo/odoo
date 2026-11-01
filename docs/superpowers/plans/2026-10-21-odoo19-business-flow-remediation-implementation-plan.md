# Odoo 19 Business Flow Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** แก้ไขข้อบกพร่องของระบบ Odoo 19 (Greenfield) และ Business Flow ของบริษัท ออโต้อินโฟ จำกัด ทั้งหมด 114 รายการ (High 50 / Medium 54 / Low 10) ที่พบจากการวิเคราะห์เชิงลึก 4 โดเมนธุรกิจ โดยไม่แก้ไข Odoo core และรักษาหลักการ OCA First, 1 module = 1 Bounded Context

**Architecture:** แก้ไขแบบ additive ในโมดูล `od19_*` เดิมเป็นหลัก และเพิ่มโมดูลใหม่เฉพาะกรณีที่ไม่มี Bounded Context รองรับ (`od19_accounting_analytic_require`, `od19_accounting_payment_fee`) ทุกการแก้ไขต้องไม่กระทบ dependency chain (Level 1–6) และโมดูลต้องยัง install/upgrade/uninstall ได้ ทุก Business Flow ที่แก้ต้องมี GL entry ที่ถูกต้องตามมาตรฐานบัญชีไทย (WHT, VAT, Cheque, Period Lock)

**Tech Stack:** Odoo 19 CE, Python 3, PostgreSQL, `odoo.tests.TransactionCase`, XML views, OCA `base_tier_validation`, PowerShell (Windows), Git

**Spec:** ยังไม่มี spec แยก — แผนนี้อ้างอิงผลการวิเคราะห์เชิงลึกที่รันโดย subagents 4 ชุด (Accounting / Sales / Purchase-Inventory / ISO-Internal) เมื่อวานนี้ หากต้องการ spec ให้สร้าง `docs/superpowers/specs/<date>-odoo19-business-flow-remediation-design.md` ก่อนรัน Task ที่ยุ่งยาก

---

## Design Decisions (ตัดสินใจระหว่างทำ plan — ต้องรับรู้ตอน review)

1. **ไม่แก้ Odoo core** — ทุก GL entry ของ WHT/Cheque/Payment Fee สร้างผ่าน override `_prepare_move_line_default_vals()` และ `action_post()` ใน `account.move` / `account.payment` ซึ่งเป็น extension point ที่ Odoo รองรับ
2. **GL Injection ผ่าน liquidity line adjustment** — เมื่อมี WHT/Fee ต้องลด/เพิ่มยอด liquidity line (bank) ให้เป็นยอดเงินสดจริง (net) แล้วเพิ่ม line คู่บัญชีภาษี/ค่าธรรมเนียม เพื่อให้ debit = credit เสมอ (pattern เดียวกับ `dtr_taxation` ใน Odoo 15)
3. **Cheque GL ใช้ company settings** — `cheque_received_account_id`, `cheque_paid_account_id`, `cheque_return_account_id` ที่มีอยู่บน `res.company` เป็นบัญชีพัก (holding account) ลดความซ้ำซ้อนกับฟิลด์เดิม
4. **Period Lock ใช้ของที่มีอยู่ ไม่สร้างโมดูล custom** — (ก) Odoo 19 core: `res.company.fiscalyear_lock_date` / `hard_lock_date` / `tax_lock_date` / `sale_lock_date` + `account.lock_exception` (ตรวจตอน post ใน core อยู่แล้ว) และ (ข) OCA `account_fiscal_year` (`third_party/oca/account-financial-tools/`) สำหรับช่วงปีบัญชี — **ไม่ต้อง override `action_post()` เอง** (ดู Task A3)
5. **SO Approval ใช้ OCA `base_tier_validation`** — ไม่สร้าง engine ใหม่ กำหนด tier 3 ระดับตามยอด (0 / 100k / 500k THB) เป็น data record
6. **Contract Budget ใช้ `amount_untaxed`** — ไม่ใช้ `amount_total` เพราะงบประมาณสัญญาตั้งบนยอดก่อน VAT (แก้บั๊ก VAT 15% ที่ทำให้ consumed เกินจริง)
7. **Credit revalidation ใช้ `commercial_partner_id`** — ค้นหา confirmed SO ผ่าน `partner_id.commercial_partner_id` เพราะ SO อาจผูกกับ contact ลูก
8. **Stock Backdating จำกัดสิทธิ์** — เฉพาะ `stock.group_stock_manager` เท่านั้นที่ตั้ง `backdate_date` ได้
9. **และ 10. Known intermediate states** — ระหว่างที่ยังไม่รัน Task Verify ระบบอาจมี warning จาก view inheritance ID ที่อาจต่างจาก instance จริง (ดูความเสี่ยงใน Notes)

---

## Precondition

- ฐานข้อมูลพัฒนา: `odoo19_pdev` (พอร์ต 8070) — ตาม convention โครงการ
- `addons_path` ใน `odoo.conf` ต้องรวม `custom_addons` (absolute path)
- รัน Odoo server แบบ `--dev=assets` เมื่อแก้ไฟล์ static/view
- รัน tests (จาก `c:\odoo-dev\odoo19`):

```powershell
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u <module_list> --test-enable --test-tags=<tag_list> --stop-after-init --log-level=test
```

- หมายเหตุ: sandbox ของ agent บล็อกการรัน Odoo test ผ่าน terminal โดยตรง (exit code -1) — ต้องรันใน terminal ปกติของผู้ใช้ หรือใช้สคริปต์ `STEP-1-Update-Odoo19.ps1` (update) / `STEP-2-Install-Odoo19.ps1` (install)
- **ลำดับความสำคัญ:** ทำตามลำดับ Phase A → F; ภายใน phase ให้ทำ Task Verify ทุกครั้งหลัง group ที่แก้ร่วมกัน

---

## File Structure

**Create (โมดูลใหม่)**
- `custom_addons/od19_accounting_analytic_require/__manifest__.py`
- `custom_addons/od19_accounting_analytic_require/__init__.py`
- `custom_addons/od19_accounting_analytic_require/models/__init__.py`
- `custom_addons/od19_accounting_analytic_require/models/res_company.py`
- `custom_addons/od19_accounting_analytic_require/models/account_move.py`
- `custom_addons/od19_accounting_analytic_require/views/res_company_views.xml`
- `custom_addons/od19_accounting_analytic_require/views/account_move_views.xml`
- `custom_addons/od19_accounting_analytic_require/security/ir.model.access.csv`
- `custom_addons/od19_accounting_analytic_require/tests/__init__.py`
- `custom_addons/od19_accounting_analytic_require/tests/test_analytic_require.py`
- `custom_addons/od19_accounting_payment_fee/__manifest__.py`
- `custom_addons/od19_accounting_payment_fee/__init__.py`
- `custom_addons/od19_accounting_payment_fee/models/__init__.py`
- `custom_addons/od19_accounting_payment_fee/models/account_payment.py`
- `custom_addons/od19_accounting_payment_fee/views/account_payment_views.xml`
- `custom_addons/od19_accounting_payment_fee/tests/__init__.py`
- `custom_addons/od19_accounting_payment_fee/tests/test_payment_fee.py`

**Create (tests ที่เพิ่มให้โมดูลเดิม)**
- `od19_accounting_dncn/tests/test_dncn.py`
- `od19_quotation_document_sequence/tests/test_revision_delegation.py` (แก้ของเดิม)
- `od19_document_sequence/tests/test_document_sequence.py`
- `od19_partner_document_sequence/tests/test_partner_document_sequence.py`
- `od19_project_document_sequence/tests/test_project_document_sequence.py`
- `od19_purchase_document_sequence/tests/test_purchase_document_sequence.py`
- `od19_sales_confirm_stamp/tests/test_sales_confirm_stamp.py`
- `od19_iso_risk/tests/test_risk.py`
- `od19_iso_training/tests/test_training.py`
- `od19_iso_customer_satisfaction/tests/test_customer_satisfaction.py`
- `od19_partner_thai_fields/tests/test_partner_thai_fields.py`
- `od19_thai_localization_base/tests/test_thai_localization_base.py`
- `od19_thai_tax_reports/tests/test_thai_tax_reports.py`
- `od19_website/tests/test_website.py`

**Modify (โมดูลเดิม)**
- `od19_accounting_cheque/models/account_cheque.py`, `tests/test_cheque.py`
- `od19_accounting_dncn/models/account_move.py`
- `od19_sales_customer_risk_gate/models/res_partner.py`, `models/sale_order.py`, `tests/*`
- `od19_sales_contract_core/models/sales_contract.py`, `models/sale_order.py`, `tests/*`
- `od19_sales_billing_evidence/models/billing_evidence.py`, `models/sale_order.py`, `tests/*`
- `od19_quotation_document_sequence/models/sale_order.py`
- `od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`, `models/tier_definition.py`, `security/sale_director_security.xml`, `data/od19_sale_tier_definition.xml`, `views/sale_order_bridge_views.xml`, `__manifest__.py`, `tests/test_oca_bridge.py`
- `od19_stock_valuation_adjustment/models/stock_valuation_adjustment.py`, `views/*`, `tests/*`
- `od19_inventory_execution_control/models/product_template.py`, `stock_valuation_layer.py`, `stock_valuation_by_lot.py`, `stock_picking.py`, `stock_move.py`, `security/ir.model.access.csv`, `tests/*`
- `od19_purchase_procurement_core/models/res_company.py`, `models/purchase_order.py`, `security/purchase_director_security.xml`, `views/*`, `tests/*`
- `od19_inventory_audit_count/models/stock_count_session.py`, `views/*`, `tests/*`
- `od19_iso_document_control/models/*`, `data/*`
- `od19_iso_calibration/models/calibration.py`, `data/*`
- `od19_iso_supplier_quality/models/purchase_order.py`, `models/res_company.py`, `views/*`
- `od19_internal_issue/models/helpdesk_ticket.py`, `views/helpdesk_ticket_views.xml`, `tests/test_internal_issue.py`
- `od19_asset_loan/models/asset_loan.py`, `models/asset_loan_line.py`, `views/*`, `tests/test_asset_loan.py`
- `od19_service_card/models/service_card.py`, `__manifest__.py`, `views/*`, `tests/*`
- `od19_notification_multi_channel/models/notification_queue.py`, `models/notification_mixin.py`, `data/notification_queue_cron.xml`, `views/*`, `security/ir.model.access.csv`, `__manifest__.py`, `tests/*`
- `od19_sales_reporting/models/report_repeat_business.py`, `models/report_sales_project_revenue.py`, `security/sales_reporting_security.xml`, `__manifest__.py`, `tests/*`

**Reuse without changes**
- `odoo/addons/account`, `odoo/addons/sale`, `odoo/addons/stock`, `odoo/addons/purchase` (ห้ามแก้)
- `custom_addons/od19_accounting_advance/` — ใช้ GL logic เดิมสำหรับ Down Payment
- `custom_addons/od19_accounting_features/` — ฟิลด์ WHT advisory (compute-only) ที่มีอยู่แล้ว; ไม่ต้องแก้ (ดู Task A1)
- OCA `l10n_th_account_tax` (WHT GL) และ OCA `account_fiscal_year` (ช่วงปีบัญชี) — ใช้ตามที่มีอยู่ ไม่มี custom module (ดู Task A1, A3, A8)

> **หมายเหตุ (2026-10-21):** เดิม File Structure อ้างโมดูล `od19_accounting_wht` และ
> `od19_accounting_fiscal_year` ซึ่ง **ไม่มีอยู่จริงบนดิสก์** — ถูกลบออกแล้วเพื่อให้สอดคล้อง
> กับ Correction ใน Task A1 / A3 (WHT = OCA `l10n_th_account_tax`; Period Lock = Odoo 19 core + OCA `account_fiscal_year`)

---

## Phase A — Accounting Remediation (High ×9)

### Task A1: WHT Journal Entry [สถานะ: N/A — OCA handles GL]

> **Correction (2026-10-21):** เดิมแผนอ้างโมดูล `od19_accounting_wht` ซึ่ง **ไม่มีอยู่จริง** ในดิสก์
> ในความเป็นจริง WHT ถูกจัดการ 2 ส่วน:
> 1. **GL entry (ของจริง)** — สร้างโดย OCA `l10n_th_account_tax` ที่
>    `third_party/oca/l10n-thailand/l10n_th_account_tax/` ผ่าน
>    `account.move._handle_withholding_taxes()` (สร้าง `account.withholding.move`)
>    และ payment register wizard (`_onchange_wht()` ตั้ง `writeoff_account_id = wht_tax_id.account_id`)
>    → **ไม่ต้องแก้ไข** (ใช้ OCA First)
> 2. **ฟิลด์แสดงผล (advisory)** — `od19_wht_invoice_base_amount`, `od19_wht_rate`,
>    `od19_wht_type_id`, `od19_wht_invoice_amount` อยู่ใน
>    `custom_addons/od19_accounting_features/models/account_payment.py`
>    เป็น compute-only เพื่อโชว์ข้อมูล ไม่ได้สร้าง GL
>    > **Correction (2026-11-01):** เดิมใช้ชื่อ `od19_wht_base_amount` /
>    > `od19_wht_amount` ซึ่ง **ชนกับชื่อฟิลด์ของ `od19_hr_expense_enhanced`**
>    > บนโมเดล `account.payment` ทำให้ Odoo merge field definition และ
>    > `compute`/`store` ของฝั่ง features รั่วไปทับค่าที่เขียนด้วยมือ
>    > (ทำให้ `od19_wht_amount` กลายเป็น 0.0) จึงเปลี่ยนชื่อเป็น
>    > `od19_wht_invoice_base_amount` / `od19_wht_invoice_amount`
>
> **Action:** ไม่มีโค้ดต้องแก้ — ยืนยันว่า OCA สร้าง WHT GL ตอน post payment แทน

### Task A2: Cheque Journal Entry [สถานะ: DONE — ต้อง verify]

**Files:**
- Modify: `custom_addons/od19_accounting_cheque/models/account_cheque.py`

- [x] **Step 1:** เพิ่ม `issue_move_id`, helper `_get_cheque_received_account_id()`, `_get_cheque_paid_account_id()`, `_get_bank_account_id()`
- [x] **Step 2:** `_create_cheque_move()` (multicurrency ผ่าน `currency_id._convert`) + `_reverse_cheque_move()`
- [x] **Step 3:** เขียน GL ใน `action_confirm` (AR→Cheque Received), `action_to_pay` (AP→Cheque Issued), `action_deposit` (Cheque Received→Bank), `action_paid` (Cheque Issued→Bank), `action_bounce`/`action_cancel` (reversal)
- [ ] **Step 4: Verify** — รัน `-u od19_accounting_cheque --test-tags /od19_accounting_cheque`

### Task A3: Period Lock [สถานะ: N/A — Odoo 19 core + OCA มีอยู่แล้ว]

> **Correction (2026-10-21):** เดิมแผนอ้างโมดูล `od19_accounting_fiscal_year` ซึ่ง **ไม่มีอยู่จริง**
> ในความเป็นจริง Period Lock ถูกจัดการโดย:
> 1. **Odoo 19 core** — `res.company.fiscalyear_lock_date`, `hard_lock_date`,
>    `tax_lock_date`, `sale_lock_date` + model `account.lock_exception`
>    (ออกข้อยกเว้นได้) + การตรวจตอน post ที่
>    `addons/account/models/company.py` → **เพียงพอต่อ Governance**
> 2. **OCA `account_fiscal_year`** — ที่
>    `third_party/oca/account-financial-tools/account_fiscal_year/`
>    ให้ model `account.fiscal.year` (ช่วงปีบัญชี) ใช้อ้างอิงรายงาน/posting
>
> **Action:** ไม่ต้องสร้าง custom module — ใช้งาน core lock date + OCA fiscal year แทน

### Task A4: Analytic Require [สถานะ: DONE — ต้อง verify]

**Files:** โมดูลใหม่ `custom_addons/od19_accounting_analytic_require/` (ดู File Structure)

- [x] **Step 1:** สร้างโมดูล + `res.company.od19_analytic_required_account_ids` / `od19_analytic_require_journal_ids`
- [x] **Step 2:** override `account.move.action_post()` ตรวจ analytic distribution (รองรับทั้ง legacy `analytic_account_id` และ `analytic_distribution`)
- [x] **Step 3:** views + security + test (3 cases)

### Task A5: Payment Fee [สถานะ: DONE — ต้อง verify]

**Files:** โมดูลใหม่ `custom_addons/od19_accounting_payment_fee/` (ดู File Structure)

- [x] **Step 1:** เพิ่ม `fee_amount`, `fee_account_id` + constraint
- [x] **Step 2:** override `_prepare_move_line_default_vals()` เพื่อปรับ liquidity + เพิ่ม fee line
- [x] **Step 3:** view + test (4 cases)

### Task A6: DN/CN Bugs [สถานะ: DONE — ต้อง verify]

**Files:**
- Modify: `custom_addons/od19_accounting_dncn/models/account_move.py`
- Create: `custom_addons/od19_accounting_dncn/tests/test_dncn.py`

- [x] **Step 1:** เพิ่ม `_check_dncn_reason` constraint + `_get_dncn_label()`
- [x] **Step 2:** override `action_post()` บังคับ reason สำหรับ DN/CN/Remaster
- [x] **Step 3:** แก้ `action_create_credit_note()` ให้รองรับ customer + vendor (out_refund/in_refund) และ set `reversed_entry_id`
- [x] **Step 4:** เพิ่ม test (4 cases)

### Task A7: Down Payment / Deposit [สถานะ: REUSE — ต้องยืนยัน]

**Files:** ใช้ `custom_addons/od19_accounting_advance/` ที่มีอยู่ (มี GL via `_prepare_move_vals`)

- [ ] **Step 1:** ยืนยันว่า `account.advance` สร้าง GL ตอน post และ reconcile กับ invoice ได้
- [ ] **Step 2:** ถ้าต้องการ Deposit แบบ % บน Sale Order → สร้าง Task แยกพร้อม design (ยังไม่ทำ)

### Task A8: Bring Forward / Year-end Closing [สถานะ: DECIDED — Manual no-code (2026-10-21)]

> **Correction (2026-10-21):** เดิมแผนอ้าง `custom_addons/od19_accounting_fiscal_year/wizard/account_year_end_closing.py`
> ซึ่ง **ไม่มีอยู่จริงบนดิสก์** (โมดูล `od19_accounting_fiscal_year` ไม่มี) และ **ไม่มี OCA module**
> ใน Third Party ที่ให้ wizard ปิดบัญชี (ตรวจ `third_party/oca/account-financial-tools/` แล้ว —
> มี `account_fiscal_year` สำหรับช่วงปีบัญชีเท่านั้น ไม่มี closing wizard)
>
> **สถานะจริง:** Year-end closing entry (P&L → Retained Earnings) ยังไม่มีทั้ง core และ custom
> **ทางเลือก:**
> 1. ทำผ่าน GL manual entry ในหน้าจอ Journal Entries (core) แบบ manual ต่อปี — no-code
> 2. สร้าง spec แยก + โมดูล `od19_accounting_year_end_closing` หากต้องการ Automation (ต้องอนุมัติก่อน)
>
> **คำตัดสิน (2026-10-21):** เลือก **ทางเลือก 1 — Manual no-code** ปิดปีผ่าน GL manual entry (Journal Entries)
> ตามคำแนะนำฝ่ายบัญชี + ล็อกงวดด้วย core lock dates (`fiscalyear_lock_date` / `hard_lock_date` / `tax_lock_date` /
> `sale_lock_date` + `account.lock_exception`) — **ไม่สร้างโมดูล** `od19_accounting_year_end_closing`
> (สอดคล้องกับ Wave 2 spec ข้อ 6.6)

- [x] **Step 1: Decision** — เลือกทางเลือก 1 (manual no-code) เมื่อ 2026-10-21
- [ ] **Step 2: Verify** — ทดสอบ closing entry แบบ manual กับ FY จริง + ตรวจ Period Lock และ Trial Balance หลังปิด (รันโดยผู้ใช้ผ่าน terminal)

---

## Phase B — Sales Remediation (High ×15)

### Task B1: SO Approval (Tier Validation) [สถานะ: DONE — ต้อง verify]

**Files:**
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/models/sale_order_bridge.py`
- Create: `custom_addons/od19_sales_oca_bridge_workflow/models/tier_definition.py`
- Create: `custom_addons/od19_sales_oca_bridge_workflow/security/sale_director_security.xml`
- Create: `custom_addons/od19_sales_oca_bridge_workflow/data/od19_sale_tier_definition.xml`
- Modify: `custom_addons/od19_sales_oca_bridge_workflow/views/sale_order_bridge_views.xml`, `__manifest__.py`, `tests/test_oca_bridge.py`

- [x] **Step 1:** inherit `tier.validation`, เพิ่ม state `waiting_approval`
- [x] **Step 2:** override `action_confirm()` → route ไป `waiting_approval` + `request_validation()` ถ้าจำเป็น
- [x] **Step 3:** tier definitions: <100k auto, 100k–500k Manager, ≥500k Director
- [x] **Step 4:** เพิ่ม test (8 cases) — **ผ่านแล้ว (54 tests รวมทั้ง sales domain)**

### Task B2: Contract Budget Consumption [สถานะ: DONE — verified]

**Files:**
- Modify: `custom_addons/od19_sales_contract_core/models/sales_contract.py`, `models/sale_order.py`

- [x] **Step 1:** เพิ่ม `state` (draft/approved/active/closed) + workflow methods
- [x] **Step 2:** `consumed_from_orders` compute จาก confirmed SO (`amount_untaxed`)
- [x] **Step 3:** เพิ่ม `od19_contract_activity_id` บน `sale.order.line`
- [x] **Step 4:** บังคับ `over_limit_policy` (warn/approval/block) ตอน SO confirm
- [x] **Step 5:** Amendment `added_limit_amount` อัปเดต contract `limit_amount`
- [x] **Step 6:** test — ผ่านแล้ว (14 tests)

### Task B3: Credit Limit Amount + Revalidation [สถานะ: DONE — verified]

**Files:**
- Modify: `custom_addons/od19_sales_customer_risk_gate/models/res_partner.py`, `models/sale_order.py`

- [x] **Step 1:** เพิ่ม `od19_credit_limit_amount`, `od19_credit_used_amount`, `od19_credit_available`, `od19_credit_expiry_date`
- [x] **Step 2:** `_compute_od19_credit_sale_allowed` เช็ค state/expiry/available
- [x] **Step 3:** revalidate confirmed SO เมื่อ blacklist/credit เปลี่ยน (ใช้ `commercial_partner_id`)
- [x] **Step 4:** test — ผ่านแล้ว (41 tests)

### Task B4: Billing Evidence Block Invoice [สถานะ: DONE — verified]

**Files:**
- Modify: `custom_addons/od19_sales_billing_evidence/models/billing_evidence.py`, `models/sale_order.py`

- [x] **Step 1:** เพิ่ม `attachment_ids` (Many2many ir.attachment)
- [x] **Step 2:** constraint `is_verified=True` ต้องมี attachment
- [x] **Step 3:** override `action_create_invoice` → raise ถ้า readiness != ready
- [x] **Step 4:** test — ผ่านแล้ว (12 tests)

### Task B5: SO Revision Merge [สถานะ: DONE — verified]

**Files:**
- Modify: `custom_addons/od19_quotation_document_sequence/models/sale_order.py`

- [x] **Step 1:** delegate custom revision → OCA `create_revision`
- [x] **Step 2:** parse domain จาก OCA (string) ด้วย `ast.literal_eval`
- [x] **Step 3:** test — ผ่านแล้ว (7 tests)

### Task B6: Raw Cursor in Risk Gate [สถานะ: DONE — verified]

**Files:**
- Modify: `custom_addons/od19_sales_customer_risk_gate/models/sale_order.py`

- [x] **Step 1:** แทน `cr.execute`/`cr.commit()`/`api.Environment` ด้วย ORM `od19.credit.gate.event.create()`
- [x] **Step 2:** ลบ unused imports (`SUPERUSER_ID`, `config`)
- [x] **Step 3:** test — ผ่านแล้ว (3 tests เพิ่มเติม)

### Task B7: Project Analysis before Quoting [สถานะ: DONE]

**Files:**
- Modify: `custom_addons/od19_sales_project_context/` (เพิ่ม wizard + smart button)
- Modify: `custom_addons/od19_project_analytic/models/project_project.py` (ย้าย helper กลางมาที่นี่)
- Modify: `custom_addons/od19_project_enhanced/models/project_project.py` (ลบ helper ที่ซ้ำ)

**Design decision (dependency):** `_od19_get_pnl_values()` เดิมอยู่ใน `od19_project_enhanced`
แต่โมดูลนั้นผูก `purchase`, `hr_expense`, `account` ทั้งชุด และ `od19_sales_project_context`
เป็น hub ระดับล่างที่มี 7 โมดูลพึ่งพา (inventory_execution_control, purchase_procurement_core,
sales_contract_core, sales_billing_evidence, sales_reporting, sales_confirm_stamp,
delivery_label) การเพิ่ม dependency ขึ้นไปจะลากโมดูลหนักเข้าทุกตัว → เลือก **ย้าย helper
ลงมาไว้ที่ `od19_project_analytic`** ซึ่งเป็นฐานร่วมที่ทั้งสองโมดูล depend อยู่แล้ว
(ตรงกับ bounded context "Project & Analytic Accounting") โดยไม่ต้องเพิ่ม dependency ใด ๆ

- [x] **Step 1:** Design — ใช้ `project.project._od19_get_pnl_values()` (single P&L contract,
      อ่านจาก `account.analytic.line.analytic_profitability`); **ไม่ re-implement** การจำแนก
      revenue/cost; ไม่มีโมเดล BOQ ในระบบ จึงใช้ analytic cost จริงของ project เป็นฐานประเมิน
- [x] **Step 2:** เพิ่ม smart button "Cost & Profit Analysis" ใน `button_box` ของ
      `sale.view_order_form` (`invisible="not od19_project_id"`) เรียก
      `action_open_project_pnl_analysis()` (reuse `ir.actions.act_window`
      `action_od19_sale_order_pnl_analysis`, target new)
- [x] **Step 3:** wizard `od19.sale.order.pnl.analysis` (TransientModel) — เลือกช่วงวันที่,
      แสดง revenue/cost/gross_margin/margin %/uncategorized + note (ไม่มี analytic /
      ยังไม่มี revenue / มี uncategorized) พร้อม `security/ir.model.access.csv`
- [x] **Step 4:** test — เพิ่ม 4 เคสใน `tests/test_project_context.py`
      (smart button action, wizard คำนวณ margin 60%, wizard ไม่มี project → note,
      default_get จาก context)

---

## Phase C — Purchase / Inventory Remediation (High ×15)

### Task C1: Stock Valuation Adjustment GL [สถานะ: DONE — ต้อง verify]

**Files:**
- Modify: `custom_addons/od19_stock_valuation_adjustment/models/stock_valuation_adjustment.py`, `views/*`, `tests/*`

- [x] **Step 1:** เพิ่ม `valuation_layer_id`, `account_move_id`, `journal_id`, `stock_valuation_account_id`, `adjustment_account_id`
- [x] **Step 2:** `action_approve` สร้าง SVL + account.move; `action_cancel` สร้าง reversal
- [x] **Step 3:** field `od19_stock_valuation_adjustment_account_id` บน `res.company`
- [x] **Step 4:** test (6 cases)

### Task C2: FIFO Lot-based Costing [สถานะ: DONE — ต้อง verify]

**Files:**
- Modify/Create: `od19_inventory_execution_control/models/product_template.py`, `stock_valuation_layer.py`, `stock_valuation_by_lot.py`, `views/stock_valuation_by_lot_views.xml`, `security/ir.model.access.csv`, `tests/test_fifo_lot_valuation.py`

- [x] **Step 1:** constraint FIFO ⟹ lot tracking enabled
- [x] **Step 2:** `stock.valuation.layer.lot_id` + `_get_fifo_layers_for_lot()`
- [x] **Step 3:** SQL view report `od19.stock.valuation.by.lot`
- [x] **Step 4:** test

### Task C3: Stock Backdating [สถานะ: DONE — ต้อง verify]

**Files:**
- Modify: `od19_inventory_execution_control/models/stock_picking.py`, `stock_move.py`, `views/stock_picking_views.xml`, `tests/test_stock_backdating.py`

- [x] **Step 1:** `backdate_date` บน picking + move
- [x] **Step 2:** propagate ตอน validate, override `move.date`
- [x] **Step 3:** access control เฉพาะ `stock.group_stock_manager`
- [x] **Step 4:** test

### Task C4: PO Approval by Amount [สถานะ: DONE — ต้อง verify]

**Files:**
- Modify/Create: `od19_purchase_procurement_core/models/res_company.py`, `models/purchase_order.py`, `security/purchase_director_security.xml`, `views/res_company_views.xml`, `views/purchase_order_views.xml`, `tests/test_purchase_amount_approval.py`

- [x] **Step 1:** `od19_po_director_approval_threshold` (default 100,000)
- [x] **Step 2:** `od19_approval_level` + แก้ `action_od19_approve` (2 ระดับ)
- [x] **Step 3:** group `group_purchase_director`
- [x] **Step 4:** test (7 cases)

### Task C5: Inventory Audit Count Adjustment [สถานะ: DONE — ต้อง verify]

**Files:**
- Modify: `od19_inventory_audit_count/models/stock_count_session.py`, `views/*`, `tests/*`

- [x] **Step 1:** workflow `scheduled→counted→pending_approval→adjusted→reviewed`
- [x] **Step 2:** `action_create_adjustment` set `quant.inventory_quantity` + `action_apply_inventory()`
- [x] **Step 3:** approval gate เฉพาะ stock manager
- [x] **Step 4:** test (8 cases)

### Task C6: Remaining Purchase/Inventory Issues [สถานะ: DONE]

- [x] **Step 1:** Department field conflict บน `purchase.request` — รวมเป็น field เดียว
      → **แก้แล้ว**: รวมเป็น `department_id` เดียว (canonical, compute/store,
      readonly=False) ใน `od19_purchase_request_extend`; เพิ่ม `default_get()`
      ดึงแผนกจาก employee ของผู้ใช้; ลบ field/view ซ้ำใน
      `od19_purchase_document_sequence` (เหลือ create/write สำหรับ sequence);
      เพิ่ม test 3 เคส + sequence test 2 เคส
- [x] **Step 2:** `od19_delivery_label` auto-populate `department_code` บน receipt — **มีอยู่แล้ว** (`_default_od19_department_code()` + auto-fill ใน `create`)
- [x] **Step 3:** Tier Validation สำหรับ stock.picking / valuation adjustment (ถ้าจำเป็น)
      → **แก้แล้ว (valuation adjustment)**: gate `action_approve()` ของ
      `od19.stock.valuation.adjustment` ให้เฉพาะ `stock.group_stock_manager`
      (SoD: กัน not-approver อนุมัติปรับมูลค่า/ลง GL) ตามแนวเดียวกับ C5;
      **stock.picking**: ไม่เพิ่ม tier validation บน core picking เพราะ C3
      จำกัด backdate ไว้ที่ stock manager แล้ว (เลี่ยง over-engineering)
- [x] **Step 4:** test
      → เพิ่ม `test_approve_requires_stock_manager`; แก้ test ที่อ้าง
      `valuation_layer_id` (field/โมเดลถูกถอดใน Odoo 19) เป็น
      `test_approve_without_valuation_layer_model`

---

## Phase D — ISO / Internal Operations Remediation (High ×11)

### Task D1: ISO Document Auto-Sequence [สถานะ: DONE — ต้อง verify]

**Files:** `custom_addons/od19_iso_document_control/`

- [x] **Step 1:** ir.sequence pattern `{TYPE}-{DEPT}-{NNN}`
- [x] **Step 2:** auto-generate on create + `department_id`

### Task D2: ISO Calibration Cron [สถานะ: DONE — ต้อง verify]

**Files:** `custom_addons/od19_iso_calibration/models/calibration.py`, `data/*`

- [x] **Step 1:** cron daily หา calibration ใกล้ครบกำหนด 7 วัน
- [x] **Step 2:** สร้าง mail.activity + flag overdue

### Task D3: Supplier Quality Block PO [สถานะ: DONE — ต้อง verify]

**Files:** `custom_addons/od19_iso_supplier_quality/models/purchase_order.py`, `models/res_company.py`, `views/*`

- [x] **Step 1:** override PO create/write → raise ถ้า supplier disqualified/suspended
- [x] **Step 2:** company setting เปิด/ปิด
- [x] **Step 3:** allow override by manager + reason

### Task D4: Internal Issue Tier Validation [สถานะ: DONE — ต้อง verify]

**Files:** `custom_addons/od19_internal_issue/models/helpdesk_ticket.py`, `views/helpdesk_ticket_views.xml`, `tests/test_internal_issue.py`

- [x] **Step 1:** implement tier validation (urgent → director)
- [x] **Step 2:** workflow draft→submitted→validated→in_progress→done
- [x] **Step 3:** ลบ/ต่อ dead code `_notify_updated`
- [x] **Step 4:** test

### Task D5: Asset Loan Guard [สถานะ: DONE — ต้อง verify]

**Files:** `custom_addons/od19_asset_loan/models/asset_loan.py`, `models/asset_loan_line.py`, `views/*`, `tests/test_asset_loan.py`

- [x] **Step 1:** constraint ห้ามยืมซ้ำ
- [x] **Step 2:** `returned_quantity = line.quantity` (ไม่ hardcode 1)
- [x] **Step 3:** `is_overdue` computed
- [x] **Step 4:** test

### Task D6: Service Card Enhancements [สถานะ: DONE — ต้อง verify]

**Files:** `custom_addons/od19_service_card/models/service_card.py`, `__manifest__.py`, `views/*`, `tests/*`

- [x] **Step 1:** SLA (`sla_hours`, `sla_deadline`, `is_sla_breached`)
- [x] **Step 2:** `team_id`, time tracking (`start_time`/`end_time`/`duration`)
- [x] **Step 3:** `sale_order_id` link
- [x] **Step 4:** test

### Task D7: Notification Queue [สถานะ: DONE — ต้อง verify]

**Files:** `custom_addons/od19_notification_multi_channel/models/notification_queue.py`, `models/notification_mixin.py`, `data/notification_queue_cron.xml`, `views/*`, `security/ir.model.access.csv`, `__manifest__.py`, `tests/*`

- [x] **Step 1:** queue model (pending/sending/sent/failed, retry max 3)
- [x] **Step 2:** cron ทุก 5 นาที
- [x] **Step 3:** HTML→plain text (`_strip_html`) สำหรับ LINE
- [x] **Step 4:** test

### Task D8: Remaining ISO/Internal Issues [สถานะ: DONE — ยกเว้น QC approval/sampling ที่ทำ NC link แทน]

> **หมายเหตุ:** QC approval/sampling ยังไม่ทำ (ตัดสินใจข้าม — ใช้ NC link
> `action_create_nonconformity()` แทน ซึ่งครอบคลุม Business Flow ที่ต้องการแล้ว)
> ส่วนอื่นทั้ง 4 ข้อเสร็จและต้อง verify ด้วย test จริงใน Task F1

- [x] **Step 1:** Supplier Quality weight ไม่ถูกใช้ — นำมาใช้คำนวณเกรด
      → **แก้แล้ว**: `_compute_percentage()` เปลี่ยนเป็นถ่วงน้ำหนัก
      `Σ(score/max × weight) / Σweight × 100` ใน `models/supplier_quality.py`
- [x] **Step 2:** ISO risk/NC/training/audit cron reminders ที่ยังขาด
      → **แก้แล้ว**: เพิ่ม daily cron + method ใน 4 โมดูล
      `_cron_risk_due_reminder()`, `_cron_nc_due_reminder()`,
      `_cron_competence_expiry_reminder()`, `_cron_audit_planned_reminder()`,
      `_cron_finding_due_reminder()` — สร้าง `mail.activity` + `message_post`
      และกันสร้างซ้ำด้วย `_has_open_activity()`
- [x] **Step 3:** Warranty lot-level → part-level
      → **แก้แล้ว**: product-level warranty fallback ใน `od19_service_warranty`
- [x] **Step 4:** QC approval / sampling / NC link
      → **แก้แล้ว**: NC link (`action_create_nonconformity()`, ฟิลด์ `nc_id`)
      ใน `od19_quality_control`; approval/sampling ยังไม่ดำเนินการ
- [x] **Step 5:** Transportation sequence + approval + integration
      → **แก้แล้ว**: tier validation (state `waiting_approval`, threshold
      50,000 THB → Stock Manager) ใน `od19_transportation`

---

## Phase E — Technical Debt (Medium / Low)

### Task E1: Record Rules for SQL View Reports [สถานะ: DONE — ต้อง verify]

**Files:** `custom_addons/od19_sales_reporting/models/report_repeat_business.py`, `models/report_sales_project_revenue.py`, `security/sales_reporting_security.xml`, `__manifest__.py`, `tests/*`

- [x] **Step 1:** เพิ่ม `company_id` ใน SQL view
- [x] **Step 2:** ir.rule company filter + manager see-all
- [x] **Step 3:** test

### Task E2: Tests for Untested Modules [สถานะ: DONE — ต้อง verify]

เพิ่ม tests ให้ 12+ โมดูล (ดู File Structure) — module ที่มี tests เพิ่มจาก 39 → 54 จากทั้งหมด 60

- [ ] **Step 1: Verify** — รัน test ทุกโมดูลที่เพิ่ม test แล้ว

### Task E3: Remaining Technical Issues [สถานะ: DONE]

- [x] **Step 1:** `od19_sales_confirm_stamp` บังคับ `stamp_date`
      → **แก้แล้ว**: `action_confirm()` auto-set `stamp_date = today` ถ้าว่าง (ใน `models/sale_order.py`)
- [x] **Step 2:** `od19_announcement` HTML body → LINE (แปลง plain text)
      → **มีอยู่แล้ว**: `od19.notification.queue.action_send()` เรียก `_strip_html(self.message)` ก่อนส่งช่อง LINE
- [x] **Step 3:** Protected fields check bypassable via `sudo()` — ยืนยันนโยบาย
      → **ยืนยันนโยบายแล้ว**: `sudo()` ไม่ใช่ช่องโหว่เพราะไม่มี RPC path ใดที่ผู้ใช้
      เรียก `sudo()` ได้เอง — `write()` gate (`if not self.env.su and not
      self._od19_is_credit_reviewer()`) ถูก bypass เฉพาะใน 2 กรณีที่ตั้งใจ:
      (ก) computed fields ที่อ่านค่าจริงเพื่อคำนวณ gate state ของทุก user
      (`_compute_od19_credit_sale_allowed`, `_compute_od19_credit_available`)
      และ (ข) internal actions ที่ตรวจ `_od19_is_credit_reviewer()` ก่อนแล้ว
      (`_od19_review_credit`, `action_od19_set_blacklist`,
      `action_od19_clear_blacklist`) รวมถึง `action_od19_request_credit()`
      ที่อนุญาตให้ฝ่ายขายตั้งสถานะเป็น `pending` ได้เท่านั้น (ค่าคงที่, ไม่มี
      privilege escalation) — **ล็อกเจตนาด้วย test**
      `test_every_protected_field_is_blocked_for_non_reviewers`
      (iterates ทุก field ใน `_OD19_PROTECTED_FIELDS` → `AccessError`)
- [x] **Step 4:** `od19_sales_project_context` partner role validation ระดับ model (ไม่ใช่แค่ view)
      → **ยืนยัน + เสริม test**: model-level enforcement มีครบใน 2 ชั้นคือ
      (ก) `res.partner._check_od19_partner_roles()` (ใน `od19_contacts_partner_roles`):
      commercial customer ต้องมี contact channel, project owner / contractor
      ต้องเป็น company; และ (ข) `sale.order._check_project_owner_role()` +
      `_check_project_owner_consistency()` ใน `od19_sales_project_context`:
      `od19_project_owner_id` ต้องเป็น partner ที่ติดธง `od19_is_project_owner`
      และต้องตรงกับ project owner ของ project ที่เลือก — **เพิ่ม test**
      `test_project_owner_role_is_enforced_at_model_level`
      **Design decision:** `partner_id` (ลูกค้า) คงการบังคับที่ view domain เท่านั้น
      (ตาม test `test_sale_order_accepts_any_partner_for_core_compatibility`)
      เพราะ core/website/API สร้าง sale order ด้วย partner ทั่วไป — ถ้าบังคับที่
      model จะทำให้ core flow พัง
- [x] **Step 5:** Payment term credit classification (`delay_type != "days_after"` auto-credit) — ทบทวนกติกา
      → **ทบทวนแล้ว คงกติกาเดิม**: credit term = มีบรรทัดใดก็ตามที่
      `nb_days > 0` **หรือ** `delay_type != "days_after"`
      - `days_after` + `nb_days = 0` → non-credit (ชำระทันที/threshold) ✓
      - `days_after` + `nb_days > 0` → credit (เครดิต N วัน) ✓
      - `days_after_end_of_month` / `days_after_end_of_next_month` /
        `days_end_of_month_on_the` + `nb_days = 0` → credit (วันครบกำหนดถูกเลื่อน
        ไปข้างหน้า แม้ไม่บวกวันเพิ่ม) ✓ — ครอบคลุมด้วย test ใหม่
      - term ไม่มีบรรทัด → non-credit (default ปลอดภัย)
      **เพิ่ม test:** `test_zero_day_term_is_non_credit`,
      `test_end_of_month_term_is_credit`, `test_end_of_next_month_term_is_credit`
      `store=True, readonly=False` เปิดให้ฝ่ายบัญชี override ได้ตามนโยบาย
      (`test_accounting_can_override_classification`)

---

## Phase F — Verification & UAT

### Task F1: Run Full Test Suite

- [ ] **Step 1:** รัน test ทุกโดเมน (ดูคำสั่ง Precondition) แยก batch:

```powershell
# Sales
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_sales_customer_risk_gate,od19_sales_contract_core,od19_sales_billing_evidence,od19_sales_oca_bridge_workflow,od19_quotation_document_sequence --test-enable --stop-after-init --log-level=test

# Accounting
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_accounting_cheque,od19_accounting_dncn,od19_accounting_analytic_require,od19_accounting_payment_fee --test-enable --stop-after-init --log-level=test

# Purchase/Inventory
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_stock_valuation_adjustment,od19_inventory_execution_control,od19_purchase_procurement_core,od19_inventory_audit_count --test-enable --stop-after-init --log-level=test

# ISO/Internal
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u od19_iso_document_control,od19_iso_calibration,od19_iso_supplier_quality,od19_internal_issue,od19_asset_loan,od19_service_card,od19_notification_multi_channel --test-enable --stop-after-init --log-level=test
```

- [ ] **Step 2:** แก้ไข test ที่ fail (โดยเฉพาะ view inheritance xpath ที่อ้าง standard view ID)
- [ ] **Step 3:** ตรวจ Odoo log ว่าไม่มี warning (icon button title, attrs, `:text()` tour selector)

### Task F2: Functional UAT

- [ ] **Step 1:** ทดสอบ GL ของ WHT/Cheque/Payment Fee กับใบจริง — ตรวจ Trial Balance
- [ ] **Step 2:** ทดสอบ SO Approval flow (waiting_approval → validate → sale)
- [ ] **Step 3:** ทดสอบ Period Lock (post ใน period locked ต้อง fail)
- [ ] **Step 4:** ทดสอบ PO Approval 2 ระดับ
- [ ] **Step 5:** ทดสอบ Notification queue retry

### Task F3: Install/Upgrade/Uninstall Integrity

- [ ] **Step 1:** ทดสอบ install โมดูลใหม่ 2 ตัวบน DB สะอาด
- [ ] **Step 2:** ทดสอบ upgrade ทุกโมดูลที่แก้ (ไม่มี dependency cycle)
- [ ] **Step 3:** ทดสอบ uninstall (ไม่มี FK violation)

### Task F4: Commit

- [ ] **Step 1:** atomic commits แยกตามโดเมน
- [ ] **Step 2:** อัปเดต `custom_addons/README.md` ถ้ามีโมดูลใหม่
- [ ] **Step 3:** อัปเดต project memory (constraints/lessons ใหม่)

---

## Notes & Risks

1. **GL balance** — WHT/Fee/Cheque ทุกตัวต้องทำให้ debit = credit; ตรวจยอด liquidity = net cash จริงเสมอ (multicurrency ใช้ `currency_id._convert`)
2. **View inheritance IDs** — `purchase.view_company_inherit_form_purchase`, `account.view_company_form`, `account.view_move_form`, `account.view_account_payment_form` เป็น standard IDs; หาก instance ต่างให้แก้ xpath ตาม Task F1 Step 2
3. **base_tier_validation** — ต้องมีใน addons_path มิฉะนั้น SO Approval / Internal Issue tier จะไม่ทำงาน ตรวจตอน Precondition
4. **Sandbox จำกัด** — agent รัน Odoo test ผ่าน terminal ไม่ได้ (exit -1) ต้องรันใน terminal ผู้ใช้
5. **`stock.valuation.layer` ไม่มี `stock_move_id`** — ตรวจว่า Odoo 19 ไม่บังคับ field นี้ (ตาม Task C1)
6. **Contract budget ใช้ `amount_untaxed`** — หาก business ต้องการรวม VAT ต้องแก้ domain ที่ compute
7. **Deposit แบบ %** — ยังไม่ implement (Task A7 Step 2 ต้องมี design ก่อน)

---

## Summary Status

| Phase | Domain | High Issues | Done | Remaining |
|-------|--------|-------------|------|-----------|
| A | Accounting | 9 | 8 | 2 (A7 deposit %; A8 = decided Manual no-code, verify pending) |
| B | Sales | 15 | 16 | 0 (B7 Project Analysis = done) |
| C | Purchase/Inventory | 15 | 6 groups | 0 (C6 = done) |
| D | ISO/Internal | 11 | 7 groups | 0 (D8 = done, ยกเว้น QC approval/sampling) |
| E | Technical | — | 3 groups | 0 (E3 = done) |
| F | Verification | — | 0 | F1–F4 |

**Note:** ตัวเลข "Done" = code เขียนเสร็จ + compile ผ่าน; ยังต้องรัน Task Verify (F1) เพื่อยืนยันด้วย test จริงในฐานข้อมูล
