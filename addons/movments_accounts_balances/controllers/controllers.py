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
    def get_bills(self, start_date, end_date, selected_account_id, selected_partner_id, selected_analytic_id):
        # Define search criteria to filter bills
        domain = [('date', '>=', start_date),
                  ('date', '<=', end_date),
                  ('move_type', '=', 'in_invoice'),
                  ]

        # Retrieve bills based on the criteria
        bills = self.env['account.move'].search(domain, order='invoice_date')

        # Prepare a list to store bill data
        bill_data = []
        move_lines = self.env['account.move'].search(domain)
        for line in move_lines:
            account_info = self.env['account.move.line'].search([('move_id', '=', line.id)], limit=1)
            selected_account_id = account_info.account_id.name if account_info else False
            
            # Iterate through the retrieved bills and assemble bill data
            for bill in bills:
                bill_data.append({
                    'id': bill.id,
                    'bill_number': bill.id,
                    'bill_date': bill.date,
                    'supplier_id': bill.partner_id.name,
                    'amount': bill.amount_total,
                    'state': bill.payment_state,
                    'selected_account_id': selected_account_id
                    # Add more bill details here as needed
                })

            # Create a dictionary with a "bill_info" key
            response = {
                'bill_info': bill_data
            }

            return response

    @api.model
    def create_bills(self, bill_data):
        """
        Create bills based on the provided data and associated account.move.line records with analytic lines.

        :param bill_data: A list of dictionaries containing bill information.
        :return: A response indicating the success or failure of bill creation.
        """
        # Initialize a list to store the created bill records
        created_bills = []

        for data in bill_data:
            # Create a new bill record
            bill = self.env['account.move'].create({
                'name': data.get('bill_number'),
                'date': data.get('bill_date'),
                'partner_id': data.get('supplier_id'),
                'amount_total': data.get('total_amount'),
                'move_type': data.get('move_type', 'in_invoice'),  # You may adjust the move_type as needed
                # Add more fields here as needed
            })

            # Create an account.move.line for the bill
            move_line = self.env['account.move.line'].create({
                'move_id': bill.id,
                'account_id': data.get('account_id'),  # Replace with the actual account ID
                'name': data.get('account_entry_description', 'Account Entry Description'),
                'price_unit': data.get('price_unit'),
                # Add more fields as needed
            })

            # Create an account.analytic.line if selected_analytic_id is provided
            selected_analytic_id = data.get('selected_analytic_id')
            if selected_analytic_id:
                analytic_line = self.env['account.analytic.line'].create({
                    'name': 'Analytic Line Description',  # Customize the description
                    'account_id': selected_analytic_id,
                    'move_line_id': move_line.id,
                    'date': bill.date,
                    'amount': data.get('price_unit'),
                    # 'partner_id': 2,
                    # 'account_id': 2,

                    # Add more fields as needed
                })

            # Append the created bill record to the list
            created_bills.append(bill)

        # You can add error handling or validation logic here

        # Create a response indicating the success of bill creation
        response = {
            'message': 'Bills and associated account.move.lines created successfully',
            'created_bills': [(bill.id, bill.name, bill.amount_total, bill.date) for bill in created_bills],
        }

        return response

    @api.model
    def unpost_entry(self, entry):
        if entry.state != 'posted':
            return f"Journal entry (ID: {entry.id}) is not posted, no action required."

        try:
            # Unpost the entry
            entry.button_cancel()

            # You can now make changes to the entry or its related items
            # ...

            return f"Journal entry (ID: {entry.id}) unposted successfully."
        except Exception as e:
            return f"Failed to unpost the journal entry (ID: {entry.id}): {str(e)}"

    @api.model
    def delete_bills(self, start_date, end_date):
        # Define the domain to select records for deletion
        domain = [('date', '>=', start_date),
                  ('date', '<=', end_date),
                  ('move_type', '=', 'in_invoice')]

        # Search for records in the 'account.move' model based on the domain
        bills_to_delete = self.env['account.move'].search(domain)

        deleted_entry_ids = []

        for bill in bills_to_delete:
            # Unreconcile the bill
            if bill.line_ids:
                for line in bill.line_ids:
                    if line.reconciled:
                        line.remove_move_reconcile()

            try:
                # Unpost the entry
                bill.button_draft()
            except Exception as e:
                return f"Failed to unpost the journal entry (ID: {bill.id}): {str(e)}"

            try:
                # Delete the entry
                bill.unlink()
            except Exception as e:
                return f"Failed to delete the journal entry (ID: {bill.id}): {str(e)}"

            deleted_entry_ids.append(bill.id)

        return f"{len(deleted_entry_ids)} bills un-reconciled and deleted successfully."

    @api.model
    def delete_bill(self, bill_id):
        bill = self.env['account.move'].browse(bill_id)
        deleted_entry_ids = []

        if bill:
            # Unreconcile the bill
            if bill.line_ids:
                for line in bill.line_ids:
                    if line.reconciled:
                        line.remove_move_reconcile()

            try:
                # Unpost the entry
                bill.button_draft()
            except Exception as e:
                return f"Failed to unpost the journal entry (ID: {bill.id}): {str(e)}"

            try:
                # Delete the entry
                bill.unlink()
            except Exception as e:
                return f"Failed to delete the journal entry (ID: {bill.id}): {str(e)}"

            deleted_entry_ids.append(bill.id)

            return f"Bill (ID: {bill.id}) un-reconciled and deleted successfully."
        else:
            return "Bill not found."

