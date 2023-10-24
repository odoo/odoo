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
        domain = [('account_id', '=', account_id)]
    
        if start_date and end_date:
            domain.extend([
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])
        
        move_lines = self.env['account.move.line'].search(domain)
        ledger_data = []
    
        for line in move_lines:
            analytic_info = self.env['account.analytic.line'].search([('move_line_id', '=', line.id)], limit=1)
        
            analytic_move_id = analytic_info.id if analytic_info else None
            analytic_amount = analytic_info.amount if analytic_info else None
            analytic_name = analytic_info.name if analytic_info else None
            partner_id = line.partner_id.id if line.partner_id else None
            partner_type = None
            if line.partner_id:
                partner = line.partner_id
                if partner.customer_rank > 0 and partner.supplier_rank > 0:
                    partner_type = 'Customer/Vendor'
                elif partner.customer_rank > 0:
                    partner_type = 'Customer'
                elif partner.supplier_rank > 0:
                    partner_type = 'Vendor'
        
            ledger_data.append({
                'id': line.id,
                'date': line.date,
                'debit': line.debit,
                'credit': line.credit,
                'partner_id': partner_id,  
                'partner_type': partner_type,
                'analytic_move_id': analytic_move_id,
                'analytic_amount': analytic_amount,
                'analytic_name': analytic_name
            })
        return ledger_data