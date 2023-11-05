from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountBalance(models.Model):
    _inherit = 'account.account'

    @api.model
    def get_all_accounts(self):
        accounts = self.env['account.account'].search([])

        account_data = [{'id': account.id, 'name': account.name} for account in accounts]

        return account_data

    @api.model
    def get_balance(self, account_id, end_date):
        # Define search criteria to filter account move lines
        domain = [('account_id', '=', account_id),
                  ('date', '<=', end_date)]

        # Retrieve the most recent account move line based on the criteria
        move_line = self.env['account.move.line'].search(domain, order='date DESC', limit=1)

        # Prepare ledger data or return an empty list if no move lines are found
        balance_info = [{
            'name': move_line.name,
            'date': move_line.date,
            'balance': move_line.balance,
        }] if move_line else []

        # Return the general ledger data
        return {'balance_info': balance_info}

    @api.model
    def general_ledger_report(self, account_id, start_date, end_date):
        domain = [
            ('account_id', '=', account_id),
            ('date', '>=', start_date),
            ('date', '<=', end_date)
        ]
        move_lines = self.env['account.move.line'].search(domain)

        ledger_data = []

        for line in move_lines:
            analytic_info = self.env['account.analytic.line'].search([('move_line_id', '=', line.id)], limit=1)
            analytic_account_id = analytic_info.account_id if analytic_info else "",
            analytic_account_name = analytic_account_id.name if analytic_info else "",
            analytic_account_amount = analytic_info.amount if analytic_info else "",
            partner_id = line.partner_id.id if line.partner_id else "",
            partner_type = None
            if line.partner_id:
                partner = line.partner_id
                if partner.customer_rank > 0 and partner.supplier_rank > 0:
                    partner_type = 'Customer/Vendor'
                elif partner.customer_rank > 0:
                    partner_type = 'Customer'
                elif partner.supplier_rank > 0:
                    partner_type = 'Vendor'

            else:
                partner_type = ""

            ledger_data.append({
                'date': line.date,
                'debit': line.debit,
                'credit': line.credit,
                'account_root_id': line.account_root_id.id,
                'analytic_move_id': analytic_info.id,
                'analytic_account_amount': analytic_account_amount,
                'analytic_account_name': analytic_account_name,
                'partner_id': partner_id,
                'partner_type': partner_type,

            })

        return {
            'ledger_data': ledger_data,
        }

    @api.model
    def create_bill(self, partner_id, invoice_date, due_date, reference, line_data, global_narration):
        # Retrieve the currency ID for USD
        currency_usd_id = self.env.ref('base.USD').id

        Bill = self.env['account.move']
        invoice_lines = []
        for line in line_data:
            invoice_line_vals = {
                'name': line['description'],
                'quantity': 1,
                'price_unit': line['amount'],
                'account_id': line['account_id'],
                'analytic_account_id': line.get('analytic_account_id', False),  # Add analytic account if provided
            }
            invoice_lines.append((0, 0, invoice_line_vals))

        bill = Bill.create({
            'move_type': 'in_invoice',  # Vendor Bill
            'partner_id': partner_id,
            'invoice_date': invoice_date,
            'invoice_date_due': due_date,
            'invoice_line_ids': invoice_lines,
            'currency_id': currency_usd_id,  # Specify the currency as USD
            'ref': reference,
            'narration': global_narration,  # Global note for the entire bill
        })
        return bill

