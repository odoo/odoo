# Part of Odoo. See LICENSE file for full copyright and licensing details.

import lxml.html

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPPurchaseReport(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jp_standard')

    def test_unit_price_column_drops_a_decimal_part_worth_nothing(self):
        order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_a.id, 'product_qty': 2.0, 'price_unit': 105.0})],
        })
        html = self.env['ir.actions.report']._render_qweb_html('purchase.report_purchaseorder', order.ids)[0]
        table = lxml.html.fromstring(html).find_class('o_main_table')[0]
        column = [th.get('name') for th in table.xpath('./thead/tr/th')].index('th_price_unit')

        self.assertEqual([row.xpath('./td')[column].text_content().strip() for row in table.xpath('./tbody/tr')], ['105'])
