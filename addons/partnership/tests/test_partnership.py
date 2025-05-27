# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import ValidationError

from .common import PartnershipCommon


class TestPartnership(PartnershipCommon):

    def test_sell_basic_partnership(self):
        self.sale_order_partnership.action_confirm()
        self.assertEqual(
            self.partner.grade_id,
            self.partnership_product.grade_id,
            "Selling the partnership should assign the grade to the partner",
        )
        self.assertEqual(
            self.partner.specific_property_product_pricelist,
            self.partnership_product.grade_id.default_pricelist_id,
            "Selling the partnership should assign the pricelist to the partner",
        )

    def test_sell_basic_partnership_to_partner_with_children(self):
        self.sale_order_partnership.action_confirm()
        self.assertEqual(
            self.partner.child_ids.grade_id,
            self.partnership_product.grade_id,
            "Selling the partnership should assign the grade to the children of the partner",
        )
        self.assertEqual(
            self.partner.child_ids.specific_property_product_pricelist,
            self.partnership_product.grade_id.default_pricelist_id,
            "Selling the partnership should assign the pricelist to the children of the partner",
        )

    def test_sell_basic_partnership_to_children_partners(self):
        partner_with_children = self.env['res.partner'].create({
            'name': 'Parent Company',
            'child_ids': [
                Command.create({'name': 'Child Company 1'}),
                Command.create({'name': 'Child Company 2'}),
            ],
        })
        for child in partner_with_children.child_ids:
            sale_order_partnership_with_child = self.env['sale.order'].create({
                'partner_id': child.id,
                'order_line': [Command.create({'product_id': self.partnership_product.id})],
            })
            sale_order_partnership_with_child.action_confirm()
            self.assertEqual(
                child.grade_id,
                self.partnership_product.grade_id,
                "Selling the partnership to the child should assign the grade to the child",
            )
            self.assertFalse(
                partner_with_children.grade_id,
                "Selling the partnership to the child should not assign the grade to the parent",
            )
            for c in partner_with_children.child_ids:
                if c != child:
                    self.assertFalse(
                        c.grade_id,
                        "Selling the partnership to the child should not assign the grade to another child",
                    )
            child.grade_id = False

    def test_constrains_uniqueness_partnership_grade(self):
        partnership = self.env['product.product'].create({
            'name': 'Partnership',
            'type': 'service',
            'list_price': 100.00,
            'service_tracking': 'partnership',
            'grade_id': self.env['res.partner.grade'].create({'name': 'A+'}).id,
        })
        with self.assertRaises(ValidationError):
            # A sale order cannot contain partnership products assigning different grade levels
            self.sale_order_partnership.order_line = [Command.create({'product_id': partnership.id})]
