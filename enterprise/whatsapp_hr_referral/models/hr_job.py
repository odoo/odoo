# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class Job(models.Model):
    _inherit = 'hr.job'

    def action_open_whatsapp_composer(self):
        self.ensure_one()
        link_to_share_wizard = self.env['hr.referral.link.to.share'].create({
            'job_id': self.id,
            'channel': 'direct',
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.composer',
            'view_mode': 'form',
            'name': _('Share Job By WhatsApp'),
            'target': 'new',
            'context': {
                'active_id': link_to_share_wizard.id,
                'active_model': link_to_share_wizard._name,
            },
        }
