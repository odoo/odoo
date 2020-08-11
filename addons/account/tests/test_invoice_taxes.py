# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_savepoint import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestInvoiceTaxes(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].country_id = cls.env.ref('base.be')

        cls.percent_tax_1 = cls.env['account.tax'].create({
            'name': '21%',
            'amount_type': 'percent',
            'amount': 21,
            'sequence': 10,
        })
        cls.percent_tax_1_incl = cls.env['account.tax'].create({
            'name': '21% incl',
            'amount_type': 'percent',
            'amount': 21,
            'price_include': True,
            'include_base_amount': True,
            'sequence': 20,
        })
        cls.percent_tax_2 = cls.env['account.tax'].create({
            'name': '12%',
            'amount_type': 'percent',
            'amount': 12,
            'sequence': 30,
        })
        cls.group_tax = cls.env['account.tax'].create({
            'name': 'group 12% + 21%',
            'amount_type': 'group',
            'amount': 21,
            'children_tax_ids': [
                (4, cls.percent_tax_1_incl.id),
                (4, cls.percent_tax_2.id)
            ],
            'sequence': 40,
        })

        cls.tax_report_line = cls.env['account.tax.report.line'].create({
            'name': 'test_tax_report_line',
            'tag_name': 'test_tax_report_line',
            'country_id': cls.env.ref('base.be').id,
            'sequence': 10,
        })
        cls.tax_tag_pos = cls.tax_report_line.tag_ids.filtered(lambda x: not x.tax_negate)
        cls.tax_tag_neg = cls.tax_report_line.tag_ids.filtered(lambda x: x.tax_negate)
        cls.base_tax_report_line = cls.env['account.tax.report.line'].create({
            'name': 'base_test_tax_report_line',
            'tag_name': 'base_test_tax_report_line',
            'country_id': cls.env.ref('base.be').id,
            'sequence': 10,
        })
        cls.base_tag_pos = cls.base_tax_report_line.tag_ids.filtered(lambda x: not x.tax_negate)
        cls.base_tag_neg = cls.base_tax_report_line.tag_ids.filtered(lambda x: x.tax_negate)

    def _create_invoice(self, taxes_per_line, inv_type='out_invoice'):
        ''' Create an invoice on the fly.

        :param taxes_per_line: A list of tuple (price_unit, account.tax recordset)
        '''
        return self.env['account.move'].create({
            'type': inv_type,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'xxxx',
                'quantity': 1,
                'price_unit': amount,
                'tax_ids': [(6, 0, taxes.ids)],
            }) for amount, taxes in taxes_per_line],
        })

    def test_one_tax_per_line(self):
        ''' Test:
        price_unit | Taxes
        ------------------
        100        | 21%
        121        | 21% incl
        100        | 12%

        Expected:
        Tax         | Taxes     | Base      | Amount
        --------------------------------------------
        21%         | /         | 100       | 21
        21% incl    | /         | 100       | 21
        12%         | /         | 100       | 12
        '''
        invoice = self._create_invoice([
            (100, self.percent_tax_1),
            (121, self.percent_tax_1_incl),
            (100, self.percent_tax_2),
        ])
        invoice.post()
        self.assertRecordValues(invoice.line_ids.filtered('tax_line_id'), [
            {'name': self.percent_tax_1.name,       'tax_base_amount': 100, 'price_unit': 21, 'tax_ids': []},
            {'name': self.percent_tax_1_incl.name,  'tax_base_amount': 100, 'price_unit': 21, 'tax_ids': []},
            {'name': self.percent_tax_2.name,       'tax_base_amount': 100, 'price_unit': 12, 'tax_ids': []},
        ])

    def test_affecting_base_amount(self):
        ''' Test:
        price_unit | Taxes
        ------------------
        121        | 21% incl, 12%
        100        | 12%

        Expected:
        Tax         | Taxes     | Base      | Amount
        --------------------------------------------
        21% incl    | 12%       | 100       | 21
        12%         | /         | 121       | 14.52
        12%         | /         | 100       | 12
        '''
        invoice = self._create_invoice([
            (121, self.percent_tax_1_incl + self.percent_tax_2),
            (100, self.percent_tax_2),
        ])
        invoice.post()
        self.assertRecordValues(invoice.line_ids.filtered('tax_line_id').sorted(lambda x: x.price_unit), [
            {'name': self.percent_tax_1_incl.name,      'tax_base_amount': 100, 'price_unit': 21,      'tax_ids': [self.percent_tax_2.id]},
            {'name': self.percent_tax_2.name,           'tax_base_amount': 221, 'price_unit': 26.52,   'tax_ids': []},
        ])

    def test_group_of_taxes(self):
        ''' Test:
        price_unit | Taxes
        ------------------
        121        | 21% incl + 12%
        100        | 12%

        Expected:
        Tax         | Taxes     | Base      | Amount
        --------------------------------------------
        21% incl    | /         | 100       | 21
        12%         | 21% incl  | 121       | 14.52
        12%         | /         | 100       | 12
        '''
        invoice = self._create_invoice([
            (121, self.group_tax),
            (100, self.percent_tax_2),
        ])
        invoice.post()
        self.assertRecordValues(invoice.line_ids.filtered('tax_line_id').sorted(lambda x: x.price_unit), [
            {'name': self.percent_tax_1_incl.name,      'tax_base_amount': 100, 'price_unit': 21,      'tax_ids': [self.percent_tax_2.id]},
            {'name': self.percent_tax_2.name,           'tax_base_amount': 221, 'price_unit': 26.52,   'tax_ids': []},
        ])

    def _create_tax_tag(self, tag_name):
        return self.env['account.account.tag'].create({
            'name': tag_name,
            'applicability': 'taxes',
            'country_id': self.env.company.country_id.id,
        })

    def test_tax_repartition(self):
        inv_base_tag = self._create_tax_tag('invoice_base')
        inv_tax_tag_10 = self._create_tax_tag('invoice_tax_10')
        inv_tax_tag_90 = self._create_tax_tag('invoice_tax_90')
        ref_base_tag = self._create_tax_tag('refund_base')
        ref_tax_tag = self._create_tax_tag('refund_tax')

        user_type = self.env.ref('account.data_account_type_current_assets')
        account_1 = self.env['account.account'].create({'name': 'test1', 'code': 'test1', 'user_type_id': user_type.id})
        account_2 = self.env['account.account'].create({'name': 'test2', 'code': 'test2', 'user_type_id': user_type.id})

        tax = self.env['account.tax'].create({
            'name': "Tax with account",
            'amount_type': 'fixed',
            'type_tax_use': 'sale',
            'amount': 42,
            'invoice_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [(4, inv_base_tag.id, 0)],
                }),

                (0,0, {
                    'factor_percent': 10,
                    'repartition_type': 'tax',
                    'account_id': account_1.id,
                    'tag_ids': [(4, inv_tax_tag_10.id, 0)],
                }),

                (0,0, {
                    'factor_percent': 90,
                    'repartition_type': 'tax',
                    'account_id': account_2.id,
                    'tag_ids': [(4, inv_tax_tag_90.id, 0)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0,0, {
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [(4, ref_base_tag.id, 0)],
                }),

                (0,0, {
                    'factor_percent': 10,
                    'repartition_type': 'tax',
                    'tag_ids': [(4, ref_tax_tag.id, 0)],
                }),

                (0,0, {
                    'factor_percent': 90,
                    'repartition_type': 'tax',
                    'account_id': account_1.id,
                    'tag_ids': [(4, ref_tax_tag.id, 0)],
                }),
            ],
        })

        # Test invoice repartition
        invoice = self._create_invoice([(100, tax)], inv_type='out_invoice')
        invoice.post()

        self.assertEqual(len(invoice.line_ids), 4, "There should be 4 account move lines created for the invoice: payable, base and 2 tax lines")
        inv_base_line = invoice.line_ids.filtered(lambda x: not x.tax_repartition_line_id and x.account_id.user_type_id.type != 'receivable')
        self.assertEqual(len(inv_base_line), 1, "There should be only one base line generated")
        self.assertEqual(abs(inv_base_line.balance), 100, "Base amount should be 100")
        self.assertEqual(inv_base_line.tag_ids, inv_base_tag, "Base line should have received base tag")
        inv_tax_lines = invoice.line_ids.filtered(lambda x: x.tax_repartition_line_id.repartition_type == 'tax')
        self.assertEqual(len(inv_tax_lines), 2, "There should be two tax lines, one for each repartition line.")
        self.assertEqual(abs(inv_tax_lines.filtered(lambda x: x.account_id == account_1).balance), 4.2, "Tax line on account 1 should amount to 4.2 (10% of 42)")
        self.assertEqual(inv_tax_lines.filtered(lambda x: x.account_id == account_1).tag_ids, inv_tax_tag_10, "Tax line on account 1 should have 10% tag")
        self.assertAlmostEqual(abs(inv_tax_lines.filtered(lambda x: x.account_id == account_2).balance), 37.8, 2, "Tax line on account 2 should amount to 37.8 (90% of 42)")
        self.assertEqual(inv_tax_lines.filtered(lambda x: x.account_id == account_2).tag_ids, inv_tax_tag_90, "Tax line on account 2 should have 90% tag")

        # Test refund repartition
        refund = self._create_invoice([(100, tax)], inv_type='out_refund')
        refund.post()

        self.assertEqual(len(refund.line_ids), 4, "There should be 4 account move lines created for the refund: payable, base and 2 tax lines")
        ref_base_line = refund.line_ids.filtered(lambda x: not x.tax_repartition_line_id and x.account_id.user_type_id.type != 'receivable')
        self.assertEqual(len(ref_base_line), 1, "There should be only one base line generated")
        self.assertEqual(abs(ref_base_line.balance), 100, "Base amount should be 100")
        self.assertEqual(ref_base_line.tag_ids, ref_base_tag, "Base line should have received base tag")
        ref_tax_lines = refund.line_ids.filtered(lambda x: x.tax_repartition_line_id.repartition_type == 'tax')
        self.assertEqual(len(ref_tax_lines), 2, "There should be two refund tax lines")
        self.assertEqual(abs(ref_tax_lines.filtered(lambda x: x.account_id == ref_base_line.account_id).balance), 4.2, "Refund tax line on base account should amount to 4.2 (10% of 42)")
        self.assertAlmostEqual(abs(ref_tax_lines.filtered(lambda x: x.account_id == account_1).balance), 37.8, 2, "Refund tax line on account 1 should amount to 37.8 (90% of 42)")
        self.assertEqual(ref_tax_lines.mapped('tag_ids'), ref_tax_tag, "Refund tax lines should have the right tag")

    def test_misc_journal_entry_tax_tags_sale(self):
        sale_tax = self.env['account.tax'].create({
            'name': 'tax',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 10,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'factor_percent': 100.0,
                    'tag_ids': [(6, 0, self.base_tag_pos.ids)],
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'factor_percent': 100.0,
                    'tag_ids': [(6, 0, self.tax_tag_pos.ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'factor_percent': 100.0,
                    'tag_ids': [(6, 0, self.base_tag_neg.ids)],
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'factor_percent': 100.0,
                    'tag_ids': [(6, 0, self.tax_tag_neg.ids)],
                }),
            ],
        })

        # === Tax in debit ===

        move_form = Form(self.env['account.move'], view='account.view_move_form')
        move_form.ref = 'azerty'

        # Debit base tax line.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'debit_line_1'
            credit_line.account_id = self.company_data['default_account_revenue']
            credit_line.debit = 1000.0
            credit_line.tax_ids.clear()
            credit_line.tax_ids.add(sale_tax)

            self.assertTrue(credit_line.recompute_tax_line)

        # Balance the journal entry.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'balance'
            credit_line.account_id = self.company_data['default_account_revenue']
            credit_line.credit = 1100.0

        move = move_form.save()

        self.assertRecordValues(move.line_ids.sorted('balance'), [
            {'balance': -1100.0,    'tax_ids': [],              'tag_ids': []},
            {'balance': 100.0,      'tax_ids': [],              'tag_ids': self.tax_tag_neg.ids},
            {'balance': 1000.0,     'tax_ids': sale_tax.ids,    'tag_ids': self.base_tag_neg.ids},
        ])

        # === Tax in credit ===

        move_form = Form(self.env['account.move'], view='account.view_move_form')
        move_form.ref = 'azerty'

        # Debit base tax line.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'debit_line_1'
            credit_line.account_id = self.company_data['default_account_revenue']
            credit_line.credit = 1000.0
            credit_line.tax_ids.clear()
            credit_line.tax_ids.add(sale_tax)

            self.assertTrue(credit_line.recompute_tax_line)

        # Balance the journal entry.
        with move_form.line_ids.new() as debit_line:
            debit_line.name = 'balance'
            debit_line.account_id = self.company_data['default_account_revenue']
            debit_line.debit = 1100.0

        move = move_form.save()

        self.assertRecordValues(move.line_ids.sorted('balance'), [
            {'balance': -1000.0,    'tax_ids': sale_tax.ids,    'tag_ids': self.base_tag_neg.ids},
            {'balance': -100.0,     'tax_ids': [],              'tag_ids': self.tax_tag_neg.ids},
            {'balance': 1100.0,     'tax_ids': [],              'tag_ids': []},
        ])

    def test_misc_journal_entry_tax_tags_purchase(self):
        purch_tax = self.env['account.tax'].create({
            'name': 'tax',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 10,
            'invoice_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'factor_percent': 100.0,
                    'tag_ids': [(6, 0, self.base_tag_pos.ids)],
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'factor_percent': 100.0,
                    'tag_ids': [(6, 0, self.tax_tag_pos.ids)],
                }),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {
                    'repartition_type': 'base',
                    'factor_percent': 100.0,
                    'tag_ids': [(6, 0, self.base_tag_neg.ids)],
                }),
                (0, 0, {
                    'repartition_type': 'tax',
                    'factor_percent': 100.0,
                    'tag_ids': [(6, 0, self.tax_tag_neg.ids)],
                }),
            ],
        })

        # === Tax in debit ===

        move_form = Form(self.env['account.move'])
        move_form.ref = 'azerty'

        # Debit base tax line.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'debit_line_1'
            credit_line.account_id = self.company_data['default_account_revenue']
            credit_line.debit = 1000.0
            credit_line.tax_ids.clear()
            credit_line.tax_ids.add(purch_tax)

            self.assertTrue(credit_line.recompute_tax_line)

        # Balance the journal entry.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'balance'
            credit_line.account_id = self.company_data['default_account_revenue']
            credit_line.credit = 1100.0

        move = move_form.save()

        self.assertRecordValues(move.line_ids.sorted('balance'), [
            {'balance': -1100.0,    'tax_ids': [],              'tag_ids': []},
            {'balance': 100.0,      'tax_ids': [],              'tag_ids': self.tax_tag_pos.ids},
            {'balance': 1000.0,     'tax_ids': purch_tax.ids,   'tag_ids': self.base_tag_pos.ids},
        ])

        # === Tax in credit ===

        move_form = Form(self.env['account.move'])
        move_form.ref = 'azerty'

        # Debit base tax line.
        with move_form.line_ids.new() as credit_line:
            credit_line.name = 'debit_line_1'
            credit_line.account_id = self.company_data['default_account_revenue']
            credit_line.credit = 1000.0
            credit_line.tax_ids.clear()
            credit_line.tax_ids.add(purch_tax)

            self.assertTrue(credit_line.recompute_tax_line)

        # Balance the journal entry.
        with move_form.line_ids.new() as debit_line:
            debit_line.name = 'balance'
            debit_line.account_id = self.company_data['default_account_revenue']
            debit_line.debit = 1100.0

        move = move_form.save()

        self.assertRecordValues(move.line_ids.sorted('balance'), [
            {'balance': -1000.0,    'tax_ids': purch_tax.ids,   'tag_ids': self.base_tag_pos.ids},
            {'balance': -100.0,     'tax_ids': [],              'tag_ids': self.tax_tag_pos.ids},
            {'balance': 1100.0,     'tax_ids': [],              'tag_ids': []},
        ])
