from odoo import api, models, _


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------
    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if snailmail_moves_without_valid_address := moves.filtered(
            lambda m: 'snailmail' in moves_data[m]['sending_methods'] and not self.env['snailmail.letter']._is_valid_address(m.partner_id)
        ):
            alerts['snailmail_account_partner_invalid_address'] = {
                'level': 'danger' if len(snailmail_moves_without_valid_address) == 1 else 'warning',
                'message': _(
                    "The partners on the following invoices have no valid address, "
                    "so those invoices will not be sent: %s",
                    ", ".join(snailmail_moves_without_valid_address.mapped('name'))
                ),
                'action_text': _("View Invoice(s)"),
                'action': snailmail_moves_without_valid_address._get_records_action(name=_("Check Invoice(s)")),
            }
        return alerts

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------
    @api.model
    def _prepare_snailmail_letter_values(self, move):
        return {
            'partner_id': move.partner_id.id,
            'model': 'account.move',
            'res_id': move.id,
            'company_id': move.company_id.id,
            'report_template': self.env['ir.actions.report']._get_report('account.account_invoices').id
        }

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------
    def _is_applicable_to_move(self, method, move):
        # EXTENDS 'account'
        if method == 'snailmail':
            return self.env['snailmail.letter']._is_valid_address(move.partner_id)
        else:
            return super()._is_applicable_to_move(method, move)

    def _hook_if_success(self, moves_data):
        # EXTENDS 'account'
        super()._hook_if_success(moves_data)

        to_send = {
            move: move_data
            for move, move_data in moves_data.items()
            if 'snailmail' in move_data['sending_methods'] and self._is_applicable_to_move('snailmail', move)
        }
        if to_send:
            self.env['snailmail.letter'].create([
                {
                    'user_id': move_data.get('author_user_id') or self.env.user.id,
                    **self._prepare_snailmail_letter_values(move),
                }
                for move, move_data in to_send.items()
            ])\
            ._snailmail_print(immediate=False)
