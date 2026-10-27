# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.mrp_account.tests.common import TestBomPriceCommon


@tagged('-at_install', 'post_install')
class TestBomCost(TestBomPriceCommon):

    _test_user_groups = (
        'mrp.group_mrp_user',  # subject: kits and their bills of materials
        'stock.group_stock_manager',  # setup: _make_in_move sets value_manual -> inverse creates product.value (stock.group_stock_manager)
        'account.group_account_invoice',  # subject: stock valuation journal entries asserted by the tests
        'product.group_product_manager',  # subject: action_bom_cost recomputes product standard_price
    )

    _test_user_name = 'Test User'

    @classmethod
    def _create_bom(cls, product, lines, bom_type='phantom', **kwargs):
        return cls.Bom.create({
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_id': product.id,
            'type': bom_type,
            'bom_line_ids': [
                Command.create({'product_id': component.id, 'product_qty': qty})
                for component, qty in lines
            ],
            **kwargs,
        })

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.comp_avco = cls._create_product('Comp AVCO', 10, quantity=0, category=cls.category_avco_auto)
        cls.comp_std = cls._create_product('Comp Standard', 5, quantity=0, category=cls.category_standard_auto)

        # -----------------------------------------------
        # AVCO Kit = 2 Comp AVCO + 1 Comp Standard
        #          = 2 * 10 + 5 = 25 (before any receipt)
        # -----------------------------------------------
        cls.kit_avco = cls._create_product('Kit AVCO', 1, quantity=0, category=cls.category_avco_auto)
        cls._create_bom(cls.kit_avco, [(cls.comp_avco, 2), (cls.comp_std, 1)])

    def test_batch_bom_cost_components_first(self):
        """ Components recomputed in the same batch are recomputed first, and their new cost is
        used for the products containing them, whatever the order of the products in the batch.
        """
        # Parent = 2 AVCO Kit + 1 Comp Standard = 2 * 25 + 5 = 55
        parent = self._create_product('Parent', 1, quantity=0, category=self.category_avco_auto)
        self._create_bom(parent, [(self.kit_avco, 2), (self.comp_std, 1)])
        # Grand Parent = 1 Parent + 1 AVCO Kit = 55 + 25 = 80
        grand_parent = self._create_product('Grand Parent', 1, quantity=0, category=self.category_avco_auto)
        self._create_bom(grand_parent, [(parent, 1), (self.kit_avco, 1)])

        (grand_parent | parent | self.kit_avco).action_bom_cost()
        self.assertRecordValues(self.kit_avco | parent | grand_parent, [
            {'standard_price': 25},
            {'standard_price': 55},
            {'standard_price': 80},
        ])

        # Only the products of the batch are recomputed: the cost of the others is used as is
        self.kit_avco.standard_price = 1
        grand_parent.action_bom_cost()
        self.assertRecordValues(self.kit_avco | parent | grand_parent, [
            {'standard_price': 1},
            {'standard_price': 55},
            {'standard_price': 56},
        ])

    def test_batch_bom_cost_byproduct(self):
        """ Products without BoM are priced from the BoM producing them as by-product, using the
        new cost of its components recomputed in the same batch. A by-product without cost share
        keeps its cost.
        """
        finished = self._create_product('Finished', 1, quantity=0)
        byproduct = self._create_product('By-Product', 1, quantity=0)
        byproduct_no_share = self._create_product('By-Product No Share', 7, quantity=0)
        # Total = 2 AVCO Kit = 50, by-product gets 20% of it for 2 units => 5 per unit
        self._create_bom(finished, [(self.kit_avco, 2)], bom_type='normal', byproduct_ids=[
            Command.create({'product_id': byproduct.id, 'product_qty': 2, 'cost_share': 20}),
            Command.create({'product_id': byproduct_no_share.id, 'product_qty': 1, 'cost_share': 0}),
        ])

        (byproduct | byproduct_no_share | finished | self.kit_avco).action_bom_cost()
        self.assertRecordValues(self.kit_avco | finished | byproduct | byproduct_no_share, [
            {'standard_price': 25},
            {'standard_price': 40},
            {'standard_price': 5},
            {'standard_price': 7},
        ])

    def test_avco_kit_cost_follows_components(self):
        """ The cost of an AVCO kit is recomputed when the cost of its components changes, without
        revaluation as kits are not valued.
        """
        self.assertEqual(self.kit_avco.standard_price, 1)
        kit_values = self.env['product.value'].search([('product_id', '=', self.kit_avco.id)])

        # Comp AVCO: 10 units @ 20 => 20, AVCO Kit = 2 * 20 + 5 = 45
        self._make_in_move(self.comp_avco, 10, unit_cost=20)
        self.assertEqual(self.comp_avco.standard_price, 20)
        self.assertRecordValues(self.kit_avco, [{'standard_price': 45, 'total_value': 0}])

        # Comp AVCO: 10 units @ 20 + 10 units @ 30 => 25, AVCO Kit = 2 * 25 + 5 = 55
        self._make_in_move(self.comp_avco, 10, unit_cost=30)
        self.assertEqual(self.comp_avco.standard_price, 25)
        self.assertRecordValues(self.kit_avco, [{'standard_price': 55, 'total_value': 0}])

        self.assertEqual(self.env['product.value'].search([('product_id', '=', self.kit_avco.id)]), kit_values)
        self.assertFalse(self.env['account.move.line'].search([('product_id', '=', self.kit_avco.id)]))

    def test_avco_kit_cost_nested_kits(self):
        """ The cost of the AVCO kits containing AVCO kits is recomputed too. """
        # Parent = 2 AVCO Kit + 1 Comp Standard
        parent = self._create_product('Parent', 1, quantity=0, category=self.category_avco_auto)
        self._create_bom(parent, [(self.kit_avco, 2), (self.comp_std, 1)])

        # Comp AVCO @ 20 => AVCO Kit = 45, Parent = 2 * 45 + 5 = 95
        self._make_in_move(self.comp_avco, 10, unit_cost=20)
        self.assertRecordValues(self.kit_avco | parent, [
            {'standard_price': 45},
            {'standard_price': 95},
        ])

    def test_non_avco_kit_cost_is_kept(self):
        """ Only the AVCO kits are recomputed: a non AVCO kit keeps its cost, and so do the kits
        containing it, as well as the manufactured products.
        """
        kit_std = self._create_product('Kit Standard', 1, quantity=0, category=self.category_standard_auto)
        self._create_bom(kit_std, [(self.comp_avco, 1)])
        kit_fifo = self._create_product('Kit FIFO', 2, quantity=0, category=self.category_fifo_auto)
        self._create_bom(kit_fifo, [(self.comp_avco, 1)])
        parent = self._create_product('Parent of Kit Standard', 3, quantity=0, category=self.category_avco_auto)
        self._create_bom(parent, [(kit_std, 1)])
        manufactured = self._create_product('Manufactured AVCO', 4, quantity=0, category=self.category_avco_auto)
        self._create_bom(manufactured, [(self.comp_avco, 1)], bom_type='normal')

        self._make_in_move(self.comp_avco, 10, unit_cost=20)
        self.assertRecordValues(self.kit_avco | kit_std | kit_fifo | parent | manufactured, [
            {'standard_price': 45},
            {'standard_price': 1},
            {'standard_price': 2},
            {'standard_price': 3},
            {'standard_price': 4},
        ])

    def test_avco_kit_cost_variants(self):
        """ A kit BoM defined on the template recomputes the cost of all its variants. """
        attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'value_ids': [Command.create({'name': 'S'}), Command.create({'name': 'L'})],
        })
        template = self.env['product.template'].create({
            'name': 'Kit Variants',
            'is_storable': True,
            'standard_price': 1,
            'categ_id': self.category_avco_auto.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': attribute.id,
                'value_ids': [Command.set(attribute.value_ids.ids)],
            })],
        })
        self.Bom.sudo().create({  # setup master-data
            'product_tmpl_id': template.id,
            'type': 'phantom',
            'bom_line_ids': [Command.create({'product_id': self.comp_avco.id, 'product_qty': 3})],
        })
        self.assertEqual(len(template.product_variant_ids), 2)

        self._make_in_move(self.comp_avco, 10, unit_cost=20)
        self.assertRecordValues(template.product_variant_ids, [
            {'standard_price': 60},
            {'standard_price': 60},
        ])

    def test_avco_kit_cost_other_company(self):
        """ The kits of another company are not recomputed. """
        kit_other_company = self._create_product('Kit Other Company', 1, quantity=0, category=self.category_avco_auto)
        self._create_bom(kit_other_company, [(self.comp_avco, 1)]).sudo().company_id = self.other_company

        self._make_in_move(self.comp_avco, 10, unit_cost=20)
        self.assertRecordValues(self.kit_avco | kit_other_company, [
            {'standard_price': 45},
            {'standard_price': 1},
        ])
