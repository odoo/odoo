from odoo import models, api
from odoo.exceptions import ValidationError

class AccountBalance(models.Model):
    _inherit = 'account.account'

    @api.model
    def get_all_accounts(self):
        accounts = self.env['account.account'].search([])

        account_data = [{'id': account.id, 'name': account.name} for account in accounts]

        return account_data

    @api.model
    def get_balance(self, account_id, start_date, end_date):
        # Define search criteria to filter account move lines
        domain = [
            ('account_id', '=', account_id),
            ('date', '<=', end_date)
        ]

        # Retrieve account move lines based on the criteria
        move_lines = self.env['account.move.line'].search(domain, order='date DESC', limit=1)
    
        balance_info = {}
        if move_lines:
            move_line = move_lines[0]
            balance_info = {
                'date': move_line.date,
                'balance': move_line.balance
            }
        
        return balance_info

    @api.model
    def get_general_ledger(self, account_id, start_date, end_date):
        # Define search criteria to filter account move lines
        domain = [
            ('account_id', '=', account_id),
        ]

        if start_date and end_date:
            domain.extend([
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])

        move_lines = self.env['account.move.line'].search(domain)

        # Prepare a list to store ledger data
        ledger_data = []

        # Iterate through the retrieved move lines and assemble ledger data
        for line in move_lines:
            move_line_id = line.id
            analytic_account_info = self.env['account.analytic.line'].search([('move_line_id', '=', move_line_id)])
            if analytic_account_info:
                # Get the first analytic move ID if available
                analytic_move_id = analytic_account_info[0].id
                analytic_amount = analytic_account_info[0].amount
                analytic_name = analytic_account_info[0].name
            else:
                analytic_move_id = None
                analytic_amount = None
                analytic_name = None

            ledger_data.append({
                'id': line.id,
                'date': line.date,
                'debit': line.debit,
                'credit': line.credit,
                'analytic_move_id': analytic_move_id,
                'analytic_amount': analytic_amount,
                'analytic_name': analytic_name

            })

        # Return the general ledger data
        return ledger_data



