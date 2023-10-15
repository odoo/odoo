from odoo import models, api
from odoo.exceptions import ValidationError

class AccountBalance(models.Model):
    _inherit = 'account.account'

    @api.model
    def get_all_accounts(self):
        accounts = self.env['account.account'].search([])

        account_ids = [str(account.id) for account in accounts]

        return account_ids

    @api.model
    def getbalance(self, start_date, end_date, selected_account_id):
        results = []

        try:
            # Convert the selected account ID to an integer
            selected_account_id = int(selected_account_id)

            # Retrieve the selected account based on the provided account ID
            selected_account = self.env['account.account'].browse(selected_account_id)

            if selected_account:
                query_params = [selected_account_id, end_date]

                query = """
                          SELECT a.id AS account_id, a.name AS account_name, a.root_id AS root_id,
                                 l.date AS date, COALESCE(SUM(debit - credit), 0) AS balance
                          FROM account_move_line AS l
                          LEFT JOIN account_account AS a ON l.account_id = a.id
                          WHERE l.account_id = %s AND l.date <= %s
                      """

                # Check if start_date is not provided or is an empty string
                if not start_date or start_date == "":
                    pass  # Start date is not provided; no need to add it to the query
                else:
                    query += " AND l.date >= %s"
                    query_params.append(start_date)

                query += " GROUP BY a.id, a.name, a.root_id, l.date"

                self.env.cr.execute(query, query_params)
                results = self.env.cr.dictfetchall()
        except ValueError as e:
            # Handle conversion error
            error_message = "Error converting selected_account_id to an integer: " + str(e)
            print("Error:", error_message)
        except Exception as e:
            # Handle other exceptions
            error_message = str(e)
            print("Error:", error_message)

        return results

    @api.model
    def ledger_debit_credit(self, target_date_start, target_date_end, selected_account_id):
        # Initialize a list to store the results as dictionaries
        results = []

        # Retrieve the selected account based on the provided account ID
        selected_account_id = int(selected_account_id)
        selected_account = self.env['account.account'].browse(selected_account_id)

        if selected_account:
            query_params = [selected_account.id, target_date_end]

            query = """
                        SELECT a.id AS account_id, a.name AS account_name, a.root_id AS root_id,
                               l.date AS date, 
                               COALESCE(SUM(debit), 0) AS debit, 
                               COALESCE(SUM(credit), 0) AS credit, 
                               COALESCE(SUM(debit - credit), 0) AS balance
                        FROM account_move_line AS l
                        LEFT JOIN account_account AS a ON l.account_id = a.id
                        WHERE l.account_id = %s AND l.date <= %s
                        """

            # Check if start_date is provided and not an empty string
            if target_date_start and target_date_start.strip():
                query += " AND l.date >= %s"
                query_params.append(target_date_start)

            query += " GROUP BY a.id, a.name, a.root_id, l.date"

            self.env.cr.execute(query, query_params)
            results += self.env.cr.dictfetchall()

        return results



