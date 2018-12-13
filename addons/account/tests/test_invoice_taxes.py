# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests.common import Form
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestInvoiceTaxes(AccountingTestCase):

    def setUp(self):
        super(TestInvoiceTaxes, self).setUp()

        self.percent_tax_1 = self.env['account.tax'].create({
            'name': '21%',
            'amount_type': 'percent',
            'amount': 21,
            'sequence': 10,
        })
        self.percent_tax_1_incl = self.env['account.tax'].create({
            'name': '21% incl',
            'amount_type': 'percent',
            'amount': 21,
            'price_include': True,
            'include_base_amount': True,
            'sequence': 20,
        })
        self.percent_tax_2 = self.env['account.tax'].create({
            'name': '12%',
            'amount_type': 'percent',
            'amount': 12,
            'sequence': 30,
        })
        self.group_tax = self.env['account.tax'].create({
            'name': 'group 12% + 21%',
            'amount_type': 'group',
            'amount': 21,
            'children_tax_ids': [
                (4, self.percent_tax_1_incl.id),
                (4, self.percent_tax_2.id)
            ],
            'sequence': 40,
        })

    def _create_invoice(self, taxes_per_line):
        ''' Create an invoice on the fly.

        :param taxes_per_line: A list of tuple (price_unit, account.tax recordset)
        '''
        self_ctx = self.env['account.invoice'].with_context(type='out_invoice')
        journal_id = self_ctx._default_journal().id
        self_ctx = self_ctx.with_context(journal_id=journal_id)

        with Form(self_ctx, view='account.invoice_form') as invoice_form:
            invoice_form.partner_id = self.env.ref('base.partner_demo')

            for amount, taxes in taxes_per_line:
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    invoice_line_form.name = 'xxxx'
                    invoice_line_form.quantity = 1
                    invoice_line_form.price_unit = amount
                    invoice_line_form.invoice_line_tax_ids.clear()
                    for tax in taxes:
                        invoice_line_form.invoice_line_tax_ids.add(tax)
        return invoice_form.save()

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
        invoice.action_invoice_open()
        self.assertRecordValues(invoice.tax_line_ids, [
            {'name': self.percent_tax_1.name,       'base': 100, 'amount': 21, 'tax_ids': []},
            {'name': self.percent_tax_1_incl.name,  'base': 100, 'amount': 21, 'tax_ids': []},
            {'name': self.percent_tax_2.name,       'base': 100, 'amount': 12, 'tax_ids': []},
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
        21% incl    | /         | 100       | 21
        12%         | 21% incl  | 121       | 14.52
        12%         | /         | 100       | 12
        '''
        invoice = self._create_invoice([
            (121, self.percent_tax_1_incl + self.percent_tax_2),
            (100, self.percent_tax_2),
        ])
        invoice.action_invoice_open()
        self.assertRecordValues(invoice.tax_line_ids.sorted(lambda x: x.amount), [
            {'name': self.percent_tax_2.name,           'base': 100, 'amount': 12,      'tax_ids': []},
            {'name': self.percent_tax_2.name,           'base': 121, 'amount': 14.52,   'tax_ids': [self.percent_tax_1_incl.id]},
            {'name': self.percent_tax_1_incl.name,      'base': 100, 'amount': 21,      'tax_ids': []},
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
        invoice.action_invoice_open()
        self.assertRecordValues(invoice.tax_line_ids.sorted(lambda x: x.amount), [
            {'name': self.percent_tax_2.name,           'base': 100, 'amount': 12,      'tax_ids': []},
            {'name': self.percent_tax_2.name,           'base': 121, 'amount': 14.52,   'tax_ids': [self.percent_tax_1_incl.id]},
            {'name': self.percent_tax_1_incl.name,      'base': 100, 'amount': 21,      'tax_ids': []},
        ])
