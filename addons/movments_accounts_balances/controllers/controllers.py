import re
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountBalance(models.Model):
    _inherit = 'account.account'

    @api.model
    def getbalance(self, target_date_start, target_date_end, selected_account_id):
        # Initialize a list to store the results as dictionaries
        results = []

        try:
            # Check if target_date_start is provided
            if not target_date_start:
                raise ValidationError("Start date is mandatory.")

            # Check if target_date_end is provided
            if not target_date_end:
                raise ValidationError("End date is mandatory.")

            # Convert the selected account ID to a string
            selected_account_id = str(selected_account_id)

            # Retrieve the selected account based on the provided account ID
            selected_account = self.env['account.account'].browse(selected_account_id)

            if selected_account:
                # Calculate the balance for the selected account within the date range
                self.env.cr.execute("""
                    SELECT a.id AS account_id, a.name AS account_name, a.root_id AS root_id,
                           l.date AS date, COALESCE(SUM(debit - credit), 0) AS balance
                    FROM account_move_line AS l
                    LEFT JOIN account_account AS a ON l.account_id = a.id
                    WHERE l.account_id = %s AND l.date >= %s AND l.date <= %s
                    GROUP BY a.id, a.name, a.root_id, l.date
                """, (selected_account_id, target_date_start, target_date_end))

                results += self.env.cr.dictfetchall()
        except ValidationError as e:
            error_message = str(e)

            # Extract the main error message using regular expressions
            match = re.search(r"'([^']*)'", error_message)
            if match:
                main_error_message = match.group(1)
                print("Error:", main_error_message)
            else:
                print("Error format not recognized.")

        return results

    @api.model
    def get_all_accounts(self):
        accounts = self.env['account.account'].search([])

        account_ids = [str(account.id) for account in accounts]

        return account_ids
