# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.point_of_sale.tests.common import CommonPosTest

# TODO-PARP: Move tests and remove File


@odoo.tests.tagged('post_install', '-at_install')
class TestPosMargin(CommonPosTest):
    """
    Test the margin computation on orders with basic configuration
    The tests contain the base scenarios.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.pos_config_usd

    def test_positive_margin(self):
        """
        Test margin where it should be more than zero
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        # open a session
        self.open_new_session()

        orders = list(self.create_orders([
            {'lines': [[product1, 1]], 'config': self.config},
            {'lines': [[product2, 1]], 'config': self.config},
            {'lines': [[product1, 2], [product2, 2]], 'config': self.config},
        ]).values())

        # check margins
        self.assertEqual(orders[0].margin, 5)
        self.assertEqual(orders[1].margin, 20)
        self.assertEqual(orders[2].margin, 50)

        # check margins percent
        self.assertEqual(orders[0].margin_percent, 0.5)
        self.assertEqual(orders[1].margin_percent, 0.4)
        self.assertEqual(round(orders[2].margin_percent, 2), 0.42)

        # close session
        self.close_pos_session(config=self.config)

    def test_negative_margin(self):
        """
        Test margin where it should be less than zero
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 15)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 100)

        # open a session
        self.open_new_session()

        orders = list(self.create_orders([
            {'lines': [[product1, 1]], 'config': self.config},
            {'lines': [[product2, 1]], 'config': self.config},
            {'lines': [[product1, 2], [product2, 2]], 'config': self.config},
        ]).values())

        # check margins
        self.assertEqual(orders[0].margin, -5)
        self.assertEqual(orders[1].margin, -50)
        self.assertEqual(orders[2].margin, -110)

        # check margins percent
        self.assertEqual(orders[0].margin_percent, -0.5)
        self.assertEqual(orders[1].margin_percent, -1)
        self.assertEqual(round(orders[2].margin_percent, 2), -0.92)

        # close session
        self.close_pos_session(config=self.config)

    def test_full_margin(self):
        """
        Test margin where the product cost is always 0
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10)
        product2 = self.create_product('Product 2', self.categ_basic, 50)

        # open a session
        self.open_new_session()

        orders = list(self.create_orders([
            {'lines': [[product1, 1]], 'config': self.config},
            {'lines': [[product2, 1]], 'config': self.config},
            {'lines': [[product1, 2], [product2, 2]], 'config': self.config},
        ]).values())

        # check margins
        self.assertEqual(orders[0].margin, 10)
        self.assertEqual(orders[1].margin, 50)
        self.assertEqual(orders[2].margin, 120)

        # check margins percent
        self.assertEqual(orders[0].margin_percent, 1)
        self.assertEqual(orders[1].margin_percent, 1)
        self.assertEqual(orders[2].margin_percent, 1)

        # close session
        self.close_pos_session(config=self.config)

    def test_tax_margin(self):
        """
        Test margin with tax on products
        Product 1 price without tax = 10
        Product 2 price without tax = 50
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5, self.taxes['tax7'].ids)
        product2 = self.create_product('Product 2', self.categ_basic, 55, 30, self.taxes['tax10_incl'].ids)

        # open a session
        self.open_new_session()

        orders = list(self.create_orders([
            {'lines': [[product1, 1]], 'config': self.config},
            {'lines': [[product2, 1]], 'config': self.config},
            {'lines': [[product1, 2], [product2, 2]], 'config': self.config},
        ]).values())

        # check margins
        self.assertEqual(orders[0].margin, 5)
        self.assertEqual(orders[1].margin, 20)
        self.assertEqual(orders[2].margin, 50)

        # check margins percent
        self.assertEqual(orders[0].margin_percent, 0.5)
        self.assertEqual(orders[1].margin_percent, 0.4)
        self.assertEqual(round(orders[2].margin_percent, 2), 0.42)

        # close session
        self.close_pos_session(config=self.config)

    def test_other_currency_margin(self):
        """
        Test margin with tax on products and with different currency
        The currency rate is 0.5 so the product price is halved in this currency.
        """

        # change the config
        current_config = self.config
        self.config = self.pos_config_eur

        # same parameters as test_positive_margin
        product1 = self.create_product('Product 1', self.categ_basic, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        # open a session
        self.open_new_session(config=self.config)

        orders = list(self.create_orders([
            {'lines': [[product1, 1]], 'config': self.config},
            {'lines': [[product2, 1]], 'config': self.config},
            {'lines': [[product1, 2], [product2, 2]], 'config': self.config},
        ]).values())

        # check margins in the config currency
        self.assertEqual(orders[0].margin, 2.5)
        self.assertEqual(orders[1].margin, 10)
        self.assertEqual(orders[2].margin, 25)

        # check margins percent which should be the same as test_positive_margin
        self.assertEqual(orders[0].margin_percent, 0.5)
        self.assertEqual(orders[1].margin_percent, 0.4)
        self.assertEqual(round(orders[2].margin_percent, 2), 0.42)

        # close session
        self.close_pos_session(config=self.config)

        # set the config back
        self.config = current_config

    def test_tax_and_other_currency_margin(self):
        """
        Test margin with different currency between products and config with taxes.
        Product 1 price without tax = 10
        Product 2 price without tax = 50
        The currency rate is 0.5 so the product price is halved in this currency.
        """

        # change the config
        current_config = self.config
        self.config = self.pos_config_eur

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5, self.taxes['tax7'].ids)
        product2 = self.create_product('Product 2', self.categ_basic, 55, 30, self.taxes['tax10_incl'].ids)

        # open a session
        self.open_new_session(config=self.config)

        orders = list(self.create_orders([
            {'lines': [[product1, 1]], 'config': self.config},
            {'lines': [[product2, 1]], 'config': self.config},
            {'lines': [[product1, 2], [product2, 2]], 'config': self.config},
        ]).values())

        # check margins in the config currency
        self.assertEqual(orders[0].margin, 2.5)
        self.assertEqual(orders[1].margin, 10)
        self.assertEqual(orders[2].margin, 25)

        # check margins percent which should be the same as test_tax_margin
        self.assertEqual(orders[0].margin_percent, 0.5)
        self.assertEqual(orders[1].margin_percent, 0.4)
        self.assertEqual(orders[2].margin_percent, 0.4167)

        # close session
        self.close_pos_session(config=self.config)

        # set the config back
        self.config = current_config

    def test_return_margin(self):
        """
        Test margin where we return product (negative line quantity)
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        # open a session
        self.open_new_session()

        orders = list(self.create_orders([
            {'is_refund': True, 'lines': [[product1, -1]], 'config': self.config},
            {'is_refund': True, 'lines': [[product2, -1]], 'config': self.config},
            {'is_refund': True, 'lines': [[product1, -2], [product2, -2]], 'config': self.config},
        ]).values())

        # check margins
        self.assertEqual(orders[0].margin, -5)
        self.assertEqual(orders[1].margin, -20)
        self.assertEqual(orders[2].margin, -50)

        # check margins percent
        self.assertEqual(orders[0].margin_percent, 0.5)
        self.assertEqual(orders[1].margin_percent, 0.4)
        self.assertEqual(round(orders[2].margin_percent, 2), 0.42)

        # close session
        self.close_pos_session(config=self.config)
