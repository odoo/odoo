from odoo import _, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_alerts(self, moves, moves_data):
        alerts = super()._get_alerts(moves, moves_data)
        tr_nilvera_moves = moves.filtered(lambda m: 'tr_nilvera' in moves_data[m]['extra_edis'])
        # If the invoice is linked to an SO and that SO has e-Dispatch orders, it is required to select the
        # dispatches before sending to Nilvera.
        if moves_with_unlinked_dispatches := tr_nilvera_moves.filtered(lambda m: m._has_unlinked_dispatches()):
            alerts['tr_moves_with_unlinked_dispatches'] = {
                'level': 'danger',
                'message': _(
                    "Please ensure the e-Dispatch Order field has all related orders "
                    "before sending the invoice to Nilvera.",
                ),
                'action_text': _("View Invoice(s)"),
                'action': moves_with_unlinked_dispatches._get_records_action(name=_("Check data on Invoice(s)")),
            }

        return alerts
