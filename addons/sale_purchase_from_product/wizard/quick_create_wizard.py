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

from odoo import fields, models, api


class QuickCreateOrder(models.TransientModel):
    _name = 'quick.sale.purchase.wizard'
    _description = 'Quick Create Wizard'

    def _sale_ids_domain(self):
        """list out only the draft orders"""
        return [('state', 'in', ['draft', 'sent'])]

    type = fields.Selection([('new_order', 'Create New Order'), ('existing_order', 'Add to existing Orders')],
                            required=True, default='new_order')
    partner_id = fields.Many2one('res.partner', tring="Customer")
    order_date = fields.Datetime(string="Order Date")
    payment_term_id = fields.Many2one('account.payment.term', string="Payment Terms")
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    line_ids = fields.One2many('quick.sale.line.wizard', 'order_id', string="Sale Order Line")
    sale_ids = fields.Many2many('sale.order', string="Sale Orders", domain=_sale_ids_domain)

    @api.model
    def default_get(self, fields):
        res = super(QuickCreateOrder, self).default_get(fields)
        active_records = self.env.context.get('active_ids', [])
        products = self.env['product.product'].search([('id', 'in', active_records)])
        wizard_line = [(5, 0, 0)]
        for rec in products:
            line = (0, 0, {
               'product_id': rec.id,
               'product_uom_qty': 1,
               'price_unit': rec.lst_price,
               'tax_id': rec.taxes_id.ids,
            })
            wizard_line.append(line)
        res.update({
            'line_ids': wizard_line})
        return res

    def action_update_order(self):
        """Update Sale Order"""
        for order in self.sale_ids:
            order.update({
                'order_line': [(0, 0, {
                    'product_id': rec.product_id.id,
                    'product_uom_qty': rec.product_uom_qty,
                    'price_unit': rec.price_unit,
                    'tax_id': rec.tax_id.ids,
                }) for rec in self.line_ids]
            })

    def action_create(self):
        """Create Sale Order"""
        order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_id.id,
            'date_order': self.order_date if self.order_date else fields.datetime.now(),
            'user_id': self.user_id.id,
            'payment_term_id': self.payment_term_id.id,
            'order_line': [(0, 0, {
                'product_id': rec.product_id.id,
                'product_uom_qty': rec.product_uom_qty,
                'price_unit': rec.price_unit,
                'tax_id': rec.tax_id.ids,
            }) for rec in self.line_ids]
        })
        return order

    def action_create_view(self):
        """Create and view the order created"""
        order = self.action_create()
        view = self.env['ir.model.data']._xmlid_lookup('sale.view_order_form')[2]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': order.id,
            'view_mode': 'form',
            'views': [(view, "form"), (False, "form")],
            'view_id': view,
        }

