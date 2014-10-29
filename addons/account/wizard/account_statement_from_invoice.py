import time
from openerp import models, fields, api, _

class account_statement_from_invoice_lines(models.TransientModel):
    """
    Generate Entries by Statement from Invoices
    """
    _name = "account.statement.from.invoice.lines"
    _description = "Entries by Statement from Invoices"

    line_ids = fields.Many2many('account.move.line', string='Invoices')

    @api.multi
    def populate_statement(self):
        statement_id = self._context.get('statement_id', False)
        if not statement_id:
            return {'type': 'ir.actions.act_window_close'}
        if not self.line_ids:
            return {'type': 'ir.actions.act_window_close'}

        CurrencyObj = self.env['res.currency']
        statement = self.env['account.bank.statement'].browse(statement_id)

        # for each selected move lines
        for line in self.line_ids:
            ctx = self._context.copy()
            #  take the date for computation of currency => use payment date
            ctx['date'] = time.strftime('%Y-%m-%d')
            amount = 0.0

            if line.debit > 0:
                amount = line.debit
            elif line.credit > 0:
                amount = -line.credit

            if line.amount_currency:
                amount = CurrencyObj.with_context(ctx).compute(line.currency_id.id,
                    statement.currency.id, line.amount_currency)
            elif (line.invoice and line.invoice.currency_id.id != statement.currency.id):
                amount = CurrencyObj.with_context(ctx).compute(line.invoice.currency_id.id,
                    statement.currency.id, amount)

            context = self._context.copy()
            context.update({'move_line_ids': [line.id],
                            'invoice_id': line.invoice.id})

            self.env['account.bank.statement.line'].with_context(context).create({
                'name': line.name or '?',
                'amount': amount,
                'partner_id': line.partner_id.id,
                'statement_id': statement_id,
                'ref': line.ref,
                'date': statement.date,
            })
        return {'type': 'ir.actions.act_window_close'}
