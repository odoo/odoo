# -*- coding: utf-8 -*-
from odoo.addons.sale.tests.common import TestSaleCommonBase


class TestSaleFlow(TestSaleCommonBase):
    ''' Test running at-install to test flows independently to other modules, e.g. 'sale_stock'. '''

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        user = cls.env['res.users'].create({
            'name': 'Because I am saleman!',
            'login': 'saleman',
            'groups_id': [(6, 0, cls.env.user.groups_id.ids), (4, cls.env.ref('account.group_account_user').id)],
        })
        user.partner_id.email = 'saleman@test.com'

        # Shadow the current environment/cursor with the newly created user.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': cls.env.ref('base.USD').id,
        })
        cls.company_data = cls.setup_sale_configuration_for_company(cls.company)

        cls.partner_a = cls.env['res.partner'].create({
            'name': 'partner_a',
            'company_id': False,
        })

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
        })

        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Test analytic_account',
            'code': 'analytic_account',
            'plan_id': cls.analytic_plan.id,
            'company_id': cls.company.id,
            'partner_id': cls.partner_a.id
        })

        user.company_ids |= cls.company
        user.company_id = cls.company

    def test_qty_delivered(self):
        ''' Test 'qty_delivered' at-install to avoid a change in the behavior when 'sale_stock' is installed. '''

        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'analytic_account_id': self.analytic_account.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [
                (0, 0, {
                    'name': self.company_data['product_order_cost'].name,
                    'product_id': self.company_data['product_order_cost'].id,
                    'product_uom_qty': 2,
                    'qty_delivered': 1,
                    'product_uom': self.company_data['product_order_cost'].uom_id.id,
                    'price_unit': self.company_data['product_order_cost'].list_price,
                }),
                (0, 0, {
                    'name': self.company_data['product_delivery_cost'].name,
                    'product_id': self.company_data['product_delivery_cost'].id,
                    'product_uom_qty': 4,
                    'qty_delivered': 1,
                    'product_uom': self.company_data['product_delivery_cost'].uom_id.id,
                    'price_unit': self.company_data['product_delivery_cost'].list_price,
                }),
            ],
        })

        sale_order.action_confirm()

        self.assertRecordValues(sale_order.order_line, [
            {'qty_delivered': 1.0},
            {'qty_delivered': 1.0},
        ])
