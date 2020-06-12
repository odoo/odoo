# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields
from odoo.exceptions import UserError

from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountMovePaymentTerms(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.payment_reference1 = 'turlututu1'
        cls.payment_reference2 = 'turlututu2'
        cls.payment_reference3 = 'turlututu3'
        cls.payment_reference4 = 'turlututu4'

    def _test_invoice_has_payment_reference_1(self, invoice):
        payment_term_lines = invoice.line_ids.filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))
        self.assertRecordValues(invoice, [{
            'payment_reference': self.payment_reference1,
        }])
        self.assertRecordValues(payment_term_lines, [
            {'name': self.payment_reference1},
            {'name': self.payment_reference1},
        ])

    def _test_invoice_has_payment_reference_2(self, invoice):
        payment_term_lines = invoice.line_ids.filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))
        self.assertRecordValues(invoice, [{
            'payment_reference': self.payment_reference2,
        }])
        self.assertRecordValues(payment_term_lines, [
            {'name': self.payment_reference2},
            {'name': self.payment_reference2},
        ])

    def _test_invoice_contains_payment_reference_3_4(self, invoice):
        payment_term_lines = invoice.line_ids.filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))
        self.assertRecordValues(invoice, [{
            'payment_reference': self.payment_reference2,
        }])
        self.assertRecordValues(payment_term_lines, [
            {'name': self.payment_reference3},
            {'name': self.payment_reference4},
        ])

    def test_create_payment_reference_flow(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b.id,
            'payment_reference': self.payment_reference1,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, self.product_a.taxes_id.ids)],
            })],
        })

        self._test_invoice_has_payment_reference_1(invoice)

        invoice.payment_reference = self.payment_reference2

        self._test_invoice_has_payment_reference_2(invoice)

        payment_term_lines = invoice.line_ids.filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))
        payment_term_lines[0].name = self.payment_reference3
        payment_term_lines[1].name = self.payment_reference4

        self._test_invoice_contains_payment_reference_3_4(invoice)

    def test_onchange_payment_reference_flow(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_b
        move_form.payment_reference = self.payment_reference1
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
        invoice = move_form.save()

        self._test_invoice_has_payment_reference_1(invoice)

        with Form(invoice) as move_form:
            move_form.payment_reference = self.payment_reference2

        self._test_invoice_has_payment_reference_2(invoice)

        payment_term_lines = invoice.line_ids.filtered(lambda line: line.account_internal_type in ('receivable', 'payable'))
        with Form(invoice) as move_form:
            for i, orm_command in enumerate(move_form._values['line_ids']):
                line_id = orm_command[1]
                if line_id == payment_term_lines[0].id:
                    payment_reference = self.payment_reference3
                elif line_id == payment_term_lines[1].id:
                    payment_reference = self.payment_reference4
                else:
                    continue
                with move_form.line_ids.edit(i) as line_form:
                    line_form.name = payment_reference

        self._test_invoice_contains_payment_reference_3_4(invoice)
