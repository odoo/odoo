from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _compute_l10n_in_gstr_section(self):
        super()._compute_l10n_in_gstr_section()

        def has_tags(category):
            return any(tag in tax_tags for tag in tax_tags_ids[category])

        def is_b2cs():
            return has_tags('gst')

        def is_nil_rated():
            return has_tags('nil')

        in_pos_closing_and_reversed_lines = self.filtered(
            lambda l: l.move_id.country_code == 'IN' and
            l.move_id.move_type == 'entry' and
            l.parent_state == 'posted' and
            (l.move_id.pos_session_ids != False or l.move_id.reversed_pos_order_id != False)
            )
        if not in_pos_closing_and_reversed_lines:
            return

        gstr_mapping_fun = {
            "b2cs": is_b2cs,
            "nil_rated": is_nil_rated
        }

        tax_tags_ids = self.get_l10n_in_tax_tag_ids()

        for line in in_pos_closing_and_reversed_lines:
            tax_tags = line.tax_tag_ids.ids
            line.l10n_in_gstr_section = next(
            (section for section, function in gstr_mapping_fun.items() if function),
            'out_of_scope'
        )
