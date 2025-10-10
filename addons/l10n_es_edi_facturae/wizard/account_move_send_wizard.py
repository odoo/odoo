from odoo import models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    def _compute_extra_edi_checkboxes(self):
        super()._compute_extra_edi_checkboxes()
        for wizard in self:
            checkboxes = wizard.extra_edi_checkboxes or {}
            if 'es_facturae' in checkboxes:
                # Set 'checked' status for the 'es_facturae' checkbox
                checkboxes['es_facturae']['checked'] = wizard.move_id._l10n_es_edi_facturae_get_default_enable()
