from odoo import Command, fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLibrosExport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='es_pymes'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.maxDiff = None
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.es').id,
            'name': 'Los Pollos Hermanos',
            'vat': 'ESA12345674',
            'l10n_es_reports_iae_group': 'A036533',
        })
        cls.partner_a = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.es').id,
            'name': 'Esperado Espagnole',
            'vat': 'ES59962470K',
        })
        cls.partner_us = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.us').id,
            'name': 'US Company',
            'vat': 'US66655598K',
        })
        cls.partner_fr = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.fr').id,
            'name': 'French Company',
            'vat': 'FR23334175221',
        })
        company_id = cls.company_data['company'].id
        cls.tax_21 = cls.env.ref(f'account.{company_id}_account_tax_template_s_iva21b')
        cls.tax_10 = cls.env.ref(f'account.{company_id}_account_tax_template_p_iva10_ic_bc')
        cls.tax_21_surcharge = cls.env.ref(f'account.{company_id}_account_tax_template_s_req52')
        cls.tax_10_surcharge = cls.env.ref(f'account.{company_id}_account_tax_template_p_req014')
        cls.tax_dua_ignore = cls.env.ref(f'account.{company_id}_account_tax_template_p_iva_isub')
        cls.tax_dua_group = cls.env.ref(f'account.{company_id}_account_tax_template_p_iva10_ibc_group')
        cls.tax_dua_rentencion = cls.env.ref(f'account.{company_id}_account_tax_template_p_irpf20')

    def get_libros_sheet_line_vals(self):
        report = self.env.ref('account.generic_tax_report')
        options = self._generate_options(report, fields.Date.from_string('2019-01-01'), fields.Date.from_string('2019-12-31'))
        domain = report._get_options_domain(options, 'strict_range') + [('move_type', '!=', 'entry')]
        lines = self.env['account.move.line'].search(domain)
        return self.env['l10n_es.libros.registro.export.handler']._get_sheet_line_vals(lines)

    def get_amount_vals(self, line_vals):
        amount_fields = ('total_amount', 'base_amount', 'tax_rate', 'taxed_amount', 'surcharge_type', 'surcharge_fee',
                         'income_computable', 'expense_deductible', 'tax_deductible', 'withholding_type', 'withholding_amount')
        amount_vals = {field: value for field, value in line_vals.items() if field in amount_fields}
        return amount_vals

    def test_libros_export_line_vals(self):
        self.init_invoice('out_invoice', amounts=[1000], invoice_date=fields.Date.from_string('2019-10-12'), taxes=self.tax_21, post=True)
        self.init_invoice('in_invoice', amounts=[1000], invoice_date=fields.Date.from_string('2019-06-15'), taxes=self.tax_21, post=True)
        inc_line_vals, exp_line_vals = self.get_libros_sheet_line_vals()
        line_vals = [inc_line_vals[m][t] for m in inc_line_vals for t in inc_line_vals[m]][0]
        self.assertDictEqual(line_vals, {
            'activity_code': 'A', 'activity_group': '6533', 'activity_type': '03', 'base_amount': '1000.00',
            'billing_agreement': '', 'date_expedition': '10/12/2019', 'date_transaction': '', 'external_reference': '',
            'income_computable': '1000.00', 'income_concept': 'I01', 'invoice_final_number': '',
            'invoice_number': 'INV/2019/00001', 'invoice_series': '', 'invoice_type': 'F1', 'operation_code': '01',
            'operation_exempt': '', 'operation_qualification': 'S1', 'partner_name': 'Esperado Espagnole',
            'partner_nif_code': '', 'partner_nif_id': '59962470K', 'partner_nif_type': '', 'payment_amount': '',
            'payment_date': '', 'payment_medium': '', 'payment_medium_id': '', 'period': '4T', 'property_reference': '',
            'property_situation': '', 'surcharge_fee': '0.00', 'surcharge_type': '0.00', 'tax_rate': '21.00',
            'taxed_amount': '210.00', 'total_amount': '1210.00', 'withholding_amount': '0.00', 'withholding_type': '0.00',
            'year': 2019,
        })
        line_vals = [exp_line_vals[m][t] for m in exp_line_vals for t in exp_line_vals[m]][0]
        self.assertDictEqual(line_vals, {
            'activity_code': 'A', 'activity_group': '6533', 'activity_type': '03', 'base_amount': '1000.00',
            'billing_agreement': '', 'date_expedition': '06/15/2019', 'date_reception': '06/15/2019',
            'date_transaction': '', 'deductible_later': '', 'deduction_period': '', 'deduction_year': '',
            'expense_concept': 'G01', 'expense_deductible': '1000.00', 'expense_final_number': '',
            'expense_series_number': 'BILL/2019/06/0001', 'external_reference': '', 'investment_good': 'N',
            'invoice_type': 'F1', 'isp_taxable': 'N', 'operation_code': '01', 'partner_name': 'Esperado Espagnole',
            'partner_nif_code': '', 'partner_nif_id': '59962470K', 'partner_nif_type': '', 'payment_amount': '',
            'payment_date': '', 'payment_medium': '', 'payment_medium_id': '', 'period': '2T', 'property_reference': '',
            'property_situation': '', 'reception_number': '', 'reception_number_final': '', 'surcharge_fee': '0.00',
            'surcharge_type': '0.00', 'tax_deductible': '210.00', 'tax_rate': '21.00', 'taxed_amount': '210.00',
            'total_amount': '1210.00', 'withholding_amount': '0.00', 'withholding_type': '0.00', 'year': 2019,
        })

    def test_libros_export_one_line_multi_tax(self):
        """ This test highlights a current limitation. When 2 taxes of the same type are used
        on an invoice line, only the last of them is displayed in the "tax_rate" column.
        There is no column to display the second tax rate.
        """
        company_id = self.company_data['company'].id
        tax_10 = self.env.ref(f'account.{company_id}_account_tax_template_s_iva10b')
        self.init_invoice('out_invoice', amounts=[500], post=True, taxes=[self.tax_21, tax_10])
        inc_line_vals = self.get_libros_sheet_line_vals()[0]
        line_vals_list = [inc_line_vals[m][t] for m in inc_line_vals for t in inc_line_vals[m]]
        self.assertEqual(len(line_vals_list), 1)
        amount_vals = self.get_amount_vals(line_vals_list[0])
        self.assertDictEqual(amount_vals, {
            'income_computable': '500.00', 'total_amount': '655.00', 'base_amount': '500.00', 'tax_rate': '10.00',
            'taxed_amount': '155.00', 'surcharge_type': '0.00', 'surcharge_fee': '0.00', 'withholding_type': '0.00',
            'withholding_amount': '0.00',
        })

    def test_libros_export_multi_line_one_tax(self):
        self.init_invoice('out_invoice', amounts=[500, 700], post=True, taxes=self.tax_21)
        inc_line_vals = self.get_libros_sheet_line_vals()[0]
        move_idx = [m for m in inc_line_vals][0]
        self.assertEqual(len(inc_line_vals[move_idx]), 1)

    def test_libros_export_with_surcharge(self):
        self.init_invoice('out_invoice', amounts=[500], post=True, taxes=[self.tax_21, self.tax_21_surcharge])
        inc_line_vals = self.get_libros_sheet_line_vals()[0]
        line_vals_list = [inc_line_vals[m][t] for m in inc_line_vals for t in inc_line_vals[m]]
        self.assertEqual(len(line_vals_list), 1)
        amount_vals = self.get_amount_vals(line_vals_list[0])
        self.assertDictEqual(amount_vals, {
            'income_computable': '500.00', 'total_amount': '631.00', 'base_amount': '500.00', 'tax_rate': '21.00',
            'taxed_amount': '105.00', 'surcharge_type': '5.20', 'surcharge_fee': '26.00', 'withholding_type': '0.00',
            'withholding_amount': '0.00',
        })

    def test_libros_export_with_wrong_surcharge_raises_error(self):
        self.init_invoice('out_invoice', amounts=[500], post=True, taxes=[self.tax_21, self.tax_10_surcharge])
        with self.assertRaisesRegex(UserError, "Unable to find matching surcharge tax"):
            self.get_libros_sheet_line_vals()

    def test_libros_export_with_ignore_type(self):
        self.init_invoice('in_invoice', amounts=[500], post=True, taxes=[self.tax_dua_ignore])
        exp_line_vals = self.get_libros_sheet_line_vals()[1]
        line_vals_list = [exp_line_vals[m][t] for m in exp_line_vals for t in exp_line_vals[m]]
        self.assertEqual(line_vals_list, [])

    def test_libros_export_with_retencion(self):
        self.init_invoice('in_invoice', amounts=[500], post=True, taxes=[self.tax_dua_rentencion])
        exp_line_vals = self.get_libros_sheet_line_vals()[1]
        line_vals_list = [exp_line_vals[m][t] for m in exp_line_vals for t in exp_line_vals[m]]
        self.assertEqual(line_vals_list, [])

    def test_libros_export_with_retencion_and_other_tax(self):
        self.init_invoice('in_invoice', amounts=[500], post=True, taxes=[self.tax_dua_rentencion, self.tax_21])
        exp_line_vals = self.get_libros_sheet_line_vals()[1]
        line_vals_list = [exp_line_vals[m][t] for m in exp_line_vals for t in exp_line_vals[m]]
        self.assertEqual(len(line_vals_list), 1)
        amount_vals = self.get_amount_vals(line_vals_list[0])
        self.assertDictEqual(amount_vals, {
            'expense_deductible': '500.00', 'total_amount': '505.00', 'base_amount': '500.00', 'tax_rate': '21.00',
            'taxed_amount': '105.00', 'tax_deductible': '105.00', 'surcharge_type': '0.00', 'surcharge_fee': '0.00',
            'withholding_type': '20.00', 'withholding_amount': '100.00',
        })

    def test_libros_export_with_dua_group(self):
        self.init_invoice('in_invoice', amounts=[500], post=True, taxes=[self.tax_dua_group])
        exp_line_vals = self.get_libros_sheet_line_vals()[1]
        line_vals_list = [exp_line_vals[m][t] for m in exp_line_vals for t in exp_line_vals[m]]
        self.assertEqual(len(line_vals_list), 1)
        line_vals = line_vals_list[0]
        self.assertDictEqual(line_vals, {
            'activity_code': 'A', 'activity_group': '6533', 'activity_type': '03', 'base_amount': '500.00',
            'billing_agreement': '', 'date_expedition': '01/01/2019', 'date_reception': '01/01/2019',
            'date_transaction': '', 'deductible_later': '', 'deduction_period': '', 'deduction_year': '',
            'expense_concept': 'G01', 'expense_deductible': '500.00', 'expense_final_number': '',
            'expense_series_number': 'BILL/2019/01/0001', 'external_reference': '', 'investment_good': 'N',
            'invoice_type': 'F5', 'isp_taxable': 'N', 'operation_code': '01', 'partner_name': 'Esperado Espagnole',
            'partner_nif_code': '', 'partner_nif_id': '59962470K', 'partner_nif_type': '', 'payment_amount': '',
            'payment_date': '', 'payment_medium': '', 'payment_medium_id': '', 'period': '1T', 'property_reference': '',
            'property_situation': '', 'reception_number': '', 'reception_number_final': '', 'surcharge_fee': '0.00',
            'surcharge_type': '0.00', 'tax_deductible': '50.00', 'tax_rate': '10.00', 'taxed_amount': '50.00',
            'total_amount': '550.00', 'withholding_amount': '0.00', 'withholding_type': '0.00', 'year': 2019,
        })

    def test_libros_export_with_credit_note(self):
        invoice = self.init_invoice('out_invoice', amounts=[1000], post=True, taxes=self.tax_21)
        credit_note = invoice._reverse_moves([{'invoice_date': invoice.invoice_date}])
        credit_note.action_post()
        inc_line_vals = self.get_libros_sheet_line_vals()[0]
        line_vals_list = [inc_line_vals[m][t] for m in inc_line_vals for t in inc_line_vals[m]]
        self.assertEqual(len(line_vals_list), 2)
        self.assertDictEqual(line_vals_list[0], {
            'activity_code': 'A', 'activity_group': '6533', 'activity_type': '03', 'base_amount': '-1000.00',
            'billing_agreement': '', 'date_expedition': '01/01/2019', 'date_transaction': '', 'external_reference': '',
            'income_computable': '-1000.00', 'income_concept': 'I01', 'invoice_final_number': '',
            'invoice_number': 'RINV/2019/00001', 'invoice_series': '', 'invoice_type': 'R1', 'operation_code': '01',
            'operation_exempt': '', 'operation_qualification': 'S1', 'partner_name': 'Esperado Espagnole',
            'partner_nif_code': '', 'partner_nif_id': '59962470K', 'partner_nif_type': '', 'payment_amount': '',
            'payment_date': '', 'payment_medium': '', 'payment_medium_id': '', 'period': '1T', 'property_reference': '',
            'property_situation': '', 'surcharge_fee': '0.00', 'surcharge_type': '0.00', 'tax_rate': '21.00',
            'taxed_amount': '-210.00', 'total_amount': '-1210.00', 'withholding_amount': '0.00', 'withholding_type': '0.00',
            'year': 2019,
        })
        self.assertDictEqual(line_vals_list[1], {
            'activity_code': 'A', 'activity_group': '6533', 'activity_type': '03', 'base_amount': '1000.00',
            'billing_agreement': '', 'date_expedition': '01/01/2019', 'date_transaction': '', 'external_reference': '',
            'income_computable': '1000.00', 'income_concept': 'I01', 'invoice_final_number': '',
            'invoice_number': 'INV/2019/00001', 'invoice_series': '', 'invoice_type': 'F1', 'operation_code': '01',
            'operation_exempt': '', 'operation_qualification': 'S1', 'partner_name': 'Esperado Espagnole',
            'partner_nif_code': '', 'partner_nif_id': '59962470K', 'partner_nif_type': '', 'payment_amount': '',
            'payment_date': '', 'payment_medium': '', 'payment_medium_id': '', 'period': '1T', 'property_reference': '',
            'property_situation': '', 'surcharge_fee': '0.00', 'surcharge_type': '0.00', 'tax_rate': '21.00',
            'taxed_amount': '210.00', 'total_amount': '1210.00', 'withholding_amount': '0.00', 'withholding_type': '0.00',
            'year': 2019,
        })

    def test_libros_export_eu_bill(self):
        be_partner = self.env['res.partner'].create({
            'country_id': self.env.ref('base.be').id,
            'name': 'Belgian Partner',
            'vat': 'BE0477472701',
        })
        company_id = self.company_data['company'].id
        eu_tax_21 = self.env.ref(f'account.{company_id}_account_tax_template_p_iva21_ic_bc')
        self.init_invoice('in_invoice', partner=be_partner, amounts=[1000], post=True, taxes=eu_tax_21)
        exp_line_vals = self.get_libros_sheet_line_vals()[1]
        line_vals_list = [exp_line_vals[m][t] for m in exp_line_vals for t in exp_line_vals[m]]
        self.assertEqual(len(line_vals_list), 1)
        amount_vals = self.get_amount_vals(line_vals_list[0])
        self.assertDictEqual(amount_vals, {
            'expense_deductible': '1000.00', 'total_amount': '1000.00', 'base_amount': '1000.00', 'tax_rate': '21.00',
            'taxed_amount': '0.00', 'tax_deductible': '0.00', 'surcharge_type': '0.00', 'surcharge_fee': '0.00',
            'withholding_type': '0.00', 'withholding_amount': '0.00',
        })

    def test_libros_export_advanced_taxes_combination(self):
        """ Test an invoice with 7 invoice lines having different combinations of taxes:

              amount  |               taxes
            ------------------------------------------------
              100.00  |  tax_21
              100.00  |  tax_05_se + tax_4_iva
              100.00  |  tax_05_se + tax_4_iva + tax_9_whi
              100.00  |  tax_05_se + tax_5_iva
              111.11  |  tax_21 + tax_9_whi
              111.11  |  tax_21 + tax_9_whi
              500.00  |  tax_9_whi

            tax_21: 21% IVA tax
            tax_4_iva: 4% IVA tax
            tax_5_iva: 5% IVA tax
            tax_05_se: 0.5% Surcharge tax ("Recargo de Equivalencia" Spanish tax type)
            tax_9_whi: 9% Withholding tax ("Retencion" Spanish tax type)
        """
        company_id = self.company_data['company'].id
        tax_4_iva = self.env.ref(f'account.{company_id}_account_tax_template_s_iva4b')
        tax_5_iva = self.env.ref(f'account.{company_id}_account_tax_template_s_iva5b')
        tax_05_se = self.env.ref(f'account.{company_id}_account_tax_template_s_req05')
        tax_9_whi = self.env.ref(f'account.{company_id}_account_tax_template_s_irpf9')

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': fields.Date.from_string('2019-06-15'),
            'line_ids': [
                Command.create({
                    'name': 'line 1',
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_21.ids)],
                }),
                Command.create({
                    'name': 'line 2',
                    'price_unit': 100.0,
                    'tax_ids': [Command.set((tax_05_se + tax_4_iva).ids)],
                }),
                Command.create({
                    'name': 'line 3',
                    'price_unit': 100.0,
                    'tax_ids': [Command.set((tax_05_se + tax_4_iva + tax_9_whi).ids)],
                }),
                Command.create({
                    'name': 'line 4',
                    'price_unit': 100.0,
                    'tax_ids': [Command.set((tax_05_se + tax_5_iva).ids)],
                }),
                # the 2 following lines should be merged together
                Command.create({
                    'name': 'line 5',
                    'price_unit': 111.11,
                    'tax_ids': [Command.set((self.tax_21 + tax_9_whi).ids)],
                }),
                Command.create({
                    'name': 'line 6',
                    'price_unit': 111.11,
                    'tax_ids': [Command.set((self.tax_21 + tax_9_whi).ids)],
                }),
                # this line should not appear as it only contains one withholding tax
                Command.create({
                    'name': 'line 7',
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(tax_9_whi.ids)],
                }),
            ],
        })
        move.action_post()
        inc_line_vals = self.get_libros_sheet_line_vals()[0]
        line_vals_list = [inc_line_vals[m][t] for m in inc_line_vals for t in inc_line_vals[m]]
        self.assertEqual(len(line_vals_list), 5)
        amount_vals = {}
        for i in range(5):
            amount_vals[i] = self.get_amount_vals(line_vals_list[i])
        self.assertDictEqual(amount_vals[0], {
            'income_computable': '100.00', 'total_amount': '121.00', 'base_amount': '100.00', 'tax_rate': '21.00',
            'taxed_amount': '21.00', 'surcharge_type': '0.00', 'surcharge_fee': '0.00', 'withholding_type': '0.00',
            'withholding_amount': '0.00',
        })
        self.assertDictEqual(amount_vals[1], {
            'income_computable': '100.00', 'total_amount': '104.50', 'base_amount': '100.00', 'tax_rate': '4.00',
            'taxed_amount': '4.00', 'surcharge_type': '0.50', 'surcharge_fee': '0.50', 'withholding_type': '0.00',
            'withholding_amount': '0.00',
        })
        self.assertDictEqual(amount_vals[2], {
            'income_computable': '100.00', 'total_amount': '95.50', 'base_amount': '100.00', 'tax_rate': '4.00',
            'taxed_amount': '4.00', 'surcharge_type': '0.50', 'surcharge_fee': '0.50', 'withholding_type': '9.00',
            'withholding_amount': '9.00',
        })
        self.assertDictEqual(amount_vals[3], {
            'income_computable': '100.00', 'total_amount': '105.50', 'base_amount': '100.00', 'tax_rate': '5.00',
            'taxed_amount': '5.00', 'surcharge_type': '0.50', 'surcharge_fee': '0.50', 'withholding_type': '0.00',
            'withholding_amount': '0.00',
        })
        self.assertDictEqual(amount_vals[4], {
            'income_computable': '222.22', 'total_amount': '248.88', 'base_amount': '222.22', 'tax_rate': '21.00',
            'taxed_amount': '46.66', 'surcharge_type': '0.00', 'surcharge_fee': '0.00', 'withholding_type': '9.00',
            'withholding_amount': '20.00',
        })

    def test_libros_export_nif(self):
        self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_21)
        self.init_invoice('out_invoice', partner=self.partner_fr, amounts=[1000], post=True, taxes=self.tax_21)
        self.init_invoice('out_invoice', partner=self.partner_us, amounts=[1000], post=True, taxes=self.tax_21)
        inc_line_vals = self.get_libros_sheet_line_vals()[0]
        line_vals_list = [inc_line_vals[m][t] for m in inc_line_vals for t in inc_line_vals[m]]
        self.assertEqual(len(line_vals_list), 3)

        line_vals = line_vals_list[2]
        self.assertEqual(line_vals['partner_nif_code'], '')
        self.assertEqual(line_vals['partner_nif_id'], '59962470K')
        self.assertEqual(line_vals['partner_nif_type'], '')

        line_vals = line_vals_list[1]
        self.assertEqual(line_vals['partner_nif_code'], '')
        self.assertEqual(line_vals['partner_nif_id'], 'FR23334175221')
        self.assertEqual(line_vals['partner_nif_type'], '02')

        line_vals = line_vals_list[0]
        self.assertEqual(line_vals['partner_nif_code'], 'US')
        self.assertEqual(line_vals['partner_nif_id'], 'US66655598K')
        self.assertEqual(line_vals['partner_nif_type'], '06')
