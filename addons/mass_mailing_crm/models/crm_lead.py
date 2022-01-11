# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _mailing_enabled = True

    def action_send_mail_to_leads(self):
        ''' Send emails from mailing.mailing to selected leads if user 
        has mass_mailing rights '''
        action = super(CrmLead, self).action_send_mail_to_leads()
        if self.env.user.has_group('mass_mailing.group_mass_mailing_user'):
            action['context'] = {
                'default_mailing_domain': [('id', 'in', self.env.context['active_ids'])],
                'default_mailing_model_id': self.env['ir.model']._get(self._name).id,
            }
            action['res_model'] = "mailing.mailing"
            action['target'] = 'current'
            action['view_id'] = [self.env.ref('mass_mailing.mailing_mailing_view_form_nomodel').id, 'form']
        return action
