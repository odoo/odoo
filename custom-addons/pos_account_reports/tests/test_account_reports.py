# -*- coding: utf-8 -*-

from odoo import Command, fields
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class POSTestTaxReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        company = cls.company_data['company']
        test_country = cls.env['res.country'].create({
            'name': "Hassaleh",
            'code': 'HH',
        })
        cls.change_company_country(company, test_country)

        # Create some tax report
        cls.tax_report = cls.env['account.report'].create({
            'name': 'Test',
            'root_report_id': cls.env.ref('account.generic_tax_report').id,
            'availability_condition': 'country',
            'country_id': test_country.id,
            'column_ids': [Command.create({'name': 'balance', 'sequence': 1, 'expression_label': 'balance'})]
        })

        cls.pos_tax_report_line_invoice_base = cls._create_tax_report_line("Invoice Base", cls.tax_report, tag_name='pos_invoice_base', sequence=0)
        cls.pos_tax_report_line_invoice_tax = cls._create_tax_report_line("Invoice Tax", cls.tax_report, tag_name='pos_invoice_tax', sequence=1)
        cls.pos_tax_report_line_refund_base = cls._create_tax_report_line("Refund Base", cls.tax_report, tag_name='pos_refund_base', sequence=2)
        cls.pos_tax_report_line_refund_tax = cls._create_tax_report_line("Refund Tax", cls.tax_report, tag_name='pos_refund_tax', sequence=3)

        # Create a tax using the created report
        cls.pos_tax = cls.env['account.tax'].create({
            'name': 'Impôt recto',
            'amount': '10',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'invoice_repartition_line_ids': [
                (0,0, {
                    'repartition_type': 'base',
                    'tag_ids': cls._get_tag_ids("+", cls.pos_tax_report_line_invoice_base.expression_ids),
                }),

                (0,0, {
                    'repartition_type': 'tax',
                    'tag_ids': cls._get_tag_ids("+", cls.pos_tax_report_line_invoice_tax.expression_ids),
                }),
            ],
            'refund_repartition_line_ids': [
                (0,0, {
                    'repartition_type': 'base',
                    'tag_ids': cls._get_tag_ids("+", cls.pos_tax_report_line_refund_base.expression_ids),
                }),

                (0,0, {
                    'repartition_type': 'tax',
                    'tag_ids': cls._get_tag_ids("+", cls.pos_tax_report_line_refund_tax.expression_ids),
                }),
            ],
        })

        pos_tax_account = cls.env['account.account'].create({
            'name': 'POS tax account',
            'code': 'POSTaxTest',
            'account_type': 'asset_current',
            'company_id': company.id,
        })

        rep_ln_tax = cls.pos_tax.invoice_repartition_line_ids + cls.pos_tax.refund_repartition_line_ids
        rep_ln_tax.filtered(lambda x: x.repartition_type == 'tax').write({'account_id': pos_tax_account.id})

        # Create POS objects
        pos_journal = cls.env['account.journal'].create({
            'name': 'POS journal',
            'type': 'sale',
            'code': 'POS',
            'company_id': company.id,
        })

        cls.pos_config = cls.env['pos.config'].create({
            'name': 'Crab Shop',
            'company_id': company.id,
            'journal_id': pos_journal.id,
        })

        cls.pos_product = cls.env['product.product'].create({
            'name': 'Crab',
            'type': 'consu',
        })

        cls.company_data['default_journal_cash'].pos_payment_method_ids.unlink()
        cls.pos_payment_method = cls.env['pos.payment.method'].create({
            'name': 'POS test payment method',
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'journal_id': cls.company_data['default_journal_cash'].id,
        })

        # Add the payment method to the pos_config
        cls.pos_config.write({'payment_method_ids': [(4, cls.pos_payment_method.id, 0)]})

    def _create_and_pay_pos_order(self, qty, price_unit):
        tax_amount = (self.pos_tax.amount / 100) * qty * price_unit # Only possible because the tax is 'percent' and price excluded. Don't do this at home !
        rounded_total = self.company_data['company'].currency_id.round(tax_amount + price_unit * qty)

        order = self.env['pos.order'].create({
            'company_id': self.company_data['company'].id,
            'partner_id': self.partner_a.id,
            'session_id': self.pos_config.current_session_id.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.pos_product.id,
                'price_unit': price_unit,
                'qty': qty,
                'tax_ids': [(6, 0, self.pos_tax.ids)],
                'price_subtotal': qty * price_unit,
                'price_subtotal_incl': rounded_total,
            })],
            'amount_total': rounded_total,
            'amount_tax': self.company_data['company'].currency_id.round(tax_amount),
            'amount_paid': 0,
            'amount_return': 0,
            'last_order_preparation_change': '{}'
        })

        # Pay the order
        context_payment = {
            "active_ids": [order.id],
            "active_id": order.id
        }
        pos_make_payment = self.env['pos.make.payment'].with_context(context_payment).create({
            'amount': rounded_total,
            'payment_method_id': self.pos_payment_method.id,
        })
        pos_make_payment.with_context(context_payment).check()

    def test_pos_tax_report(self):
        self._check_tax_report_content()

    @freeze_time("2020-01-01")
    def _check_tax_report_content(self):
        today = fields.Date.today()
        self.pos_config.open_ui()
        self._create_and_pay_pos_order(1, 30)
        self._create_and_pay_pos_order(-1, 40)
        self.pos_config.current_session_id.action_pos_session_closing_control()

        self.env.flush_all()
        report_opt = self._generate_options(self.tax_report, today, today)
        self.assertLinesValues(
            self.tax_report._get_lines(report_opt),
            #   Name                                                Balance
            [   0,                                                  1],
            [
                (self.pos_tax_report_line_invoice_base.name,        30),
                (self.pos_tax_report_line_invoice_tax.name,         3),
                (self.pos_tax_report_line_refund_base.name,         40),
                (self.pos_tax_report_line_refund_tax.name,          4),
            ],
            report_opt,
        )
