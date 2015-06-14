# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################
from openerp import models, api


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.invoice.refund"

    @api.multi
    def compute_refund(self, mode='refund'):
        result = super(AccountInvoiceRefund, self).compute_refund(mode)
        active_ids = self.env.context.get('active_ids')
        if not active_ids:
            return result
        inv_obj = self.env['account.invoice']
        # An example of result['domain'] computed by the parent wizard is:
        # [('type', '=', 'out_refund'), ('id', 'in', [43L, 44L])]
        # The created refund invoice is the first invoice in the
        # ('id', 'in', ...) tupla
        created_inv = [x[2] for x in result['domain']
                       if x[0] == 'id' and x[1] == 'in']
        if created_inv and created_inv[0]:
            for form in self:
                refund_inv_id = created_inv[0][0]
                inv_obj.browse(refund_inv_id).write(
                    {'origin_invoices_ids': [(6, 0, active_ids)],
                     'refund_invoices_description': form.description or ''})
        return result
