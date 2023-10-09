from odoo import api, fields, models

class AccountBalance(models.Model):
    _inherit = 'account.account'

    @api.model
    def getbalance(self, target_date_start, target_date_end):
        # Initialize a list to store the results as dictionaries
        results = []

        # Retrieve all accounts
        accounts = self.env['account.account'].search([])

        for account in accounts:
            # Calculate the balance for the account within the date range
            self.env.cr.execute("""
                SELECT a.id AS account_id, a.name AS account_name, a.root_id AS root_id,
                       l.date AS date, COALESCE(SUM(debit - credit), 0) AS balance
                FROM account_move_line AS l
                LEFT JOIN account_account AS a ON l.account_id = a.id
                WHERE l.account_id = %s AND l.date >= %s AND l.date <= %s
                GROUP BY a.id, a.name, a.root_id, l.date
            """, (account.id, target_date_start, target_date_end))

            results += self.env.cr.dictfetchall()

        return results