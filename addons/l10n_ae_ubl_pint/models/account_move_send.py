from odoo import models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _l10n_ae_pint_applicable_moves(self, moves, moves_data):
        """ Return the moves about to be sent as PINT AE, whichever transport carries them.

        Other transports add the moves their own send route applies to.
        """
        return moves.filtered(lambda m: moves_data[m]['invoice_edi_format'] == 'pint_ae')

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        ae_moves = self._l10n_ae_pint_applicable_moves(moves, moves_data)
        if not ae_moves:
            return alerts

        alerts.update(ae_moves._l10n_ae_pint_export_check())
        alerts.update(ae_moves.commercial_partner_id._l10n_ae_pint_export_check())
        alerts.update(ae_moves.company_id.partner_id._l10n_ae_pint_export_check())
        alerts.update(ae_moves.invoice_line_ids.product_id._l10n_ae_pint_export_check())
        return alerts
