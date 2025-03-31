from unittest.mock import patch

from odoo import Command
from odoo.addons.l10n_es_edi_tbai.tests.common import TestEsEdiTbaiCommonGipuzkoa
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosEdi(TestEsEdiTbaiCommonGipuzkoa, TestPointOfSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_es = cls.env['res.partner'].create({
            'name': 'ES Partner',
            'vat': 'ESF35999705',
            'country_id': cls.env.ref('base.es').id,
            'invoice_edi_format': None,
        })

    @classmethod
    def create_pos_order(cls, session, price_unit):
        return cls.PosOrder.create({
            'session_id': session.id,
            'lines': [
                Command.create({
                    'product_id': cls.product_a.id,
                    'price_unit': price_unit,
                    'qty': 1,
                    'tax_ids': cls._get_tax_by_xml_id('s_iva21b').ids,
                    'price_subtotal': price_unit,
                    'price_subtotal_incl': price_unit * 1.21,
                }),
            ],
            'amount_tax': 0.21 * price_unit,
            'amount_total': 1.21 * price_unit,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

    @classmethod
    def pay_pos_order(cls, pos_order):
        context_make_payment = {
            'active_ids': pos_order.ids,
            'active_id': pos_order.id,
        }
        pos_make_payment = cls.PosMakePayment.with_context(context_make_payment).create({
            'amount': pos_order.amount_total,
        })
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=cls.mock_response_post_invoice_success,
        ):
            pos_make_payment.with_context(context_make_payment).check()

    def test_tbai_pos_order(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        pos_order = self.create_pos_order(current_session, 100.0)
        self.pay_pos_order(pos_order)

        self.assertEqual(pos_order.state, 'paid')
        self.assertEqual(pos_order.l10n_es_tbai_state, 'sent')

    def test_tbai_pos_order_to_invoice(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        pos_order = self.create_pos_order(current_session, 500.0)

        # The amount is above 400 (default simplified invoice limit) so an error should be raised if it's not invoiced
        with self.assertRaises(UserError):
            self.pay_pos_order(pos_order)

        # Now with the pos order invoiced
        pos_order.partner_id = self.partner_es
        pos_order.to_invoice = True
        self.pay_pos_order(pos_order)

        self.assertEqual(pos_order.state, 'invoiced')
        # The edi is handled by the invoice
        self.assertFalse(pos_order.l10n_es_tbai_state)

    def test_tbai_refund_pos_order(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # Create and pay a pos order not invoiced
        pos_order = self.create_pos_order(current_session, 100.0)
        self.pay_pos_order(pos_order)

        # Create the refund
        refund_action = pos_order.refund()
        pos_refund = self.PosOrder.browse(refund_action['res_id'])

        # An error is raised if the refund is invoiced
        pos_refund.to_invoice = True
        with self.assertRaises(UserError):
            self.pay_pos_order(pos_refund)

        # Now works with the refund not invoiced
        pos_refund.to_invoice = False
        self.pay_pos_order(pos_refund)

        self.assertEqual(pos_refund.state, 'paid')
        self.assertEqual(pos_refund.l10n_es_tbai_state, 'sent')

    def test_tbai_refund_invoiced_pos_order(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # Create and pay a pos order not invoiced
        pos_order = self.create_pos_order(current_session, 500.0)
        pos_order.partner_id = self.partner_es
        pos_order.to_invoice = True
        self.pay_pos_order(pos_order)

        # Create the refund
        refund_action = pos_order.refund()
        pos_refund = self.PosOrder.browse(refund_action['res_id'])

        # An error is raised if the refund is not invoiced
        with self.assertRaises(UserError):
            self.pay_pos_order(pos_refund)

        # Now works with the refund invoiced
        pos_refund.to_invoice = True
        self.pay_pos_order(pos_refund)

        self.assertEqual(pos_refund.state, 'invoiced')
        self.assertFalse(pos_refund.l10n_es_tbai_state)
