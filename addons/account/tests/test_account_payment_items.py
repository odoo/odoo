# -*- coding: utf-8 -*-
from datetime import date, datetime, timedelta
from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestAccountPaymentItems(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bill = cls.create_bill(due_date='2023-03-20')
        cls.late_bill = cls.create_bill(due_date='2023-03-01')
        cls.discount_bill = cls.create_bill(due_date='2023-03-20', discount_days=19)
        cls.late_discount_bill = cls.create_bill(due_date='2023-04-20', discount_days=9)

    @classmethod
    def create_bill(cls, due_date, discount_days=None):
        payment_term = cls.create_payment_term(due_date, discount_days)
        bill = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'partner_id': cls.partner_a.id,
            'date': '2023-03-15',
            'invoice_date': '2023-03-01',
            'invoice_date_due': due_date,
            'invoice_payment_term_id': payment_term.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'quantity': 1,
                'name': 'product_a',
                'discount': 10.00,
                'price_unit': 100,
                'tax_ids': [],
                'discount_date': date(2023, 3, 1) + timedelta(days=discount_days) if discount_days else False,
                'date_maturity': due_date,
            })]
        })
        bill.action_post()
        return bill

    @classmethod
    def create_payment_term(cls, due_date, discount_days=None):
        due_days = (datetime.strptime(due_date, '%Y-%m-%d').date() - date(2023, 3, 1)).days
        payment_term = cls.env['account.payment.term'].create({
            'name': 'Payment Term For Testing',
            'early_discount': bool(discount_days),
            'discount_days': discount_days if discount_days else False,
            'discount_percentage': 5,
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 100,
                    'delay_type': 'days_after',
                    'nb_days': due_days,
                }),
            ],
        })
        return payment_term

    @freeze_time("2023-03-15")
    def test_payment_date(self):
        self.assertEqual(str(self.bill.line_ids[0].payment_date), '2023-03-20')
        self.assertEqual(str(self.late_bill.line_ids[0].payment_date), '2023-03-01')
        self.assertEqual(str(self.discount_bill.line_ids[0].payment_date), '2023-03-20')
        self.assertEqual(str(self.late_discount_bill.line_ids[0].payment_date), '2023-04-20')

    def test_search_payment_date(self):
        for today, search, expected in [
            ('2023-03-05', '2023-03-01', self.late_bill),
            ('2023-03-05', '2023-03-30', self.bill + self.late_bill + self.discount_bill + self.late_discount_bill),
            ('2023-03-15', '2023-03-01', self.late_bill),
            ('2023-03-15', '2023-03-30', self.bill + self.late_bill + self.discount_bill),
            ('2023-03-25', '2023-03-01', self.late_bill),
            ('2023-03-25', '2023-03-30', self.bill + self.late_bill + self.discount_bill),
            ('2023-03-25', '2023-06-30', self.bill + self.late_bill + self.discount_bill + self.late_discount_bill),
        ]:
            with freeze_time(today):
                self.assertEqual(self.env['account.move.line'].search([
                    ('payment_date', '=', search),
                    ('partner_id', '=', self.partner_a.id),
                ]).move_id, expected)
