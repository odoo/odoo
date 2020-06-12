# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestAccountMoveTaxes(AccountTestInvoicingCommon):

    def _test_tax_armageddon_results(self, invoice):
        self.assertRecordValues(invoice.line_ids.sorted(lambda line: line.balance), [
            {
                'tax_ids': self.tax_armageddon.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2000.0,
                'debit': 0.0,
                'credit': 1000.0,
                'tax_exigible': False,
            },
            {
                'tax_ids': self.tax_armageddon.children_tax_ids[1].ids,
                'tax_line_id': self.tax_armageddon.children_tax_ids[0].id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -240.0,
                'debit': 0.0,
                'credit': 120.0,
                'tax_exigible': True,
            },
            {
                'tax_ids': [],
                'tax_line_id': self.tax_armageddon.children_tax_ids[1].id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -240.0,
                'debit': 0.0,
                'credit': 120.0,
                'tax_exigible': False,
            },
            {
                'tax_ids': self.tax_armageddon.children_tax_ids[1].ids,
                'tax_line_id': self.tax_armageddon.children_tax_ids[0].id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -160.0,
                'debit': 0.0,
                'credit': 80.0,
                'tax_exigible': True,
            },
            {
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2640.0,
                'debit': 1320.0,
                'credit': 0.0,
                'tax_exigible': True,
            },
        ])

    def test_invoice_create_tax_armageddon(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 2400.0,
                'tax_ids': [(6, 0, self.tax_armageddon.ids)],
            })],
        })

        self._test_tax_armageddon_results(invoice)

    def test_invoice_onchange_tax_armageddon(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        move_form.currency_id = self.currency_data['currency']
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.tax_ids.clear()
            line_form.tax_ids.add(self.tax_armageddon)
            line_form.price_unit = 2400.0
        invoice = move_form.save()

        self._test_tax_armageddon_results(invoice)

    def test_entry_onchange_tax_armageddon(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='entry'))
        move_form.date = fields.Date.from_string('2017-01-01')
        with move_form.line_ids.new() as line_form:
            line_form.name = 'credit_line'
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.currency_id = self.currency_data['currency']
            line_form.amount_currency = -2000.0
            line_form.tax_ids.clear()
            line_form.tax_ids.add(self.tax_armageddon)
        with move_form.line_ids.new() as line_form:
            line_form.name = 'debit_line'
            line_form.account_id = self.company_data['default_account_receivable']
            line_form.currency_id = self.currency_data['currency']
            line_form.amount_currency = 2640.0
        move = move_form.save()

        self._test_tax_armageddon_results(move)

    def _test_invoice_manual_edition_of_taxes_single_currency(self, invoice):
        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_a.id,
                'tax_ids': (self.tax_sale_a + self.tax_sale_b).ids,
                'tax_line_id': False,
                'debit': 0.0,
                'credit': 1000.0,
            },
            {
                'product_id': False,
                'tax_ids': [],
                'tax_line_id': self.tax_sale_a.id,
                'debit': 0.0,
                'credit': 160.0,
            },
            {
                'product_id': False,
                'tax_ids': [],
                'tax_line_id': self.tax_sale_b.id,
                'debit': 0.0,
                'credit': 140.0,
            },
            {
                'product_id': False,
                'tax_ids': [],
                'tax_line_id': False,
                'debit': 1300.0,
                'credit': 0.0,
            },
        ], {
            'amount_untaxed': 1000.0,
            'amount_tax': 300.0,
            'amount_total': 1300.0,
        })

    def test_invoice_create_manual_edition_of_taxes_single_currency(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, (self.tax_sale_a + self.tax_sale_b).ids)],
            })],
        })

        tax_line_1 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_sale_a)
        tax_line_2 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_sale_b)
        invoice.write({
            'line_ids': [
                (1, tax_line_1.id, {'credit': tax_line_1.credit + 10.0}),
                (1, tax_line_2.id, {'credit': tax_line_2.credit - 10.0}),
            ],
        })

        self._test_invoice_manual_edition_of_taxes_single_currency(invoice)

        invoice.action_post()

        self._test_invoice_manual_edition_of_taxes_single_currency(invoice)

    def test_invoice_onchange_manual_edition_of_taxes_single_currency(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.tax_ids.clear()
            line_form.tax_ids.add(self.tax_sale_a)
            line_form.tax_ids.add(self.tax_sale_b)
        invoice = move_form.save()

        tax_line_index_1 = [line.tax_line_id for line in invoice.line_ids].index(self.tax_sale_a)
        tax_line_index_2 = [line.tax_line_id for line in invoice.line_ids].index(self.tax_sale_b)
        with Form(invoice) as move_form:
            with move_form.line_ids.edit(tax_line_index_1) as line_form:
                line_form.credit += 10.0
            with move_form.line_ids.edit(tax_line_index_2) as line_form:
                line_form.credit -= 10.0

        self._test_invoice_manual_edition_of_taxes_single_currency(invoice)

        invoice.action_post()

        self._test_invoice_manual_edition_of_taxes_single_currency(invoice)

    def _test_invoice_manual_edition_of_taxes_foreign_currency(self, invoice):
        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_a.id,
                'tax_ids': (self.tax_sale_a + self.tax_sale_b).ids,
                'tax_line_id': False,
                'amount_currency': -2000.0,
                'debit': 0.0,
                'credit': 1000.0,
            },
            {
                'product_id': False,
                'tax_ids': [],
                'tax_line_id': self.tax_sale_a.id,
                'amount_currency': -310.0,
                'debit': 0.0,
                'credit': 155.0,
            },
            {
                'product_id': False,
                'tax_ids': [],
                'tax_line_id': self.tax_sale_b.id,
                'amount_currency': -290.0,
                'debit': 0.0,
                'credit': 145.0,
            },
            {
                'product_id': False,
                'tax_ids': [],
                'tax_line_id': False,
                'amount_currency': 2600.0,
                'debit': 1300.0,
                'credit': 0.0,
            },
        ], {
            'amount_untaxed': 2000.0,
            'amount_tax': 600.0,
            'amount_total': 2600.0,
        })

    def test_invoice_create_manual_edition_of_taxes_foreign_currency(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, (self.tax_sale_a + self.tax_sale_b).ids)],
            })],
        })

        tax_line_1 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_sale_a)
        tax_line_2 = invoice.line_ids.filtered(lambda line: line.tax_line_id == self.tax_sale_b)
        invoice.write({
            'line_ids': [
                (1, tax_line_1.id, {'amount_currency': tax_line_1.amount_currency - 10.0}),
                (1, tax_line_2.id, {'amount_currency': tax_line_2.amount_currency + 10.0}),
            ],
        })

        self._test_invoice_manual_edition_of_taxes_foreign_currency(invoice)

        invoice.action_post()

        self._test_invoice_manual_edition_of_taxes_foreign_currency(invoice)

    def test_invoice_onchange_manual_edition_of_taxes_foreign_currency(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        move_form.currency_id = self.currency_data['currency']
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.tax_ids.clear()
            line_form.tax_ids.add(self.tax_sale_a)
            line_form.tax_ids.add(self.tax_sale_b)
        invoice = move_form.save()

        tax_line_index_1 = [line.tax_line_id for line in invoice.line_ids].index(self.tax_sale_a)
        tax_line_index_2 = [line.tax_line_id for line in invoice.line_ids].index(self.tax_sale_b)
        with Form(invoice) as move_form:
            with move_form.line_ids.edit(tax_line_index_1) as line_form:
                line_form.amount_currency -= 10.0
            with move_form.line_ids.edit(tax_line_index_2) as line_form:
                line_form.amount_currency += 10.0

        self._test_invoice_manual_edition_of_taxes_foreign_currency(invoice)

        invoice.action_post()

        self._test_invoice_manual_edition_of_taxes_foreign_currency(invoice)

    def test_invoice_create_trigger_tax_recomputation(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, self.tax_sale_a.ids)],
            })],
        })

        # Manual edition of tax line.
        tax_line = invoice.line_ids.filtered('tax_line_id')
        invoice.write({'line_ids': [(1, tax_line.id, {'credit': 160.0, 'name': 'blubliblou'})]})
        self.assertRecordValues(tax_line, [{'debit': 0.0, 'credit': 160.0, 'name': 'blubliblou'}])

        # Manual edition of taxes should be lost when editing the label.
        invoice.write({'invoice_line_ids': [(1, invoice.invoice_line_ids.id, {'name': 'blablabla'})]})
        self.assertRecordValues(tax_line, [{'debit': 0.0, 'credit': 160.0, 'name': 'blubliblou'}])

    def test_invoice_onchange_trigger_tax_recomputation(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2017-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.tax_ids.clear()
            line_form.tax_ids.add(self.tax_sale_a)
        invoice = move_form.save()

        # Manual edition of tax line.
        tax_line_index_1 = [line.tax_line_id for line in invoice.line_ids].index(self.tax_sale_a)
        with Form(invoice) as move_form:
            with move_form.line_ids.edit(tax_line_index_1) as line_form:
                line_form.credit = 160.0
                # Custom label on tax lines is allowed.
                line_form.name = 'blubliblou'

        tax_line = invoice.line_ids.filtered('tax_line_id')
        self.assertRecordValues(tax_line, [{'debit': 0.0, 'credit': 160.0, 'name': 'blubliblou'}])

        # Manual edition of taxes should be lost when editing the label.
        with Form(invoice) as move_form:
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.name = 'blablabla'

        self.assertRecordValues(tax_line, [{'debit': 0.0, 'credit': 160.0, 'name': 'blubliblou'}])

    def test_misc_operation_onchange_tax_recomputation(self):
        ''' Test the taxes computation when encoding a misc. journal entry. '''

        move_form = Form(self.env['account.move'].with_context(default_move_type='entry'))
        move_form.date = fields.Date.from_string('2016-01-01')
        with move_form.line_ids.new() as line_form:
            line_form.name = 'debit_line_1'
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.amount_currency = 1000.0 # =1000.0 debit
            line_form.tax_ids.clear()
            line_form.tax_ids.add(self.tax_sale_a) #=150 debit
        with move_form.line_ids.new() as line_form:
            line_form.name = 'debit_line_2'
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.amount_currency = 5000.0 # =5000.0 debit
            line_form.tax_ids.clear()
            line_form.tax_ids.add(self.tax_sale_a) #=750 debit
        with move_form.line_ids.new() as line_form:
            line_form.name = 'credit_line_1'
            line_form.account_id = self.company_data['default_account_revenue']
            line_form.amount_currency = -18000.0 # =6000 credit
            line_form.currency_id = self.currency_data['currency']
            line_form.tax_ids.clear()
            line_form.tax_ids.add(self.tax_sale_b) #=900 credit
        move = move_form.save()

        self.assertRecordValues(move.line_ids.sorted(lambda line: (line.tax_line_id, -line.amount_currency)), [
            {
                'tax_ids': self.tax_sale_a.ids,
                'tax_line_id': False,
                'currency_id': self.company_data['currency'].id,
                'partner_id': False,
                'amount_currency': 5000.0,
                'debit': 5000.0,
                'credit': 0.0,
            },
            {
                'tax_ids': self.tax_sale_a.ids,
                'tax_line_id': False,
                'currency_id': self.company_data['currency'].id,
                'partner_id': False,
                'amount_currency': 1000.0,
                'debit': 1000.0,
                'credit': 0.0,
            },
            {
                'tax_ids': self.tax_sale_b.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'partner_id': False,
                'amount_currency': -18000.0,
                'debit': 0.0,
                'credit': 6000.0,
            },
            {
                'tax_ids': [],
                'tax_line_id': self.tax_sale_a.id,
                'currency_id': self.company_data['currency'].id,
                'partner_id': False,
                'amount_currency': 900.0,
                'debit': 900.0,
                'credit': 0.0,
            },
            {
                'tax_ids': [],
                'tax_line_id': self.tax_sale_b.id,
                'currency_id': self.currency_data['currency'].id,
                'partner_id': False,
                'amount_currency': -2700.0,
                'debit': 0.0,
                'credit': 900.0,
            },
        ])

        with Form(move) as move_form:
            credit_line_index = [line.name for line in move.line_ids].index('credit_line_1')
            with move_form.line_ids.edit(credit_line_index) as line_form:
                line_form.partner_id = self.partner_a
                line_form.amount_currency = -18030.0 # will produce a tax line of amount_currency=2704.5 & credit=901.5
                line_form.credit = 6000.0
            debit_line_index = [line.name for line in move.line_ids].index('debit_line_1')
            with move_form.line_ids.edit(debit_line_index) as line_form:
                line_form.debit = 1010.0 # the tax line should get debit=901.5
            tax_line_index = [line.tax_line_id for line in move.line_ids].index(self.tax_sale_a)
            with move_form.line_ids.edit(tax_line_index) as line_form:
                line_form.amount_currency = 891.5 # manual edition of tax.

            # At this point, debit = 1010.0 + 5000.0 + 891.5, credit = 6000.0 + 901.5

        self.assertRecordValues(move.line_ids.sorted(lambda line: (line.tax_line_id, -line.amount_currency)), [
            {
                'tax_ids': self.tax_sale_a.ids,
                'tax_line_id': False,
                'currency_id': self.company_data['currency'].id,
                'partner_id': False,
                'amount_currency': 5000.0,
                'debit': 5000.0,
                'credit': 0.0,
            },
            {
                'tax_ids': self.tax_sale_a.ids,
                'tax_line_id': False,
                'currency_id': self.company_data['currency'].id,
                'partner_id': False,
                'amount_currency': 1010.0,
                'debit': 1010.0,
                'credit': 0.0,
            },
            {
                'tax_ids': self.tax_sale_b.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'partner_id': self.partner_a.id,
                'amount_currency': -18030.0,
                'debit': 0.0,
                'credit': 6000.0,
            },
            {
                'tax_ids': [],
                'tax_line_id': self.tax_sale_a.id,
                'currency_id': self.company_data['currency'].id,
                'partner_id': False,
                'amount_currency': 891.5,
                'debit': 891.5,
                'credit': 0.0,
            },
            {
                'tax_ids': [],
                'tax_line_id': self.tax_sale_b.id,
                'currency_id': self.currency_data['currency'].id,
                'partner_id': self.partner_a.id,
                'amount_currency': -2704.5,
                'debit': 0.0,
                'credit': 901.5,
            },
        ])
