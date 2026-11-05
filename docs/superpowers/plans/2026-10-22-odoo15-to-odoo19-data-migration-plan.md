# Odoo 15 → Odoo 19 Data Migration Plan (Greenfield + ETL)

> **For agentic workers:** REQUIRED SUB-SKILL: ใช้ superpowers:subagent-driven-development หรือ superpowers:executing-plans เพื่อทำตามแผนนี้ทีละ Task โดยใช้ checkbox (`- [ ]`) ในการติดตามความคืบหน้า

**Goal:** ย้ายข้อมูลจาก Odoo 15 (`custom15_autoinfo`) เข้าสู่ Odoo 19 (Greenfield) โดยย้ายเฉพาะ **master data + ยอดยกมา (opening balances)** เพื่อให้ระบบใหม่เริ่มดำเนินธุรกิจได้ตั้งแต่วัน cut-over โดยไม่ต้องย้ายประวัติธุรกรรมย้อนหลังทั้งหมด

**Architecture:** ฐานข้อมูล Odoo 19 ใหม่สะอาด + ติดตั้งโมดูล `od19_*` (79 โมดูล — ฟีเจอร์ครบตาม `GAP_ANALYSIS_OD15_to_OD19.md`) + OCA + `l10n_th` แล้วจึงนำเข้าข้อมูลผ่าน **ETL ภายนอก** (อ่านฝั่ง Odoo 15 แบบ read-only ผ่าน PostgreSQL, เขียนฝั่ง Odoo 19 ผ่าน **ORM เท่านั้น**) ทุกเรกคอร์ดผูก External ID รูปแบบ `__import15__.<model>.<legacy_id>` เพื่อให้รันซ้ำได้ (idempotent) และตรวจสอบย้อนกลับได้

**Tech Stack:** Odoo 19 Enterprise (Greenfield), PostgreSQL (pg_dump / psql / staging DB `od15_stage`), Python 3 (`venv19`, psycopg2), Odoo ORM ผ่าน `odoo shell`, openpyxl (mapping workbook), PowerShell (Windows), Git

**เอกสารและเครื่องมือที่เตรียมไว้แล้ว:**

| ประเภท | ไฟล์ |
|---|---|
| แผนงาน (ไฟล์นี้) | `docs/superpowers/plans/2026-10-22-odoo15-to-odoo19-data-migration-plan.md` |
| Checklist profiling | `docs/superpowers/programs/odoo19-enterprise/discovery/legacy-od15-data-profiling-checklist.md` |
| Mapping workbook (11 ชีต) | `docs/superpowers/programs/odoo19-enterprise/discovery/od15-to-od19-data-mapping.xlsx` |
| SQL profiling (read-only) | `migration/extract/01_profiling_queries.sql` |
| Import runner | `migration/import/run.py`, `common.py`, `legacy.py` |
| Import steps (9 ขั้น) | `migration/import/steps/s01_reference.py` … `s09_sequences.py` |
| CSV mapping templates | `migration/mapping/*.csv` (`account_map`, `tax_map`, `uom_map`, `journal_map`, `payment_term_map`, `partner_category_map`) |

---

## Design Decisions (ตัดสินใจแล้ว — ต้องรับรู้ตอน review)

1. **Greenfield + ETL ไม่ใช้ OpenUpgrade** — เพราะโมดูล custom ถูกสร้างใหม่ทั้งหมดและเปลี่ยนชื่อ (`autoinfo_*`/`dtr_*` → `od19_*`) ตารางเดิมจะกลายเป็น orphan ทำให้ประโยชน์ของ OpenUpgrade เหลือเฉพาะ core แต่แลกมาด้วยภาระ 4-hop upgrade (15→16→17→18→19) + pre/post-migration script ต่อเวอร์ชัน — ไม่คุ้มกับความต้องการที่ยืนยันว่า **ไม่ต้องมีประวัติธุรกรรมย้อนหลังในระบบใหม่**
2. **ไม่ย้ายประวัติธุรกรรม** — Odoo 15 จะถูกเก็บไว้เป็น **read-only archive** สำหรับค้นเอกสารย้อนหลัง (Phase 8) ส่วน Odoo 19 เริ่มด้วยยอดยกมา ณ วันตัดยอด
3. **เขียน Odoo 19 ด้วย ORM เท่านั้น** — ห้าม raw SQL/`cr.commit()` ใน logic ธุรกิจ (constraint โปรเจกต์) การ `commit()` ระหว่าง step อนุญาตเฉพาะใน `run.py` ซึ่งเป็นเครื่องมือภายนอก (กัน transaction ยาวหลายชั่วโมง)
4. **Idempotency ด้วย External ID** — `__import15__.<model>.<legacy_id>` ผ่าน `ir.model.data` ทำให้ re-run ได้ไม่เกิดข้อมูลซ้ำ (จำเป็นมากเพราะต้องซ้อม import หลายรอบ)
5. **ไม่สร้าง Odoo model ใหม่เพื่อเก็บ mapping** — mapping เก็บเป็น CSV ใน `migration/mapping/` (หลีกเลี่ยงการเพิ่มโมดูลที่ไม่มี bounded context)
6. **ลำดับการโหลดตายตัว 1→9** — อ้างอิงลำดับในชีต `00-คู่มือ` ของ workbook: Company/CoA → Journals/Taxes/Terms/Pricelists → Partners → Products → เงื่อนไขซื้อขาย → People/Rights → Projects/Job No./Analytic → ยอดยกมา → Sequences
7. **ยอดยกมาต้อง tie กับ legacy 100%** — เป็นเกณฑ์ผ่านแบบห้ามผ่อนปรน (Gate) ก่อน cut-over
8. **Sequence ต้องต่อเนื่อง** — ไม่รีเซ็ตเลขเอกสาร เพื่อไม่ให้เลขชนกับเอกสารเดิมที่ยังอ้างถึงในระบบเก่า/เอกสารกระดาษ

---

## Precondition

- ได้ **DB dump ของ Odoo 15** (custom format) แล้ว ✅ — มีอยู่แล้ว 2 ไฟล์ใน `migration/od15_export/`: `odoo_golive.dump` (158 MB — ชุด go-live) และ `od15_autoerp_prd.dump` (10 MB — ชุด production ของ ออโต้อินโฟ); รายการไฟล์แนบ (filestore) อยู่ที่ `migration/od15_export/attach_files.txt` → **ไม่ใช่ blocker ลำดับ 1 อีกต่อไป** (อัปเดต 2026-11-02)
- มีสิทธิ์ SSH เข้า server Linux ของ Odoo 15 (`/var/odoo`) และสิทธิ์ `pg_dump`/`psql`
- เครื่อง Windows dev: `c:\odoo-dev\odoo19`, venv `venv19`, config `odoo.conf`, DB พัฒนา `odoo19_pdev` (พอร์ต 8070)
- โมดูล `od19_*` ติดตั้ง/อัปเกรดผ่านได้ปกติ และ snapshot DB ก่อนเริ่ม import ทุกครั้ง
- ฝ่ายบัญชี sign-off **วันตัดยอด (cut-over date)** และยอมรับว่าประวัติย้อนหลังจะดูจาก Odoo 15 (read-only)

**คำสั่งที่ใช้บ่อย (จาก `c:\odoo-dev\odoo19`):**

```powershell
# อัปเดตโมดูลที่เกี่ยวกับการนำเข้า (ถ้ามีการแก้โค้ด)
venv19\Scripts\python.exe odoo-bin -c odoo.conf -d odoo19_pdev -u <module_list> --stop-after-init

# รัน import runner (dry-run ก่อนเสมอ)
$env:MIG_DRY_RUN="1"; $env:MIG_STEPS="s03_partners"
venv19\Scripts\python.exe odoo-bin shell -c odoo.conf -d odoo19_mig_test --no-http < migration\import\run.py
```

> หมายเหตุ: sandbox ของ agent บล็อกการรัน Odoo ผ่าน terminal โดยตรง — ขั้นตอนที่ต้องแตะ DB จริงให้ผู้ใช้รันใน terminal ปกติ

---

## Cut-over Policy

| เรื่อง | ข้อกำหนด |
|---|---|
| วันตัดยอด | วันสิ้นเดือน (แนะนำ 31 ธ.ค. หรือสิ้นเดือนที่ปิดงบได้) — ล็อกด้วย `fiscalyear_lock_date` |
| ช่วง Freeze | Odoo 15 หยุดคีย์เอกสารล่วงหน้า 1 วันทำการก่อน cut-over |
| Delta | เอกสารที่เกิดระหว่างซ้อม import → cut-over (ปกติ 0 รายการถ้า freeze จริง) |
| Rollback | เก็บ Odoo 15 ไว้ใช้งานต่อได้ทันที + snapshot DB 19 ที่สถานะก่อน cut-over |
| เกณฑ์ย้อนกลับ | tie ยอดไม่ได้ / GL ไม่สมดุล / นำเข้าสต็อกไม่ครบ → ย้อนกลับทันที |

---

## Phase 0 — Freeze & Backup (Blocker)

**Deliverable:** ไฟล์ dump + filestore ที่ตรวจ restore ได้จริง

- [ ] 0.1 ยืนยันชื่อ DB และ `data_dir` จาก config ของ Odoo 15 บน server
```bash
grep -E "db_name|db_host|db_user|data_dir" /etc/odoo/odoo.conf /var/odoo/*/odoo.conf 2>/dev/null
```
- [ ] 0.2 ประกาศ **Freeze** ผู้ใช้ Odoo 15 (ห้ามคีย์เอกสารใหม่) และบันทึกเวลาที่ freeze
- [ ] 0.3 Dump DB แบบ custom format
```bash
sudo -u postgres pg_dump -Fc -d <db15> -f /var/backups/db15_$(date +%Y%m%d).dump
```
- [ ] 0.4 สำรอง filestore (attachment/รูป/ลายเซ็น)
```bash
sudo tar -czf /var/backups/filestore15_$(date +%Y%m%d).tgz -C <data_dir>/filestore <db15>
```
- [ ] 0.5 คัดลอกไฟล์ทั้งสองมาเครื่อง Windows และตรวจ checksum (SHA256) ตรงกัน
- [ ] 0.6 **ทดสอบ restore** เป็น DB ชื่อ `od15_stage` บนเครื่อง dev และเปิดหน้า Odoo 15 ชี้ไปที่ DB นี้ได้ (เพื่อยืนยันว่า dump ใช้งานได้จริง)

**Gate 0:** restore สำเร็จ + เปิดดูข้อมูลได้ + checksum ตรง → ถ้าไม่ผ่าน ห้ามเริ่ม Phase 1

---

## Phase 1 — Staging & Profiling

**Deliverable:** ผล profiling ที่กรอกครบใน `legacy-od15-data-profiling-checklist.md` + ทะเบียนโมดูลที่ต้อง map

- [ ] 1.1 ตั้ง `od15_stage` เป็น read-only สำหรับผู้ใช้ profiling (`ALTER DATABASE od15_stage SET default_transaction_read_only = on;`) — **ห้ามรัน profiling บน production DB**
- [ ] 1.2 รัน `migration/extract/01_profiling_queries.sql` และบันทึกผลลง result log ของ checklist
```powershell
psql -h <host> -U <user> -d od15_stage -f migration\extract\01_profiling_queries.sql
```
- [ ] 1.3 ยืนยันเวอร์ชัน Odoo 15 และทะเบียนโมดูล `state='installed'` แยก core / OCA / custom (`autoinfo_*`, `dtr_*`)
- [ ] 1.4 กรอกชีต **"06-พนักงาน-สิทธิ์"**, **"01-ผังบัญชี"** และทะเบียนโมดูล: ระบุว่าโมดูล legacy ใดถูกแทนด้วยโมดูล `od19_*` ใด (อ้างอิง `GAP_ANALYSIS_OD15_to_OD19.md`) หรือ **N-A** (ไม่ย้าย)
- [ ] 1.5 ตรวจ data quality ตาม Section 3 ของ checklist (VAT ผิดรูปแบบ, ชื่อซ้ำ, สินค้าไม่มีรหัส, สต็อกติดลบ, บัญชี code ซ้ำ, เอกสารค้างเกิน 1 ปี) และบันทึกรายการที่ต้องแก้
- [ ] 1.6 บันทึก **baseline ตัวเลข** ที่ต้อง tie หลัง import (Section 4): TB ณ วันตัดยอด, AR/AP aging, สต็อก (qty+value), สินทรัพย์+ค่าเสื่อม, WHT ค้าง, เงินทดรอง, เช็คค้าง, จำนวนเอกสารค้าง

**Gate 1:** ไม่มี blocking data-quality issue ค้าง + baseline ถูกบันทึกและฝ่ายบัญชีรับทราบ

---

## Phase 2 — Mapping & Cut-over Decision

**Deliverable:** mapping workbook ที่กรอกครบทุกชีต + วันตัดยอดที่อนุมัติ

- [ ] 2.1 กรอกชีต **"01-ผังบัญชี"** ให้ครบทุกบัญชีที่มีการเคลื่อนไหว (ห้ามเหลือบัญชีที่มียอดแต่ไม่มี mapping) — ระบุบัญชีที่ต้อง merge
- [ ] 2.2 กรอกชีต **"02-ภาษี-เงื่อนไข"** (Journal/Tax/Payment Term/Pricelist) และ export เป็น `migration/mapping/*.csv` ให้ตรงกับชีต
- [ ] 2.3 กรอกชีต **"03-Partner"** และ **"04-สินค้า"**
- [ ] 2.4 กรอกชีต **"05-เงื่อนไขซื้อขาย"** (7 sale term + 5 purchase term → `od19_sale_terms` / `od19_purchase_terms`)
- [ ] 2.5 กรอกชีต **"07-Project-JobNo"** (รูปแบบ Job No. เป้าหมาย `S + Initials + YY-RunningNumber`)
- [ ] 2.6 กรอกชีต **"08-ยอดยกมา"** และ **"09-Sequence"** (ค่า next number ที่ต้องตั้ง)
- [ ] 2.7 ทบทวนชีต **"10-ความเสี่ยง"** กำหนดเจ้าของ + มาตรการ + ระดับ
- [ ] 2.8 อนุมัติ **วันตัดยอด** และช่วง Freeze อย่างเป็นทางการ

**Gate 2:** workbook สถานะครบ ทุกชีต (ไม่เหลือ TODO ในชีต 01, 08, 09) + วันตัดยอดอนุมัติ

---

## Phase 3 — Sandbox & Scaffold Validation

**Deliverable:** DB ทดสอบที่ import ซ้ำได้โดยไม่เกิดข้อมูลซ้ำ

- [ ] 3.1 สร้าง DB ทดสอบ `odoo19_mig_test` และติดตั้งโมดูล `od19_*` + OCA + `l10n_th` ให้เหมือน production เป้าหมาย
- [ ] 3.2 ตั้งค่า env สำหรับ runner: `OD15_HOST`, `OD15_PORT`, `OD15_DB=od15_stage`, `OD15_USER`, `OD15_PASSWORD`
- [ ] 3.3 ทดสอบ idempotency: รัน `MIG_STEPS=s03_partners` **สองครั้ง** บน DB ทดสอบ → จำนวน partner ต้องเท่าเดิมและไม่มี record ซ้ำ
- [ ] 3.4 ทดสอบโหมด `MIG_DRY_RUN=1` ว่าไม่มีการเขียนข้อมูลจริง (นับ record ก่อน/หลังเท่ากัน)
- [ ] 3.5 ตรวจว่า `migration/mapping/*.csv` ยังมีแถว `EXAMPLE_*` หลงเหลือ → ต้องลบออกทั้งหมดก่อน import จริง
- [ ] 3.6 ตรวจ log ว่าไม่มี warning/error ที่เกิดจากฟิลด์ไม่มีใน DB (ถ้ามีให้ sync schema ด้วย `-u <module>`)

**Gate 3:** รันซ้ำได้ผลเท่าเดิม + dry-run ไม่เขียนข้อมูล + ไม่มีแถว EXAMPLE ค้าง

---

## Phase 4 — Master Data Import (s01 → s07)

**Deliverable:** master data ครบใน DB ทดสอบ แล้วจึงรันกับ `odoo19_pdev`

- [x] 4.1 **s01_reference** — ผังบัญชี, สกุลเงิน, บริษัท, ภาษี (ผ่าน `account_map.csv` / `tax_map.csv`) — ต้องไม่มีบัญชี unmapped
      → ผังบัญชี **นำเข้าแล้ว 316 บัญชี** (จาก 317; ตัด 1 บัญชี 999999 ที่ชนกับ 'Current Year Earnings' ของ Odoo) | สกุลเงิน = THB (ตรง legacy)
      → **โปรไฟล์บริษัท นำเข้าจาก OD15 แล้ว** — ชื่อ "บริษัท ออโต้อินโฟ จำกัด" / VAT `0105540010417` / ที่อยู่ (street เต็ม) / โทร `0-2934-5410-6` / อีเมล `sales@auto-info.co.th` / เว็บไซต์ ตรงกับ OD15; `city`/`zip` ที่ OD15 ไม่มีค่า + `company_registry` ที่ OD15 เก็บสกุลเงิน 'THB' ผิดช่อง ถูกเคลียร์ให้ตรงต้นทาง — รันซ้ำ = "ข้อมูลตรงกับระบบเดิมแล้ว — ไม่ต้องแก้" (idempotent, ดู `migration/import/s01_run.log`)
- [x] 4.2 **s02_master** — Journals, Payment Terms, Pricelists → สมุดรายวัน 24 | เงื่อนไขชำระ 15 | หน่วยนับ 24 | นโยบายราคา 5 | ภาษีจับคู่ได้ 17/30 (ส่วนที่เหลือใช้ภาษีมาตรฐาน l10n_th)
- [x] 4.3 **s03_partners** — partners + ฟิลด์ไทย (`od19_partner_thai_fields`: เลขภาษี/รหัสสาขา) + payment term + salesperson + credit limit → คู่ค้า/ผู้ติดต่อ **1,057 ราย**
- [x] 4.4 **s04_products** — products/UoM/Categories/Supplier Info + วิธีตีราคา FIFO → สินค้า/บริการ **6,464 รายการ** | รายการราคา 1 (ข้าม 1 — สินค้าปิดใช้งาน)
- [x] 4.5 **s05_terms** — เงื่อนไขซื้อ/ขาย master 12 รายการ → ขาย 601 (7 ประเภท) | ซื้อ 86 (5 ประเภท) — รวม **687** (หักชื่อซ้ำตามการออกแบบ)
- [x] 4.6 **s06_people** — พนักงาน/แผนก/ผู้ใช้/กลุ่มสิทธิ์ + ZKTeco device mapping → แผนก 31 | ตำแหน่งงาน 43 | ผู้ใช้ 111 (ผูก) | พนักงาน **113**
- [x] 4.7 **s07_projects** — Projects, Job No., Analytic Account, Project Owner, Project Type → โครงการ **3,188 รายการ**
- [x] 4.8 ตรวจคุณภาพหลัง import: จำนวน record ต่อโมเดลตรงกับ legacy (ภายในส่วนที่ตั้งใจย้าย), ชื่อ/รหัสไม่มี encoding เพี้ยน (ภาษาไทย) → **ผ่าน** — ตรวจครบ 23 โมเดล ไม่มีโมเดลคาดหวังที่หาย (ดู `migration/recon/import_coverage.log`); จำนวนตรงกับ baseline ตามข้อ 5.x
- [ ] 4.9 ตรวจสิทธิ์ผู้ใช้ (Access Rights Governance): กลุ่มที่ไม่มี `privilege_id` จะตกไปอยู่ "Extra Rights" และเห็นเฉพาะโหมด Debug — ต้องจัดกลุ่มใหม่ให้ถูกต้อง

**Gate 4:** master data ครบ + สิทธิ์ผู้ใช้ถูกต้อง + ตัวเลข record ตรงกับ mapping workbook

---

## Phase 5 — Opening Balances Import & Reconciliation (s08)

**Deliverable:** ยอดยกมาที่ tie กับ legacy 100%

- [x] 5.1 **AR/AP** — Opening Journal Entry (`move_type='entry'`) แยกราย partner เพื่อให้ aging ใช้ได้; ต้องผ่านการตรวจของฝ่ายบัญชี → นำเข้า 123 คู่ค้า + 1 ใบไม่ระบุคู่ค้า | ยอดสุทธิ = 16,360,966.40
- [x] 5.2 **สต็อกคงเหลือ** — Inventory Adjustment ตีราคาตามต้นทุน FIFO และ **ต้องสร้าง `stock.valuation.layer`** เสมอ (มิฉะนั้น GL จะไม่ตรงกับมูลค่าสินค้า) → 587 สินค้า | มูลค่า = 24,822,034.22 (ผูก GL 1140.01)
- [x] 5.3 **สินทรัพย์ + ค่าเสื่อมสะสม** — สร้าง `account.asset` ให้ตรงกับทะเบียน legacy → 790 รายการ | มูลค่าทะเบียน 35,752,913.77 | มูลค่าสุทธิ 7,637,061.04
- [x] 5.4 **WHT ค้าง / เงินทดรอง / เช็คค้าง** — นำเข้าตามโมดูล `od19_accounting_cheque`, `od19_accounting_advance` → WHT 1,767 ใบ / เงินจ่ายล่วงหน้า 2,088 ใบ / เช็ค 1,070 ใบ (draft ไม่ลง GL)
- [x] 5.5 Recon #1: Trial Balance ณ วันตัดยอด เทียบ baseline (ต้องเท่ากันทุกบัญชีที่มียอด) → **ผ่าน** GL สมดุล (net=0.00); บัญชีงบดุล 57 บัญชีตรงทั้งหมด
- [x] 5.6 Recon #2: AR/AP aging แยกราย partner เทียบ baseline → **ผ่าน** 135 คู่ (บัญชี×คู่ค้า) ตรงทั้งหมด | ยอดรวม = 16,360,966.40
- [x] 5.7 Recon #3: ปริมาณ + มูลค่าสต็อกแยกรายสินค้า เทียบ baseline → **ผ่าน** มูลค่า OD19 = GL = 24,822,034.22; ปริมาณต่าง 2 หน่วย (สินค้า archive ในระบบเดิม 1 รายการ ไม่ย้าย — อธิบายได้)
- [x] 5.8 Recon #4: จำนวน/มูลค่าสินทรัพย์, WHT, เงินทดรอง, เช็คค้าง เทียบ baseline → **ผ่าน** สินทรัพย์ 790/35,752,913.77/7,637,061.04; WHT 1,766+ข้าม 1=1,767; เงินทดรอง 234,576,379.97; เช็ค 1,070/281,087,579.91
- [ ] 5.9 บันทึกผล reconciliation ลง checklist + ให้ฝ่ายบัญชี sign-off → บันทึกผลแล้ว (เครื่องมือ `migration/recon/run.py`, log `migration/recon/recon.log`) — **รอฝ่ายบัญชี sign-off**

**Gate 5:** Recon #1–#4 ผ่านทั้งหมด (ผลต่าง = 0 ในทุกรายการที่มียอด) — ถ้าไม่ผ่าน **ห้าม** ไป Phase 6
→ **ผลรันล่าสุด: ผ่านทั้งหมด (Recon #1-#4) — ไม่มีผลต่างเกิน 0.01**

---

## Phase 6 — Sequences & Attachments (s09)

- [x] 6.1 ตั้ง `ir.sequence` next number ต่อเนื่องจากเลขล่าสุดของ legacy (แยกตามแผนก เช่น `WH/{DEPT}/...`) → 33 sequences ที่จับคู่ได้ตั้งต่อเนื่องตาม `sequence_map.csv`; รัน s09 = "ปรับเลข 0 / คงเดิม 58" (ทุกตัวปลายทาง ≥ legacy แล้ว) | log `migration/import/s09_run.log`
- [x] 6.2 ทดสอบออกเลขเอกสารใหม่ 1 ฉบับต่อประเภท → ต้องไม่ชนกับเลขเดิม → พยากรณ์เลขถัดไปไม่ consume เลข (เช่น QT26110357, QI26110173, PT2611-0005, PI2611-0003, PVV26110223, VATP/2026/11/2014) | log `migration/recon/sequence_check.log`
- [x] 6.3 (ถ้าจำเป็น) นำเข้า attachment ที่ยังต้องใช้ในระบบใหม่: คัดลอกไฟล์เข้า filestore + สร้างเรกคอร์ด `ir_attachment` ให้สอดคล้องกัน → 7,379 รายการ (เฉพาะที่ผูกกับข้อมูลที่ย้ายแล้ว); รันซ้ำ created=0/skipped=7379
- [x] 6.4 ตรวจว่าไม่มีเอกสารที่ออกเลขแล้วย้อนหลังไปทับช่วงที่ legacy ใช้ไปแล้ว → ตรวจ 33 sequences เทียบ effective (OD15): ผ่าน 33 / ต่ำกว่า legacy 0; ส่วน `skip` ที่ eff>1 (25 รายการ — IV/IS/IS49 PrePrint, APTH, CVP, ...) ไม่มีความเสี่ยงเลขชนเพราะ OD19 ใช้ `tax_invoice_number` เป็น manual Char ไม่มี ir.sequence → บันทึกเป็น "รอการยืนยันคู่ใน OD19"

**Gate 6:** ออกเลขเอกสารใหม่ต่อเนื่องถูกต้อง + ไม่มีเลขชน
→ **ผลรันล่าสุด: ผ่าน** (sequence_check: 33 ผ่าน / 0 ต่ำกว่า legacy; s09 idempotent) — อ้าง `migration/recon/sequence_check.log` + `migration/import/s09_run.log`

---

## Phase 7 — Cut-over Rehearsal & Go-live

- [ ] 7.1 ซ้อม cut-over เต็มรูปแบบบน DB จำลองทั้งหมด (Phase 4→6 ต่อเนื่อง) และจับเวลา
- [ ] 7.2 Snapshot DB ก่อน cut-over จริง (rollback point)
- [ ] 7.3 วันที่จริง: Freeze Odoo 15 → dump รอบสุดท้าย → import delta (ถ้ามี) → รัน Recon ซ้ำ
- [ ] 7.4 ตรวจฟังก์ชันหลักหลัง cut-over: ออกใบเสนอราคา, ยืนยัน SO (ผ่าน credit gate), ออก PO, รับเข้า/เบิกจ่ายสต็อก, ออก Invoice, WHT/เช็ค, พิมพ์รายงานไทย (Sarabun), Dashboard
- [ ] 7.5 เปิดใช้งานจริง + แจ้งผู้ใช้ + ตั้ง watch period

**Gate 7:** ฟังก์ชันหลักผ่านทุกข้อ + Recon ผ่านซ้ำ ณ วันจริง

---

## Phase 8 — Post Go-live & Legacy Archive

- [ ] 8.1 เก็บ Odoo 15 เป็น **read-only archive** (ห้ามคีย์เอกสารใหม่) พร้อมช่องทางค้นประวัติให้ผู้ใช้
- [ ] 8.2 ตรวจ log/warning ของ Odoo 19 ในช่วง watch period และแก้ให้สะอาด
- [ ] 8.3 สรุปบทเรียน + อัปเดต mapping workbook ให้เป็นสถานะ VERIFIED
- [ ] 8.4 ปรับ `GAP_ANALYSIS_OD15_to_OD19.md` และ Wave Matrix ให้สะท้อนสถานะหลัง migration

---

## Acceptance Criteria (ภาพรวม)

1. ไม่มีการแก้ไขไฟล์ core ของ Odoo ทั้งโปรเจกต์
2. ยอดยกมา tie กับ legacy 100% ในทุกหมวด และฝ่ายบัญชี sign-off
3. import ซ้ำได้ (idempotent) โดยไม่เกิดข้อมูลซ้ำหรือข้อมูลขยะ
4. เลขเอกสารใหม่ต่อเนื่อง ไม่ชนกับ legacy
5. สิทธิ์ผู้ใช้สอดคล้องกับ Access Rights Governance
6. Odoo 15 ยังคงเข้าถึงได้เพื่อค้นประวัติ (read-only)
7. log การ import สะอาด ไม่มี warning จากฟิลด์ที่ไม่มีอยู่จริง

---

## Risks (ดูรายละเอียดในชีต "10-ความเสี่ยง")

| # | ความเสี่ยง | มาตรการ |
|---|---|---|
| R01 | ยังไม่มี DB dump ของ Odoo 15 | Phase 0 เป็น blocker — ห้ามเริ่มงานอื่นก่อน |
| R02 | mapping รหัสบัญชีไม่ครบ | ตรวจจำนวนบัญชีที่มียอด vs ที่ map แล้ว ก่อน Phase 5 |
| R03 | เลขเอกสารชนกับของเดิม | ตั้ง sequence ต่อเนื่องจาก legacy (Phase 6) |
| R04 | ยอดสต็อกไม่ตรงกับ GL | บังคับสร้าง `stock.valuation.layer` ทุกครั้งที่ปรับสต็อก |
| R05 | Attachment/filestore ไม่ครบ | ตรวจจำนวนไฟล์ใน filestore เทียบ `ir_attachment` ก่อน Phase 6 |
| R06 | mapping ยอดยกมาผิดจากความต่างของผังบัญชี | ทำ Recon แยกราย partner/บัญชี และให้บัญชี sign-off |
| R07 | ข้อมูลไทยเพี้ยน (encoding/ฟอนต์) | ตรวจชื่อไทยหลัง import + ใช้ `od19_thai_font_support` |
| R08 | Freeze ล่าช้า/มีเอกสารเกิดใหม่ระหว่าง cut-over | กำหนดวัน cut-over + delta import procedure ชัดเจน |

---

## Notes

- **ห้ามลบหรือแก้ข้อมูลใน `od15_stage`** — เป็นหลักฐานอ้างอิงสำหรับ recon และ audit
- ขั้นตอนที่แตะ DB จริงต้องรันโดยผู้ใช้ใน terminal ปกติ (agent sandbox รัน Odoo ไม่ได้)
- ทุกครั้งก่อน import ให้ snapshot DB ปลายทาง (pg_dump) เพื่อย้อนกลับได้
- `migration/` เป็น tooling ภายนอก ไม่ใช่ Odoo module — ห้ามมี `__manifest__.py`
- แถวใน CSV mapping ที่ขึ้นต้นด้วย `EXAMPLE_` จะถูก loader ข้าม แต่ต้องลบออกก่อน import จริงเพื่อความชัดเจน
