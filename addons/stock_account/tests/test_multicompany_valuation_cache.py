# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestMultiCompanyValuationCache(TransactionCase):
    """
    Test that avg_cost and total_value are not shared across company scopes.

    _compute_value sums over env.companies and converts into env.company's
    currency, so its result depends on allowed_company_ids and not only on the
    active company.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({
            'name': 'Company B',
            'currency_id': cls.company_a.currency_id.id,
        })

        cls.categ = cls.env['product.category'].create({
            'name': 'Test AVCO Category',
            'property_cost_method': 'average',
            'property_valuation': 'periodic',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Shared AVCO Product',
            'is_storable': True,
            'categ_id': cls.categ.id,
            'company_id': False,
        })

        # 10 units at 10.00 in company A, 10 units at 40.00 in company B
        for company, price in ((cls.company_a, 10.0), (cls.company_b, 40.0)):
            cls.product.with_company(company).standard_price = price
            warehouse = cls.env['stock.warehouse'].search(
                [('company_id', '=', company.id)], limit=1)
            cls.env['stock.quant'].with_company(company).with_context(
                inventory_mode=True, allowed_company_ids=company.ids,
            ).create({
                'product_id': cls.product.id,
                'inventory_quantity': 10,
                'location_id': warehouse.lot_stock_id.id,
            }).action_apply_inventory()
        cls.env.flush_all()

    def _avg_cost(self, companies):
        """Read avg_cost with the active company pinned to A, varying only the
        set of allowed companies."""
        return self.product.with_company(self.company_a).with_context(
            allowed_company_ids=companies.ids).avg_cost

    def test_avg_cost_is_not_shared_between_company_scopes(self):
        both = self.company_a | self.company_b

        # Each scope, computed on its own
        self.product.invalidate_recordset(['avg_cost'])
        self.assertEqual(self._avg_cost(self.company_a), 10.0)
        self.product.invalidate_recordset(['avg_cost'])
        self.assertEqual(self._avg_cost(both), 25.0)

        # A single-company read must not be handed back to a multi-company one
        self.product.invalidate_recordset(['avg_cost'])
        self._avg_cost(self.company_a)
        self.assertEqual(self._avg_cost(both), 25.0)

        # ... nor the other way round
        self.product.invalidate_recordset(['avg_cost'])
        self._avg_cost(both)
        self.assertEqual(self._avg_cost(self.company_a), 10.0)
