# -*- coding: utf-8 -*-

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.multi
    def write(self, vals):
        tax_ids = self.env['pos.order.line'].sudo().search([
            ('order_id.session_id.state', '!=', 'closed')
        ]).read(['tax_ids'])
        # Flatten the list of taxes, see https://stackoverflow.com/questions/952914
        tax_ids = set([i for sl in [t['tax_ids'] for t in tax_ids] for i in sl])
        if tax_ids & set(self.ids):
            raise UserError(_(
                'It is forbidden to modify a tax used in a POS order not posted. ' +
                'You must close the POS sessions before modifying the tax.'
            ))
        return super(AccountTax, self).write(vals)
