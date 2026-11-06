# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleMrpLotPackaging(TransactionCase):
    """ Nettle is sold by kg, but produced and delivered in bags whose size depends on the lot:
    bags of 20 kg for some lots, bags of 18 kg for others. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref('uom.group_uom') | cls.env.ref('stock.group_production_lot') | cls.env.ref('stock.group_lot_on_delivery_slip')
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.bag_type = cls.env['stock.package.type'].create({'name': 'Paper bag'})
        cls.uom_bag_20, cls.uom_bag_18 = cls.env['uom.uom'].create([
            {'name': f'x {size} kg', 'relative_factor': size, 'relative_uom_id': cls.uom_kg.id, 'package_type_id': cls.bag_type.id}
            for size in (20, 18)
        ])
        cls.category = cls.env['product.category'].create({'name': 'Herbs', 'packaging_reserve_method': 'lot'})
        cls.nettle = cls.env['product.product'].create({
            'name': 'Nettle',
            'is_storable': True,
            'tracking': 'lot',
            'categ_id': cls.category.id,
            'uom_id': cls.uom_kg.id,
            'uom_ids': [Command.set((cls.uom_bag_20 | cls.uom_bag_18).ids)],
        })
        cls.dried_nettle = cls.env['product.product'].create({'name': 'Dried nettle', 'is_storable': True, 'uom_id': cls.uom_kg.id})
        cls.env['stock.quant']._update_available_quantity(cls.dried_nettle, cls.stock_location, 1000)
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.nettle.product_tmpl_id.id,
            'product_qty': 1,
            'uom_id': cls.uom_bag_20.id,
            'produce_whole_units': True,
            'bom_line_ids': [Command.create({'product_id': cls.dried_nettle.id, 'product_qty': 20, 'uom_id': cls.uom_kg.id})],
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Herbal shop'})

    def _create_order(self, quantity):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [Command.create({'product_id': self.nettle.id, 'product_uom_qty': quantity, 'product_uom_id': self.uom_kg.id})],
        })
        order.action_confirm()
        return order

    def _add_lot(self, name, quantity, packaging):
        lot = self.env['stock.lot'].create({'name': name, 'product_id': self.nettle.id, 'packaging_uom_id': packaging.id})
        self.env['stock.quant']._update_available_quantity(self.nettle, self.stock_location, quantity, lot_id=lot)
        return lot

    def test_manufacture_whole_bags(self):
        """ 50 kg ordered with a bill of materials in bags of 20 kg: 3 bags are manufactured, not 2.5, and the
        produced lot is packed in bags of 20 kg. """
        self.warehouse.manufacture_to_resupply = True
        routes = self.warehouse.manufacture_pull_id.route_id | self.env.ref('stock.route_warehouse0_mto')
        routes.write({'active': True, 'product_selectable': True})
        self.nettle.route_ids = [Command.set(routes.ids)]

        self._create_order(50)
        production = self.env['mrp.production'].search([('product_id', '=', self.nettle.id)])
        self.assertRecordValues(production, [{'product_qty': 3, 'uom_id': self.uom_bag_20.id, 'product_uom_qty': 60}])

        production.action_confirm()
        with Form(production) as production_form:
            production_form.lot_producing_ids.set(self.env['stock.lot'].create({'name': 'NM-B619', 'product_id': self.nettle.id}))
            production_form.qty_producing = 3
        production.button_mark_done()
        self.assertEqual(production.lot_producing_ids.packaging_uom_id, self.uom_bag_20)

    def test_deliver_whole_bags_of_the_lots(self):
        """ 50 kg ordered, 40 kg in bags of 20 kg and 36 kg in bags of 18 kg in stock: the delivery takes the 2 bags
        of 20 kg and 1 bag of 18 kg, so 58 kg, and the delivery slip shows the bags of each lot. """
        lot_20 = self._add_lot('NM-B619', 40, self.uom_bag_20)
        lot_18 = self._add_lot('NM-A512', 36, self.uom_bag_18)
        order = self._create_order(50)
        picking = order.picking_ids
        picking.action_assign()

        self.assertRecordValues(picking.move_ids, [{'product_uom_qty': 50, 'quantity': 58}])
        self.assertRecordValues(picking.move_line_ids.sorted('quantity'), [
            {'lot_id': lot_18.id, 'quantity': 18},
            {'lot_id': lot_20.id, 'quantity': 40},
        ])
        self.assertEqual(picking.state, 'assigned')

        picking.button_validate()
        slip = self.env['ir.actions.report']._render_qweb_html('stock.action_report_delivery', picking.ids)[0].decode()
        self.assertIn('x 20 kg', slip)
        self.assertIn('x 18 kg', slip)
        self.assertEqual(order.order_line.qty_delivered, 58)

    def test_lot_without_enough_for_a_whole_bag(self):
        """ A lot without enough quantity to complete its last bag is reserved as usual. """
        self._add_lot('NM-B619', 50, self.uom_bag_20)
        picking = self._create_order(45).picking_ids
        picking.action_assign()
        self.assertRecordValues(picking.move_ids, [{'product_uom_qty': 45, 'quantity': 45}])

    def test_delivery_slip_without_lots(self):
        """ Without lots on the delivery slip, the bags of each kind are listed under the delivered quantity. """
        self.env.user.group_ids -= self.env.ref('stock.group_lot_on_delivery_slip')
        self._add_lot('NM-B619', 40, self.uom_bag_20)
        self._add_lot('NM-A512', 36, self.uom_bag_18)
        picking = self._create_order(50).picking_ids
        picking.action_assign()
        picking.button_validate()
        slip = self.env['ir.actions.report']._render_qweb_html('stock.action_report_delivery', picking.ids)[0].decode()
        slip = ' '.join(slip.split())
        self.assertIn('<span>50</span> <span>kg</span>', slip)
        self.assertIn('<span>58</span> <span>kg</span>', slip)
        self.assertIn('<span class="text-muted">2</span> <span class="text-muted">x 20 kg</span>', slip)
        self.assertIn('<span class="text-muted">1</span> <span class="text-muted">x 18 kg</span>', slip)
