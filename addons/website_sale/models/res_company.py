# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Labels to be displayed on the payment buttons, see the rest in payment/models/res_company.py
    free_order_label = fields.Char(
        string="Free Order Label",
        help="The label to be displayed on the payment buttons for orders with Total Amount zero",
        default="Confirm Order",
        translate=True,
    )

    def _get_default_pricelist_vals(self):
        """ Override of product. Called at company creation or activation of the pricelist setting.

        We don't want the default website from the current company to be applied on every company

        Note: self.ensure_one()

        :rtype: dict
        """
        values = super()._get_default_pricelist_vals()
        values['website_id'] = False
        return values
