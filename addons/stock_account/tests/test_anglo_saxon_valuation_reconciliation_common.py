# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import fields

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class ValuationReconciliationTestCommon(AccountTestInvoicingCommon):
    """ Base class for tests checking interim accounts reconciliation works
    in anglosaxon accounting. It sets up everything we need in the tests, and is
    extended in both sale_stock and purchase modules to run the 'true' tests.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.stock_account_product_categ = cls.env['product.category'].create({
            'name': 'Test category',
            'property_valuation': 'real_time',
            'property_cost_method': 'fifo',
            'property_stock_valuation_account_id': cls.company_data['default_account_stock_valuation'].id,
        })

        cls.test_product_order = cls.env['product.product'].create({
            'name': "Test product template invoiced on order",
            'standard_price': 42.0,
            'is_storable': True,
            'categ_id': cls.stock_account_product_categ.id,
            'uom_id': cls.uom_unit.id,
        })
        cls.test_product_delivery = cls.env['product.product'].create({
            'name': 'Test product template invoiced on delivery',
            'standard_price': 42.0,
            'is_storable': True,
            'categ_id': cls.stock_account_product_categ.id,
            'uom_id': cls.uom_unit.id,
        })

        cls.res_users_stock_user = cls.env['res.users'].create({
            'name': "Inventory User",
            'login': "su",
            'email': "stockuser@yourcompany.com",
            'group_ids': [(6, 0, [cls.env.ref('stock.group_stock_user').id])],
        })

    @classmethod
    def collect_company_accounting_data(cls, company):
        company_data = super().collect_company_accounting_data(company)

        # Create stock config.
        company_data.update({
            'default_account_stock_valuation': cls.env['account.account'].with_company(company).create({
                'name': 'default_account_stock_valuation',
                'code': 'STOCKVAL',
                'reconcile': True,
                'account_type': 'asset_current',
            }),
            'default_warehouse': cls.env['stock.warehouse'].search(
                [('company_id', '=', company.id)],
                limit=1,
            ),
        })
        return company_data

    def _process_pickings(self, pickings, date=False, quantity=False):

        def do_picking():
            pickings.action_confirm()
            pickings.action_assign()
            if quantity:
                for picking in pickings:
                    for ml in picking.move_line_ids:
                        ml.quantity = quantity
            pickings.move_ids.picked = True
            pickings._action_done()

        if not date:
            date = fields.Date.today()
            do_picking()
            return
        with freeze_time(date):
            do_picking()
