# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class HrCandidate(models.Model):
    _inherit = 'hr.candidate'

    def action_send_sms(self):
        return {
            'name': _('Send SMS'),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_mode': 'form',
            'res_model': 'sms.composer',
            'context': {
                'default_composition_mode': 'mass',
                'default_mass_keep_log': True,
                'default_res_ids': self.ids,
            }
        }
