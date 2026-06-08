# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    def _check_delivery_address(self, **kwargs):
        """Override of `website_sale`to check that the shipping address is compliant with Gelato.

        :param res.partner partner_sudo: The partner whose delivery address to check.
        :return: Whether all checked fields are within length limit.
        :rtype: bool
        """
        res = super()._check_delivery_address(**kwargs)
        order_sudo = kwargs.get("order_sudo")
        if not res or not order_sudo:
            return res

        if any(order_sudo.order_line.product_id.mapped("gelato_product_uid")):
            try:
                self._gelato_check_address_length_limit()
            except ValidationError:
                return False
        return True
