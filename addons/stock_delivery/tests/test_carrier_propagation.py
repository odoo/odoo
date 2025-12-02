# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch, DEFAULT
from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestCarrierPropagation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env.ref("stock.warehouse0")

        # Set Warehouse as multi steps delivery
        cls.warehouse.delivery_steps = "pick_pack_ship"

        # Create a delivery product and its carrier
        cls.ProductProduct = cls.env['product.product']
        cls.SaleOrder = cls.env['sale.order']
        cls.StockMove = cls.env["stock.move"]

        cls.partner_propagation = cls.env['res.partner'].create({
            'name': 'My Carrier Propagation Customer'})

        cls.product_uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product_delivery_normal = cls.env['product.product'].create({
            'name': 'Normal Delivery Charges',
            'invoice_policy': 'order',
            'type': 'service',
            'list_price': 10.0,
            'categ_id': cls.env.ref('delivery.product_category_deliveries').id,
        })
        cls.normal_delivery = cls.env['delivery.carrier'].create({
            'name': 'Normal Delivery Charges',
            'fixed_price': 10,
            'delivery_type': 'fixed',
            'product_id': cls.product_delivery_normal.id,
        })
        cls.customer_location = cls.env.ref("stock.stock_location_customers")
        cls.output_location = cls.env.ref("stock.stock_location_output")
        cls.super_product = cls.ProductProduct.create({
            'name': 'Super Product',
            'invoice_policy': 'delivery',
        })
        mto_route = cls.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        cls.warehouse.mto_pull_id.procure_method = "make_to_stock"
        cls.mto_product = cls.ProductProduct.create({
            'name': 'MTO Product',
            'invoice_policy': 'delivery',
            'route_ids': [(6, 0, mto_route.ids)],
        })
        cls.rule_pack = cls.warehouse.delivery_route_id.rule_ids.filtered(lambda r: r.picking_type_id == cls.warehouse.pack_type_id)

    def test_carrier_no_propagation(self):
        """
            Set the carrier propagation to False on stock.rule
            Create a Sale Order, confirm it
            Check that the carrier is set on the OUT
            Check that the carrier is not set on the PACK
        """
        self.rule_pack.propagate_carrier = False

        so = self.SaleOrder.create({
            'name': 'Sale order',
            'partner_id': self.partner_propagation.id,
            'partner_invoice_id': self.partner_propagation.id,
            'order_line': [
                (0, 0, {'name': self.super_product.name, 'product_id': self.super_product.id, 'product_uom_qty': 1, 'price_unit': 1,}),
            ]
        })
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': so.id,
            'default_carrier_id': self.normal_delivery.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()
        # Confirm the SO
        so.action_confirm()

        pick = so.picking_ids
        self.assertEqual(self.normal_delivery, pick.carrier_id)
        pick.button_validate()

        pack = pick.move_ids.move_dest_ids.picking_id
        self.assertFalse(pack.carrier_id)

    def test_carrier_propagation(self):
        """
            Set the carrier propagation to True on stock.rule
            Create a Sale Order, confirm it
            Check that the carrier is set on the OUT
            Check that the carrier is set on the PACK
        """
        self.rule_pack.propagate_carrier = True

        for product in [self.super_product, self.mto_product]:
            so = self.SaleOrder.create({
                'name': 'Sale order',
                'partner_id': self.partner_propagation.id,
                'partner_invoice_id': self.partner_propagation.id,
                'order_line': [
                    (0, 0, {'name': product.name, 'product_id': product.id, 'product_uom_qty': 1, 'price_unit': 1,}),
                ]
            })
            delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
                'default_order_id': so.id,
                'default_carrier_id': self.normal_delivery.id,
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.button_confirm()
            # Confirm the SO
            so.action_confirm()

            pick = so.picking_ids
            self.assertEqual(self.normal_delivery, pick.carrier_id)
            pick.button_validate()

            pack = pick.move_ids.move_dest_ids.picking_id
            self.assertEqual(self.normal_delivery, pack.carrier_id)
            pack.button_validate()

            ship = pack.move_ids.move_dest_ids.picking_id
            self.assertEqual(self.normal_delivery, ship.carrier_id)

    def test_route_based_on_carrier_delivery(self):
        """
            Check that the route on the sale order line is selected as per the first priority even if route on shipping mehod is present
            Also, Check that the route on the shipping method is selected if there is no route selected on sale order line
        """
        route1 = self.env['stock.route'].create({
            'name': 'Route1',
            'sale_selectable' : True,
            'shipping_selectable': True,
            'rule_ids': [Command.create({
                'name': 'rule1',
                'location_src_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.customer_location.id,
                'company_id': self.env.company.id,
                'action': 'pull',
                'auto': 'transparent',
                'picking_type_id': self.ref('stock.picking_type_out'),
            })],
        })
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.env.ref('stock.stock_location_stock').id,
        })
        route2 = self.env['stock.route'].create({
            'name': 'Route2',
            'sale_selectable' : True,
            'shipping_selectable':True,
            'rule_ids': [Command.create({
                'name': 'rule2',
                'location_src_id': shelf1_location.id,
                'location_dest_id': self.customer_location.id,
                'company_id': self.env.company.id,
                'action': 'pull',
                'auto': 'transparent',
                'picking_type_id': self.ref('stock.picking_type_out'),
            })],
        })
        self.normal_delivery.write({
            "route_ids": [Command.link(route2.id)]
        })

        sale_order1 = self.SaleOrder.create({
            'partner_id': self.partner_propagation.id,
            'order_line': [Command.create({
                'name': 'Cable Management Box',
                'product_id': self.super_product.id,
                'product_uom_qty': 2,
                'price_unit': 750.00,
                'route_ids': route1.ids,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order1.id,
            'default_carrier_id': self.normal_delivery.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        sale_order1.action_confirm()
        self.assertEqual(sale_order1.picking_ids.location_id, route1.rule_ids.location_src_id)

        # check route without add in sale order line
        sale_order2 = self.SaleOrder.create({
            'partner_id': self.partner_propagation.id,
            'order_line': [Command.create({
                'name': 'Cable Management Box',
                'product_id': self.super_product.id,
                'product_uom_qty': 2,
                'price_unit': 750.00,
            })],
        })

        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order2.id,
            'default_carrier_id': self.normal_delivery.id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        choose_delivery_carrier.button_confirm()

        sale_order2.action_confirm()
        self.assertEqual(sale_order2.picking_ids.location_id, route2.rule_ids.location_src_id)

    def test_carrier_picking_batch_validation(self):
        """
        Create 2 delivery orders with carriers. Make them respectively
        valid and invalid on the carrier side. Validate the pickings in batch
        Since the pickings are processed unbatched on the carrier side the
        "UserError" of the invalid picking can not be raised and should be
        replaced by a warning activity.
        """
        self.warehouse.delivery_steps = "ship_only"
        alien = self.env['res.users'].create({
            'login': 'Mars Man',
            'name': 'Spleton',
            'email': 'alien@mars.com',
            'group_ids': self.env.ref('stock.group_stock_user'),
        })
        super_product_2 = self.ProductProduct.create({
            'name': 'Super Product 2',
            'invoice_policy': 'delivery',
        })
        sale_orders = self.env['sale.order'].create([
            {
                'partner_id': self.partner_propagation.id,
                'order_line': [
                    Command.create({
                        'product_id': self.super_product.id
                    }),
                ]
            },
            {
                'partner_id': self.partner_propagation.id,
                'order_line': [
                    Command.create({
                        'product_id': super_product_2.id
                    }),
                ]
            },
        ])
        for so in sale_orders:
            delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
                'default_order_id': so.id,
                'default_carrier_id': self.normal_delivery.id,
            }))
            choose_delivery_carrier = delivery_wizard.save()
            choose_delivery_carrier.button_confirm()

        def fail_send_to_shipper(pick):
            # side effect to throw an error for a given picking but resolve the normal call for the other
            def _throw_error_on_chosen_picking(self):
                if self == pick:
                    raise UserError("Something went wrong, parcel not returned from Sendcloud: {'weight': ['The weight must be less than 10.001 kg']}")
                else:
                    return DEFAULT
            return _throw_error_on_chosen_picking

        sale_orders.action_confirm()
        for i in range(0, len(sale_orders)):
            # check that a delivery was created for the associated carrier
            self.assertEqual(sale_orders[i].picking_ids.carrier_id.id, sale_orders[i].carrier_id.id)
        pickings = sale_orders.picking_ids
        pickings.action_assign()
        picking_class = 'odoo.addons.stock_delivery.models.stock_picking.StockPicking'
        with patch(picking_class + '.send_to_shipper', new=fail_send_to_shipper(pickings[1])):
            pickings.with_user(alien).button_validate()
        # both pickings should be validated but and activity should have been created for the invalid picking
        self.assertEqual(pickings.mapped('state'), ['done', 'done'])
        self.assertTrue(self.env['mail.activity'].search([('res_model', '=', 'stock.picking'), ('res_id', '=', pickings[1].id), ('user_id', '=', alien.id)], limit=1))
