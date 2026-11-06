from odoo import _, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    def _compute_extra_edi_checkboxes(self):
        super()._compute_extra_edi_checkboxes()
        for wizard in self:
            checkboxes = wizard.extra_edi_checkboxes or {}
            if 'ro_edi' not in checkboxes and self._is_ro_edi_applicable(wizard.move_id):
                optional_checkbox = {'ro_edi': {'checked': False, 'label': self._get_all_extra_edis()['ro_edi']['label']}}
                wizard.extra_edi_checkboxes = {**checkboxes, **optional_checkbox}
            if 'ro_edi' not in checkboxes and wizard.move_id.l10n_ro_edi_state == 'invoice_sent':
                readonly_checkbox = {'ro_spv': {'checked': False, 'readonly': True, 'label': self._get_all_extra_edis()['ro_edi']['label'], 'question_circle': _("You can't send now. Invoice is waiting for an answer.")}}
                wizard.extra_edi_checkboxes = {**checkboxes, **readonly_checkbox}
