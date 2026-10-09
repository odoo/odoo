# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import html2plaintext


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPSaleReport(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('sales_team.group_sale_salesman')
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jp_standard')
        # l10n_din5008_sale restyles the unit price cell for every company on a full install.
        cls.env['ir.ui.view'].search([('key', '=', 'l10n_din5008_sale.report_saleorder_document')]).active = False

    def test_unit_price_column_keeps_its_decimals_under_a_surcharge(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({'product_id': self.product_a.id, 'price_unit': price_unit, 'discount': -10.0})
                for price_unit in (200.0, 101.0)
            ],
        })
        html = self.env['ir.actions.report']._render_qweb_html('sale.report_saleorder', order.ids)[0]
        text = html2plaintext(html)

        self.assertIn('220.00', text)
        self.assertIn('111.10', text)
