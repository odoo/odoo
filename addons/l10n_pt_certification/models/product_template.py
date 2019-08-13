# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # 3.3.5
    @api.constrains('name')
    def _check_name_inalterability(self):
        for rec in self:
            if rec.env['account.invoice.line'].search_count([('product_id.product_tmpl_id', '=', rec.id)]):
                raise ValidationError(_("You can't modify the name of a product with created invoices."))
