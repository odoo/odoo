# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form

@common.tagged('post_install', '-at_install')
class TestDeliveryCost(common.TransactionCase):

    def test_delivery_real_cost(self):
        """Ensure that the price is correctly set on the delivery line in the case of a Back Order
        """
        self.partner_18 = self.env['res.partner'].create({'name': 'My Test Customer'})
        self.product_4 = self.env['product.product'].create({'name': 'A product to deliver', 'weight': 1.0})
        self.product_uom_unit = self.env.ref('uom.product_uom_unit')

        product_delivery = self.env['product.product'].create({
            'name': 'Delivery Charges',
            'type': 'service',
            'list_price': 40.0,
            'categ_id': self.env.ref('delivery.product_category_deliveries').id,
        })
        delivery_carrier = self.env['delivery.carrier'].create({
            'name': 'Delivery Now Free Over 100',
            'fixed_price': 40,
            'delivery_type': 'fixed',
            'invoice_policy': 'real',
            'product_id': product_delivery.id,
            'free_over': False,
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'order_line': [(0, 0, {
                'name': 'PC Assamble + 2GB RAM',
                'product_id': self.product_4.id,
                'product_uom_qty': 2,
                'product_uom': self.product_uom_unit.id,
                'price_unit': 120.00,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': so.id,
            'default_carrier_id': delivery_carrier.id,
        }))
        delivery_wizard.save().button_confirm()

        delivery_line = so.order_line.filtered('is_delivery')
        self.assertEqual(len(delivery_line), 1)
        self.assertEqual(
            delivery_line.price_unit,
            0,
            "The invoicing policy of the carrier is set to 'real cost' and that cost is not yet "
            "known, hence the 0 value"
        )
        so.action_confirm()

        picking = so.picking_ids[0]
        self.assertEqual(picking.carrier_id.id, so.carrier_id.id)
        picking.move_ids[0].quantity = 1.0
        self.assertGreater(picking.shipping_weight, 0.0)

        # Confirm picking for one quantiy and create a back order for the second
        picking.move_ids.picked = True
        picking._action_done()
        self.assertEqual(picking.carrier_price, 40.0)
        # Check that the delivery cost (previously set to 0) has been correctly updated
        self.assertEqual(delivery_line.price_unit, picking.carrier_price)

        # Confirm the back order
        bo = picking.backorder_ids
        bo.move_ids[0].quantity = 1.0
        self.assertGreater(bo.shipping_weight, 0.0)
        bo.move_ids.picked = True
        bo._action_done()
        self.assertEqual(bo.carrier_price, 40.0)

        new_delivery_line = so.order_line.filtered('is_delivery') - delivery_line
        self.assertEqual(len(new_delivery_line), 1)
        self.assertEqual(new_delivery_line.price_unit, bo.carrier_price)
