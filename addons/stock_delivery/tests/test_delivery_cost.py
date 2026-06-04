# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import common, Form

@common.tagged('post_install', '-at_install')
class TestDeliveryCost(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_18 = cls.env['res.partner'].create({'name': 'My Test Customer'})
        cls.product_4 = cls.env['product.product'].create({'name': 'A product to deliver', 'weight': 1.0})
        cls.product_delivery = cls.env['product.product'].create({
            'name': 'Delivery Charges',
            'type': 'service',
            'list_price': 40.0,
            'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
        })
        cls.delivery_carrier = cls.env['delivery.carrier'].create({
            'name': 'Delivery Now Free Over 100',
            'fixed_price': 40,
            'margin': 50,
            'delivery_type': 'fixed',
            'invoice_policy': 'real',
            'product_id': cls.product_delivery.id,
            'free_over': False,
        })
        cls.package_type = cls.env['stock.package.type'].create({
            'name': 'Simple Package Type',
            'base_weight': 1.0,
        })
        cls.usd_currency = cls.env.ref('base.USD')
        cls.eur_currency = cls.env.ref('base.EUR')

    def test_delivery_real_cost(self):
        """Ensure that the price is correctly set on the delivery line in the case of a Back Order
        """
        so = self.env['sale.order'].create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'order_line': [(0, 0, {
                'name': 'PC Assamble + 2GB RAM',
                'product_id': self.product_4.id,
                'product_uom_qty': 2,
                'price_unit': 120.00,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': so.id,
            'default_carrier_id': self.delivery_carrier.id,
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

    def test_delivery_real_cost_locked_so(self):
        """Real shipping cost must be pushed onto the delivery line after
        shipping when the SO is locked, while a regular write on the same
        protected fields must be blocked
        """
        self.env.user.group_ids += self.env.ref("sale.group_auto_done_setting")
        so = self.env['sale.order'].create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'order_line': [(0, 0, {
                'name': 'PC Assemble + 2GB RAM',
                'product_id': self.product_4.id,
                'product_uom_qty': 1,
                'price_unit': 120.00,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': so.id,
            'default_carrier_id': self.delivery_carrier.id,
        }))
        delivery_wizard.save().button_confirm()

        delivery_line = so.order_line.filtered('is_delivery')
        self.assertEqual(len(delivery_line), 1)
        self.assertEqual(delivery_line.price_unit, 0)
        so.action_confirm()
        self.assertTrue(so.locked)

        # Direct write on the locked delivery line (no context flag) must raise
        with self.assertRaises(UserError):
            delivery_line.write({'price_unit': 99.0})

        # Validating the picking sets the allow_delivery_cost_update context
        # so the real carrier price is written through the lock
        picking = so.picking_ids[0]
        picking.move_ids.quantity = 1.0
        picking.move_ids.picked = True
        picking._action_done()
        self.assertEqual(picking.carrier_price, 40.0)
        self.assertEqual(delivery_line.price_unit, picking.carrier_price)

    def test_get_package_currency(self):
        '''
        Ensure packages returned by `_get_packages_from_picking` and `_get_packages_from_order` have
        the correct currency.
        '''
        self.env.company.currency_id = self.usd_currency
        eur_pricelist = self.env['product.pricelist'].create({
            'name': 'EUR Pricelist',
            'currency_id': self.eur_currency.id,
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner_18.id,
            'partner_invoice_id': self.partner_18.id,
            'partner_shipping_id': self.partner_18.id,
            'pricelist_id': eur_pricelist.id,
            'order_line': [Command.create({
                'name': 'PC Assemble + 2GB RAM',
                'product_id': self.product_4.id,
                'product_uom_qty': 2,
                'price_unit': 120.00,
            })],
        })
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': so.id,
            'default_carrier_id': self.delivery_carrier.id,
        }))
        delivery_wizard.save().button_confirm()
        self.assertTrue(so.order_line.filtered('is_delivery'))
        so.action_confirm()

        package = self.env['delivery.carrier']._get_packages_from_order(so, self.package_type)
        self.assertEqual(package[0].currency_id, self.eur_currency)
        picking = so.picking_ids[0]
        self.assertEqual(picking.company_id.currency_id, self.usd_currency)
        package = self.env['delivery.carrier']._get_packages_from_picking(picking, self.package_type)
        self.assertEqual(package[0].currency_id, self.eur_currency)
