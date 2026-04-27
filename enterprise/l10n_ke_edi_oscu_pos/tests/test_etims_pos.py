from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo.addons.l10n_ke_edi_oscu.tests.common import TestKeEdiCommon
from odoo.addons.l10n_ke_edi_oscu.tests.test_live import TestKeEdi
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import float_round


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEtimsPos(TestKeEdiCommon, TestPointOfSaleCommon):

    @classmethod
    @TestKeEdi.setup_country('ke')
    def setUpClass(cls):
        super().setUpClass()

        cls.company.l10n_ke_server_mode = 'demo'

        cls.product3.write({
            'type': 'consu',
            'is_storable': True,
            'l10n_ke_product_type_code': '2',
            'l10n_ke_packaging_unit_id': cls.env['l10n_ke_edi_oscu.code'].search([('code', '=', 'BA')], limit=1).id,
            'unspsc_code_id': cls.env['product.unspsc.code'].search([
                ('code', '=', '52161557'),
            ], limit=1).id,
            'l10n_ke_origin_country_id': cls.env.ref('base.be').id,
            'l10n_ke_packaging_quantity': 2,
            'taxes_id': [Command.set(cls.tax_sale_a.ids)],
            'standard_price': 30
        })

        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_data['company'].id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id

        cls.env['stock.quant'].create({
            'product_id': cls.product3.id,
            'location_id': cls.stock_location.id,
            'quantity': 20.0,
        })

    def test_etims_post_order(self):
        """ Testing the pos order process to make sure everything is correctly sends to eTIMS
        """
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        price_unit = 200
        tax_rate = self.tax_sale_a.amount / 100

        # 1) create the pos order
        pos_order = self.PosOrder.create({
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'lines': [
                Command.create({
                    'product_id': self.product3.id,
                    'price_unit': price_unit,
                    'price_subtotal': price_unit,
                    'price_subtotal_incl': float_round((1 + tax_rate) * price_unit, precision_digits=2),
                    'qty': 1,
                    'tax_ids': self.tax_sale_a.ids,
                }),
            ],
            'amount_tax': float_round(tax_rate * price_unit, precision_digits=2),
            'amount_total': float_round((1 + tax_rate) * price_unit, precision_digits=2),
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        # 2) pay the order
        context_make_payment = {
            'active_ids': pos_order.ids,
            'active_id': pos_order.id,
        }
        pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': pos_order.amount_total,
            'payment_method_id': self.bank_payment_method.id,
        })

        # 3) Send order to eTIMS
        pos_make_payment.with_context(context_make_payment).check()
        pos_order.action_post_order()

        self.assertEqual(pos_order.l10n_ke_oscu_internal_data, 'GRKJVWYCFBPTYQ225X2UEYONVE')
        self.assertEqual(pos_order.l10n_ke_oscu_signature, '123456789ODOOGR3')
        self.assertEqual(pos_order.l10n_ke_oscu_receipt_number, 169)

        # # 4) Send stock move to eTIMS
        self.env.ref('l10n_ke_edi_oscu_stock.ir_cron_send_stock_moves').method_direct_trigger()

        self.assertEqual(pos_order.picking_ids.l10n_ke_oscu_sar_number, 1)

    def test_invoice_order(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        price_unit = 300
        tax_rate = self.tax_sale_a.amount / 100

        # 1) create a pos order
        pos_order = self.PosOrder.create({
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'lines': [
                Command.create({
                    'product_id': self.product3.id,
                    'price_unit': price_unit,
                    'price_subtotal': price_unit,
                    'price_subtotal_incl': float_round((1 + tax_rate) * price_unit, precision_digits=2),
                    'qty': 1,
                    'tax_ids': self.tax_sale_a.ids,
                }),
            ],
            'amount_tax': float_round(tax_rate * price_unit, precision_digits=2),
            'amount_total': float_round((1 + tax_rate) * price_unit, precision_digits=2),
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
        })

        # 2) pay the order
        context_make_payment = {
            'active_ids': pos_order.ids,
            'active_id': pos_order.id,
        }
        pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': pos_order.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })

        # 3) Send order to eTIMS
        pos_make_payment.with_context(context_make_payment).check()
        pos_order.action_post_order()

        # As the etims call is send in the pos order, we just copy the values from pos order to invoice
        # to avoid duplicate calls
        self.assertEqual(pos_order.l10n_ke_oscu_internal_data, pos_order.account_move.l10n_ke_oscu_internal_data)
        self.assertEqual(pos_order.l10n_ke_oscu_signature, pos_order.account_move.l10n_ke_oscu_signature)
        self.assertEqual(pos_order.l10n_ke_oscu_receipt_number, pos_order.account_move.l10n_ke_oscu_receipt_number)

    def test_cant_send_order_with_product_out_of_stock(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        price_unit = 200
        tax_rate = self.tax_sale_a.amount / 100

        # 1) create the pos order
        pos_order = self.PosOrder.create({
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'lines': [
                Command.create({
                    'product_id': self.product3.id,
                    'price_unit': price_unit,
                    'price_subtotal': price_unit,
                    'price_subtotal_incl': float_round((1 + tax_rate) * price_unit, precision_digits=2),
                    'qty': 100,
                    'tax_ids': self.tax_sale_a.ids,
                }),
            ],
            'amount_tax': float_round(tax_rate * price_unit, precision_digits=2),
            'amount_total': float_round((1 + tax_rate) * price_unit, precision_digits=2),
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        # 2) pay the order
        context_make_payment = {
            'active_ids': pos_order.ids,
            'active_id': pos_order.id,
        }
        pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': pos_order.amount_total,
            'payment_method_id': self.bank_payment_method.id,
        })

        with self.assertRaises(UserError):
            # 3) Send order to eTIMS, should raise an error
            pos_make_payment.with_context(context_make_payment).check()
            pos_order.action_post_order()

    def test_refund_pos_order(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        price_unit = 300
        tax_rate = self.tax_sale_a.amount / 100

        # 1) create a pos order
        pos_order = self.PosOrder.create({
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'lines': [
                Command.create({
                    'product_id': self.product3.id,
                    'price_unit': price_unit,
                    'price_subtotal': price_unit,
                    'price_subtotal_incl': float_round((1 + tax_rate) * price_unit, precision_digits=2),
                    'qty': 1,
                    'tax_ids': self.tax_sale_a.ids,
                }),
            ],
            'amount_tax': float_round(tax_rate * price_unit, precision_digits=2),
            'amount_total': float_round((1 + tax_rate) * price_unit, precision_digits=2),
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
        })

        # 2) pay the order
        context_make_payment = {
            'active_ids': pos_order.ids,
            'active_id': pos_order.id,
        }
        pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': pos_order.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })

        # 3) Send order to eTIMS
        pos_make_payment.with_context(context_make_payment).check()
        pos_order.action_post_order()

        # 4) Refund the order
        refund_action = pos_order.refund()
        refund = self.PosOrder.browse(refund_action['res_id'])

        context_make_payment = {
            'active_ids': refund.ids,
            'active_id': refund.id,
        }
        pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })

        # 5) Send order to eTIMS
        pos_make_payment.with_context(context_make_payment).check()
        refund.action_post_order()

        self.assertEqual(refund.l10n_ke_oscu_internal_data, 'GRKJVWYCFBPTYQ225X2UEYONVE')
        self.assertEqual(refund.l10n_ke_oscu_signature, '123456789ODOOGR3')
        self.assertEqual(refund.l10n_ke_oscu_receipt_number, 169)
