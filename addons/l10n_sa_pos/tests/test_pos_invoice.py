from datetime import date, datetime
from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosOrderSaInvoiceDate(TestPoSCommon):

    @freeze_time('2026-03-16 20:30:00')
    def test_pos_invoice_date_uses_riyadh_not_user_tz(self):
        """
        Dubai user creates order at Mar 17 00:30 AM (UTC+4) = Mar 16 20:30 UTC.
        Generic _prepare_invoice_vals sets invoice_date = Mar 17 (Dubai tz).
        Only for POS systems (SA), override must use Riyadh date = Mar 16 instead.
        """
        self.company.account_fiscal_country_id = self.env.ref('base.sa')
        self.config = self.basic_config
        self.open_new_session()
        order = self.env['pos.order'].create({
            'company_id': self.company.id,
            'session_id': self.pos_session.id,
            'partner_id': self.customer.id,
            'date_order': datetime(2026, 3, 16, 20, 30, 0),  # Dubai time in UTC
            'lines': [Command.create({
                'product_id': self.create_product('Test Product', self.categ_basic, 10.0).id,
                'price_unit': 10,
                'discount': 0,
                'qty': 1,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_paid': 10.0,
            'amount_total': 10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
        })
        order.with_context(
            generate_pdf=False, skip_edi_auto_post=True
        )._generate_pos_order_invoice()
        self.assertEqual(order.account_move.invoice_date, date(2026, 3, 16))
