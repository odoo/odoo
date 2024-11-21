# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUnexpectedAmount(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context={
            **cls.env.context,
            'disable_abnormal_invoice_detection': False,
        })

    def _invoice_vals(self, date='2020-01-01', price_unit=100):
        return {
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': date,
            'line_ids': [
                Command.create({
                    'name': 'product',
                    'price_unit': price_unit,
                    'tax_ids': [Command.clear()],
                })
            ],
        }

    def test_higher_amount(self):
        base = self.env['account.move'].create([self._invoice_vals(price_unit=100) for i in range(10)])
        base.action_post()
        bills = self.env['account.move'].create([
            self._invoice_vals(price_unit=100),
            self._invoice_vals(price_unit=200),
            self._invoice_vals(price_unit=50),
            self._invoice_vals(price_unit=10),
        ])
        self.assertFalse(bills[0].abnormal_amount_warning, "The price of 100 is not deviant and thus shouldn't trigger a warning")
        self.assertTrue(bills[1].abnormal_amount_warning, "The price of 200 is deviant and thus should trigger a warning")
        self.assertTrue(bills[2].abnormal_amount_warning, "The price of 50 is deviant and thus should trigger a warning")
        self.assertTrue(bills[3].abnormal_amount_warning, "The price of 10 is deviant and thus should trigger a warning")

        # cleaning the bills context to have an unbiased env test for the wizard trigerring
        bills = bills.with_context({
            k: v for k, v in self.env.context.items() if k != 'disable_abnormal_invoice_detection'
        })

        wizard_thrown = bills[0].action_post()
        self.assertFalse(wizard_thrown,
                         "Invoice is not deviant, no wizard should be thrown")

        wizard_thrown = bills[1].action_post()
        self.assertFalse(wizard_thrown,
                         "The amount is deviant but the context key isn't set, the wizard shouldn't be thrown")

        wizard_thrown = bills[2].with_context(disable_abnormal_invoice_detection=True).action_post()
        self.assertFalse(wizard_thrown,
                         "The amount is deviant and the context key is set to True, the wizard shouldn't be thrown")

        wizard_thrown = bills[3].with_context(disable_abnormal_invoice_detection=False).action_post()
        self.assertTrue(wizard_thrown,
                        "The amount is deviant and the context key is set to False, the wizard shouldn't be thrown")

    def test_date_too_soon_year(self):
        base = self.env['account.move'].create([
            self._invoice_vals(date=f'{year}-01-01')
            for year in range(2000, 2010)
        ])
        base.action_post()

        move = self.env['account.move'].create(self._invoice_vals(date='2010-01-01'))
        self.assertFalse(move.abnormal_date_warning)
        move = self.env['account.move'].create(self._invoice_vals(date='2009-06-01'))
        self.assertTrue(move.abnormal_date_warning)

    def test_date_too_soon_month(self):
        # We get one invoice on the last day of the month from December 2019 to September 2020
        base = self.env['account.move'].create([
            self._invoice_vals(date=date(2020, month, 1) - timedelta(days=1))
            for month in range(1, 11)
        ])
        base.action_post()

        # No issue in having an invoice missing a period, it is the vendor's responsibility
        move_november = self.env['account.move'].create(self._invoice_vals(date=date(2020, 11, 30)))
        self.assertFalse(move_november.abnormal_date_warning)
        # The next invoice being on the last day of november is expected
        move_october = self.env['account.move'].create(self._invoice_vals(date=date(2020, 10, 31)))
        self.assertFalse(move_october.abnormal_date_warning)
        # But any invoice before the threshold is not expected
        move_october2 = self.env['account.move'].create(self._invoice_vals(date=date(2020, 10, 20)))
        self.assertTrue(move_october2.abnormal_date_warning)

        # If we posted the one with the abnormal date, then the other one becomes abnormal
        move_october2._post(soft=False)
        move_october.invalidate_recordset(['abnormal_date_warning'])
        self.assertTrue(move_october.abnormal_date_warning)
