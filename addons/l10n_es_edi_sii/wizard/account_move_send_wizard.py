# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    @api.depends('move_id')
    def _compute_extra_edi_checkboxes(self):
        super()._compute_extra_edi_checkboxes()

        for wizard in self:
            if wizard.extra_edi_checkboxes and 'es_edi_sii_resend' in wizard.extra_edi_checkboxes:
                checkboxes = dict(wizard.extra_edi_checkboxes)
                checkboxes['es_edi_sii_resend']['checked'] = False
                wizard.extra_edi_checkboxes = checkboxes
