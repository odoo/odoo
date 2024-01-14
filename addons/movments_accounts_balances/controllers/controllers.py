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

    ##create/get/delete_bills
    @api.model
    def create_bill(self, bill_vals, partner_id, bill_date, bill_date_due, reference, narration):
        """
        Create a bill and corresponding analytic lines based on the provided data.
        """
        # Prepare the invoice lines
        bill_lines = []
        for line in bill_vals:
            bill_line_vals = {
                'name': line.get('description', ''),
                'quantity': line.get('quantity', 1.0),
                'price_unit': line.get('price_unit', 0.0),
                'account_id': line.get('account_id'),
                # Assuming that the analytic account ID is also provided in line
                'analytic_account_id': line.get('analytic_account_id'),
            }
            bill_lines.append((0, 0, bill_line_vals))

        # Create a new AR invoice record
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner_id,
            'invoice_date': bill_date,
            'invoice_date_due': bill_date_due,
            'ref': reference,
            'narration': narration,
            'invoice_line_ids': bill_lines,
        })
        bill.action_post()

        # Create analytic lines for each invoice line if analytic_account_id is provided
        for line in bill.invoice_line_ids:
            if line.analytic_account_id:
                self.env['account.analytic.line'].create({
                    'account_id': line.analytic_account_id.id,
                    'name': line.name,
                    'amount': line.price_subtotal,  # or any other relevant amount
                    'move_id': line.id,
                })

        return {
            "ID": bill.id,
            "Name": bill.name,
            "Amount": bill.amount_total,
            "Date": bill.invoice_date,
            "Due Date": bill.invoice_date_due
        }

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
    def create_bill_payment(self, bills_ids, journal_id, payment_method_line_id):
        Payment = self.env['account.payment']
        Bill = self.env['account.move']
        bills = Bill.browse(bills_ids)

        total_amount = sum(bill.amount_residual for bill in bills)
        payment_vals = {
            'amount': total_amount,
            'partner_id': bills[0].partner_id.id,  # Assuming all bills are for the same partner
            'partner_type': 'supplier',
            'payment_type': 'outbound',
            'journal_id': journal_id,
            'payment_method_line_id': payment_method_line_id,

        }

        payment = Payment.create(payment_vals)
        payment.action_post()

        # Reconcile each bill with the payment
        # for bill in bills:
        #     payment.register_payment(bill.invoice_payments_widget)

        return payment.id

    @api.model
    def get_bill_payment(self, payment_id):
        # Define search criteria to filter bills
        domain = [
            ('id', '=', payment_id),
            ('move_type', '=', 'in_invoice'),
        ]

        # Retrieve bills based on the criteria
        payment = self.env['account.move'].search(domain, order='invoice_date')

        # Prepare a list to store bill data
        payment_data = []

        # for bill in bills:
        # Retrieve invoice lines for each bill
        payment_lines = payment.invoice_line_ids
        selected_account_id = (
                payment_lines and payment_lines[0].account_id.name or False
        )

        # Assemble bill data
        payment_data.append({
            'id': payment.id,
            'bill_number': payment.id,
            'bill_date': payment.invoice_date,
            'supplier_id': payment.partner_id.name,
            'amount': payment.amount_total,
            'state': payment.payment_state,
            'selected_account_id': selected_account_id,
            # Add more bill details here as needed
        })

        # Create a dictionary with a "bill_info" key
        response = {'payment_info': payment_data}

        return response

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



















