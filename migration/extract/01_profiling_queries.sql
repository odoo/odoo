-- =====================================================================
-- 01_profiling_queries.sql
-- ---------------------------------------------------------------------
-- วัตถุประสงค์ (Purpose)
--   ชุดคำสั่ง Profiling ข้อมูลจากฐานข้อมูล Odoo 15 CE (legacy) เพื่อใช้ใน
--   โครงการย้ายข้อมูลแบบ Greenfield + ETL ไปยัง Odoo 19
--   โดยฐานข้อมูล Odoo 19 ใหม่จะรับเฉพาะข้อมูลหลัก (master data) และ
--   ยอดยกมา (opening balances) เท่านั้น ไม่ยกประวัติธุรกรรมทั้งก้อน
--   ดังนั้นการ Profiling จึงเน้น 3 เรื่อง:
--     (a) ปริมาณข้อมูล (data volume)
--     (b) ช่องว่างคุณภาพข้อมูลที่จะทำให้การ import ล้มเหลว (data quality)
--     (c) ตัวเลข opening balance ที่ต้อง tie หลัง import (reconciliation baseline)
--
-- ข้อบังคับสำคัญ (MANDATORY)
--   1) ต้องรันบนสำเนาที่ restore แล้วเท่านั้น เช่น ฐานข้อมูลชื่อ od15_stage
--      ห้ามรันบนฐานข้อมูล production ของระบบเดิมเด็ดขาด
--   2) ไฟล์นี้เป็น READ-ONLY 100% ใช้เฉพาะ SELECT / WITH เท่านั้น
--      ไม่มี DDL/DML ใด ๆ
--   3) แนะนำให้ตั้งค่าให้การเชื่อมต่อเป็น read-only ด้วย เช่น
--      - role ที่มีสิทธิ์อ่านเท่านั้น
--      - หรือรันใน transaction เดียวแล้ว ROLLBACK
--   4) ก่อนรัน ตรวจสอบว่าฐานข้อมูลสำเนาถูกตั้งชื่อว่า od15_stage และ
--      ตรวจว่า transaction_read_only = on (ดู Query [0.3])
--
-- วิธีรัน (How to run)
--   psql -h <host> -U <user> -d od15_stage -f 01_profiling_queries.sql
--   (บน Windows PowerShell อาจใช้คู่กับ -v ON_ERROR_STOP=1 เพื่อหยุดเมื่อ error)
--   แนะนำให้ redirect ผลลัพธ์เป็นไฟล์เก็บหลักฐาน:
--     psql -h <host> -U <user> -d od15_stage -f 01_profiling_queries.sql > profiling_result.txt
--
-- หมายเหตุเรื่องวันที่ตัดยอด (cutoff date)
--   ทุก Query ที่มีคำว่า DATE '2025-12-31' คือตัวอย่างวันตัดยอด ให้แก้ไขเป็น
--   วันที่ตัดยอดจริงของโครงการก่อนรัน (แก้ทั้งไฟล์ให้ตรงกัน)
--
-- หมายเหตุด้าน schema ที่ตรวจสอบกับ source Odoo 15 CE แล้ว
--   - Odoo 15 ใช้ account_account.internal_type (ค่าคือ 'receivable'/'payable')
--     NOT 'asset_receivable'/'liability_payable' ซึ่งเป็นของ Odoo 17+
--   - account_move_line ไม่มีคอลัมน์ account_type/internal_type ที่เก็บจริง
--     (มีเฉพาะ related แบบไม่ store) จึงต้อง JOIN ไปที่ account_account
--   - account_move.line.full_reconcile_id และ amount_residual มีจริง
--   - product_product / product_template ไม่มีคอลัมน์ standard_price ตรง ๆ
--     เพราะเป็นฟิลด์ company_dependent เก็บค่าใน ir_property
--     (res_id = 'product.product,<id>', type = 'float')
-- =====================================================================


-- =====================================================================
-- ส่วนที่ 0 : ขั้นตอนเตรียมการ / ตรวจเวอร์ชัน
-- =====================================================================

-- [0.1] ตรวจเวอร์ชัน Odoo 15 ที่บันทึกในฐานข้อมูล (ค่า base_version)
--       ผลที่ต้องการ: ค่าขึ้นต้นด้วย "15." เช่น 15.0
SELECT key, value
FROM ir_config_parameter
WHERE key = 'base_version';

-- [0.2] ตรวจเวอร์ชันที่ติดตั้งจริงของโมดูลหลัก (latest_version)
--       ผลที่ต้องการ: latest_version ของ base คือ 15.0.x.x.x
SELECT name, latest_version, state
FROM ir_module_module
WHERE name IN ('base', 'web', 'account', 'stock', 'stock_account', 'sale', 'purchase', 'hr', 'project')
ORDER BY name;

-- [0.3] ยืนยันว่ากำลังรันบนฐานข้อมูล od15_stage และการเชื่อมต่อเป็น read-only
--       ผลที่ต้องการ: database_name = od15_stage และ transaction_read_only = on
SELECT current_database()                                   AS database_name,
       current_user                                         AS connected_role,
       current_setting('transaction_read_only')             AS transaction_read_only;


-- =====================================================================
-- ส่วนที่ 1 : ทะเบียนโมดูลที่ติดตั้งจริง
-- =====================================================================

-- [1.1] จำนวนโมดูลที่ติดตั้งทั้งหมด (state = 'installed')
--       เกณฑ์ผ่าน: ตัวเลขนี้ต้องสอดคล้องกับทะเบียนโมดูลในเอกสาร checklist
SELECT COUNT(*) AS installed_modules
FROM ir_module_module
WHERE state = 'installed';

-- [1.2] รายชื่อโมดูลที่ติดตั้งทั้งหมด พร้อมชื่อผู้พัฒนา (author) และเวอร์ชัน
--       ใช้ประกอบการแยก core / OCA / custom
SELECT name           AS module_name,
       shortdesc      AS module_label,
       latest_version AS version,
       author,
       maintainer
FROM ir_module_module
WHERE state = 'installed'
ORDER BY name;

-- [1.3] แยกหมวดโมดูล: core / OCA / custom
--       custom ตรวจจาก prefix ของโมดูลที่พบจริงในระบบเดิม (autoinfo_*, dtr_*, ฯลฯ)
--       เกณฑ์ผ่าน: รายชื่อ custom ที่ได้ ต้องตรงกับ Module Inventory ใน checklist
SELECT m.name AS module_name,
       m.latest_version AS version,
       CASE
           WHEN m.name LIKE 'autoinfo%'
                OR m.name LIKE 'od15_autoinfo%'
                OR m.name LIKE 'dtr\_%'
                OR m.name = 'account_invoice_get_sale'
               THEN 'custom'
           WHEN m.author ILIKE '%OCA%' OR m.maintainer ILIKE '%OCA%'
               THEN 'OCA'
           ELSE 'core/other'
       END AS module_group
FROM ir_module_module m
WHERE m.state = 'installed'
ORDER BY module_group, module_name;

-- [1.4] นับจำนวนโมดูลแต่ละหมวด (core / OCA / custom)
SELECT CASE
           WHEN m.name LIKE 'autoinfo%'
                OR m.name LIKE 'od15_autoinfo%'
                OR m.name LIKE 'dtr\_%'
                OR m.name = 'account_invoice_get_sale'
               THEN 'custom'
           WHEN m.author ILIKE '%OCA%' OR m.maintainer ILIKE '%OCA%'
               THEN 'OCA'
           ELSE 'core/other'
       END AS module_group,
       COUNT(*) AS module_count
FROM ir_module_module m
WHERE m.state = 'installed'
GROUP BY module_group
ORDER BY module_group;

-- [1.5] รายชื่อโมดูล custom ที่ติดตั้งจริง (เฉพาะ autoinfo_* / dtr_* / account_invoice_get_sale)
--       เกณฑ์ผ่าน: ไม่ควรมีโมดูล custom ใดที่ยังไม่อยู่ใน mapping od19_* ปลายทาง
SELECT name AS module_name, latest_version AS version
FROM ir_module_module
WHERE state = 'installed'
  AND (name LIKE 'autoinfo%'
       OR name LIKE 'od15_autoinfo%'
       OR name LIKE 'dtr\_%'
       OR name = 'account_invoice_get_sale')
ORDER BY name;


-- =====================================================================
-- ส่วนที่ 2 : ปริมาณข้อมูล (row counts)
-- =====================================================================

-- [2.1] จำนวนแถวของตาราง master data หลัก
--       เกณฑ์ผ่าน: ได้ตัวเลข baseline เพื่อประเมิน time/volume ของ ETL
SELECT 'res_company'         AS table_name, COUNT(*) AS row_count FROM res_company
UNION ALL SELECT 'res_users',          COUNT(*) FROM res_users
UNION ALL SELECT 'res_partner',        COUNT(*) FROM res_partner
UNION ALL SELECT 'hr_department',      COUNT(*) FROM hr_department
UNION ALL SELECT 'hr_employee',        COUNT(*) FROM hr_employee
UNION ALL SELECT 'product_category',   COUNT(*) FROM product_category
UNION ALL SELECT 'product_template',   COUNT(*) FROM product_template
UNION ALL SELECT 'product_product',    COUNT(*) FROM product_product
UNION ALL SELECT 'product_supplierinfo', COUNT(*) FROM product_supplierinfo
UNION ALL SELECT 'uom_uom',            COUNT(*) FROM uom_uom
UNION ALL SELECT 'product_pricelist',  COUNT(*) FROM product_pricelist
UNION ALL SELECT 'product_pricelist_item', COUNT(*) FROM product_pricelist_item
ORDER BY table_name;

-- [2.2] จำนวนแถวของตารางบัญชี (accounting)
SELECT 'account_account'          AS table_name, COUNT(*) AS row_count FROM account_account
UNION ALL SELECT 'account_journal',          COUNT(*) FROM account_journal
UNION ALL SELECT 'account_tax',              COUNT(*) FROM account_tax
UNION ALL SELECT 'account_payment_term',     COUNT(*) FROM account_payment_term
UNION ALL SELECT 'account_analytic_account', COUNT(*) FROM account_analytic_account
UNION ALL SELECT 'account_move',             COUNT(*) FROM account_move
UNION ALL SELECT 'account_move_line',        COUNT(*) FROM account_move_line
ORDER BY table_name;

-- [2.3] จำนวนแถวของตารางขาย/ซื้อ
SELECT 'sale_order'          AS table_name, COUNT(*) AS row_count FROM sale_order
UNION ALL SELECT 'sale_order_line',          COUNT(*) FROM sale_order_line
UNION ALL SELECT 'purchase_order',           COUNT(*) FROM purchase_order
UNION ALL SELECT 'purchase_order_line',      COUNT(*) FROM purchase_order_line
ORDER BY table_name;

-- [2.4] จำนวน account_move แยกตาม move_type และ state
--       (ใช้ประเมินว่าจะยกเฉพาะเอกสารค้าง หรือยกยอดเป็น journal entry เปิดบัญชี)
--       เกณฑ์ผ่าน: ทราบจำนวนเอกสาร draft/posted/cancel ของแต่ละประเภท
SELECT move_type, state, COUNT(*) AS move_count
FROM account_move
GROUP BY move_type, state
ORDER BY move_type, state;

-- [2.5] จำนวนแถวตารางสต็อกและมูลค่าสต็อก
SELECT 'stock_quant'             AS table_name, COUNT(*) AS row_count FROM stock_quant
UNION ALL SELECT 'stock_move',              COUNT(*) FROM stock_move
UNION ALL SELECT 'stock_valuation_layer',   COUNT(*) FROM stock_valuation_layer
ORDER BY table_name;

-- [2.6] จำนวนแถวโปรเจกต์และการวิเคราะห์ + ไฟล์แนบ
SELECT 'project_project'   AS table_name, COUNT(*) AS row_count FROM project_project
UNION ALL SELECT 'ir_attachment',      COUNT(*) FROM ir_attachment
ORDER BY table_name;


-- =====================================================================
-- ส่วนที่ 3 : คุณภาพข้อมูล (data quality) — ต้องแก้ก่อน import
-- =====================================================================

-- [3.1a] partner ประเภทนิติบุคคล (is_company) ที่ไม่มีเลขผู้เสียภาษี (VAT ว่าง)
--        เกณฑ์ผ่าน: จำนวนใกล้ 0 (หรือระบุในรายการยกเว้นที่ตกลงกับฝ่ายบัญชี)
SELECT id, name, vat, active
FROM res_partner
WHERE is_company = TRUE
  AND (vat IS NULL OR btrim(vat) = '')
ORDER BY name;

-- [3.1b] partner ที่ VAT ไม่ใช่ 13 หลัก (หลังตัดอักขระที่ไม่ใช่ตัวเลขออก)
--        เกณฑ์ผ่าน: ไม่เหลือแถวที่ผิดรูปแบบก่อน import
SELECT id, name, vat
FROM res_partner
WHERE vat IS NOT NULL
  AND btrim(vat) <> ''
  AND regexp_replace(vat, '[^0-9]', '', 'g') !~ '^[0-9]{13}$'
ORDER BY name;

-- [3.2] partner ที่มีชื่อซ้ำกัน (ต้องยุบรวม/แยกแยะก่อน import)
--       เกณฑ์ผ่าน: จำนวนกลุ่มชื่อซ้ำเป็น 0 หรือมีเอกสาร justification
SELECT name, COUNT(*) AS occurrences
FROM res_partner
WHERE active = TRUE
GROUP BY name
HAVING COUNT(*) > 1
ORDER BY occurrences DESC, name;

-- [3.3] partner ที่ถูกปิดใช้งาน (active = FALSE) แต่ยังมียอดค้าง receivables/payables
--       เกณฑ์ผ่าน: ไม่มีรายการค้างที่ผูกกับ partner ที่ปิดใช้งาน
SELECT rp.id AS partner_id, rp.name AS partner_name, rp.active,
       SUM(aml.amount_residual) AS open_residual
FROM account_move_line aml
JOIN res_partner rp       ON rp.id = aml.partner_id
JOIN account_account aa   ON aa.id = aml.account_id
WHERE rp.active = FALSE
  AND aml.parent_state = 'posted'
  AND aml.full_reconcile_id IS NULL
  AND aa.internal_type IN ('receivable', 'payable')
GROUP BY rp.id, rp.name, rp.active
HAVING ROUND(SUM(aml.amount_residual), 2) <> 0
ORDER BY open_residual DESC;

-- [3.4] สินค้าที่ไม่มีรหัสสินค้า (default_code ว่าง)
--       เกณฑ์ผ่าน: ไม่เหลือสินค้า active ที่ไม่มี default_code ก่อน import
SELECT pp.id, pt.name AS product_name, pp.default_code
FROM product_product pp
JOIN product_template pt ON pt.id = pp.product_tmpl_id
WHERE (pp.default_code IS NULL OR btrim(pp.default_code) = '')
  AND pt.active = TRUE
ORDER BY pt.name;

-- [3.5] ตรวจ UoM ที่ถูกใช้ พร้อมจำนวนสินค้า (เพื่อหา UoM แปลก/ไม่เป็นมาตรฐาน)
--       เกณฑ์ผ่าน: ทุก UoM ที่ใช้ เป็นหน่วยมาตรฐานที่ตกลง (เช่น Units, kg, m, l)
SELECT u.id AS uom_id, u.name AS uom_name, u.category_id, COUNT(pt.id) AS product_count
FROM uom_uom u
LEFT JOIN product_template pt ON pt.uom_id = u.id
GROUP BY u.id, u.name, u.category_id
ORDER BY product_count DESC, u.name;

-- [3.6] สินค้าคงคลัง (storable) ที่ราคาต้นทุน = 0
--       เกณฑ์ผ่าน: สินค้าที่มีสต็อกคงเหลือต้องมี standard_price > 0
--       หมายเหตุ: Odoo 15 เก็บ standard_price เป็น company_dependent
--                 ใน ir_property (res_id = 'product.product,<id>') จึงต้อง JOIN
SELECT pp.id, pt.name AS product_name, pp.default_code,
       COALESCE(ip.value_float, 0) AS standard_price
FROM product_product pp
JOIN product_template pt ON pt.id = pp.product_tmpl_id
LEFT JOIN ir_property ip ON ip.name = 'standard_price'
     AND ip.res_id = 'product.product,' || pp.id
WHERE COALESCE(ip.value_float, 0) = 0
  AND pt.type = 'product'
ORDER BY pt.name;

-- [3.7] สินค้าที่มีสต็อกติดลบ (รวมเฉพาะ location ภายใน = internal)
--       เกณฑ์ผ่าน: ไม่มี on_hand_qty ติดลบก่อนทำ opening stock
SELECT sq.product_id, pp.default_code, pt.name AS product_name,
       SUM(sq.quantity) AS on_hand_qty
FROM stock_quant sq
JOIN stock_location sl      ON sl.id = sq.location_id
JOIN product_product pp     ON pp.id = sq.product_id
JOIN product_template pt    ON pt.id = pp.product_tmpl_id
WHERE sl.usage = 'internal'
GROUP BY sq.product_id, pp.default_code, pt.name
HAVING SUM(sq.quantity) < 0
ORDER BY on_hand_qty;

-- [3.8] บัญชีที่ code ซ้ำกันภายในบริษัทเดียวกัน
--       เกณฑ์ผ่าน: ไม่มี code ซ้ำในบริษัทเดียว (company_id, code) เป็น unique
SELECT company_id, code, COUNT(*) AS occurrences
FROM account_account
GROUP BY company_id, code
HAVING COUNT(*) > 1
ORDER BY company_id, code;

-- [3.9] ภาษีที่ rate (amount) ผิดจากที่คาดไว้ (ตรวจเฉพาะชนิด percent)
--       บริบทไทย: VAT มาตรฐาน = 7 และ 0 ; รายการอื่นให้ทบทวนทีละราย
--       เกณฑ์ผ่าน: ไม่มีภาษี percent ที่ rate ไม่ถูกต้องหลุดไปยัง Odoo 19
SELECT id, name, type_tax_use, amount_type, amount, active
FROM account_tax
WHERE amount_type = 'percent'
  AND ROUND(amount::numeric, 2) NOT IN (0.00, 7.00)
ORDER BY type_tax_use, amount;

-- [3.10a] เอกสารร่าง (draft) ที่ค้างเก่าเกิน 1 ปี
--        เกณฑ์ผ่าน: รายการที่ค้างเก่าต้องถูกยกเลิก/ปิด หรือมีเอกสารอนุมัติ
SELECT move_type, state, COUNT(*) AS move_count, MIN(date) AS oldest_date
FROM account_move
WHERE state = 'draft'
  AND date < (CURRENT_DATE - INTERVAL '1 year')
GROUP BY move_type, state
ORDER BY move_count DESC;

-- [3.10b] เอกสาร posted ที่ยังไม่ชำระ (not_paid/partial) และค้างเก่าเกิน 1 ปี
--        เกณฑ์ผ่าน: รายการเหล่านี้ต้องถูกนำไปคิดในยอด AR/AP opening ให้ครบ
SELECT am.move_type, COUNT(DISTINCT am.id) AS move_count, MIN(am.date) AS oldest_date
FROM account_move am
WHERE am.state = 'posted'
  AND am.payment_state IN ('not_paid', 'partial')
  AND am.date < (CURRENT_DATE - INTERVAL '1 year')
GROUP BY am.move_type
ORDER BY move_count DESC;

-- [3.11a] สรุปไฟล์แนบ (attachment): ที่เก็บและขนาดรวม
--        ใช้ประเมินว่าจะต้องคัดลอกไฟล์จาก filestore เท่าใด
SELECT COUNT(*)                                                          AS total_attachments,
       COUNT(*) FILTER (WHERE store_fname IS NOT NULL AND db_datas IS NULL) AS stored_on_filestore,
       COUNT(*) FILTER (WHERE db_datas IS NOT NULL)                       AS stored_in_database,
       pg_size_pretty(COALESCE(SUM(file_size), 0)::bigint)                AS total_size
FROM ir_attachment;

-- [3.11b] ไฟล์แนบที่ระเบียนไม่สมบูรณ์ (ไม่มีทั้ง store_fname และ db_datas)
--        เกณฑ์ผ่าน: ไม่มี attachment ที่ข้อมูลว่างเปล่า
--        หมายเหตุ: การตรวจว่าไฟล์จริงหายจาก filestore ต้องทำที่ระดับ filesystem
--                  นอกฐานข้อมูล ไม่สามารถตรวจได้ด้วย SQL เพียงอย่างเดียว
SELECT id, name, res_model, res_id, store_fname, file_size
FROM ir_attachment
WHERE (store_fname IS NULL OR btrim(store_fname) = '')
  AND db_datas IS NULL
ORDER BY id
LIMIT 200;


-- =====================================================================
-- ส่วนที่ 4 : ตัวเลข baseline ที่ต้อง tie หลัง import (reconciliation)
-- =====================================================================
-- หมายเหตุ: แก้ DATE '2025-12-31' เป็นวันตัดยอดจริงก่อนรันทุก Query ในส่วนนี้

-- [4.1a] Trial Balance ณ วันตัดยอด — แยกตามบัญชี
--        ใช้ tie กับยอดยกมาที่ import เข้า Odoo 19
SELECT aa.id   AS account_id,
       aa.code AS account_code,
       aa.name AS account_name,
       aa.internal_type,
       SUM(aml.debit)   AS total_debit,
       SUM(aml.credit)  AS total_credit,
       SUM(aml.balance) AS balance
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
JOIN account_move am    ON am.id = aml.move_id
WHERE am.state = 'posted'
  AND aml.date <= DATE '2025-12-31'
GROUP BY aa.id, aa.code, aa.name, aa.internal_type
ORDER BY aa.code;

-- [4.1b] Trial Balance ณ วันตัดยอด — ยอดรวมทั้งบริษัท (ต้อง debit = credit)
--        เกณฑ์ผ่าน: total_debit = total_credit และ balance รวม = 0
SELECT SUM(aml.debit)   AS total_debit,
       SUM(aml.credit)  AS total_credit,
       SUM(aml.balance) AS balance
FROM account_move_line aml
JOIN account_move am ON am.id = aml.move_id
WHERE am.state = 'posted'
  AND aml.date <= DATE '2025-12-31';

-- [4.2] AR opening — ยอดลูกหนี้คงเหลือ แยกตาม partner
--       ใช้ account_move_line ที่ full_reconcile_id IS NULL และ account เป็น receivable
SELECT rp.id   AS partner_id,
       rp.name AS partner_name,
       SUM(aml.amount_residual) AS ar_open_balance
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
JOIN account_move am    ON am.id = aml.move_id
JOIN res_partner rp     ON rp.id = aml.partner_id
WHERE aa.internal_type = 'receivable'
  AND am.state = 'posted'
  AND aml.full_reconcile_id IS NULL
  AND ROUND(aml.amount_residual, 2) <> 0
GROUP BY rp.id, rp.name
ORDER BY ar_open_balance DESC;

-- [4.2b] AR aging (ตามวันครบกำหนด date_maturity) — แยกช่วงอายุหนี้
SELECT rp.id   AS partner_id,
       rp.name AS partner_name,
       SUM(CASE WHEN aml.date_maturity IS NULL OR aml.date_maturity >= DATE '2025-12-31'
                THEN aml.amount_residual ELSE 0 END) AS not_due,
       SUM(CASE WHEN aml.date_maturity < DATE '2025-12-31'
                 AND aml.date_maturity >= DATE '2025-09-30'
                THEN aml.amount_residual ELSE 0 END) AS due_0_90,
       SUM(CASE WHEN aml.date_maturity < DATE '2025-09-30'
                THEN aml.amount_residual ELSE 0 END) AS due_over_90
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
JOIN account_move am    ON am.id = aml.move_id
JOIN res_partner rp     ON rp.id = aml.partner_id
WHERE aa.internal_type = 'receivable'
  AND am.state = 'posted'
  AND aml.full_reconcile_id IS NULL
  AND ROUND(aml.amount_residual, 2) <> 0
GROUP BY rp.id, rp.name
ORDER BY rp.name;

-- [4.3] AP opening — ยอดเจ้าหนี้คงเหลือ แยกตาม partner
SELECT rp.id   AS partner_id,
       rp.name AS partner_name,
       SUM(aml.amount_residual) AS ap_open_balance
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
JOIN account_move am    ON am.id = aml.move_id
JOIN res_partner rp     ON rp.id = aml.partner_id
WHERE aa.internal_type = 'payable'
  AND am.state = 'posted'
  AND aml.full_reconcile_id IS NULL
  AND ROUND(aml.amount_residual, 2) <> 0
GROUP BY rp.id, rp.name
ORDER BY ap_open_balance DESC;

-- [4.3b] AP aging (ตามวันครบกำหนด date_maturity) — แยกช่วงอายุหนี้
SELECT rp.id   AS partner_id,
       rp.name AS partner_name,
       SUM(CASE WHEN aml.date_maturity IS NULL OR aml.date_maturity >= DATE '2025-12-31'
                THEN aml.amount_residual ELSE 0 END) AS not_due,
       SUM(CASE WHEN aml.date_maturity < DATE '2025-12-31'
                 AND aml.date_maturity >= DATE '2025-09-30'
                THEN aml.amount_residual ELSE 0 END) AS due_0_90,
       SUM(CASE WHEN aml.date_maturity < DATE '2025-09-30'
                THEN aml.amount_residual ELSE 0 END) AS due_over_90
FROM account_move_line aml
JOIN account_account aa ON aa.id = aml.account_id
JOIN account_move am    ON am.id = aml.move_id
JOIN res_partner rp     ON rp.id = aml.partner_id
WHERE aa.internal_type = 'payable'
  AND am.state = 'posted'
  AND aml.full_reconcile_id IS NULL
  AND ROUND(aml.amount_residual, 2) <> 0
GROUP BY rp.id, rp.name
ORDER BY rp.name;

-- [4.4a] มูลค่าสต็อกและปริมาณคงเหลือ แยกตามสินค้า (จาก stock_valuation_layer)
--       remaining_qty/remaining_value = FIFO layer ที่ยังเหลือ = opening stock
SELECT pp.default_code,
       pt.name AS product_name,
       SUM(svl.remaining_qty)   AS remaining_qty,
       SUM(svl.remaining_value) AS remaining_value
FROM stock_valuation_layer svl
JOIN product_product pp  ON pp.id = svl.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
GROUP BY pp.default_code, pt.name
HAVING ROUND(SUM(svl.remaining_qty)::numeric, 4) <> 0
    OR ROUND(SUM(svl.remaining_value)::numeric, 2) <> 0
ORDER BY remaining_value DESC;

-- [4.4b] ปริมาณคงเหลือจาก stock_quant (นับจริงในคลัง) แยกตามสินค้า
--       ใช้เทียบกับ [4.4a] เพื่อตรวจว่าปริมาณและมูลค่าสอดคล้องกัน
SELECT pp.default_code,
       pt.name AS product_name,
       SUM(sq.quantity) AS on_hand_qty
FROM stock_quant sq
JOIN stock_location sl   ON sl.id = sq.location_id
JOIN product_product pp  ON pp.id = sq.product_id
JOIN product_template pt ON pt.id = pp.product_tmpl_id
WHERE sl.usage = 'internal'
GROUP BY pp.default_code, pt.name
HAVING SUM(sq.quantity) <> 0
ORDER BY pp.default_code;

-- [4.4c] มูลค่าสต็อกรวมทั้งบริษัท (ใช้ tie ยอด Stock Valuation หลัง import)
SELECT SUM(remaining_qty)   AS total_remaining_qty,
       SUM(remaining_value) AS total_inventory_value
FROM stock_valuation_layer;

-- [4.9] จำนวนเอกสารค้างทั้งหมด (ใช้เป็นตัวเลข baseline จำนวนเอกสารคงเหลือ)
SELECT 'account_move_draft'          AS metric, COUNT(*) AS doc_count FROM account_move WHERE state = 'draft'
UNION ALL SELECT 'account_move_posted_unpaid', COUNT(*) FROM account_move WHERE state = 'posted' AND payment_state IN ('not_paid', 'partial')
UNION ALL SELECT 'sale_order_confirmed',       COUNT(*) FROM sale_order WHERE state = 'sale'
UNION ALL SELECT 'sale_order_quotation_open',  COUNT(*) FROM sale_order WHERE state IN ('draft', 'sent')
UNION ALL SELECT 'purchase_order_confirmed',   COUNT(*) FROM purchase_order WHERE state = 'purchase'
UNION ALL SELECT 'purchase_order_rfq_open',    COUNT(*) FROM purchase_order WHERE state IN ('draft', 'sent', 'to approve')
UNION ALL SELECT 'project_active',             COUNT(*) FROM project_project WHERE active = TRUE
ORDER BY metric;


-- =====================================================================
-- ส่วนที่ 5 : OPTIONAL — ตารางที่ต้องยืนยันก่อนใช้
-- ---------------------------------------------------------------------
-- คำเตือน: Query กลุ่มนี้บางตัวอ้างถึงตารางที่มาจากโมดูล enterprise/OCA/custom
--           ซึ่ง "ยังยืนยันไม่ได้" จาก source Odoo 15 CE ที่ตรวจสอบ
--           ให้รัน [5.0] เพื่อตรวจว่าตารางมีอยู่จริงก่อน
--           แล้วจึงเปิดใช้ Query ด้านล่างเฉพาะรายการที่ยืนยันแล้วเท่านั้น
-- =====================================================================

-- [5.0] ตรวจรายชื่อตารางที่เกี่ยวข้อง (asset / WHT / prepayment / cheque)
--       รันก่อนเพื่อรู้ว่าตารางใดมีอยู่จริงในฐานข้อมูล od15_stage
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (table_name LIKE 'account_asset%'
       OR table_name LIKE '%wht%'
       OR table_name LIKE '%cheque%'
       OR table_name LIKE '%prepay%'
       OR table_name LIKE 'dtr_%')
ORDER BY table_name;

-- [5.1] (OPTIONAL) ทะเบียนสินทรัพย์ + ค่าเสื่อมราคาสะสม
--       ต้องยืนยันก่อนว่าโมดูล asset (account_asset) ถูกติดตั้ง (ดู [1.2])
--       ตาราง account_asset มาจากโมดูล enterprise/OCA — ยังไม่ยืนยันใน CE นี้
--       ชื่อคอลัมน์ (original_value / book_value / value_residual) ต้องตรวจกับ
--       โมดูลจริงก่อนเปิดใช้
-- SELECT id, name, original_value, book_value, value_residual, active
-- FROM account_asset
-- WHERE active = TRUE
-- ORDER BY name;

-- [5.2] (OPTIONAL) ยอด WHT ค้าง (ภาษีหัก ณ ที่จ่าย)
--       ตารางเป็นของโมดูล custom (เช่น dtr_wht จากโมดูล dtr_account/autoinfo_account)
--       ต้องยืนยันชื่อตาราง/คอลัมน์จาก [5.0] และ ir_module_module ก่อน
-- SELECT COUNT(*) AS wht_rows
-- FROM dtr_wht;

-- [5.3] (OPTIONAL) ยอดเงินทดรองจ่ายค้าง (prepayment/advance)
--       ตารางเป็นของโมดูล custom (เช่น dtr_account_prepayment / dtr_account_billing)
--       ต้องยืนยันชื่อตาราง/คอลัมน์จาก [5.0] ก่อน
-- SELECT COUNT(*) AS prepayment_rows
-- FROM dtr_account_prepayment;

-- [5.4] (OPTIONAL) เช็คค้างรับ/ค้างจ่าย
--       ตารางเป็นของโมดูล custom (cheque) — ต้องยืนยันจาก [5.0] ก่อน
-- SELECT COUNT(*) AS cheque_rows
-- FROM account_cheque;
