# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class MembershipInvoice(models.TransientModel):
    _name = "membership.invoice"
    _description = "Membership Invoice"

    product_id = fields.Many2one('product.product', string='Membership', required=True)
    member_price = fields.Float(string='Member Price', digits= dp.get_precision('Product Price'), required=True)

    @api.onchange('product_id')
    def onchange_product(self):
        """This function returns value of  product's member price based on product id.
        """
        price_dict = self.product_id.price_compute('list_price')
        self.member_price = price_dict.get(self.product_id.id) or False

    @api.multi
    def membership_invoice(self):
        if self:
            datas = {
                'membership_product_id': self.product_id.id,
                'amount': self.member_price
            }
        invoice_list = self.env['res.partner'].browse(self._context.get('active_ids')).create_membership_invoice(datas=datas)

        search_view_ref = self.env.ref('account.view_account_invoice_filter', False)
        form_view_ref = self.env.ref('account.invoice_form', False)

        return  {
            'domain': [('id', 'in', invoice_list)],
            'name': 'Membership Invoices',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(False, 'tree'), (form_view_ref and form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }
