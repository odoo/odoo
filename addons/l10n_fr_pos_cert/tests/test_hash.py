from odoo.addons.point_of_sale.tests.common import CommonPosTest
from odoo.addons.account_edi.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestHash(CommonPosTest):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()

    def test_hashes_should_be_equal_if_no_alteration(self):
        product1 = self.env['product.product'].create({
            'name': 'product1',
        })

        self.pos_config_usd.open_ui()
        pos_session = self.pos_config_usd.current_session_id
        draft_order = {
            'access_token': False,
            'amount_paid': 0,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': 0,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'lines': [],
            'name': '/',
            'partner_id': False,
            'session_id': pos_session.id,
            'sequence_number': 2,
            'payment_ids': [],
            'uuid': '12345-123-1234',
            'last_order_preparation_change': '{}',
            'user_id': self.env.uid,
            'state': 'draft',
        }

        self.env['pos.order'].sync_from_ui([draft_order])
        self.env.invalidate_all()

        paid_order = {
            'access_token': False,
            'amount_paid': 20,
            'amount_return': -5.0,
            'amount_tax': 0,
            'amount_total': 15.0,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'lines': [[0,
                0,
                {'discount': 0,
                'pack_lot_ids': [],
                'price_unit': 15.0,
                'product_id': product1.id,
                'price_subtotal': 15.0,
                'price_subtotal_incl': 15.0,
                'qty': 1,
                'tax_ids': []}]],
            'name': 'Order 12345-123-1234',
            'partner_id': False,
            'session_id': pos_session.id,
            'sequence_number': 2,
            'payment_ids': [[0,
                0,
                {'amount': 20.0,
                'name': fields.Datetime.now(),
                'payment_method_id': self.cash_payment_method.id}]],
            'uuid': '12345-123-1234',
            'last_order_preparation_change': '{}',
            'user_id': self.env.uid,
            'state': 'paid',
        }

        self.env['pos.order'].sync_from_ui([paid_order])
        self.env.invalidate_all()

        posted_order = self.env['pos.order'].search([('uuid', '=', '12345-123-1234')])
        self.assertEqual(posted_order.state, 'paid')

        self.pos_config_usd.current_session_id.action_pos_session_closing_control()

        self.assertEqual(posted_order.l10n_fr_hash, posted_order._compute_hash(''))
