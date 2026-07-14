# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.common import SaleCommon

class SaleManagementCommon(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Ensure user has access to sale order templates
        cls.env.user.groups_id += cls.env.ref('sale_management.group_sale_order_template')

        cls.empty_order_template = cls.env['sale.order.template'].create({
            'name': "Test Quotation Template",
        })
