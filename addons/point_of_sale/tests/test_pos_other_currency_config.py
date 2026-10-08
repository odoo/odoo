# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import fields, tools
from odoo.addons.point_of_sale.tests.common import CommonPosTest

# TODO-PARP: Move tests and remove File


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSOtherCurrencyConfig(CommonPosTest):
    """ Test PoS with basic configuration
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.config = cls.pos_config_eur
        cls.product1 = cls.create_product('Product 1', cls.categ_basic, 10.0, 5)
        cls.product2 = cls.create_product('Product 2', cls.categ_basic, 20.0, 10)
        cls.product3 = cls.create_product('Product 3', cls.categ_basic, 30.0, 15)
        cls.product7 = cls.create_product('Product 7', cls.categ_basic, 7, 7, tax_ids=cls.taxes['tax7'].ids)
        # change the price of product2 to 12.99 fixed. No need to convert.
        pricelist_item = cls.env['product.pricelist.item'].create({
            'product_tmpl_id': cls.product2.product_tmpl_id.id,
            'fixed_price': 12.99,
        })
        cls.config.pricelist_id.write({'item_ids': [(6, 0, (cls.config.pricelist_id.item_ids | pricelist_item).ids)]})

    def test_01_check_product_cost(self):
        # Product price should be half of the original price because currency rate is 0.5.
        # The shared EUR fixture uses a rate of 0.5.
        # Except for product2 where the price is specified in the pricelist.

        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product1, 1), 5.00)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product2, 1), 12.99)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product3, 1), 15.00)
        self.assertAlmostEqual(self.config.pricelist_id._get_product_price(self.product7, 1), 3.50)

    def test_bank_journal_balance(self):
        """Verify that debit and credit are balanced when adding a difference to the bank."""

        self.open_new_session(config=self.config)
        session_id = self.pos_session
        self.create_pos_order(
            [[self.product1, 1, 0, {'price_unit': 10}]],
            payments=[[self.bank_pm2, 10]],
            config=self.config,
        )
        session_id.close_session_from_ui({self.bank_pm2.id: 20})
        self.assertEqual(session_id.state, 'closed')

        # Check debit/credit session's balance
        for move in session_id._get_related_account_moves():
            debit = credit = 0.0
            for line in move.line_ids:
                debit += line.debit
                credit += line.credit
            self.assertEqual(tools.float_compare(debit, credit, precision_rounding=self.pos_config_eur.currency_id.rounding), 0)  # debit and credit should be equal

    def test_with_session_check_product_cost(self):
        def find_by(list_of_dicts, key, value):
            return next((d for d in list_of_dicts if d.get(key) == value), None)

        self.pos_config_eur.open_ui()
        product = self.pos_config_eur.current_session_id.load_data({'only_records': True})['product.product']

        self.assertAlmostEqual(find_by(product, 'id', self.product1.id)['lst_price'], 5.00)
        self.assertAlmostEqual(find_by(product, 'id', self.product2.id)['lst_price'], 10.00)
        self.assertAlmostEqual(find_by(product, 'id', self.product3.id)['lst_price'], 15.00)
        self.assertAlmostEqual(find_by(product, 'id', self.product7.id)['lst_price'], 3.50)

    def test_pos_data_standard_price_converted(self):
        self.pos_config_eur.open_ui()
        res = self.pos_config_eur.current_session_id.load_data({'only_records': True})
        product1_data = next(filter(lambda product: product['display_name'] == "Product 1", res['product.product']))
        self.assertEqual(product1_data['standard_price'], 2.5)  # standard price should be converted

    def test_pos_data_shared_product_cost_currency(self):
        """ A product shared across companies (company_id = False) takes its sale-price
        currency from the main company but its cost currency from the active company.
        When the POS runs in a company whose currency differs from the main company, the
        cost (standard_price) must be converted from cost_currency_id, not currency_id,
        otherwise it gets wrongly multiplied by the exchange rate even though it is
        already expressed in the POS currency.
        """
        main_company = self.env['res.company']._get_main_company()
        self.assertNotEqual(main_company.currency_id, self.other_currency)

        other_company = self.env['res.company'].create({
            'name': 'Other Currency Company',
            'currency_id': self.other_currency.id,
        })
        self.env.user.company_ids |= other_company

        self.env['res.currency.rate'].create({
            'name': fields.Date.today(),
            'currency_id': main_company.currency_id.id,
            'rate': 2.0,
            'company_id': other_company.id,
        })

        shared_product = self.env['product.product'].create({
            'name': 'Shared Product',
            'available_in_pos': True,
            'is_storable': True,
            'taxes_id': [(5, 0, 0)],
            'lst_price': 100.0,
            'company_id': False,
        }).with_company(other_company)
        # standard_price is company-dependent: set it for the active company, where it
        # is therefore expressed in that company's currency (the "other" currency).
        shared_product.standard_price = 100.0

        self.assertEqual(shared_product.currency_id, main_company.currency_id)
        self.assertEqual(shared_product.cost_currency_id, self.other_currency)

        self.assertEqual(self.pos_config_eur.currency_id, self.other_currency)
        [data] = shared_product._load_pos_data_read(shared_product, self.pos_config_eur)

        self.assertAlmostEqual(data['standard_price'], 100.0)
        self.assertAlmostEqual(data['lst_price'], 50.0)

    def test_combo_prices_converted_to_pos_currency(self):
        # A combo's `base_price` and its items' `extra_price` are stored in the
        # company currency. When loaded in a PoS running another currency they
        # must be converted, just like standalone product prices (rate 0.5).
        combo = self.env['product.combo'].create({
            'name': 'Combo choice',
            'company_id': self.company.id,
            'combo_item_ids': [
                (0, 0, {'product_id': self.product1.product_variant_id.id, 'extra_price': 20.0}),
                (0, 0, {'product_id': self.product3.product_variant_id.id, 'extra_price': 0.0}),
            ],
        })
        # base_price is the min lst_price among the items, in company currency (product1 = 10.0).
        self.assertAlmostEqual(combo.base_price, 10.0)

        combo_read = self.env['product.combo']._load_pos_data_read(combo, self.config)[0]
        self.assertAlmostEqual(combo_read['base_price'], 5.0)

        combo_item_read = self.env['product.combo.item']._load_pos_data_read(combo.combo_item_ids, self.config)
        extra_prices = {rec['product_id']: rec['extra_price'] for rec in combo_item_read}
        self.assertAlmostEqual(extra_prices[self.product1.product_variant_id.id], 10.0)
        self.assertAlmostEqual(extra_prices[self.product3.product_variant_id.id], 0.0)
