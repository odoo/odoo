# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _


class AccountInvoiceTax(models.TransientModel):

    _name = 'account.invoice.tax'
    _description = 'Account Invoice Tax'

    move_id = fields.Many2one('account.move')
    tax_id = fields.Many2one('account.tax', required=True)
    amount = fields.Float(required=True)

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']
        res['move_id'] = move_ids[0].id if move_ids else False
        return res

    @api.onchange('move_id')
    def onchange_move_id(self):
        taxes = self.env['account.tax'].search([])
        return {'domain': {'tax_id': [('id', '=', taxes.ids)]}}

    def add_tax(self):
        """ Add the given taxes to all the invoice line of the current invoice """
        if self.move_id:
            self.move_id.invoice_line_ids.write({'tax_ids': [(4, self.tax_id.id)]})
            self.move_id.with_context(check_move_validity=False)._recompute_dynamic_lines(recompute_all_taxes=True)
            # TODO set the amount in the line
            # line_with_tax = self.move_id.line_ids.filtered(lambda x: x.tax_line_id == self.tax_id)
            # line_with_tax.with_context(check_move_validity=False).debit = self.amount
