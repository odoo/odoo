# Copyright 2020 Sergio Corato <https://github.com/sergiocorato>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMrpProductionChangeQty(TestMrpCommon):

    def setUp(self):
        super(TestMrpProductionChangeQty, self).setUp()

    def test_update_product_qty(self):
        # bom_3 (product_6) = product_2:12 + product_4:8 [normal]
        # -> bom_2 (product_5):2 = product_3:3 [phantom]
        # -> bom_1 (product_4):2 = product_2:2 + product_1:4 [normal]
        # total 4 mo lines: product_2:12, product_4:8, product_4:4, product_3:6
        man_order = self.env['mrp.production'].create({
            'name': 'MO-Test',
            'product_id': self.product_6.id,
            'product_uom_id': self.product_6.uom_id.id,
            'product_qty': 1,
            'bom_id': self.bom_3.id,
        })
        self.assertEqual(len(man_order.move_raw_ids), 4)
        self.env['change.production.qty'].create({
            'mo_id': man_order.id,
            'product_qty': man_order.product_qty,
        }).change_prod_qty()
        self.assertEqual(len(man_order.move_raw_ids), 4)
        # add 1 line in sub-bom phantom
        self.bom_2.write({
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_1.id, 'product_qty': 4})
            ]
        })
        self.env['change.production.qty'].create({
            'mo_id': man_order.id,
            'product_qty': man_order.product_qty,
        }).change_prod_qty()
        self.assertEqual(len(man_order.move_raw_ids), 5)

        # remove 1 line in sub-bom phantom
        self.bom_2.bom_line_ids.filtered(
            lambda x: x.product_id.id == self.product_1.id).unlink()
        self.env['change.production.qty'].create({
            'mo_id': man_order.id,
            'product_qty': man_order.product_qty,
        }).change_prod_qty()
        self.assertEqual(len(man_order.move_raw_ids), 4)
