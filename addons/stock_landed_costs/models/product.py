# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import UserError
from odoo import _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    landed_cost_ok = fields.Boolean('Is a Landed Cost', help='Indicates whether the product is a landed cost.')

    def write(self, vals):
        for product in self:
            if (('type' in vals and vals['type'] != 'service') or ('landed_cost_ok' in vals and not vals['landed_cost_ok'])) and product.type == 'service' and product.landed_cost_ok:
                if self.env['account.move.line'].search_count([('product_id', 'in', product.product_variant_ids.ids), ('is_landed_costs_line', '=', True)]):
                    raise UserError(_("You cannot change the product type or disable landed cost option because the product is used in an account move line."))
                vals['landed_cost_ok'] = False

        return super().write(vals)
