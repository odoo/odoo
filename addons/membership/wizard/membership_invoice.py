# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MembershipInvoice(models.TransientModel):
    _name = 'membership.invoice'
    _description = "Membership Invoice"

    product_id = fields.Many2one('product.product', string='Membership', required=True)
    member_price = fields.Float(string='Member Price', digits='Product Price', required=True)

    @api.onchange('product_id')
    def onchange_product(self):
        """This function returns value of  product's member price based on product id.
        """
        price_dict = self.product_id._price_compute('list_price')
        self.member_price = price_dict.get(self.product_id.id) or False

    def membership_invoice(self):
        invoice_list = self.env['res.partner'].browse(self._context.get('active_ids')).create_membership_invoice(self.product_id, self.member_price)

        search_view_ref, form_view_ref, list_view_ref = self.env.ref(
            'account.view_account_invoice_filter',
            'account.view_move_form',
            'account.view_move_tree',
        )

        return  {
            'domain': [('id', 'in', invoice_list.ids)],
            'name': 'Membership Invoices',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'views': [(list_view_ref.id, 'list'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and [search_view_ref.id],
        }
