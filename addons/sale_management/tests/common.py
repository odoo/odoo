# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.common import SaleCommon


class SaleManagementCommon(SaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Ensure user has access to sale order templates
        cls.env.user.group_ids += cls.env.ref('sale_management.group_sale_order_template')

        cls.empty_order_template = cls.env['sale.order.template'].create({
            'name': "Test Quotation Template",
        })

    @staticmethod
    def _get_optional_product_lines(order):
        """Returns the order lines that are optional products. """
        return order.order_line.filtered(
            lambda line: not line.display_type and line._is_line_optional(),
        )
