from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountInvoiceTax(models.TransientModel):

    _name = 'account.invoice.tax'
    _description = 'Account Invoice Tax'

    tax_id = fields.Many2one('account.tax', required=True)
    amount = fields.float()

    def add_tax(self):
        """ Add the given taxes to all the invoice line of the current invoice """
        if self.env.context.get('active_model') != 'account.move':
            raise UserError(_('This wizard can only be called from the account move'))
        move_id = self.env.context.get('active_id')
        if move_id:
            self.env['account.move'].browse(move_id).invoice_line_ids.write({'tax_ids': [(4, self.tax_id.id)]})
