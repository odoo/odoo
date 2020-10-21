# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    landed_cost_ok = fields.Boolean('Is a Landed Cost', help='Indicates whether the product is a landed cost.')

    @api.constrains('landed_cost_ok')
    def _check_landed_cost_ok(self):
        for tmpl in self:
            if tmpl.landed_cost_ok and not (tmpl.type == 'service' and \
                tmpl.categ_id.property_valuation == 'real_time' and \
                tmpl.categ_id.property_cost_method in ('fifo','average')):
                    raise ValidationError(_('Landed costs can only be applied to products with a FIFO or AVCO costing method and an automated inventory valuation (which requires the accounting application to be installed).'))
