from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # E-Invoice Methods
    def _l10n_in_is_global_discount(self):
        self.ensure_one()
        return not self.tax_ids and self.price_subtotal < 0

    def _l10n_in_check_einvoice_validation(self):
        _ = self.env._
        error_messages = {
            'invalid_hsn': _(
                "Missing or invalid HSN/SAC code: Ensure that invoice lines contain "
                "4, 6 or 8 digits"
            ),
            'restrict_negative_discount_line': _("Negative discount is not allowed"),
            'tax_validation': _(
                "Set an appropriate GST tax on invoice lines "
                "(if it's zero rated or nil rated then apply it too)"
            ),
        }

        error_lines = {}
        for line in self:
            error_codes = []
            if line.display_type != 'product' or line._l10n_in_is_global_discount():
                continue
            if line._l10n_in_check_invalid_hsn_code():
                error_codes.append('invalid_hsn')
            if line.discount < 0:
                error_codes.append('restrict_negative_discount_line')
            if not any(tax.l10n_in_tax_type in ['gst', 'nil_rated', 'exempt', 'non_gst'] for tax in line.tax_ids.flatten_taxes_hierarchy()):
                error_codes.append('tax_validation')
            for code in error_codes:
                error_lines[code] = error_lines.get(code, self.env['account.move.line']) | line

        return {
            f"l10n_in_edi_{error_code}": {
                'message': error_messages[error_code],
                'action_text': _("View Invoice Lines"),
                # The context are set in view_move_line_tree_hsn_l10n_in
                # Please make sure to change, if any change in error codes
                'action': lines.with_context(**{
                    error_code: True,
                    'send_and_print': True
                })._get_records_action(
                    name=_("Check Invoice Lines"),
                    domain=[('id', 'in', lines.ids)],
                    views=[(
                        self.env.ref('l10n_in.view_move_line_tree_hsn_l10n_in').id,
                        'list'
                    )],
                ),
            }
            for error_code, lines in error_lines.items()
        }
