from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


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
            analytic_account_id = analytic_info.account_id if analytic_info else ""
            analytic_account_name = analytic_account_id.name if analytic_info else ""
            analytic_account_amount = analytic_info.amount if analytic_info else "",
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

    ##create/get/delete_bills
    @api.model
    def create_bill(self, description, quantity, price_unit, account_id, analytic_account_id, partner_id,
                    bill_date, bill_date_due, narration):
        """
        Create a bill and corresponding analytic line based on the provided data.
        """
        # Prepare the analytic line, if an analytic account ID is provided
        analytic_line_vals = []
        if analytic_account_id:
            analytic_line_vals.append((0, 0, {
                'account_id': analytic_account_id,
                'name': description,
            }))

        # Prepare the bill line
        bill_line_vals = {
            'name': description,
            'quantity': quantity,
            'price_unit': price_unit,
            'account_id': account_id,
            'analytic_line_ids': analytic_line_vals,  # Linking analytic lines to the invoice line
        }

        # Create a new Bill record
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner_id,
            'invoice_date': bill_date,
            'invoice_date_due': bill_date_due,
            'narration': narration,
            'invoice_line_ids': [(0, 0, bill_line_vals)],
        })
        bill.action_post()

        return bill

    @api.model
    def get_bill(self, bill_id):
        """
        Retrieve a bill and its details based on the bill ID.
        :param bill_id: ID of the bill to retrieve.
        :return: A dictionary containing the bill data or an error message.
        """
        # Define search criteria to filter bills
        domain = [
            ('id', '=', bill_id),
            ('move_type', '=', 'in_invoice'),
        ]

        # Retrieve the bill based on the criteria
        bill = self.env['account.move'].search(domain, order='invoice_date', limit=1)
        if not bill:
            return {'error': 'Bill not found'}

        # Prepare data for invoice lines
        invoice_line_data = [{
            'line_id': line.id,
            'account_id': line.account_id.id,
            'account_name': line.account_id.name,
            'quantity': line.quantity,
            'price_unit': line.price_unit,
        } for line in bill.invoice_line_ids]

        # Assemble bill data
        bill_data = {
            'id': bill.id,
            'bill_number': bill.ref,
            'bill_date': bill.invoice_date,
            'supplier_id': bill.partner_id.name,
            'amount': bill.amount_total,
            'state': bill.payment_state,
            'invoice_lines': invoice_line_data,
        }

        return {'bill_info': bill_data}



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

    ##create/get/delete_bills payment
    @api.model
    def create_bill_payment(self, bill_id, journal_id, payment_date, payment_method_line_id):
        Payment = self.env['account.payment']
        Bill = self.env['account.move']
        bill_id = Bill.browse(bill_id)

        if not bill_id:
            raise ValueError("No bills found with the provided IDs")

        total_amount = sum(bill.amount_residual for bill in bill_id)
        payment_vals = {
            'amount': total_amount,
            'date': payment_date,
            'partner_id': bill_id[0].partner_id.id,
            'partner_type': 'supplier',
            'payment_type': 'outbound',
            'payment_method_line_id': payment_method_line_id,
            'journal_id': journal_id
        }

        payment = Payment.create(payment_vals)
        payment.action_post()

        # Register payment against each bill
        for bill in bill_id:
            bill.action_register_payment()

        # Convert the payment record to a dictionary
        payment_data = {
            'id': payment.id,
            'amount': payment.amount,
            'date': payment.date,
            'partner_id': payment.partner_id.id,
            'partner_type': payment.partner_type,
            'payment_type': payment.payment_type,
            'payment_method_line_id': payment.payment_method_line_id.id,
            'journal_id': payment.journal_id.id
        }

        return payment_data


    @api.model
    def get_bill_payment_by_journal_entry_id(self, journal_entry_id):
        Payment = self.env['account.payment']
        # Search for payment associated with the given journal entry
        payment = Payment.search([('move_id', '=', journal_entry_id)], limit=1)

        if payment:
            # Prepare a dictionary of relevant payment details
            payment_data = {
                'id': payment.id,
                'name': payment.name,
                'amount': payment.amount,
                # 'payment_date': payment.payment_date,
                'partner_id': payment.partner_id.id,
                'partner_name': payment.partner_id.name,
                'state': payment.state,
                # Include other fields as necessary
            }
            return payment_data
        else:
            return {'error': "No payment found for the provided journal entry ID."}


    @api.model
    def delete_bill_payment(self, payment_id):
        invoice = self.env['account.move']
        payment = invoice.search([('id', '=', payment_id), ('move_type', '=', 'in_invoice')])

        if not payment:
            return "Payment not found."

        # Check if the bill is posted (validated)
        if payment.state == 'posted':
            # Add logic to cancel related journal entries (if any)
            # Example: bill.button_draft() or bill.button_cancel()
            try:
                payment.button_draft()  # Reset to draft
            except Exception as e:
                return "Failed to reset Payment to draft: {}".format(e)

        # Additional logic to unreconcile payments if the Invoice is reconciled

        try:
            payment.unlink()  # Delete the bill
            return "Payment deleted successfully."
        except Exception as e:
            return "Failed to delete Payment: {}".format(e)

    #### create / get / delete_invoice_payment



    @api.model
    def cancel_and_delete_bill_payment(self, payment_id):
        Payment = self.env['account.move']
        payment = Payment.browse(payment_id)

        if not payment:
            return "Payment not found."

        # Attempt to cancel the payment if it's not already in a cancellable state
        if payment.state not in ['draft', 'cancelled']:
            try:

            except UserError as e:
                return "Failed to cancel payment: {}".format(e)
            except ValidationError as e:
                return "Validation error occurred: {}".format(e)
            except Exception as e:
                return "Unexpected error occurred: {}".format(e)

        # Check again if the payment is in a cancellable state after attempting cancellation
        if payment.state in ['draft', 'cancelled']:
            try:
                payment.unlink()
                return "Payment deleted successfully."
            except Exception as e:
                return "Failed to delete payment: {}".format(e)
        else:
            return "Payment cannot be deleted as it is not in draft or cancelled state."



















