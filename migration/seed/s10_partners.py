# -*- coding: utf-8 -*-
"""s10_partners — คู่ค้าตัวอย่าง (ลูกค้า/ผู้ขาย) สำหรับ Odoo 19

หมายเหตุ: เป็นข้อมูลสมมติสำหรับพนักงานทดสอบ ไม่ใช่ข้อมูลจริงจากระบบเดิม
"""
import seed_common

_TAX = '0105558000014'  # เลขประจำตัวผู้เสียภาษีตัวอย่าง (ใช้ซ้ำได้กับหลายรายเพื่อการทดสอบ)

_CUSTOMERS = [
    ('cust_01', 'บริษัท สยามเทค อุตสาหกรรม จำกัด', 'สำนักงานใหญ่', 'เลขที่ 99 หมู่ 4 ถ.สุขุมวิท', 'บางนา', 'กรุงเทพมหานคร', '10260', '021234001', 'contact@siamtech.example'),
    ('cust_02', 'บริษัท กรุงเทพ ก่อสร้าง จำกัด', 'สำนักงานใหญ่', 'เลขที่ 12 ถ.รัชดาภิเษก', 'ห้วยขวาง', 'กรุงเทพมหานคร', '10310', '021234002', 'info@bkkconstruct.example'),
    ('cust_03', 'บริษัท อีสเทิร์น ฟู้ดส์ โปรดักส์ จำกัด', 'โรงงาน', 'เลขที่ 45 นิคมอุตสาหกรรมอมตะซิตี้', 'ปลวกแดง', 'ระยอง', '21140', '038123003', 'sales@easternfoods.example'),
    ('cust_04', 'บริษัท ไทยพรีซิชั่น อิเล็คทริค จำกัด', 'สำนักงานใหญ่', 'เลขที่ 88 ถ.บางนา-ตราด', 'บางพลี', 'สมุทรปราการ', '10540', '021234004', 'purchase@tpelectric.example'),
    ('cust_05', 'บริษัท นครปฐม การเกษตร จำกัด', 'สำนักงานใหญ่', 'เลขที่ 7 ถ.เพชรเกษม', 'เมือง', 'นครปฐม', '73000', '034123005', 'agri@npk.example'),
    ('cust_06', 'บริษัท ชลบุรี ปิโตรเคมี จำกัด', 'โรงงาน', 'เลขที่ 200 นิคมอุตสาหกรรมแหลมฉบัง', 'ศรีราชา', 'ชลบุรี', '20230', '038123006', 'contact@cbpetro.example'),
    ('cust_07', 'บริษัท เชียงใหม่ รีสอร์ท แอนด์ สปา จำกัด', 'สำนักงานใหญ่', 'เลขที่ 55 ถ.นิมมานเหมินท์', 'เมือง', 'เชียงใหม่', '50200', '053123007', 'reserve@cmresort.example'),
    ('cust_08', 'บริษัท อุดรธานี ทรานสปอร์ต จำกัด', 'สำนักงานใหญ่', 'เลขที่ 33 ถ.มิตรภาพ', 'เมือง', 'อุดรธานี', '41000', '042123008', 'logistics@udtransport.example'),
    ('cust_09', 'บริษัท ระยอง เอ็นจิเนียริ่ง จำกัด', 'สำนักงานใหญ่', 'เลขที่ 66 ถ.สุขุมวิท', 'เมือง', 'ระยอง', '21000', '038123009', 'eng@ryengineering.example'),
    ('cust_10', 'บริษัท สงขลา ซีฟู้ด จำกัด', 'โรงงาน', 'เลขที่ 21 ถ.เพชรเกษม', 'หาดใหญ่', 'สงขลา', '90110', '074123010', 'sales@songkhlaseafood.example'),
]

_CUSTOMER_PEOPLE = [
    ('cperson_01', 'คุณสมชาย ใจดี', 'กรุงเทพมหานคร'),
    ('cperson_02', 'คุณวิภา รักไทย', 'นนทบุรี'),
    ('cperson_03', 'คุณประเสริฐ มั่งมี', 'ปทุมธานี'),
]

_VENDORS = [
    ('vend_01', 'บริษัท เหล็กไทย คอร์ปอเรชั่น จำกัด', 'เลขที่ 1 ถ.พระราม 2', 'บางขุนเทียน', 'กรุงเทพมหานคร', '10150', '024123001', 'sales@thaisteel.example'),
    ('vend_02', 'บริษัท ปูนสยามวัสดุก่อสร้าง จำกัด', 'เลขที่ 15 ถ.เพชรเกษม', 'หนองแขม', 'กรุงเทพมหานคร', '10160', '024123002', 'order@siamcement.example'),
    ('vend_03', 'บริษัท สยาม อิเล็กทรอนิกส์ ซัพพลาย จำกัด', 'เลขที่ 210 ถ.เทพารักษ์', 'เมือง', 'สมุทรปราการ', '10270', '024123003', 'supply@siamel.example'),
    ('vend_04', 'บริษัท บรรจุภัณฑ์ไทย จำกัด', 'เลขที่ 8 ถ.เศรษฐกิจ 1', 'กระทุ่มแบน', 'สมุทรสาคร', '74110', '034123004', 'pack@thaipkg.example'),
    ('vend_05', 'บริษัท เคมีภัณฑ์ตะวันออก จำกัด', 'เลขที่ 77 นิคมอุตสาหกรรมมาบตาพุด', 'เมือง', 'ระยอง', '21150', '038123005', 'chem@eastchem.example'),
    ('vend_06', 'บริษัท ซ่อมบำรุงอุตสาหกรรม จำกัด', 'เลขที่ 5 ถ.นิมิตรใหม่', 'คลองสามวา', 'กรุงเทพมหานคร', '10510', '024123006', 'service@indmaint.example'),
    ('vend_07', 'บริษัท ขนส่งด่วนไทย จำกัด', 'เลขที่ 40 ถ.กาญจนาภิเษก', 'บางแค', 'กรุงเทพมหานคร', '10160', '024123007', 'cs@thaiexpress.example'),
    ('vend_08', 'บริษัท ซอฟต์แวร์โซลูชั่น จำกัด', 'เลขที่ 300 อาคารดิจิทัลพาร์ค ถ.เพชรบุรีตัดใหม่', 'ห้วยขวาง', 'กรุงเทพมหานคร', '10310', '024123008', 'sales@softsolution.example'),
    ('vend_09', 'บริษัท สำนักงานบัญชีกรุงเทพ จำกัด', 'เลขที่ 62 ถ.สีลม', 'บางรัก', 'กรุงเทพมหานคร', '10500', '024123009', 'account@bkkacc.example'),
    ('vend_10', 'บริษัท พลังงานสะอาด จำกัด', 'เลขที่ 19 ถ.รามคำแหง', 'บางกะปิ', 'กรุงเทพมหานคร', '10240', '024123010', 'energy@cleanpower.example'),
]


def _th(ctx):
    return ctx.env.ref('base.th', raise_if_not_found=False)


def _enrich_company(ctx, th):
    """เติมที่อยู่/เลขผู้เสียภาษี/เลขสาขาให้บริษัทตัวเอง เพื่อให้ใบกำกับภาษี 86/4 ผ่าน."""
    comp = ctx.company.partner_id
    vals = {}
    if 'vat' in comp._fields and not comp.vat:
        vals['vat'] = _TAX
    if 'street' in comp._fields and not comp.street:
        vals['street'] = 'เลขที่ 1 อาคารสำนักงานใหญ่ ถ.สุขุมวิท'
    if 'city' in comp._fields and not comp.city:
        vals['city'] = 'คลองเตย'
    if 'zip' in comp._fields and not comp.zip:
        vals['zip'] = '10110'
    if th and 'country_id' in comp._fields and not comp.country_id:
        vals['country_id'] = th.id
    if 'company_registry' in comp._fields and not comp.company_registry:
        vals['company_registry'] = '00000'
    if vals:
        ctx.guard('company-partner', comp.write, vals)


def run(ctx):
    ctx.step('s10_partners', 'คู่ค้าไทย (ลูกค้า/ผู้ขาย)')
    th = _th(ctx)
    customers, vendors = [], []

    # บริษัทเอง: ต้องมีชื่อ/ที่อยู่/เลขผู้เสียภาษี/เลขสาขาครบก่อนออกใบกำกับภาษี
    _enrich_company(ctx, th)

    for key, name, label, street, city, state, zipc, phone, email in _CUSTOMERS:
        vals = {
            'name': name, 'is_company': True, 'company_type': 'company',
            'vat': _TAX, 'street': street, 'city': city, 'zip': zipc,
            'country_id': th.id if th else False, 'phone': phone, 'email': email,
            'customer_rank': 1, 'supplier_rank': 0,
            'company_registry': '00001',  # เลขสาขา (ม.86/4 ข้อ 8)
        }
        if label and 'l10n_th_branch_name' in ctx.fields('res.partner'):
            vals['l10n_th_branch_name'] = label
        rec = ctx.upsert('res.partner', key, vals)
        if rec:
            customers.append(rec)

    for key, name, city in _CUSTOMER_PEOPLE:
        vals = {
            'name': name, 'is_company': False, 'company_type': 'person',
            'city': city, 'country_id': th.id if th else False,
            'customer_rank': 1, 'supplier_rank': 0,
        }
        rec = ctx.upsert('res.partner', key, vals)
        if rec:
            customers.append(rec)

    for key, name, street, city, state, zipc, phone, email in _VENDORS:
        vals = {
            'name': name, 'is_company': True, 'company_type': 'company',
            'vat': _TAX, 'street': street, 'city': city, 'zip': zipc,
            'country_id': th.id if th else False, 'phone': phone, 'email': email,
            'customer_rank': 0, 'supplier_rank': 1,
            'company_registry': '00001',
        }
        rec = ctx.upsert('res.partner', key, vals)
        if rec:
            vendors.append(rec)

    # fallback: ถ้าสร้างไม่ได้เลย ให้หยิบคู่ค้าที่มีอยู่เดิมมาใช้ต่อ
    if not customers:
        customers = list(ctx.find('res.partner', [('customer_rank', '>', 0)], limit=10))
    if not vendors:
        vendors = list(ctx.find('res.partner', [('supplier_rank', '>', 0)], limit=10))

    ctx.state['customers'] = customers
    ctx.state['vendors'] = vendors
    ctx.log("ลูกค้า %d ราย / ผู้ขาย %d ราย" % (len(customers), len(vendors)))
