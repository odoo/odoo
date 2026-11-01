# การประเมินและแผนใช้งานโมดูล OCA — Odoo 19 CE — เอกสารรวม

| รายการ | รายละเอียด |
|---|---|
| เวอร์ชันเอกสาร | R01 (รวมเอกสาร) |
| วันที่จัดทำ | 2026-11-01 |
| ประเภท | เอกสารรวม (consolidation) — เนื้อหาแต่ละส่วนคงจากต้นฉบับเดิม ไม่ดัดแปลง |
| ขอบเขต | การประเมินโมดูล OCA / การจับคู่ Gap → OCA / แผนติดตั้ง-โรลเอาต์ OCA |
| ระบบอ้างอิง | Odoo 19 CE (`custom_addons/od19_*` + OCA `third_party/oca`) |
| รวมต้นฉบับ | 5 ฉบับ (ดูสารบัญ) |
| เอกสารที่เกี่ยวข้อง | `GAP_ANALYSIS_OD15_to_OD19.md`, `TH_PROCESS_GAP_AND_WAVE6_PLAN_TH.md` |

## สารบัญ

| ส่วน | หัวข้อ | ต้นฉบับเดิม |
|---|---|---|
| 1 | การประเมินโมดูล OCA (ฉบับภาษาไทย) | `OCA_MODULE_ASSESSMENT_TH.md` |
| 2 | OCA Module Assessment (English original) | `OCA_MODULE_ASSESSMENT.md` |
| 3 | การจับคู่ Gap → OCA Solutions | `OCA_MODULE_MATCHING.md` |
| 4 | แผนติดตั้ง / โรลเอาต์ — โมดูล `auditlog` | `OCA_ROLLOUT_PLAN_auditlog_TH.md` |
| 5 | แผนติดตั้ง / โรลเอาต์ — กลุ่ม P1 ที่เหลือ (8 โมดูล) | `OCA_ROLLOUT_PLANS_P1_TH.md` |

> 📌 **หมายเหตุ:** เอกสารนี้เกิดจากการรวมเอกสารที่อยู่ในหมวดเดียวกันให้เหลือฉบับเดียว โดยคงเนื้อหาเดิมของแต่ละส่วนไว้ครบถ้วน ไม่ดัดแปลง (ปรับเฉพาะลิงก์ที่อ้างถึงไฟล์ซึ่งถูกย้ายมารวม ให้ชี้กลับมายังเอกสารนี้)

---

# ส่วนที่ 1 — การประเมินโมดูล OCA (ฉบับภาษาไทย)

> 📄 **ต้นฉบับเดิม:** `OCA_MODULE_ASSESSMENT_TH.md`

# การประเมินโมดูล OCA — Odoo 19 CE (`odoo19`)

**บทบาท:** สถาปนิกเทคนิค Odoo อาวุโส / ผู้ตรวจสอบโมดูล OCA
**ขอบเขต:** วิเคราะห์และให้ข้อเสนอแนะเท่านั้น — **ไม่มีการติดตั้ง อัปเกรด ถอน หรือรันโมดูลใด ๆ**
**แหล่งหลักฐาน:** `odoo.conf`, `.gitmodules`, `custom_addons/*`, manifest ใน `third_party/oca/*`, เอกสารกำกับดูแลใน `docs/superpowers/**`, `OCA_MODULE_ASSESSMENT_TH.md`, `GAP_ANALYSIS_OD15_to_OD19.md`
**วันที่ประเมิน:** 2026-10-15

> ⚠️ **สถานะ (อัปเดต 2026-10-19):** เอกสารนี้เป็น *การประเมินและข้อเสนอแนะ* ณ 2026-10-15 (ก่อนดำเนินการจริง)
> สำหรับสถานะส่งมอบล่าสุด ให้ยึด [GAP_ANALYSIS_OD15_to_OD19.md](GAP_ANALYSIS_OD15_to_OD19.md) (หัวข้อ "สถานะจริง ณ 2026-10-19")
> และผลการติดตั้งชุดเต็ม 251 โมดูล (custom 79 + OCA + core) ที่ผ่านความสะอาดของ log เมื่อ 2026-10-19

> หมายเหตุด้านความเข้ากันได้: โมดูล OCA ที่อ้างถึงทั้งหมดได้รับการตรวจสอบว่า **ประกาศเวอร์ชัน `19.0.x` ใน manifest บน branch `19.0`** (ตรวจ 291 manifest) นี่เป็นการตรวจสอบ **ระดับ manifest เท่านั้น** **ไม่ใช่** การพิสูจน์ว่าทำงานได้จริงในระดับรันไทม์ จุดที่ยืนยันพฤติกรรมรันไทม์ไม่ได้ จะระบุว่า **COMPATIBILITY NOT VERIFIED (runtime)**

---

# เฟส 1 — การวิเคราะห์ระบบปัจจุบัน

## 1.1 ข้อเท็จจริงของแพลตฟอร์ม

| รายการ | ผลที่พบ |
| --- | --- |
| เวอร์ชัน Odoo | 19.0 (Community Edition) |
| อนุกรมสคีมาฐานข้อมูล | 19.0.1.3 |
| ฐานข้อมูล | `odoo19` (PostgreSQL 16.15), `dbfilter = ^odoo19$` |
| Edition | **Community (CE)** — ไม่มีโมดูล Enterprise |
| HTTP | Nginx 1.27.2 → `http_port = 8070`, `gevent_port = 8072`, `proxy_mode = True` |
| URL สาธารณะ | `https://pdev-erp.auto-info.com` (Cloudflare Flexible SSL + DDNS) |
| OS | Windows (Local/Pre-UAT); Linux `/var/odoo` (เป้าหมายเซิร์ฟเวอร์) |
| Workers | `workers = 0` (ปิดโหมด multi-process) |
| Cron threads | `max_cron_threads = 2` |
| Memory guard | soft 2 GB / hard 2.5 GB |
| Time guard | `limit_time_real = 120`, `limit_time_cpu = 60` |
| Logging | `log_level = info`, `logfile = C:\odoo-dev\odoo19\odoo_server.log` |
| DB manager | `list_db = True` ⚠️ |
| Secrets | พบ `db_password` ใน `odoo.conf`; `admin_passwd` แฮชแล้ว (pbkdf2) ⚠️ |

## 1.2 สถาปัตยกรรม Addon

- `addons_path` (พาธสัมบูรณ์ คั่นด้วยจุลภาค): `addons` ของ Odoo core, `custom_addons` และ **OCA Git submodules 13 รายการ** ใต้ `third_party/oca`
- Repository ของ OCA (ทั้งหมด branch `19.0`): `l10n-thailand`, `sale-blanket`, `sale-workflow`, `server-backend`, `server-tools`, `server-ux`, `helpdesk`, `account-financial-tools`, `purchase-workflow`, `tier-validation`, `reporting-engine`, `knowledge`, `website`
- **โมดูลกำหนดเอง:** ประมาณ 80 โมดูลใต้ `custom_addons` นำหน้าด้วย `od19_*`
- **โมดูลที่ติดตั้งแล้ว:** ประมาณ 234 (custom + OCA บางส่วน + core)

## 1.3 OCA ที่ติดตั้งแล้ว (มีอยู่แล้ว — อย่าเสนอเป็น "ของใหม่")

`base_user_role`, `base_exception`, `base_revision`, `base_tier_validation`, `purchase_request_tier_validation`, `sale_blanket_order`, `sale_delivery_state` (sale_stock_delivery_state), `sale_exception`, `sale_order_revision`, `sale_company_currency`, `account_asset_management`, `account_fiscal_year`, `l10n_th_account_tax`, `l10n_th_amount_to_text`, `l10n_th_base_sequence`, `l10n_th_base_utils`, `helpdesk_mgmt`, `helpdesk_mgmt_project`, `helpdesk_product`, `purchase_request`, `report_xlsx`, `report_xlsx_helper`, `document_knowledge`, `document_page`

## 1.4 สถาปัตยกรรมความปลอดภัย / สิทธิ์การเข้าถึง

- **กลุ่มตามบทบาท** ผ่าน `base_user_role` (เป็นพื้นฐานที่ดี)
- **ความปลอดภัยระดับทีม** ในโมดูล helpdesk ที่ขยายเอง (`od19_helpdesk_extension`, `od19_internal_issue`) โดยใช้ group + record rules ใน `security/*.xml`
- **โมดูลควบคุม ISO** (9 โมดูล) พร้อมลำดับเอกสารแยกตามแผนก
- **ไม่มีบันทึกการตรวจสอบระดับเรกคอร์ด (audit trail)** — `auditlog` มีอยู่ใน repo แต่ **ยังไม่ติดตั้ง**
- **ไม่มีประวัติการเปลี่ยนสิทธิ์ผู้ใช้/บทบาท** — `base_user_role_history` มีแต่ยังไม่ติดตั้ง
- **ไม่มีข้อจำกัดการ export** — `base_export_manager` มีแต่ยังไม่ติดตั้ง
- **DB manager เปิดเผย** (`list_db = True`)
- **Secrets อยู่ในไฟล์ config** (`db_password`)

## 1.5 กลไกรายงาน (Reporting)

- QWeb PDF + XLSX ของ Odoo (`report_xlsx`, `report_xlsx_helper` ติดตั้งแล้ว)
- สะพาน Jasper กำหนดเอง (`od19_reporting_jasper`), รายงานภาษีไทย (`od19_thai_tax_reports`), รายงาน WHT, รายงาน payment voucher และโมดูลรายงานอย่างเดียวอีกจำนวนมาก
- **ไม่มีชั้นรายงาน SQL ที่ผู้ใช้กำหนดเองได้** (`bi_sql_editor` / `sql_request_abstract` มีแต่ยังไม่ติดตั้ง)
- **ไม่มีพารามิเตอร์รายงาน** (`report_qweb_parameter` ยังไม่ติดตั้ง)

## 1.6 การมอนิเตอร์ / ล็อก / ระบบอัตโนมัติ

- ล็อกเป็นไฟล์อย่างเดียวที่ระดับ `info`; **ไม่ได้ตั้งค่า log rotation** ใน Odoo
- **ไม่มีการมอนิเตอร์ข้อผิดพลาด** (`sentry` ยังไม่ติดตั้ง)
- **ไม่มีการแจ้งเตือนเมื่อ cron ล้มเหลว** (`scheduler_error_mailer` ยังไม่ติดตั้ง)
- **ไม่มีการสำรองข้อมูลอัตโนมัติ** (`auto_backup` ยังไม่ติดตั้ง) — ขณะที่ baseline ความพร้อมใช้งานจริงกำหนดให้ต้องมีหลักฐาน backup + restore ก่อน go-live
- มีระบบอัตโนมัติผ่าน scheduled/server actions ของ Odoo และเอกสาร discovery ระบุว่าเป็น **จุดเสี่ยงที่รู้อยู่แล้ว**

## 1.7 จุดอ่อนที่พบ (ผลลัพธ์เฟส 1)

**ประสิทธิภาพ (Performance)**
- `workers = 0` → ไม่มีการสเกลแบบ worker/multi-process; request ที่ใช้เวลานานจะบล็อก loop แบบ threaded นี่คือข้อจำกัดการสเกลที่ใหญ่ที่สุดสำหรับ ERP หลายผู้ใช้
- ไม่ได้ตั้ง `limit_request` (ค่าเริ่มต้น 8192) → เสี่ยง request ที่อายุยืนรั่วหน่วยความจำในโหมด worker
- ไม่มี log rotation → ไฟล์ล็อกโตไม่จำกัดทั้งบน Windows และ Linux
- ไม่ควบคุม cron ซ้อนทับ (มี 2 cron threads; ไม่มี guard กันซ้อน)

**ความซ้ำซ้อน / การบำรุงรักษา**
- โมดูลออกเลขเอกสารใกล้เคียงกัน 6 ตัว: `od19_document_sequence`, `od19_accounting_document_sequence`, `od19_quotation_document_sequence`, `od19_purchase_document_sequence`, `od19_project_document_sequence`, `od19_partner_document_sequence`
- `od19_misc_features` เป็นโมดูลรวมของหลายอย่าง (logo ISO, sequence guard, data link, runtime guard, รายงานลูกค้าซื้อซ้ำ) — ผิดหลัก cohesion
- หลายโมดูลดูเหมือนเป็น **โครงร่างเปล่า หรือ report-only** ที่ `models/`/`report/`/`wizard/` มีแต่ `__init__.py` ว่าง (เช่น `od19_accounting_reporting`, `od19_accounting_money_in_report`, `od19_service_card`; ส่วน `od19_accounting_payment_voucher_reports` เป็น report-only ตามดีไซน์) **ต้องตรวจสอบก่อนถือว่าทำงานได้**

**การควบคุมที่ขาดหาย**
- ไม่มี audit trail สำหรับการเขียน/ลบ, ไม่มีประวัติการเปลี่ยนสิทธิ์, ไม่มีการควบคุมการ export
- ไม่มีเครื่องมือจัดระเบียบ/ลบ object ขยะใน DB
- ไม่มีการจัดการ/มองเห็น session (ใครล็อกอินอยู่ที่ไหน)

**จุดอ่อนด้านความปลอดภัย**
- `list_db = True` เปิดช่อง endpoint ของ database manager
- รหัสผ่าน DB เก็บในไฟล์ config แบบข้อความธรรมดา; ต้องยืนยันว่าไม่ถูก commit เข้า VCS
- ไม่มีการบังคับ dbfilter ที่ระดับ proxy (`dbfilter_from_header`) แม้ใช้ Nginx + Cloudflare
- ไม่มีข้อจำกัด "technical user" สำหรับบัญชี service

**ช่องว่างด้านการสังเกตระบบ (Observability)**
- ไม่มีการเก็บข้อผิดพลาดแบบรวมศูนย์, ไม่มีการแจ้งเตือน cron ล้มเหลว, ไม่มีหน้าสืบค้น audit

**ความเสี่ยงด้านคุณภาพข้อมูล**
- การออกเลขเอกสารตามปีและรหัสอ้างอิงคู่ค้าเป็นแบบกำหนดเอง; หากไม่มี audit trail การแก้ไขย้อนหลังจะมองไม่เห็น

---

# เฟส 2 — การค้นหาโมดูล OCA (จำแนกหมวด)

โมดูลทั้งหมดด้านล่างมีอยู่ใน submodule `third_party/oca` ที่ pin ไว้ (branch 19.0) โดยคอลัมน์ "ติดตั้งแล้ว" หมายถึงโมดูลที่ใช้งานอยู่แล้ว

| # | หมวด | ชื่อเทคนิค | Repo | ติดตั้งแล้ว |
| --- | --- | --- | --- | --- |
| 1 | B Monitoring | `auditlog` | server-tools | ไม่ |
| 2 | B Monitoring | `sentry` | server-tools | ไม่ |
| 3 | B Monitoring | `scheduler_error_mailer` | server-tools | ไม่ |
| 4 | D Prevention | `auto_backup` | server-tools | ไม่ |
| 5 | C Troubleshooting | `database_cleanup` | server-tools | ไม่ |
| 6 | A/D Performance/Prevention | `base_cron_exclusion` | server-tools | ไม่ |
| 7 | G Security | `base_export_manager` | server-ux | ไม่ |
| 8 | C/G Troubleshooting/Security | `session_db` | server-tools | ไม่ |
| 9 | F Reporting | `bi_sql_editor` (+`sql_request_abstract`) | reporting-engine | ไม่ |
| 10 | F Reporting | `date_range` (+`date_range_account`) | server-ux | ไม่ |
| 11 | F Reporting | `report_qweb_parameter` | reporting-engine | ไม่ |
| 12 | E/F Workflow/Reporting | `base_comment_template` | reporting-engine | ไม่ |
| 13 | G Security | `base_user_role_history` | server-backend | ไม่ |
| 14 | E Workflow | `server_action_mass_edit` | server-ux | ไม่ |
| 15 | F Reporting | `report_qr` | reporting-engine | ไม่ |
| 16 | D Prevention | `base_cancel_confirm` | server-ux | ไม่ |
| 17 | C Troubleshooting | `upgrade_analysis` | server-tools | ไม่ |
| 18 | E Utility | `base_technical_features` | server-ux | ไม่ |
| 19 | G Security | `base_technical_user` | server-tools | ไม่ |
| 20 | D Prevention | `base_optional_quick_create` | server-ux | ไม่ |
| 21 | D Prevention | `base_time_window` | server-tools | ไม่ |
| 22 | E/D Workflow | `base_substate` | server-ux | ไม่ |
| 23 | G Security | `base_menu_visibility_restriction` | server-ux | ไม่ |
| 24 | E Utility | `filter_multi_user` | server-ux | ไม่ |
| 25 | E Utility | `document_quick_access` | server-ux | ไม่ |
| 26 | A Performance | `base_partition` | server-tools | ไม่ |
| 27 | G Security | `dbfilter_from_header` | server-tools | ไม่ |
| 28 | F Reporting | `report_async` | reporting-engine | ไม่ |
| 29 | F Reporting | `report_qweb_element_page_visibility` | reporting-engine | ไม่ |
| 30 | F Reporting | `kpi` | reporting-engine | ไม่ |
| 31 | B Monitoring | `tracking_manager` | server-tools | ไม่ |
| 32 | E Utility | `base_view_inheritance_extension` | server-tools | ไม่ |
| 33 | D Prevention | `module_auto_update` | server-tools | ไม่ (ดู P4) |

---

# เฟส 3–5 — การประเมินโมดูลแบบละเอียด (17 ฟิลด์ต่อโมดูล)

## 1. `auditlog` — บันทึกการตรวจสอบ (Audit Trail) ✅ P1

1. **หมวด:** B — Monitoring & Anomaly Detection
2. **ชื่อโมดูล:** Audit Log
3. **ชื่อเทคนิค:** `auditlog`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/auditlog`
5. **วัตถุประสงค์:** บันทึกการตรวจสอบระดับ ORM ครบถ้วนสำหรับ create/write/unlink บนโมเดลที่กำหนด
6. **ปัญหาที่แก้ในปัจจุบัน:** ยังไม่มี audit trail ของการเขียน/ลบ; ISO 9001 และความสมบูรณ์ทางการเงินต้องการการตรวจสอบย้อนหลัง รวมถึงการลบ (`auditlog` บันทึก `unlink`) เอกสาร discovery ระบุว่าระบบอัตโนมัติและการแก้ไขข้อมูลเป็นความเสี่ยงที่ยังไม่ปิด
7. **คุณสมบัติหลัก:** ตั้งกฎรายโมเดล; บันทึกค่าเก่า→ใหม่ระดับฟิลด์; บันทึกผู้ใช้, IP, HTTP method; บันทึกการลบ; ค้นหา/export ล็อก; รองรับ trigger ระดับ DB (ทางเลือก)
8. **สถานะความเข้ากันได้:** Manifest `19.0.2.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`, `mail`
10. **ความขัดแย้งที่อาจเกิด:** น้อยมาก. เพิ่มตาราง/trigger. อย่าปรับใช้กับโมเดลชั่วคราวที่ปริมาณสูง (เช่น `mail.message`, `bus.*`, `ir.logging`) เพื่อหลีกเลี่ยง write amplification
11. **ผลกระทบฐานข้อมูล:** เพิ่มตาราง `auditlog.*` และ trigger (ทางเลือก); โตขึ้นตามเวลา — ต้องวางแผน retention
12. **ผลกระทบด้านความปลอดภัย:** เชิงบวก; แสดงประวัติการเปลี่ยนแปลงให้เฉพาะผู้มีสิทธิ์ (มี ACL ของตัวเอง)
13. **ระดับความเสี่ยง:** **MEDIUM**
14. **คำอธิบายความเสี่ยง:** เกี่ยวเข้าไปในเส้นทาง ORM write สำหรับโมเดลที่ตั้งค่า; หากตั้งกฎผิดขอบเขตจะเพิ่ม latency และขนาด DB อย่างมีนัยสำคัญ ถอนติดตั้งได้ แต่ควร archive ตารางล็อกก่อน
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้ง แล้วจำกัดขอบเขตเฉพาะโมเดลที่สำคัญทางการเงิน/ISO
17. **เหตุผล:** ปิดช่องว่างด้านธรรมาภิบาลที่ใหญ่ที่สุดโดยตรง (การตรวจสอบย้อนหลัง) ตามข้อกำหนด ISO 9001 และ baseline ความพร้อมใช้งานจริง

## 2. `sentry` — มอนิเตอร์ข้อผิดพลาด ✅ P1

1. **หมวด:** B — Monitoring & Anomaly Detection
2. **ชื่อโมดูล:** Sentry Integration
3. **ชื่อเทคนิค:** `sentry`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/sentry`
5. **วัตถุประสงค์:** ส่ง exception ของ Python/Odoo (พร้อม traceback, ผู้ใช้, context) ไปยังเซิร์ฟเวอร์ Sentry
6. **ปัญหาที่แก้:** ไม่มีการเก็บข้อผิดพลาดแบบรวมศูนย์; ข้อผิดพลาดบนโปรดักชันอยู่แค่ในไฟล์ล็อกภายในเครื่องและไม่มีการแจ้งเตือน
7. **คุณสมบัติหลัก:** hook ของ logger + WSGI exception, เสริมข้อมูลผู้ใช้/context, ตั้งค่า DSN และ environment, breadcrumbs
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.1`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`; ไลบรารี Python `sentry-sdk` (ต้อง pip เพิ่ม)
10. **ความขัดแย้งที่อาจเกิด:** ไม่คาดว่าจะขัดกับ core; ต้องมีเครือข่ายออกไปยัง endpoint ของ Sentry
11. **ผลกระทบฐานข้อมูล:** **ไม่มี**
12. **ผลกระทบด้านความปลอดภัย:** ส่ง context ข้อผิดพลาดออกนอกเครื่อง — ต้องปิดข้อมูลส่วนบุคคลและห้ามส่ง secrets; หากกังวลเรื่องที่ตั้งข้อมูลควรใช้ DSN แบบ self-hosted
13. **ระดับความเสี่ยง:** **LOW–MEDIUM**
14. **คำอธิบายความเสี่ยง:** ไม่มีการเปลี่ยนสคีมา; ความเสี่ยงคือความเป็นส่วนตัวของข้อมูลขาออก และ dependency `sentry-sdk` ที่ขาดจะทำให้โหลดโมดูลไม่ผ่าน
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งพร้อม DSN ที่ตรวจสอบแล้วและตั้งค่ากรองข้อมูลส่วนบุคคล
17. **เหตุผล:** ให้ประโยชน์ด้าน observability สูงสุดโดยแทบไม่มีต้นทุน DB; เป็นข้อกำหนดเบื้องต้นของ baseline "ต้องมี logging และ monitoring ก่อน go-live"

## 3. `auto_backup` — สำรองฐานข้อมูลอัตโนมัติ ✅ P1

1. **หมวด:** D — Prevention & Protection
2. **ชื่อโมดูล:** Database Auto-Backup
3. **ชื่อเทคนิค:** `auto_backup`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/auto_backup`
5. **วัตถุประสงค์:** dump ฐานข้อมูลตามกำหนดเวลา (และ filestore ถ้าต้องการ) พร้อม retention
6. **ปัญหาที่แก้:** baseline ความพร้อมใช้งานจริงกำหนดให้ต้องมี backup **รวม filestore** และเส้นทาง restore ที่ทดสอบได้; ยังไม่มีโมดูล backup อัตโนมัติติดตั้งอยู่
7. **คุณสมบัติหลัก:** cron backup ราย DB ไปยังโฟลเดอร์ที่กำหนด, retention ตามจำนวน/วัน, backup filestore (ทางเลือก), "backup now" แบบ manual, แจ้งเตือนทางอีเมล
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.1`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`
10. **ความขัดแย้งที่อาจเกิด:** ไม่มีในเชิงฟังก์ชัน. บน Windows พาธ/สิทธิ์ปลายทางต้องเขียนได้โดยบัญชี service ของ Odoo
11. **ผลกระทบฐานข้อมูล:** ไม่กระทบสคีมา; ผลิตไฟล์ dump บนดิสก์ (ต้องตั้ง retention กันดิสก์เต็ม)
12. **ผลกระทบด้านความปลอดภัย:** ไฟล์ backup มีข้อมูลทั้งหมด — เก็บในพาธที่ป้องกัน, ห้ามเปิดผ่านเว็บ, จำกัดการเข้าถึง
13. **ระดับความเสี่ยง:** **LOW–MEDIUM**
14. **คำอธิบายความเสี่ยง:** ไม่มีการเปลี่ยน ORM/สคีมา; ความเสี่ยงคือดิสก์เต็ม (ไม่ตั้ง retention) และไฟล์ backup ไม่ถูกป้องกัน
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้ง; เขียน backup ออกนอกเครื่องแอป; ทดสอบ restore แยกต่างหาก
17. **เหตุผล:** backup + restore เป็นด่านบังคับก่อน go-live. หมายเหตุ: backup ด้วยโมดูล **ไม่ใช่** สิ่งทดแทนการทดสอบ restore และสำเนานอกสถานที่

## 4. `scheduler_error_mailer` — แจ้งเตือน cron ล้มเหลว ✅ P1

1. **หมวด:** B — Monitoring & Anomaly Detection
2. **ชื่อโมดูล:** Scheduler Error Mailer
3. **ชื่อเทคนิค:** `scheduler_error_mailer`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/scheduler_error_mailer`
5. **วัตถุประสงค์:** ส่งอีเมลหาผู้ดูแลเมื่อ scheduled job (`ir.cron`) ล้มเหลว
6. **ปัญหาที่แก้:** baseline เตือนว่า "job ที่ล้มเหลวแบบเงียบ" เป็นตัวบล็อกความพร้อม; ปัจจุบัน cron ที่ล้มเหลวมองไม่เห็น
7. **คุณสมบัติหลัก:** เกี่ยวเข้ากับการจัดการข้อผิดพลาดของ cron, ส่งเมลหาผู้รับที่กำหนดพร้อม job ที่ล้มและ traceback
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`, `mail`
10. **ความขัดแย้งที่อาจเกิด:** ไม่มี
11. **ผลกระทบฐานข้อมูล:** ไม่มี
12. **ผลกระทบด้านความปลอดภัย:** traceback อาจเปิดเผยข้อมูลภายใน — ส่งเฉพาะผู้ดูแลภายใน
13. **ระดับความเสี่ยง:** **LOW**
14. **คำอธิบายความเสี่ยง:** เป็น hook ระดับเมลเท่านั้น; ไม่เปลี่ยนสคีมา; ไม่ override core นอกเส้นทาง cron error
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งและส่งไปยัง alias ของผู้ดูแลภายใน
17. **เหตุผล:** ต้นทุนต่ำ ปิดช่องว่าง "cron ล้มเหลวเงียบ" โดยตรง

## 5. `database_cleanup` — สุขอนามัย DB / แก้ปัญหา ✅ P1

1. **หมวด:** C — Troubleshooting & Fixes
2. **ชื่อโมดูล:** Database Cleanup
3. **ชื่อเทคนิค:** `database_cleanup`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/database_cleanup`
5. **วัตถุประสงค์:** ตรวจหาและลบ object DB ที่ตกค้าง/ซ่อนอยู่ (คอลัมน์, ตาราง, ข้อมูลโมเดล) ที่เหลือจากโมดูลที่ถูกถอด
6. **ปัญหาที่แก้:** โมดูลกำหนดเอง ~80 + OCA จำนวนมากหมุนเวียนตาม Wave; คอลัมน์/ตารางที่ตกค้างสะสมและทำให้บำรุงรักษา/อัปเกรดยาก
7. **คุณสมบัติหลัก:** ลบคอลัมน์/ตาราง, ลบแถวข้อมูลตกค้าง, ลบข้อมูลโมเดล/ฟิลด์, ดูตัวอย่างก่อนลบ, ทำงานระดับ DB เท่านั้น
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.6`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`
10. **ความขัดแย้งที่อาจเกิด:** ไม่มีตอนติดตั้ง; **การดำเนินการลบเป็น manual และต้องตรวจสอบก่อน**
11. **ผลกระทบฐานข้อมูล:** สูงเมื่อใช้งานจริง (ลบคอลัมน์/ตาราง) — แต่เกิดเฉพาะเมื่อผู้ดูแลสั่งชัดเจน
12. **ผลกระทบด้านความปลอดภัย:** จำกัดให้เฉพาะ superuser/กลุ่ม technical
13. **ระดับความเสี่ยง:** **MEDIUM–HIGH**
14. **คำอธิบายความเสี่ยง:** สามารถทำให้ข้อมูลสูญหายแบบย้อนกลับไม่ได้หากใช้โดยไม่ตรวจสอบ ตัวติดตั้งเองไม่เป็นอันตราย ความเสี่ยงอยู่ที่ *การใช้งาน* แนวทางลดความเสี่ยง: backup เต็มก่อน, ใช้ preview แบบ dry-run, จำกัดผู้ดูแลคนเดียว
15. **ลำดับความสำคัญ:** **P1** (ติดตั้งตอนนี้ ใช้อย่างระมัดระวัง)
16. **ข้อเสนอแนะ:** ติดตั้งเพื่อความสามารถด้านบำรุงรักษา; ห้ามรัน purge โดยไม่มี backup ใหม่
17. **เหตุผล:** เครื่องมือบำรุงรักษาระยะยาวที่จำเป็นสำหรับ ERP ที่มีโมดูลกำหนดเองจำนวนมาก; ป้องกันสคีมาเน่าข้าม Wave

## 6. `base_cron_exclusion` — ป้องกัน cron ซ้อนทับ ✅ P1

1. **หมวด:** A — Performance & Optimization / D — Prevention
2. **ชื่อโมดูล:** Base Cron Exclusion
3. **ชื่อเทคนิค:** `base_cron_exclusion`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/base_cron_exclusion`
5. **วัตถุประสงค์:** ป้องกันไม่ให้ scheduled job เดียวกันรันพร้อมกัน (และ mutual-exclusion ระหว่าง job)
6. **ปัญหาที่แก้:** `max_cron_threads = 2` โดยไม่มี guard กันซ้อน → cron ตัวเดิมที่ใช้เวลานานซ้อนทับกันได้ ทำให้ประมวลผลซ้ำและโหลดพุ่ง
7. **คุณสมบัติหลัก:** เพิ่มฟิลด์ "exclusive" บน `ir.cron`; ข้ามการรันถ้า job เดียวกัน/ที่อนุญาตยังรันอยู่
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`
10. **ความขัดแย้งที่อาจเกิด:** ไม่มี
11. **ผลกระทบฐานข้อมูล:** ไม่มี
12. **ผลกระทบด้านความปลอดภัย:** ไม่มี
13. **ระดับความเสี่ยง:** **LOW**
14. **คำอธิบายความเสี่ยง:** เพิ่มฟิลด์เล็ก ๆ บน `ir.cron`; ไม่แทนที่ตรรกะ core
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งและทำเครื่องหมาย job ที่ใช้เวลานานเป็น exclusive
17. **เหตุผล:** ปรับปรุงเสถียรภาพ/การสเกลโดยตรงด้วยความเสี่ยงน้อยมาก; เสริมรันไทม์แบบ threaded (`workers=0`)

## 7. `base_export_manager` — กำกับการ export ✅ P1

1. **หมวด:** G — Access Rights & Security
2. **ชื่อโมดูล:** Base Export Manager
3. **ชื่อเทคนิค:** `base_export_manager`
4. **Repo OCA:** `OCA/server-ux` → `third_party/oca/server-ux/base_export_manager`
5. **วัตถุประสงค์:** ควบคุมว่าใคร export ได้ และจำกัดว่าจะ export โมเดล/ฟิลด์ใดได้
6. **ปัญหาที่แก้:** ปัจจุบันผู้ใช้ทุกคน export แบบ mass ได้ทุกอย่าง — เป็นความเสี่ยงการนำข้อมูลออกสำหรับ ERP ที่มีข้อมูลลูกค้า/การเงิน
7. **คุณสมบัติหลัก:** กฎ export รายโมเดล, allow-list ของฟิลด์, สิทธิ์ export ตามกลุ่ม, UI จัดการกฎ
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`, `web`
10. **ความขัดแย้งที่อาจเกิด:** ต่ำ; เพิ่ม ACL. เปลี่ยน UX การ export — ควรแจ้งผู้ใช้
11. **ผลกระทบฐานข้อมูล:** เพิ่มตารางกฎ `ir.exports.*` ขนาดเล็ก
12. **ผลกระทบด้านความปลอดภัย:** **เชิงบวกอย่างมีนัยสำคัญ** — ลดการเปิดเผยข้อมูลแบบ mass export
13. **ระดับความเสี่ยง:** **LOW–MEDIUM**
14. **คำอธิบายความเสี่ยง:** เปลี่ยนโมเดลสิทธิ์ข้อมูล; กฎที่ตั้งผิดอาจจำกัด export ที่ถูกต้องเกินไป
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งและตั้งค่าเริ่มต้นแบบ deny สำหรับโมเดลอ่อนไหว
17. **เหตุผล:** ปิดช่องว่างการนำข้อมูลออกที่มีอยู่จริง ด้วยโมดูลเบาและขอบเขตชัดเจน

## 8. `session_db` — ควบคุม/ดูแล session ✅ P1

1. **หมวด:** C — Troubleshooting / G — Security
2. **ชื่อโมดูล:** Session DB
3. **ชื่อเทคนิค:** `session_db`
4. **Repo OCA:** `OCA/server-tools` → `third_party/oca/server-tools/session_db`
5. **วัตถุประสงค์:** เก็บ HTTP session ในฐานข้อมูล ทำให้ดูรายการ session และสั่ง terminate ได้
6. **ปัญหาที่แก้:** ไม่มีทางดูหรือสั่งปิด session ที่ใช้งานอยู่; จำเป็นต่อการรับมือเหตุการณ์และการคง session ข้ามการรีสตาร์ต
7. **คุณสมบัติหลัก:** session store บน DB, มุมมอง session สำหรับผู้ดูแล, บังคับ logout, ตั้งอายุได้
8. **สถานะความเข้ากันได้:** Manifest `19.0.1.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `base`
10. **ความขัดแย้งที่อาจเกิด:** session คงอยู่ข้ามการรีสตาร์ต (ผู้ใช้อาจสังเกตได้); ต้องมี cron ทำความสะอาด
11. **ผลกระทบฐานข้อมูล:** เพิ่มตาราง `session.db`-style พร้อมทำความสะอาดเป็นระยะ; มี write ทุกครั้งที่ session refresh (ปานกลาง)
12. **ผลกระทบด้านความปลอดภัย:** เชิงบวก — สั่งปิด session รวมศูนย์เพื่อรับมือเหตุการณ์
13. **ระดับความเสี่ยง:** **LOW–MEDIUM**
14. **คำอธิบายความเสี่ยง:** เปลี่ยนที่จัดเก็บ session; หากไม่ทำความสะอาดตารางจะโต ไม่ override core นอกเหนือ session store
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งพร้อม job ทำความสะอาด session ตามกำหนด
17. **เหตุผล:** คุณค่าด้านปฏิบัติการ/ความปลอดภัยสูงสำหรับ instance ที่เปิดผ่าน Cloudflare; ผลกระทบวงกว้างน้อย

## 9. `bi_sql_editor` (+ `sql_request_abstract`) — รายงานที่กำหนดค่าได้ ✅ P1

1. **หมวด:** F — Data Processing & Reporting
2. **ชื่อโมดูล:** BI SQL Editor (dependency: SQL Request Abstract)
3. **ชื่อเทคนิค:** `bi_sql_editor`, `sql_request_abstract`
4. **Repo OCA:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/bi_sql_editor`, `.../sql_request_abstract`
5. **วัตถุประสงค์:** สร้าง SQL view แบบอ่านอย่างเดียวและเปิดเป็นรายงาน list/pivot/graph พร้อม export โดยไม่ต้องเขียนโค้ด
6. **ปัญหาที่แก้:** KPI/การรวมข้อมูลเพื่อเจ้าของกิจการในปัจจุบันต้องสร้างโมดูลรายงาน Python เฉพาะทีละรายงาน; โมดูลนี้ให้ admin นิยามผลลัพธ์เชิงวิเคราะห์เองได้
7. **คุณสมบัติหลัก:** เครื่องมือแก้ SQL view พร้อม validation, สร้าง list/pivot/graph อัตโนมัติ, action drill-down, materialised view, สร้างเมนู/action, ACL
8. **สถานะความเข้ากันได้:** Manifest `bi_sql_editor` `19.0.2.0.1`, `sql_request_abstract` `19.0.1.0.0`. รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
9. **Dependencies:** `sql_request_abstract` → `base`
10. **ความขัดแย้งที่อาจเกิด:** ไม่มีกับโมดูลรายงานที่มีอยู่ (อยู่ร่วมกันได้) หากโมดูลกำหนดเองเปิด query เดียวกันอยู่แล้ว ควรเลือกแหล่งเดียว
11. **ผลกระทบฐานข้อมูล:** สร้าง DB view/materialised view — เป็น object สคีมาที่โมดูลเป็นเจ้าของ; ต้องจัดทำเอกสาร
12. **ผลกระทบด้านความปลอดภัย:** **สูงขึ้น** — SQL ดิบมีพลังมาก ต้องจำกัดให้กลุ่มที่เชื่อถือได้; ควรใช้ **DB role แบบ read-only** สำหรับ view
13. **ระดับความเสี่ยง:** **MEDIUM**
14. **คำอธิบายความเสี่ยง:** ให้สิทธิ์เขียน SQL แก่ผู้ใช้ระดับสูงและสร้าง object DB ถาวร การใช้ผิดอาจเสี่ยงเปิดเผยข้อมูลหรือ query หนัก แนวทางลดความเสี่ยง: ใช้กลุ่ม read-only และทบทวน query
15. **ลำดับความสำคัญ:** **P1**
16. **ข้อเสนอแนะ:** ติดตั้งสำหรับ admin จำนวนน้อย; บังคับ SQL read-only และทบทวน query
17. **เหตุผล:** สนับสนุนเป้าหมายรายงานเพื่อเจ้าของกิจการของโปรแกรมโดยตรง และลดโค้ดกำหนดเองต่อรายงาน ทางเลือกอื่น (โมดูลกำหนดเองหนึ่งต่อรายงาน) บำรุงรักษามากกว่า

## 10. `date_range` (+ `date_range_account`) — ช่วงเวลารายงาน ✅ P2

1. **หมวด:** F — Reporting
2. **ชื่อเทคนิค:** `date_range`, `date_range_account`
3. **Repo OCA:** `OCA/server-ux` → `third_party/oca/server-ux/date_range`, `date_range_account`
4. **วัตถุประสงค์:** ช่วงวันที่ที่ใช้ซ้ำได้และผู้ใช้กำหนดเอง (รอบบัญชี, ช่วงเวลากำหนดเอง) ใช้ในตัวกรอง/domain ของรายงาน
5. **ปัญหาที่แก้:** รายงานตามรอบบัญชีปัจจุบันทำแบบ ad-hoc; `date_range_account` เป็น dependency มาตรฐานของรายงานบัญชีตามรอบ
6. **คุณสมบัติหลัก:** ช่วงที่มีชื่อ (แบบ fix/window), กฎตัวสร้าง, แยกรายบริษัท, hook รวมกับรายงาน
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**
8. **Dependencies:** `base`; `date_range_account` → `account`, `date_range`
9. **ความขัดแย้ง:** ไม่มี (อาจถูกดึงเป็น dependency โดยโมดูลรายงาน OCA อื่น)
10. **ผลกระทบ DB:** ตาราง `date_range.*` ขนาดเล็ก
11. **ผลกระทบด้านความปลอดภัย:** เป็นกลาง
12. **ความเสี่ยง:** **LOW** — เพิ่มเติม เบา
13. **คำอธิบายความเสี่ยง:** ไม่ override core; เป็นเพียงข้อมูลอ้างอิงใหม่
14. **ลำดับความสำคัญ:** **P2**
15. **ข้อเสนอแนะ:** ติดตั้งเมื่อตั้งค่ารายงานตามรอบเวลา
16. **เหตุผล:** เป็น building block มาตรฐาน; คุณค่าต่ำจนกว่ารายงานจะนำไปใช้ จากนั้นให้ประโยชน์สูง

## 11. `report_qweb_parameter` — พารามิเตอร์รายงานที่ผู้ใช้ตั้งได้ ✅ P2

1. **หมวด:** F — Reporting
2. **ชื่อเทคนิค:** `report_qweb_parameter`
3. **Repo OCA:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/report_qweb_parameter`
4. **วัตถุประสงค์:** เพิ่มพารามิเตอร์ที่ผู้ใช้แก้ได้และมี validation ให้รายงาน QWeb (เลี่ยงการแก้ template ด้วยมือ)
5. **ปัญหาที่แก้:** การปรับรายงาน (ข้อความหัวบริษัท, หมายเหตุท้าย) ต้องให้นักพัฒนาแก้ XML
6. **คุณสมบัติหลัก:** นิยามพารามิเตอร์ต่อรายงาน พร้อมชนิด/validation, แก้ได้ตอนสั่งพิมพ์
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**
8. **Dependencies:** `base`
9. **ความขัดแย้ง:** ไม่คาดว่าเกิด; เสริมรายงาน QWeb/ISO ที่กำหนดเอง
10–11. **DB/ความปลอดภัย:** ตารางพารามิเตอร์เล็ก; ความปลอดภัยเป็นกลาง
12–13. **ความเสี่ยง:** **LOW** — ไม่ override core
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ติดตั้งสำหรับรายงานที่ต้องการพารามิเตอร์รันไทม์
16. **เหตุผล:** ลดรอบการแก้ไขโดยนักพัฒนาสำหรับการเปลี่ยนรายงานroutine

## 12. `base_comment_template` — บล็อกความเห็นที่ใช้ซ้ำได้ ✅ P2

1. **หมวด:** E/F — Workflow / Reporting
2. **ชื่อเทคนิค:** `base_comment_template`
3. **Repo OCA:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/base_comment_template`
4. **วัตถุประสงค์:** นิยามบล็อกความเห็นที่ใช้ซ้ำได้ แนบกับเอกสารและพิมพ์บนรายงาน
5. **ปัญหาที่แก้:** ข้อกำหนด/หมายเหตุถูกทำซ้ำในแต่ละโมดูล (`od19_sale_terms`, `od19_purchase_terms`) — คลัง template เดียวจะลดความซ้ำซ้อน
6. **คุณสมบัติหลัก:** โมเดล template, ใช้ตาม domain, เปิด/ปิดการพิมพ์/placeholder, โหมดแทนที่หรือต่อท้าย
7. **ความเข้ากันได้:** Manifest `19.0.0.0.2` (หมายเหตุ: การ port 19.0 ยังอยู่ในช่วงต้นมาก). รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)**
8. **Dependencies:** `base`
9. **ความขัดแย้ง:** อาจ **ทับซ้อน** กับโมดูลข้อกำหนดกำหนดเองที่มีอยู่ — ต้องตัดสินใจแหล่งข้อมูลเดียว (source of truth) ก่อนนำมาใช้
10–11. **DB/ความปลอดภัย:** ตาราง template เล็ก; เป็นกลาง
12–13. **ความเสี่ยง:** **LOW–MEDIUM** — ความเสี่ยงทางเทคนิคต่ำ แต่ port ระยะต้นและทับซ้อนเชิงฟังก์ชัน
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ประเมินเทียบกับ `od19_*_terms` ก่อนนำมาใช้; อย่ารันทั้งสองพร้อมกัน
16. **เหตุผล:** เครื่องมือลดความซ้ำที่ดี แต่ใช้ได้ต่อเมื่อมัน *แทนที่* (ไม่ใช่ทำซ้ำ) ข้อกำหนดกำหนดเองที่มีอยู่

## 13. `base_user_role_history` — ตรวจสอบการเปลี่ยนสิทธิ์ ✅ P2

1. **หมวด:** G — Access Rights & Security
2. **ชื่อเทคนิค:** `base_user_role_history`
3. **Repo OCA:** `OCA/server-backend` → `third_party/oca/server-backend/base_user_role_history`
4. **วัตถุประสงค์:** ติดตามการเปลี่ยนแปลงของผู้ใช้/บทบาท (ใครเปลี่ยนอะไร เมื่อไร)
5. **ปัญหาที่แก้:** การเปลี่ยนสิทธิ์ไม่มีการติดตาม; ตอบคำถาม "ใครให้สิทธิ์นี้" ได้ยาก
6. **คุณสมบัติหลัก:** ล็อกประวัติการเปลี่ยนบทบาท/ผู้ใช้, snapshot บทบาทปัจจุบัน/ก่อนหน้า, รวมกับ chatter
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**. ต้องพึ่ง `base_user_role` ที่ติดตั้งแล้ว
8. **Dependencies:** `base_user_role`
9. **ความขัดแย้ง:** ไม่มี (ขยายโมเดลบทบาทที่ติดตั้งแล้ว)
10–11. **DB/ความปลอดภัย:** เพิ่มแถวประวัติ; **คุณค่าด้านความปลอดภัยเชิงบวก**
12–13. **ความเสี่ยง:** **LOW** — เพิ่มเติมบนฐานที่ติดตั้งแล้ว
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ติดตั้งคู่กับ `auditlog`
16. **เหตุผล:** การตรวจสอบความปลอดภัยที่ตรงจุดและต้นทุนต่ำสำหรับชั้น RBAC

## 14. `server_action_mass_edit` — แก้ไขเป็นกลุ่ม ✅ P2

1. **หมวด:** E — Utilities & Workflow
2. **ชื่อเทคนิค:** `server_action_mass_edit`
3. **Repo OCA:** `OCA/server-ux` → `third_party/oca/server-ux/server_action_mass_edit`
4. **วัตถุประสงค์:** server action ประเภทแก้ไขฟิลด์เป็นกลุ่มบนเรกคอร์ดที่เลือก
5. **ปัญหาที่แก้:** การแก้ไขข้อมูลเป็นกลุ่มในปัจจุบันต้องใช้สคริปต์เฉพาะกิจหรือแก้ทีละเรกคอร์ด
6. **คุณสมบัติหลัก:** mass update ตาม domain, ดูตัวอย่างเรกคอร์ดที่จะกระทบ, กำหนดค่าต่อฟิลด์, รันจาก server action
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**
8. **Dependencies:** `base`
9. **ความขัดแย้ง:** ไม่มี
10–11. **DB/ความปลอดภัย:** เขียนหลายเรกคอร์ดพร้อมกันได้ → จำกัดให้กลุ่มที่เชื่อถือได้; เพิ่มเฉพาะการตั้งค่า action
12–13. **ความเสี่ยง:** **MEDIUM** — mass write อาจเปลี่ยนข้อมูลวงกว้างโดยไม่ตั้งใจหาก domain ผิด
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ติดตั้ง จำกัดให้กลุ่ม admin/technical
16. **เหตุผล:** เพิ่มผลิตภาพจริงสำหรับงานแก้ไขข้อมูล แต่ต้องมี guard ด้านสิทธิ์

## 15. `report_qr` — QR Code บนรายงาน ✅ P2

1. **หมวด:** F — Reporting
2. **ชื่อเทคนิค:** `report_qr`
3. **Repo OCA:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/report_qr`
4. **วัตถุประสงค์:** แสดง QR code ในรายงาน QWeb
5. **ปัญหาที่แก้:** ระบบ e-tax/e-invoice ไทยและการตรวจสอบมีแนวโน้มต้องมีเนื้อหา QR บนเอกสารพิมพ์
6. **คุณสมบัติหลัก:** helper QWeb สำหรับฝังภาพ QR จาก payload ใด ๆ
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**; ต้องมีไลบรารี Python `qrcode` (pip เพิ่ม)
8. **Dependencies:** `base` (+ ไลบรารี `qrcode`)
9. **ความขัดแย้ง:** ไม่มี
10–11. **DB/ความปลอดภัย:** ไม่มี/น้อยมาก
12–13. **ความเสี่ยง:** **LOW** — เป็น helper แสดงผลเท่านั้น
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ติดตั้งเมื่อต้องมีเอกสารที่มี QR
16. **เหตุผล:** เล็ก เป็นมาตรฐาน และเปิดทางให้ผลลัพธ์การพิมพ์พร้อม compliance

## 16. `base_cancel_confirm` — guard การยกเลิก ✅ P2

1. **หมวด:** D — Prevention & Protection
2. **ชื่อเทคนิค:** `base_cancel_confirm`
3. **Repo OCA:** `OCA/server-ux` → `third_party/oca/server-ux/base_cancel_confirm`
4. **วัตถุประสงค์:** บังคับให้ยืนยันชัดเจนก่อนยกเลิกเรกคอร์ด
5. **ปัญหาที่แก้:** การยกเลิกออเดอร์/ใบแจ้งหนี้โดยไม่ตั้งใจสามารถเกิดขึ้นได้โดยไม่มี guard เพิ่มเติม — ตรงกับวัตถุประสงค์ "ป้องกันข้อผิดพลาดในการปฏิบัติงาน" ของโครงการ
6. **คุณสมบัติหลัก:** wizard ยืนยันตอนยกเลิกสำหรับโมเดลที่เปิดใช้
7. **ความเข้ากันได้:** `19.0.1.0.0`. รันไทม์ **NOT VERIFIED**
8. **Dependencies:** `base`
9. **ความขัดแย้ง:** ไม่คาดว่าเกิด; ตรวจสอบกับ override การยกเลิกใน `od19_sale_wizards`/`od19_purchase_wizards`
10–11. **DB/ความปลอดภัย:** ไม่มี; เป็น guard ระดับ UX ที่เพิ่มเติม
12–13. **ความเสี่ยง:** **LOW** — guard ระดับ UI
14. **ลำดับความสำคัญ:** **P2** / 15. **ข้อเสนอแนะ:** ติดตั้งสำหรับโมเดลที่มีนัยสำคัญทางการเงิน
16. **เหตุผล:** บริการวัตถุประสงค์ด้านการป้องกันโดยตรงด้วยความเสี่ยงน้อยมาก

---

## เฟส 3–5 — การประเมินแบบย่อ (P3 / P4)

| โมดูล | หมวด | Repo | เวอร์ชัน (manifest) | ความเสี่ยง | เหตุผล | ลำดับ |
| --- | --- | --- | --- | --- | --- | --- |
| `upgrade_analysis` | C | server-tools | 19.0.1.1.4 | MEDIUM | เทียบสคีมา/ข้อมูลข้ามเวอร์ชัน; สำคัญต่อความปลอดภัยในการอัปเกรด OCA/custom; ต้องมี reference revision | P2 |
| `base_technical_features` | E | server-ux | 19.0.1.0.0 | LOW | เปิดฟิลด์เทคนิคให้กลุ่มเฉพาะ; ช่วยแก้ปัญหา | P3 |
| `base_technical_user` | G | server-tools | 19.0.1.0.0 | LOW | บล็อกการใช้ผู้ใช้ "technical" เป็นทางลัด API; hardening | P3 |
| `base_optional_quick_create` | D | server-ux | 19.0.1.0.0 | LOW | ป้องกันการสร้างเร็วซ้ำโดยไม่ตั้งใจ | P3 |
| `base_time_window` | D | server-tools | 19.0.1.0.0 | LOW–MEDIUM | ตรวจสอบช่วงวันที่ไม่ทับซ้อน; เหมาะกับสัญญา/แผนงาน | P3 |
| `base_substate` | E | server-ux | 19.0.1.0.0 | LOW | สถานะย่อยของเรกคอร์ด; ทับซ้อนฟิลด์สถานะกำหนดเอง | P3 |
| `base_menu_visibility_restriction` | G | server-ux | 19.0.1.0.0 | LOW | ซ่อนเมนูตามกลุ่ม — สะอาดกว่าการทำเมนูซ้ำ | P3 |
| `filter_multi_user` | E | server-ux | 19.0.1.0.0 | LOW | ตัวกรองใช้ร่วมในทีม; ได้ UX | P3 |
| `document_quick_access` | E | server-ux | 19.0.1.0.0 | LOW | ลิงก์เอกสารเร็ว; UX เล็กน้อย | P3 |
| `base_partition` | A | server-tools | 19.0.1.0.0 | MEDIUM–HIGH | partition ตารางขนาดใหญ่มาก (log/auditlog). ใช้เมื่อพิสูจน์แล้วว่าโตจริง | P3 |
| `dbfilter_from_header` | G | server-tools | 19.0.1.0.0 | MEDIUM | บังคับ dbfilter ที่ proxy — แต่โครงการ pin `dbfilter` และใช้ DB เดียวอยู่แล้ว; เกี่ยวเฉพาะ multi-DB ผ่าน Nginx | P3 |
| `report_async` | F | reporting-engine | 19.0.1.0.0 | MEDIUM | สร้างรายงานหนักแบบ async; ต้องมี queue. ใช้เมื่อมีรายงานใหญ่ | P3 |
| `report_qweb_element_page_visibility` | F | reporting-engine | 19.0.1.0.0 | LOW | แสดง/ซ่อนองค์ประกอบหน้าแรก/หน้าสุดท้าย — รองรับข้อกำหนดวาง footer ISO | P3 |
| `kpi` | F | reporting-engine | 19.0.1.0.1 | LOW–MEDIUM | คำนวณ/แสดง KPI; ทับซ้อน BI SQL Editor + dashboard. เลือกอย่างเดียว | P3 |
| `tracking_manager` | B | server-tools | 19.0.1.0.1 | LOW | ตั้งค่า field tracking โดยไม่เขียนโค้ด; ทับซ้อน `auditlog` | P3 |
| `base_view_inheritance_extension` | E | server-tools | 19.0.1.0.0 | LOW | XPath ที่ยืดหยุ่นขึ้นใน view ที่ inherit; สะดวกเฉพาะนักพัฒนา | P3 |
| `base_kanban_stage` | E | server-tools | 19.0.1.0.0 | LOW | โมเดล stage ทั่วไป; ใช้เมื่อสร้าง kanban pipeline | P3 |
| `attachment_unindex_content` | A | server-tools | 19.0.1.0.0 | LOW–MEDIUM | ข้ามการทำดัชนีเนื้อหาไฟล์แนบเพื่อลดโหลด — แต่โครงการ *ต้องการ* ทำดัชนี PDF (pdfminer.six); ขัดกับเจตนา | P4 ตามเจตนาปัจจุบัน |
| `sequence_python` | E | server-tools | 19.0.1.0.0 | LOW | ค่าลำดับจาก Python; โมดูลกำหนดเองอาจครอบคลุมแล้ว | P3 |
| `module_auto_update` | D | server-tools | 19.0.1.0.1 | **HIGH** | อัปเดตโมดูลอัตโนมัติเมื่อโค้ดเปลี่ยน — อันตรายกับ 13 OCA submodule + ~80 โมดูลกำหนดเอง; อาจกระตุ้นการอัปเกรดสคีมาโดยไม่ตั้งใจตอนโหลด | **P4** |
| `module_change_auto_install` | D | server-tools | 19.0.1.0.0 | MEDIUM | ติดตั้งโมดูลอัตโนมัติเมื่อไฟล์เปลี่ยน; ความเสี่ยงคลาสเดียวกับข้างบน | P3–P4 |
| `rpc_helper` | C | server-tools | 19.0.1.0.0 | LOW | ตัวช่วย RPC/ดีบัก URL — เครื่องมือนักพัฒนาเท่านั้น | P3 |
| `base_search_fuzzy` | A | server-tools | 19.0.1.0.0 | MEDIUM | ค้นหาแบบ trigram; เพิ่ม DB extension และต้นทุน index. ใช้เมื่อพิสูจน์ว่าค้นหาช้า | P4 |
| `base_external_dbsource` | — | server-backend | 19.0.1.0.0 | **HIGH** | เชื่อมต่อ DB ภายนอกได้ตามอำเภอใจ — พื้นผิวโจมตี/นำข้อมูลออก. ไม่แนะนำ | **P4** |
| `bus_alt_connection` | — | server-tools | 19.0.1.0.0 | MEDIUM | bus/IM connection อีกทาง; ยังไม่พบความจำเป็น | P4 |
| `iap_alternative_provider` | — | server-tools | 19.0.1.0.0 | MEDIUM | ใช้เมื่อต้องเปลี่ยนผู้ให้บริการ IAP ของ Odoo | P4 |
| `onchange_helper` | E | server-tools | 19.0.1.0.0 | LOW | ตัวช่วยนักพัฒนา; ไม่มีความจำเป็นทางธุรกิจ | P4 |
| `base_fontawesome` | E | server-tools | 19.0.1.0.0 | LOW | แพ็กชุดไอคอน; Odoo มีไอคอนให้แล้ว | P4 |
| `base_write_diff` | B | server-tools | 19.0.1.0.0 | LOW | ล็อก write diff ลงไฟล์; ทับซ้อน `auditlog` | P4 |

---

# เฟส 6 — การตรวจสอบความซ้ำซ้อนและความขัดแย้ง

| โมดูลที่เสนอ | Core/EE | OCA ที่ติดตั้ง | โมดูลกำหนดเอง | ข้อสรุป |
| --- | --- | --- | --- | --- |
| `auditlog` | Core มีแค่ tracking ผ่าน `mail.thread` (ระดับฟิลด์ ต่อโมเดล) — **ไม่ใช่** audit trail ของ write/delete เต็มรูปแบบ | — | มีการใช้ `tracking=True` ในโมเดล ISO (บางส่วน) | **เพิ่มความสามารถ** ไม่ใช่ของซ้ำจริง |
| `sentry` | Core ล็อกลงไฟล์เท่านั้น | — | — | ไม่ซ้ำ |
| `auto_backup` | Core ไม่มีตัวจัดตาราง backup ในตัว | — | — | ไม่ซ้ำ |
| `scheduler_error_mailer` | Core ล็อก cron ล้มเหลวแบบเงียบ | — | — | ไม่ซ้ำ |
| `database_cleanup` | `upgrade_analysis` (คนละวัตถุประสงค์) | — | — | ไม่ซ้ำ |
| `base_cron_exclusion` | `ir.cron` ของ core ไม่มี mutual-exclusion | — | `od19_misc_features.runtime_guard` ไม่เกี่ยวข้อง (guard AR/AP) | ไม่ซ้ำ |
| `base_export_manager` | export ของ core ไม่มี ACL | — | — | ไม่ซ้ำ |
| `session_db` | session ของ core อยู่บน filesystem | — | — | ไม่ซ้ำ |
| `bi_sql_editor` | Core มีเฉพาะ "Pivot/Graph" บนโมเดลที่มีอยู่ | `report_xlsx` (เพียงรูปแบบผลลัพธ์) | โมดูลรายงานกำหนดเองหลายตัว | ไม่ซ้ำ; **ลด** โมดูลกำหนดเองในอนาคต |
| `date_range` | Core มี util ปีบัญชี แต่ไม่มีช่วงที่ผู้ใช้กำหนดเอง | — | — | ไม่ซ้ำ |
| `report_qweb_parameter` | QWeb ของ core แก้ต้องเขียนโค้ด | — | — | ไม่ซ้ำ |
| `base_comment_template` | — | — | `od19_sale_terms`, `od19_purchase_terms` | **ทับซ้อน** — นำมาใช้ต่อเมื่อแทนที่โมดูล terms กำหนดเอง |
| `base_user_role_history` | — | `base_user_role` (ติดตั้งแล้ว) | — | เสริมฐานที่ติดตั้งแล้ว |
| `server_action_mass_edit` | Core มี server actions แต่ไม่มี UI mass-edit | — | — | ไม่ซ้ำ |
| `report_qr` | Core ไม่มี helper QR | — | — | ไม่ซ้ำ |
| `base_cancel_confirm` | Core แค่ยกเลิก | — | มี override การยกเลิกกำหนดเอง | ต้องตรวจสอบการทำงานร่วม |
| `module_auto_update` | — | — | — | เสี่ยงและซ้ำซ้อนกับการ deploy แบบควบคุม |
| `attachment_unindex_content` | — | — | memory: ต้องการทำดัชนี PDF (pdfminer.six) | **ขัดกับเจตนา** — ข้าม |
| `base_external_dbsource` | — | — | — | **คำแนะนำเชิงลบด้านความปลอดภัย** |

---

# เฟส 7 — ผลลัพธ์

## บทสรุปผู้บริหาร (Executive Summary)

instance `odoo19` เป็น **Odoo 19 CE greenfield ที่มีโครงสร้างดี** ด้วยแนวทาง "OCA-first, custom-second" อย่างมีวินัย มี OCA submodule 13 รายการที่ pin ไว้ และโมดูลกำหนดเอง `od19_*` ~80 ตัว ครอบคลุม sales, purchasing, accounting, ISO, helpdesk และ inventory รากฐานสถาปัตยกรรมแข็งแรงดี อย่างไรก็ตาม ระบบมีความ **ไม่สมดุลของวุฒิภาวะ** ชัดเจน: ด้าน *ธุรกิจ* ครอบคลุมดี แต่ **ชั้นปฏิบัติการ/ธรรมาภิบาลบาง** สรุปคือ:

1. **ไม่มี audit trail, ไม่มีการมอนิเตอร์ข้อผิดพลาด, ไม่มีการแจ้งเตือน cron ล้มเหลว, ไม่มี backup อัตโนมัติ, ไม่มีการควบคุม export และไม่มีการจัดการ session** — ทั้งหมดนี้ baseline *ความพร้อมใช้งานจริง* ของโครงการเองกำหนดให้ต้องมีก่อน go-live และ ISO 9001 ต้องการการตรวจสอบย้อนหลัง
2. **รันไทม์เป็นแบบ single-process threaded (`workers = 0`)** และไม่มี guard กัน cron ซ้อน — เป็นข้อจำกัดด้านการสเกล/เสถียรภาพหลักสำหรับ ERP หลายผู้ใช้
3. **จุดอ่อนด้านความปลอดภัย 2 จุดชัดเจน:** DB manager เปิดเผย (`list_db = True`) และรหัสผ่าน DB อยู่ในไฟล์ config แบบข้อความธรรมดา (ต้องยืนยันการกันออกจาก VCS)
4. **หนี้ด้านการบำรุงรักษา** ในชั้นกำหนดเอง: โมดูลออกเลขเอกสารขนานกัน 6 ตัว, โมดูลรวมของหลายอย่าง 1 ตัว (`od19_misc_features`) และโมดูลที่ดูเหมือนโครงร่างเปล่า/report-only หลายตัว ควรตรวจสอบหรือรวม

แนวทางที่แนะนำคือ **ไม่** เน้นปริมาณ แต่ใช้ **โมดูล P1 ประมาณ 9 ตัว** ที่ปิดช่องว่างด้านปฏิบัติการ ความปลอดภัย และ observability ด้วยความเสี่ยง LOW–MEDIUM พร้อมรายการ P2 สั้น ๆ สำหรับ reporting และ workflow มีหลายโมดูลที่ **ไม่แนะนำอย่างชัดเจน** (auto-update โมดูล, external DB source, fuzzy search, de-index ไฟล์แนบ) เพราะเพิ่มความเสี่ยงหรือขัดกับเจตนาที่มีอยู่

## ข้อเสนอแนะอันดับต้น (มูลค่าสูงสุด)

| อันดับ | โมดูล | คุณค่า | ความเสี่ยง | ลำดับ |
| --- | --- | --- | --- | --- |
| 1 | `auditlog` | การตรวจสอบ write/delete ครบถ้วน (ISO + การเงิน) | MEDIUM | P1 |
| 2 | `sentry` | มอนิเตอร์ข้อผิดพลาดรวมศูนย์ | LOW–MEDIUM | P1 |
| 3 | `auto_backup` | ระบบสำรองอัตโนมัติ (ด่าน go-live) | LOW–MEDIUM | P1 |
| 4 | `base_export_manager` | หยุดการนำข้อมูลออกแบบ mass | LOW–MEDIUM | P1 |
| 5 | `scheduler_error_mailer` | ยุติปัญหา cron ล้มเหลวเงียบ | LOW | P1 |
| 6 | `base_cron_exclusion` | ป้องกัน cron ซ้อนทับ | LOW | P1 |
| 7 | `database_cleanup` | สุขอนามัยสคีมาระยะยาว | MEDIUM–HIGH (เฉพาะปฏิบัติการ) | P1 |
| 8 | `session_db` | มองเห็น/สั่งปิด session | LOW–MEDIUM | P1 |
| 9 | `bi_sql_editor` | รายงานเพื่อเจ้าของกิจการที่กำหนดค่าได้ | MEDIUM | P1 |

## ข้อเสนอแนะด้านความปลอดภัย (Security)

- **`auditlog`** (P1) — การตรวจสอบ write/delete รากฐานของการตรวจสอบความปลอดภัย/ISO
- **`base_export_manager`** (P1) — จำกัด mass export ของข้อมูลลูกค้า/การเงิน
- **`session_db`** (P1) — เห็นและปิด session ที่ใช้งานอยู่ระหว่างเหตุการณ์
- **`base_user_role_history`** (P2) — ตรวจสอบว่าใครเปลี่ยนบทบาท/สิทธิ์
- **`base_technical_user`** (P3) — เสริมความแข็งแรงเส้นทาง technical/service user
- **`base_menu_visibility_restriction`** (P3) — ซ่อนเมนูตามกลุ่มแทนการทำเมนูซ้ำ
- **คำแนะนำเชิงลบ:** `base_external_dbsource` (ความเสี่ยง HIGH พื้นผิวการนำข้อมูลออก) → **ห้ามติดตั้ง**

**PROPOSED CHANGE — NOT EXECUTED (config ความปลอดภัย ไม่ใช่โมดูล):**
- ตั้ง `list_db = False` ใน `odoo.conf` และใช้ `dbfilter` เพียงอย่างเดียว
- ยืนยันว่า `odoo.conf` (ที่มี `db_password`) ถูกกันออกจาก VCS; ควรใช้ env/กลไก secret แทน
- พิจารณา rate limiting ฝั่ง Nginx และกฎ Cloudflare WAF ซึ่งมีนัยจาก DDNS/proxy ที่ตั้งไว้แล้ว

## ข้อเสนอแนะด้านประสิทธิภาพ (Performance)

- **`base_cron_exclusion`** (P1) — ป้องกัน job ยาวซ้อนทับภายใต้ `max_cron_threads = 2`
- **`base_partition`** (P3) — เฉพาะเมื่อพิสูจน์ได้ว่าตาราง audit/log ใหญ่จริง; มิฉะนั้นข้าม
- **คำแนะนำเชิงลบ:** `base_search_fuzzy` (P4) — เพิ่ม trigram index/DB extension โดยไม่มีความจำเป็นที่พิสูจน์ได้
- **คำแนะนะเชิงลบ:** `module_auto_update` (P4, HIGH) — อัปเกรดอัตโนมัติแบบไม่ควบคุมข้าม 13 OCA submodule + ~80 โมดูลกำหนดเอง

**PROPOSED CHANGE — NOT EXECUTED (runtime/config):**
- ประเมิน `workers = N` (multi-process) สำหรับโปรดักชัน และตั้ง `limit_request`; ตรวจสอบกับขีดจำกัดหน่วยความจำและการ deploy บน Windows
- เพิ่ม log rotation สำหรับ `odoo_server.log` (Odoo ไม่ rotate เองโดยค่าเริ่มต้น)
- ทบทวน `max_cron_threads` เทียบกับระยะเวลาจริงของงาน เมื่อ `base_cron_exclusion` ทำงานแล้ว

## ข้อเสนอแนะด้านปฏิบัติการ (Operations)

- **`sentry`** (P1) — เก็บและแจ้งเตือนข้อผิดพลาด
- **`scheduler_error_mailer`** (P1) — แจ้งเตือน cron ล้มเหลว
- **`auto_backup`** (P1) — backup ตามกำหนด + retention
- **`database_cleanup`** (P1) — ลบ object สคีมาตกค้างในช่วง maintenance window
- **`session_db`** (P1) — ควบคุม session ด้านปฏิบัติการ
- **`upgrade_analysis`** (P2) — ความปลอดภัยในการอัปเกรดบนหลักฐาน
- **`rpc_helper`**, **`base_technical_features`** (P3) — เครื่องมือ admin/วินิจฉัย

## ข้อเสนอแนะด้านเวิร์กโฟลว์ (Workflow)

- **`server_action_mass_edit`** (P2) — แก้ไขข้อมูลเป็นกลุ่มแบบควบคุมได้
- **`base_cancel_confirm`** (P2) — guard การยกเลิกโดยไม่ตั้งใจ
- **`base_comment_template`** (P2) — แทนตรรกะข้อกำหนด/หมายเหตุที่ซ้ำ (เฉพาะถ้าแทนที่ `od19_*_terms`)
- **`filter_multi_user`**, **`base_menu_visibility_restriction`**, **`document_quick_access`** (P3) — UX/ผลิตภาพ
- **การรวม (custom ไม่ใช่ OCA):** รวมโมดูล `*_document_sequence` 6 ตัว และแยก `od19_misc_features` — ลดพื้นผิวการบำรุงรักษา

## ข้อเสนอแนะด้านรายงานและข้อมูล (Reporting & Data)

- **`bi_sql_editor` + `sql_request_abstract`** (P1) — view/รายงานเชิงวิเคราะห์ที่ admin นิยามเองโดยไม่ต้องเขียนโค้ดใหม่
- **`date_range` + `date_range_account`** (P2) — ช่วงเวลารายงานมาตรฐาน
- **`report_qweb_parameter`** (P2) — พารามิเตอร์รายงานที่ผู้ใช้แก้ได้
- **`base_comment_template`** (P2) — หมายเหตุการพิมพ์ที่สม่ำเสมอ
- **`report_qr`** (P2) — QR บนเอกสาร (ความพร้อม e-tax/e-invoice)
- **`report_qweb_element_page_visibility`** (P3) — ควบคุมองค์ประกอบหน้าแรก/สุดท้าย (รองรับการวาง footer ISO)
- **เลือกอย่างใดอย่างหนึ่ง** ระหว่าง `kpi` **หรือ** `bi_sql_editor` สำหรับ dashboard KPI — อย่าซ้อนทั้งสอง

---

# บันทึกการส่งมอบ — สิ่งที่ยังไม่ได้ทำ

ตามข้อจำกัดของการประเมินนี้ **ไม่มีการติดตั้ง อัปเกรด ถอน แก้ไข migrate หรือรีสตาร์ตสิ่งใดเลย** ไม่มีไฟล์ซอร์ส ไฟล์ config สิทธิ์การเข้าถึง หรือ record rule ใดถูกแก้ไข ข้อค้นพบทั้งหมดมาจากการอ่าน `odoo.conf`, `.gitmodules`, manifest ของโมดูล และเอกสารกำกับดูแลใน `docs/superpowers/**`

การเปลี่ยนแปลงด้าน config หรือ runtime ที่กล่าวถึงข้างต้นถูกระบุชัดว่า **"PROPOSED CHANGE — NOT EXECUTED"** และต้องได้รับอนุมัติแยกก่อนดำเนินการ

## ขอบเขตจำกัดของการประเมินนี้

- ความเข้ากันได้ของโมดูลตรวจสอบใน **ระดับ manifest เท่านั้น** (declared `19.0.x` บน branch `19.0`) ไม่ได้รันทดสอบพฤติกรรมจริง และระบุเป็น **COMPATIBILITY NOT VERIFIED (runtime)** ในจุดที่เกี่ยวข้อง
- ชุดโมดูลที่ติดตั้งนำมาจากการ discovery ก่อนหน้า (~234 โมดูล); ควรยืนยันซ้ำจาก `ir_module_module` ก่อนตัดสินใจติดตั้งใด ๆ
- โมดูลกำหนดเองหลายตัวดูเหมือนเป็นโครงร่างเปล่าหรือ report-only และต้องตรวจสอบก่อนนับว่าเป็นความครอบคลุมที่ทำงานได้จริง

---

# ส่วนที่ 2 — OCA Module Assessment (English original)

> 📄 **ต้นฉบับเดิม:** `OCA_MODULE_ASSESSMENT.md`

# OCA Module Assessment — Odoo 19 CE (`odoo19`)

**Role:** Senior Odoo Technical Architect / OCA Module Auditor
**Scope:** Analysis and recommendation only — **no module installed, upgraded, removed, or executed.**
**Evidence basis:** `odoo.conf`, `.gitmodules`, `custom_addons/*`, `third_party/oca/*` manifests, `docs/superpowers/**` governance artifacts, `OCA_MODULE_ASSESSMENT_TH.md`, `GAP_ANALYSIS_OD15_to_OD19.md`.
**Assessment date:** 2026-10-15

> ⚠️ **STATUS (อัปเดต 2026-10-19):** เอกสารนี้เป็น *การประเมินและข้อเสนอแนะ* ณ 2026-10-15 (ก่อนดำเนินการจริง)
> สำหรับสถานะส่งมอบล่าสุด ให้ยึด [GAP_ANALYSIS_OD15_to_OD19.md](GAP_ANALYSIS_OD15_to_OD19.md) (หัวข้อ "สถานะจริง ณ 2026-10-19")
> และผลการติดตั้งชุดเต็ม 251 โมดูล (custom 79 + OCA + core) ที่ผ่านความสะอาดของ log เมื่อ 2026-10-19

> Compatibility note: every OCA submodule referenced below was verified to **declare a `19.0.x` manifest version on branch `19.0`** (291 manifests checked). This is *manifest-level* verification only. It does **not** prove runtime/functional correctness. Where runtime behavior could not be confirmed from source, entries are marked **COMPATIBILITY NOT VERIFIED (runtime)**.

---

# PHASE 1 — CURRENT SYSTEM ANALYSIS

## 1.1 Platform facts

| Item | Finding |
| --- | --- |
| Odoo version | 19.0 (Community Edition) |
| DB schema series | 19.0.1.3 |
| Database | `odoo19` (PostgreSQL 16.15), `dbfilter = ^odoo19$` |
| Edition | **Community (CE)** — no Enterprise modules present |
| HTTP | Nginx 1.27.2 → `http_port = 8070`, `gevent_port = 8072`, `proxy_mode = True` |
| Public URL | `https://pdev-erp.auto-info.com` (Cloudflare Flexible SSL + DDNS) |
| OS | Windows (Local/Pre-UAT); Linux `/var/odoo` (server target) |
| Workers | `workers = 0` (threaded/prefork disabled) |
| Cron threads | `max_cron_threads = 2` |
| Memory guard | soft 2 GB / hard 2.5 GB |
| Time guard | `limit_time_real = 120`, `limit_time_cpu = 60` |
| Logging | `log_level = info`, `logfile = C:\odoo-dev\odoo19\odoo_server.log` |
| DB manager | `list_db = True` ⚠️ |
| Secrets | `db_password` present in `odoo.conf`; `admin_passwd` hashed (pbkdf2) ⚠️ |

## 1.2 Addon architecture

- `addons_path` (absolute, comma-separated): Odoo core `addons`, `custom_addons`, and **13 OCA Git submodules** under `third_party/oca`.
- OCA repositories (all branch `19.0`): `l10n-thailand`, `sale-blanket`, `sale-workflow`, `server-backend`, `server-tools`, `server-ux`, `helpdesk`, `account-financial-tools`, `purchase-workflow`, `tier-validation`, `reporting-engine`, `knowledge`, `website`.
- **Custom modules:** ~80 modules under `custom_addons` with prefix `od19_*`.
- **Installed modules:** ~234 (custom + a subset of OCA + core).

## 1.3 Installed OCA (already present — do NOT re-recommend as "new")

`base_user_role`, `base_exception`, `base_revision`, `base_tier_validation`, `purchase_request_tier_validation`, `sale_blanket_order`, `sale_delivery_state` (sale_stock_delivery_state), `sale_exception`, `sale_order_revision`, `sale_company_currency`, `account_asset_management`, `account_fiscal_year`, `l10n_th_account_tax`, `l10n_th_amount_to_text`, `l10n_th_base_sequence`, `l10n_th_base_utils`, `helpdesk_mgmt`, `helpdesk_mgmt_project`, `helpdesk_product`, `purchase_request`, `report_xlsx`, `report_xlsx_helper`, `document_knowledge`, `document_page`.

## 1.4 Security / access architecture

- **Role-based groups** via `base_user_role` (good baseline).
- **Team-scoped security** in custom helpdesk extensions (`od19_helpdesk_extension`, `od19_internal_issue`) using `security/*.xml` group + record rules.
- **ISO control modules** (9) with departmental document sequences.
- **No record-level audit trail** — `auditlog` is present in the repo but **not installed**.
- **No user/permission change history** — `base_user_role_history` present but not installed.
- **No export restriction** — `base_export_manager` present but not installed.
- **DB manager exposed** (`list_db = True`).
- **Secrets in config file** (`db_password`).

## 1.5 Reporting mechanisms

- Odoo native QWeb PDF + XLSX (`report_xlsx`, `report_xlsx_helper` installed).
- Custom Jasper bridge (`od19_reporting_jasper`), Thai tax reports (`od19_thai_tax_reports`), WHT reports, payment voucher reports, many report-only custom modules.
- **No user-configurable SQL reporting layer** (`bi_sql_editor` / `sql_request_abstract` available but not installed).
- **No report parameterisation** (`report_qweb_parameter` not installed).

## 1.6 Monitoring / logging / automation

- Logging is file-only at `info` level; **no log rotation configured** in Odoo.
- **No error monitoring** (`sentry` not installed).
- **No cron failure alerting** (`scheduler_error_mailer` not installed).
- **No automated backup** (`auto_backup` not installed) — while the production-readiness baseline requires backup + restore evidence before go-live.
- Automation exists via Odoo scheduled/server actions and are explicitly recorded as a **known risk hotspot** in discovery docs.

## 1.7 Identified weaknesses (Phase 1 output)

**Performance**
- `workers = 0` → no worker/multi-process scaling; long requests block the threaded loop. For a multi-user ERP this is the single largest scalability limiter.
- No `limit_request` set (default 8192) → risk of long-lived requests leaking memory in worker mode.
- No log rotation → unbounded log file growth on both Windows and Linux.
- Cron overlap is uncontrolled (two cron threads; no exclusion guard).

**Redundancy / maintainability**
- Six near-parallel numbering modules: `od19_document_sequence`, `od19_accounting_document_sequence`, `od19_quotation_document_sequence`, `od19_purchase_document_sequence`, `od19_project_document_sequence`, `od19_partner_document_sequence`.
- `od19_misc_features` is a grab-bag (logo ISO, sequence guard, data link, runtime guard, repeat-customer report) — cohesion smell.
- Several modules appear to be **stubs or report-only placeholders** with empty `models/`/`report/`/`wizard/` initialisers (e.g. `od19_accounting_reporting`, `od19_accounting_money_in_report`, `od19_service_card`, `od19_accounting_payment_voucher_reports` is report-only by design). **Verify before treating any as functional.**

**Missing controls**
- No audit trail for write/delete, no permission-change history, no export controls.
- No DB bloat/orphan-object hygiene tooling.
- No session management/visibility (who is logged in where).

**Security weaknesses**
- `list_db = True` exposes the database manager endpoint.
- DB password stored in a plaintext-config file; must confirm it is excluded from VCS.
- No proxy-level DB-filter enforcement (`dbfilter_from_header`) despite Nginx + Cloudflare ingress.
- No "technical user" restriction for a service account.

**Observability gaps**
- No centralised error capture, no cron-failure notification, no audit query surface.

**Data-quality risks**
- Year-based document sequences and partner references are custom; without audit trail, back-dated edits are invisible.

---

# PHASE 2 — OCA MODULE DISCOVERY (classified candidates)

All modules below exist in the pinned `third_party/oca` submodules (branch 19.0). "INSTALLED" flags modules already active.

| # | Category | Technical name | Repo | Installed |
| --- | --- | --- | --- | --- |
| 1 | B Monitoring | `auditlog` | server-tools | no |
| 2 | B Monitoring | `sentry` | server-tools | no |
| 3 | B Monitoring | `scheduler_error_mailer` | server-tools | no |
| 4 | D Prevention | `auto_backup` | server-tools | no |
| 5 | C Troubleshooting | `database_cleanup` | server-tools | no |
| 6 | A/D Performance/Prevention | `base_cron_exclusion` | server-tools | no |
| 7 | G Security | `base_export_manager` | server-ux | no |
| 8 | C/G Troubleshooting/Security | `session_db` | server-tools | no |
| 9 | F Reporting | `bi_sql_editor` (+`sql_request_abstract`) | reporting-engine | no |
| 10 | F Reporting | `date_range` (+`date_range_account`) | server-ux | no |
| 11 | F Reporting | `report_qweb_parameter` | reporting-engine | no |
| 12 | E/F Workflow/Reporting | `base_comment_template` | reporting-engine | no |
| 13 | G Security | `base_user_role_history` | server-backend | no |
| 14 | E Workflow | `server_action_mass_edit` | server-ux | no |
| 15 | F Reporting | `report_qr` | reporting-engine | no |
| 16 | D Prevention | `base_cancel_confirm` | server-ux | no |
| 17 | C Troubleshooting | `upgrade_analysis` | server-tools | no |
| 18 | E Utility | `base_technical_features` | server-ux | no |
| 19 | G Security | `base_technical_user` | server-tools | no |
| 20 | D Prevention | `base_optional_quick_create` | server-ux | no |
| 21 | D Prevention | `base_time_window` | server-tools | no |
| 22 | E/D Workflow | `base_substate` | server-ux | no |
| 23 | G Security | `base_menu_visibility_restriction` | server-ux | no |
| 24 | E Utility | `filter_multi_user` | server-ux | no |
| 25 | E Utility | `document_quick_access` | server-ux | no |
| 26 | A Performance | `base_partition` | server-tools | no |
| 27 | G Security | `dbfilter_from_header` | server-tools | no |
| 28 | F Reporting | `report_async` | reporting-engine | no |
| 29 | F Reporting | `report_qweb_element_page_visibility` | reporting-engine | no |
| 30 | F Reporting | `kpi` | reporting-engine | no |
| 31 | B Monitoring | `tracking_manager` | server-tools | no |
| 32 | E Utility | `base_view_inheritance_extension` | server-tools | no |
| 33 | D Prevention | `module_auto_update` | server-tools | no (see P4) |

---

# PHASE 3–5 — DETAILED MODULE ASSESSMENT (17 fields each)

## 1. `auditlog` — Audit Trail ✅ P1

1. **Category:** B — Monitoring & Anomaly Detection
2. **Module name:** Audit Log
3. **Technical name:** `auditlog`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/auditlog`
5. **Purpose:** Full ORM-level audit trail of create/write/unlink on configured models.
6. **Current problem it solves:** No write/delete audit trail exists; ISO 9001 and financial integrity require traceability of record changes, including deletions (`auditlog` records `unlink`). Discovery docs list automations and data edits as unresolved risk.
7. **Key features:** Per-model rule configuration; tracks field-level old→new values; logs user, IP, HTTP method; logs deletions; log search/export; optional DB-level triggers.
8. **Compatibility status:** Manifest `19.0.2.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`, `mail`.
10. **Potential conflicts:** Minimal. Adds DB triggers/log tables. Ensure it is not applied to high-volume transient models (e.g. `mail.message`, `bus.*`, `ir.logging`) to avoid write amplification.
11. **Database impact:** Adds `auditlog.*` tables + optional triggers; grows over time — plan retention.
12. **Security impact:** Positive; exposes historical changes to authorised users only (own ACLs).
13. **Risk level:** **MEDIUM**
14. **Risk explanation:** Hooks into ORM write paths for configured models; mis-scoped rules add measurable write latency and DB growth. Reversible by uninstall but historical log tables should be archived first.
15. **Priority:** **P1**
16. **Recommendation:** Install, then scope to financial/ISO-critical models only.
17. **Reason:** Directly closes the largest governance gap (traceability) required by ISO 9001 and the production-readiness baseline.

## 2. `sentry` — Error Monitoring ✅ P1

1. **Category:** B — Monitoring & Anomaly Detection
2. **Module name:** Sentry Integration
3. **Technical name:** `sentry`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/sentry`
5. **Purpose:** Forwards Python/Odoo exceptions (with traceback, user, context) to a Sentry server.
6. **Current problem it solves:** No centralised error capture; production errors are only in a local log file with no alerting.
7. **Key features:** Logger + WSGI exception hooks, user/context enrichment, configurable DSN and environment, breadcrumbs.
8. **Compatibility status:** Manifest `19.0.1.0.1`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`; Python `sentry-sdk` (external pip requirement).
10. **Potential conflicts:** None expected with Odoo core; requires outbound network to the Sentry endpoint.
11. **Database impact:** **None.**
12. **Security impact:** Sends error context off-box — must scrub PII and never send secrets; use a self-hosted DSN if data residency matters.
13. **Risk level:** **LOW–MEDIUM**
14. **Risk explanation:** No schema change; the only risks are outbound data privacy and a missing `sentry-sdk` dependency blocking module load.
15. **Priority:** **P1**
16. **Recommendation:** Install with a reviewed DSN and PII-scrubbing config.
17. **Reason:** Highest-value observability gain at near-zero DB cost; prerequisite for the "logging and monitoring before go-live" baseline.

## 3. `auto_backup` — Automated Database Backup ✅ P1

1. **Category:** D — Prevention & Protection
2. **Module name:** Database Auto-Backup
3. **Technical name:** `auto_backup`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/auto_backup`
5. **Purpose:** Scheduled dump of the DB (and optionally filestore) with retention.
6. **Current problem it solves:** Production-readiness baseline requires backup **and filestore** coverage plus a testable restore path; no automated backup module is installed.
7. **Key features:** Per-DB cron backups to a configured folder, retention by count/day, optional filestore backup, manual "backup now", email notify.
8. **Compatibility status:** Manifest `19.0.1.0.1`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`.
10. **Potential conflicts:** None functional. On Windows, target path/permissions must be writable by the Odoo service account.
11. **Database impact:** None on schema; produces dump files on disk (storage growth — set retention).
12. **Security impact:** Backup files contain full data — store on a protected path, exclude from web exposure, restrict access.
13. **Risk level:** **LOW–MEDIUM**
14. **Risk explanation:** No ORM/schema change; risks are disk exhaustion (no retention) and unsecured backup artifacts.
15. **Priority:** **P1**
16. **Recommendation:** Install; write backups off the app server; validate a restore separately.
17. **Reason:** Backup + restore is a hard go-live gate. Note: module backup is **not** a substitute for a tested restore and off-site copy.

## 4. `scheduler_error_mailer` — Cron Failure Alerting ✅ P1

1. **Category:** B — Monitoring & Anomaly Detection
2. **Module name:** Scheduler Error Mailer
3. **Technical name:** `scheduler_error_mailer`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/scheduler_error_mailer`
5. **Purpose:** Emails administrators when a scheduled job (`ir.cron`) fails.
6. **Current problem it solves:** Baseline warns that "jobs which fail silently" are a readiness blocker; today a failing cron is invisible.
7. **Key features:** Hooks cron error handling, sends mail to configured recipients with the failing job and traceback.
8. **Compatibility status:** Manifest `19.0.1.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`, `mail`.
10. **Potential conflicts:** None.
11. **Database impact:** None.
12. **Security impact:** Tracebacks may expose internals — send only to internal admins.
13. **Risk level:** **LOW**
14. **Risk explanation:** Mail-only hook; no schema change; no core override beyond cron error path.
15. **Priority:** **P1**
16. **Recommendation:** Install and route to an internal admin alias.
17. **Reason:** Cheap, direct closure of the "silent cron failure" reliability gap.

## 5. `database_cleanup` — DB Hygiene / Troubleshooting ✅ P1

1. **Category:** C — Troubleshooting & Fixes
2. **Module name:** Database Cleanup
3. **Technical name:** `database_cleanup`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/database_cleanup`
5. **Purpose:** Detect and purge orphaned/hidden DB objects (columns, tables, model data) left by removed modules.
6. **Current problem it solves:** ~80 custom + many OCA modules churn over Waves; leftover columns/tables accumulate and complicate maintenance/upgrades.
7. **Key features:** Purge columns/tables, purge orphaned data rows, purge model/field data, preview before purge, DB-only operations.
8. **Compatibility status:** Manifest `19.0.1.0.6`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`.
10. **Potential conflicts:** None at install; **destructive operations are manual and must be reviewed**.
11. **Database impact:** High when actually used (drops columns/tables) — but only on explicit admin action.
12. **Security impact:** Restrict to superuser/technical group.
13. **Risk level:** **MEDIUM–HIGH**
14. **Risk explanation:** Capable of irreversible data loss if used without review. Installed itself is harmless; the *operations* are the risk. Mitigate: full backup first, dry-run previews, single-admin access.
15. **Priority:** **P1** (install now, use surgically)
16. **Recommendation:** Install for maintenance capability; never run purges without a fresh backup.
17. **Reason:** Essential long-term maintainability tool for a module-heavy custom ERP; prevents schema rot across Waves.

## 6. `base_cron_exclusion` — Cron Overlap Prevention ✅ P1

1. **Category:** A — Performance & Optimization / D — Prevention
2. **Module name:** Base Cron Exclusion
3. **Technical name:** `base_cron_exclusion`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/base_cron_exclusion`
5. **Purpose:** Prevent the same scheduled job from running concurrently (and mutual-exclusion between jobs).
6. **Current problem it solves:** `max_cron_threads = 2` with no exclusion guard → the same long cron can overlap, causing duplicate processing and load spikes.
7. **Key features:** New "exclusive" field on `ir.cron`; skips a run if the same/allowed job is still running.
8. **Compatibility status:** Manifest `19.0.1.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`.
10. **Potential conflicts:** None.
11. **Database impact:** None.
12. **Security impact:** None.
13. **Risk level:** **LOW**
14. **Risk explanation:** Small, additive field on `ir.cron`; no core logic replacement.
15. **Priority:** **P1**
16. **Recommendation:** Install and mark long jobs as exclusive.
17. **Reason:** Direct stability/scalability improvement with negligible risk; complements the threaded (`workers=0`) runtime.

## 7. `base_export_manager` — Export Governance ✅ P1

1. **Category:** G — Access Rights & Security
2. **Module name:** Base Export Manager
3. **Technical name:** `base_export_manager`
4. **OCA repository:** `OCA/server-ux` → `third_party/oca/server-ux/base_export_manager`
5. **Purpose:** Control who can export, and restrict which models/fields may be exported.
6. **Current problem it solves:** Any user can mass-export any list today — a data-exfiltration risk for an ERP holding customer/financial data.
7. **Key features:** Per-model export rules, field allow-lists, per-group export permissions, UI for rule maintenance.
8. **Compatibility status:** Manifest `19.0.1.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`, `web`.
10. **Potential conflicts:** Low; adds ACLs. Changes export UX — brief users.
11. **Database impact:** Adds small `ir.exports.*` rule tables.
12. **Security impact:** **Positive and significant** — reduces mass-export exposure.
13. **Risk level:** **LOW–MEDIUM**
14. **Risk explanation:** Data-permission model change; mis-configured rules could over-restrict legitimate exports.
15. **Priority:** **P1**
16. **Recommendation:** Install and default-deny sensitive models.
17. **Reason:** Closes a concrete data-exfiltration gap with a light, well-scoped module.

## 8. `session_db` — Session Control / Admin ✅ P1

1. **Category:** C — Troubleshooting / G — Security
2. **Module name:** Session DB
3. **Technical name:** `session_db`
4. **OCA repository:** `OCA/server-tools` → `third_party/oca/server-tools/session_db`
5. **Purpose:** Store HTTP sessions in the database, enabling session listing/termination.
6. **Current problem it solves:** No way to see or terminate active sessions; needed for incident response and to keep sessions alive across restarts.
7. **Key features:** DB-backed session store, admin session view, force-logout, configurable lifetime.
8. **Compatibility status:** Manifest `19.0.1.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `base`.
10. **Potential conflicts:** Sessions persist across restarts (behavior change users may notice); needs a cleanup cron.
11. **Database impact:** Adds `session.db`-style table with periodic cleanup; write volume on every session refresh (modest).
12. **Security impact:** Positive — centralised session kill for incident response.
13. **Risk level:** **LOW–MEDIUM**
14. **Risk explanation:** Changes session storage location; if not cleaned, table grows. No core logic override beyond session store.
15. **Priority:** **P1**
16. **Recommendation:** Install with a scheduled session-cleanup job.
17. **Reason:** High operational/security value for a Cloudflare-exposed instance; low blast radius.

## 9. `bi_sql_editor` (+ `sql_request_abstract`) — Configurable Reporting ✅ P1

1. **Category:** F — Data Processing & Reporting
2. **Module name:** BI SQL Editor (dependency: SQL Request Abstract)
3. **Technical name:** `bi_sql_editor`, `sql_request_abstract`
4. **OCA repository:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/bi_sql_editor`, `.../sql_request_abstract`
5. **Purpose:** Create read-only SQL views and expose them as list/pivot/graph reports with an export, without writing code.
6. **Current problem it solves:** Owner-value KPIs/aggregations currently require custom Python report modules per report; this allows admin-defined analytical outputs.
7. **Key features:** SQL view editor with validation, auto list/pivot/graph, drill-down actions, materialised views, menu/action generation, access ACLs.
8. **Compatibility status:** Manifest `bi_sql_editor` `19.0.2.0.1`, `sql_request_abstract` `19.0.1.0.0`. Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
9. **Dependencies:** `sql_request_abstract` → `base`.
10. **Potential conflicts:** None with existing report modules (they coexist). If a custom module already exposes the same query, prefer one source.
11. **Database impact:** Creates DB views/materialised views — schema objects owned by the module; document them.
12. **Security impact:** **Elevated** — raw SQL is powerful. Must be restricted to a trusted group; use a **read-only DB role** for the views.
13. **Risk level:** **MEDIUM**
14. **Risk explanation:** Grants SQL authoring to privileged users and creates persistent DB objects. Misuse risks data exposure or heavy queries. Mitigate with a read-only group and query review.
15. **Priority:** **P1**
16. **Recommendation:** Install for a small set of admins; enforce read-only SQL and review queries.
17. **Reason:** Directly supports the program's owner-value reporting goal and reduces per-report custom code; the alternative (one custom module per report) is more maintenance.

## 10. `date_range` (+ `date_range_account`) — Reporting Periods ✅ P2

1. **Category:** F — Reporting
2. **Technical name:** `date_range`, `date_range_account`
3. **OCA repository:** `OCA/server-ux` → `third_party/oca/server-ux/date_range`, `date_range_account`
4. **Purpose:** Reusable, user-defined date ranges (fiscal periods, custom windows) usable in report filters/domains.
5. **Current problem:** Fiscal-period reporting is currently ad-hoc; `date_range_account` is the standard dependency for period-based accounting reports.
6. **Key features:** Named ranges (fixed/window), generator rules, per-company, integration hooks for reports.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**.
8. **Dependencies:** `base`; `date_range_account` → `account`, `date_range`.
9. **Conflicts:** None (may be pulled in as a dependency by other OCA reporting modules).
10. **DB impact:** Small `date_range.*` tables.
11. **Security impact:** Neutral.
12. **Risk:** **LOW** — additive, light.
13. **Risk explanation:** No core overrides; only new reference data.
14. **Priority:** **P2**
15. **Recommendation:** Install when period-based reporting is configured.
16. **Reason:** Standard building block; low value until reports consume it, then high leverage.

## 11. `report_qweb_parameter` — User-Configurable Report Parameters ✅ P2

1. **Category:** F — Reporting
2. **Technical name:** `report_qweb_parameter`
3. **OCA repository:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/report_qweb_parameter`
4. **Purpose:** Add validated, user-editable parameters to QWeb reports (avoid manual template edits).
5. **Current problem:** Report tweaks (company header text, footer notes) require developer edits to XML.
6. **Key features:** Per-report parameter definitions with types/validation, editable at print time.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**.
8. **Dependencies:** `base`.
9. **Conflicts:** None expected; complements custom QWeb/ISO footer reports.
10–11. **DB/Security:** Small parameter tables; neutral security.
12–13. **Risk:** **LOW** — no core override.
14. **Priority:** **P2** / 15. **Recommendation:** Install for reports needing runtime parameters.
16. **Reason:** Reduces developer round-trips for routine report changes.

## 12. `base_comment_template` — Reusable Comment Blocks ✅ P2

1. **Category:** E/F — Workflow / Reporting
2. **Technical name:** `base_comment_template`
3. **OCA repository:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/base_comment_template`
4. **Purpose:** Define reusable comment blocks attachable to documents and printable on reports.
5. **Current problem:** Terms/notes are duplicated module-by-module (`od19_sale_terms`, `od19_purchase_terms`) — a single template library would reduce duplication.
6. **Key features:** Template model, domain-based applicability, print/placeholder toggle, replace-vs-append modes.
7. **Compatibility:** Manifest `19.0.0.0.2` (note: very early in the 19.0 port). Runtime **COMPATIBILITY NOT VERIFIED (runtime)**.
8. **Dependencies:** `base`.
9. **Conflicts:** Potential **overlap** with the existing custom terms modules — decide one source of truth before adopting.
10–11. **DB/Security:** Small template table; neutral.
12–13. **Risk:** **LOW–MEDIUM** — low technical risk, but early-stage port and functional overlap.
14. **Priority:** **P2** / 15. **Recommendation:** Evaluate against `od19_*_terms` before adopting; do not run both.
16. **Reason:** Good deduplication tool, but only if it replaces (not duplicates) existing custom terms.

## 13. `base_user_role_history` — Permission Change Audit ✅ P2

1. **Category:** G — Access Rights & Security
2. **Technical name:** `base_user_role_history`
3. **OCA repository:** `OCA/server-backend` → `third_party/oca/server-backend/base_user_role_history`
4. **Purpose:** Track changes to users/roles (who changed what, when).
5. **Current problem:** Permission changes are untracked; hard to answer "who granted this access?".
6. **Key features:** History log of role/user changes, current/previous role snapshot, chatter-integrated.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**. Depends on installed `base_user_role`.
8. **Dependencies:** `base_user_role`.
9. **Conflicts:** None (extends the installed role model).
10–11. **DB/Security:** Adds history rows; **positive** security value.
12–13. **Risk:** **LOW** — additive on an already-installed base.
14. **Priority:** **P2** / 15. **Recommendation:** Install alongside `auditlog`.
16. **Reason:** Cheap, targeted security auditability for the RBAC layer.

## 14. `server_action_mass_edit` — Bulk Editing ✅ P2

1. **Category:** E — Utilities & Workflow
2. **Technical name:** `server_action_mass_edit`
3. **OCA repository:** `OCA/server-ux` → `third_party/oca/server-ux/server_action_mass_edit`
4. **Purpose:** Server action type to mass-update fields across selected records.
5. **Current problem:** Bulk corrective updates currently need ad-hoc scripts or per-record edits.
6. **Key features:** Domain-based mass update, preview affected records, per-field values, run from a server action.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**.
8. **Dependencies:** `base`.
9. **Conflicts:** None.
10–11. **DB/Security:** Can write many records at once → restrict to trusted groups; adds action config only.
12–13. **Risk:** **MEDIUM** — mass writes can cause wide unintended changes if the domain is wrong.
14. **Priority:** **P2** / 15. **Recommendation:** Install, restrict to admin/technical groups.
16. **Reason:** Genuine productivity for data-correction tasks, but must be access-guarded.

## 15. `report_qr` — QR Codes on Reports ✅ P2

1. **Category:** F — Reporting
2. **Technical name:** `report_qr`
3. **OCA repository:** `OCA/reporting-engine` → `third_party/oca/reporting-engine/report_qr`
4. **Purpose:** Render QR codes in QWeb reports.
5. **Current problem:** Thai e-tax/e-invoice and verification flows increasingly expect QR content on printed documents.
6. **Key features:** QWeb helper to embed QR images from arbitrary payloads.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**; requires Python `qrcode` (external pip dep).
8. **Dependencies:** `base` (+ `qrcode` library).
9. **Conflicts:** None.
10–11. **DB/Security:** None/minimal.
12–13. **Risk:** **LOW** — display-only helper.
14. **Priority:** **P2** / 15. **Recommendation:** Install when a QR-bearing document is required.
16. **Reason:** Small, standard, enables compliance-ready printed outputs.

## 16. `base_cancel_confirm` — Cancellation Guard ✅ P2

1. **Category:** D — Prevention & Protection
2. **Technical name:** `base_cancel_confirm`
3. **OCA repository:** `OCA/server-ux` → `third_party/oca/server-ux/base_cancel_confirm`
4. **Purpose:** Force an explicit confirmation before cancelling records.
5. **Current problem:** Accidental cancellation of orders/invoices is possible without an extra guard — maps to the project's "prevent operational errors" objective.
6. **Key features:** Confirmation wizard on cancel for enabled models.
7. **Compatibility:** `19.0.1.0.0`. Runtime **NOT VERIFIED**.
8. **Dependencies:** `base`.
9. **Conflicts:** None expected; verify against custom cancel overrides in `od19_sale_wizards`/`od19_purchase_wizards`.
10–11. **DB/Security:** None; additive UX guard.
12–13. **Risk:** **LOW** — UI-level guard.
14. **Priority:** **P2** / 15. **Recommendation:** Install for financially significant models.
16. **Reason:** Directly serves the prevention objective at negligible risk.

---

## PHASE 3–5 — COMPACT ASSESSMENT (P3 / P4)

| Module | Cat | Repo | Version (manifest) | Risk | Why | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| `upgrade_analysis` | C | server-tools | 19.0.1.1.4 | MEDIUM | Compares schema/data across versions; key for OCA/custom upgrade safety; requires a reference revision. | P2 |
| `base_technical_features` | E | server-ux | 19.0.1.0.0 | LOW | Exposes technical fields to a dedicated group; aids troubleshooting. | P3 |
| `base_technical_user` | G | server-tools | 19.0.1.0.0 | LOW | Blocks the "technical" user from being used as an API bypass; hardening. | P3 |
| `base_optional_quick_create` | D | server-ux | 19.0.1.0.0 | LOW | Prevents accidental quick-create duplicates. | P3 |
| `base_time_window` | D | server-tools | 19.0.1.0.0 | LOW–MEDIUM | Validates non-overlapping date windows; useful for contracts/planning. | P3 |
| `base_substate` | E | server-ux | 19.0.1.0.0 | LOW | Sub-states for records; overlaps custom status fields. | P3 |
| `base_menu_visibility_restriction` | G | server-ux | 19.0.1.0.0 | LOW | Hide menus per group — cleaner than duplicated menu items. | P3 |
| `filter_multi_user` | E | server-ux | 19.0.1.0.0 | LOW | Shared team filters; UX gain. | P3 |
| `document_quick_access` | E | server-ux | 19.0.1.0.0 | LOW | Quick document links; minor UX. | P3 |
| `base_partition` | A | server-tools | 19.0.1.0.0 | MEDIUM–HIGH | Table partitioning for very large tables (logs/auditlog). Only if growth is proven. | P3 |
| `dbfilter_from_header` | G | server-tools | 19.0.1.0.0 | MEDIUM | Enforce DB filter at the proxy — but the project already pins `dbfilter` and single-DB; only relevant if multi-DB via Nginx. | P3 |
| `report_async` | F | reporting-engine | 19.0.1.0.0 | MEDIUM | Async heavy report generation; needs queue infra. Useful only for large reports. | P3 |
| `report_qweb_element_page_visibility` | F | reporting-engine | 19.0.1.0.0 | LOW | Show/hide elements on first/last page — supports the ISO footer-placement requirement. | P3 |
| `kpi` | F | reporting-engine | 19.0.1.0.1 | LOW–MEDIUM | KPI computation/display; overlaps BI SQL Editor + dashboards. Pick one. | P3 |
| `tracking_manager` | B | server-tools | 19.0.1.0.1 | LOW | Configure field tracking without code; overlaps `auditlog`. | P3 |
| `base_view_inheritance_extension` | E | server-tools | 19.0.1.0.0 | LOW | Richer XPath in inherited views; dev convenience only. | P3 |
| `base_kanban_stage` | E | server-tools | 19.0.1.0.0 | LOW | Generic stage model; only if building kanban pipelines. | P3 |
| `attachment_unindex_content` | A | server-tools | 19.0.1.0.0 | LOW–MEDIUM | Skip attachment content indexing to reduce load — but the project *wants* PDF indexing (pdfminer.six); potential conflict of intent. | P4 for current intent |
| `sequence_python` | E | server-tools | 19.0.1.0.0 | LOW | Python-based sequence values; custom modules may already cover this. | P3 |
| `module_auto_update` | D | server-tools | 19.0.1.0.1 | **HIGH** | Auto-updates modules on code change — dangerous with 13 OCA submodules + ~80 custom modules; can trigger unintended schema upgrades at load. | **P4** |
| `module_change_auto_install` | D | server-tools | 19.0.1.0.0 | MEDIUM | Auto-install modules on file change; same class of risk as above. | P3–P4 |
| `rpc_helper` | C | server-tools | 19.0.1.0.0 | LOW | RPC/debug URL helpers — developer tool only. | P3 |
| `base_search_fuzzy` | A | server-tools | 19.0.1.0.0 | MEDIUM | Trigram search; adds DB extensions and index cost. Only if search is proven slow. | P4 |
| `base_external_dbsource` | — | server-backend | 19.0.1.0.0 | **HIGH** | Arbitrary external DB connections — an exfiltration/attack surface. Not recommended. | **P4** |
| `bus_alt_connection` | — | server-tools | 19.0.1.0.0 | MEDIUM | Alternate bus/IM connection; no need identified. | P4 |
| `iap_alternative_provider` | — | server-tools | 19.0.1.0.0 | MEDIUM | Only if replacing Odoo IAP providers. | P4 |
| `onchange_helper` | E | server-tools | 19.0.1.0.0 | LOW | Developer helper; no business need. | P4 |
| `base_fontawesome` | E | server-tools | 19.0.1.0.0 | LOW | Icon set packaging; Odoo ships icons. | P4 |
| `base_write_diff` | B | server-tools | 19.0.1.0.0 | LOW | Logs write diffs to a file; overlaps `auditlog`. | P4 |

---

# PHASE 6 — DUPLICATION & CONFLICT CHECK

| Candidate | Core/EE | Installed OCA | Custom modules | Verdict |
| --- | --- | --- | --- | --- |
| `auditlog` | Core has `mail.thread` tracking only (field-level, per-model) — **not** a full write/delete audit trail | — | `tracking=True` used in ISO models (partial) | **Adds capability**, no true duplicate |
| `sentry` | Core logs to file only | — | — | No duplicate |
| `auto_backup` | Core has no built-in backup scheduler | — | — | No duplicate |
| `scheduler_error_mailer` | Core silently logs cron failures | — | — | No duplicate |
| `database_cleanup` | `upgrade_analysis` (different purpose) | — | — | No duplicate |
| `base_cron_exclusion` | Core `ir.cron` has no mutual-exclusion | — | `od19_misc_features.runtime_guard` is unrelated (AR/AP guard) | No duplicate |
| `base_export_manager` | Core export has no ACL | — | — | No duplicate |
| `session_db` | Core filesystem sessions | — | — | No duplicate |
| `bi_sql_editor` | Core "Pivot/Graph" only over existing models | `report_xlsx` (output format only) | multiple custom report modules | No duplicate; **reduces** future custom modules |
| `date_range` | Core has fiscal-year util but not user-defined ranges | — | — | No duplicate |
| `report_qweb_parameter` | Core QWeb edits require code | — | — | No duplicate |
| `base_comment_template` | — | — | `od19_sale_terms`, `od19_purchase_terms` | **OVERLAP** — adopt only if replacing the custom terms modules |
| `base_user_role_history` | — | `base_user_role` (installed) | — | Complements installed base |
| `server_action_mass_edit` | Core has server actions but no mass-edit UI | — | — | No duplicate |
| `report_qr` | Core has no QR helper | — | — | No duplicate |
| `base_cancel_confirm` | Core just cancels | — | custom cancel overrides exist | Verify interaction |
| `module_auto_update` | — | — | — | Risky, redundant with controlled deploys |
| `attachment_unindex_content` | — | — | memory: PDF indexing desired (pdfminer.six) | **Conflict of intent** — skip |
| `base_external_dbsource` | — | — | — | **Security anti-recommendation** |

---

# PHASE 7 — OUTPUT

## EXECUTIVE SUMMARY

The `odoo19` instance is a **well-structured Odoo 19 CE greenfield** with a disciplined "OCA-first, custom-second" posture, 13 pinned OCA submodules, and ~80 custom `od19_*` modules covering sales, purchasing, accounting, ISO, helpdesk, and inventory. The architectural foundation is sound. However, the system has a **clear maturity split**: strong *business* coverage, but a **thin operational/governance layer**. Concretely:

1. **No audit trail, no error monitoring, no cron-failure alerting, no automated backup, no export controls, and no session management** are installed — all of which the project's own *production-readiness baseline* requires before go-live, and which ISO 9001 traceability demands.
2. **Runtime is single-process threaded (`workers = 0`)** with no cron-exclusion guard — the principal scalability/stability limiter for a multi-user ERP.
3. **Security posture has two concrete gaps:** the DB manager is exposed (`list_db = True`) and a DB password sits in a plaintext config file (VCS-exclusion must be confirmed).
4. **Maintainability debt** exists in the custom layer: six parallel numbering modules, one "grab-bag" module (`od19_misc_features`), and several apparent stub/report-only modules that should be verified or consolidated.

The recommended action is **not** breadth. A **tight set of ~9 P1 modules** closes the operational, security, and observability gaps with LOW–MEDIUM risk, plus a short P2 list for reporting and workflow. Several available modules are explicitly **not recommended** (auto-update of modules, external DB sources, fuzzy search, attachment de-indexing) because they either add risk or conflict with existing intent.

## TOP RECOMMENDATIONS (highest value)

| Rank | Module | Value | Risk | Priority |
| --- | --- | --- | --- | --- |
| 1 | `auditlog` | Full write/delete traceability (ISO + finance) | MEDIUM | P1 |
| 2 | `sentry` | Centralised error monitoring | LOW–MEDIUM | P1 |
| 3 | `auto_backup` | Backup automation (go-live gate) | LOW–MEDIUM | P1 |
| 4 | `base_export_manager` | Stops mass data exfiltration | LOW–MEDIUM | P1 |
| 5 | `scheduler_error_mailer` | Ends silent cron failures | LOW | P1 |
| 6 | `base_cron_exclusion` | Prevents overlapping crons | LOW | P1 |
| 7 | `database_cleanup` | Long-term schema hygiene | MEDIUM–HIGH (ops only) | P1 |
| 8 | `session_db` | Session visibility/kill | LOW–MEDIUM | P1 |
| 9 | `bi_sql_editor` | Configurable owner-value reporting | MEDIUM | P1 |

## SECURITY RECOMMENDATIONS

- **`auditlog`** (P1) — write/delete traceability, the foundation of any security/ISO audit.
- **`base_export_manager`** (P1) — restrict mass export of customer/financial data.
- **`session_db`** (P1) — see and terminate active sessions during incidents.
- **`base_user_role_history`** (P2) — audit who changed roles/permissions.
- **`base_technical_user`** (P3) — harden the technical/service-user path.
- **`base_menu_visibility_restriction`** (P3) — hide menus per group instead of duplicating menus.
- **Anti-recommendations:** `base_external_dbsource` (HIGH risk exfiltration surface) → **do not install**.

**PROPOSED CHANGE — NOT EXECUTED (security config, no module):**
- Set `list_db = False` in `odoo.conf` and use `dbfilter` alone.
- Confirm `odoo.conf` (containing `db_password`) is excluded from VCS; prefer an env/secret mechanism.
- Consider Nginx-side rate limiting and Cloudflare WAF rules already implied by the DDNS/proxy setup.

## PERFORMANCE RECOMMENDATIONS

- **`base_cron_exclusion`** (P1) — prevents overlapping long jobs under `max_cron_threads = 2`.
- **`base_partition`** (P3) — only if audit/log tables are proven large; otherwise skip.
- **Anti-recommendation:** `base_search_fuzzy` (P4) — adds trigram indexes/DB extensions without proven need.
- **Anti-recommendation:** `module_auto_update` (P4, HIGH) — uncontrolled auto-upgrades across 13 OCA submodules + ~80 custom modules.

**PROPOSED CHANGE — NOT EXECUTED (runtime/config):**
- Evaluate `workers = N` (multi-process) for production and set `limit_request`; verify against memory limits and the Windows deployment.
- Add log rotation for `odoo_server.log` (Odoo does not rotate by default).
- Review `max_cron_threads` against actual job duration once `base_cron_exclusion` is in place.

## OPERATIONS RECOMMENDATIONS

- **`sentry`** (P1) — error capture and alerting.
- **`scheduler_error_mailer`** (P1) — cron failure notification.
- **`auto_backup`** (P1) — scheduled backup + retention.
- **`database_cleanup`** (P1) — purge orphaned schema objects during maintenance windows.
- **`session_db`** (P1) — operational session control.
- **`upgrade_analysis`** (P2) — evidence-based upgrade safety.
- **`rpc_helper`**, **`base_technical_features`** (P3) — admin/diagnostic conveniences.

## WORKFLOW RECOMMENDATIONS

- **`server_action_mass_edit`** (P2) — controlled bulk data corrections.
- **`base_cancel_confirm`** (P2) — guard against accidental cancellations.
- **`base_comment_template`** (P2) — replace duplicated term/note logic (only if it replaces `od19_*_terms`).
- **`filter_multi_user`**, **`base_menu_visibility_restriction`**, **`document_quick_access`** (P3) — UX/productivity.
- **Consolidation (custom, not OCA):** merge the six `*_document_sequence` modules and split `od19_misc_features` — reduces maintenance surface.

## REPORTING & DATA RECOMMENDATIONS

- **`bi_sql_editor` + `sql_request_abstract`** (P1) — admin-defined analytical views/reports without new code.
- **`date_range` + `date_range_account`** (P2) — standard reporting periods.
- **`report_qweb_parameter`** (P2) — user-editable report parameters.
- **`base_comment_template`** (P2) — consistent printed notes.
- **`report_qr`** (P2) — QR on documents (e-tax/e-invoice readiness).
- **`report_qweb_element_page_visibility`** (P3) — first/last-page element control (supports ISO footer placement).
- **Pick ONE of** `kpi` **or** `bi_sql_editor` for KPI dashboards — do not stack both.

---

# DELIVERY NOTE — WHAT WAS NOT DONE

Per the assessment constraints, **nothing was installed, upgraded, removed, modified, migrated, or restarted.** No source file, configuration file, access right, or record rule was changed. All findings come from reading `odoo.conf`, `.gitmodules`, module manifests, and the `docs/superpowers/**` governance artifacts.

Any configuration or runtime change discussed above is explicitly labelled **"PROPOSED CHANGE — NOT EXECUTED"** and requires separate approval before implementation.

## Limits of this assessment

- Module compatibility was verified only at the **manifest level** (`19.0.x` declared on branch `19.0`). Functional/runtime behaviour was **not** executed and is marked **COMPATIBILITY NOT VERIFIED (runtime)** where relevant.
- The installed-module set was taken from prior discovery (~234 modules); re-confirm from `ir_module_module` before any installation decision.
- Several custom modules appear to be stubs or report-only placeholders and must be verified before being counted as functional coverage.

---

# ส่วนที่ 3 — การจับคู่ Gap → OCA Solutions

> 📄 **ต้นฉบับเดิม:** `OCA_MODULE_MATCHING.md`

# OCA Module Matching Report: Gaps → OCA Solutions

**วันที่:** 2026-10-14 (อัปเดตล่าสุด: **2026-10-19**)
**วัตถุประสงค์:** จับคู่ฟีเจอร์ที่ยังขาดจาก Gap Analysis กับ OCA modules ที่มีอยู่ใน `third_party/oca` หรือสามารถดึงมาใช้จาก OCA GitHub เพื่อหลีกเลี่ยงการพัฒนา custom module

> ⚠️ **NOTE (2026-10-19):** เอกสารนี้เป็น *ผลวิเคราะห์การจับคู่เชิงประวัติศาสตร์* (ช่วงวางแผน 2026-10-14)
> ตั้งแต่จัดทำเอกสารนี้ ฟีเจอร์ที่เคย "ขาด" เกือบทั้งหมดได้รับการพัฒนาเสร็จแล้ว
> **ให้ยึด [GAP_ANALYSIS_OD15_to_OD19.md](GAP_ANALYSIS_OD15_to_OD19.md) (หัวข้อ "สถานะจริง ณ 2026-10-19") เป็นแหล่งอ้างอิงสถานะหลัก**
> สรุปสถานะส่งมอบ: ✅ IMPLEMENTED 23 · 🟡 PARTIAL 1 · ❌ MISSING 1 (Document Signing)
> ตารางด้านล่างคงไว้เพื่อบันทึกเหตุผลการเลือกใช้ OCA แทนการเขียนเอง (OCA-First)

**สัญลักษณ์:**
- ✅ มี OCA module ครอบคลุม (อยู่ใน third_party แล้ว)
- 🟡 มี OCA module ครอบคลุมบางส่วน (ต้องปรับแต่งเล็กน้อย)
- 🔵 มี OCA module ใน OCA GitHub (ยังไม่ได้ clone เข้ามา)
- ❌ ไม่มี OCA module (ต้องพัฒนาเอง)

---

## 1. Sales (การขาย)

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| 7 master report models (price, delivery, payment product/engineering, validity, warranty, credit) | `base_comment_template` + `sale_order_note_template` | 🟡 | ใช้ comment template สำหรับ terms/conditions ที่เป็นข้อความ แต่ master report models ที่เป็น data-driven ต้อง custom |
| Wizard เปลี่ยนวันที่จัดส่งทั้งเอกสาร | `sale_order_line_date` + `sale_delivery_split_date` | ✅ | `sale_order_line_date` เพิ่ม commitment_date ต่อบรรทัด สามารถเขียน wizard เล็กๆ เพื่ออัปเดตทุกบรรทัดได้ หรือใช้ `sale_order_line_date` + mass edit ได้เลย |
| Wizard "Get Sale Order Lines" บน invoice | `sale_product_set` | 🟡 | `sale_product_set` อนุญาตให้เพิ่มชุดสินค้า แต่ไม่ใช่ดึงจาก SO อื่นๆ — ต้อง custom เล็กน้อยเพื่อเปลี่ยน source เป็น SO |
| Downpayment invoice linking (origin_second/po_origin) | `sale_advance_payment` + `purchase_advance_payment` | ✅ | `sale_advance_payment` รองรับ advance payment บน SO และเชื่อมกับ invoice |
| Cancel Reason บน SO | `sale_cancel_reason` | ✅ | มี wizard cancel พร้อมเหตุผล พร้อม mass cancel |
| Validity period auto-cancel | `sale_validity_auto_cancel` | ✅ | Cron อัตโนมัติยกเลิก SO ที่หมดอายุ |
| Sale Order Type (แยกประเภท) | `sale_order_type` | ✅ | มี model sale.order.type พร้อมกำหนดค่า default ต่างๆ |
| Sub-state บน SO | `sale_substate` + `base_substate` | ✅ | มี sub-state management พร้อม workflow |
| Tier Validation บน SO | `sale_tier_validation` | ✅ | รองรับหลายระดับอนุมัติ |
| Trade discount บน SO | `sale_order_general_discount` | ✅ | ส่วนลดทั้งเอกสาร |
| Triple discount บน SO line | `account_invoice_triple_discount` (dependency) | ✅ | ส่วนลด 3 ชั้นต่อบรรทัด |
| Last price info | `sale_last_price_info` | ✅ | แสดงราคาล่าสุดบน product |

---

## 2. Purchase (การจัดซื้อ)

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| Trade Discount Wizard | `purchase_order_general_discount` + `purchase_triple_discount` | ✅ | ส่วนลดทั้งเอกสาร และ 3 ชั้นต่อบรรทัด |
| 5 master report models (warranty, delivery_to, term, shipment, weight) | `base_comment_template` + `purchase_default_terms_conditions` | 🟡 | Terms/conditions จาก template แต่ data-driven models ต้อง custom |
| PR line pricing (price_unit, discount, taxes) | `purchase_request` (core) | 🟡 | `purchase_request` มี PR line พร้อม price_unit/discount แต่ taxes อาจต้องปรับแต่ง |
| Analytic จาก project บน PR/PO | Odoo native `analytic_distribution` (Odoo 19) + `purchase_request` | ✅ | Odoo 19 มี analytic_distribution บน PO line โดยธรรมชาติ และสามารถดึงจาก project ได้ |
| vendor_ref / your_ref บน PR | `purchase_request` core | 🟡 | มี field partner_ref อยู่แล้ว บางเวอร์ชัน ถ้าไม่มีต้องเพิ่ม |
| Cancel Reason บน PO | `purchase_tier_validation` + `base_cancel_confirm` | 🟡 | ไม่มี cancel reason โดยตรง แต่สามารถใช้ `base_cancel_confirm` |
| Purchase Order Type | `purchase_order_type` | ✅ | มี model purchase.order.type |
| Purchase Request Type | `purchase_request_type` | ✅ | มี model purchase.request.type |
| Tier Validation บน PO | `purchase_tier_validation` | ✅ | รองรับหลายระดับอนุมัติ |
| Purchase deposit/advance payment | `purchase_deposit` + `purchase_advance_payment` | ✅ | สร้าง deposit/advance จาก PO |
| Last price info | `purchase_last_price_info` | ✅ | แสดงราคาซื้อล่าสุดบน product |
| Purchase stock price unit sync | `purchase_stock_price_unit_sync` | ✅ | อัปเดต cost price ใน stock moves ที่ทำแล้ว |

---

## 3. Accounting (การบัญชี)

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| Asset Disposal Workflow | `account_asset_disposal` (OCA/account-financial-tools) | 🔵 | มีใน OCA GitHub สำหรับเวอร์ชันเก่า ต้องตรวจสอบ Odoo 19 หรือ port มาใช้งาน |
| WHT PDF Print (4 แบบ: ภงด.1, ภงด.3, ภงด.53, ภงด.53 ทริส) | `l10n_th_account_tax` + `l10n_th_withholding_tax_cert_form` | ✅🔵 | `l10n_th_account_tax` **อยู่ใน third_party แล้ว มี WHT cert และ PND1/PND3/PND53 forms `l10n_th_withholding_tax_cert_form` อยู่ใน OCA GitHub |
| WHT base computed + wht.type model | `l10n_th_account_tax` | ✅ | มี model `withholding.tax.code.income`, `withholding.tax.cert`, WHT calculation บน payment |
| Cancel Reason Wizard บน invoice | `account_move_cancel_confirm` + `account_invoice_refund_reason` (OCA/account-invoicing) | 🔵 | `account_move_cancel_confirm` ยืนยันการ cancel `account_invoice_refund_reason` เหตุผลคืนเงิน |
| Payer/Payee บน prepayment | `account_payment_partner` (OCA/bank-payment) | 🔵 | เพิ่ม payment mode และ partner บน payment |
| Create vendor bill from PO wizard | Odoo native + `purchase` | ✅ | Odoo มี native "Create Bill" จาก PO อยู่แล้ว |
| BOT URL config | ต้อง custom | ❌ | ไม่มี OCA module เฉพาะ |
| Prepayment actual due date (+30 days) | `account_payment_partner` + custom cron | 🟡 | ใช้ custom field + cron สำหรับ +30 days |
| Account Move sequence จาก sequence | `account_move_name_sequence` | ✅ | มีอยู่ใน third_party |
| Invoice chronology constraint | `account_invoice_constraint_chronology` | ✅ | บังคับวันที่เรียงลำดับ |
| Tier Validation บน invoice | `account_move_tier_validation` | ✅ | มีอยู่แล้ว |
| Cancel confirm บน invoice | `base_cancel_confirm` | ✅ | มี wizard cancel confirm |

---

## 4. Project (โครงการ)

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| Project Risk Report (SQL view + risk score) | `bi_sql_editor` | 🟡 | ใช้สร้าง SQL view สำหรับ risk report แต่ risk score logic ต้องเขียน SQL เอง |
| Hierarchical Project Type model | `project` native (Odoo) | 🟡 | Odoo มี project type แต่ hierarchical อาจต้อง custom |
| Task deadline email notification cron | `project` native + `base_automation` (Odoo native) | ✅ | ใช้ Automated Actions ธรรมชาติ |
| No backward stage change | `project_task_stage_force` หรือ custom constraint | 🟡 | ไม่มี OCA โดยตรง ต้อง custom หรือใช้ server action |
| Job Assignment Document fields | `project` native + custom fields | 🟡 | ต้อง custom fields |
| SO/PO linking จาก project | `sale_purchase_stock_auto_confirm` หรือ native | 🟡 | Odoo มี project linking กับ SO/PO แต่อาจต้อง custom |
| Project milestones | `project_milestone` (OCA/project) | 🔵 | มีใน OCA GitHub |
| Project budget | `project_budget` (OCA/project) | 🔵 | มีใน OCA GitHub |

---

## 5. HR/Expense/Fleet

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| Department head as auto approver | `hr_expense_tier_validation` + `base_tier_validation_formula` | 🟡 | ใช้ tier validation formula เพื่อกำหนด approver จาก dept head อัตโนมัติ |
| Cash tracking state (expense) + return/reset wizards | ต้อง custom | ❌ | ไม่มี OCA module เฉพาะ |
| XLSX expense reports | `report_xlsx` + custom report | 🟡 | ใช้ `report_xlsx` เป็น base แล้วเขียน report เอง |
| Delegate approvals | `base_tier_validation_forward` | ✅ | มี forward tier validation |
| WHT for expense payment | `l10n_th_account_tax` | ✅ | WHT บน payment รองรับ expense ได้ |
| Insurance/Act expire date + email notification cron | `fleet` native + `base_automation` | 🟡 | Odoo fleet มี contract/insurance ใช้ Automated Actions สำหรับ email |
| Service done notification | `fleet` native + `base_automation` | 🟡 | ใช้ Automated Actions |
| Expense Tier Validation | `hr_expense_tier_validation` | ✅ | มีอยู่ใน third_party |

---

## 6. Stock/Inventory (สต็อก)

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| FIFO valuation service + monthly stock report email cron | `stock_account` native + `stock_account_valuation_report` (OCA/stock-logistics-reporting) | 🔵 | Odoo มี FIFO native แต่ as-of report ต้องใช้ OCA module |
| FIFO as-of wizard | `stock_inventory_valuation_report` (OCA/stock-logistics-reporting) | 🔵 | มีใน OCA GitHub |
| BF revaluation | `stock landeds_costs` (Odoo native) | 🟡 | Odoo มี landed costs แต่ BF revaluation อาจต้อง custom |
| stock.picking.additional.line model | `purchase_landed_cost` (OCA) หรือ custom | 🟡 | ไม่มีโดยตรง แต่สามารถใช้ landed cost หรือ custom |
| Signature chain auto-resolve | `signature` (Odoo native) | 🟡 | Odoo มี sign app แต่ auto-resolve chain ต้อง custom |

---

## 7. Reports/Misc

| ฟีเจอร์ที่ขาด | OCA Module Match | สถานะ | คำอธิบาย |
|---------------|-------------------|--------|----------|
| Document Signing (sign) | `sign` (Odoo native - Enterprise) | 🟡 | Odoo Sign เป็น Enterprise feature สำหรับ CE อาจต้องใช้ OCA หรือ custom |
| logo_iso field | custom field | ❌ | ไม่มี OCA module เฉพาะ |
| Skip date/sequence constraint | `l10n_th_base_sequence` + custom | 🟡 | `l10n_th_base_sequence` มี BE year แต่ skip constraint ต้อง custom |
| Runtime guard tool | `auditlog` + custom | 🟡 | ใช้ auditlog สำหรับ tracking แต่ runtime guard ต้อง custom |
| Abstract service preserve sale_line_ids/purchase_line_id | custom abstract model | ❌ | ไม่มี OCA module เฉพาะ ต้องสร้าง abstract |
| Sequence reset period | `sequence_reset_period` (server-ux) | ✅ | มีอยู่ใน third_party |
| Audit log (deleted/changed records) | `auditlog` (server-tools) | ✅ | มีอยู่ใน third_party |
| XLSX report engine | `report_xlsx` (reporting-engine) | ✅ | มีอยู่ใน third_party |
| PDF report parameters | `report_qweb_parameter` (reporting-engine) | ✅ | มีอยู่ใน third_party |

---

## 📊 สรุปภาพรวม

### OCA modules ที่มีอยู่แล้วใน third_party (สามารถใช้ได้ทันที)

| OCA Module | ครอบคลุมฟีเจอร์ |
|------------|-------------------|
| `l10n_th_account_tax` | WHT types, WHT cert, WHT calculation, PND forms, PIT |
| `l10n_th_amount_to_text` | แปลงตัวเลขเป็นข้อความไทย |
| `l10n_th_base_sequence` | Buddhist Era year ใน sequence |
| `auditlog` | Track deleted/changed records |
| `report_xlsx` | XLSX report engine |
| `account_asset_management` | Base asset management |
| `sale_cancel_reason` | Cancel reason บน SO |
| `sale_order_general_discount` | ส่วนลดทั้งเอกสารบน SO |
| `sale_order_line_date` | commitment date ต่อบรรทัด SO |
| `sale_delivery_split_date` | แยก delivery ตามวันที่ |
| `sale_order_type` | SO type |
| `sale_substate` | Sub-state บน SO |
| `sale_tier_validation` | Tier validation บน SO |
| `sale_validity_auto_cancel` | Auto-cancel SO หมดอายุ |
| `sale_advance_payment` | Advance payment บน SO |
| `sale_last_price_info` | ราคาขายล่าสุด |
| `purchase_order_general_discount` | ส่วนลดทั้งเอกสารบน PO |
| `purchase_triple_discount` | ส่วนลด 3 ชั้นบน PO |
| `purchase_order_type` | PO type |
| `purchase_request_type` | PR type |
| `purchase_tier_validation` | Tier validation บน PO |
| `purchase_deposit` | Deposit จาก PO |
| `purchase_advance_payment` | Advance payment บน PO |
| `purchase_last_price_info` | ราคาซื้อล่าสุด |
| `purchase_stock_price_unit_sync` | Sync ราคา cost ใน stock |
| `base_cancel_confirm` | Cancel confirm wizard |
| `account_move_name_sequence` | Sequence จาก journal entry |
| `account_invoice_constraint_chronology` | Chronology constraint |
| `account_move_tier_validation` | Tier validation บน invoice |
| `hr_expense_tier_validation` | Tier validation บน expense |
| `base_tier_validation_forward` | Forward/delegate approvals |
| `base_substate` | Base sub-state |
| `sequence_reset_period` | Reset sequence ตามช่วงเวลา |
| `bi_sql_editor` | สร้าง SQL view สำหรับ BI |
| `base_comment_template` | Comment/terms templates |
| `sale_order_note_template` | SO terms template |
| `purchase_default_terms_conditions` | PO default terms |
| `sale_product_set` | Product set บน SO |
| `report_qweb_parameter` | Report parameters |
| `purchase_request` | Purchase request (PR) |

### OCA modules ที่ต้อง clone เพิ่มจาก OCA GitHub

| OCA Module | Repository | ครอบคลุมฟีเจอร์ |
|------------|------------|-------------------|
| `account_asset_disposal` | OCA/account-financial-tools | Asset disposal workflow |
| `l10n_th_withholding_tax_cert_form` | OCA/l10n-thailand | WHT cert PDF form (Thai standard) |
| `account_move_cancel_confirm` | OCA/account-invoicing | Cancel confirm บน invoice |
| `account_invoice_refund_reason` | OCA/account-invoicing | Refund reason |
| `account_payment_partner` | OCA/bank-payment | Payer/Payee บน payment |
| `stock_account_valuation_report` | OCA/stock-logistics-reporting | Stock valuation report |
| `stock_inventory_valuation_report` | OCA/stock-logistics-reporting | Inventory valuation as-of |
| `project_milestone` | OCA/project | Project milestones |
| `project_budget` | OCA/project | Project budget |
| `purchase_landed_cost` | OCA/purchase-workflow | Landed cost (อาจช่วย additional line) |

### ฟีเจอร์ที่ไม่มี OCA module (ต้องพัฒนา custom)

| ฟีเจอร์ | เหตุผล |
|---------|---------|
| BOT URL config | เฉพาะธุรกิจไทย ไม่มี OCA |
| Cash tracking state (expense) | ไม่มี OCA module เฉพาะ |
| logo_iso field | เฉพาะบริษัท ไม่มี OCA |
| Skip date/sequence constraint (skip logic) | ต้อง custom logic |
| Runtime guard tool | เฉพาะ internal tool ไม่มี OCA |
| Abstract service preserve sale_line_ids/purchase_line_id | เฉพาะ business logic ไม่มี OCA |
| No backward stage change (project) | ไม่มี OCA โดยตรง |
| stock.picking.additional.line model | ไม่มี OCA โดยตรง (สามารถใช้ landed cost แทนได้บางส่วน) |

---

## 🎯 ข้อเสนอแนะ

### ลำดับความสำคัญในการนำ OCA module

**ระดับ 1 (ใช้ได้ทันที - อยู่ใน third_party แล้ว):**
1. `l10n_th_account_tax` — ครอบคลุม WHT ทั้งหมด (สำคัญที่สุด)
2. `sale_cancel_reason`, `purchase_order_general_discount`, `purchase_triple_discount`
3. `sale_order_line_date`, `sale_delivery_split_date` — delivery date
4. `sale_tier_validation`, `purchase_tier_validation`, `hr_expense_tier_validation` — approvals
5. `sale_advance_payment`, `purchase_advance_payment`, `purchase_deposit` — downpayment
6. `sale_order_type`, `purchase_order_type`, `purchase_request_type` — document types
7. `base_comment_template`, `sale_order_note_template`, `purchase_default_terms_conditions` — terms templates
8. `bi_sql_editor` — SQL views สำหรับ reports
9. `base_tier_validation_forward` — delegate approvals
10. `sale_validity_auto_cancel` — auto-cancel expired SO

**ระดับ 2 (ต้อง clone จาก OCA GitHub):**
1. `account_asset_disposal` — asset disposal
2. `l10n_th_withholding_tax_cert_form` — WHT PDF forms
3. `account_move_cancel_confirm`, `account_invoice_refund_reason` — cancel/refund reasons
4. `account_payment_partner` — payer/payee
5. `stock_account_valuation_report` — stock valuation

**ระดับ 3 (ต้องพัฒนา custom เท่านั้น):**
1. BOT URL config
2. Cash tracking state
3. Skip date/sequence constraint logic
4. Runtime guard tool
5. Abstract service for line preservation

---

## 💡 ข้อสังเกตสำคัญ

1. **WHT** — `l10n_th_account_tax` ที่มีอยู่แล้วใน third_party ครอบคลุม WHT ได้เกือบทั้งหมด รวมถึง wht.type model, WHT cert, PND1/PND3/PND53 เพียงแค่ต้องเพิ่ม `l10n_th_withholding_tax_cert_form` สำหรับ PDF form มาตรฐานไทย

2. **Approvals** — ใช้ `tier-validation` modules ทั้งหมด ที่มีอยู่แล้วใน third_party ได้เลย สำหรับ dept head auto-approver ใช้ `base_tier_validation_formula` เพื่อกำหนด formula

3. **Discount** — ใช้ `purchase_order_general_discount` และ `purchase_triple_discount` สำหรับ trade discount บน PO และ `sale_order_general_discount` สำหรับ SO

4. **Delivery date** — ใช้ `sale_order_line_date` + `sale_delivery_split_date` ได้เลย

5. **Downpayment** — ใช้ `sale_advance_payment` และ `purchase_advance_payment` / `purchase_deposit`

6. **Analytic** — Odoo 19 มี `analytic_distribution` โดยธรรมชาติบน PO/SO line สามารถดึงจาก project ได้

7. **Reports** — ใช้ `bi_sql_editor` สำหรับ SQL views และ `report_xlsx` สำหรับ XLSX reports

---

# ส่วนที่ 4 — แผนติดตั้ง / โรลเอาต์ — โมดูล `auditlog`

> 📄 **ต้นฉบับเดิม:** `OCA_ROLLOUT_PLAN_auditlog_TH.md`

# แผนติดตั้ง / โรลเอาต์ — โมดูล `auditlog` (OCA Audit Log)

> ⚠️ **PROPOSED CHANGE — NOT EXECUTED**
> เอกสารนี้เป็น **แผน** เท่านั้น ยังไม่มีการติดตั้ง อัปเกรด แก้ไข config/สิทธิ์ หรือรีสตาร์ตบริการใด ๆ ทุกคำสั่งในเอกสารนี้เป็น *ข้อเสนอ* ที่ต้องได้รับอนุมัติก่อนดำเนินการ
>
> 📌 **STATUS (อัปเดต 2026-10-19):** เอกสารนี้คงไว้เป็น *ข้อเสนอเชิงแผน* สำหรับอ้างอิง สำหรับสถานะส่งมอบล่าสุด ให้ยึด [GAP_ANALYSIS_OD15_to_OD19.md](file:///c:/odoo-dev/odoo19/GAP_ANALYSIS_OD15_to_OD19.md)

| หัวข้อ | ค่า |
| --- | --- |
| โมดูล | Audit Log |
| ชื่อเทคนิค | `auditlog` |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/auditlog` |
| เวอร์ชัน (manifest) | `19.0.2.0.0` |
| License | AGPL-3 |
| Dependencies | `base` (เท่านั้น — ไม่มี dependency ภายนอก/pip เพิ่ม) |
| `application` | `True` |
| หมวด OCA | B — Monitoring & Anomaly Detection |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **MEDIUM** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

---

## 1. เหตุผลและเป้าหมาย

**ปัญหาที่แก้:** ปัจจุบันระบบไม่มีบันทึกการตรวจสอบการเขียน/ลบข้อมูลเลย ทำให้:
- ไม่สามารถตอบคำถาม "ใครแก้/ลบเรกคอร์ดนี้ เมื่อไร ค่าเดิมคืออะไร" ได้
- ISO 9001 ต้องการการตรวจสอบย้อนหลังของเอกสารควบคุม
- ไม่มีหลักฐานประกอบการตรวจสอบทางการเงิน/ภาษี

**ผลลัพธ์ที่ต้องการ (Owner Value):**
1. ตรวจสอบย้อนหลังได้ระดับฟิลด์ (ค่าเก่า → ค่าใหม่) พร้อมผู้ใช้/เวลา/IP
2. มีหลักฐานสำหรับ ISO 9001 และการตรวจสอบภายใน
3. ระบุความผิดปกติ (anomaly) เช่น การแก้ไขย้อนหลัง การลบผิดพลาด

**สิ่งที่อยู่นอกขอบเขต (Out of scope):**
- ไม่ใช่ระบบอนุมัติ (ใช้ `base_tier_validation` ที่มีอยู่)
- ไม่ใช่ monitoring ระดับ infrastructure (ใช้ `sentry` แยก)
- ไม่แทนที่ field tracking ของ Odoo (`mail.thread`) — ใช้ร่วมกัน

---

## 2. ข้อกำหนดเบื้องต้น (Prerequisites)

| # | รายการ | สถานะที่ต้องยืนยัน |
| --- | --- | --- |
| 1 | submodule `third_party/oca/server-tools` มีอยู่และ checkout branch 19.0 | พบแล้ว (ตรวจ manifest แล้ว) |
| 2 | `addons_path` รวม `third_party/oca/server-tools` | พบแล้วใน `odoo.conf` |
| 3 | ไม่มี Python dependency เพิ่ม | ยืนยัน: depends เพียง `base` |
| 4 | มี backup ฐานข้อมูล + filestore ที่กู้คืนได้ก่อนติดตั้ง | ต้องทำก่อน (ดูข้อ 5) |
| 5 | พื้นที่ดิสก์เพียงพอสำหรับตาราง log + retention | ต้องประเมิน |
| 6 | ยืนยันว่า `auditlog` = "to install" ในสคีมา 19.0.1.3 | ต้องตรวจ `ir_module_module` |

**หมายเหตุ License:** โมดูลเป็น AGPL-3 — ใช้ภายในองค์กร (ไม่แจกจ่าย/ไม่เปิดเป็นบริการสาธารณะ) ไม่ก่อภาระเผยแพร่ซอร์ส แต่ควรบันทึกไว้ในการทบทวนสิทธิ์

---

## 3. รูปแบบข้อมูลและองค์ประกอบที่จะเกิดขึ้น

จากซอร์สจริงของโมดูล:

**โมเดล (ตารางใหม่):**
- `auditlog.rule` — กฎการตรวจสอบ (โมเดลเป้าหมาย, ฟิลด์ที่บันทึก, การ subscribe)
- `auditlog.log` — หัวบันทึก (โมเดล/เรกคอร์ด/การดำเนินการ/ผู้ใช้/เวลา)
- `auditlog.log.line` — รายละเอียดระดับฟิลด์ (ค่าเก่า/ค่าใหม่)
- `auditlog.log.line.view` — มุมมองประกอบ
- `auditlog.http.request` — ข้อมูล HTTP request (IP, method, URL)
- `auditlog.http.session` — ข้อมูล session ที่เกี่ยวข้อง
- `auditlog.autovacuum` (wizard) — ลบ log เก่า

**กลุ่มสิทธิ์ (Odoo 19 ใช้ `res.groups.privilege` + `privilege_id`):**
- `auditlog.group_auditlog_user` — อ่าน log เท่านั้น (ผ่าน action "View Logs" บนเรกคอร์ดที่ถูกติดตาม)
- `auditlog.group_auditlog_manager` — จัดการกฎการตรวจสอบ
- `base.group_system` (ERP Administrator) → สืบทอด `group_auditlog_manager` อัตโนมัติ

**Scheduled Action (สร้างให้ แต่ปิดไว้):**
- ชื่อ `Auto-vacuum audit logs`, code `model.autovacuum(180)`, รอบ 1 วัน, `active = False`
- ต้องเปิดใช้งานเอง + ตั้ง retention ตามนโยบาย

**Migration:** มี `migrations/19.0.1.0.0/post-migration.py` (ทำงานอัตโนมัติตอนอัปเกรด)

**เมนู:** Settings / Technical / Audit / Rules และ Settings / Technical / Audit / Logs

---

## 4. ลำดับสภาพแวดล้อม (ตามนโยบาย 5 สภาพแวดล้อมของโครงการ)

ห้ามติดตั้งบน Production ก่อนผ่านขั้นก่อนหน้า:

```
Local Dev → Shared Dev/Integration → Test/QA → UAT/Training → Production
```

| สภาพแวดล้อม | เป้าหมายของรอบนี้ |
| --- | --- |
| Local Dev (Windows) | ติดตั้ง + ตั้งกฎ + ทดสอบฟังก์ชัน + วัดผลกระทบ |
| Shared Dev/Integration | ยืนยันว่าไม่ขัดกับโมดูลกำหนดเอง/OCA ที่ติดตั้ง |
| Test/QA | ทดสอบภาระงาน (write volume) + autovacuum |
| UAT/Training | ผู้ตรวจสอบ/MR ใช้งานจริง, ตรวจ ACL |
| Production | เปิดใช้จริงหลังผ่าน UAT + มีแผนย้อนกลับ |

---

## 5. ขั้นตอนติดตั้ง (PROPOSED — ยังไม่ดำเนินการ)

### ขั้นที่ 1 — Pre-flight (อ่านเท่านั้น)
- [ ] ยืนยันเวอร์ชันจริง: `ir_module_module` มี `auditlog` state = `uninstalled`/ยังไม่มี
- [ ] ตรวจว่ารายการที่ติดตั้ง ~234 ไม่มีโมดูลที่ดึงตารางทับซ้อน
- [ ] ตรวจพื้นที่ดิสก์และขนาด DB ปัจจุบัน
- [ ] บันทึก baseline: จำนวนเรกคอร์ดในตารางที่จะถูกติดตาม + เวลาตอบสนองปัจจุบัน

### ขั้นที่ 2 — Backup (บังคับก่อนติดตั้ง)
- [ ] `pg_dump` ฐานข้อมูล `odoo19` (ใช้ `.pgpass` หรือ prompt แบบ interactive — **ห้ามใส่รหัสผ่านใน command line**)
- [ ] สำรอง filestore `C:\odoo-dev\odoo19\data`
- [ ] ทดสอบกู้คืนบนฐานข้อมูลชั่วคราว

### ขั้นที่ 3 — ติดตั้งโมดูล
ทางเลือก A (UI — แนะนำบน Dev):
- Apps → Update Apps List → ค้นหา "Audit Log" → Install

ทางเลือก B (CLI — แนะนำบน Integration/QA):
```
python odoo-bin -c odoo.conf -d odoo19 -i auditlog --stop-after-init
```
(ปรับพาธ `odoo-bin`/`odoo.conf` ตามสภาพแวดล้อม Windows/Linux)

### ขั้นที่ 4 — รีสตาร์ตและตรวจสอบ
- [ ] รีสตาร์ตบริการ Odoo (Windows service / systemd)
- [ ] ตรวจ `odoo_server.log` ว่าไม่มี ERROR/WARNING จาก `auditlog`
- [ ] ยืนยัน Registry โหลดครบ (จำนวนโมดูลเท่าเดิม +1)

### ขั้นที่ 5 — ตั้งค่าหลังติดตั้ง
- [ ] เปิดใช้งาน `Auto-vacuum audit logs` (Scheduled Actions) และตั้ง retention ตามนโยบาย
- [ ] กำหนดผู้ใช้เข้ากลุ่ม `Auditlog Manager` (ผู้ดูแลระบบเท่านั้น)
- [ ] กำหนดผู้ใช้เข้ากลุ่ม `Auditlog User` (ผู้ตรวจสอบภายใน/บัญชี — อ่านเท่านั้น)
- [ ] พิจารณา PostgreSQL autovacuum ของตาราง `auditlog_log*` (โมดูลอ้างถึงการปรับค่านี้ใน description)

---

## 6. การกำหนดขอบเขตโมเดล (Model Scoping Matrix)

> หลักการ: **เลือกเฉพาะโมเดลที่สำคัญ** — ไม่เปิดทั้งระบบ เพื่อควบคุม write amplification
> ทุกกฎใหม่ต้อง "Subscribe" จึงจะเริ่มบันทึก

| ลำดับ | โมเดล | เหตุผล | ระดับ |
| --- | --- | --- | --- |
| 1 | `sale.order` | สัญญา/ใบเสนอราคา, ส่วนลด, เงื่อนไข | สูง |
| 2 | `account.move` | ใบแจ้งหนี้/ใบกำกับภาษี — การเงิน/ภาษี | สูง |
| 3 | `account.payment` | การชำระเงิน/เช็ค/ค่าธรรมเนียม | สูง |
| 4 | `purchase.order` | จัดซื้อ, ราคา, ผู้ขาย | สูง |
| 5 | `res.partner` | เครดิต/แบล็คลิสต์ (กำหนดฟิลด์ที่ติดตาม) | สูง |
| 6 | `sales.contract` (od19) | วงเงิน/การใช้จริงตามสัญญาหลัก | สูง |
| 7 | `account.cheque` / `account.cheque.book` (od19) | สมุดเช็ค | กลาง |
| 8 | `iso.document` (od19) | เอกสารควบคุม ISO — ตรวจสอบย้อนหลัง | กลาง |
| 9 | `account.asset` (OCA) | การตัดจำหน่าย/โอนสินทรัพย์ | กลาง |
| 10 | `product.return` (od19) | RMA/การคืนสินค้า | กลาง |

**โมเดลที่ควร "ยกเว้น" (ห้ามติดตาม):** `mail.message`, `mail.tracking.value`, `mail.followers`, `bus.bus`, `ir.logging`, `ir.cron`, `ir.attachment` (ปริมาณสูง), และตาราง `auditlog.*` เอง

**สำหรับ `res.partner`:** ไม่ควรติดตามทุกฟิลด์ — เลือกเฉพาะ `credit_limit`, สถานะแบล็คลิสต์, เงื่อนไขการชำระ เนื่องจากมี write ปริมาณสูง

---

## 7. ผลกระทบและแนวทางปรับประสิทธิภาพ

| ประเด็น | ผลกระทบ | แนวทาง |
| --- | --- | --- |
| Write amplification | ทุก create/write/unlink ของโมเดลที่ติดตามจะเขียนเพิ่ม (หัว + บรรทัดต่อฟิลด์ที่เปลี่ยน) | จำกัดโมเดล/ฟิลด์ (ข้อ 6) |
| ขนาด DB | ตาราง `auditlog_log*` โตต่อเนื่อง | เปิด autovacuum cron + ตั้ง retention |
| `workers = 0` (threaded) | การวัดผลกระทบต้องวัดในโหมดรันไทม์จริง | วัดก่อน/หลังบน Integration; พิจารณา `workers=N` แยกเป็นอีกงาน |
| การลบ (unlink) | พฤติกรรมการบันทึกการลบ (รวม cascade/SQL-level) | **ต้องยืนยันในขั้นทดสอบ** — ระบุ COMPATIBILITY NOT VERIFIED |
| PostgreSQL autovacuum | ตาราง log อาจทำให้ autovacuum ทำงานหนัก | พิจารณาปรับ per-table autovacuum |
| ขนาดตารางล็อกของ DB | เพิ่มขึ้นจาก baseline | เทียบ baseline ข้อ 5.1 |

---

## 8. ความปลอดภัยและการเข้าถึง

- **อ่าน log:** เฉพาะกลุ่ม `auditlog.group_auditlog_user` ขึ้นไป
- **จัดการกฎ:** เฉพาะกลุ่ม `auditlog.group_auditlog_manager` (ผู้ดูแลระบบได้มาอัตโนมัติ)
- **ระวัง:** log อาจมีข้อมูลอ่อนไหว (ค่าเก่า/ใหม่ของฟิลด์การเงิน) → จำกัดผู้เข้าถึง
- **ห้าม** ให้สิทธิ์ Manager แก่ผู้ใช้ทั่วไป เพราะสามารถปิด/แก้กฎเพื่อลบร่องรอยได้
- พิจารณาแยกกลุ่มสำหรับ "ผู้ตรวจสอบภายใน/ISO" แบบอ่านอย่างเดียว
- ตรวจสอบว่าไม่มี record rule ของโมดูลกำหนดเองที่บังเอิญเปิด/ปิดการเข้าถึง `auditlog.*`

---

## 9. เกณฑ์การยอมรับ (Acceptance Criteria)

ต้องผ่านทุกข้อบน Integration/QA ก่อนไป UAT:

1. แก้ไขเรกคอร์ด `sale.order` → เกิด `auditlog.log` + `log.line` ที่บันทึกค่าเก่า/ใหม่ถูกต้อง
2. สร้าง/แก้ `account.move` → บันทึกครบพร้อมผู้ใช้และเวลา
3. ลบเรกคอร์ดที่ติดตาม → มีบันทึกการลบ (**ต้องยืนยันว่าทำงานจริง**)
4. เปิด action "View Logs" บนเรกคอร์ด → เห็นเฉพาะ log ของเรกคอร์ดนั้น
5. โมเดลที่ **ไม่ได้** สร้างกฎ → ไม่เกิด log (ยืนยันว่าไม่ leak)
6. ผู้ใช้ที่ไม่มีกลุ่ม `Auditlog User` → เข้าเมนู Logs ไม่ได้
7. `Auto-vacuum` ทำงาน: ลบ log เก่ากว่า N วันตามที่ตั้ง
8. ไม่มี ERROR/WARNING ใหม่ใน `odoo_server.log` หลังรีสตาร์ต
9. เวลาตอบสนองของ write หลักไม่แย่ลงเกินเกณฑ์ที่ยอมรับ (วัดจาก baseline ข้อ 5.1)

*(โมดูลมีชุดทดสอบของตัวเองในโฟลเดอร์ `tests/` — สามารถอ้างอิงเป็นแนวทางได้)*

---

## 10. การตรวจสอบหลังติดตั้ง (Monitoring)

- ตรวจขนาดตาราง `auditlog_log`, `auditlog_log_line` รายสัปดาห์
- ตรวจว่า cron autovacuum ทำงานจริง (ไม่มี = DB โตไม่หยุด)
- ดู `odoo_server.log` ว่าไม่มี warning จาก auditlog
- เมื่อติดตั้ง `sentry`/`scheduler_error_mailer` แล้ว จะได้การแจ้งเตือนอัตโนมัติ

---

## 11. แผนย้อนกลับ (Rollback)

| สถานการณ์ | การดำเนินการ |
| --- | --- |
| โหลดโมดูลล้มเหลว | ตรวจ log, ยังไม่ต้องถอน; แก้ dependency/พาธ |
| ประสิทธิภาพแย่เกินเกณฑ์ | ปิด (unsubscribe) กฎโมเดลที่หนักก่อน — ไม่ต้องถอนโมดูล |
| ต้องถอนทั้งหมด | Uninstall ผ่าน Apps → **ตาราง `auditlog.*` และประวัติ log จะหาย** → ต้อง export log ก่อนถอน |
| ฐานข้อมูลเสียหาย | กู้คืนจาก backup ในข้อ 5.2 |

**คำเตือนสำคัญ:** การถอนโมดูลทำให้ **สูญเสียประวัติการตรวจสอบทั้งหมด** — ต้องพิจารณาเก็บถาวรแยกก่อน

---

## 12. ความเสี่ยงและแนวทางบรรเทา

| ความเสี่ยง | ระดับ | แนวทางบรรเทา |
| --- | --- | --- |
| Write latency เพิ่มจากการติดตามมากเกินไป | MEDIUM | จำกัดโมเดล/ฟิลด์ + วัดก่อน/หลัง |
| DB โตไม่หยุด (ไม่เปิด autovacuum) | MEDIUM | เปิด cron + retention + ตรวจรายสัปดาห์ |
| ผู้มีสิทธิ์ Manager ปิดร่องรอย | MEDIUM | จำกัดกลุ่มแคบ + ตรวจการเปลี่ยนกฎผ่าน `sentry`/audit ของ Odoo |
| สูญเสีย log เมื่อถอนโมดูล | MEDIUM | export ก่อนถอน + backup |
| พฤติกรรมการบันทึก unlink ไม่ตรงคาดหวัง | MEDIUM | ทดสอบยืนยันใน QA ก่อน UAT (เกณฑ์ข้อ 9.3) |
| ความเข้ากันได้รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ติดตั้งบน Local/Integration ก่อนเสมอ |

---

## 13. รายการงานตามลำดับ (Task Checklist — ไม่ระบุเวลา)

- [ ] T1 Pre-flight checks + baseline (ข้อ 5.1)
- [ ] T2 Backup DB + filestore + ทดสอบกู้คืน (ข้อ 5.2)
- [ ] T3 ติดตั้งบน Local Dev (ข้อ 5.3)
- [ ] T4 รีสตาร์ต + ตรวจ log/registry (ข้อ 5.4)
- [ ] T5 สร้างกฎตาม Model Scoping Matrix (ข้อ 6)
- [ ] T6 ตั้งกลุ่มสิทธิ์ (ข้อ 8)
- [ ] T7 เปิด autovacuum cron + retention (ข้อ 5.5)
- [ ] T8 ทดสอบตามเกณฑ์การยอมรับ (ข้อ 9)
- [ ] T9 วัดผลกระทบประสิทธิภาพ เทียบ baseline (ข้อ 7)
- [ ] T10 ย้ำบน Shared Dev/Integration → Test/QA → UAT ตามลำดับ (ข้อ 4)
- [ ] T11 เตรียม rollback + export log (ข้อ 11)
- [ ] T12 อนุมัติ go/no-go ก่อน Production

---

## 14. การอนุมัติและหลักฐานที่ต้องเก็บ (Discovery Evidence)

| ผู้รับผิดชอบ | หน้าที่ |
| --- | --- |
| Config owner | ยืนยัน `odoo.conf`/addons_path ไม่เปลี่ยนนอกแผน |
| Deployment owner | รันขั้นตอนติดตั้ง + เก็บหลักฐานทุกรอบ |
| Security reviewer | ตรวจกลุ่ม `Auditlog Manager/User` และการเข้าถึง log |
| Backup owner | ยืนยัน backup + restore สำเร็จก่อนติดตั้ง |
| Incident first responder | เฝ้าระหว่างติดตั้ง Production |

**หลักฐานที่ต้องเก็บทุกรอบ:** ผล pre-flight, log การติดตั้ง, ภาพหน้าจอกฎที่สร้าง, ผลทดสอบเกณฑ์ยอมรับ, ค่า perf ก่อน/หลัง, ผลทดสอบ restore

---

## 15. ภาคผนวก — คำสั่งอ้างอิง (PROPOSED — ยังไม่รัน)

ติดตั้ง (CLI):
```
python odoo-bin -c odoo.conf -d odoo19 -i auditlog --stop-after-init
```
อัปเดตโมดูลภายหลัง:
```
python odoo-bin -c odoo.conf -d odoo19 -u auditlog --stop-after-init
```
ตรวจสถานะโมดูล (อ่านเท่านั้น — ผ่าน UI: Apps / Technical / Modules) หรือ SQL:
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'auditlog';
```
ตรวจขนาดตาราง log (อ่านเท่านั้น):
```sql
SELECT pg_size_pretty(pg_total_relation_size('auditlog_log')),
       pg_size_pretty(pg_total_relation_size('auditlog_log_line'));
```

> หมายเหตุ: ห้ามใส่รหัสผ่านฐานข้อมูลใน command line ให้ใช้ `.pgpass` หรือ interactive prompt เท่านั้น

---

**สรุป:** แผนนี้อ้างอิงซอร์สจริงของ `auditlog` 19.0.2.0.0 (depends เพียง `base`, มีกลุ่มสิทธิ์ `Auditlog User/Manager`, cron autovacuum ปิดไว้โดยค่าเริ่มต้น) ความเสี่ยงหลักคือผลกระทบประสิทธิภาพและขนาด DB ซึ่งควบคุมได้ด้วยการจำกัดขอบเขตโมเดลและ retention — **ยังไม่มีการดำเนินการใด ๆ ตามแผนนี้**

---

# ส่วนที่ 5 — แผนติดตั้ง / โรลเอาต์ — กลุ่ม P1 ที่เหลือ (8 โมดูล)

> 📄 **ต้นฉบับเดิม:** `OCA_ROLLOUT_PLANS_P1_TH.md`

# แผนติดตั้ง / โรลเอาต์ — โมดูล OCA กลุ่ม P1 ชุดที่เหลือ (8 โมดูล)

> ⚠️ **PROPOSED CHANGE — NOT EXECUTED**
> เอกสารนี้เป็น **แผน** เท่านั้น **ยังไม่มีการติดตั้ง อัปเกรด ถอน แก้ไข config/สิทธิ์/record rule หรือรีสตาร์ตบริการใด ๆ**
> ทุกคำสั่งในเอกสารนี้เป็น *ข้อเสนอ* ที่ต้องได้รับอนุมัติก่อนดำเนินการ
> ฉบับนี้เป็นภาคต่อของ [OCA_MODULE_ASSESSMENT_TH.md](file:///c:/odoo-dev/odoo19/OCA_MODULE_ASSESSMENT_TH.md) โดยใช้โครงสร้าง 15 หัวข้อเดียวกัน
>
> 📌 **STATUS (อัปเดต 2026-10-19):** เอกสารนี้คงไว้เป็น *ข้อเสนอเชิงแผน* สำหรับอ้างอิง สำหรับสถานะส่งมอบล่าสุด ให้ยึด [GAP_ANALYSIS_OD15_to_OD19.md](file:///c:/odoo-dev/odoo19/GAP_ANALYSIS_OD15_to_OD19.md)

---

## ภาพรวมชุด P1 ที่เหลือ

เรียงตาม **ความเสี่ยงจากน้อยไปมาก** (แนะนำให้ติดตั้งตามลำดับนี้ เพื่อสร้างชั้นความปลอดภัย/ย้อนกลับก่อนแตะโมดูลที่เสี่ยงสูง)

| # | โมดูล | หมวด | ความเสี่ยง | pip เพิ่ม | depends เพิ่ม | เหตุผลหลัก |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `base_cron_exclusion` | Performance | LOW | ไม่มี | `base` | แก้ปัญหา cron ทับซ้อน (workers=0) |
| 2 | `scheduler_error_mailer` | Monitoring | LOW | ไม่มี | `mail` | แจ้งเตือน cron ล้มเหลวทางอีเมล |
| 3 | `base_export_manager` | Security | LOW–MEDIUM | ไม่มี | `web` | คุมสิทธิ์/โปรไฟล์การ export |
| 4 | `session_db` | Infrastructure | MEDIUM | ไม่มี | (patch, ใช้ `base`) | เก็บ session ลง DB |
| 5 | `sentry` | Monitoring | MEDIUM–HIGH | `sentry_sdk>=2.0.0,<=2.22.0` | `base` | Error tracking + alerting |
| 6 | `auto_backup` | Prevention | MEDIUM–HIGH | `paramiko<4.0.0`, `pysftp`, `cryptography` | `mail` | สำรอง DB อัตโนมัติ |
| 7 | `bi_sql_editor` | Reporting | MEDIUM–HIGH | ไม่มี | `spreadsheet_dashboard`, `sql_request_abstract` | รายงาน SQL/materialized view |
| 8 | `database_cleanup` | Utilities (destructive) | HIGH | ไม่มี | `base` | ล้างขยะ DB/module/field |

**หมายเหตุความเข้ากันได้:** ทุกโมดูลเป็น manifest `19.0.x` (ยืนยันแล้ว) แต่ **ระดับรันไทม์ยังไม่พิสูจน์ → COMPATIBILITY NOT VERIFIED (runtime)** ทุกจุด

---

# 1) `base_cron_exclusion` — Base Cron Exclusion

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/base_cron_exclusion` |
| เวอร์ชัน | `19.0.1.0.0` |
| License | LGPL-3 |
| Dependencies | `base` เท่านั้น |
| pip เพิ่ม | ไม่มี |
| Development status | **Production/Stable** |
| หมวด | A — Performance & Optimization |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **LOW** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — ระบบรัน `workers = 0` (threaded) ซึ่งทำให้ cron ที่ทำงานพร้อมกันทับซ้อนกันได้ (บทเรียนเดิม: ความไม่เสถียรของ cron ทับซ้อน) โมดูลนี้ให้เลือกได้ว่า scheduled action ใด **ห้ามทำงานพร้อมกัน** เพื่อลด lock contention และการเขียนทับกันเอง — เป้าหมาย: cron ที่แข่งทรัพยากรกัน (เช่น autovacuum, sync, mail) ไม่รันซ้อน

**2. ข้อกำหนดเบื้องต้น** — submodule `server-tools` (พบแล้ว) · `addons_path` รวมพาธ (พบแล้ว) · ไม่มี pip เพิ่ม · มี backup ก่อนติดตั้ง

**3. องค์ประกอบที่จะเกิด** — ฟิลด์เพิ่มบน `ir.cron` (เลือก cron ที่ไม่ควรทำงานพร้อมกัน) + ไฟล์ view `views/ir_cron_view.xml` · **ไม่มีตาราง/โมเดลใหม่** · ไม่มีกลุ่มสิทธิ์ใหม่

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production (ตามนโยบาย 5 สภาพแวดล้อม)

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: บันทึก baseline ของ cron ที่ทำงานถี่/หนัก (รายชื่อ + เวลา)
- 5.2 Backup DB + filestore + ทดสอบกู้คืน
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i base_cron_exclusion --stop-after-init`
- 5.4 รีสตาร์ต + ตรวจ `odoo_server.log` ว่าไม่มี ERROR/WARNING ใหม่
- 5.5 ตั้งค่า: ผูก cron ที่แข่งทรัพยากรกันเข้าด้วยกัน

**6. การตั้งค่า** — เลือกคู่/กลุ่ม cron ที่ควร "exclude" กัน เช่น cron sync ภายนอกกับ cron สร้างรายงานหนัก, ให้ cron สำคัญไม่ถูกกันเวลาโดยไม่จำเป็น

**7. ผลกระทบประสิทธิภาพ** — positive: ลด overlap/lock · ข้อควรระวัง: ถ้าตั้ง exclusion ผิด อาจทำให้ cron บางตัว "รอ" นานขึ้น → ตรวจคิว/`nextcall`

**8. ความปลอดภัย** — ไม่มีผลต่อ ACL (ไม่มีโมเดลใหม่) · จำกัดเฉพาะผู้ดูแลระบบที่แก้ `ir.cron`

**9. เกณฑ์การยอมรับ**
1. cron ที่ผูก exclusion ไม่รันพร้อมกันจริง (ดู log/เวลา)
2. cron อื่นไม่ได้รับผลกระทบ
3. ไม่มี ERROR/WARNING ใหม่ใน log
4. จำนวนโมดูลหลังติดตั้ง +1, registry โหลดครบ

**10. Monitoring** — เฝ้า `nextcall` ของ cron ที่ผูก exclusion ว่าคิวไม่ยาวผิดปกติ · ตรวจ log ว่าไม่มี cron ค้าง

**11. Rollback** — ถอนผ่าน Apps ได้ (ไม่มีการทำลายข้อมูล) หรือเพียงเลิกตั้งค่า exclusion · DB/filestore ปลอดภัยจาก backup 5.2

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| ตั้ง exclusion ผิด → cron รอนาน | LOW | ทดสอบบน Integration, เริ่มจากคู่น้อย |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | LOW | ติดตั้งบน Local/Integration ก่อน |

**13. Task Checklist** — T1 baseline cron · T2 backup+restore · T3 ติดตั้ง Local · T4 รีสตาร์ต+ตรวจ log · T5 ตั้ง exclusion · T6 ทดสอบเกณฑ์ยอมรับ · T7 ย้ำ Integration→QA→UAT · T8 rollback plan · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — Deployment owner เก็บ log ติดตั้ง + รายการ cron ที่ตั้ง exclusion · Config owner ยืนยัน config ไม่เปลี่ยน

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i base_cron_exclusion --stop-after-init
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'base_cron_exclusion';
```

---

# 2) `scheduler_error_mailer` — Scheduler Error Mailer

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/scheduler_error_mailer` |
| เวอร์ชัน | `19.0.1.0.0` |
| License | AGPL-3 |
| Dependencies | `mail` |
| pip เพิ่ม | ไม่มี |
| Hook | มี `post_init_hook` |
| หมวด | B — Monitoring & Anomaly Detection |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **LOW** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — ปัจจุบัน cron ที่ล้มเหลวจะเงียบ (เหลือเพียง traceback ใน log) โมดูลนี้ผูกอีเมลเทมเพลตแจ้งเตือนเข้ากับ `ir.cron` ทุกตัว → ผู้ดูแลได้รับอีเมลเมื่อ scheduled action ล้มเหลว — เป้าหมาย: ไม่มี cron ล้มเหลวแบบเงียบ

**2. ข้อกำหนดเบื้องต้น** — `mail` ติดตั้งแล้ว (มีอยู่) · มี outgoing mail server ที่ใช้งานได้ · มีผู้รับอีเมลแจ้งเตือน · backup ก่อนติดตั้ง

**3. องค์ประกอบที่จะเกิด** — อีเมลเทมเพลต `scheduler_error_mailer.scheduler_error_mailer` (จาก `data/ir_cron_email_tpl.xml`) · view เพิ่มบน `ir.cron` (`views/ir_cron.xml`) · **`post_init_hook` จะเขียน `email_template_id` ให้ `ir.cron` ทุกตัว (รวมที่ inactive)** โดยอัตโนมัติ · ไม่มีตารางใหม่

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: ยืนยัน outgoing mail server ทำงาน (ส่งทดสอบ)
- 5.2 Backup DB + filestore
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i scheduler_error_mailer --stop-after-init`
- 5.4 รีสตาร์ต + ตรวจ log; ยืนยัน `post_init_hook` ตั้งเทมเพลตครบ
- 5.5 ตั้งค่า: เลือกผู้รับ/ทดสอบ trigger อีเมล (อาจใช้ cron ทดสอบที่ล้มเหลวโดยตั้งใจ)

**6. การตั้งค่า** — ตรวจว่าเทมเพลต `scheduler_error_mailer.scheduler_error_mailer` มีผู้รับถูกต้อง · พิจารณาแยกผู้รับต่อ cron ถ้าจำเป็น · ยืนยันว่าไม่เกิดอีเมลสแปมจาก cron ที่ล้มเหลวเป็นประจำ

**7. ผลกระทบประสิทธิภาพ** — ไม่มีนัยสำคัญ (ทำงานเฉพาะตอน error) · ระวัง: ถ้า cron ล้มเหลวถี่จะได้อีเมลจำนวนมาก → ตั้งผู้รับเป็นกลุ่ม/distribution list

**8. ความปลอดภัย** — อีเมลข้อผิดพลาดอาจมี traceback ข้อมูลธุรกิจ → จำกัดผู้รับภายในองค์กร · ไม่เพิ่มสิทธิ์ผู้ใช้ (ผู้ใช้ทั่วไปไม่เห็น `ir.cron`)

**9. เกณฑ์การยอมรับ**
1. cron ที่ล้มเหลว → ส่งอีเมลแจ้งเตือนจริง
2. เทมเพลตถูกผูกกับ `ir.cron` ทุกตัวหลังติดตั้ง
3. cron ที่ทำงานปกติ → ไม่มีอีเมล
4. ไม่มี ERROR/WARNING ใหม่ใน log

**10. Monitoring** — ตรวจว่ามีอีเมลแจ้งเตือนเข้ามาจริงในกล่องผู้ดูแล · เฝ้า cron ที่ล้มเหลวซ้ำ (อาจเป็นสัญญาณปัญหาจริง)

**11. Rollback** — ถอนผ่าน Apps ได้ (ไม่มีข้อมูลถูกทำลาย) · เทมเพลต/ฟิลด์ถูกถอดออก · DB ปลอดภัยจาก backup

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| อีเมลล้นจาก cron ที่ล้มเหลวถี่ | LOW | ตั้งผู้รับเป็นกลุ่ม + แก้ cron ต้นเหตุ |
| Traceback ถูกส่งออกนอก (ถ้าผู้รับภายนอก) | LOW | ใช้ผู้รับภายในเท่านั้น |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | LOW | ติดตั้ง Local/Integration ก่อน |

**13. Task Checklist** — T1 ยืนยัน mail server · T2 backup · T3 ติดตั้ง Local · T4 รีสตาร์ต+ตรวจ hook · T5 ตั้งผู้รับ+ทดสอบ · T6 ทดสอบเกณฑ์ยอมรับ · T7 ย้ำ Integration→QA→UAT · T8 rollback plan · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — เก็บภาพหน้าจอเทมเพลต + ตัวอย่างอีเมลแจ้งเตือนจริง + log ติดตั้ง

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i scheduler_error_mailer --stop-after-init
```
```sql
SELECT c.id, c.name, c.email_template_id FROM ir_cron c WHERE c.email_template_id IS NULL;
```

---

# 3) `base_export_manager` — Manage model export profiles

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-ux` → `third_party/oca/server-ux/base_export_manager` |
| เวอร์ชัน | `19.0.1.0.0` |
| License | AGPL-3 |
| Dependencies | `web` |
| pip เพิ่ม | ไม่มี |
| Hook | มี `post_init_hook` (inverse `ir.exports.line.name`) |
| Assets | ESM: `base_export_manager/static/src/views/list/list_controller.esm.js` |
| หมวด | G — Access Rights & Security |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **LOW–MEDIUM** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — Odoo core ให้ทุกคน export ข้อมูลได้กว้าง (ความเสี่ยง data exfiltration / mass export) โมดูลนี้เพิ่ม **โปรไฟล์การ export** ต่อโมเดล และ **จำกัดฟิลด์ที่แต่ละกลุ่มผู้ใช้ส่งออกได้** — เป้าหมาย: คุมการส่งออกข้อมูลอ่อนไหว (ลูกค้า, ราคา, การเงิน)

**2. ข้อกำหนดเบื้องต้น** — `web` (core) · มี backup · ต้องเข้าใจว่ามี `ir.exports` อยู่เดิม (โมดูลจะ inverse ค่า `name` เดิมใน `ir.exports.line`)

**3. องค์ประกอบที่จะเกิด** — โมเดล `ir.exports` (โปรไฟล์) + `ir.exports.line` (ฟิลด์) ถูกขยาย · view เพิ่มบน `ir.exports`, `ir.model`, `ir.model.access`, `res.groups` · asset ESM ใน backend · `post_init_hook` ปรับข้อมูลเก่าให้สอดคล้อง

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: ตรวจว่ามี `ir.exports` เดิม/ผู้ใช้ที่ถูกจำกัดการ export
- 5.2 Backup DB + filestore
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i base_export_manager --stop-after-init`
- 5.4 รีสตาร์ต + ตรวจ log; ยืนยัน `post_init_hook` ทำงานไม่มี error
- 5.5 ตั้งค่า: สร้างโปรไฟล์ export ต่อโมเดล + ผูกกับกลุ่มผู้ใช้

**6. การตั้งค่า** — กำหนดว่าโมเดลใด "บังคับใช้โปรไฟล์" (ผู้ใช้เลือกฟิลด์เองไม่ได้) และจำกัดฟิลด์อ่อนไหว (เช่น `credit_limit`, ต้นทุน) ไม่ให้กลุ่มทั่วไปส่งออก

**7. ผลกระทบประสิทธิภาพ** — ไม่มีนัยสำคัญ (จำกัดอยู่ที่หน้าจอ export) · asset ESM โหลดที่ backend list view เท่านั้น

**8. ความปลอดภัย** — เป็น **มาตรการป้องกัน**โดยตรง: ลดความเสี่ยง mass export · ต้องทดสอบว่าผู้ใช้ที่ไม่มีสิทธิ์ไม่สามารถ export ฟิลด์ต้องห้ามได้จริง (ทั้ง UI และ RPC) · ยืนยันว่าไม่ปิดกั้นการ export ที่ชอบด้วยกฎหมายของบัญชี/ผู้ตรวจสอบ

**9. เกณฑ์การยอมรับ**
1. ผู้ใช้กลุ่มที่ถูกจำกัด → เลือกฟิลด์ต้องห้ามในหน้า export ไม่ได้
2. การ export ผ่าน UI ใช้โปรไฟล์ที่กำหนด
3. ผู้ใช้ที่ได้รับอนุญาต export ได้ตามปกติ
4. `post_init_hook` ไม่ทำให้ข้อมูล `ir.exports.line` เดิมเสียหาย
5. ไม่มี ERROR/WARNING ใหม่ใน log

**10. Monitoring** — ตรวจ log การ export ที่ถูกปฏิเสธ (ถ้ามี) · ทบทวนโปรไฟล์เมื่อมีโมเดล/ฟิลด์ใหม่

**11. Rollback** — ถอนผ่าน Apps ได้ (โปรไฟล์/ฟิลด์ถูกถอด) · **ควร export รายการโปรไฟล์ไว้ก่อนถอน** · DB ปลอดภัยจาก backup

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| จำกัดเข้มเกิน → ขวางงานบัญชี/ตรวจสอบ | MEDIUM | ทดสอบกับกลุ่มจริงใน UAT |
| ผู้ใช้ bypass ผ่าน RPC/import | MEDIUM | ทดสอบ RPC + ใช้ร่วมกับ record rules |
| `post_init_hook` ผิดพลาดกับข้อมูลเก่า | LOW | backup + ทดสอบบน Integration |
| รันไทม์กับ 19.0 (asset ESM) ยังไม่พิสูจน์ | MEDIUM | ตรวจหน้า list/export บน Local |

**13. Task Checklist** — T1 สำรวจ `ir.exports` เดิม · T2 backup · T3 ติดตั้ง Local · T4 รีสตาร์ต+ตรวจ hook/asset · T5 สร้างโปรไฟล์+ผูกกลุ่ม · T6 ทดสอบ UI+RPC · T7 ย้ำ Integration→QA→UAT · T8 rollback+export โปรไฟล์ · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — Security reviewer ยืนยันผลทดสอบการจำกัดฟิลด์ · เก็บภาพหน้าจอโปรไฟล์ + ผลทดสอบ RPC

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i base_export_manager --stop-after-init
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'base_export_manager';
```

---

# 4) `session_db` — Store sessions in DB

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/session_db` |
| เวอร์ชัน | `19.0.1.0.0` |
| License | LGPL-3 |
| Dependencies | (manifest **ไม่มีคีย์ `depends`** → ค่าเริ่มต้นเป็น `base`) |
| pip เพิ่ม | ไม่มี |
| ลักษณะพิเศษ | **Monkey patch** `http.root.session_store` → `PGSessionStore` (ทำงานตอน import) |
| หมวด | A/D — Infrastructure |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **MEDIUM** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — ปกติ Odoo เก็บ session เป็นไฟล์บนดิสก์ (filestore/sessions) ซึ่งมีปัญหากับ multi-process/การรีสตาร์ต/การย้ายเครื่อง โมดูลนี้ย้าย session ไปเก็บใน **ฐานข้อมูล PostgreSQL** — เป้าหมาย: session คงอยู่ข้ามรีสตาร์ต worker และจัดการรวมศูนย์ได้

**2. ข้อกำหนดเบื้องต้น** — Zip: submodule `server-tools` (พบแล้ว) · **ต้องเข้าใจว่าโมดูลนี้เป็น server-level patch** → โดยทั่วไปต้องให้โหลดผ่าน `server_wide_modules` (เช่น `web,session_db` หรือรวมกับ `sentry`) มิฉะนั้น patch อาจไม่ถูกนำไปใช้ · backup ก่อนติดตั้ง

**3. องค์ประกอบที่จะเกิด** — ไม่มีโมเดล/ตาราง Odoo ที่มองเห็น (อาจมีตาราง session ระดับ DB ที่ patch จัดการ) · ไม่มีกลุ่มสิทธิ์ใหม่ · **ไม่มี `data/security/view`** · มีชุดทดสอบ `tests/test_pg_session_store.py`

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production *(ต้องระวังเป็นพิเศษ: กระทบการล็อกอินทั้งระบบ)*

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: บันทึกค่า `server_wide_modules` ปัจจุบัน และทดสอบว่าการล็อกอินเดิมทำงาน
- 5.2 Backup DB + filestore (สำคัญ: มี session เก่าอยู่ใน filestore)
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i session_db --stop-after-init`
- 5.4 เพิ่ม `session_db` เข้า `server_wide_modules` ใน `odoo.conf` (PROPOSED) แล้วรีสตาร์ต
- 5.5 ตรวจว่า: ล็อกอินใหม่ได้, session ใหม่ถูกเก็บใน DB, ไม่มี ERROR/WARNING ใหม่

**6. การตั้งค่า** — `server_wide_modules = web,session_db` (หรือรวมกับ `sentry` ถ้าติดตั้งแล้ว) · ยืนยัน `dbfilter = ^odoo19$` ยังถูกต้อง

**7. ผลกระทบประสิทธิภาพ** — session อ่าน/เขียนผ่าน DB → เพิ่ม query เล็กน้อยต่อ request · โดยทั่วไปดีขึ้นเมื่อมีหลาย worker · ต้องวัดบน Integration

**8. ความปลอดภัย** — session ใน DB ต้องเข้าถึงได้เฉพาะ role Odoo · ตรวจว่า session ที่ค้าง/หมดอายุถูกล้าง · **ความเสี่ยงสูงสุดคือกระทบการล็อกอินทั้งระบบ** → ต้องมี rollback ทันที (เอา `session_db` ออกจาก `server_wide_modules` แล้วรีสตาร์ต)

**9. เกณฑ์การยอมรับ**
1. ผู้ใช้ล็อกอิน/ออกได้ตามปกติ
2. session ถูกเก็บใน DB (ยืนยันได้) และคงอยู่ข้ามรีสตาร์ต worker
3. ไม่มี ERROR/WARNING ใหม่ใน log
4. session เก่าที่ค้างใน filestore ไม่ทำให้เกิดข้อผิดพลาด
5. `server_wide_modules` โหลดโมดูลสำเร็จ

**10. Monitoring** — เฝ้า log การล็อกอิน/สิทธิ์หลังติดตั้ง · ตรวจขนาดตาราง session และการล้าง session หมดอายุ

**11. Rollback** — **(เร็ว)** เอา `session_db` ออกจาก `server_wide_modules` → รีสตาร์ต → ระบบกลับไปใช้ session บนดิสก์ · ถอนโมดูลผ่าน Apps · กู้จาก backup ถ้าจำเป็น

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| กระทบการล็อกอินทั้งระบบ | MEDIUM–HIGH | ทดสอบ Local/Integration ก่อน, มี rollback ทันที |
| patch ไม่ทำงาน (ไม่อยู่ใน server_wide_modules) | MEDIUM | ยืนยันค่า config + ตรวจ log ว่ามี "Monkey patching session store" |
| ไม่มี `depends` ทำ install พฤติกรรมต่างจากคาด | MEDIUM | ยืนยันด้วยการทดสอบบน Integration |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ติดตั้ง Local/Integration ก่อน |

**13. Task Checklist** — T1 บันทึก `server_wide_modules` + ทดสอบ login baseline · T2 backup · T3 ติดตั้ง Local · T4 เพิ่ม server_wide_modules + รีสตาร์ต · T5 ตรวจ session ใน DB + login · T6 ทดสอบเกณฑ์ยอมรับ · T7 ย้ำ Integration→QA→UAT · T8 เตรียม rollback ทันที · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — Deployment owner เก็บ log รีสตาร์ต + หลักฐาน session ใน DB · Incident first responder เฝ้าระหว่างติดตั้ง Production

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i session_db --stop-after-init
```
```
; odoo.conf (PROPOSED)
server_wide_modules = web,session_db
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'session_db';
```

---

# 5) `sentry` — Sentry (Error Tracking)

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/sentry` |
| เวอร์ชัน | `19.0.1.0.1` |
| License | AGPL-3 |
| Dependencies | `base` |
| pip เพิ่ม | **`sentry_sdk>=2.0.0,<=2.22.0`** (บังคับ) |
| Hook | **`post_load`** (โหลดตอน bootstrap เซิร์ฟเวอร์) |
| หมวด | B — Monitoring & Anomaly Detection |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **MEDIUM–HIGH** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — ปัจจุบันข้อผิดพลาดระดับรันไทม์ (exception, traceback) อยู่แต่ใน `odoo_server.log` ไม่มีการแจ้งเตือน/รวบรวม โมดูลนี้เชื่อม Odoo เข้ากับ Sentry (หรือ self-hosted) เพื่อรวบรวม error และแจ้งเตือนเชิงรุก — เป้าหมาย: ตรวจจับความผิดปกติ/ข้อผิดพลาดก่อนผู้ใช้ร้องเรียน

**2. ข้อกำหนดเบื้องต้น**
- submodule `server-tools` (พบแล้ว)
- **ติดตั้ง pip ก่อน:** `pip install "sentry_sdk>=2.0.0,<=2.22.0"` (ไม่งั้น `post_load` จะ no-op เพราะ `HAS_SENTRY_SDK = False`)
- มี Sentry DSN (หรือ self-hosted) — ตามบันทึกเดิม **ยังรอ DSN**
- ตัดสินใจเรื่อง PDPA/PII: ต้องกรองข้อมูลส่วนบุคคลก่อนส่งออกนอกเครื่อง (ดูข้อ 8)

**3. องค์ประกอบที่จะเกิด** — ไม่มีตาราง/โมเดล Odoo · **patch WSGI** (`odoo.http.Application.__call__` ถูกห่อด้วย `SentryWsgiMiddleware`) · `ThreadingIntegration` · logging integration · ส่งข้อความ "Starting Odoo Server" ตอนบูต (ถ้า `sentry_startup_message` ไม่ใช่ False) · **ต้องเพิ่ม `sentry` เข้า `server_wide_modules`**

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production *(เริ่มจาก environment/DSN แยกต่อสภาพแวดล้อม)*

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: ติดตั้ง `sentry_sdk` ใน venv ของทุก environment · เตรียม DSN
- 5.2 Backup DB + filestore
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i sentry --stop-after-init`
- 5.4 เพิ่ม `sentry` เข้า `server_wide_modules` + เพิ่มส่วน `[sentry]` ในไฟล์ config (PROPOSED) → รีสตาร์ต
- 5.5 ทดสอบ: สร้างข้อผิดพลาดทดสอบ (route/script) → ยืนยันว่ามี event ใน Sentry

**6. การตั้งค่า (PROPOSED)**
```
[options]
server_wide_modules = web,sentry          ; (ถ้าใช้ session_db ให้รวมด้วย)

[sentry]
sentry_dsn = https://<public_key>:<secret_key>@sentry.example.com/<project id>
sentry_enabled = true
sentry_logging_level = warn
sentry_exclude_loggers = werkzeug
sentry_ignore_exceptions = odoo.exceptions.AccessDenied,odoo.exceptions.AccessError,odoo.exceptions.MissingError,odoo.exceptions.RedirectWarning,odoo.exceptions.UserError,odoo.exceptions.ValidationError,odoo.exceptions.Warning,odoo.exceptions.except_orm
sentry_include_context = true
sentry_environment = production
sentry_release = <version>
sentry_startup_message = true
```
> ซอร์สจริงอ่านส่วน `[sentry]` จาก config (ผ่าน `server_environment` ถ้ามี หรือจากไฟล์ config ที่ระบุ) — ต้องยืนยันพาธ/วิธีโหลดบน Windows ก่อนใช้ 실제
> ตัวเลือกอื่น ๆ ตั้งได้โดยเติม prefix `sentry_` (เช่น `send_default_pii`, `traces_sample_rate`, `sample_rate`)

**7. ผลกระทบประสิทธิภาพ** — overhead เล็กน้อยต่อ request (WSGI middleware) · ระวัง `traces_sample_rate` สูงจะเพิ่มภาระ · แนะนำเริ่มที่ logging level `warn`

**8. ความปลอดภัย (สำคัญที่สุดของโมดูลนี้)**
- **PII/PDPA:** ตั้ง `send_default_pii = false` และพิจารณา `sentry_exclude_loggers` เพื่อไม่ส่งข้อมูลส่วนบุคคล/ธุรกิจออกนอกเครื่อง
- ตรวจ `processor.py` ที่จัดการ `sentry_dsn` ว่ามีการ mask ข้อมูลอ่อนไหว
- จำกัดผู้ที่เข้าถึง Sentry project (เห็น stack trace + context)
- DSN เป็น credential → เก็บในไฟล์ config ที่มีสิทธิ์จำกัด (ห้าม commit; ห้ามใส่ใน command line)
- ใช้ self-hosted Sentry หากข้อกำหนดข้อมูลเข้มงวด

**9. เกณฑ์การยอมรับ**
1. เกิดข้อผิดพลาดทดสอบ → มี event ใน Sentry พร้อม release/environment
2. ไม่มี PII รั่วไหลใน event (ตรวจ payload)
3. ข้อผิดพลาดที่ระบุใน `sentry_ignore_exceptions` → ไม่ถูกส่ง
4. ไม่มี ERROR/WARNING ใหม่ใน log (ยกเว้นข้อความ Sentry ที่คาดไว้)
5. `server_wide_modules` โหลด `sentry` สำเร็จ (ยืนยันว่ามี log/message "Starting Odoo Server")

**10. Monitoring** — ทบทวน Sentry issue เป็นประจำ · ตั้ง alert rule (เช่น error rate) · ตรวจว่า DSN/โควต้าไม่หมด

**11. Rollback** — เอา `sentry` ออกจาก `server_wide_modules` + รีสตาร์ต (หยุดส่งข้อมูลทันที) · ถอนโมดูลผ่าน Apps · **คำเตือน:** ไม่มีข้อมูล Odoo ถูกทำลาย แต่ event ที่ส่งไปแล้วอยู่ที่ Sentry

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| ข้อมูลอ่อนไหว/PII รั่วออกนอกเครื่อง | **HIGH** | `send_default_pii=false` + กรอง logger + self-hosted |
| ขาด pip `sentry_sdk` → โมดูลเงียบไม่ทำงาน | MEDIUM | ติดตั้ง pip ก่อน + ตรวจ log |
| patch WSGI ขัดกับ `proxy_mode`/Nginx | MEDIUM | ทดสอบหลัง Nginx บน Integration |
| โควต้า Sentry/ค่าใช้จ่าย | LOW | ตั้ง sample rate + alert |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ติดตั้ง Local/Integration ก่อน |

**13. Task Checklist** — T1 ติดตั้ง pip `sentry_sdk` ทุก env · T2 backup · T3 ติดตั้ง Local · T4 เพิ่ม server_wide_modules + `[sentry]` + รีสตาร์ต · T5 ทดสอบ event + ตรวจ PII · T6 ทดสอบหลัง Nginx (proxy_mode) · T7 ย้ำ Integration→QA→UAT · T8 rollback plan · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — Security reviewer ยืนยันการกรอง PII · เก็บภาพ event ใน Sentry + payload ที่ตรวจแล้ว

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
pip install "sentry_sdk>=2.0.0,<=2.22.0"
python odoo-bin -c odoo.conf -d odoo19 -i sentry --stop-after-init
```
> ห้ามใส่ DSN/รหัสผ่านใน command line — เก็บในไฟล์ config ที่มีสิทธิ์จำกัดเท่านั้น

---

# 6) `auto_backup` — Database Auto-Backup

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/auto_backup` |
| เวอร์ชัน | `19.0.1.0.1` |
| License | AGPL-3 |
| Dependencies | `mail` |
| pip เพิ่ม | **`paramiko<4.0.0`, `pysftp`, `cryptography`** (สำหรับ SFTP) |
| โมเดล | `db.backup` (`name`, `folder`, `days_to_keep`, `method`, `sftp_*`, `backup_format`) |
| Constraint | `days_to_keep >= 0` |
| หมวด | D — Prevention & Protection |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **MEDIUM–HIGH** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — สำรองฐานข้อมูลอัตโนมัติตามรอบ (นโยบายเดิม: **ทุก 1 เดือน, เก็บ 365 วัน, โฟลเดอร์ `C:\odoo-dev\odoo19\backups`**) — เป้าหมาย: มีสำเนาสำรองที่กู้คืนได้สม่ำเสมอ ลดความเสี่ยงข้อมูลสูญหาย

**2. ข้อกำหนดเบื้องต้น**
- submodule `server-tools` · `mail` ติดตั้งแล้ว
- **ติดตั้ง pip:** `paramiko<4.0.0`, `pysftp`, `cryptography` (จำเป็นถ้าใช้ SFTP; ถ้าใช้ local เท่านั้นอาจยังถูกบังคับตรวจตอนติดตั้ง)
- มีพื้นที่ดิสก์เพียงพอ และโฟลเดอร์ backup มีสิทธิ์เขียน
- **⚠️ ความขัดแย้งที่ทราบแล้ว (จากบันทึกเดิม):** ใน Odoo 19 การตั้ง `list_db = False` (hardening) จะทำให้ `dump_db` ถูกบล็อก → `auto_backup` ทำงานล้มเหลว → **ต้องตัดสินใจเลือกระหว่าง hardening (`list_db=False`) กับ backup ในระบบ** หรือใช้ backup ภายนอกระบบแทน

**3. องค์ประกอบที่จะเกิด** — โมเดล `db.backup` (ตั้งค่าโฟลเดอร์/รอบ/retention/local-SFTP) · scheduled action (จาก `data/ir_cron.xml`) · mail subtype (`data/mail_message_subtype.xml`) สำหรับแจ้งผล · view + security csv · **ไม่มีกลุ่มสิทธิ์พิเศษใหม่**

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production *(ทดสอบ restore จริงทุกขั้น)*

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: **ตัดสินใจเรื่อง `list_db`** ให้ชัด + ตรวจพื้นที่ดิสก์ + ยืนยันโฟลเดอร์ backup
- 5.2 Backup DB + filestore (**แบบ manual นอกโมดูลนี้**)
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i auto_backup --stop-after-init`
- 5.4 รีสตาร์ต + ตรวจ log
- 5.5 ตั้งค่า: สร้างเรกคอร์ด `db.backup` (folder = `C:\odoo-dev\odoo19\backups`, รอบ = รายเดือน, `days_to_keep = 365`) + เปิด cron + **ทดสอบกู้คืนจากไฟล์ที่สร้าง**

**6. การตั้งค่า** — `method = local` (แนะนำเริ่มต้น) หรือ `sftp` (ต้องมี `sftp_host/port/user/password หรือ private_key`) · `backup_format` (zip/dump) · ตั้งผู้รับอีเมลแจ้งผล · ยืนยันว่า cron ทำงานตามรอบ

**7. ผลกระทบประสิทธิภาพ** — การ dump DB เป็นภาระหนักชั่วคราว → ตั้งรอบในเวลาที่ระบบว่าง · ตรวจพื้นที่ดิสก์ต่อเนื่อง (retention 365 วัน + ขนาด DB)

**8. ความปลอดภัย**
- ไฟล์ backup มีข้อมูลทั้งระบบ → **ต้องเข้ารหัส/จำกัดสิทธิ์โฟลเดอร์** และห้ามวางในที่ web เข้าถึงได้
- SFTP credential เก็บเป็นความลับ (ห้าม commit)
- **ความขัดแย้ง hardening:** ถ้าปิด `list_db=False` โมดูลจะล้มเหลว → ต้องเลือกกลยุทธ์ (ดูข้อ 2)
- พิจารณาสำรองออกนอกเครื่อง (off-site/SFTP) ตามหลัก 3-2-1

**9. เกณฑ์การยอมรับ**
1. cron สร้างไฟล์ backup ในโฟลเดอร์ที่กำหนดตามรอบ
2. **กู้คืนสำเร็จ** บนฐานข้อมูลทดสอบจากไฟล์ที่สร้างจริง
3. retention: ไฟล์เก่ากว่า `days_to_keep` ถูกลบ
4. มีอีเมลแจ้งผล (สำเร็จ/ล้มเหลว)
5. ไม่มี ERROR/WARNING ใหม่ใน log
6. ยืนยันพฤติกรรมเมื่อ `list_db` ตามที่นโยบายกำหนด

**10. Monitoring** — ตรวจไฟล์ล่าสุดมีอยู่และขนาดสมเหตุผล · ตรวจว่ามีอีเมลแจ้งผลทุกครั้ง · เฝ้าพื้นที่ดิสก์

**11. Rollback** — ถอนผ่าน Apps ได้ (ไม่ทำลายข้อมูล) · **ไฟล์ backup ที่สร้างแล้วยังอยู่** · ถ้าไม่ต้องใช้แล้วควรเก็บไฟล์ล่าสุดไว้ก่อนถอน

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| **`list_db=False` ทำให้ backup ล้มเหลว** | **HIGH** | ตัดสินใจนโยบายให้ชัด / ใช้ backup ภายนอก |
| ไฟล์ backup รั่ว/ไม่เข้ารหัส | HIGH | จำกัดสิทธิ์โฟลเดอร์ + off-site + encryption |
| พื้นที่ดิสก์เต็ม | MEDIUM | retention + ตรวจรายเดือน + off-site |
| กู้คืนไม่ได้จริง (ไม่เคยทดสอบ) | HIGH | ทดสอบ restore ทุกขั้น (เกณฑ์ข้อ 9.2) |
| SFTP/credential ผิดพลาด | MEDIUM | ทดสอบ connection ก่อนเปิด cron |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ติดตั้ง Local/Integration ก่อน |

**13. Task Checklist** — T1 ตัดสินใจนโยบาย `list_db` + ตรวจดิสก์ · T2 backup manual + ทดสอบ restore · T3 ติดตั้ง pip + โมดูล Local · T4 รีสตาร์ต+ตรวจ log · T5 สร้าง `db.backup` + เปิด cron · T6 ทดสอบ backup + **restore จริง** · T7 ย้ำ Integration→QA→UAT · T8 rollback plan · T9 go/no-go

**14. การอนุมัติ/หลักฐาน** — Backup owner ยืนยัน restore สำเร็จ · เก็บรายการไฟล์ backup + log restore + ภาพการตั้งค่า `db.backup`

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
pip install "paramiko<4.0.0" pysftp cryptography
python odoo-bin -c odoo.conf -d odoo19 -i auto_backup --stop-after-init
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'auto_backup';
SELECT id, name, folder, method, days_to_keep FROM db_backup;
```
> ห้ามใส่รหัสผ่านฐานข้อมูลใน command line ให้ใช้ `.pgpass` หรือ interactive prompt เท่านั้น

---

# 7) `bi_sql_editor` — BI SQL Editor

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/reporting-engine` → `third_party/oca/reporting-engine/bi_sql_editor` |
| เวอร์ชัน | `19.0.2.0.1` |
| License | AGPL-3 |
| Dependencies | **`spreadsheet_dashboard`** (core — พบใน `addons/`) + **`sql_request_abstract`** (OCA reporting-engine — พบแล้ว) |
| pip เพิ่ม | ไม่มี |
| Hook | มี **`uninstall_hook`** (ตั้ง `bi.sql.view` ทั้งหมดกลับเป็น draft) |
| หมวด | F — Data Processing & Reporting |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **MEDIUM–HIGH** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — ให้สร้าง **BI view จาก SQL** (normal หรือ materialized view) และทำรายงาน/แดชบอร์ดจากข้อมูล (ใช้ร่วมกับ `spreadsheet_dashboard`) — เป้าหมาย: รายงานวิเคราะห์ที่ยืดหยุ่นโดยไม่ต้องเขียนโมดูลใหม่ (คู่กับ `auditlog` เพื่อช่วยตรวจสอบ) — **เป็นทางเลือกแทน/หรือทดแทน `kpi` (ต้องเลือกอย่างเดียว — ดูข้อ 6 ของรายงานประเมิน)**

**2. ข้อกำหนดเบื้องต้น**
- submodule `reporting-engine` (พบแล้ว) · ยืนยันว่า `spreadsheet_dashboard` มีใน CE 19.0 (**พบแล้ว** ที่ `addons/spreadsheet_dashboard`)
- จะติดตั้ง `sql_request_abstract` เป็น dependency อัตโนมัติ (OCA) — ต้องยอมรับ
- **ต้องมี DB role แบบ read-only** สำหรับ SQL ที่รันจากผู้ใช้ (ลดความเสี่ยง) — ดูข้อ 8
- backup ก่อนติดตั้ง

**3. องค์ประกอบที่จะเกิด** — โมเดล `bi.sql.view` (และที่เกี่ยวข้องกับ `sql.request.abstract`) · security csv · view `views/view_bi_sql_view.xml` · demo (ไม่โหลดใน production) · **`uninstall_hook` จะตั้ง view ทั้งหมดเป็น draft ก่อนถอน**

**4. ลำดับสภาพแวดล้อม** — Local Dev → Shared Dev → Test/QA → UAT → Production

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: ยืนยัน `spreadsheet_dashboard`/`sql_request_abstract` พร้อม · ทบทวนนโยบาย SQL + สิทธิ์
- 5.2 Backup DB + filestore
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i bi_sql_editor --stop-after-init` (จะติดตั้ง dependency ให้)
- 5.4 รีสตาร์ต + ตรวจ log
- 5.5 ตั้งค่า: สร้าง BI view ตัวอย่าง (normal view) → ทดสอบสร้าง materialized view + refresh + แสดงในแดชบอร์ด

**6. การตั้งค่า** — จำกัดผู้สร้าง BI view (กลุ่มเฉพาะ) · เลือก normal view สำหรับข้อมูลสด / materialized view สำหรับข้อมูลหนัก + ตั้งรอบ refresh · **ต้องเลือกอย่างเดียวระหว่าง `bi_sql_editor` กับโมดูล `kpi` เดิม** เพื่อเลี่ยงความซ้ำซ้อน

**7. ผลกระทบประสิทธิภาพ** — materialized view กินพื้นที่และต้อง refresh (ภาระตอน refresh) · query ที่เขียนไม่ดีจะหนัก DB → ต้อง review SQL · ใช้ read-only role เพื่อจำกัด

**8. ความปลอดภัย (สำคัญมาก)**
- โมดูลรัน **SQL ตามที่ผู้ใช้กำหนด** → ความเสี่ยงสูงสุดคือ SQL injection/แก้ข้อมูล
- จำกัดสิทธิ์สร้าง/แก้ BI view เฉพาะผู้ดูแล/นักวิเคราะห์ที่เชื่อถือได้
- **แนะนำใช้ DB role ที่อ่านได้อย่างเดียว** สำหรับ connection ที่รัน query (ถ้าสถาปัตยกรรมรองรับ)
- ทบทวน query ที่สร้างว่าไม่ดึงข้อมูลอ่อนไหวเกินจำเป็น และสอดคล้อง PDPA
- ตรวจว่าไม่มี record rule ของโมดูลกำหนดเองที่ขัดกับการเข้าถึง BI view

**9. เกณฑ์การยอมรับ**
1. สร้าง BI view (normal) สำเร็จและแสดงข้อมูลถูกต้อง
2. สร้าง materialized view + refresh สำเร็จ
3. แสดงผลในแดชบอร์ด/spreadsheet ได้
4. ผู้ใช้ที่ไม่มีสิทธิ์สร้าง/แก้ BI view → ถูกปฏิเสธ
5. `uninstall_hook` ทำงาน (ทดสอบตั้ง view เป็น draft) — **ทดสอบบน Integration เท่านั้น**
6. ไม่มี ERROR/WARNING ใหม่ใน log

**10. Monitoring** — ตรวจภาระ DB ตอน refresh · เฝ้าขนาด materialized view · ทบทวน SQL ที่มีอยู่เป็นระยะ

**11. Rollback** — ถอนผ่าน Apps (เรียก `uninstall_hook` ตั้ง view เป็น draft) · **ควรบันทึก SQL ของ BI view ไว้ก่อนถอน** (จะหายไปกับโมดูล) · DB ปลอดภัยจาก backup

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| SQL ที่ผู้ใช้เขียนแก้/ลบข้อมูลได้ | **HIGH** | read-only role + จำกัดกลุ่ม + review |
| materialized view หนัก DB/พื้นที่ | MEDIUM | เลือก normal view + ตั้งรอบ refresh |
| ซ้ำซ้อนกับโมดูล `kpi` เดิม | MEDIUM | เลือกใช้เพียงตัวเดียว |
| dependency `sql_request_abstract` เพิ่มความซับซ้อน | LOW | ยอมรับ + ทดสอบบน Integration |
| `uninstall_hook` ลบ view ที่ใช้งานอยู่ | MEDIUM | ทดสอบบน Integration, สำรอง SQL |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ติดตั้ง Local/Integration ก่อน |

**13. Task Checklist** — T1 ยืนยัน dependency + นโยบาย read-only · T2 backup · T3 ติดตั้ง Local (+deps) · T4 รีสตาร์ต+ตรวจ log · T5 สร้าง/ทดสอบ BI view + แดชบอร์ด · T6 ทดสอบสิทธิ์ + `uninstall_hook` บน Integration · T7 ตัดสินใจเรื่อง `kpi` (เลือกอย่างเดียว) · T8 ย้ำ Integration→QA→UAT · T9 rollback + สำรอง SQL · T10 go/no-go

**14. การอนุมัติ/หลักฐาน** — Security reviewer ยืนยันการจำกัดสิทธิ์ SQL · เก็บภาพ BI view + ผล refresh + สำเนา SQL

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i bi_sql_editor --stop-after-init
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name IN ('bi_sql_editor','sql_request_abstract');
```

---

# 8) `database_cleanup` — Database cleanup

| หัวข้อ | ค่า |
| --- | --- |
| Repository | `OCA/server-tools` → `third_party/oca/server-tools/database_cleanup` |
| เวอร์ชัน | `19.0.1.0.6` |
| License | AGPL-3 |
| Dependencies | `base` |
| pip เพิ่ม | ไม่มี |
| Wizards | purge: menus, modules, models, fields, columns, tables, data + create_indexes |
| หมวด | E — Utilities (Destructive) |
| ลำดับความสำคัญ | **P1** |
| ความเสี่ยง | **HIGH** |
| สถานะความเข้ากันได้ | Manifest ตรง 19.0 · รันไทม์ **COMPATIBILITY NOT VERIFIED (runtime)** |

**1. เหตุผลและเป้าหมาย** — เมื่อติดตั้ง/ถอนโมดูลหลายรอบ จะเหลือขยะใน DB (ตาราง/คอลัมน์/ฟิลด์/โมเดล/เมนู/ข้อมูล) โมดูลนี้ให้เครื่องมือ purge และสร้าง index เพื่อดูแลสุขภาพ DB — เป้าหมาย: DB สะอาดขึ้น (ใช้ **หลัง** การเปลี่ยนแปลงโมดูลครั้งใหญ่เท่านั้น)

**2. ข้อกำหนดเบื้องต้น**
- submodule `server-tools` (พบแล้ว) · backup ก่อนติดตั้ง
- **⚠️ เป็นโมดูลทำลายข้อมูล (destructive)** — purge สามารถลบตาราง/คอลัมน์/ข้อมูลได้ → **ห้ามรันบน Production โดยไม่มี backup ที่ทดสอบ restore และการอนุมัติชัดเจน**
- เข้าใจความหมายของแต่ละ wizard (dry-run ถ้ามี)

**3. องค์ประกอบที่จะเกิด** — wizard หลายตัว (`purge.wizard` + line ต่าง ๆ: menus/modules/models/fields/columns/tables/data) · `create.indexes` wizard · menu + security csv · **ไม่มีตารางธุรกิจใหม่** แต่ **มีอำนาจลบโครงสร้าง DB**

**4. ลำดับสภาพแวดล้อม** — Local Dev (ทดลอง+ทำความเข้าใจ) → Shared Dev → Test/QA → UAT → **Production (เฉพาะเมื่ออนุมัติ + backup พร้อม)**

**5. ขั้นตอนติดตั้ง (PROPOSED)**
- 5.1 Pre-flight: **แจ้งเตือนความเสี่ยงสูง** + เตรียม backup ที่ทดสอบ restore
- 5.2 Backup DB + filestore (บังคับ)
- 5.3 ติดตั้ง: `python odoo-bin -c odoo.conf -d odoo19 -i database_cleanup --stop-after-init`
- 5.4 รีสตาร์ต + ตรวจ log
- 5.5 ใช้งาน: เปิด purge wizard → **ทบทวนรายการที่ระบบเสนอ (dry-run) ก่อนกดยืนยันทุกครั้ง**

**6. การตั้งค่า** — จำกัดสิทธิ์เข้าถึง wizard เฉพาะผู้ดูแลระบบเท่านั้น · ใช้ `create_indexes` เพื่อเพิ่ม index ที่ขาด (ประโยชน์เชิงประสิทธิภาพ) · **ห้ามรัน purge แบบกวาดทั้งหมดโดยไม่ตรวจรายการ**

**7. ผลกระทบประสิทธิภาพ** — `create_indexes` เพิ่มประสิทธิภาพ query (แต่กินพื้นที่) · purge ลดขนาด DB — ทั้งสองมีภาระชั่วคราว ควรทำในเวลาว่าง

**8. ความปลอดภัย (สำคัญที่สุด)**
- **ความเสี่ยงสูงสุด: ลบข้อมูล/โครงสร้างถาวรโดยไม่สามารถย้อนกลับ** → ต้องมี backup + restore test + การอนุมัติต่อครั้ง
- จำกัดสิทธิ์กลุ่มให้แคบที่สุด (ผู้ดูแลระบบ)
- ทบทวนรายการที่ purge เสนอทีละรายการ (ไม่เชื่อรายการอัตโนมัติ 100%)
- ระวังการลบตาราง/คอลัมน์ที่ยังใช้โดยโมดูลกำหนดเอง `od19_*`

**9. เกณฑ์การยอมรับ**
1. ติดตั้งสำเร็จ ไม่มี ERROR/WARNING ใหม่ใน log
2. เข้าเมนู purge/index ได้เฉพาะผู้ดูแลระบบ
3. ทดสอบ `create_indexes` บน Integration สำเร็จ
4. ทดสอบ purge บนสำเนา DB (Integration) แล้วระบบยังทำงานปกติ
5. มี backup + restore test ล่าสุดกำกับก่อนใช้บน Production

**10. Monitoring** — ตรวจขนาด DB และสุขภาพหลัง purge · ตรวจว่า index ที่สร้างไม่ซ้ำซ้อน · บันทึกทุกการ purge (ใคร/เมื่อไร/อะไร)

**11. Rollback** — **ไม่มี undo** → ต้องกู้จาก backup เท่านั้น · ถอนโมดูลได้ (ตัว wizard หายไป) แต่ **ผลของการ purge ไม่ย้อนกลับ**

**12. ความเสี่ยง**

| ความเสี่ยง | ระดับ | บรรเทา |
| --- | --- | --- |
| ลบข้อมูล/ตารางถาวรผิดพลาด | **HIGH** | backup+restore test + อนุมัติต่อครั้ง + ทบทวนรายการ |
| ลบโครงสร้างที่โมดูล od19_* ยังใช้ | **HIGH** | ตรวจ dependency ก่อน purge |
| ผู้ใช้ไม่มีสิทธิ์เข้าถึง wizard | LOW | จำกัดกลุ่มแคบ |
| รันไทม์กับ 19.0 ยังไม่พิสูจน์ | MEDIUM | ทดสอบบนสำเนา DB/Integration ก่อน |

**13. Task Checklist** — T1 แจ้งความเสี่ยง + อนุมัติหลักการ · T2 backup + restore test · T3 ติดตั้ง Local (ทดลอง) · T4 รีสตาร์ต+ตรวจ log · T5 ทดสอบ `create_indexes` · T6 ทดสอบ purge บนสำเนา DB (Integration) · T7 จำกัดสิทธิ์กลุ่ม · T8 rollback plan (กู้จาก backup) · T9 อนุมัติ go/no-go ก่อน Production

**14. การอนุมัติ/หลักฐาน** — Backup owner ยืนยัน restore · Security reviewer ยืนยันกลุ่มสิทธิ์ · เก็บ log ทุกการ purge + ภาพรายการที่ purge

**15. ภาคผนวกคำสั่ง (PROPOSED)**
```
python odoo-bin -c odoo.conf -d odoo19 -i database_cleanup --stop-after-init
```
```sql
SELECT name, state, latest_version FROM ir_module_module WHERE name = 'database_cleanup';
```
> **คำเตือน:** อย่ารันคำสั่ง purge ผ่าน SQL ตรง ๆ — ใช้ wizard ใน UI เพื่อให้ระบบตรวจสอบ dependency
> ห้ามใส่รหัสผ่านฐานข้อมูลใน command line ให้ใช้ `.pgpass` หรือ interactive prompt เท่านั้น

---

## สรุปลำดับการติดตั้งที่แนะนำ (ยังไม่ดำเนินการ)

```
1. base_cron_exclusion     (LOW  — ฐาน, แก้ cron ทับซ้อน)
2. scheduler_error_mailer  (LOW  — แจ้งเตือน cron ล้มเหลว)
3. base_export_manager     (LOW–MEDIUM — คุม export)
4. session_db              (MEDIUM — ต้องมี rollback ทันที)
5. sentry                  (MEDIUM–HIGH — ต้องมี DSN + กรอง PII)
6. auto_backup             (MEDIUM–HIGH — ต้องแก้ปม list_db)
7. bi_sql_editor           (MEDIUM–HIGH — ต้องมี read-only role + เลือกแทน kpi)
8. database_cleanup        (HIGH — ทำลายข้อมูล, ทำหลังสุดและเมื่ออนุมัติ)
```

**ทุกโมดูลต้องผ่าน:** Local Dev → Shared Dev/Integration → Test/QA → UAT/Training → Production พร้อม backup + restore test ก่อนทุกครั้ง

> เอกสารนี้เป็น **PROPOSED CHANGE — NOT EXECUTED** ทั้งฉบับ ยังไม่มีการติดตั้ง แก้ไข config/สิทธิ์ หรือรีสตาร์ตบริการใด ๆ
