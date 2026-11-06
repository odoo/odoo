# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import ast
from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def create(self, vals):
        """Inherited for passing the product Tags."""
        res = super(ProductProduct, self).create(vals)
        if not res.product_tag_ids:
            pro_tag = self.env['ir.config_parameter'].sudo().get_param(
                'odoo_product_tags.product_tag_ids')
            if pro_tag:
                tag_ids = ast.literal_eval(pro_tag)
                res.update({
                    "product_tag_ids": [(6, 0, tag_ids)],
                })
            return res
        else:
            return res

    def action_apply_product_tags(self):
        """Applying product tags"""
        return {
            'name': 'Apply Product Tag',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.tags.wizard',
            'context': {
                'default_product_ids': self.ids,
                'default_is_product': True
            },
            'target': 'new',
        }
