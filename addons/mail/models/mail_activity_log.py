# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from datetime import timedelta

class MailActivityLog(models.Model):
    _name = 'mail.activity.log'
    _description = 'Set of emails sent and linked to an activity'
    mail_message_id = fields.Many2one('mail.message', store=True)

    @api.autovacuum
    def _gc_outdated_logs(self):
        self.env['mail.activity.log'].search([
            ('create_date', '<', fields.Datetime.now() - timedelta(hours=2))
        ]).unlink()
