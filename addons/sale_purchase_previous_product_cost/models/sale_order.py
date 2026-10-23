# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2022-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from odoo import models, api, fields
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    sale_date = fields.Datetime(comodel_name='sale.order', string='Sale Date',
                                related='order_id.date_order', store=True)

    def get_product_form(self):
        self.product_id.order_partner_id = self.order_id.partner_id.id
        return {
            'name': self.product_id.name,
            'view_mode': 'form',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.product_id.id
        }


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    purchase_date = fields.Datetime(comodel_name='purchase.order', string='Purchase Date',
                                    related='order_id.date_order', store=True)

    def get_product_form(self):
        self.product_id.order_partner_id = self.order_id.partner_id.id
        return {
            'name': self.product_id.name,
            'view_mode': 'form',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.product_id.id
        }


class ProductTemplate(models.Model):
    _inherit = "product.product"

    order_partner_id = fields.Many2one('res.partner', string="Partner")

    def action_sale_product_prices(self):
        rel_view_id = self.env.ref(
            'sale_purchase_previous_product_cost.last_sale_product_prices_view')
        if self.order_partner_id.id:
            sale_lines = self.env['sale.order.line'].search([('product_id', '=', self.id),
                                                             ('order_partner_id', '=', self.order_partner_id.id)],
                                                            order='create_date DESC').mapped('id')
        else:
            sale_lines = self.env['sale.order.line'].search([('product_id', '=', self.id)],
                                                            order='create_date DESC').mapped('id')
        if not sale_lines:
            raise UserError("No sales history found.!")
        else:
            return {
                'domain': [('id', 'in', sale_lines)],
                'views': [(rel_view_id.id, 'tree')],
                'name': 'Sales History',
                'res_model': 'sale.order.line',
                'view_id': False,
                'type': 'ir.actions.act_window',
            }

    def action_purchase_product_prices(self):
        rel_view_id = self.env.ref(
            'sale_purchase_previous_product_cost.last_sale_product_purchase_prices_view')
        if self.order_partner_id.id:
            purchase_lines = self.env['purchase.order.line'].search([('product_id', '=', self.id),
                                                                     ('partner_id', '=', self.order_partner_id.id)],
                                                                    order='create_date DESC').mapped('id')
        else:
            purchase_lines = self.env['purchase.order.line'].search([('product_id', '=', self.id)],
                                                                    order='create_date DESC').mapped('id')
        if not purchase_lines:
            raise UserError("No purchase history found.!")
        else:
            return {
                'domain': [('id', 'in', purchase_lines)],
                'views': [(rel_view_id.id, 'tree')],
                'name': 'Purchase History',
                'res_model': 'purchase.order.line',
                'view_id': False,
                'type': 'ir.actions.act_window',
            }
