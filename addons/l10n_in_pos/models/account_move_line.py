from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _get_l10n_in_gstr_section(self, tax_tags_dict):
        result = super()._get_l10n_in_gstr_section(tax_tags_dict)

        eco_9_5_tag = tax_tags_dict['eco_9_5']
        all_gst_tags = tax_tags_dict['cgst'] + tax_tags_dict['sgst'] + tax_tags_dict['igst'] + tax_tags_dict['cess']

        def get_section(line):
            tax_tags = line.tax_tag_ids.ids
            if any(tag == eco_9_5_tag for tag in tax_tags):
                return 'sale_eco_9_5'
            if any(tag in tax_tags for tag in all_gst_tags):
                return 'sale_b2cs'
            if any(tax.l10n_in_tax_type == 'nil_rated' for tax in line.tax_ids):
                return 'sale_nil_rated'
            if any(tax.l10n_in_tax_type == 'exempt' for tax in line.tax_ids):
                return 'sale_exempt'
            if any(tax.l10n_in_tax_type == 'non_gst' for tax in line.tax_ids):
                return 'sale_non_gst_supplies'
            return 'sale_out_of_scope'

        in_pos_closing_and_reversed_lines = self.filtered(
            lambda l: l.move_id.country_code == 'IN'
            and l.move_id.move_type == 'entry'
            and l.display_type in ('product', 'tax')
            and (l.move_id.sudo().pos_session_ids or l.move_id.sudo().reversed_pos_order_id)
        )
        if not in_pos_closing_and_reversed_lines:
            return result

        move_lines_by_gstr_section = in_pos_closing_and_reversed_lines.grouped(get_section)

        for section, lines in move_lines_by_gstr_section.items():
            result[section] = result.get(section, self.env['account.move.line']) | lines

        return result
