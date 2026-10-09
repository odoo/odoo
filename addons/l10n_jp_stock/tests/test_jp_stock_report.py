# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import new_test_user, tagged
from odoo.tools import html2plaintext


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPStockReport(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('jp')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].external_report_layout_id = cls.env.ref('l10n_jp.external_layout_jp_standard')
        picking_type = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1).out_type_id
        cls.picking = cls.env['stock.picking'].create({
            'name': 'JP-DEL-0001',
            'partner_id': cls.partner_a.id,
            'picking_type_id': picking_type.id,
            'move_ids': [Command.create({'product_id': cls.product_a.id, 'product_uom_qty': 1})],
        })

    def test_slip_titles_head_the_page(self):
        stock_user = new_test_user(self.env, login='jp_stock_user', groups='stock.group_stock_user')
        for report, title in (
            ('stock.report_deliveryslip', 'JP-DEL-0001'),
            ('stock.report_return_document', 'RETURN OF JP-DEL-0001'),
        ):
            with self.subTest(report=report):
                html = self.env['ir.actions.report'].with_user(stock_user)._render_qweb_html(report, self.picking.ids)[0]
                text = html2plaintext(html)

                self.assertEqual(text.count(title), 1)
                self.assertLess(text.index(title), text.index(self.partner_a.name))

    def test_delivery_slip_addresses_the_company_of_a_contact(self):
        self.env['res.lang']._activate_lang('ja_JP')
        company = self.env['res.partner'].create({'name': 'JP Trading', 'vat': 'T7000012050002', 'lang': 'ja_JP'})
        contact = self.env['res.partner'].create({'name': 'Taro Yamada', 'parent_id': company.id, 'lang': 'ja_JP'})
        self.picking.partner_id = contact

        html = self.env['ir.actions.report']._render_qweb_html('stock.report_deliveryslip', self.picking.ids)[0]

        self.assertRegex(html2plaintext(html), r'JP Trading\s+御中')
