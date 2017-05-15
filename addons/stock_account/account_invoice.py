# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################
from openerp import models, api, exceptions, _


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def unlink(self):
        for invoice in self:
            if invoice.origin.find(",") >= 0:
                picking_names = invoice.origin.split(',')
            else:
                picking_names = [invoice.origin]
            for picking_name in picking_names:
                cond = [('name', '=', picking_name)]
                picking = self.env['stock.picking'].search(cond, limit=1)
                if picking and picking.state != 'cancel':
                    raise exceptions.Warning(_('Before deleting invoice should'
                                               ' cancel the picking: %s')
                                             % picking_name)
        return super(AccountInvoice, self).unlink()

    @api.multi
    def action_cancel(self):
        res = super(AccountInvoice, self).action_cancel()
        for invoice in self:
            if invoice.origin.find(",") >= 0:
                picking_names = invoice.origin.split(',')
            else:
                picking_names = [invoice.origin]
            for picking_name in picking_names:
                cond = [('name', '=', picking_name)]
                picking = self.env['stock.picking'].search(cond, limit=1)
                if picking:
                    picking.write({'invoice_state': '2binvoiced'})
        return res
