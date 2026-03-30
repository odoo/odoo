# -*- coding: utf-8 -*-
"""Comprehensive tests for the WPS text-file wizard and bank-account grouping.

Covers:
  - Wizard field defaults & constraints
  - Header record: 300-char fixed-width, field positions, value date duplication
  - Detail records: amount in halalas, breakdown fields, trailing padding
  - Bank-account grouping: employee-level, batch-level fallback, error on missing
  - Multi-bank-account batches → separate files
  - Edge cases: zero-net slips skipped, special chars in names, long IBANs
  - action_open_wps_wizard returns correct window action
  - action_export_bank_file (Excel) respects grouping
"""
from datetime import date, datetime

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestWpsFileWizard(TransactionCase):
    """Tests for ksw.wps.file.wizard and hr.payslip.run grouping logic."""

    LINE_LEN = 300

    # ================================================================
    # setUp — reusable fixtures
    # ================================================================

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Company & partner ──
        cls.company = cls.env.company
        cls.company_partner = cls.company.partner_id

        # ── Banks ──
        cls.bank_rajhi = cls.env['res.bank'].create({
            'name': 'Al Rajhi Bank',
            'bic': 'RJHISARI',
        })
        cls.bank_anb = cls.env['res.bank'].create({
            'name': 'Arab National Bank',
            'bic': 'ARNBSARI',
        })

        # ── Company bank accounts (source / debit accounts) ──
        cls.company_bank_1 = cls.env['res.partner.bank'].create({
            'acc_number': 'SA71800005786080100T0001',
            'partner_id': cls.company_partner.id,
            'bank_id': cls.bank_rajhi.id,
            'x_wps_cic_number': '1389678',
            'x_wps_debit_account': 'SA7180000578608010033217',
            'x_wps_mol_id': '004-110457',
        })
        cls.company_bank_2 = cls.env['res.partner.bank'].create({
            'acc_number': 'SA99304001080999999T0002',
            'partner_id': cls.company_partner.id,
            'bank_id': cls.bank_anb.id,
            'x_wps_cic_number': '9999999',
            'x_wps_debit_account': 'SA9930400108099999990011',
            'x_wps_mol_id': '004-999999',
        })

        # ── Work schedule (minimal) ──
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'WPS Test Calendar',
            'tz': 'Asia/Riyadh',
        })

        # ── Salary rule category refs ──
        cls.cat_basic = cls.env.ref('om_hr_payroll.BASIC')
        cls.cat_hra = cls.env.ref('om_hr_payroll.HRA')
        cls.cat_gross = cls.env.ref('om_hr_payroll.GROSS')
        cls.cat_ded = cls.env.ref('om_hr_payroll.DED')
        cls.cat_net = cls.env.ref('om_hr_payroll.NET')

        # ── Dummy salary rule (required FK for payslip lines) ──
        cls.rule_basic = cls._get_or_create_rule(cls, 'BASIC', cls.cat_basic)
        cls.rule_hra = cls._get_or_create_rule(cls, 'HRA', cls.cat_hra)
        cls.rule_gross = cls._get_or_create_rule(cls, 'GROSS', cls.cat_gross)
        cls.rule_ded = cls._get_or_create_rule(cls, 'ATTDED', cls.cat_ded)
        cls.rule_net = cls._get_or_create_rule(cls, 'NET', cls.cat_net)

        # ── Employees ──
        cls.emp_1 = cls._create_employee(
            cls, 'KADEM ALI KADEM ALAHMER', '283',
            '1007478256', cls.bank_rajhi,
            'SA26304001080939089T0001',
        )
        cls.emp_2 = cls._create_employee(
            cls, 'MOHAMMED AMIN GHANI ALSHAIBANI', '001',
            '2023599638', cls.bank_rajhi,
            'SA25200000031338984T0002',
        )
        cls.emp_3 = cls._create_employee(
            cls, 'NABIL ALI JUMAH', '003',
            '2024116150', cls.bank_anb,
            'SA06304001080601281T0003',
        )

        # ── Assign company bank account to employees ──
        cls.emp_1.sudo().write({
            'x_salary_bank_account_id': cls.company_bank_1.id,
        })
        cls.emp_2.sudo().write({
            'x_salary_bank_account_id': cls.company_bank_1.id,
        })
        cls.emp_3.sudo().write({
            'x_salary_bank_account_id': cls.company_bank_2.id,
        })

        # ── Payslip batch ──
        cls.batch = cls.env['hr.payslip.run'].create({
            'name': 'March 2026',
            'date_start': date(2026, 3, 1),
            'date_end': date(2026, 3, 31),
        })

        # ── Payslips with manually-set salary lines ──
        cls.slip_1 = cls._create_payslip(
            cls, cls.emp_1, cls.batch,
            basic=9880, hra=2000, gross=13880, deductions=4059, net=9821,
        )
        cls.slip_2 = cls._create_payslip(
            cls, cls.emp_2, cls.batch,
            basic=12000, hra=0, gross=14500, deductions=0, net=14500,
        )
        cls.slip_3 = cls._create_payslip(
            cls, cls.emp_3, cls.batch,
            basic=3500, hra=700, gross=4400, deductions=0, net=4400,
        )

    # ── Factory helpers ──

    def _get_or_create_rule(self, code, category):
        rule = self.env['hr.salary.rule'].search(
            [('code', '=', code)], limit=1,
        )
        if not rule:
            rule = self.env['hr.salary.rule'].create({
                'name': code,
                'code': code,
                'category_id': category.id,
                'sequence': 100,
                'condition_select': 'none',
                'amount_select': 'fix',
                'amount_fix': 0,
            })
        return rule

    def _create_employee(self, name, barcode, id_number, bank, iban):
        emp = self.env['hr.employee'].create({
            'name': name,
            'barcode': barcode,
            'identification_id': id_number,
            'resource_calendar_id': self.calendar.id,
        })
        # Employee personal bank account
        bank_acc = self.env['res.partner.bank'].create({
            'acc_number': iban,
            'partner_id': emp.work_contact_id.id,
            'bank_id': bank.id,
        })
        # Link to employee's bank_account_ids (M2M) so primary_bank_account_id computes
        emp.sudo().write({'bank_account_ids': [(4, bank_acc.id)]})
        return emp

    def _create_payslip(self, employee, batch, basic, hra, gross,
                        deductions, net):
        slip = self.env['hr.payslip'].create({
            'name': 'Slip %s' % employee.name,
            'employee_id': employee.id,
            'date_from': batch.date_start,
            'date_to': batch.date_end,
            'payslip_run_id': batch.id,
            'version_id': employee.current_version_id.id,
        })
        # Create payslip lines directly (bypass compute)
        Line = self.env['hr.payslip.line']
        version_id = employee.current_version_id.id

        def _mk(rule, amount):
            Line.create({
                'slip_id': slip.id,
                'salary_rule_id': rule.id,
                'code': rule.code,
                'name': rule.name,
                'category_id': rule.category_id.id,
                'employee_id': employee.id,
                'version_id': version_id,
                'amount': amount,
                'quantity': 1,
                'rate': 100,
                'sequence': rule.sequence,
            })

        _mk(self.rule_basic, basic)
        _mk(self.rule_hra, hra)
        _mk(self.rule_gross, gross)
        if deductions:
            _mk(self.rule_ded, -abs(deductions))
        _mk(self.rule_net, net)
        return slip

    def _make_wizard(self, batch=None, value_date=None):
        """Create a wizard instance for the given batch."""
        batch = batch or self.batch
        return self.env['ksw.wps.file.wizard'].create({
            'payslip_run_id': batch.id,
            'value_date': value_date or date(2026, 3, 30),
        })

    # ================================================================
    # Tests — Wizard basics
    # ================================================================

    def test_wizard_default_date(self):
        """Value date defaults to today."""
        wiz = self.env['ksw.wps.file.wizard'].with_context(
            default_payslip_run_id=self.batch.id,
        ).create({})
        self.assertEqual(wiz.value_date, date.today())

    def test_wizard_requires_batch(self):
        """payslip_run_id is mandatory — DB raises on null."""
        from psycopg2 import IntegrityError
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env['ksw.wps.file.wizard'].create({
                'value_date': date(2026, 3, 30),
            })

    # ================================================================
    # Tests — action_open_wps_wizard
    # ================================================================

    def test_action_open_wps_wizard(self):
        """Batch button returns act_window for the wizard with correct context."""
        action = self.batch.action_open_wps_wizard()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'ksw.wps.file.wizard')
        self.assertEqual(action['target'], 'new')
        self.assertEqual(
            action['context']['default_payslip_run_id'], self.batch.id,
        )

    # ================================================================
    # Tests — Bank-account grouping
    # ================================================================

    def test_group_by_employee_bank_account(self):
        """Slips grouped by employee's x_salary_bank_account_id."""
        groups = self.batch._group_slips_by_bank_account()
        # emp_1 and emp_2 → company_bank_1 ; emp_3 → company_bank_2
        self.assertIn(self.company_bank_1, groups)
        self.assertIn(self.company_bank_2, groups)
        self.assertEqual(len(groups[self.company_bank_1]), 2)
        self.assertEqual(len(groups[self.company_bank_2]), 1)

    def test_group_fallback_to_batch_bank(self):
        """When employee has no bank, falls back to batch-level bank."""
        # Clear employee-level bank for emp_3
        self.emp_3.sudo().write({'x_salary_bank_account_id': False})
        self.batch.write({'x_salary_bank_account_id': self.company_bank_1.id})

        groups = self.batch._group_slips_by_bank_account()
        # All three should now be under company_bank_1
        self.assertIn(self.company_bank_1, groups)
        self.assertEqual(len(groups[self.company_bank_1]), 3)

        # Restore
        self.emp_3.sudo().write({
            'x_salary_bank_account_id': self.company_bank_2.id,
        })
        self.batch.write({'x_salary_bank_account_id': False})

    def test_group_no_bank_collected_under_empty(self):
        """Employees with no bank at any level → empty-recordset key."""
        self.emp_3.sudo().write({'x_salary_bank_account_id': False})
        self.batch.write({'x_salary_bank_account_id': False})

        groups = self.batch._group_slips_by_bank_account()
        empty_key = self.env['res.partner.bank']
        self.assertIn(empty_key, groups)
        self.assertIn(self.slip_3, groups[empty_key])

        # Restore
        self.emp_3.sudo().write({
            'x_salary_bank_account_id': self.company_bank_2.id,
        })

    # ================================================================
    # Tests — Error handling
    # ================================================================

    def test_error_empty_batch(self):
        """Wizard raises if batch has no payslips."""
        empty_batch = self.env['hr.payslip.run'].create({
            'name': 'Empty', 'date_start': date(2026, 3, 1),
            'date_end': date(2026, 3, 31),
        })
        wiz = self._make_wizard(batch=empty_batch)
        with self.assertRaises(UserError):
            wiz.action_generate()

    def test_error_no_bank_account(self):
        """Wizard raises listing employees with no bank account."""
        self.emp_3.sudo().write({'x_salary_bank_account_id': False})
        self.batch.write({'x_salary_bank_account_id': False})

        wiz = self._make_wizard()
        with self.assertRaises(UserError) as cm:
            wiz.action_generate()
        self.assertIn('NABIL ALI JUMAH', str(cm.exception))

        # Restore
        self.emp_3.sudo().write({
            'x_salary_bank_account_id': self.company_bank_2.id,
        })

    def test_error_no_positive_net(self):
        """Wizard raises if all slips have zero net."""
        zero_batch = self.env['hr.payslip.run'].create({
            'name': 'Zero', 'date_start': date(2026, 3, 1),
            'date_end': date(2026, 3, 31),
            'x_salary_bank_account_id': self.company_bank_1.id,
        })
        emp = self._create_employee(
            'ZERO GUY', '999', '9999999999',
            self.bank_rajhi, 'SA0000000000000000000000',
        )
        emp.sudo().write({
            'x_salary_bank_account_id': self.company_bank_1.id,
        })
        self._create_payslip(
            emp, zero_batch,
            basic=0, hra=0, gross=0, deductions=0, net=0,
        )
        wiz = self._make_wizard(batch=zero_batch)
        with self.assertRaises(UserError):
            wiz.action_generate()

    # ================================================================
    # Tests — Header record format
    # ================================================================

    def test_header_line_length(self):
        """Header record is exactly 300 characters."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        header = content.split('\n')[0]
        self.assertEqual(len(header), self.LINE_LEN)

    def test_header_starts_with_filler_and_G(self):
        """Header begins with 12 zeros and 'G'."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        header = content.split('\n')[0]
        self.assertEqual(header[:12], '0' * 12)
        self.assertEqual(header[12], 'G')

    def test_header_value_date_duplicated(self):
        """Value date appears twice at positions 13-20 and 21-28."""
        wiz = self._make_wizard(value_date=date(2026, 3, 30))
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        header = content.split('\n')[0]
        self.assertEqual(header[13:21], '20260330')
        self.assertEqual(header[21:29], '20260330')

    def test_header_total_amount_13_chars(self):
        """Total amount is 13-char zero-padded SAR at position 29-41."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(
            self.company_bank_1, self.slip_1 | self.slip_2,
        )
        header = content.split('\n')[0]
        # emp_1 net=9821, emp_2 net=14500 → total=24321
        expected_total = str(9821 + 14500).zfill(13)
        self.assertEqual(header[29:42], expected_total)

    def test_header_record_count(self):
        """Record count is 10-char zero-padded at position 42-51."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(
            self.company_bank_1, self.slip_1 | self.slip_2,
        )
        header = content.split('\n')[0]
        self.assertEqual(header[42:52], '0000000002')

    def test_header_debit_iban(self):
        """Debit IBAN is 24-char left-justified at position 52-75."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        header = content.split('\n')[0]
        expected_iban = self.company_bank_1.x_wps_debit_account
        self.assertEqual(header[52:76], expected_iban.ljust(24)[:24])

    def test_header_currency_and_file_ref(self):
        """SAR at 76-78, E01 at 79-81."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        header = content.split('\n')[0]
        self.assertEqual(header[76:79], 'SAR')
        self.assertEqual(header[79:82], 'E01')

    def test_header_cic_number(self):
        """CIC is 15-char zero-padded after creation time + batch."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        header = content.split('\n')[0]
        # position after creation_date(8)+time(6)+batch(2) = 82+16 = 98
        cic_pos = 98
        self.assertEqual(header[cic_pos:cic_pos + 15], '000000001389678')

    def test_header_mol_id(self):
        """MOL ID is 10-char left-justified at position 113."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        header = content.split('\n')[0]
        self.assertEqual(header[113:123], '004-110457')

    def test_header_payment_type(self):
        """PAYR appears in the header."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        header = content.split('\n')[0]
        self.assertIn('PAYR', header)

    def test_header_ends_with_N(self):
        """Header ends with 'N'."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        header = content.split('\n')[0]
        self.assertEqual(header[-1], 'N')

    # ================================================================
    # Tests — Detail record format
    # ================================================================

    def test_detail_line_length(self):
        """Every detail line is exactly 300 characters."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(
            self.company_bank_1, self.slip_1 | self.slip_2,
        )
        lines = [l for l in content.split('\n') if l]
        for line in lines[1:]:  # skip header
            self.assertEqual(
                len(line), self.LINE_LEN,
                'Detail line length mismatch: %d' % len(line),
            )

    def test_detail_employee_ref(self):
        """First 12 chars are zero-padded employee barcode."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        self.assertEqual(detail[:12], '000000000283')

    def test_detail_bank_code(self):
        """Chars 13-16 are the first 4 of the SWIFT/BIC."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        self.assertEqual(detail[12:16], 'RJHI')

    def test_detail_employee_iban(self):
        """Employee IBAN is 24-char at position 25-48."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        bank = self.emp_1.sudo().primary_bank_account_id
        self.assertTrue(bank, 'Employee should have a primary bank account')
        iban = bank.acc_number.replace(' ', '')
        self.assertEqual(detail[24:48], iban.ljust(24)[:24])

    def test_detail_employee_name_uppercase(self):
        """Employee name is uppercase, 50-char padded, at position 60-109."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        name_field = detail[59:109]
        self.assertEqual(len(name_field), 50)
        self.assertTrue(name_field.startswith('KADEM ALI KADEM ALAHMER'))
        # Rest is spaces
        self.assertEqual(name_field.strip(), 'KADEM ALI KADEM ALAHMER')

    def test_detail_net_amount_halalas(self):
        """Net amount at pos 110-124 is 15-char zero-padded halalas."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        # 9821 SAR = 982100 halalas
        self.assertEqual(detail[109:124], '000000000982100')

    def test_detail_employee_id(self):
        """Employee national/iqama ID at pos 125-134 is 10-char zero-padded."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        self.assertEqual(detail[124:134], '1007478256')

    def test_detail_basic_halalas(self):
        """Basic salary at pos 140-152 is 13-char halalas."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        # basic=9880 SAR → 988000 halalas
        self.assertEqual(detail[139:152], '0000000988000')

    def test_detail_hra_halalas(self):
        """HRA at pos 153-164 is 12-char halalas."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        # hra=2000 SAR → 200000 halalas
        self.assertEqual(detail[152:164], '000000200000')

    def test_detail_other_earnings_halalas(self):
        """Other earnings at pos 165-176 is 12-char halalas."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        # other = gross - basic - hra = 13880 - 9880 - 2000 = 2000 SAR → 200000
        self.assertEqual(detail[164:176], '000000200000')

    def test_detail_deductions_halalas(self):
        """Deductions at pos 177-188 is 12-char halalas."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        # deductions=4059 SAR → 405900 halalas
        self.assertEqual(detail[176:188], '000000405900')

    def test_detail_currency_field(self):
        """SAR at pos 189-191."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]
        self.assertEqual(detail[188:191], 'SAR')

    def test_detail_salary_formula(self):
        """basic + hra + other - deductions == net (all in halalas)."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, self.slip_1)
        detail = content.split('\n')[1]

        net_h = int(detail[109:124])
        basic_h = int(detail[139:152])
        hra_h = int(detail[152:164])
        other_h = int(detail[164:176])
        ded_h = int(detail[176:188])

        self.assertEqual(basic_h + hra_h + other_h - ded_h, net_h)

    # ================================================================
    # Tests — Full file generation (action_generate)
    # ================================================================

    def test_action_generate_returns_download_url(self):
        """action_generate returns an ir.actions.act_url for download."""
        wiz = self._make_wizard()
        result = wiz.action_generate()
        self.assertEqual(result['type'], 'ir.actions.act_url')
        self.assertIn('/web/content/', result['url'])
        self.assertIn('download=true', result['url'])

    def test_action_generate_creates_attachment(self):
        """An ir.attachment is created for the batch."""
        wiz = self._make_wizard()
        before = self.env['ir.attachment'].search_count([
            ('res_model', '=', 'hr.payslip.run'),
            ('res_id', '=', self.batch.id),
        ])
        wiz.action_generate()
        after = self.env['ir.attachment'].search_count([
            ('res_model', '=', 'hr.payslip.run'),
            ('res_id', '=', self.batch.id),
        ])
        # Two bank accounts → two attachments
        self.assertEqual(after - before, 2)

    def test_action_generate_filename(self):
        """Attachment filename includes batch name and value date."""
        # Put all employees on same bank to get one file
        self.emp_3.sudo().write({
            'x_salary_bank_account_id': self.company_bank_1.id,
        })
        wiz = self._make_wizard(value_date=date(2026, 3, 30))
        wiz.action_generate()
        att = self.env['ir.attachment'].search([
            ('res_model', '=', 'hr.payslip.run'),
            ('res_id', '=', self.batch.id),
            ('name', 'like', 'WPS_%'),
        ], order='id desc', limit=1)
        self.assertIn('March_2026', att.name)
        self.assertIn('20260330', att.name)
        self.assertTrue(att.name.endswith('.txt'))

        # Restore
        self.emp_3.sudo().write({
            'x_salary_bank_account_id': self.company_bank_2.id,
        })

    # ================================================================
    # Tests — Zero-net payslips are skipped
    # ================================================================

    def test_zero_net_slips_excluded(self):
        """Payslips with NET=0 are excluded from the file."""
        zero_emp = self._create_employee(
            'ZERO SALARY', '000', '0000000000',
            self.bank_rajhi, 'SA0000000000000000000000',
        )
        zero_emp.sudo().write({
            'x_salary_bank_account_id': self.company_bank_1.id,
        })
        self._create_payslip(
            zero_emp, self.batch,
            basic=0, hra=0, gross=0, deductions=0, net=0,
        )
        wiz = self._make_wizard()
        content = wiz._build_wps_text(
            self.company_bank_1,
            self.batch.slip_ids.filtered(
                lambda s: s.employee_id.sudo().x_salary_bank_account_id
                == self.company_bank_1
            ),
        )
        lines = [l for l in content.split('\n') if l]
        # Header + 2 employees (emp_1, emp_2), zero employee excluded
        self.assertEqual(len(lines), 3)
        # Header count field should also say 2
        header = lines[0]
        self.assertEqual(header[42:52], '0000000002')

    # ================================================================
    # Tests — Multi-bank generates separate sections
    # ================================================================

    def test_multi_bank_separate_texts(self):
        """Each bank account generates its own content via _build_wps_text."""
        wiz = self._make_wizard()
        groups = self.batch._group_slips_by_bank_account()
        self.assertEqual(len(groups), 2)

        for bank_account, slips in groups.items():
            content = wiz._build_wps_text(bank_account, slips)
            lines = [l for l in content.split('\n') if l]
            # Header + detail lines
            self.assertGreater(len(lines), 1)
            # Header has correct bank's CIC
            header = lines[0]
            cic = bank_account.x_wps_cic_number
            self.assertIn(cic.zfill(15), header)

    # ================================================================
    # Tests — Sorting
    # ================================================================

    def test_detail_rows_sorted_by_name(self):
        """Detail rows are sorted alphabetically by employee name."""
        wiz = self._make_wizard()
        content = wiz._build_wps_text(
            self.company_bank_1, self.slip_1 | self.slip_2,
        )
        lines = [l for l in content.split('\n') if l]
        details = lines[1:]
        self.assertEqual(len(details), 2)
        # KADEM < MOHAMMED alphabetically
        name_1 = details[0][59:109].strip()
        name_2 = details[1][59:109].strip()
        self.assertLess(name_1, name_2)

    # ================================================================
    # Tests — Edge cases
    # ================================================================

    def test_name_truncated_to_50(self):
        """Names longer than 50 chars are truncated."""
        long_emp = self._create_employee(
            'A' * 60, '777', '7777777777',
            self.bank_rajhi, 'SA1111111111111111111111',
        )
        long_emp.sudo().write({
            'x_salary_bank_account_id': self.company_bank_1.id,
        })
        slip = self._create_payslip(
            long_emp, self.batch,
            basic=1000, hra=0, gross=1000, deductions=0, net=1000,
        )
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, slip)
        detail = content.split('\n')[1]
        name_field = detail[59:109]
        self.assertEqual(len(name_field), 50)
        self.assertEqual(name_field, 'A' * 50)

    def test_non_numeric_barcode_defaults_zero(self):
        """Non-numeric barcode → employee ref all zeros."""
        emp = self._create_employee(
            'ALPHA REF', 'ABC', '1111111111',
            self.bank_rajhi, 'SA2222222222222222222222',
        )
        emp.sudo().write({
            'x_salary_bank_account_id': self.company_bank_1.id,
        })
        slip = self._create_payslip(
            emp, self.batch,
            basic=500, hra=0, gross=500, deductions=0, net=500,
        )
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, slip)
        detail = content.split('\n')[1]
        self.assertEqual(detail[:12], '0' * 12)

    def test_no_employee_bank_uses_spaces(self):
        """If employee has no personal bank account, fields are space/zero padded."""
        emp = self.env['hr.employee'].create({
            'name': 'NO BANK EMP',
            'barcode': '888',
            'identification_id': '8888888888',
            'resource_calendar_id': self.calendar.id,
        })
        emp.sudo().write({
            'x_salary_bank_account_id': self.company_bank_1.id,
        })
        slip = self._create_payslip(
            emp, self.batch,
            basic=1000, hra=0, gross=1000, deductions=0, net=1000,
        )
        wiz = self._make_wizard()
        content = wiz._build_wps_text(self.company_bank_1, slip)
        detail = content.split('\n')[1]
        # Bank code → 4 spaces
        self.assertEqual(detail[12:16], '    ')
        # IBAN → 24 spaces
        self.assertEqual(detail[24:48], ' ' * 24)

    # ================================================================
    # Tests — Excel export grouping (action_export_bank_file)
    # ================================================================

    def test_excel_export_error_no_slips(self):
        """Excel export raises on empty batch."""
        empty = self.env['hr.payslip.run'].create({
            'name': 'Empty', 'date_start': date(2026, 3, 1),
            'date_end': date(2026, 3, 31),
        })
        with self.assertRaises(UserError):
            empty.action_export_bank_file()

    def test_excel_export_error_no_bank(self):
        """Excel export raises listing employees with no bank account."""
        self.emp_3.sudo().write({'x_salary_bank_account_id': False})
        self.batch.write({'x_salary_bank_account_id': False})
        with self.assertRaises(UserError) as cm:
            self.batch.action_export_bank_file()
        self.assertIn('NABIL', str(cm.exception))
        # Restore
        self.emp_3.sudo().write({
            'x_salary_bank_account_id': self.company_bank_2.id,
        })

    def test_excel_export_returns_download(self):
        """Excel export returns an act_url for download."""
        result = self.batch.action_export_bank_file()
        self.assertEqual(result['type'], 'ir.actions.act_url')
        self.assertIn('/web/content/', result['url'])

    # ================================================================
    # Tests — Helper methods
    # ================================================================

    def test_sar_to_halalas(self):
        """_sar_to_halalas rounds correctly."""
        wiz = self._make_wizard()
        self.assertEqual(wiz._sar_to_halalas(9821), 982100)
        self.assertEqual(wiz._sar_to_halalas(0), 0)
        self.assertEqual(wiz._sar_to_halalas(100.505), 10050)  # banker's rounding
        self.assertEqual(wiz._sar_to_halalas(100.555), 10056)
        self.assertEqual(wiz._sar_to_halalas(0.01), 1)

    def test_pr_padding(self):
        """_pr pads and truncates correctly."""
        wiz = self._make_wizard()
        self.assertEqual(wiz._pr('ABC', 5), 'ABC  ')
        self.assertEqual(wiz._pr('ABCDEF', 4), 'ABCD')
        self.assertEqual(wiz._pr('', 3), '   ')
        self.assertEqual(wiz._pr(None, 3), '   ')

    def test_pz_zero_padding(self):
        """_pz zero-pads and truncates correctly."""
        wiz = self._make_wizard()
        self.assertEqual(wiz._pz(42, 6), '000042')
        self.assertEqual(wiz._pz(0, 3), '000')
        self.assertEqual(wiz._pz(123456, 4), '1234')  # truncates from right

    def test_swift4_extraction(self):
        """_swift4 returns first 4 chars of BIC."""
        wiz = self._make_wizard()
        self.assertEqual(wiz._swift4(self.company_bank_1), 'RJHI')
        self.assertEqual(wiz._swift4(self.company_bank_2), 'ARNB')











