# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestBankRecWidgetCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_data_2 = cls.setup_multi_currency_data(default_values={
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        }, rate2016=6.0, rate2017=4.0)
        cls.currency_data_3 = cls.setup_multi_currency_data(default_values={
            'name': 'Black Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Black Choco',
            'currency_subunit_label': 'Black Cacao Powder',
        }, rate2016=12.0, rate2017=8.0)

    @classmethod
    def _create_invoice_line(cls, move_type, **kwargs):
        ''' Create an invoice on the fly.'''
        kwargs.setdefault('partner_id', cls.partner_a.id)
        kwargs.setdefault('invoice_date', '2017-01-01')
        kwargs.setdefault('invoice_line_ids', [])
        for one2many_values in kwargs['invoice_line_ids']:
            one2many_values.setdefault('name', 'xxxx')
            one2many_values.setdefault('quantity', 1)
            one2many_values.setdefault('tax_ids', [])

        invoice = cls.env['account.move'].create({
            'move_type': move_type,
            **kwargs,
            'invoice_line_ids': [Command.create(x) for x in kwargs['invoice_line_ids']],
        })
        invoice.action_post()
        return invoice.line_ids\
            .filtered(lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable'))

    @classmethod
    def _create_st_line(cls, amount, date='2019-01-01', payment_ref='turlututu', **kwargs):
        st_line = cls.env['account.bank.statement.line'].create({
            'amount': amount,
            'date': date,
            'payment_ref': payment_ref,
            'journal_id': kwargs.get('journal_id', cls.company_data['default_journal_bank'].id),
            **kwargs,
        })
        # The automatic reconcile cron checks the create_date when considering st_lines to run on.
        # create_date is a protected field so this is the only way to set it correctly
        cls.env.cr.execute("UPDATE account_bank_statement_line SET create_date = %s WHERE id=%s",
                           (st_line.date, st_line.id))
        return st_line

    @classmethod
    def _create_reconcile_model(cls, **kwargs):
        return cls.env['account.reconcile.model'].create({
            'name': "test",
            'rule_type': 'invoice_matching',
            'allow_payment_tolerance': True,
            'payment_tolerance_type': 'percentage',
            'payment_tolerance_param': 0.0,
            **kwargs,
            'line_ids': [
                Command.create({
                    'account_id': cls.company_data['default_account_revenue'].id,
                    'amount_type': 'percentage',
                    'label': f"test {i}",
                    **line_vals,
                })
                for i, line_vals in enumerate(kwargs.get('line_ids', []))
            ],
        })
