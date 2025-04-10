from odoo import _, api, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    @api.onchange('extra_edi_checkboxes')
    def _onchange_extra_edi_checkboxes(self):
        checkboxes = self.extra_edi_checkboxes or {}
        if 'rs_edi' in checkboxes:
            if checkboxes['rs_edi']['checked']:
                checkboxes['rs_cir_checkbox']['readonly'] = False
            else:
                checkboxes['rs_cir_checkbox']['checked'] = False
                checkboxes['rs_cir_checkbox']['readonly'] = True
            self.extra_edi_checkboxes = {**checkboxes}
