from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ge_wht_category_ids = fields.Many2many(related='commercial_partner_id.l10n_ge_wht_category_ids')

    def _reverse_moves(self, default_values_list=None, cancel=False):
        reverse_moves = super()._reverse_moves(default_values_list=default_values_list, cancel=cancel)
        # account._reverse_moves only reverses the balance of an entry: reverse the base the withholding return reads too.
        for line in reverse_moves.filtered('reversed_entry_id.origin_payment_id').line_ids.filtered(lambda line: line.tax_line_id.is_withholding_tax and line.tax_line_id.country_code == 'GE'):
            line.tax_base_amount = -line.tax_base_amount
        return reverse_moves
