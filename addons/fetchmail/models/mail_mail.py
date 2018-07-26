# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailMail(models.Model):

    _inherit = "mail.mail"

    fetchmail_server_id = fields.Many2one('fetchmail.server', "Inbound Mail Server", readonly=True, index=True, oldname='server_id')

    @api.preupdate()
    def _preupdate_fetchmail_server_id(self, vals):
        fetchmail_server_id = self.env.context.get('fetchmail_server_id')
        if fetchmail_server_id:
            vals['fetchmail_server_id'] = fetchmail_server_id
