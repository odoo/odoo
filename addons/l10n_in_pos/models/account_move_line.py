from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_l10n_in_gstr_section(self):
        super()._compute_l10n_in_gstr_section()

        def has_tags(category):
            return any(tag in tax_tags for tag in tax_tags_ids[category])

        def get_transaction_type(move):
            return 'intra_state' if move.l10n_in_state_id == move.company_id.state_id else 'inter_state'

        def is_b2cs(line):
            return (
                line.move_id.l10n_in_gst_treatment in ('unregistered', 'consumer') and
                has_tags('gst') and
                (get_transaction_type(line.move_id) == 'intra_state' or
                (get_transaction_type(line.move_id) == 'inter_state' and
                    (not line.move_id.reversed_entry_id and line.move_id.amount_total <= 100000) or
                    (line.move_id.reversed_entry_id and line.move_id.reversed_entry_id.amount_total <= 100000)
                ))
            )

        def is_nil_rated(line):
            return (
                line.move_id.l10n_in_gst_treatment not in ('overseas', 'special_economic_zone') and
                has_tags('nil')
            )

        indian_moves_lines = self.filtered(
            lambda l: l.move_id.country_code == 'IN' and
            l.move_id.move_type == 'entry' and
            l.parent_state == 'posted' and
            (l.move_id.pos_session_ids != False or l.move_id.reversed_pos_order_id != False)
            )
        if not indian_moves_lines:
            return

        gstr_mapping_fun = {
            "b2cs": is_b2cs,
            "nil_rated": is_nil_rated
        }

        tax_tags_ids = self.get_l10n_in_tax_tag_ids()

        for line in indian_moves_lines:
            tax_tags = line.tax_tag_ids.ids
            line.l10n_in_gstr_section = next(
            (section for section, function in gstr_mapping_fun.items() if function(line)),
            'out_of_scope'
        )
