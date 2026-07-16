from odoo import api, models


class PdpFlow10XMLBuilder(models.AbstractModel):
    _inherit = 'pdp.flow.10.xml.builder'

    @api.model
    def _get_entry_line_price_unit(self, line):
        if line.move_id._l10n_fr_pdp_reports_pos_is_transaction_entry():
            # In 17.0, POS sales are credits and refunds are separate debit lines on the closing move.
            return -line.amount_currency
        return super()._get_entry_line_price_unit(line)

    @api.model
    def _get_tax_summary(
        self, move_lines, buyer=None, seller=None,
        line_validation_function=False, agregation_function=False,
    ):
        pos_entries = move_lines.move_id.filtered(
            lambda move: move._l10n_fr_pdp_reports_pos_is_transaction_entry()
        )
        move_lines = move_lines.filtered(
            lambda line: line.move_id not in pos_entries
            or line.account_id.account_type in ('income', 'income_other')
        )
        return super()._get_tax_summary(
            move_lines,
            buyer=buyer,
            seller=seller,
            line_validation_function=line_validation_function,
            agregation_function=agregation_function,
        )
