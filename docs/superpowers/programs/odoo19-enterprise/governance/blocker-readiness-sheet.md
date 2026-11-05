# Blocker Readiness Sheet — กลุ่ม C (รอการตัดสินใจ/ข้อมูลจากบุคคล)

## Document Metadata

| Field | Value |
| --- | --- |
| Program | Odoo 19 Enterprise (Greenfield + ETL) |
| Artifact path | `docs/superpowers/programs/odoo19-enterprise/governance/blocker-readiness-sheet.md` |
| Artifact owner | Program lead (ผู้รวบรวม) · เจ้าของรายข้อตามตาราง |
| Artifact status | **Draft (decision agenda)** — รอคำตอบ/ลายเซ็นจากเจ้าของ |
| ที่มา | EPIC D/E/F/G ของ [backlog-closure-plan](file:///c:/odoo-dev/odoo19/docs/superpowers/plans/2026-11-01-backlog-closure-plan.md) + Phase 0–8 ของ [data-migration-plan](file:///c:/odoo-dev/odoo19/docs/superpowers/plans/2026-10-22-odoo15-to-odoo19-data-migration-plan.md) |
| Last updated | 2026-11-05 |

## วัตถุประสงค์

รวบรวม **blocker ที่รอการตัดสินใจ/ข้อมูลจากบุคคล** (ไม่ใช่งานโค้ด) ให้เป็นวาระเดียวที่เคาะได้เร็ว
แต่ละข้อระบุ: **คำถามที่ต้องตอบ · เจ้าของ · สิ่งที่ต้องได้ (หลักฐาน) · ผลกระทบถ้าเลื่อน**
เพื่อให้ตอบครบแล้วปิดงานได้ทันทีโดยไม่ต้องย้อนอ่านหลายเอกสาร

> **กติกา:** เอกสารนี้ **ไม่สร้างข้อเท็จจริงใหม่** — ทุกข้ออ้างอิงหลักฐานที่มีอยู่จริงใน repo
> หากเจ้าของตอบแล้ว ให้บันทึกคำตอบ + วันที่ + ผู้ตอบ กลับเข้าข้อนั้น

---

## 1. ตารางสรุป (Decision Agenda)

| รหัส | คำถามที่ต้องตอบ | เจ้าของ (role) | สิ่งที่ต้องได้ (หลักฐาน) | ผลกระทบถ้าเลื่อน |
| --- | --- | --- | --- | --- |
| **D4** | ยอดยกมา (AR/AP/สินค้า/สินทรัพย์/WHT/เบิกล่วงหน้า/เช็ค) tie กับ Odoo 15 ได้ 100% หรือไม่ และอนุมัติปิดยอดหรือยัง? | ฝ่ายบัญชี + Migration/Data lead | งบทดลอง tie ตรง + ลายเซ็น 3 ช่อง (ผู้จัดทำ/ผู้ตรวจสอบ/ผู้อนุมัติ) | DoD ข้อ 4 ไม่ผ่าน → **ปิดโปรแกรม/go-live ไม่ได้** |
| **E1** | Mapping ผังบัญชี OD15→OD19 (รวมบัญชีที่ merge) ยืนยันได้หรือไม่ และผูก Account/Analytic Tag ครบหรือยัง? | ฝ่ายบัญชี | mapping workbook ชีต "01-ผังบัญชี" สถานะ VERIFIED | COA import ผิด → TB เพี้ยน ย้อนแก้ยาก |
| **F1** | อนุมัติเริ่มงาน Wave 6 (WS-01..WS-15) หรือเลื่อน? | ผู้ใช้/เจ้าของโปรแกรม | คำสั่งอนุมัติ + ขอบเขตที่ยืนยัน | ช่องว่างกระบวนการไทย 15 ข้อค้าง |
| **F2** | เริ่ม W6-DASH-PHASE3 (per-domain boards D1/D2/D3) เมื่อใด? | ผู้ใช้/เจ้าของโปรแกรม | อนุมัติ design + ลำดับงาน | Dashboard ระดับโดเมนไม่ครบ |
| **G1** | ยืนยัน "ไม่ adopt" `account_payment_order` (ACCA-001) หรือต้องการรีวิวใหม่? | ฝ่ายบัญชี | ยืนยันผลตัดสินใจ (มีบันทึกแล้ว 2026-10-26) | (ต่ำ) flow จ่ายคงเดิม |
| **G2** | ยืนยันการ adopt OCA `account_move_name_sequence` + `account_lock_date_update` (ACCA-008)? | ฝ่ายบัญชี | ยืนยันผลตัดสินใจ (implement แล้ว) | เลขเอกสาร/ล็อกงวดอาจไม่ตรงข้อกำหนดผู้สอบ |
| **G3** | ยืนยัน custom partial unique index บน `ref` (`account_invoice_supplier_ref_unique`) แทน OCA? | ฝ่ายบัญชี | ยืนยันผลตัดสินใจ (implement แล้ว) | กันเลขผู้ขายซ้ำไม่ครบตามนโยบาย |
| **G4** | ยืนยันฟิลด์อำเภอ/ตำบล (`od19_amphoe`/`od19_subdistrict`) เพียงพอต่อที่อยู่ไทย? | ฝ่ายบัญชี | ยืนยันผลตัดสินใจ (implement แล้ว) | เอกสาร/ที่อยู่ไทยไม่ครบช่อง |
| **Checklist G3** | Module custom 167 ตัว มี mapping/แทนที่/N-A ครบหรือยัง? | Migration/Data lead + ฝ่ายที่เกี่ยวข้อง | ตารางครบ 167/167 | import ขาดโมดูลที่ต้อง map |
| **Checklist G4** | Blocking data-quality (Section 3.1–3.3, 3.5, 3.7, 3.13) ถูกแก้/รับทราบแล้วหรือยัง? | ฝ่ายที่เกี่ยวข้อง | รายการ blocking ปิดหรือมีแผน remediate | import ล้มเหลว/ข้อมูลเสียเข้าใหม่ |
| **Checklist G5** | Baseline ตัวเลข (Section 4) มีฝ่ายบัญชีรับทราบ/ลงนามหรือยัง? | ฝ่ายบัญชี | baseline บันทึกครบ + sign-off | ไม่มีเส้นอ้าง photo ตอน tie ยอด |
| **Mig Ph0** | Freeze Odoo 15 + dump รอบสุดท้าย พร้อมเมื่อใด? | ผู้ใช้/IT ops | dump + filestore + checksum + ทดสอบ restore ผ่าน | ETL เริ่มไม่ได้ |
| **Mig Ph1** | Profiling ปิด (ทำแล้ว) — ฝ่ายบัญชีรับทราบ baseline แล้วหรือยัง? | ฝ่ายบัญชี | Gate 1 ผ่าน | Phase 2 เริ่มไม่ได้ |
| **Mig Ph2** | อนุมัติวันตัดยอด (cut-off) อย่างเป็นทางการ? | ฝ่ายบัญชี + ผู้ใช้ | workbook ครบทุกชีต + วันตัดยอดอนุมัติ | import ยอดยกมาไม่มีจุดอ้างอิง |
| **Mig Ph7** | วันที่ go-live จริง + ช่วง Freeze? | ผู้ใช้/เจ้าของโปรแกรม | แผน cut-over + rollback point | go-live เลื่อน |
| **Mig Ph8** | นโยบาย Odoo 15 read-only archive + watch period? | ผู้ใช้/IT ops | ข้อตกลง archive + ผู้รับผิดชอบ | ค้นประวัติไม่ได้หลังปิดระบบเดิม |

---

## 2. รายละเอียดรายข้อ

### 2.1 EPIC D — Data Migration

#### D4 — Opening balance tie + sign-off `[blocker หลัก]`

- **นิยาม:** ยอดยกมาต้อง tie กับ legacy 100%; Acceptance = งบทดลอง tie ตรง + ลายเซ็น 3 ช่อง (ผู้จัดทำ/ผู้ตรวจสอบ/ผู้อนุมัติ) จากฝ่ายบัญชี
  ([backlog-closure-plan §D4](file:///c:/odoo-dev/odoo19/docs/superpowers/plans/2026-11-01-backlog-closure-plan.md))
- **สถานะปัจจุบัน:** ยังไม่ tie — รอ ETL รันจริง (D3) และข้อมูล baseline ที่ profiled แล้ว
- **สิ่งที่ต้องมีก่อนตอบ:** ตัวเลข baseline จาก Section 4 ของ [profiling checklist](file:///c:/odoo-dev/odoo19/docs/superpowers/programs/odoo19-enterprise/discovery/legacy-od15-data-profiling-checklist.md) (บันทึกแล้ว) + ผล import จริงจาก sandbox
- **ขึ้นกับ:** D3 (ETL smoke test) + Checklist G4/G5
- **หลักฐานปิดงาน:** งบทดลองเทียบ legacy + แบบฟอร์ม sign-off 3 ช่อง (แนบไฟล์)

#### Migration Phase 0 — Freeze & Backup `[blocker เริ่มต้น]`

- **นิยาม/เกณฑ์:** restore สำเร็จ + เปิดดูข้อมูลได้ + checksum ตรง → ถ้าไม่ผ่าน ห้ามเริ่ม Phase 1
  ([data-migration-plan Ph0](file:///c:/odoo-dev/odoo19/docs/superpowers/plans/2026-10-22-odoo15-to-odoo19-data-migration-plan.md))
- **สถานะปัจจุบัน:** มี dump แล้ว 2 ชุด (`odoo_golive.dump` 158 MB / `od15_autoerp_prd.dump` 10 MB) + manifest `attach_files.txt`; ยังไม่ยืนยัน freeze รอบสุดท้ายของวันจริง
- **คำถาม:** กำหนด **วัน freeze** และสั่งหยุดคีย์เอกสารใน Odoo 15 เมื่อใด

#### Migration Phase 1 — Staging & Profiling `[เกือบปิด]`

- **สถานะปัจจุบัน:** **Profiling รันแล้ว** บน `od15_stage` read-only → [profiling_result.txt](file:///c:/odoo-dev/odoo19/migration/od15_export/profiling_result.txt) (4.1 MB); module inventory installed 432 (core 206 / OCA 59 / custom 167)
- **เหลือ:** Gate 1 ต้อง "ไม่มี blocking data-quality ค้าง + baseline ฝ่ายบัญชีรับทราบ" → ผูกกับ Checklist G4/G5

#### Migration Phase 2 — Mapping & Cut-over Decision

- **สถานะปัจจุบัน:** mapping workbook กรอกชีต 01/08/09 แล้ว (D2 ปิด 2026-11-02) — เหลือ **อนุมัติวันตัดยอดอย่างเป็นทางการ**
- **คำถาม:** อนุมัติ **cut-off date** (ค่าใน SQL เป็นเพียงตัวอย่าง ไม่ใช่วันจริง) เป็นวันใด
- **เกณฑ์ผ่าน Gate 2:** workbook ครบทุกชีต + วันตัดยอดอนุมัติ

#### Migration Phase 7 — Cut-over Rehearsal & Go-live

- **เกณฑ์ผ่าน Gate 7:** ฟังก์ชันหลักผ่านทุกข้อ (ใบเสนอราคา, SO ผ่าน credit gate, PO, รับเข้า/เบิกจ่าย, Invoice, WHT/เช็ค, รายงานไทย Sarabun, Dashboard) + Recon ผ่านซ้ำ ณ วันจริง
- **คำถาม:** วันที่ go-live จริง + ผู้รับผิดชอบ watch period

#### Migration Phase 8 — Post Go-live & Legacy Archive

- **คำถาม:** นโยบายเก็บ Odoo 15 เป็น read-only archive + ช่องทางค้นประวัติ + เจ้าของ

---

### 2.2 EPIC E — COA Migration

#### E1 — ยืนยัน mapping ผังบัญชี + ผูก Tag `[blocker]`

- **นิยาม:** ยืนยัน mapping OD15 → Odoo 19 และผูก Account/Analytic Tag; **Blocker:** รอผู้ใช้/ฝ่ายบัญชียืนยัน — เน้นความต่อเนื่องของ Legacy COA ถ้าผังมาตรฐาน OD19 ไม่ครอบ
  ([backlog-closure-plan §E1](file:///c:/odoo-dev/odoo19/docs/superpowers/plans/2026-11-01-backlog-closure-plan.md))
- **สถานะปัจจุบัน:** mapping workbook เติมชีต "01-ผังบัญชี" แล้ว (D2) → ยังไม่ยืนยัน VERIFIED
- **ตัวเลือก (จาก Open Decisions #5):** ให้ผู้ใช้ยืนยันเอง / ให้ทีมเสนอ mapping (ที่แนะนำ: **ให้ทีมเสนอ**)
- **เกณฑ์ผ่าน:** ทุกบัญชีที่มียอดมี mapping (ไม่มีบัญชีที่มียอดแต่ไม่มี mapping) + ระบุบัญชีที่ต้อง merge
- **ผลกระทบถ้าเลื่อน:** COA import ผิด ยอด TB เพี้ยน แก้ย้อนหลังยาก

---

### 2.3 EPIC F — Wave 6 / Dashboard

#### F1 — Wave 6 Thai Process Gaps (WS-01..WS-15)

- **นิยาม:** ปิดช่องว่างกระบวนการธุรกิจไทย 15 รายการ ตาม [TH_PROCESS_GAP_AND_WAVE6_PLAN_TH.md](file:///c:/odoo-dev/odoo19/TH_PROCESS_GAP_AND_WAVE6_PLAN_TH.md)
- **Blocker:** รออนุมัติก่อนเริ่ม (ยังไม่เริ่มงาน WS ใด)
- **ตัวเลือก (Open Decisions #4):** อนุมัติเริ่ม / เลื่อน (ที่แนะนำ: **รอคำสั่ง**)

#### F2 — W6-DASH-PHASE3

- **นิยาม:** per-domain boards (D1 Finance / D2 Logistics / D3 HR) + `check_access()` cleanup + doc sync
- **สถานะ:** Draft — [design doc](file:///c:/odoo-dev/odoo19/docs/superpowers/specs/2026-10-22-odoo19-dashboard-phase3-completion-design.md)
- **คำถาม:** อนุมัติ design + จัดลำดับงาน (ต่อจาก F1 หรือขนานได้)

---

### 2.4 EPIC G — Open Decisions ฝ่ายบัญชี

> **ข้อเท็จจริงสำคัญ:** คำตัดสินทั้ง 4 ข้อ **บันทึกไว้แล้วเมื่อ 2026-10-26** ใน
> [accounting-requirements-coverage.md §4](file:///c:/odoo-dev/odoo19/docs/superpowers/programs/odoo19-enterprise/backlog/accounting-requirements-coverage.md)
> และ G2/G3/G4 **implement จริงแล้ว** (มีเทสต์ในโค้ด) → สิ่งที่เหลือคือ **การยืนยันอย่างเป็นทางการของฝ่ายบัญชี**
> (backlog-closure-plan ยังคงแสดงว่า "รอคำตอบ" — เป็นสถานะที่ล้าสมัยกว่าหลักฐานในโค้ด)

| รหัส | คำตัดสินที่บันทึกไว้ | หลักฐานในโค้ด | สิ่งที่เหลือ |
| --- | --- | --- | --- |
| **G1** `account_payment_order` (ACCA-001) | **ไม่ adopt** — คง Prepare Payment บน `account.payment`; บันทึก "รอ OCA 19.0 / revisit" | — (ไม่มี dependency ใหม่) | ยืนยันผลตัดสินใจ |
| **G2** `account_move_name_sequence` / `account_lock_date_update` (ACCA-008) | **ใช้ OCA** เป็น dependency ของ `od19_accounting_features` | `custom_addons/od19_accounting_features/__manifest__.py` | ยืนยันผลตัดสินใจ |
| **G3** `account_invoice_supplier_ref_unique` | **ทำ custom** — partial unique index บน `ref` ต่อ (company, commercial partner) | [test_supplier_ref_unique.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_accounting_features/tests/test_supplier_ref_unique.py) | ยืนยันผลตัดสินใจ |
| **G4** ฟิลด์อำเภอ/ตำบล | **ต้องการ** — เพิ่ม `od19_amphoe` / `od19_subdistrict` | [res_partner.py](file:///c:/odoo-dev/odoo19/custom_addons/od19_partner_thai_fields/models/res_partner.py) + [test](file:///c:/odoo-dev/odoo19/custom_addons/od19_partner_thai_fields/tests/test_partner_thai_fields.py) | ยืนยันผลตัดสินใจ |

**Action ที่แนะนำ:** ให้ฝ่ายบัญชียืนยันทั้ง 4 ข้อเป็นชุดเดียว แล้วอัปเดตสถานะใน
backlog-closure-plan §EPIC G (`- [ ]` → `- [x]` พร้อมวันที่/ผู้ออกคำสั่ง)

---

### 2.5 Checklist Gates (Profiling) — Section 5

อ้างอิง [profiling checklist §5](file:///c:/odoo-dev/odoo19/docs/superpowers/programs/odoo19-enterprise/discovery/legacy-od15-data-profiling-checklist.md)

| Gate | นิยาม | สถานะ |
| --- | --- | --- |
| **G3** | Module inventory ครบ — โมดูล custom ที่ติดตั้งจริง 167 ตัว ต้องมี mapping | mapping workbook (D2) เติมชีตแล้ว → ยังไม่ยืนยันครบ 167/167 |
| **G4** | ไม่มี blocking data-quality ค้าง (Section 3.1–3.3, 3.5, 3.7, 3.13) | รอรายการ blocking ปิด/รับทราบ |
| **G5** | Baseline (Section 4) บันทึกครบ + sign-off | บันทึกแล้ว → รอ sign-off ฝ่ายบัญชี |

> ⚠️ **ข้อควรระวังเรื่องรหัสซ้ำ:** "G3/G4/G5" ของ **checklist นี้** คนละชุดกับ
> "G1–G4" ของ **EPIC G** — ให้อ้างบริบทกำกับเสมอเมื่อสื่อสาร

---

## 3. ลำดับการปลดล็อกที่แนะนำ (Critical Path)

```text
Mig Ph0 (Freeze/dump)  ──►  Checklist G4 (data-quality)  ──►  Mig Ph1 Gate 1
        │                                                          │
        └──►  Mig Ph2 (อนุมัติ cut-off) ◄── E1 (COA verified) ◄────┘
                         │
                         ▼
              D3 ETL smoke test ──► D4 opening tie + sign-off
                         │
                         ▼
         Mig Ph7 (rehearsal/go-live) ──► Mig Ph8 (archive)
                         │
                         └──►  EPIC G ยืนยัน (ขนานได้)  +  F1/F2 (ขนานได้)
```

- **เส้นทางวิกฤต (ห้ามเลื่อน):** Mig Ph0 → Checklist G4 → Mig Ph2 → D3 → **D4** → Mig Ph7
- **ทำขนานได้:** EPIC G ยืนยัน, F1/F2, Mig Ph8 (เตรียมนโยบายล่วงหน้า)

---

## 4. Definition of Done ของเอกสารนี้

- [ ] ทุกข้อใน Sec.1 มี **เจ้าของที่ระบุชื่อจริง** (ไม่ใช่แค่ role)
- [ ] ทุกข้อมี **คำตอบ + วันที่ + ผู้ตอบ** บันทึกกลับเข้าข้อนั้น
- [ ] เมื่อปิดครบ → อัปเดต DoD ระดับโปรแกรม (ข้อ 4, 5, 6) ใน [backlog-closure-plan](file:///c:/odoo-dev/odoo19/docs/superpowers/plans/2026-11-01-backlog-closure-plan.md)
- [ ] สถานะเอกสารเปลี่ยนจาก `Draft` → `Closed`
