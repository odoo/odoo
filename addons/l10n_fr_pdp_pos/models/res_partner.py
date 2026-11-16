# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_pos_check_peppol_endpoint(self):
        super().action_pos_check_peppol_endpoint()
        states = dict(self._fields['pdp_verification_display_state']._description_selection(self.env))
        state = self.pdp_verification_display_state
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': states.get(state, ''),
                'type': 'success' if state in ['peppol_valid', 'pdp_valid'] else 'warning',
            },
        }
