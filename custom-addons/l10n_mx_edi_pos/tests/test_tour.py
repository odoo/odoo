# -*- coding: utf-8 -*-
from .common import TestMxEdiPosCommon
import odoo
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(TestMxEdiPosCommon, TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_mx.write({
            "name": "Arturo Garcia",
            "l10n_mx_edi_usage": "I01",
        })

    def test_mx_pos_invoice_order(self):
        self.start_tour("/web", "l10n_mx_edi_pos.tour_invoice_order", login=self.env.user.login)

    def test_mx_pos_invoice_order_default_usage(self):
        self.start_tour("/web", "l10n_mx_edi_pos.tour_invoice_order_default_usage", login=self.env.user.login)

    def test_mx_pos_invoice_previous_order(self):
        self.start_tour("/web", "l10n_mx_edi_pos.tour_invoice_previous_order", login=self.env.user.login)
        invoice = self.env['account.move'].search([('move_type', '=', 'out_invoice')], order='id desc', limit=1)
        self.assertRecordValues(invoice, [{
            'partner_id': self.partner_mx.id,
            'l10n_mx_edi_usage': "G03",
            'l10n_mx_edi_cfdi_to_public': True,
        }])

    def test_mx_pos_invoice_previous_order_default_usage(self):
        self.start_tour("/web", "l10n_mx_edi_pos.tour_invoice_previous_order_default_usage", login=self.env.user.login)
        invoice = self.env['account.move'].search([('move_type', '=', 'out_invoice')], order='id desc', limit=1)
        self.assertRecordValues(invoice, [{
            'partner_id': self.partner_mx.id,
            'l10n_mx_edi_usage': "I01",
            'l10n_mx_edi_cfdi_to_public': True,
        }])

    def test_qr_code_receipt_mx(self):
        """This test make sure that no user is created when a partner is set on the PoS order.
            It also makes sure that the invoice is correctly created.
        """
        self.authenticate(None, None)
        self.new_partner = self.env['res.partner'].create({
            'name': 'AAA Partner',
            'zip': '12345',
            'country_id': self.env.company.country_id.id,
        })
        self.product1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'type': 'product',
            'list_price': 10.0,
            'taxes_id': False,
        })
        self.main_pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': self.new_partner.id,
            'access_token': '1234567890',
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
                'price_unit': 10,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': False,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_tax': 10,
            'amount_total': 10,
            'amount_paid': 10.0,
            'amount_return': 10.0,
        })
        self.main_pos_config.current_session_id.close_session_from_ui()
        get_invoice_data = {
            'access_token': self.pos_order.access_token,
            'name': self.new_partner.name,
            'email': "test@test.com",
            'company_name': self.new_partner.company_name,
            'street': "Test street",
            'city': "Test City",
            'zipcode': self.new_partner.zip,
            'country_id': self.new_partner.country_id.id,
            'state_id': self.new_partner.state_id,
            'phone': "123456789",
            'invoice_l10n_mx_edi_usage': 'D10',
            'partner_l10n_mx_edi_fiscal_regime': '624',
            'csrf_token': odoo.http.Request.csrf_token(self)
        }
        self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', data=get_invoice_data)
        self.assertEqual(self.env['res.partner'].sudo().search_count([('name', '=', 'AAA Partner')]), 1)
        self.assertTrue(self.pos_order.is_invoiced, "The pos order should have an invoice")
        self.assertEqual(self.pos_order.account_move.l10n_mx_edi_usage, 'D10', 'Invoice values not saved')
        self.assertEqual(self.new_partner.l10n_mx_edi_fiscal_regime, '624', 'Partner values not saved')
