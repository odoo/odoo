# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account_inter_company_rules.tests.common import TestInterCompanyRulesCommon


class TestInterCompanyRulesCommonSOPO(TestInterCompanyRulesCommon):

    @classmethod
    def setUpClass(cls):
        super(TestInterCompanyRulesCommonSOPO, cls).setUpClass()
        # Required for `warehouse_id` to be visible in the view
        cls.env.user.groups_id += cls.env.ref('stock.group_stock_multi_warehouses') \
                                  + cls.env.ref('account.group_delivery_invoice_address')

        # Set warehouse on company A
        cls.company_a.warehouse_id = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_a.id)])

        # Set warehouse on company B
        cls.company_b.warehouse_id = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_b.id)])

        cls.res_users_company_a.groups_id += cls.env.ref('sales_team.group_sale_salesman') + cls.env.ref('purchase.group_purchase_user')
        cls.res_users_company_b.groups_id += cls.env.ref('sales_team.group_sale_salesman') + cls.env.ref('purchase.group_purchase_user')
