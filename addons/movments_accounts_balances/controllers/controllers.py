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
                if start_date and start_date != "":
                    query += " AND l.date >= %s"
                    query_params.append(start_date)

                query += " GROUP BY a.id, a.name, a.root_id, l.date"
                query += " ORDER BY l.date DESC"  # Order results by date in descending order

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
    def general_ledger_report(self, account_id, start_date, end_date):
        # Define search criteria to filter account move lines
        domain = [
            ('account_id', '=', account_id),
        ]

        if start_date and end_date:
            domain.extend([
                ('date', '>=', start_date),
                ('date', '<=', end_date)
            ])
        # else:
        # domain.append(('date', '<=', end_date))

        # Retrieve account move lines based on the criteria
        move_lines = self.env['account.move.line'].search(domain)

        # Prepare a list to store ledger data
        ledger_data = []

        # Iterate through the retrieved move lines and assemble ledger data
        for line in move_lines:
            ledger_data.append({
                'date': line.date,
                'debit': line.debit,
                'credit': line.credit,
                'balance': line.balance,
                'account_root_id': line.account_root_id.id

            })

        # Retrieve account information for the specified account_id
        account_info = self.env['account.account'].browse(account_id)

        # Create a dictionary to combine account information and ledger data
        general_ledger = {
            'account_info': {
                'id': account_info.id,
                'name': account_info.name,
                # You can add more account details here as needed
            },
            'ledger_data': ledger_data,
        }

        # Return the general ledger data
        return general_ledger



