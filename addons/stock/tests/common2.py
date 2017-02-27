# -*- coding: utf-8 -*-

from odoo.addons.product.tests import common


class TestStockCommon(common.TestProductCommon):

    def _create_pack_operation(self, product, product_qty, picking_id, **values):
        PackOperation = self.env['stock.pack.operation'].sudo(self.user_stock_manager)
        vals = {
            'picking_id': picking_id.id,
            'product_id': product.id,
            'product_qty': product_qty,
            'qty_done': product_qty}
        vals.update(**values)
        pack_operation = PackOperation.new(vals)
        pack_operation.onchange_product_id()
        return PackOperation.create(pack_operation._convert_to_write(pack_operation._cache))

    def _create_picking_in(self, warehouse):
        Picking = self.env['stock.picking']
        picking_values = {
            'picking_type_id': warehouse.in_type_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': warehouse.lot_stock_id.id,
        }
        return Picking.create(picking_values)

    def _create_move(self, product, src_location, dst_location, **values):
        # TDE FIXME: user as parameter
        Move = self.env['stock.move'].sudo(self.user_stock_manager)
        # simulate create + onchange
        move = Move.new({'product_id': product.id, 'location_id': src_location.id, 'location_dest_id': dst_location.id})
        move.onchange_product_id()
        move_values = move._convert_to_write(move._cache)
        move_values.update(**values)
        return Move.create(move_values)

    def _create_move_in(self, product, warehouse, picking=None, create_picking=False, **values):
        if not picking and create_picking:
            picking = self._create_picking_in(warehouse)
        if picking:
            values['picking_id'] = picking.id
        # TDE FIXME: shouldn't location come from picking ??
        return self._create_move(product, self.env.ref('stock.stock_location_suppliers'), warehouse.lot_stock_id, **values)

    @classmethod
    def setUpClass(cls):
        super(TestStockCommon, cls).setUpClass()

        # Fetch stock-related user groups
        user_group_employee = cls.env.ref('base.group_user')
        user_group_stock_user = cls.env.ref('stock.group_stock_user')
        user_group_stock_manager = cls.env.ref('stock.group_stock_manager')

        # User Data: stock user and stock manager
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_stock_user = Users.create({
            'name': 'Pauline Poivraisselle',
            'login': 'pauline',
            'email': 'p.p@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [user_group_stock_user.id])]})
        cls.user_stock_manager = Users.create({
            'name': 'Julie Tablier',
            'login': 'julie',
            'email': 'j.j@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [user_group_stock_manager.id])]})

        # Warehouses
        cls.warehouse_1 = cls.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'BWH'})

        # Locations
        cls.location_1 = cls.env['stock.location'].create({
            'name': 'TestLocation1',
            'posx': 3,
            'location_id': cls.warehouse_1.lot_stock_id.id,
        })

        # Existing data
        cls.existing_inventories = cls.env['stock.inventory'].search([])
        cls.existing_quants = cls.env['stock.quant'].search([])

        # Inventory
        inventory_wizard = cls.env['stock.change.product.qty'].create({
            'product_id': cls.product_1.id,
            'new_quantity': 50.0,
            'location_id': cls.warehouse_1.lot_stock_id.id,
        })
        inventory_wizard.change_product_qty()
