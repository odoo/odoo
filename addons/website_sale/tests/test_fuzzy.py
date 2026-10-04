# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website.tools import MockRequest
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleFuzzy(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env.registry.has_trigram:
            cls.env.cr.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            cls.env.registry.has_trigram = True
        cls.website = cls.env.ref('website.default_website')
        cls.public_user = cls.website.user_id
        cls.valid_product = cls.env['product.template'].create({
            'name': 'FuzzyProductUnique',
            'sale_ok': True,
            'is_published': True,
        })
        # More than the 1000 pre-ranking candidate limit: if eligibility were
        # applied after ranking, these closer matches would fill the limit and
        # hide the valid product.
        cls.decoy_products = cls.env['product.template'].create([{
            'name': f'FuzzyProdcutUnique-{index:04d}',
            'sale_ok': False,
            'is_published': True,
        } for index in range(1001)])
        cls.env.flush_all()
        cls.search_options = {
            'allowFuzzy': True,
            'displayDescription': False,
            'displayDetail': False,
            'displayExtraLink': False,
            'displayImage': False,
        }

    def _search(self, term):
        website = self.website.with_user(self.public_user).with_context(
            website_id=self.website.id,
        )
        with MockRequest(website.env, website=website):
            return website._search_with_fuzzy(
                'products_only', term, limit=None, order='name asc',
                options=self.search_options,
            )

    def test_fuzzy_candidates_filtered_before_ranking(self):
        self.assertTrue(self.env.registry.has_trigram)
        self.assertEqual(len(self.decoy_products), 1001)
        self.assertEqual(set(self.decoy_products.mapped('is_published')), {True})
        self.assertEqual(set(self.decoy_products.mapped('sale_ok')), {False})

        count, details, fuzzy_term = self._search('FuzzyProdcutUnique')

        self.assertEqual(fuzzy_term, 'fuzzyproductunique')
        self.assertEqual(count, 1)
        self.assertEqual(details[0]['results'].ids, self.valid_product.ids)

        count, details, fuzzy_term = self._search('FuzzyProductUnique')

        self.assertFalse(fuzzy_term)
        self.assertEqual(count, 1)
        self.assertEqual(details[0]['results'].ids, self.valid_product.ids)
