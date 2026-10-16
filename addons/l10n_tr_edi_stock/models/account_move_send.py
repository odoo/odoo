from odoo import models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        tr_edi_moves = moves.filtered(
            lambda m: 'tr_edi' in moves_data[m]['extra_edis'] and m.company_id._l10n_tr_edi_dispatch_enabled(),
        )
        if moves_with_unlinked_dispatches := tr_edi_moves.filtered(lambda m: m._l10n_tr_edi_has_unlinked_dispatches()):
            if earchive_despatch_moves := moves_with_unlinked_dispatches.filtered(lambda m: m._l10n_tr_edi_has_earchive_despatch_moves()):
                alerts['tr_earchive_despatch_moves'] = {
                    'level': 'info',
                    'message': self.env._(
                        "The following invoice(s) will be sent as an e-Dispatch Invoice. "
                        "Please make sure this is correct before sending.",
                    ),
                    'action_text': self.env._("View Invoice(s)"),
                    'action': earchive_despatch_moves._get_records_action(name=self.env._("Check data on Invoice(s)")),
                }
            if other_moves_with_unlinked_dispatches := moves_with_unlinked_dispatches - earchive_despatch_moves:
                alerts['tr_other_moves_with_unlinked_dispatches'] = {
                    'level': 'info',
                    'message': self.env._(
                        "The following invoice(s) have deliveries, but no e-Dispatch Orders are selected. "
                        "Please verify that this information is correct before sending.",
                    ),
                    'action_text': self.env._("View Invoice(s)"),
                    'action': other_moves_with_unlinked_dispatches._get_records_action(name=self.env._("Check data on Invoice(s)")),
                }

        return alerts
