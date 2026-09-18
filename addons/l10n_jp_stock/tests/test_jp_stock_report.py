# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import html2plaintext


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPStockReport(AccountTestInvoicingCommon):
    _test_user_groups = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.lang']._activate_lang('ja_JP')
        cls.partner_a.lang = 'ja_JP'
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jis_standard')
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.picking_type_out = cls.warehouse.out_type_id
        cls.customer_location = cls.picking_type_out.default_location_dest_id

    def test_delivery_slip_uses_honorific(self):
        picking = self.env['stock.picking'].create({
            'name': 'JP-DEL-0001',
            'partner_id': self.partner_a.id,
            'picking_type_id': self.picking_type_out.id,
            'move_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
                'uom_id': self.product_a.uom_id.id,
                'location_id': self.picking_type_out.default_location_src_id.id,
                'location_dest_id': self.customer_location.id,
            })],
        })
        picking.action_confirm()

        html = self.env['ir.actions.report'].sudo()._render_qweb_html('stock.report_deliveryslip', picking.ids)[0]
        text = html2plaintext(html)

        self.assertIn('様', text)
