# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPSummaryInvoice(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        cls.startClassPatcher(freeze_time('2026-11-17'))
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('sales_team.group_sale_salesman')
        cls.product_a.invoice_policy = 'order'
        cls.partner_a.l10n_jp_closing_day_ids = cls.env.ref('l10n_jp_sale.closing_day_15')

    def _create_order(self, date_order, **values):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': date_order,
            'order_line': [Command.create({'product_id': self.product_a.id})],
            **values,
        })
        order.action_confirm()
        # Confirming an order resets its date.
        order.date_order = date_order
        return order

    def test_order_closes_on_the_first_closing_date_from_its_date(self):
        self.partner_a.l10n_jp_closing_day_ids = self.env.ref('l10n_jp_sale.closing_day_15') + self.env.ref('l10n_jp_sale.closing_day_end_of_month')
        orders = self.env['sale.order'].concat(
            self._create_order(date_order)
            for date_order in ('2026-11-14 03:00:00', '2026-11-15 03:00:00', '2026-11-16 03:00:00', '2027-02-16 03:00:00')
        )

        self.assertEqual(orders.mapped('l10n_jp_closing_date'), [
            fields.Date.to_date('2026-11-15'),
            fields.Date.to_date('2026-11-15'),
            fields.Date.to_date('2026-11-30'),
            fields.Date.to_date('2027-02-28'),
        ])

    def test_closed_orders_are_billed_together_at_the_last_closing_date(self):
        payment_term = self.env.ref(f'account.{self.env.company.id}_l10n_jp_payment_term_end_of_2nd_following_month')
        other_site = self.env['res.partner'].create({'name': "Other site", 'type': 'delivery', 'parent_id': self.partner_a.id})
        orders = (
            self._create_order('2026-10-10 03:00:00', payment_term_id=payment_term.id)
            + self._create_order('2026-11-10 03:00:00', payment_term_id=payment_term.id, partner_shipping_id=other_site.id)
        )

        invoice = orders._create_invoices()

        self.assertRecordValues(invoice, [{
            'invoice_date': fields.Date.to_date('2026-11-15'),
            'invoice_date_due': fields.Date.to_date('2027-01-31'),
        }])
        self.assertEqual(invoice.line_ids.sale_line_ids.order_id, orders)

    def test_order_missed_its_closing_once_a_later_closing_date_has_passed(self):
        orders = self._create_order('2026-10-15 03:00:00') + self._create_order('2026-10-16 03:00:00')

        self.assertEqual(orders.mapped('l10n_jp_missed_closing'), [True, False])

    def test_summary_invoice_is_due_at_the_next_closing_date(self):
        self.partner_a.write({
            'l10n_jp_closing_day_ids': [Command.link(self.env.ref('l10n_jp_sale.closing_day_end_of_month').id)],
            'l10n_jp_pay_at_next_closing': True,
        })
        order = self._create_order('2026-11-10 03:00:00', payment_term_id=self.pay_terms_b.id)

        invoice = order._create_invoices()
        invoice.action_post()

        self.assertRecordValues(invoice, [{
            'invoice_date': fields.Date.to_date('2026-11-15'),
            'invoice_date_due': fields.Date.to_date('2026-11-30'),
            'invoice_payment_term_id': False,
        }])
        self.assertEqual(invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term').date_maturity, fields.Date.to_date('2026-11-30'))

    def test_order_billed_before_its_closing_date_keeps_the_invoice_date_empty(self):
        order = self._create_order('2026-11-16 03:00:00')

        invoice = order._create_invoices()

        self.assertFalse(invoice.invoice_date)
