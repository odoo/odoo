from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        ae_moves = moves.filtered(lambda m: moves_data[m]['invoice_edi_format'] == 'pint_ae')
        alerts.update(ae_moves.commercial_partner_id._l10n_ae_ubl_pint_export_check())
        alerts.update(ae_moves.company_id.partner_id._l10n_ae_ubl_pint_export_check())
        alerts.update(ae_moves._l10n_ae_ubl_pint_export_check())
        alerts.update(ae_moves.invoice_line_ids.product_id._l10n_ae_ubl_pint_export_check())
        return alerts
