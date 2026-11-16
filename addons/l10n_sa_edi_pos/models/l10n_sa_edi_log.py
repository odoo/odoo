from odoo import models
from odoo.exceptions import UserError


class L10nSaEdiLog(models.Model):
    _inherit = 'l10n_sa_edi.log'

    def action_retry(self):
        self.ensure_one()
        invoice = self.l10n_sa_edi_document_id.resource
        if not invoice.pos_order_ids:
            return super().action_retry()

        alerts = invoice._l10n_sa_get_alerts()
        if alerts:
            messages = [alert['message'] for alert in alerts.values()]
            raise UserError('\n'.join(messages))
        if not invoice._l10n_sa_is_phase_2_applicable():
            raise UserError(self.env._(
                'ZATCA Phase 2 configuration is incomplete for this POS invoice. '
                'Please recheck the ZATCA configurations.',
            ))

        return invoice.l10n_sa_edi_document_id._l10n_sa_post_zatca_edi(False)
