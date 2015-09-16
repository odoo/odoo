# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        res = super(MailComposeMessage, self).send_mail()
        if self.env.context.get('active_model') == 'event.registration':
            self.env['event.registration'].browse(self.env.context.get('active_id')).event_id.write({'rescheduled_alert': False})
        return res
