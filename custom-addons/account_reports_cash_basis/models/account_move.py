from odoo import fields, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    impacting_cash_basis = fields.Boolean(store=False, search='_search_impacting_cash_basis')

    def _search_impacting_cash_basis(self, operator, value):
        """
        Searches moves that impact the cash basis:
            - Move with cash or bank journals
            - Move without any receivable or payable line
            - Move with a receivable or payable line and a partial is associated, specifically with a receivable or payable line
        """

        query = """
            WITH moves_with_receivable_payable AS (
                SELECT DISTINCT aml.move_id as id
                FROM account_move_line aml
                JOIN account_account account ON aml.account_id = account.id
                WHERE account.account_type IN ('asset_receivable', 'liability_payable')
            ), 
            reconciled_move_on_receivable_payable AS (
                SELECT DISTINCT aml.move_id as id
                FROM account_partial_reconcile part
                JOIN account_move_line aml ON aml.id = part.debit_move_id OR aml.id = part.credit_move_id
                JOIN account_account account ON aml.account_id = account.id
                WHERE account.account_type IN ('asset_receivable', 'liability_payable')
            )
            SELECT DISTINCT move.id
            FROM account_move move
            LEFT JOIN account_journal journal ON journal.id = move.journal_id
            LEFT JOIN moves_with_receivable_payable move_rp on move_rp.id = move.id
            LEFT JOIN reconciled_move_on_receivable_payable rec_move on rec_move.id = move.id
            WHERE
                journal.type IN ('cash', 'bank')
                OR
                move_rp.id IS NULL
                OR 
                rec_move.id IS NOT NULL
        """

        # op is 'inselect' if (impacting_cash_basis, '=', True) or (impacting_cash_basis, '!=', False), 'not inselect' otherwise
        op = 'inselect' if (operator == '=') ^ (value is False) else 'not inselect'
        return [('id', op, (query, {}))]
