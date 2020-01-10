from odoo import api, fields, models

class ResBank(models.Model):
    _inherit = 'res.bank'

    clearing_number = fields.Char(string='Clearing Number', help='Swedish Bank Clearing Number, 4 digits.')
    account_digits = fields.Integer(string='Account Numbers', help='Swedish Bank Account numbers.', default=0)
    account_padding = fields.Boolean(string='Account Padding', help='Swedish Bank Account Padding with 0 in front of account number.', default=False)

    @api.model
    def get_bank_id_from_clearing(self, clearing):
        if clearing:
            query = """
                SELECT id 
                FROM 
                    (SELECT id, split_part(unnest(string_to_array(RTRIM(LTRIM(clearing_number, '[('), ')]'), '), (')), ', ', 1) AS part_a, 
                        split_part(unnest(string_to_array(RTRIM(LTRIM(clearing_number, '[('), ')]'), '), (')), ', ', 2) AS part_b 
                    FROM res_bank) AS cno 
                WHERE %s BETWEEN part_a AND part_b;
            """
            self._cr.execute(query, [clearing])

            return self._cr.fetchone() 

        return False
