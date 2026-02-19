# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Ammu Raj (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MassPriceUpdate(models.TransientModel):
    """Change Price and Cost of Products by Percentage"""
    _name = 'mass.price.update'
    _description = "Mass Price Update"

    apply_to = fields.Selection([
        ('all', 'All Products'), ('category', 'Selected Categories'),
        ('selected', 'Selected Products')], default='selected',
        string='Apply To', required=True,
        help='Allows to select the products based on the conditions')
    apply_on = fields.Selection([
        ('price', 'Price'), ('cost', 'Cost')], default='price',
        string='Apply On', required=True, help='Apply on Price or Cost')
    change = fields.Float(string='Change',
                          help='The percentage for adding or reducing to the actual price')
    apply_type = fields.Selection([
        ('add', 'Add'), ('reduce', 'Reduce')], default='add',
        string='Apply Type', required=True,
        help='Choose the applying type whether add or reduce')
    product_ids = fields.Many2many(
        'product.product', string='Products', default=False,
        domain="[('active', '=', True)]", help='Choose the required products')
    category_ids = fields.Many2many(
        'product.category', string='Categories', default=False,
        help='Choose the required Categories')
    line_ids = fields.One2many('change.price.line', 'mass_price_update_id',
                               string='Lines', readonly=True,
                               help='The selected product with updated price')

    @api.onchange('apply_to')
    def _onchange_apply_to(self):
        """When select an option from apply_to, the related records will show"""
        if self.apply_to == 'all':
            self.write({
                'category_ids': [(5,)],
                'line_ids': [(5,)],
                'product_ids': [(6, 0, self.env['product.product'].search(
                    [('active', '=', True)]).ids)]
            })
        elif self.apply_to == 'category':
            self.write({
                'line_ids': [(5,)],
                'product_ids': [(6, 0, self.env['product.product'].search(
                    [('categ_id', 'in', self.category_ids.ids)]).ids)]
            })
        else:
            self.write({
                'product_ids': [(5,)],
                'category_ids': [(5,)],
                'line_ids': [(5,)]
            })

    @api.onchange('product_ids')
    def _onchange_product_ids(self):
        """Updating the products in lines"""
        if self.product_ids:
            self.write({'line_ids': [(5,)]})
            lines = []
            for product in self.product_ids:
                lines.append((0, 0, {'product_id': product._origin.id}))
            self.write({'line_ids': lines})

    @api.onchange('category_ids')
    def _onchange_category_ids(self):
        """When select the category related product will show"""
        if self.category_ids:
            self.write({'line_ids': [(5,)], 'product_ids': [(5,)]})
            lines = []
            products = self.env['product.product'].sudo().search(
                [('categ_id', 'in', self.category_ids.ids)])
            for product in products:
                lines.append((0, 0, {'product_id': product.id}))
            self.write({
                'product_ids': products.ids,
                'line_ids': lines
            })

    def action_change_price(self):
        """This function is used to change the price or cost of products"""
        if self.apply_to == 'category' and not self.product_ids:
            raise UserError(_("Please select any category with products."))
        if self.apply_to == 'selected' and not self.product_ids:
            raise UserError(_("Please select any product."))
        if not self.change:
            raise UserError(_("Please enter the change in percentage."))
        if self.apply_type == 'add':
            percentage_num = 1 + self.change
        else:
            percentage_num = 1 - self.change
        if self.apply_on == 'price':
            for product in self.product_ids:
                product.lst_price = product.lst_price * percentage_num
        else:
            for product in self.product_ids:
                product_template = product.product_tmpl_id
                product_template.standard_price = (
                        product_template.standard_price * percentage_num)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _(
                    f"""The {'sales price' if self.apply_on == 'price'
                    else 'cost'} is updated."""),
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
