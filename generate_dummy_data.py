# -*- coding: utf-8 -*-
import datetime
import random
import odoo
from odoo import fields, tools, api
from odoo.api import Environment

def run():
    tools.config.parse_config(['-c', 'odoo.conf', '-d', 'sifnext_dev'])
    registry = odoo.modules.registry.Registry.new('sifnext_dev')
    with registry.cursor() as cr:
        env = Environment(cr, odoo.SUPERUSER_ID, {})

        # Ensure superuser / admin user has PPL groups
        grp_finance = env.ref('sifnext_ppl.group_ppl_finance', raise_if_not_found=False)
        grp_approver = env.ref('sifnext_ppl.group_ppl_approver', raise_if_not_found=False)
        if grp_finance and grp_finance not in env.user.group_ids:
            env.user.write({'group_ids': [(4, grp_finance.id)]})
        if grp_approver and grp_approver not in env.user.group_ids:
            env.user.write({'group_ids': [(4, grp_approver.id)]})

        companies = env['res.company'].search([], order='id asc')
        print(f'=== GENERATING COMPLETE DUMMY DATA FOR {len(companies)} COMPANIES ===')

        # ----------------------------------------------------
        # MASTER VENDORS (Shared)
        # ----------------------------------------------------
        Vendor = env['sif.vendor'].sudo()
        vendor_names = [
            'PT PLN (Persero)', 'PT Pertamina Retail', 'PT Telkom Indonesia Tbk',
            'CV Media Alat Tulis', 'PT Nusa Konstruksi', 'CV Anugerah Jaya',
            'PT Surya Kencana', 'PT Mitra Utama'
        ]
        vendors = []
        for vname in vendor_names:
            v = Vendor.search([('name', '=', vname)], limit=1)
            if not v:
                v = Vendor.create({
                    'name': vname,
                    'phone': f'031-892{random.randint(1000, 9999)}',
                    'email': f'{vname.lower().replace(" ", "").replace(".", "")[:12]}@vendor.co.id',
                    'address': 'Jl. Veteran No. 45, Gresik',
                })
            vendors.append(v)
        print(f'Master Vendors Ready: {len(vendors)}')

        # ----------------------------------------------------
        # MASTER BANK (Shared)
        # ----------------------------------------------------
        BankMaster = env['transaksi.bank.master'].sudo()
        bank_list = [
            ('BCA', 'Bank Central Asia'),
            ('BNI', 'Bank Negara Indonesia'),
            ('Mandiri', 'Bank Mandiri'),
            ('BRI', 'Bank Rakyat Indonesia'),
            ('BTN', 'Bank Tabungan Negara'),
            ('CIMB', 'Bank CIMB Niaga'),
            ('BSI', 'Bank Syariah Indonesia'),
        ]
        master_banks = {}
        for bcode, bname in bank_list:
            bm = BankMaster.search([('name', '=ilike', f'%{bcode}%')], limit=1)
            if not bm:
                bm = BankMaster.create({'name': bname, 'code': bcode})
            master_banks[bcode] = bm
        print(f'Master Banks Ready: {len(master_banks)}')

        # ----------------------------------------------------
        # COAs (Shared Master)
        # ----------------------------------------------------
        COA = env['sif.coa'].sudo()
        exp_coas = list(COA.search([('active', '=', True), ('parent_id', '!=', False), ('account_type', '=', 'expense')]))
        inc_coas = list(COA.search([('active', '=', True), ('parent_id', '!=', False), ('account_type', '=', 'income')]))
        asset_coas = list(COA.search([('active', '=', True), ('parent_id', '!=', False), ('account_type', '=', 'asset')]))
        liab_coas = list(COA.search([('active', '=', True), ('parent_id', '!=', False), ('account_type', '=', 'liability')]))
        cash_coa = asset_coas[0] if asset_coas else False

        # Academic Year
        AcadYear = env['education.academic.year'].sudo()
        acad_year = AcadYear.search([('code', '=', 'TA2526')], limit=1)
        if not acad_year:
            acad_year = AcadYear.create({
                'name': 'Tahun Ajaran 2025/2026',
                'code': 'TA2526',
                'start_date': '2025-07-01',
                'end_date': '2026-06-30',
                'is_current': True,
                'company_id': companies[0].id,
            })

        emp_names_template = [
            'Budi Santoso', 'Siti Aminah', 'Rudi Hermawan', 'Dewi Lestari',
            'Agus Setiawan', 'Rina Wijaya', 'Eko Prasetyo', 'Maya Indah',
            'Hendra Saputra', 'Nita Anggraini'
        ]

        for company in companies:
            c_id = company.id
            c_name = company.name
            print(f'\n==================================================')
            print(f'>>> POPULATING: {c_name} (Company ID: {c_id})')
            print(f'==================================================')

            # ----------------------------------------------------
            # 1. MODUL KARYAWAN (10 Karyawan per Company)
            # ----------------------------------------------------
            Department = env['hr.department'].sudo()
            dept_code = f'DEPT-{c_id}'
            dept = Department.search([('company_id', '=', c_id)], limit=1)
            if not dept:
                dept = Department.create({
                    'name': f'Departemen Operasional {c_name}',
                    'company_id': c_id,
                    'sif_code': dept_code,
                    'sif_journal_unit_dept': 'pusat',
                })
            elif not dept.sif_code:
                dept.write({'sif_code': dept_code})

            Employee = env['hr.employee'].sudo()
            employees = []
            for idx, ename in enumerate(emp_names_template, start=1):
                full_emp_name = f'{ename} ({c_name})'
                emp = Employee.search([('company_id', '=', c_id), ('name', '=', full_emp_name)], limit=1)
                if not emp:
                    emp = Employee.create({
                        'name': full_emp_name,
                        'company_id': c_id,
                        'department_id': dept.id,
                        'work_email': f'emp{idx}.c{c_id}@sif.or.id',
                    })
                employees.append(emp)
            print(f'  [1/8 Karyawan] OK: {len(employees)} Karyawan Dibuat')

            # ----------------------------------------------------
            # 2. MODUL PAYROLL (10 Slip Payroll per Company)
            # ----------------------------------------------------
            Batch = env['custom.payroll.batch'].sudo()
            batch = Batch.search([('company_id', '=', c_id), ('name', 'ilike', f'Payroll September 2026 {c_name}%')], limit=1)
            if not batch:
                slips_payload = []
                for emp in employees:
                    base_salary = 5000000.0 + random.randint(1, 10) * 500000.0
                    slips_payload.append((0, 0, {
                        'employee_id': emp.id,
                        'company_id': c_id,
                        'total_gaji_pokok': base_salary,
                        'status': 'confirmed',
                    }))
                batch = Batch.create({
                    'name': f'Payroll September 2026 {c_name}',
                    'company_id': c_id,
                    'periode_bulan': '9',
                    'periode_tahun': 2026,
                    'status': 'approved',
                    'slip_ids': slips_payload
                })
            print(f'  [2/8 Payroll] OK: Batch ({batch.name}) dengan {len(batch.slip_ids)} Slip Gaji')

            # ----------------------------------------------------
            # 3. MODUL RKA (10 Anggaran RKA per Company)
            # ----------------------------------------------------
            Rka = env['sif.rka.budget'].sudo()
            # Pick 10 expense COAs deterministically per company with variation
            start_offset = (c_id - 1) * 3
            company_coas = exp_coas[start_offset:start_offset + 10]
            if len(company_coas) < 10:
                company_coas = exp_coas[:10]

            rka_budgets = []
            for idx, coa_item in enumerate(company_coas, start=1):
                r = Rka.search([('company_id', '=', c_id), ('account_id', '=', coa_item.id), ('tahun', '=', '2026')], limit=1)
                budget_val = 30000000.0 + idx * 15000000.0
                if not r:
                    r = Rka.create({
                        'name': f'RKA 2026 - {coa_item.name} ({c_name})',
                        'company_id': c_id,
                        'account_id': coa_item.id,
                        'tahun': '2026',
                        'nilai': budget_val,
                    })
                rka_budgets.append(r)
            print(f'  [3/8 RKA] OK: {len(rka_budgets)} Anggaran RKA Dibuat')

            # ----------------------------------------------------
            # 4. MODUL PPL (13 PPL per Company: 10 Approved + 3 Draft)
            # ----------------------------------------------------
            PPL = env['sifnext.ppl'].sudo()
            ppl_titles = [
                ("Pengadaan ATK Operasional", 3500000.0, "langsung", "cash", "approved"),
                ("Pembayaran Tagihan PLN & PDAM", 12500000.0, "jatuh_tempo", "bank", "approved"),
                ("Sewa Fasilitas Kantor", 25000000.0, "jatuh_tempo", "bank", "approved"),
                ("Biaya Pemeliharaan Gedung", 8500000.0, "langsung", "cash", "approved"),
                ("Pengadaan Laptop Karyawan Baru", 18000000.0, "jatuh_tempo", "bank", "approved"),
                ("Biaya SPPD Tim Operasional", 6200000.0, "langsung", "cash", "approved"),
                ("BBM & Transport Operasional", 4500000.0, "langsung", "cash", "approved"),
                ("Biaya Promosi & Brosur", 11000000.0, "jatuh_tempo", "bank", "approved"),
                ("Biaya Jamuan Rapat Direksi", 2800000.0, "langsung", "cash", "approved"),
                ("Biaya Jasa Notaris & Perijinan", 9500000.0, "jatuh_tempo", "bank", "approved"),
                ("Pengadaan Perangkat Internet (Draft)", 5000000.0, "langsung", "cash", "draft"),
                ("Renovasi Ruangan Rapat (Draft)", 15000000.0, "jatuh_tempo", "bank", "draft"),
                ("Pelatihan & Training Pegawai (Draft)", 7500000.0, "langsung", "bank", "draft"),
            ]

            created_ppls = []
            for p_idx, (title_base, amount, p_term, p_method, target_state) in enumerate(ppl_titles, start=1):
                full_title = f'{title_base} - {c_name}'
                ppl_rec = PPL.search([('company_id', '=', c_id), ('title', '=', full_title)], limit=1)
                rka_ref = rka_budgets[(p_idx - 1) % len(rka_budgets)]
                vendor_ref = vendors[(p_idx - 1) % len(vendors)]

                if not ppl_rec:
                    vals = {
                        'title': full_title,
                        'description': f'Deskripsi {full_title}',
                        'company_id': c_id,
                        'department_id': dept.id,
                        'vendor_id': vendor_ref.id,
                        'payment_term': p_term,
                        'payment_method': p_method,
                        'line_ids': [(0, 0, {
                            'description': full_title,
                            'quantity': 1,
                            'unit_price': amount,
                            'journal_account_id': rka_ref.account_id.id,
                            'rka_id': rka_ref.id,
                        })]
                    }
                    if p_term == 'jatuh_tempo':
                        vals.update({
                            'due_date': fields.Date.today(),
                            'payment_dest_bank': 'BCA',
                            'payment_dest_account_number': f'88300{c_id}{p_idx}',
                            'payment_dest_account_name': vendor_ref.name,
                        })

                    ppl_rec = PPL.create(vals)
                    if target_state == 'approved':
                        ppl_rec._workflow_write({
                            'state': 'approved',
                            'approved_by': env.user.id,
                            'approved_at': fields.Datetime.now()
                        })

                created_ppls.append(ppl_rec)

            appr_count = sum(1 for p in created_ppls if p.state == 'approved')
            draft_count = sum(1 for p in created_ppls if p.state == 'draft')
            print(f'  [4/8 PPL] OK: Total {len(created_ppls)} PPL ({appr_count} Approved, {draft_count} Draft)')

            # ----------------------------------------------------
            # 5. MODUL TRANSAKSI (Daftar Rekening & 10 Input Transaksi)
            # ----------------------------------------------------
            BankAccount = env['transaksi.bank.account'].sudo()
            bank_accounts = []
            account_types_list = [
                ('Rekening Utama', '14000', 'BCA'),
                ('Rekening Operasional', '14001', 'BCA'),
                ('Rekening Payroll', '00900', 'BNI'),
                ('Rekening Deposito', '11200', 'Mandiri'),
                ('Rekening Cadangan', '02000', 'BRI'),
            ]
            for acc_name, acc_prefix, b_code in account_types_list:
                acc_num = f'{acc_prefix}{c_id}88{random.randint(10, 99)}'
                ba = BankAccount.search([('company_id', '=', c_id), ('name', 'ilike', f'{acc_name} {c_name}%')], limit=1)
                if not ba:
                    ba = BankAccount.create({
                        'name': f'{acc_name} {c_name}',
                        'bank_id': master_banks[b_code].id if b_code in master_banks else False,
                        'account_number': acc_num,
                        'account_holder': c_name,
                        'company_id': c_id,
                    })
                bank_accounts.append(ba)

            Tx = env['transaksi.transaction'].sudo()
            tx_records = []
            for t_idx in range(1, 11):
                is_inhouse = (t_idx % 2 != 0)
                ref_num = f'TRX-{c_id}-2026-{t_idx:03d}'
                tx = Tx.search([('company_id', '=', c_id), ('ref_number', '=', ref_num)], limit=1)
                target_state = 'approved' if t_idx <= 8 else 'draft'

                if not tx:
                    if is_inhouse:
                        # Inhouse: sender BCA to receiver BCA (bank_accounts[0] to bank_accounts[1])
                        tx = Tx.create({
                            'transfer_category': 'inhouse',
                            'transfer_type': 'single',
                            'company_id': c_id,
                            'department_id': dept.id,
                            'sender_account_id': bank_accounts[0].id,
                            'single_bank_id': master_banks['BCA'].id,
                            'single_destination_account': bank_accounts[1].account_number,
                            'single_account_holder_name': bank_accounts[1].account_holder,
                            'single_rupiah': 5000000.0 + t_idx * 1000000.0,
                            'ref_number': ref_num,
                            'purpose': 'operational',
                            'state': target_state,
                        })
                    else:
                        # Interbank: sender BCA to recipient BRI / BNI (different bank)
                        tx = Tx.create({
                            'transfer_category': 'interbank',
                            'transfer_type': 'single',
                            'company_id': c_id,
                            'department_id': dept.id,
                            'sender_account_id': bank_accounts[0].id,
                            'single_bank_id': master_banks['BRI'].id,
                            'single_destination_account': f'02000{c_id}99{t_idx}',
                            'single_account_holder_name': f'Vendor Mitra {t_idx}',
                            'single_rupiah': 8000000.0 + t_idx * 1500000.0,
                            'ref_number': ref_num,
                            'purpose': 'purchase',
                            'state': target_state,
                        })
                tx_records.append(tx)
            print(f'  [5/8 Transaksi] OK: {len(bank_accounts)} Rekening & {len(tx_records)} Input Transaksi')

            # ----------------------------------------------------
            # 6. MODUL PENDAPATAN (10 Pendapatan per Company: 8 Approved, 2 Draft)
            # ----------------------------------------------------
            Cat = env['pendapatan.category'].sudo()
            cat_list = [
                (f'Pendapatan Jasa & Operasional {c_name}', f'INC-OPS-{c_id}', inc_coas[0] if inc_coas else False),
                (f'Pendapatan Sewa Fasilitas {c_name}', f'INC-SEW-{c_id}', inc_coas[1] if len(inc_coas) > 1 else inc_coas[0]),
                (f'Pendapatan Bunga & Bagi Hasil {c_name}', f'INC-BNG-{c_id}', inc_coas[2] if len(inc_coas) > 2 else inc_coas[0]),
            ]
            categories = []
            for cname, ccode, coa_ref in cat_list:
                inc_cat = Cat.search([('company_id', '=', c_id), ('code', '=', ccode)], limit=1)
                if not inc_cat and coa_ref:
                    inc_cat = Cat.create({
                        'name': cname,
                        'code': ccode,
                        'company_id': c_id,
                        'coa_pendapatan_id': coa_ref.id,
                        'coa_kas_id': cash_coa.id if cash_coa else False,
                    })
                if inc_cat:
                    categories.append(inc_cat)

            Pend = env['pendapatan.pendapatan'].sudo()
            pend_records = []
            for p_i in range(1, 11):
                desc_text = f'Pendapatan Transaksi #{p_i} ({c_name})'
                p_rec = Pend.search([('company_id', '=', c_id), ('description', '=', desc_text)], limit=1)
                st = 'posted' if p_i <= 8 else 'draft'
                cat_target = categories[(p_i - 1) % len(categories)] if categories else False

                if not p_rec and cat_target:
                    p_rec = Pend.create({
                        'tanggal': fields.Date.today(),
                        'company_id': c_id,
                        'department_id': dept.id,
                        'category_id': cat_target.id,
                        'amount': 15000000.0 + p_i * 2500000.0,
                        'period_label': 'September 2026',
                        'description': desc_text,
                        'state': st,
                    })
                pend_records.append(p_rec)
            print(f'  [6/8 Pendapatan] OK: {len(pend_records)} Input Pendapatan (8 Posted, 2 Draft)')

            # ----------------------------------------------------
            # 7. MODUL AKUNTANSI (10 Jurnal per Company)
            # ----------------------------------------------------
            Jurnal = env['sif.jurnal.entry'].sudo()
            jurnal_entries = []
            for j_i in range(1, 11):
                j_ref = f'JRN-{c_id}-2026-{j_i:02d}'
                j_entry = Jurnal.search([('company_id', '=', c_id), ('ref', '=', j_ref)], limit=1)
                exp_acc = exp_coas[(j_i - 1) % len(exp_coas)]
                amt = 4000000.0 + j_i * 1200000.0

                if not j_entry and exp_acc and cash_coa:
                    j_entry = Jurnal.create({
                        'date': fields.Date.today(),
                        'ref': j_ref,
                        'company_id': c_id,
                        'unit_dept': dept.sif_journal_unit_dept or 'pusat',
                        'state': 'posted',
                        'line_ids': [
                            (0, 0, {
                                'account_id': exp_acc.id,
                                'name': f'Pencatatan Biaya {exp_acc.name} #{j_i}',
                                'debit': amt,
                                'credit': 0.0,
                                'company_id': c_id,
                            }),
                            (0, 0, {
                                'account_id': cash_coa.id,
                                'name': f'Pengeluaran Kas/Rekening #{j_i}',
                                'debit': 0.0,
                                'credit': amt,
                                'company_id': c_id,
                            })
                        ]
                    })
                jurnal_entries.append(j_entry)
            print(f'  [7/8 Akuntansi Jurnal] OK: {len(jurnal_entries)} Jurnal Entry Posted')

            # ----------------------------------------------------
            # 8. MODUL TAGIHAN PENDIDIKAN (10 Tagihan per Company)
            # ----------------------------------------------------
            School = env['education.school'].sudo()
            school = School.search([('company_id', '=', c_id)], limit=1)
            if not school and categories:
                school = School.create({
                    'name': f'Lembaga Pendidikan {c_name}',
                    'code': f'SCH-{c_id}',
                    'level': 'sma',
                    'category_id': categories[0].id,
                    'company_id': c_id,
                })

            ClassRec = env['education.class'].sudo()
            class_rec = ClassRec.search([('school_id', '=', school.id)], limit=1) if school else False
            if not class_rec and school:
                class_rec = ClassRec.create({
                    'name': f'Kelas X-1 {c_name}',
                    'code': f'K-X1-{c_id}',
                    'school_id': school.id,
                    'academic_year_id': acad_year.id,
                })

            StudentRec = env['education.student'].sudo()
            ParentRec = env['education.parent'].sudo()
            BillRec = env['education.bill'].sudo()
            education_bills = []

            for s_i in range(1, 11):
                parent_rec = ParentRec.search([('company_id', '=', c_id), ('name', '=', f'Wali Murid #{s_i} ({c_name})')], limit=1)
                if not parent_rec:
                    parent_rec = ParentRec.create({
                        'name': f'Wali Murid #{s_i} ({c_name})',
                        'company_id': c_id,
                        'phone': f'0812999{c_id}{s_i:02d}',
                        'email': f'wali{s_i}.c{c_id}@gmail.com',
                    })

                student_rec = StudentRec.search([('company_id', '=', c_id), ('name', '=', f'Siswa #{s_i} ({c_name})')], limit=1)
                if not student_rec and school and class_rec:
                    student_rec = StudentRec.create({
                        'name': f'Siswa #{s_i} ({c_name})',
                        'student_id_number': f'NISN{c_id}99{s_i:02d}',
                        'company_id': c_id,
                        'school_id': school.id,
                        'class_id': class_rec.id,
                        'parent_id': parent_rec.id,
                    })

                if student_rec and school and class_rec:
                    bill_rec = BillRec.search([('company_id', '=', c_id), ('student_id', '=', student_rec.id)], limit=1)
                    st_bill = 'unpaid' if s_i <= 7 else ('verified' if s_i <= 9 else 'draft')
                    b_type = 'spp' if s_i % 2 != 0 else 'ukt'
                    if not bill_rec:
                        bill_rec = BillRec.create({
                            'company_id': c_id,
                            'school_id': school.id,
                            'student_id': student_rec.id,
                            'class_id': class_rec.id,
                            'academic_year_id': acad_year.id,
                            'bill_type': b_type,
                            'month': f'{((s_i - 1) % 12) + 1:02d}',
                            'year': 2026,
                            'due_date': fields.Date.today(),
                            'amount': 2500000.0 + s_i * 500000.0,
                            'state': st_bill,
                        })
                    education_bills.append(bill_rec)

            print(f'  [8/8 Tagihan Pendidikan] OK: {len(education_bills)} Tagihan Pendidikan')

        cr.commit()
        print('\n==================================================')
        print('SUCCESS: ALL DUMMY DATA FOR 5 COMPANIES REGENERATED!')
        print('==================================================')

if __name__ == '__main__':
    run()
