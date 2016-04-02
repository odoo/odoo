# -*- encoding: utf-8 -*-
from openerp import models


class account_invoice_line(models.Model):
    _inherit = ['account.invoice.line']

    def get_digital_purchases(self,uid):
        user = self.env['res.users'].browse(uid)
        partner = user.partner_id

        # Get paid invoices
        purchases = self.sudo().search_read(
            domain=[('invoice_id.state', '=', 'paid'), ('invoice_id.partner_id', '=', partner.id), ('product_id.product_tmpl_id.type', '=', 'digital')],
            fields=['product_id'],
        )

        # I only want product_ids, but search_read insists in giving me a list of
        # (product_id: <id>, name: <product code> <template_name> <attributes>)
        return map(lambda x: x['product_id'][0], purchases)