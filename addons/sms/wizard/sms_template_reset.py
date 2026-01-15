# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SmsTemplateReset(models.TransientModel):
    _name = 'sms.template.reset'
    _description = 'SMS Template Reset'

    template_ids = fields.Many2many('sms.template')

    def reset_template(self):
        if not self.template_ids:
            return False
        self.template_ids.reset_template()
        if self.env.context.get('params', {}).get('view_type') == 'list':
            next_action = {'type': 'ir.actions.client', 'tag': 'reload'}
        else:
            next_action = {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _('SMS Templates have been reset'),
                'next': next_action,
            }
        }
