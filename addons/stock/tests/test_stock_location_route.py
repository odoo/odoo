# -*- coding: utf-8 -*-

from odoo.tests import common
from odoo.exceptions import UserError


class TestStockLocationRoute(common.TransactionCase):
    def test_unlink_prevent_route_group(self):
        route_a = self.env["stock.location.route"].create(
            {"name": "a_route"}
        )
        self.env['ir.model.data'].create({
            'name': route_a.name,
            'module': 'Stock',
            'model': route_a._name,
            'res_id': route_a.id,
        })
        with self.assertRaises(UserError, msg="You cannot delete route a_route; archive it instead."):
            route_a.unlink()
