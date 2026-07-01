from random import randint

from odoo.addons.point_of_sale.tests.common import TestPoSCommon, CommonPosTest
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon


def archive_products(env):
    # Archive all existing product to avoid noise during the tours
    all_pos_product = env['product.template'].search([('available_in_pos', '=', True)])
    tip = env.ref('point_of_sale.product_product_tip').product_tmpl_id
    (all_pos_product - tip)._write({'active': False})


class CommonPosStockTest(ValuationReconciliationTestCommon, CommonPosTest):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        archive_products(self.env)


class TestPosStockCommon(TestPoSCommon, ValuationReconciliationTestCommon):
    """ Set common values for different special test cases.

    The idea is to set up common values here for the tests
    and implement different special scenarios by inheriting
    this class.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('point_of_sale.group_pos_manager')

        cls.company_data['company'].write({
            'point_of_sale_update_stock_quantities': 'real',
            'country_id': cls.env['res.country'].create({
                'name': 'PoS Land',
                'code': 'WOW',
            }),
        })

        # categ_anglo
        #   - product category with fifo and real_time valuations
        #   - used for checking anglo saxon accounting behavior
        cls.categ_basic = cls.env.ref('product.product_category_services')
        cls.env.company.anglo_saxon_accounting = True
        cls.categ_anglo = cls._create_categ_anglo()

        cls.stock_location_components = cls.env["stock.location"].create({
            'name': 'Shelf 1',
            'location_id': cls.company_data['default_warehouse'].lot_stock_id.id,
        })

    #####################
    ## private methods ##
    #####################

    @classmethod
    def _create_categ_anglo(cls):
        return cls.env['product.category'].create({
            'name': 'Anglo',
            'parent_id': False,
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
            'property_stock_valuation_account_id': cls.company_data['default_account_stock_valuation'].copy().id
        })

    ####################
    ## public methods ##
    ####################

    def create_random_uid(self):
        return ('%05d-%03d-%04d' % (randint(1, 99999), randint(1, 999), randint(1, 9999)))

    @classmethod
    def adjust_inventory(cls, products, quantities):
        """ Adjust inventory of the given products
        """
        for product, qty in zip(products, quantities):
            cls.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product.id,
                'inventory_quantity': qty,
                'location_id': cls.stock_location_components.id,
            }).action_apply_inventory()
