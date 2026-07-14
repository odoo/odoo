from odoo import api, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    @api.depends('move_ids.l10n_ro_edi_state', 'enable_ubl_cii_xml')
    def _compute_l10n_ro_edi_send_enable(self):
        # Override to enable the sending to SPV if the invoice does not have an index,
        # i.e, it has not yet been sent
        super()._compute_l10n_ro_edi_send_enable()
        for wizard in self:
            wizard.l10n_ro_edi_send_enable &= not any(
                move.l10n_ro_edi_index
                for move in wizard.move_ids
            )
