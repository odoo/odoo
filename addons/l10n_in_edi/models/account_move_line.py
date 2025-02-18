from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # E-Invoice Methods
    def _l10n_in_is_global_discount(self):
        self.ensure_one()
        return not self.tax_ids and self.price_subtotal < 0

    def _l10n_in_check_einvoice_validation(self):
        def _group_by_error_code(line):
            error_code = []
            if line.display_type != 'product' or line._l10n_in_is_global_discount():
                return False
            if line._l10n_in_check_invalid_hsn_code():
                error_code.append('invalid_hsn')
            if line.discount < 0:
                error_code.append('restrict_negative_discount_line')
            Move = line.env['account.move']
            all_base_tags = Move._get_l10n_in_gst_tags() + Move._get_l10n_in_non_taxable_tags()
            if (
                not line.tax_tag_ids
                or not any(line_tag_id in all_base_tags for line_tag_id in line.tax_tag_ids.ids)
            ):
                error_code.append('tax_validation')
            return False
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
            for error_code, lines in self.grouped(_group_by_error_code).items()
            if error_code
        }
