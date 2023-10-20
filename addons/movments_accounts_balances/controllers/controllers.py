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
    def getbalance(self, account_id, start_date, end_date):
        # Define search criteria to filter account move lines
        domain = [
            ('account_id', '=', account_id),
        ]

        if start_date and end_date:
            domain.extend([
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])
        else:
            domain.append(('date', '<=', end_date))

        # Retrieve account move lines based on the criteria
        move_lines = self.env['account.move.line'].search(domain)

        # Prepare a list to store ledger data
        ledger_data = []

        # Iterate through the retrieved move lines and assemble ledger data
        for line in move_lines:
            ledger_data.append({
                'date': line.date,
                'debit': line.debit,
                'credit': line.credit,
                'balance': line.balance,
                'account_root_id': line.account_root_id.id,
                'Name': line.name,

            })

        # Retrieve account information for the specified account_id
        account_info = self.env['account.account'].browse(account_id)

        # Create a dictionary to combine account information and ledger data
        general_ledger = {
            'account_info': {
                'id': account_info.id,
                'name': account_info.name,
                # You can add more account details here as needed
            },
            'ledger_data': ledger_data,
        }

        # Return the general ledger data
        return general_ledger

    @api.model
    def general_ledger_report(self, account_id, start_date, end_date):
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
            ledger_data.append({
                'date': line.date,
                'debit': line.debit,
                'credit': line.credit,
                'balance': line.balance,
                'account_root_id': line.account_root_id.id,
                'Name': line.name,

            })

        # Retrieve account information for the specified account_id
        account_info = self.env['account.account'].browse(account_id)

        # Create a dictionary to combine account information and ledger data
        general_ledger = {
            'account_info': {
                'id': account_info.id,
                'name': account_info.name,
                # You can add more account details here as needed
            },
            'ledger_data': ledger_data,
        }

        # Return the general ledger data
        return general_ledger



