# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp


class membership_invoice(models.TransientModel):
    """Membership Invoice"""

    _name = "membership.invoice"
    _description = "Membership Invoice"
    product_id = fields.Many2one('product.product', 'Membership', required=True)
    member_price = fields.Float('Member Price', digits=dp.get_precision('Product Price'), required=True)
    
    @api.onchange('product_id')
    def onchange_product(self):
        """This function returns value of  product's member price based on product id.
        """
        if not self.product_id:
            self.member_price = False
        else:
            self.member_price = self.product_id.price_get()[self.product_id.id]

    @api.multi
    def membership_invoice(self):
        partner_id = None
        ResPartner = self.env['res.partner']
        datas = {}
        pid = self.env.context.get('active_ids', [])
        if self:
            datas.update(membership_product_id=self.product_id.id, amount=self.member_price)
        if pid:
            partner_id = ResPartner.browse(pid)
            invoice_list = partner_id.create_membership_invoice(datas=datas)

        try:
            search_view_id = self.env.ref('account.view_account_invoice_filter').id
        except ValueError:
            search_view_id = False
        try:
            form_view_id = self.env.ref('account.invoice_form').id
        except ValueError:
            form_view_id = False

        return {
            'domain': [('id', 'in', invoice_list)],
            'name': 'Membership Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(False, 'tree'), (form_view_id, 'form')],
            'search_view_id': search_view_id,
        }
