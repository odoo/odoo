from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def set_missing_hsn_codes_in_pos_orders(self):
        self.ensure_one()
        PosOrderLine = self.env['pos.order.line']
        base_domain = [
            ('order_id.session_id', '=', self.id),
            ('order_id.account_move', '=', False),
            ('l10n_in_hsn_code', '=', False),
            ('tax_ids', '!=', False),
        ]

        # Lines where product already has HSN
        lines_with_product_hsn = PosOrderLine.search(
            base_domain + [('product_id.l10n_in_hsn_code', '!=', False)]
        )
        for line in lines_with_product_hsn:
            line.l10n_in_hsn_code = line.product_id.l10n_in_hsn_code

        # Lines where product itself is missing HSN
        return PosOrderLine.search(
            base_domain + [('product_id.l10n_in_hsn_code', '=', False)]
        )

    def _prepare_account_move_line_commands_for_reversal(self, order, invoice_to_reverse):
        commands = super()._prepare_account_move_line_commands_for_reversal(order, invoice_to_reverse)
        if not order.config_id.company_id.l10n_in_is_gst_registered:
            return commands

        product_lines = invoice_to_reverse.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )

        for idx, line in enumerate(product_lines):
            command = commands[idx]
            command[2]["l10n_in_hsn_code"] = line.l10n_in_hsn_code
            command[2]["product_uom_id"] = line.product_uom_id.id

        return commands

    def _validate_session_accounting(self):
        super()._validate_session_accounting()
        gst_sessions = self.filtered(
            lambda session: session.company_id.l10n_in_is_gst_registered
            and (session.sales_move_id or session.refunds_move_id),
        )
        if gst_sessions:
            tax_tags_dict = self.env['account.move.line']._get_l10n_in_tax_tag_ids()
            (gst_sessions.sales_move_id | gst_sessions.refunds_move_id).line_ids._set_l10n_in_gstr_section(tax_tags_dict)
