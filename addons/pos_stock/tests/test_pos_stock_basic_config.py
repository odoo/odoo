# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.point_of_sale.tests.test_pos_basic_config import TestPoSBasicConfig
from odoo.addons.pos_stock.tests.common import TestPosStockCommon


class TestPoSStockBasicConfig(TestPoSBasicConfig, TestPosStockCommon):
    """ Test PoS with basic configurations.
    """

    def test_limited_products_loading_priority(self):
        """
        This test makes sure that pos_stock's limited products loading
        feature prioritizes product templates in this order, with ties
        being broken by the next trait:
        1st. "Favorited" products (is_favorite)
        2nd. "Service" type products (type)
        3rd. Products with more recent stock move activity
        4th. Recently written to products (write_date)
        """
        # Restrict the loaded-product domain to our own POS category so any
        # other available_in_pos product (demo data, combos, setUp fixtures)
        # never competes for the limited slots.
        test_categ = self.env['pos.category'].create({'name': 'Priority Test Category'})
        self.config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, test_categ.ids)],
        })
        product0 = self.create_product('Priority Product 0', self.categ_basic, 10)
        product1 = self.create_product('Priority Product 1', self.categ_basic, 10)
        product2 = self.create_product('Priority Product 2', self.categ_basic, 10)
        product3 = self.create_product('Priority Product 3', self.categ_basic, 10)
        product4 = self.create_product('Priority Product 4', self.categ_basic, 10)
        (product0 | product1 | product2 | product3 | product4).product_tmpl_id.write({
            'pos_categ_ids': [(6, 0, test_categ.ids)],
        })

        # product0, product2 and product4 are tied on (is_favorite, type);
        # product0 gets a stock move so it should win that tier regardless
        # of write_date (its write_date is deliberately older than
        # product2's and product4's, as a trap), and product2/product4 are
        # then decided by write_date alone. product1 and product3 are each
        # given every trait a rung down could win on — a stock move and/or
        # the newest write_date — to prove the tier above still wins
        # despite it: product1 has neither a stock move nor a recent
        # write_date yet outranks the whole consu group purely on type,
        # and product3 has the best type and the newest write_date of all
        # yet still loses everything for not being favorited.
        now = fields.Datetime.now()
        for offset, product, vals in [
            (0, product1, {"is_favorite": True, "type": "service"}),
            (1, product0, {"is_favorite": True, "type": "consu"}),
            (2, product2, {"is_favorite": True, "type": "consu"}),
            (3, product4, {"is_favorite": True, "type": "consu"}),
            (4, product3, {"is_favorite": False, "type": "service"}),
        ]:
            self.patch(self.env.cr, 'now', lambda now=now, offset=offset: now + relativedelta(minutes=offset))
            product.product_tmpl_id.write(vals)
            self.env.flush_all()
        # Only product0 gets a stock move (only "consu" products can).
        self.adjust_inventory([product0], [10])

        session = self.open_new_session(0)

        def loaded_ids(limit):
            self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', limit)
            return self._get_loaded_product_ids(session)

        # type outranks stock move activity and write_date: product0 has
        # both, but loses to product1 for having the wrong type.
        self.assertCountEqual(loaded_ids(1), [product1.id])
        # a stock move outranks write_date: product0 wins over product2
        # and product4 despite having the oldest write_date of the three.
        self.assertCountEqual(loaded_ids(2), [product1.id, product0.id])
        # write_date breaks the tie between product4 and product2.
        self.assertCountEqual(loaded_ids(3), [product1.id, product0.id, product4.id])
        # is_favorite outranks everything else: product3 has the best
        # type and write_date of all, but isn't favorited.
        self.assertCountEqual(loaded_ids(4), [product1.id, product0.id, product4.id, product2.id])
