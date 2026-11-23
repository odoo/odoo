from odoo import models
from odoo.exceptions import LockError, UserError


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
            ('company_id.l10n_in_disable_b2c_hsn_reporting', '=', False)
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

    def _prepare_account_move_line_commands_for_reversal(self, order, original_move):
        commands = super()._prepare_account_move_line_commands_for_reversal(order, original_move)
        if not order.config_id.company_id.l10n_in_gst_registration_type:
            return commands

        # The commands are rebuilt from the order, match them with the
        # closing entry line they reverse using the same grouping.
        product_lines = original_move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        for command in commands:
            vals = command[2]
            line = product_lines.filtered(
                lambda line, vals=vals: line.account_id.id == vals['account_id']
                and line.product_id.id == (vals.get('product_id') or False)
                and set(line.tax_ids.ids) == set(vals['tax_ids'][0][2]),
            )[:1]
            if line:
                vals["l10n_in_hsn_code"] = line.l10n_in_hsn_code
                vals["product_uom_id"] = line.product_uom_id.id

        return commands

    def _validate_session_accounting(self):
        if self.company_id.country_code == 'IN':
            # Account for individual orders before cash differences are calculated.
            # This method is shared by manual, automatic and periodic closing.
            try:
                # Other transactions may still reference the session meanwhile, e.g. the
                # payments of the orders invoiced by the cron or of the synced orders.
                self.lock_for_update(allow_referencing=True)
            except LockError:
                raise UserError(self.env._('This session is being updated by another process. Please try again in a few minutes.')) from None
            orders = self.order_ids.filtered_domain(
                self.env['pos.order']._l10n_in_get_b2c_orders_to_invoice_domain(),
            ).sorted('id')
            if busy_orders := orders - orders.try_lock_for_update():
                raise UserError(self.env._(
                    'The session cannot be closed yet because the following orders are being invoiced by another process, such as the scheduled action. Please try again in a few minutes.\n%s',
                    '\n'.join(busy_orders.mapped('name')),
                ))
            failed_orders = []
            for order in orders:
                if error := order._l10n_in_try_generate_b2c_invoice():
                    failed_orders.append(f'{order.name} ({order.l10n_in_b2c_invoice_number}): {error}')
            if failed_orders:
                raise UserError(self.env._(
                    'The session cannot be closed because the invoice of the following orders could not be created:\n%s',
                    '\n'.join(failed_orders),
                ))
        super()._validate_session_accounting()
        gst_sessions = self.filtered(
            lambda session: session.company_id.l10n_in_gst_registration_type
            and (session.sale_move_ids or session.refund_move_ids),
        )
        if gst_sessions:
            tax_tags_dict = self.env['account.move.line']._get_l10n_in_tax_tag_ids()
            (gst_sessions.sale_move_ids | gst_sessions.refund_move_ids).line_ids._set_l10n_in_gstr_section(tax_tags_dict)
