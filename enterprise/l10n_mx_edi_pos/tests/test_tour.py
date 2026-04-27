# -*- coding: utf-8 -*-
from .common import TestMxEdiPosCommon
import odoo
from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_generic_localization import TestGenericLocalization
from odoo.tools import mute_logger


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
        self.start_tour("/odoo", "l10n_mx_edi_pos.tour_invoice_order", login=self.env.user.login)

    def test_mx_pos_invoice_order_default_usage(self):
        self.start_tour("/odoo", "l10n_mx_edi_pos.tour_invoice_order_default_usage", login=self.env.user.login)

    def test_mx_pos_invoice_previous_order(self):
        self.start_tour("/odoo", "l10n_mx_edi_pos.tour_invoice_previous_order", login=self.env.user.login)
        invoice = self.env['account.move'].search([('move_type', '=', 'out_invoice')], order='id desc', limit=1)
        self.assertRecordValues(invoice, [{
            'partner_id': self.partner_mx.id,
            'l10n_mx_edi_usage': "G03",
            'l10n_mx_edi_cfdi_to_public': False,
        }])

    def test_mx_pos_invoice_previous_order_default_usage(self):
        self.start_tour("/odoo", "l10n_mx_edi_pos.tour_invoice_previous_order_default_usage", login=self.env.user.login)
        invoice = self.env['account.move'].search([('move_type', '=', 'out_invoice')], order='id desc', limit=1)
        self.assertRecordValues(invoice, [{
            'partner_id': self.partner_mx.id,
            'l10n_mx_edi_usage': "I01",
            'l10n_mx_edi_cfdi_to_public': True,
        }])

    def test_mx_pos_refund_discount_order(self):
        self.product1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'is_storable': True,
            'list_price': 10.0,
            'taxes_id': False,
        })
        self.product_discount = self.env['product.product'].create({
            'name': 'Test Discount',
            'is_storable': False,
            'list_price': -0.10,
            'taxes_id': False,
        })
        self.main_pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            "name": "Order 0001",
            "pos_reference": "Order 12345-123-1234",
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': self.partner_mx.id,
            'access_token': '1234567890',
            'lines': [odoo.Command.create({
                'name': "OL/0001",
                'product_id': self.product1.id,
                'price_unit': 10,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': False,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            }),
            odoo.Command.create({
                'name': "OL/0002",
                'product_id': self.product_discount.id,
                'price_unit': -0.10,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': False,
                'price_subtotal': -0.10,
                'price_subtotal_incl': -0.10,
            })],
            'amount_tax': 0,
            'amount_total': 9.90,
            'amount_paid': 9.90,
            'amount_return': 0,
        })
        self.make_payment(self.pos_order, self.main_pos_config.payment_method_ids[0], 9.90)
        self.config.current_session_id.action_pos_session_closing_control()
        self.start_tour("/odoo", "l10n_mx_edi_pos.tour_refund_discount_order", login=self.env.user.login)

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
            'is_storable': True,
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
            'vat': 'GODE561231GR8',
            'invoice_l10n_mx_edi_usage': 'D10',
            'partner_l10n_mx_edi_fiscal_regime': '624',
            'csrf_token': odoo.http.Request.csrf_token(self)
        }
        self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', data=get_invoice_data)
        self.assertEqual(self.env['res.partner'].sudo().search_count([('name', '=', 'AAA Partner')]), 1)
        self.assertTrue(self.pos_order.is_invoiced, "The pos order should have an invoice")
        self.assertEqual(self.pos_order.account_move.l10n_mx_edi_usage, 'D10', 'Invoice values not saved')
        self.assertEqual(self.new_partner.l10n_mx_edi_fiscal_regime, '624', 'Partner values not saved')

    def test_settle_account_mx(self):
        if self.env['ir.module.module']._get('pos_settle_due').state != 'installed':
            self.skipTest("pos_settle_due needs to be installed")

        self.partner_test_1.country_id = self.env.ref('base.mx').id
        self.partner_test_1.is_company = True

        # create customer account payment method
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        # add customer account payment method to pos config
        self.main_pos_config.write({
            'payment_method_ids': [(4, self.customer_account_payment_method.id, 0)],
        })

        self.assertEqual(self.partner_test_1.total_due, 0)

        self.main_pos_config.with_user(self.pos_admin).open_ui()
        current_session = self.main_pos_config.current_session_id

        order = self.env['pos.order'].create({
            'company_id': self.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_test_1.id,
            'lines': [odoo.Command.create({
                'product_id': self.product.id,
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
            'last_order_preparation_change': '{}'
        })

        self.make_payment(order, self.customer_account_payment_method, 10.0)

        self.assertEqual(self.partner_test_1.total_due, 10)
        current_session.action_pos_session_closing_control()

        self.main_pos_config.with_user(self.user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_settle_account_due', login="accountman")
        self.assertEqual(self.partner_test_1.total_due, 0)

    def test_usage_mx_pos_invoice_order(self):
        self.main_pos_config.open_ui()

        self.product_a = self.env['product.product'].create({
            'name': 'Test Product 1',
            'is_storable': True,
            'list_price': 10.0,
            'taxes_id': False,
        })
        order_data = {
            "amount_paid": 10,
            "amount_tax": 0,
            "amount_return": 0,
            "amount_total": 10,
            "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            "fiscal_position_id": False,
            "lines": [
                Command.create({
                    "discount": 0,
                    "pack_lot_ids": [],
                    "price_unit": 10.0,
                    "product_id": self.product_a.id,
                    "price_subtotal": 10.0,
                    "price_subtotal_incl": 10.0,
                    "tax_ids": [[6, False, []]],
                    "qty": 1,
                }),
            ],
            "name": "Order 12345-123-1234",
            "partner_id": self.partner_a.id,
            "session_id": self.main_pos_config.current_session_id.id,
            "sequence_number": 2,
            "payment_ids": [
                    Command.create({
                        "amount": 10,
                        "name": fields.Datetime.now(),
                        "payment_method_id": self.bank_payment_method.id,
                    }),
            ],
            "uuid": "12345-123-1234",
            "last_order_preparation_change": "{}",
            "user_id": self.env.uid,
            "to_invoice": False,
            "l10n_mx_edi_usage": False,
        }

        order = self.env["pos.order"].sync_from_ui([order_data])["pos.order"][0]
        self.assertTrue(order, "No POS order was created during the tour.")

        usage = order['l10n_mx_edi_usage']
        self.assertTrue(usage, "The invoice has no usage set.")
        self.assertEqual(usage, "G03", f"Expected CFDI usage to be 'G03', got '{usage}' instead.")

    def test_refund_with_gift_card_mx(self):
        """
        Tests that in the case of a refund with a gift card involved, the customer can
        still pay for the order, and that the points will go up on the gift card, depending
        on how much the refunded product was worth.
        """
        if self.env['ir.module.module']._get('pos_loyalty').state != 'installed':
            self.skipTest("pos_loyalty needs to be installed")

        self.main_pos_config.with_user(self.pos_user).open_ui()
        LoyaltyProgram = self.env['loyalty.program']
        (LoyaltyProgram.search([])).write({'pos_ok': False})
        self.env.ref('loyalty.gift_card_product_50').write({'active': True})

        program_id = LoyaltyProgram.create_from_template('gift_card')['res_id']
        gift_card_program = LoyaltyProgram.browse(program_id)
        gift_card_program.write({'name': 'Test Gift Card Program'})
        self.env["loyalty.generate.wizard"].with_context(
            {"active_id": gift_card_program.id}
        ).create({"coupon_qty": 1, 'points_granted': 1}).generate_coupons()
        gift_card_program.coupon_ids.code = '043123456'

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_refund_with_gift_card_mx', login="pos_user")
        self.assertEqual(gift_card_program.coupon_ids.points, 4.2)

    def test_refund_with_discount(self):
        """
        Tests that when a refund is processed it's total amount does not exceed the original order total.
        """
        if self.env['ir.module.module']._get('pos_discount').state != 'installed':
            self.skipTest("pos_discount needs to be installed")

        self.main_pos_config.module_pos_discount = True
        self.main_pos_config.discount_product_id = self.env.ref("pos_discount.product_product_consumable", raise_if_not_found=False)
        self.main_pos_config.with_user(self.pos_user).open_ui()

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_refund_with_discount', login="pos_user")

    @mute_logger('odoo.http')
    def test_invoice_to_general_public(self):
        self.partner_mx.write({
            "zip": "",
            "country_id": ""
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, "tour_invoice_to_general_public", login="pos_user")


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestGenericMX(TestGenericLocalization):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('mx')
    def setUpClass(cls):
        super().setUpClass()
