# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_pos_check_peppol_endpoint(self):
        self.button_account_peppol_check_partner_endpoint()
        states = dict(self._fields['peppol_verification_state'].selection)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'message': states.get(self.peppol_verification_state, ''), 'type': 'info'},
        }
