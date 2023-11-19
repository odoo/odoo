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
    def get_analytic_accounts(self):
        accounts = self.env['account.analytic.account'].search([])

        account_data = [{'id': account.id, 'name': account.name} for account in accounts]

        return account_data

    @api.model
    def get_all_partners(self):
        partners = self.env['res.partner'].search([])

        partner_data = [{'id': partner.id, 'name': partner.name} for partner in partners]

        return partner_data

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
            analytic_partner_id = analytic_info.partner_id if analytic_info else False
            partner_name = analytic_partner_id.name if analytic_info else False
            analytic_account_id = analytic_info.account_id if analytic_info else ""
            analytic_account_name = analytic_account_id.name if analytic_info else ""
            analytic_account_amount = analytic_info.amount if analytic_info else "",
            partner_id = line.partner_id.id if line.partner_id else ""
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
                'partner_id': line.partner_id.name,
                'partner_type': partner_type,

            })

        return {
            'ledger_data': ledger_data,
        }

    @api.model
    def get_bill(self, bill_id):
        # Define search criteria to filter bills
        domain = [
            ('id', '=', bill_id),
            ('move_type', '=', 'in_invoice'),
        ]

        # Retrieve bills based on the criteria
        bills = self.env['account.move'].search(domain, order='invoice_date')

        # Prepare a list to store bill data
        bill_data = []

        for bill in bills:
            # Retrieve invoice lines for each bill
            invoice_lines = bill.invoice_line_ids
            selected_account_id = (
                    invoice_lines and invoice_lines[0].account_id.name or False
            )

            # Assemble bill data
            bill_data.append({
                'id': bill.id,
                'bill_number': bill.id,
                'bill_date': bill.invoice_date,
                'supplier_id': bill.partner_id.name,
                'amount': bill.amount_total,
                'state': bill.payment_state,
                'selected_account_id': selected_account_id,
                # Add more bill details here as needed
            })

        # Create a dictionary with a "bill_info" key
        response = {'bill_info': bill_data}

        return response

    @api.model
    # def create_bill(self, partner_id, invoice_date, due_date, reference, line_data, global_narration):
    def create_bill(self, bill_vals, partner_id, invoice_date, invoice_date_due, ref, narration):
        """
        Create a bill based on the provided data.

        :param partner_id: Partner ID for the bill.
        :param invoice_date: Invoice date for the bill.
        :param due_date: Due date for the bill.
        :param reference: Reference for the bill.
        :param line_data: List of dictionaries containing line data for the bill.
        :param global_narration: Global narration for the entire bill.
        :return: The created bill record.
        """
        # Prepare the invoice lines
        invoice_lines = []
        for line in bill_vals:
            invoice_line_vals = {
                'name': line.get('description', ''),
                'price_unit': line.get('amount', 0.0),
                'account_id': line.get('account_id'),
                'analytic_account_id': line.get('analytic_account_id', False),
            }
            invoice_lines.append((0, 0, invoice_line_vals))

        # Create a new bill record
        bill = self.env['account.move'].create({

            'move_type': 'in_invoice',
            'partner_id': partner_id,
            'invoice_date': invoice_date,
            'invoice_date_due': invoice_date_due,
            'ref': ref,
            'narration': narration,
            'invoice_line_ids': invoice_lines,
        })

        return bill

    @api.model
    def delete_bill(self, bill_id):
        Bill = self.env['account.move']
        bill = Bill.search([('id', '=', bill_id), ('move_type', '=', 'in_invoice')])

        if not bill:
            return "Bill not found."

        # Check if the bill is posted (validated)
        if bill.state == 'posted':
            # Add logic to cancel related journal entries (if any)
            # Example: bill.button_draft() or bill.button_cancel()
            try:
                bill.button_draft()  # Reset to draft
            except Exception as e:
                return "Failed to reset bill to draft: {}".format(e)

        # Additional logic to unreconcile payments if the bill is reconciled

        try:
            bill.unlink()  # Delete the bill
            return "Bill deleted successfully."
        except Exception as e:
            return "Failed to delete bill: {}".format(e)


















