# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import SavepointCase


class TestBoM(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mto = cls.env.ref('stock.route_warehouse0_mto')
        mto.write({'active': True})
        cls.routes = cls.env.ref('mrp.route_warehouse0_manufacture') + mto
        cls.location = cls.env.ref('stock.warehouse0').lot_stock_id

        cls.workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line 1',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })
        cls.workcenter_2 = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line 2',
            'resource_calendar_id': cls.env.ref('resource.resource_calendar_std').id,
        })

        cls.tree = cls.build_product_tree(('Main', [
            ('Sub 1', [
                ('Sub 1.1', [
                    ('Sub 1.1.1', []),
                    ('Sub 1.1.2', []),
                ]),
                ('Sub 1.2', [
                    ('Sub 1.2.1', []),
                    ('Sub 1.2.2', []),
                ]),
            ]),
            ('Sub 2', [
                ('Sub 2.1', [
                    ('Sub 2.1.1', []),
                    ('Sub 2.1.2', []),
                ]),
                ('Sub 2.2', [
                    ('Sub 2.2.1', []),
                    ('Sub 2.2.2', []),
                ]),
            ]),
        ]))

    @classmethod
    def build_product_tree(cls, tree):
        assert len(tree) == 2
        assert isinstance(tree[0], str)
        assert isinstance(tree[1], list)
        if len(tree[1]) == 0:
            leaf = (cls.env['product.product'].create({
                'name': tree[0],
                'type': 'product',
            }), [])
            cls.env['stock.quant']._update_available_quantity(leaf[0], cls.location, 10)
            return leaf
        else:
            children = [cls.build_product_tree(child) for child in tree[1]]
            return (cls.env['product.product'].create({
                'name': tree[0],
                'type': 'product',
                'route_ids': cls.routes.ids,
                'bom_ids': [(0, 0, {
                    'product_qty': 1.0,
                    'consumption': 'flexible',
                    'operation_ids': [(0, 0, {
                        'name': 'Gift Wrap Maching',
                        'workcenter_id': cls.workcenter_1.id,
                        'time_cycle_manual': 480,
                    })],
                    'type': 'normal',
                    'bom_line_ids': [
                        (0, 0, {'product_id': child[0].id, 'product_qty': 1.0})
                        for child in children
                    ],
                })],
            }), children)

    @classmethod
    def get_production_tree(cls, tree):
        children = [cls.get_production_tree(child) for child in tree[1] if len(child[1]) > 0]
        return (cls.env['mrp.production'].search([('product_id', '=', tree[0].id)]), children)

    @classmethod
    def get_tree_nodes(cls, tree):
        children = sum([cls.get_tree_nodes(child) for child in tree[1]], tree[0].browse())
        return tree[0] + children if children else tree[0]

    @classmethod
    def replenish(cls, product, qty=1):
        replenish_wizard = cls.env['product.replenish'].create({
            'product_id': product.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_uom_id': product.uom_id.id,
            'warehouse_id': cls.env.ref('stock.warehouse0').id,
            'quantity': qty,
        })
        replenish_wizard.launch_replenishment()

    def verify_scheduling(self, tree):
        assert_count = 0
        for child in tree[1]:
            assert_count += 1
            msg = f'{child[0].product_id.name} not scheduled before {tree[0].product_id.name}'
            self.assertLessEqual(child[0].date_planned_finished, tree[0].date_planned_start, msg)
        for child in tree[1]:
            assert_count += self.verify_scheduling(child)
        return assert_count

    def test_01_complete_tree_scheduling(self):
        # A simple test case: schedule the complete manufacturing order tree
        # at once, on the same workcenter.
        self.replenish(self.tree[0], qty=1)
        mo_tree = self.get_production_tree(self.tree)
        mrp_orders = self.get_tree_nodes(mo_tree)
        mrp_orders.button_plan()
        self.assertEqual(len(mrp_orders.filtered('is_planned')), 7)
        self.assertEqual(self.verify_scheduling(mo_tree), 6)

    def test_02_mixed_workcenter_scheduling(self):
        # Process one of the dependencies on a different workcenter. This makes
        # sure that dependent orders cannot be planned earlier on a different
        # workcenter if an open slot preceding the dependencies still exists.
        self.tree[1][0][0].bom_ids.operation_ids.workcenter_id = self.workcenter_2.id
        self.test_01_complete_tree_scheduling()

    def test_03_staged_scheduling(self):
        # Plan some of the dependencies separately on a different workcenter
        # first. When scheduling the remaining orders, take the finished dates
        # of the separately planned dependencies into account.
        simple_bom_product_ids = self.get_tree_nodes(self.tree).filtered(
            lambda p: p.bom_ids and not p.bom_ids.bom_line_ids.child_bom_id
        )
        self.assertEqual(len(simple_bom_product_ids), 4)
        simple_bom_product_ids.bom_ids.operation_ids.workcenter_id = self.workcenter_2.id
        self.replenish(self.tree[0], qty=1)
        mo_tree = self.get_production_tree(self.tree)
        mrp_orders = self.get_tree_nodes(mo_tree)
        mrp_orders.filtered(lambda mo: mo.product_id in simple_bom_product_ids).button_plan()
        self.assertEqual(len(mrp_orders.filtered('is_planned')), 4)
        self.get_tree_nodes(mo_tree).button_plan()
        self.assertEqual(len(mrp_orders.filtered('is_planned')), 7)
        self.assertEqual(self.verify_scheduling(mo_tree), 6)

    def test_04_truncated_tree_scheduling(self):
        # Only plan the tree truncated to a given depth. Check that all orders
        # in the truncated tree are planned even if dependencies are not.
        self.replenish(self.tree[0], qty=1)
        mo_tree = self.get_production_tree(self.tree)
        # Schedule the truncated tree of depth two
        truncated_tree = (mo_tree[0], [(child[0], []) for child in mo_tree[1]])
        mrp_orders = self.get_tree_nodes(truncated_tree)
        mrp_orders.button_plan()
        self.assertEqual(len(mrp_orders.filtered('is_planned')), 3)
        self.assertEqual(self.verify_scheduling(mo_tree[1][0]), 2)
