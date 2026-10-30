# Part of Odoo. See LICENSE file for full copyright and licensing details.

import lxml.html

from odoo import Command
from odoo.tests import new_test_user, tagged
from odoo.tools import html2plaintext

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


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

    def test_delivery_slip_addresses_the_contact_under_its_company(self):
        self.env['res.lang']._activate_lang('ja_JP')
        company = self.env['res.partner'].create({'name': 'JP Trading', 'vat': 'T7000012050002', 'lang': 'ja_JP'})
        self.picking.partner_id = self.env['res.partner'].create({'name': 'Taro Yamada', 'parent_id': company.id, 'lang': 'ja_JP'})

        html = self.env['ir.actions.report']._render_qweb_html('stock.report_deliveryslip', self.picking.ids)[0]
        recipient = lxml.html.fromstring(html).xpath("//div[@name='outgoing_delivery_address']//div[@name='recipient_name']")[0]

        self.assertEqual([' '.join(line.text_content().split()) for line in recipient], ['JP Trading', 'Taro Yamada 様'])

    def test_receipt_slip_keeps_the_name_of_our_warehouse(self):
        self.env['res.lang']._activate_lang('ja_JP')
        self.partner_a.lang = 'ja_JP'
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        receipt = self.env['stock.picking'].create({
            'partner_id': self.partner_a.id,
            'picking_type_id': warehouse.in_type_id.id,
            'move_ids': [Command.create({'product_id': self.product_a.id, 'product_uom_qty': 1})],
        })

        html = self.env['ir.actions.report']._render_qweb_html('stock.report_deliveryslip', receipt.ids)[0]
        header = lxml.html.fromstring(html).find_class('o_jp_standard_header')[0]

        self.assertIn(warehouse.partner_id.name, header.xpath(".//div[@name='outgoing_warehouse_address']")[0].text_content())
        self.assertNotIn(self.partner_a.name, header.text_content())
        self.assertNotIn('様', header.text_content())

    def test_a_company_outside_japan_keeps_the_standard_slip(self):
        self.company_data['company'].account_fiscal_country_id = self.env.ref('base.us')
        company = self.env['res.partner'].create({'name': 'JP Trading'})
        self.picking.partner_id = self.env['res.partner'].create({'name': 'Taro Yamada', 'parent_id': company.id})

        html = self.env['ir.actions.report']._render_qweb_html('stock.report_deliveryslip', self.picking.ids)[0]
        page = lxml.html.fromstring(html).find_class('page')[0]

        self.assertIn('JP-DEL-0001', page.find('.//h2').text_content())
        self.assertIn('JP Trading', html2plaintext(html))
