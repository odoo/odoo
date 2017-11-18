# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _is_fetchmail_server(self):
        return True if self.env['fetchmail.server'].sudo().search([('state', '=', 'done')]) else False
