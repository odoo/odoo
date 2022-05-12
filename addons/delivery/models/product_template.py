# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hs_code = fields.Char(
        string="HS Code",
        help="Standardized code for international shipping and goods declaration. At the moment, only used for the FedEx shipping provider.",
    )

    @api.constrains('sale_ok', 'purchase_ok')
    def _check_is_delivery(self):
        carriers = self.env['delivery.carrier'].sudo().search([('product_id', 'in', self.product_variant_ids.ids)])
        for record in self:
            if (record.sale_ok or record.purchase_ok) and carriers:
                raise ValidationError(_('This product is set as delivery product for the following shipping method(s):\n%s',\
                        '\n'.join(carriers.mapped('display_name'))))
