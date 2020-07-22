# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _


class AccountInvoiceTax(models.TransientModel):

    _name = 'account.invoice.tax'
    _description = 'Account Invoice Tax'

    move_id = fields.Many2one('account.move', required=True)
    type_operation = fields.Selection([('add', 'Add Tax'), ('remove', 'Remove Tax')])
    tax_id = fields.Many2one('account.tax', required=True)
    amount = fields.Float()

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']
        res['move_id'] = move_ids[0].id if move_ids else False
        res['type_operation'] = self.env.context.get('type_operation', 'add')
        return res

    @api.onchange('move_id')
    def onchange_move_id(self):
        taxes = self.env['account.tax'].search([]) if self.type_operation == 'add' else self.move_id.mapped('invoice_line_ids.tax_ids')
        return {'domain': {'tax_id': [('id', '=', taxes.ids)]}}

    def _get_amount_updated_values(self):
        debit = credit = 0
        if self.move_id.type == "in_invoice":
            if self.amount > 0:
                debit = self.amount
            elif self.amount < 0:
                credit = -self.amount
        else:  # For refund
            if self.amount > 0:
                credit = self.amount
            elif self.amount < 0:
                debit = -self.amount

        # If multi currency enable
        move_currency = self.move_id.currency_id
        company_currency = self.move_id.company_currency_id
        if move_currency and move_currency != company_currency:
            return {'amount_currency': self.amount if debit else -self.amount,
                    'debit': move_currency._convert(debit, company_currency, self.move_id.company_id, self.move_id.invoice_date),
                    'credit': move_currency._convert(credit, company_currency, self.move_id.company_id, self.move_id.invoice_date)}

        return {'debit': debit, 'credit': credit, 'balance': self.amount}

    def add_tax(self):
        """ Add the given taxes to all the invoice line of the current invoice """
        move_id = self.move_id.with_context(check_move_validity=False)
        move_id.invoice_line_ids.write({'tax_ids': [(4, self.tax_id.id)]})
        move_id._recompute_dynamic_lines(recompute_tax_base_amount=True)

        # set amount in the new created tax line
        line_with_tax = move_id.line_ids.filtered(lambda x: x.tax_line_id == self.tax_id)
        line_with_tax.write(self._get_amount_updated_values())
        move_id._onchange_invoice_line_ids()

    def remove_tax(self):
        """ Remove the given taxes to all the invoice line of the current invoice """
        move_id = self.move_id.with_context(check_move_validity=False)
        line_with_tax = move_id.line_ids.filtered(lambda x: x.tax_line_id == self.tax_id)
        move_id.line_ids -= line_with_tax
        move_id.invoice_line_ids.write({'tax_ids': [(3, self.tax_id.id)]})
        move_id._onchange_invoice_line_ids()
