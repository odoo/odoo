# ใบตรวจสอบการย้ายการอ้างอิงบัญชี (Remap Review Sheet) — odoo19_puat

- **วันที่**: 2026-11-05
- **ฐานข้อมูล**: `odoo19_puat`
- **ที่มา**: `docs/od19_puat_account_mapping_20261105.xlsx` (อนุมัติแล้ว 21/21 รายการ)
- **สคริปต์**: `migration/cleanup/remap_accounts.py`
- **สถานะ**: **DRY-RUN (ยังไม่แก้ข้อมูล)** — รอฝ่ายบัญชีตรวจรับก่อนรัน WRITE
- **วัตถุประสงค์**: ให้ฝ่ายบัญชีตรวจสอบรายการอ้างอิงบัญชีที่จะถูกย้าย **25 จุด** ทั้งหมด ก่อนยืนยันรันจริง

---

## 1. สรุปผล DRY-RUN

| รายการ | จำนวน |
|---|---|
| บัญชีเดิมที่พบในระบบ | **21 / 21** |
| จุดอ้างอิง config ที่จะย้าย (field + ir.default) | **25 จุด** |
| ธุรกรรมที่จะถูกแตะ (posted entries) | **0 จุด** (ข้ามทั้งหมด) |
| ฟิลด์ company_dependent (jsonb) ที่ต้องย้าย | 0 จุด |
| ir.default (ค่าตั้งต้นระบบ) | 3 จุด |
| บัญชีใหม่ที่ต้องสร้างตอน WRITE | 2 บัญชี (`1153.04`, `1153.05`) |

> หลักการสำคัญ: remap แตะเฉพาะ **ค่าตั้งต้น/config** เท่านั้น ไม่แตะรายการที่ลงบัญชีแล้ว (posted) ถ้าพบธุรกรรมจะรายงานและข้าม

---

## 2. รายการที่จะถูกย้าย 25 จุด (เรียงตามรหัสเดิม)

| # | บัญชีเดิม | → ปลายทาง | ฟิลด์อ้างอิง | จำนวน | ตรวจที่ไหนใน Odoo |
|---|---|---|---|---|---|
| 1 | 111100 | 1111.00 (เงินสด) | `account.advance.advance_account_id` | 15 | การบัญชี → Advance Payments |
| 2 | 111100 | 1111.00 (เงินสด) | `petty.cash.fund.account_id` | 28 | การบัญชี → Petty Cash → Funds |
| 3 | 111102 | 1111.01 (เงินสดย่อย) | `account.journal.default_account_id` | 1 | การบัญชี → การตั้งค่า → Journals (id 4123) |
| 4 | 111207 | 1112.01 (กระแสรายวัน Kbank 609-1-00004-9) | `account.journal.default_account_id` | 1 | Journals (id 4115) |
| 5 | 111208 | 1114.02 (ประจำ Kbank 023-3-04435-0) | `account.journal.default_account_id` | 1 | Journals (id 4116) |
| 6 | 111209 | 1113.01 (ออมทรัพย์ Kbank 609-2-00057-3) | `account.journal.default_account_id` | 1 | Journals (id 4117) |
| 7 | 111210 | 1113.02 (ออมทรัพย์ Kbank 023-2-36473-4) | `account.journal.default_account_id` | 1 | Journals (id 4118) |
| 8 | 111211 | 1114.01 (ประจำ Kbank 609-3-00181-6) | `account.journal.default_account_id` | 1 | Journals (id 4119) |
| 9 | 111212 | 1112.02 (กระแสรายวัน Kbank 023-1-06082-0) | `account.journal.default_account_id` | 1 | Journals (id 4120) |
| 10 | 111214 | 1113.03 (ออมทรัพย์ SCB 140-2-13697-4) | `account.journal.default_account_id` | 1 | Journals (id 4128) |
| 11 | 111215 | 1113.04 (ออมทรัพย์ UOB 797-163-731-9) | `account.journal.default_account_id` | 1 | Journals (id 4129) |
| 12 | 111216 | 1112.03 (กระแสรายวัน UOB 797-3-63052-4) | `account.journal.default_account_id` | 1 | Journals (id 4130) |
| 13 | 111217 | 1114.03 (ประจำ UOB 797-003-044-5) | `account.journal.default_account_id` | 1 | Journals (id 4131) |
| 14 | 112100 | 1130.00 (ลูกหนี้การค้า) | `ir.default` res.partner.account_receivable | 1 | การตั้งค่า → Technical → Defaults |
| 15 | 112101 | 1130.00 (ลูกหนี้การค้า) | `res.company.account_default_pos_receivable_account_id` | 1 | การตั้งค่า → บริษัท → (เปิดบริษัท) |
| 16 | 113100 | 1140.01 (สินค้าคงเหลือ) | `od19.stock.valuation.adjustment.stock_valuation_account_id` | 16 | คลังสินค้า → Operations → Valuation Adjustments |
| 17 | 113100 | 1140.01 (สินค้าคงเหลือ) | `res.company.account_stock_valuation_id` | 1 | การตั้งค่า → บริษัท → (เปิดบริษัท) |
| 18 | 113100 | 1140.01 (สินค้าคงเหลือ) | `ir.default` product.category.stock_valuation | 1 | การตั้งค่า → Technical → Defaults |
| 19 | 114200 | 1151.01 (ภาษีซื้อ) | `account.tax.repartition.line.account_id` | 8 | การบัญชี → การตั้งค่า → Taxes |
| 20 | 114300 | **1153.04 (ภาษีเงินได้ถูกหัก ณ ที่จ่าย)** *ใหม่* | `account.tax.repartition.line.account_id` | 8 | การบัญชี → การตั้งค่า → Taxes |
| 21 | 114400 | 1153.01 (ลูกหนี้กรมสรรพากร) | `account.tax.group.tax_receivable_account_id` | 1 | การบัญชี → การตั้งค่า → Tax Groups |
| 22 | 114401 | **1153.05 (ภาษีหัก ณ ที่จ่ายรอเครดิต/ขอคืน)** *ใหม่* | `account.tax.group.tax_receivable_account_id` | 4 | การบัญชี → การตั้งค่า → Tax Groups |
| 23 | 511100 | 5110.00 (ต้นทุนขาย) | `account.journal.default_account_id` | 2 | Journals (id 2, 4112) |
| 24 | 511100 | 5110.00 (ต้นทุนขาย) | `res.company.expense_account_id` | 1 | การตั้งค่า → บริษัท → (เปิดบริษัท) |
| 25 | 511100 | 5110.00 (ต้นทุนขาย) | `ir.default` product.category.expense | 1 | การตั้งค่า → Technical → Defaults |

---

## 3. จุดที่ต้องสังเกตเป็นพิเศษ

1. **บัญชีใหม่ 2 ตัว** (`1153.04`, `1153.05`) ยังไม่มีในผัง — สคริปต์จะสร้างให้ตอน WRITE (ปัจจุบัน DRY-RUN แจ้ง `!! ไม่พบบัญชีปลายทาง` เป็นเรื่องปกติ)
2. **`114300 → 1153.04`** และ **`114401 → 1153.05`** — เป็นการ **แยกบัญชี WHT** ตามที่อนุมัติ (114300/114401 เดิม → แยกเป็น WHT Asset / WHT Pending)
3. **`511200 → 5120.00` (ต้นทุนบริการ)** ไม่ปรากฏใน 25 จุดนี้ เพราะจัดการผ่าน**ขั้นที่ 6** (ตั้งหมวดสินค้า Services/Expenses) ซึ่งทำงานเฉพาะตอน WRITE
4. **`111100 → 1111.00`** กระทบมากสุด (43 รายการ รวม Advance 15 + Petty Cash 28) — ตรวจว่าใช้ "เงินสด" รวมถูกต้อง
5. **`113100 → 1140.01`** กระทบ Stock Valuation Adjustment 16 รายการ — ตรวจว่าใช้ "สินค้าคงเหลือ" ถูกต้อง
6. บัญชี **หัวข้อ (`.00`)** ที่ถูกอ้างถึง (`1153.00 ฯลฯ`) เป็นเรื่องปกติของการอ้างช่วง — ตรวจว่ารหัสปลายทางเป็น **leaf** จริง

---

## 4. Checklist อนุมัติ (ให้ฝ่ายบัญชีติ๊ก)

| ลำดับ | รายการตรวจ | ผู้ตรวจ | ผล |
|---|---|---|---|
| 1 | บัญชีเงินสด/เงินฝากทั้ง 11 สมุด (ข้อ 3–13) ชี้ไปบัญชีใหม่ถูกต้อง | | ☐ ผ่าน ☐ แก้ไข |
| 2 | Advance Payments (15) + Petty Cash Funds (28) → 1111.00 ถูกต้อง | | ☐ ผ่าน ☐ แก้ไข |
| 3 | Stock Valuation Adjustment (16) → 1140.01 ถูกต้อง | | ☐ ผ่าน ☐ แก้ไข |
| 4 | ภาษี (Taxes/Tax Groups) แยก WHT ถูกต้องตามที่อนุมัติ | | ☐ ผ่าน ☐ แก้ไข |
| 5 | ต้นทุนขาย/บริการ (5110.00 / 5120.00) ถูกต้อง | | ☐ ผ่าน ☐ แก้ไข |
| 6 | ยืนยันรัน WRITE (สร้าง 2 บัญชี + ย้าย 25 จุด + archive journal `PV`) | | ☐ อนุมัติ ☐ เลื่อน |

---

## 5. วิธีรัน WRITE (หลังฝ่ายบัญชีอนุมัติเท่านั้น)

```powershell
# 1) สำรอง DB ก่อน (ถ้ายังไม่มีรอบล่าสุด)
#    backups\odoo19_puat_YYYYMMDD_HHMMSS.dump

# 2) เขียนจริง
$env:OD19_REMAP_CONFIRM = "1"
Get-Content -Raw migration\cleanup\remap_accounts.py |
    venv19\Scripts\python.exe odoo-bin shell -c odoo.conf -d odoo19_puat --no-http
Remove-Item Env:\OD19_REMAP_CONFIRM
```

**หลังรัน WRITE**: ต้องตรวจว่า `จุดอ้างอิง config ที่จะย้าย: 0 จุด` (ถ้าไม่ใช่ 0 แสดงว่ามีจุดตกค้าง)

---

## 6. ภาคผนวก — ผล DRY-RUN ดิบ (2026-11-05)

```
REMAP| พบบัญชีเดิมที่จะ remap: 21/21
REMAP| สแกน: ฟิลด์ปกติ 120 ครั้ง | jsonb(จริง) 0 จุด | ir.default 3 จุด → รวม 25 จุด
REMAP| จุดอ้างอิง config ที่จะย้าย: 25 จุด | ธุรกรรม (ข้าม): 0 จุด
REMAP|   111100 → 1111.00 | [field] account.advance.advance_account_id | 15 รายการ
REMAP|   111100 → 1111.00 | [field] petty.cash.fund.account_id | 28 รายการ
REMAP|   111102 → 1111.01 | [field] account.journal.default_account_id | 1 รายการ | ids=[4123]
REMAP|   111207 → 1112.01 | [field] account.journal.default_account_id | 1 รายการ | ids=[4115]
REMAP|   111208 → 1114.02 | [field] account.journal.default_account_id | 1 รายการ | ids=[4116]
REMAP|   111209 → 1113.01 | [field] account.journal.default_account_id | 1 รายการ | ids=[4117]
REMAP|   111210 → 1113.02 | [field] account.journal.default_account_id | 1 รายการ | ids=[4118]
REMAP|   111211 → 1114.01 | [field] account.journal.default_account_id | 1 รายการ | ids=[4119]
REMAP|   111212 → 1112.02 | [field] account.journal.default_account_id | 1 รายการ | ids=[4120]
REMAP|   111214 → 1113.03 | [field] account.journal.default_account_id | 1 รายการ | ids=[4128]
REMAP|   111215 → 1113.04 | [field] account.journal.default_account_id | 1 รายการ | ids=[4129]
REMAP|   111216 → 1112.03 | [field] account.journal.default_account_id | 1 รายการ | ids=[4130]
REMAP|   111217 → 1114.03 | [field] account.journal.default_account_id | 1 รายการ | ids=[4131]
REMAP|   112100 → 1130.00 | [ir.default] res.partner.property_account_receivable_id company=1 | 1 รายการ
REMAP|   112101 → 1130.00 | [field] res.company.account_default_pos_receivable_account_id | 1 รายการ
REMAP|   113100 → 1140.01 | [field] od19.stock.valuation.adjustment.stock_valuation_account_id | 16 รายการ
REMAP|   113100 → 1140.01 | [field] res.company.account_stock_valuation_id | 1 รายการ
REMAP|   113100 → 1140.01 | [ir.default] product.category.property_stock_valuation_account_id company=1 | 1 รายการ
REMAP|   114200 → 1151.01 | [field] account.tax.repartition.line.account_id | 8 รายการ
REMAP|   114300 → 1153.04 | [field] account.tax.repartition.line.account_id | 8 รายการ
REMAP|   114400 → 1153.01 | [field] account.tax.group.tax_receivable_account_id | 1 รายการ
REMAP|   114401 → 1153.05 | [field] account.tax.group.tax_receivable_account_id | 4 รายการ
REMAP|   511100 → 5110.00 | [field] account.journal.default_account_id | 2 รายการ | ids=[2, 4112]
REMAP|   511100 → 5110.00 | [field] res.company.expense_account_id | 1 รายการ
REMAP|   511100 → 5110.00 | [ir.default] product.category.property_account_expense_categ_id company=1 | 1 รายการ
REMAP| บัญชีเดิมที่ยังมีจุดอ้างอิง (config): 111100, 111102, 111207, 111208, 111209, 111210,
       111211, 111212, 111214, 111215, 111216, 111217, 112100, 112101, 113100, 114200,
       114300, 114400, 114401, 511100
```
