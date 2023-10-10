from odoo import models, fields, api


class AccountBalance(models.Model):
    _inherit = 'account.account'

    @api.model
    def getbalance(self, target_date_start, target_date_end, selected_account_id):
        # Initialize a list to store the results as dictionaries
        results = []

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
            """, (selected_account.id, target_date_start, target_date_end))

            results += self.env.cr.dictfetchall()

        return results
    @api.model
    def get_all_accounts(self):
        accounts = self.env['account.account'].search([])

        account_ids = []
        for account in accounts:
            account_ids.append(account.id)

        return account_ids
