from odoo import models, api
from odoo.exceptions import ValidationError

class AccountBalance(models.Model):
    _inherit = 'account.account'

    @api.model
    def getbalance(self, start_date, end_date, selected_account_id):
        results = []

        try:
            # Convert the selected account ID to an integer
            selected_account_id = int(selected_account_id)

            # Retrieve the selected account based on the provided account ID
            selected_account = self.env['account.account'].browse(selected_account_id)

            if selected_account:
                if not start_date:  # Check if start_date is not provided
                    # Apply query 2 when start_date is not provided
                    query = """
                        SELECT a.id AS account_id, a.name AS account_name, a.root_id AS root_id,
                               l.date AS date, COALESCE(SUM(debit - credit), 0) AS balance
                        FROM account_move_line AS l
                        LEFT JOIN account_account AS a ON l.account_id = a.id
                        WHERE l.account_id = %s AND l.date <= %s
                        GROUP BY a.id, a.name, a.root_id, l.date
                    """
                    self.env.cr.execute(query, (selected_account_id, end_date))
                else:
                    # Apply query 1 when start_date is provided
                    query = """
                        SELECT a.id AS account_id, a.name AS account_name, a.root_id AS root_id,
                               l.date AS date, COALESCE(SUM(debit - credit), 0) AS balance
                        FROM account_move_line AS l
                        LEFT JOIN account_account AS a ON l.account_id = a.id
                        WHERE l.account_id = %s AND l.date >= %s AND l.date <= %s
                        GROUP BY a.id, a.name, a.root_id, l.date
                    """
                    self.env.cr.execute(query, (selected_account_id, start_date, end_date))

                results = self.env.cr.dictfetchall()
        except ValidationError as e:
            # Handle validation error
            main_error_message = e.args[0]
            print("Validation Error:", main_error_message)
        except Exception as e:
            # Handle other exceptions
            error_message = str(e)
            print("Error:", error_message)

        return results
    @api.model
    def get_all_accounts(self):
        accounts = self.env['account.account'].search([])

        account_ids = [str(account.id) for account in accounts]

        return account_ids

