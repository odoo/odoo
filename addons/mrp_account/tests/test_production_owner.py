# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.mrp_account.tests.common import TestBomPriceCommon


@tagged('-at_install', 'post_install')
class TestProductionOwnerValuation(TestBomPriceCommon):

    _test_user_groups = (
        'mrp.group_mrp_manager',  # subject: bills of materials and manufacturing orders
        'stock.group_tracking_owner',  # subject: consignment
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({'name': 'Herb Trader'})
        cls.herb = cls._create_product('Nettle leaves', 2.0, quantity=0)
        cls.tea_cut = cls._create_product('Nettle tea cut', 2.0, quantity=0)
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.tea_cut.product_tmpl_id.id,
            'product_id': cls.tea_cut.id,
            'product_qty': 10,
            'bom_line_ids': [Command.create({'product_id': cls.herb.id, 'product_qty': 10})],
        })

    def _produce_from_herbs(self, owner=None):
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.herb.id,
            'location_id': self.stock_location.id,
            'owner_id': owner and owner.id,
            'inventory_quantity': 10,
        }).action_apply_inventory()
        production = self._create_mo(self.bom, 10)
        production.action_assign()
        self._produce(production).button_mark_done()
        return production

    def test_owned_production_is_not_valued(self):
        """ The products of a customer, made of their components, are not valued in the company's stock. """
        production = self._produce_from_herbs(owner=self.customer)
        self.assertEqual(production.owner_id, self.customer)
        self.assertFalse(production.move_finished_ids.value)
        self.assertFalse(self.tea_cut.total_value)

    def test_company_production_is_valued(self):
        production = self._produce_from_herbs()
        self.assertFalse(production.owner_id)
        self.assertEqual(production.move_finished_ids.value, 20.0)
        self.assertEqual(self.tea_cut.total_value, 20.0)
