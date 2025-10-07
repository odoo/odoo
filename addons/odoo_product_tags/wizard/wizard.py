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
from odoo import api, fields, models, _


class ProductTagsWizard(models.TransientModel):
    _name = 'product.tags.wizard'
    _description = 'Product Tags Wizard'

    is_product = fields.Boolean('Is Product', default=False, help='Is Product')
    is_product_template = fields.Boolean('Is Product Template', default=False, help='Is Product Template')
    product_tag_ids = fields.Many2many(
        "product.tag", string="Product Tags", help="Product Tags")
    product_ids = fields.Many2many(
        'product.product', string="Products", readonly=True)
    product_tmp_ids = fields.Many2many(
        'product.template', string="Products", readonly=True)

    def action_apply_template_tags(self):
        """Applying product tag to Template"""
        product_id = self.env['product.template'].sudo().browse(
            self.env.context.get('active_ids'))
        pro_tag_ids = self.product_tag_ids.ids
        for product in product_id:
            product.update({
                "product_tag_ids": [(6, 0, pro_tag_ids)],
            })

    def action_apply_product_tags(self):
        """Applying product tag to Product"""
        product_id = self.env['product.product'].sudo().browse(
            self.env.context.get('active_ids'))
        pro_tag_ids = self.product_tag_ids.ids
        for product in product_id:
            product.update({
                "product_tag_ids": [(6, 0, pro_tag_ids)],
            })
