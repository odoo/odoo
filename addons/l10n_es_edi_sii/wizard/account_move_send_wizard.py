# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    @api.depends('move_id')
    def _compute_extra_edi_checkboxes(self):
        super()._compute_extra_edi_checkboxes()
        all_extra_edis = self._get_all_extra_edis()
        for wizard in self:
            wizard.extra_edi_checkboxes = {
                **(wizard.extra_edi_checkboxes or {}),
                **{
                    edi_key: {'checked': False, 'label': all_extra_edis[edi_key]['label'], 'help': all_extra_edis[edi_key].get('help')}
                    for edi_key in ('es_edi_sii', 'es_edi_sii_resend')
                    if all_extra_edis[edi_key]['is_applicable'](wizard.move_id)
                },
            }
