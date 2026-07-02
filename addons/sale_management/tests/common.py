# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.common import SaleCommon


class SaleManagementCommon(SaleCommon):
    # Common (non-final): design groups inherited from SaleCommon; final subclasses redefine the full list.
    _test_groups = (
        'base.group_user',
        'product.group_product_manager',  # FIXME: use base.group_user
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = 'Test Sales & Product Manager'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.empty_order_template = cls.env["sale.order.template"].create({
            "name": "Test Quotation Template"
        })

    @staticmethod
    def _get_optional_product_lines(order):
        """Return the order lines that are optional products."""
        return order.order_line.filtered(
            lambda line: not line.display_type and line._is_line_optional()
        )
