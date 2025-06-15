from odoo.tests.common import TransactionCase, tagged 

@tagged('-at_install', 'post_install', 'mytest')
class TestSaleOrderTrackSubtype(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'state': 'draft',
        })

    def test_track_subtype_when_state_changes_to_sale(self):
        self.sale_order.write({'state': 'sale'})
        result = self.sale_order._track_subtype({'state': 'draft'})
        expected = self.env.ref('sale.mt_order_confirmed')
        self.assertEqual(result, expected, "Should return 'order confirmed' subtype")

    def test_track_subtype_when_state_changes_to_sent(self):
        self.sale_order.write({'state': 'sent'})
        result = self.sale_order._track_subtype({'state': 'draft'})
        expected = self.env.ref('sale.mt_order_sent')
        self.assertEqual(result, expected, "Should return 'order sent' subtype")

    def test_track_subtype_default_fallback(self):
        result = self.sale_order._track_subtype({})
        expected = super(type(self.sale_order), self.sale_order)._track_subtype({})
        self.assertEqual(result, expected, "Should fall back to super() for other cases")
