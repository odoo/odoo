# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Partner(models.Model):
    _inherit = 'res.partner'
    _mailing_enabled = True

    def action_send_mail_to_partner(self):
        ''' Send emails from mailing.mailing to selected partners if user 
        has mass_mailing rights '''
        action = super(Partner, self).action_send_mail_to_partner()
        if self.env.user.has_group('mass_mailing.group_mass_mailing_user'):
            action['context'] = {
                'default_mailing_domain': [('id', 'in', self.env.context['active_ids'])],
                'default_mailing_model_id': self.env['ir.model']._get(self._name).id,
                'default_reply_to': '',
                'default_reply_to_mode': 'new',
            }
            action['res_model'] = "mailing.mailing"
            action['target'] = 'current'
            action['view_id'] = [self.env.ref('mass_mailing.mailing_mailing_view_form_nomodel').id, 'form']
        return action
