# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import mute_logger

from odoo.addons.product.tests.common import ProductCommon


class TestProductCombo(ProductCommon):

    def test_combo_item_count(self):
        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'combo_item_ids': [
                Command.create({'product_id': self._create_product().id}),
                Command.create({'product_id': self._create_product().id}),
                Command.create({'product_id': self._create_product().id}),
            ],
        })

        self.assertEqual(combo.combo_item_count, 3)

    def test_currency_without_company_set(self):
        self.setup_main_company(currency_code='GBP')

        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'combo_item_ids': [Command.create({'product_id': self.product.id})],
        })

        self.assertEqual(combo.currency_id.name, 'GBP')

    def test_currency_with_company_set(self):
        company_eur = self._create_company(
            name="Company EUR", currency_id=self._enable_currency('EUR').id
        )
        company_isk = self._create_company(
            name="Company ISK", currency_id=self._enable_currency('ISK').id
        )

        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'company_id': company_eur.id,
            'combo_item_ids': [Command.create({'product_id': self.product.id})],
        })

        self.assertEqual(combo.currency_id.name, 'EUR')

        combo.company_id = company_isk

        self.assertEqual(combo.currency_id.name, 'ISK')

    @freeze_time('2000-01-01')
    def test_base_price_multiple_currencies(self):
        self.setup_main_company(currency_code='GBP')
        currency_eur = self._enable_currency('EUR')
        company = self._create_company(currency_id=currency_eur.id)
        # For the sake of this test, we consider that 1 EUR is equivalent to 0.5 GBP.
        currency_eur.rate_ids = [Command.create({
            'name': '2000-01-01', 'rate': 2, 'company_id': company.id
        })]
        product_gbp = self._create_product(list_price=50)
        product_eur_a = self._create_product(company_id=company.id, list_price=90)
        product_eur_b = self._create_product(company_id=company.id, list_price=110)

        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'company_id': company.id,
            'combo_item_ids': [
                Command.create({'product_id': product_gbp.id}),
                Command.create({'product_id': product_eur_a.id}),
                Command.create({'product_id': product_eur_b.id}),
            ],
        })

        self.assertEqual(combo.base_price, 90)

    def test_empty_combo_items_raises(self):
        with self.assertRaises(ValidationError):
            self.env['product.combo'].create({
                'name': "Test combo",
                'combo_item_ids': [],
            })

    def test_duplicate_combo_items_raises(self):
        with self.assertRaises(ValidationError):
            self.env['product.combo'].create({
                'name': "Test combo",
                'combo_item_ids': [
                    Command.create({'product_id': self.product.id}),
                    Command.create({'product_id': self.product.id}),
                ],
            })

    @mute_logger('odoo.sql_db')
    def test_nested_combos_raises(self):
        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'combo_item_ids': [Command.create({'product_id': self.product.id})],
        })
        combo_product = self._create_product(type='combo', combo_ids=[Command.link(combo.id)])

        with self.assertRaises(ValidationError):
            self.env['product.combo'].create({
                'name': "Test combo",
                'combo_item_ids': [Command.create({'product_id': combo_product.id})],
            })

    def test_multi_company_consistency(self):
        company_a = self._create_company(name="Company A")
        company_b = self._create_company(name="Company B")
        product_in_company_a = self._create_product(company_id=company_a.id)

        # Raise if we try to create a combo in company B with a product in company A.
        with self.assertRaises(UserError):
            self.env['product.combo'].create({
                'name': "Test combo",
                'company_id': company_b.id,
                'combo_item_ids': [Command.create({'product_id': product_in_company_a.id})],
            })
        # Don't raise if we try to create a combo in company A with a product in company A.
        combo_in_company_a = self.env['product.combo'].create({
            'name': "Test combo",
            'company_id': company_a.id,
            'combo_item_ids': [Command.create({'product_id': product_in_company_a.id})],
        })

        # Raise if we try to create a combo product in company B with a combo in company A.
        with self.assertRaises(UserError):
            self._create_product(
                company_id=company_b.id,
                type='combo',
                combo_ids=[Command.link(combo_in_company_a.id)],
            )
        # Don't raise if we try to create a combo product in company A with a combo in company A.
        self._create_product(
            company_id=company_a.id,
            type='combo',
            combo_ids=[Command.link(combo_in_company_a.id)],
        )
        # Raise if we try to update a combo product in company A with a combo without company.
        with self.assertRaises(UserError):
            combo_in_company_a.write({
                'company_id': False,
            })
