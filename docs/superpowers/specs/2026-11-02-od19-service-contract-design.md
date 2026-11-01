# เอกสารออกแบบ / ADR: สัญญาบริการเรียกเก็บรายงวด (Service Contract) — ใช้ OCA `contract` เป็น engine + wrapper บาง

- **วันที่:** 2026-11-02
- **Child spec ID:** W6.2-WS05 (Wave 6.2 — รายได้/การเรียกเก็บ)
- **สถานะ:** Approved / Implemented (2026-11-02)
- **ประเภท:** ADR (Architecture Decision Record) + Design
- **ผู้เกี่ยวข้อง:** ฝ่ายขาย/บริการ (After-Sales) / ฝ่ายบัญชีลูกหนี้ / ผู้จัดการสัญญา / ไอที–แอดมิน
- **Canonical path:** `docs/superpowers/specs/2026-11-02-od19-service-contract-design.md`
- **อ้างอิงแผน:** [TH_PROCESS_GAP_AND_WAVE6_PLAN_TH.md](../../../TH_PROCESS_GAP_AND_WAVE6_PLAN_TH.md) WS-05 (G-04)

---

## 1. บทสรุป (Summary)

ธุรกิจบริการ (PM / AMC / สัญญาซ่อมบำรุง) ต้องมี **สัญญาบริการที่เรียกเก็บเงินเป็นงวดอัตโนมัติ** (รายเดือน/รายปี) ปัจจุบันโปรเจกต์ยังไม่มีกลไกนี้ — `od19_sales_contract_core` เป็น *สัญญาโครงการ* (วงเงิน/งวดตาม milestone) ไม่ใช่ *สัญญาบริการแบบ recurring*

**การตัดสินใจ (ADR):** ใช้โมดูล **OCA `contract` (branch 19.0)** เป็น *engine* ของการเรียกเก็บรายงวด แล้วเขียน **โมดูล wrapper `od19_service_contract`** ทำหน้าที่เฉพาะส่วนที่ OCA ไม่มี: ผูกกับ Service Card (แผน PM), ผูกกับการรับประกัน, ต่ออายุ/แจ้งเตือนครบกำหนด และมุมมอง/เมนูสำหรับผู้ใช้ไทย

> **หลักฐานว่าความเสี่ยงในแผนคลี่คลาย:** ตรวจแล้ว OCA `contract` มี branch `19.0` จริง (version `19.0.1.2.2`) และติดตั้งเป็น submodule `third_party/oca/contract` สำเร็จ (commit `5e686b840f`) — จึง **ไม่ต้องพัฒนา engine เอง**

---

## 2. ปัญหาและความต้องการ (Problem)

### 2.1 สภาพปัจจุบัน

| # | ประเด็น | หลักฐาน | สภาพ |
|---|---|---|---|
| 1 | ไม่มีสัญญาบริการ recurring | ไม่มี model recurring ในโปรเจกต์ | ต้องออกใบแจ้งหนี้มือทุกเดือน |
| 2 | งวดคงที่ทำได้แค่แบบ milestone | `od19_sales_contract_core/models/contract_billing_line.py` | ไม่มีตารางรายเดือน/รายปีอัตโนมัติ |
| 3 | ไม่ผูกสัญญากับแผน PM | `od19_service_card` ไม่มี field สัญญา | แผน PM ลอย ไม่รู้ว่าอยู่ในสัญญาใด |
| 4 | ไม่ผูกสัญญากับการรับประกัน | `od19_service_warranty` เก็บ warranty บน `stock.lot` แยกเดี่ยว | ไม่รู้ว่าอุปกรณ์ที่รับประกันอยู่ในสัญญาบริการใด |
| 5 | ไม่มีการต่ออายุ/แจ้งเตือน | — | สัญญาหมดอายุเงียบ กระทบรายได้ต่อเนื่อง |

### 2.2 ความต้องการ (Requirements)

- **R1** สร้างสัญญาบริการที่มีตารางเรียกเก็บ **รายเดือน/รายปี** (กำหนดช่วงเริ่ม–สิ้นสุดได้)
- **R2** **สร้างใบแจ้งหนี้อัตโนมัติ** ตามงวดผ่าน cron (ไม่ต้องกดเอง)
- **R3** ผูกสัญญากับ **Service Card** (แผน PM) และระบุอุปกรณ์ที่รับประกันได้
- **R4** **ต่ออายุได้** (ทั้งกดเองและอัตโนมัติเมื่อครบกำหนด)
- **R5** **แจ้งเตือนก่อนครบกำหนด** ผ่าน `mail.activity`
- **R6** ไม่แตะ Odoo core และไม่แก้ไขซอร์สของ OCA (ห้าม fork)

### 2.3 นิยามคำสำคัญ

- **สัญญาบริการ (Service Contract)** = ข้อตกลงให้บริการต่อเนื่อง มีรอบเรียกเก็บชัดเจน (monthly/yearly) ต่างจาก *สัญญาโครงการ* ที่เรียกเก็บตามงวดงาน/ความคืบหน้า
- **Pre-paid / Post-paid** = เรียกเก็บต้นงวด (ล่วงหน้า) หรือท้ายงวด (ตามหลัง)
- **Renewal** = การต่ออายุสัญญาให้ครอบคลุมงวดถัดไป

---

## 3. การพิจารณาทางเลือก (Options Considered)

| ทางเลือก | ข้อดี | ข้อเสีย | ข้อสรุป |
|---|---|---|---|
| **A. OCA `contract` + wrapper (เลือก)** | engine ครบ (recurrence rule, cron, portal, mail, template); มาตรฐาน OCA; submodule ติดตาม branch 19.0 ได้ | ต้องเรียนรู้ API OCA; มีตารางของ OCA ใน DB | **เลือก** |
| B. พัฒนา engine เองทั้งหมด | ควบคุมได้ 100% | ต้องสร้าง recurrence/cron/portal/mail เองซ้ำ; เสี่ยง bug; ขัดหลัก "ใช้ OCA ก่อน" ของโปรเจกต์ | ไม่เลือก |
| C. ต่อยอด `od19_sales_contract_core` | ใช้ของเดิม | คนละวัตถุประสงค์ (วงเงิน/milestone vs recurring); จะทำให้โมดูลบวมและขัด SoC | ไม่เลือก |

**เหตุผลที่เลือก A:** ตรงกับพันธกิจโปรเจกต์ "ใช้ OCA ก่อนพัฒนาก่อน" (OCA-first) และลดความเสี่ยงจากการสร้าง engine เองซ้ำ; OCA `contract` มีสถานะ `Production/Stable` และมี community ดูแลต่อเนื่อง

---

## 4. สถาปัตยกรรมที่เลือก (Decision)

### 4.1 ภาพรวม

```text
contract.contract  (OCA engine: recurrence, cron, invoice, portal, mail, template)
        ^
        | _inherit (เพิ่มฟิลด์/พฤติกรรมเฉพาะงานบริการ)
        |
od19_service_contract (โมดูลนี้ — wrapper บาง)
   |- contract.contract : is_service_contract, service_card_ids,
   |                      warranty_lot_ids, auto_renew, renewal_*,
   |                      action_renew(), cron_service_contract_renewal()
   |- od19.service.card : contract_id (ผูกแผน PM กลับสัญญา)
```

### 4.2 ขอบเขตความรับผิดชอบ (Separation of Concerns)

| เรื่อง | OCA `contract` (engine) | `od19_service_contract` (wrapper) |
|---|---|---|
| Recurrence rule / ตารางงวด | ใช่ | — |
| Cron สร้างใบแจ้งหนี้อัตโนมัติ | ใช่ (`contract.contract_cron_for_invoice`) | — |
| Portal / mail / template / PDF | ใช่ | — |
| ธง "สัญญาบริการ" | — | ใช่ `is_service_contract` |
| ผูก Service Card (แผน PM) | — | ใช่ |
| ผูกอุปกรณ์ที่รับประกัน (`stock.lot`) | — | ใช่ |
| ต่ออายุเอง (manual) | — | ใช่ `action_renew()` |
| ต่ออายุอัตโนมัติ + แจ้งเตือนก่อนครบกำหนด | — | ใช่ cron + `mail.activity` |
| เมนู/มุมมองสำหรับงานบริการ | — | ใช่ |

**R6 (ไม่แตะ core / ไม่ fork OCA):** ทั้งหมดทำผ่าน `_inherit` (Python) และ XML inheritance เท่านั้น

---

## 5. รายละเอียดการนำไปใช้ (Implementation)

### 5.1 โมดูล

| รายการ | ค่า |
|---|---|
| ชื่อโมดูล | `od19_service_contract` |
| depends | `contract`, `od19_service_card`, `od19_service_warranty` |
| ชนิด | wrapper (ไม่สร้าง model ใหม่ → ไม่ต้องเพิ่ม ACL) |
| submodule | `third_party/oca/contract` (branch `19.0`) + เพิ่มใน `addons_path` |

### 5.2 ฟิลด์ที่เพิ่มบน `contract.contract`

| ฟิลด์ | ชนิด | หน้าที่ |
|---|---|---|
| `is_service_contract` | Boolean | ธงระบุว่าเป็นสัญญาบริการ |
| `service_card_ids` | One2many → `od19.service.card` | แผน PM ภายใต้สัญญา |
| `service_card_count` | Integer (compute) | ตัวนับสำหรับ stat button |
| `warranty_lot_ids` | Many2many → `stock.lot` | อุปกรณ์ที่รับประกันภายใต้สัญญา |
| `auto_renew` | Boolean | ต่ออายุอัตโนมัติเมื่อครบกำหนด |
| `renewal_interval_months` | Integer (default 12) | ระยะต่ออายุ (เดือน) |
| `renewal_notice_days` | Integer (default 30) | แจ้งเตือนล่วงหน้า (วัน) |
| `renewal_notice_sent` | Boolean | กันสร้าง activity ซ้ำ |
| `is_expiring_soon` | Boolean (compute) | ใกล้ครบกำหนดหรือไม่ |

### 5.3 ฟิลด์ที่เพิ่มบน `od19.service.card`

| ฟิลด์ | ชนิด | หน้าที่ |
|---|---|---|
| `contract_id` | Many2one → `contract.contract` | สัญญาบริการที่แผน PM สังกัด |

### 5.4 พฤติกรรม

- **สร้างใบแจ้งหนี้อัตโนมัติ (R1, R2):** ใช้ `contract.contract_cron_for_invoice` ของ OCA ที่มีอยู่ — ตั้ง `recurring_rule_type=monthly`, `recurring_interval=1`, `date_start`, `date_end` และ contract line
- **ต่ออายุ (R4):** `action_renew()` ต่อ `date_end` ของทุก contract line ออกไป `renewal_interval_months` เดือน แล้วรีเซ็ต `renewal_notice_sent` (ให้ OCA คำนวณ `recurring_next_date` ต่อเอง)
- **แจ้งเตือน (R5):** cron รายวัน `cron_service_contract_renewal()` — สัญญาที่ `date_end` เข้าเขต `renewal_notice_days` → `activity_schedule` (TODO) ให้ผู้รับผิดชอบ 1 ครั้ง; ถ้า `auto_renew` และครบกำหนดแล้ว → ต่ออายุให้ทันที

### 5.5 ลำดับการโหลดข้อมูล (data)

```python
"data": [
    "data/ir_cron.xml",
    "views/contract_views.xml",
    "views/service_card_views.xml",
    "views/menus.xml",
],
```

---

## 6. เกณฑ์ยอมรับ (Acceptance Criteria → Tests)

| # | เกณฑ์ | test |
|---|---|---|
| A1 | สัญญา 12 เดือน (monthly) สร้างใบแจ้งหนี้ได้ครบ 12 ใบ ตามงวด | `test_monthly_invoice_generation` |
| A2 | ต่ออายุเองได้ (`action_renew`) → `date_end` เลื่อนออก 12 เดือน | `test_manual_renewal_extends_end_date` |
| A3 | ต่ออายุอัตโนมัติเมื่อครบกำหนด (cron) | `test_cron_auto_renewal` |
| A4 | แจ้งเตือนก่อนครบกำหนดผ่าน `mail.activity` | `test_cron_renewal_notice_activity` |
| A5 | ผูก Service Card กับสัญญาได้ | `test_service_card_link` |

---

## 7. ความเสี่ยงและมาตรการ

| ความเสี่ยง | ระดับ | มาตรการ |
|---|---|---|
| OCA เปลี่ยน API ในอนาคต | ต่ำ | ติดตาม submodule branch 19.0; wrapper บาง ชี้เฉพาะ API ที่จำเป็น |
| Cron ทับซ้อนกับ OCA cron | ต่ำ | คนละ cron / คนละความรับผิดชอบ (OCA = ออกใบแจ้งหนี้, ours = ต่ออายุ/แจ้งเตือน) |
| ต่ออายุแล้วงวดไม่ต่อเนื่อง | ต่ำ | ต่อ `date_end` ของ line โดยตรง ให้ OCA คำนวณ `recurring_next_date` เอง |

---

## 8. ผลกระทบ (Impact)

- เพิ่ม submodule `third_party/oca/contract` (branch 19.0) + ปรับ `addons_path`
- ไม่แก้ไขซอร์ส OCA (ไม่ fork) — ใช้ `_inherit` และ XML inheritance เท่านั้น
- เพิ่ม cron 1 รายการ; ไม่เพิ่ม model/ACL ใหม่

---

## 9. บันทึกการตัดสินใจ (Decision Log)

| วันที่ | ผู้ตัดสินใจ | สรุป |
|---|---|---|
| 2026-11-02 | เจ้าของโปรเจกต์ | เลือกทางเลือก A: OCA `contract` + wrapper `od19_service_contract` |
| 2026-11-02 | เจ้าของโปรเจกต์ | งานถัดไป: WS-05 (G-04) สัญญาบริการเรียกเก็บรายงวด |
