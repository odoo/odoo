# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import TransactionCase


class TestPosGetLimitedProductsLoading(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pos_categ = cls.env['pos.category'].create({
            'name': 'Tiebreak Test Category',
        })
        # 5 products tying on every ORDER BY key used by get_limited_products_loading:
        # none favorite, type 'consu' (not 'service'), no stock.move.line (pm.date NULL
        # for all), and created together in this same transaction so write_date is
        # identical for all of them.
        cls.tied_products = cls.env['product.product'].create([{
            'name': 'Tiebreak Product %s' % index,
            'type': 'consu',
            'available_in_pos': True,
            'sale_ok': True,
            'is_favorite': False,
            'pos_categ_ids': [Command.set([cls.pos_categ.id])],
        } for index in range(5)])
        cls.config = cls.env['pos.config'].create({
            'name': 'Tiebreak Test PoS',
            'limit_categories': True,
            'iface_available_categ_ids': [Command.set([cls.pos_categ.id])],
        })

    def test_get_limited_products_loading_deterministic_tiebreak(self):
        """ Products tied on every ORDER BY key (favorite, type, last stock move,
        write_date) must still be selected deterministically once LIMIT is applied.
        Without the `id` tiebreaker this selection depends on Postgres's
        unspecified physical scan order, i.e. it is flaky.
        """
        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.limited_product_count', 3)

        loaded_ids = {product['id'] for product in self.config.get_limited_products_loading(['id'])}
        tied_ids = sorted(self.tied_products.ids)
        lowest_three_ids, highest_two_ids = tied_ids[:3], tied_ids[3:]

        for product_id in lowest_three_ids:
            self.assertIn(
                product_id, loaded_ids,
                "The lowest-id tied products must be loaded first (deterministic id tiebreak)."
            )
        for product_id in highest_two_ids:
            self.assertNotIn(
                product_id, loaded_ids,
                "The highest-id tied products must not be loaded once the limit is reached."
            )
