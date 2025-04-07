from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError


class AccountBalance(models.Model):
    _inherit = 'account.account'

    @api.model
    def get_all_payment_method_line(self):
        lines = self.env['account.payment.method.line'].search([])

        line_data = [{'id': line.id, 'name': line.name} for line in lines]

        return line_data

    @api.model
    def get_all_journals(self):
        journals = self.env['account.journal'].search([])

        journal_data = [{'id': journal.id, 'name': journal.name} for journal in journals]

        return journal_data

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
    def get_all_bills(self):
        bills = self.env['account.move'].search([('move_type', '=', 'in_invoice')])

        account_data = [{'id': bill.id, 'name': bill.name} for bill in bills]

        return account_data

    @api.model
    def get_all_inv(self):
        bills = self.env['account.move'].search([('move_type', '=', 'out_invoice')])

        account_data = [{'id': bill.id, 'name': bill.name} for bill in bills]

        return account_data

    @api.model
    def get_all_payments(self):
        payments = self.env['account.move'].search([('move_type', '=', 'entry')])

        payment_data = [{'id': payment.id, 'name': payment.name} for payment in payments]

        return payment_data

    @api.model
    def get_all_partners(self):
        partners = self.env['res.partner'].search([])

        partner_data = [{'id': partner.id, 'name': partner.name} for partner in partners]

        return partner_data

    @api.model
    def get_balance(self, account_id, end_date, partner_id):
        """
        Calculate the total balance for a specific account as of a given date.

        :param account_id: ID of the account for which to calculate the balance
        :param end_date: The end date up to which the balance is calculated
        :return: A dictionary containing the balance information
        """
        # Create a search domain to filter the account move lines based on the account ID and date
        domain = [('account_id', '=', account_id), ('date', '<=', end_date)]

        # Retrieve account move lines matching the domain, order by date descending
        account_move_lines = self.env['account.move.line'].search(domain, order='date DESC')

        # Compute the total balance from the retrieved account move lines
        total_balance = sum(line.balance for line in account_move_lines)

        # Prepare balance information as a list of dictionaries
        balance_info = {
            'date': end_date,
            'balance': total_balance,
        }

        # Return the balance information
        return {'balance_info': [balance_info]}

    @api.model
    def get_balance_by_customer(self, account_id, end_date, partner_id):
        """
                Calculate the total balance for a specific account as of a given date.

                :param account_id: ID of the account for which to calculate the balance
                :param end_date: The end date up to which the balance is calculated
                :return: A dictionary containing the balance information
                """
        # Create a search domain to filter the account move lines based on the account ID and date
        domain = [('partner_id', '=', partner_id), ('date', '<=', end_date)]

        # Retrieve account move lines matching the domain, order by date descending
        account_move_lines = self.env['account.move.line'].search(domain, order='date DESC')

        # Compute the total balance from the retrieved account move lines
        total_balance = sum(line.amount_residual for line in account_move_lines)

        # Prepare balance information as a list of dictionaries
        balance_info = {
            'date': end_date,
            'balance': total_balance,
        }

        # Return the balance information
        return {'balance_info': [balance_info]}

    @api.model
    def get_balance_by_vendor(self, account_id, end_date, partner_id):
        """
        Calculate the total balance for a specific account as of a given date.

        Parameters:
        - account_id: ID of the account for which the balance is to be calculated.
        - end_date: The end date up to which the balance is calculated.
        - partner_id: Optional ID of the partner associated with the transactions (defaults to 11).

        Returns:
        - A dictionary containing the balance information as a list of dictionaries.
        """

        # Define search criteria to filter account move lines by partner, account ID, and date
        domain = [
            ('partner_id', '=', partner_id),
            ('date', '<=', end_date)
        ]

        # Retrieve account move lines that match the domain criteria, ordered by date in descending order
        account_move_lines = self.env['account.move.line'].search(domain, order='date DESC')

        # Calculate the total balance by summing up the balance of each account move line
        total_balance = sum(line.amount_residual for line in account_move_lines)

        # Assemble the balance information in a dictionary format
        balance_info = {
            'date': end_date,
            'balance': total_balance,
        }

        # Return the compiled balance information
        return {'balance_info': [balance_info]}


    @api.model
    def get_all_customers(self):
        # Define the domain to filter partners based on the customer tag
        domain = [('category_id.name', '=', 'Customer')]
        # domain = []

        # Search for partners based on the domain
        customers = self.env['res.partner'].search(domain)

        # Prepare the partner data
        customer_data = [{'id': customer.id, 'name': customer.name} for customer in customers]

        # Return the customer data
        return customer_data

    @api.model
    def get_all_vendors(self):
        # Define the domain to filter partners based on the vendor tag
        domain = [('category_id.name', '=', 'Vendor')]

        # Search for partners based on the domain
        vendors = self.env['res.partner'].search(domain)

        # Prepare the partner data
        vendor_data = [{'id': vendor.id, 'name': vendor.name} for vendor in vendors]

        # Return the vendor data
        return vendor_data



    @api.model
    def general_ledger_report(self, account_id, start_date, end_date, partner_id):
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
            analytic_account_amount = analytic_info.amount if analytic_info else ""

            partner_type = ""
            if line.partner_id:
                category_names = {category.name for category in line.partner_id.category_id}
                if 'Customer' in category_names and 'Vendor' in category_names:
                    partner_type = 'Customer/Vendor'
                elif 'Customer' in category_names:
                    partner_type = 'Customer'
                elif 'Vendor' in category_names:
                    partner_type = 'Vendor'

            ledger_data.append({
                'date': line.date,
                'debit': line.debit,
                'credit': line.credit,
                'account_root_id': line.account_root_id.id,
                'analytic_move_id': analytic_info.id if analytic_info else None,
                'analytic_account_amount': analytic_account_amount,
                'analytic_account_name': analytic_account_name,
                'partner_id': line.partner_id.id if line.partner_id else "",
                'partner_type': partner_type,
            })

        return {
            'ledger_data': ledger_data,
        }

    @api.model
    def general_ledger_report_by_vendor(self, account_id, start_date, end_date, partner_id):
        # Define the domain to filter move lines based on the partner and date range
        domain = [
            ('partner_id', '=', partner_id),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('amount_residual', '!=', 0)
        ]

        # Search for account move lines that match the domain
        move_lines = self.env['account.move.line'].search(domain)

        ledger_data = []

        for line in move_lines:
            # Get analytic line information related to the move line
            analytic_info = self.env['account.analytic.line'].search([('move_line_id', '=', line.id)], limit=1)
            analytic_account_id = analytic_info.account_id if analytic_info else ""
            analytic_account_name = analytic_account_id.name if analytic_info else ""
            analytic_account_amount = analytic_info.amount if analytic_info else ""

            partner_type = 'Vendor' if line.partner_id else ""

            # Append move line data to the ledger data list
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

        # Return the ledger data
        return {
            'ledger_data': ledger_data,
        }

    @api.model
    def general_ledger_report_by_customer(self, account_id, start_date, end_date, partner_id):
        domain = [
            ('partner_id', '=', partner_id),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('amount_residual', '!=', 0)
        ]
        move_lines = self.env['account.move.line'].search(domain)
        ledger_data = []

        for line in move_lines:
            analytic_info = self.env['account.analytic.line'].search([('move_line_id', '=', line.id)], limit=1)
            ledger_data.append({
                'date': line.date.strftime("%Y-%m-%d") if line.date else "",  # Empty string if None
                'debit': line.debit or 0.0,
                'credit': line.credit or 0.0,
                'account_root_id': line.account_root_id.id if line.account_root_id else 0,
                'analytic_move_id': analytic_info.id if analytic_info else 0,
                'analytic_account_amount': analytic_info.amount if analytic_info else 0.0,
                'analytic_account_name': analytic_info.account_id.name if analytic_info and analytic_info.account_id else "",
                'partner_id': line.partner_id.name if line.partner_id else "Unknown",
                'partner_type': 'Customer' if line.partner_id else "None"
            })
        return {'ledger_data': ledger_data}

    ##create/get/delete_bills
    @api.model
    def create_bill(self, ref, quantity, price_unit, account_id, analytic_account_id, partner_id,
                    bill_date, bill_date_due, narration):
        """
        Create a bill and corresponding analytic line based on the provided data.
        """
        # Prepare the analytic line, if an analytic account ID is provided
        analytic_line_vals = []
        if analytic_account_id:
            analytic_line_vals.append((0, 0, {
                'account_id': analytic_account_id,
                'name': ref,
            }))

        # Prepare the bill line
        bill_line_vals = {
            'name': ref,
            'quantity': quantity,
            'price_unit': price_unit,
            'account_id': account_id,
            'analytic_line_ids': analytic_line_vals,  # Linking analytic lines to the invoice line
        }

        # Create a new Bill record
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'ref': ref,
            'partner_id': partner_id,
            'invoice_date': bill_date,
            'invoice_date_due': bill_date_due,
            'narration': narration,
            'invoice_line_ids': [(0, 0, bill_line_vals)],
        })
        bill.action_post()

        return {
            'Bill ID': bill.id,
            'Bill reference': bill.ref,
            'Bill Number': bill.name,
            'Bill Date': bill.invoice_date,
            'Bill Due Date': bill.invoice_date_due,
            'Supplier': bill.partner_id.name,
            'Amount Total': bill.amount_total,
            'State': bill.payment_state,
        }



    @api.model
    def get_bill(self, bill_id):
        # Define search criteria to filter bills
        domain = [
            ('id', '=', bill_id),
            ('move_type', '=', 'in_invoice'),
        ]

        # Retrieve bills based on the criteria
        bill = self.env['account.move'].search(domain, order='invoice_date')

        # Prepare a list to store bill data
        bill_data = []

        # for bill in bills:
        # Retrieve bill lines for each bill
        bill_lines = bill.invoice_line_ids
        selected_account_id = (
                bill_lines and bill_lines[0].account_id.name or False
        )

        # Assemble bill data
        bill_data.append({
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

    @api.model
    def create_bill_payment(self, bill_ids, journal_id, payment_date, payment_method_line_id):
        AccountMove = self.env['account.move']
        bills = AccountMove.browse(bill_ids)

        if not bills.exists():
            raise UserError("No valid bills found with the provided IDs.")
        if any(bill.state != 'posted' for bill in bills):
            raise UserError("All bills must be posted to proceed with payment.")

        payment_register = self.env['account.payment.register'].with_context({
            'active_model': 'account.move',
            'active_ids': bill_ids,
        }).create({
            'payment_date': payment_date,
            'journal_id': journal_id,
            'payment_method_line_id': payment_method_line_id,
        })

        payments = payment_register.action_create_payments()

        payment_data_list = []

        for bill in bills:
            # Directly accessing move lines and their full_reconcile_id
            for move_line in bill.line_ids:
                if move_line.full_reconcile_id:
                    # Fetch other move lines that share the same full_reconcile_id and have a non-null payment_id
                    reconciled_move_lines = self.env['account.move.line'].search([
                        ('full_reconcile_id', '=', move_line.full_reconcile_id.id),
                        ('payment_id', '!=', False),
                        ('reconciled', '=', True),
                    ])

                    for r_move_line in reconciled_move_lines:
                        payment_data = {
                            'id': r_move_line.payment_id.id,  # ID of the payment
                            'bill_id': bill.id,  # ID of the bill move associated with the payment
                            'amount': r_move_line.debit if r_move_line.debit else r_move_line.credit, # Credit amount
                            'bill_date': bill.date,  # Credit amount
                            'payment_date': r_move_line.date or '',  # Date of the move line
                            'partner_id': r_move_line.partner_id.id if r_move_line.partner_id else 0,  # Partner ID
                            'journal_id': r_move_line.journal_id.id if r_move_line.journal_id else 0,  # Journal ID
                        }
                        payment_data_list.append(payment_data)

        return payment_data_list

    @api.model
    def setup_payment_journal(self, journal_name, account_id, journal_type, payment_method_name):
        """
        Sets up a payment journal and payment method in the accounting system.

        Parameters:
        journal_name (str): Name of the journal to be created or found.
        account_id (int): ID of the account associated with the journal.
        journal_type (str): Type of the journal ('bank' or 'cash').
        payment_method_name (str): Name of the payment method to be created or found.

        Returns:
        tuple: A tuple containing the IDs of the created/found journal and payment method.
        """
        AccountJournal = self.env['account.journal']
        AccountPaymentMethod = self.env['account.payment.method']

        # Create or find the journal
        journal = AccountJournal.search([('name', '=', journal_name)], limit=1)
        if not journal:
            journal_vals = {
                'name': journal_name,
                'type': journal_type,  # 'bank' or 'cash'
                'code': journal_name[:5].upper(),
                'default_account_id': account_id,  # Use the default_account_id field
            }
            journal = AccountJournal.create(journal_vals)

        # Create or find the payment method
        payment_method = AccountPaymentMethod.search([('name', '=', payment_method_name)], limit=1)
        if not payment_method:
            payment_method_vals = {
                'name': payment_method_name,
                'payment_type': 'outbound',  # 'inbound' for customer payments, 'outbound' for supplier payments
                'code': payment_method_name[:10].upper(),
            }
            payment_method = AccountPaymentMethod.create(payment_method_vals)

        # Link the payment method to the journal
        # Assuming outbound payments. Adjust as needed for inbound.
        if payment_method.id not in journal.outbound_payment_method_line_ids.ids:
            journal.write({'outbound_payment_method_line_ids': [(4, payment_method.id)]})

        return journal.id, payment_method.id

    @api.model
    def get_bill_payment_by_journal_entry_id(self, journal_entry_id):
        """
        Retrieves the bill payment details associated with a specific journal entry ID.
        Additionally fetches the bill date from the related account.move record.

        :param journal_entry_id: The ID of the journal entry.
        :return: A dictionary containing the payment details or an error message.
        """
        Payment = self.env['account.payment']
        Move = self.env['account.move']
        # Search for payment associated with the given journal entry
        payment = Payment.search([('move_id', '=', journal_entry_id)], limit=1)

        if payment:
            # Fetch the bill date from the related account.move record
            move = Move.browse([journal_entry_id])
            bill_date = move.date if move else None

            # Prepare a dictionary of relevant payment details
            payment_data = {
                'id': payment.id,
                'name': payment.name,
                'amount': payment.amount,
                'bill_date': bill_date,  # Retrieved from account.move
                'payment_date': payment.date,  # Retrieved from account.move
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
    def cancel_and_delete_bill_payment(self, payment_id=615):
        Payment = self.env['account.move']
        payment = Payment.browse(payment_id)

        if not payment:
            return "Payment not found."

        # Attempt to cancel the payment if it's not already in a cancellable state
        if payment.state not in ['draft', 'cancelled']:
            try:
                # Attempt to cancel the payment
                payment.button_draft()
            except UserError as e:
                return "Failed to cancel payment: {}".format(e)
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

    @api.model
    def create_account(self, name, code, company_id, reconcile, currency_id, tag_ids):
        """
        Create a financial account within Odoo's accounting module.

        Args:
        - name (str): The name of the account.
        - code (str): Unique identifier code for the account.
        - account_type (str): The type of account (e.g., 'asset', 'expense').
        - company_id (int): ID of the company this account belongs to.
        - reconcile (bool): Whether the account should allow reconciliation.
        - currency_id (int, optional): The currency this account operates in.
        - tag_ids (list, optional): List of tag IDs for reporting purposes.

        Returns:
        dict: Dictionary containing a key 'account_info' with list of created account details.

        Raises:
        ValidationError: If any validation fails.
        """

        if self.search([('code', '=', code), ('company_id', '=', company_id)], limit=1):
            raise ValidationError("An account with this code already exists in the selected company.")

        account_vals = {
            'name': name,
            'code': code,
            'reconcile': reconcile,
            'company_id': company_id,
            'account_type': "asset_current",
            'currency_id': currency_id or None,
            'tag_ids': [(6, 0, tag_ids)] if tag_ids else False,
        }

        new_account = self.create(account_vals)

        account_data = [{
            'id': new_account.id,
            'account_name': new_account.name,
            'account_code': new_account.code,
            'account_type': new_account.account_type,
            'is_reconcilable': new_account.reconcile,
            'currency_id': new_account.currency_id.id if new_account.currency_id else 'None',
            'company_id': new_account.company_id.id,
        }]

        response = {'account_info': account_data}
        return response

    @api.model
    def get_account(self, account_id):
        """
        Retrieves a financial account by ID within Odoo's accounting module.

        Args:
        - account_id (int): The ID of the account to retrieve.

        Returns:
        dict: Dictionary containing a key 'account_info' with details of the retrieved account.

        Raises:
        ValidationError: If the account does not exist.
        """
        # Attempt to retrieve the account using the provided ID
        account = self.browse(account_id)

        # Check if the account actually exists
        if not account.exists():
            raise ValidationError("Account with ID {} does not exist.".format(account_id))

        # Gather data from the retrieved account object
        account_data = {
            'id': account.id,
            'account_name': account.name,
            'account_code': account.code,
            'is_reconcilable': account.reconcile,
            'currency_id': account.currency_id.id if account.currency_id else 'None',
            'company_id': account.company_id.id,
        }

        # Package the account data in a response dictionary
        response = {'account_info': account_data}
        return response

    @api.model
    def delete_account(self, account_id):
        """
        Deletes a financial account from Odoo's accounting module.

        Args:
        - account_id (int): The ID of the account to be deleted.

        Returns:
        str: Success or error message.
        """
        Account = self.env['account.account']
        account = Account.search([('id', '=', account_id)])

        if not account:
            return "Account not found."

        # Proceed to delete the account
        try:
            account.unlink()  # Delete the account
            return "Account deleted successfully."
        except Exception as e:
            return "Failed to delete account: {}".format(e)


class ResPartner(models.Model):
    _inherit = 'res.partner'
    @api.model
    def create_customer(self, name, is_company, company_id, email, phone):
        """
        Create a new customer in the Odoo CRM module and assign the 'Customer' category.

        Args:
        - name (str): The name of the customer.
        - is_company (bool): True if the customer is a company, False if an individual.
        - company_id (int): ID of the company this customer is associated with, if any.
        - email (str, optional): Email address of the customer.
        - phone (str, optional): Phone number of the customer.

        Returns:
        dict: Dictionary containing a key 'partner_info' with the created customer details.

        Raises:
        ValidationError: If any validation fails.
        """
        # Search for or create the 'Customer' category
        customer_category = self.env['res.partner.category'].search([('name', '=', 'Customer')], limit=1)
        if not customer_category:
            customer_category = self.env['res.partner.category'].create({'name': 'Customer'})

        # Check for duplicate customer using name and company_id
        if self.search([('name', '=', name), ('company_id', '=', company_id)], limit=1):
            raise ValidationError("A customer with this name already exists in the selected company.")

        # Customer values to create
        customer_vals = {
            'name': name,
            'is_company': is_company,
            'company_id': company_id,
            'email': email or None,
            'phone': phone or None,
            'category_id': [(6, 0, [customer_category.id])],  # Assign the customer category
        }

        # Create new customer record
        new_customer = self.create(customer_vals)

        # Prepare customer data for response
        customer_data = {
            'id': new_customer.id,
            'name': new_customer.name,
            'is_company': new_customer.is_company,
            'email': new_customer.email,
            'phone': new_customer.phone,
            'company_id': new_customer.company_id.id if new_customer.company_id else None,
        }

        return {'partner_info': customer_data}

    @api.model
    def create_vendor(self, name, is_company, company_id, email, phone):
        """
        Create a new customer in the Odoo CRM module and assign the 'Customer' category.

        Args:
        - name (str): The name of the customer.
        - is_company (bool): True if the customer is a company, False if an individual.
        - company_id (int): ID of the company this customer is associated with, if any.
        - email (str, optional): Email address of the customer.
        - phone (str, optional): Phone number of the customer.

        Returns:
        dict: Dictionary containing a key 'partner_info' with the created customer details.

        Raises:
        ValidationError: If any validation fails.
        """
        # Search for or create the 'Customer' category
        vendor_category = self.env['res.partner.category'].search([('name', '=', 'Vendor')], limit=1)
        if not vendor_category:
            vendor_category = self.env['res.partner.category'].create({'name': 'Vendor'})

        # Check for duplicate customer using name and company_id
        if self.search([('name', '=', name), ('company_id', '=', company_id)], limit=1):
            raise ValidationError("A customer with this name already exists in the selected company.")

        # Customer values to create
        vendor_vals = {
            'name': name,
            'is_company': is_company,
            'company_id': company_id,
            'email': email or None,
            'phone': phone or None,
            'category_id': [(6, 0, [vendor_category.id])],  # Assign the customer category
        }

        # Create new customer record
        new_vendor = self.create(vendor_vals)

        # Prepare customer data for response
        vendor_data = {
            'id': new_vendor.id,
            'name': new_vendor.name,
            'is_company': new_vendor.is_company,
            'email': new_vendor.email,
            'phone': new_vendor.phone,
            'company_id': new_vendor.company_id.id if new_vendor.company_id else None,
        }

        return {'partner_info': vendor_data}

    @api.model
    def get_partner(self, partner_id):
        """
        Retrieves a partner by ID within Odoo's CRM module.

        Args:
        - partner_id (int): The ID of the partner to retrieve.

        Returns:
        dict: Dictionary containing a key 'partner_info' with details of the retrieved partner.

        Raises:
        ValidationError: If the partner does not exist.
        """
        partner = self.browse(partner_id)
        if not partner.exists():
            raise ValidationError("Partner with ID {} does not exist.".format(partner_id))

        partner_data = {
            'id': partner.id,
            'name': partner.name,
            'is_company': partner.is_company,
            'email': partner.email,
            'phone': partner.phone,
            'company_id': partner.company_id.id,
        }
        response = {'partner_info': partner_data}
        return response

    @api.model
    def delete_partner(self, partner_id):
        """
        Deletes a partner from Odoo's CRM module.

        Args:
        - partner_id (int): The ID of the partner to be deleted.

        Returns:
        str: Success or error message.
        """
        Partner = self.env['res.partner']
        partner = Partner.search([('id', '=', partner_id)])

        if not partner:
            return "Partner not found."

        try:
            partner.unlink()  # Delete the partner
            return "Partner deleted successfully."
        except Exception as e:
            return "Failed to delete partner: {}".format(e)

class AnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'  # Inherit the existing model

    @api.model
    def create_analytic_account(self, name, code, company_id, plan_id):
        """
        Create an analytic account within Odoo's accounting module.

        Args:
        - name (str): The name of the analytic account.
        - code (str): Unique identifier code for the analytic account.
        - company_id (int): ID of the company this analytic account belongs to.
        - plan_id (int): ID of the plan associated with this analytic account.

        Returns:
        dict: Dictionary containing a key 'account_info' with details of the created analytic account.

        Raises:
        ValidationError: If any validation fails.
        """
        # Check if an analytic account with the same code already exists for the given company
        if self.search([('code', '=', code), ('company_id', '=', company_id)], limit=1):
            raise ValidationError("An analytic account with this code already exists in the selected company.")

        # Prepare values for the new analytic account
        analytic_account_vals = {
            'name': name,
            'code': code,
            'company_id': company_id,
            'plan_id': plan_id
        }

        # Create the new analytic account
        new_analytic_account = self.create(analytic_account_vals)

        # Prepare the response data
        account_data = {
            'id': new_analytic_account.id,
            'account_name': new_analytic_account.name,
            'account_code': new_analytic_account.code,
            'company_id': new_analytic_account.company_id.id,
            'plan_id': new_analytic_account.plan_id.id
        }

        response = {'account_info': account_data}
        return response

    @api.model
    def get_analytic_account(self, account_id):
        """
        Retrieves an analytic account by ID within Odoo's accounting module.

        Args:
        - account_id (int): The ID of the analytic account to retrieve.

        Returns:
        dict: Dictionary containing a key 'account_info' with details of the retrieved analytic account.

        Raises:
        ValidationError: If the analytic account does not exist.
        """
        # Attempt to retrieve the analytic account using the provided ID
        account = self.browse(account_id)

        # Check if the analytic account actually exists
        if not account.exists():
            raise ValidationError("Analytic account with ID {} does not exist.".format(account_id))

        # Gather data from the retrieved analytic account object
        account_data = {
            'id': account.id,
            'account_name': account.name,
            'account_code': account.code,
            'currency_id': account.currency_id.id if account.currency_id else 'None',
            'company_id': account.company_id.id,
        }

        # Package the analytic account data in a response dictionary
        response = {'account_info': account_data}
        return response

    @api.model
    def delete_analytic_account(self, account_id):
        """
        Deletes an analytic account from Odoo's accounting module.

        Args:
        - account_id (int): The ID of the analytic account to be deleted.

        Returns:
        str: Success or error message.
        """
        AnalyticAccount = self.env['account.analytic.account']
        account = AnalyticAccount.search([('id', '=', account_id)])

        if not account:
            return "Analytic account not found."

        # Proceed to delete the analytic account
        try:
            account.unlink()  # Delete the analytic account
            return "Analytic account deleted successfully."
        except Exception as e:
            return "Failed to delete analytic account: {}".format(e)

