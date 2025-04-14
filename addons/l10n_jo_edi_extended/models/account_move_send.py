from odoo import _, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if self.env.company.l10n_jo_edi_demo_mode:
            alerts['l10n_jo_edi_demo_mode'] = {
                'level': 'info',
                'message': _("Demo mode is enabled."),
            }
        return alerts
