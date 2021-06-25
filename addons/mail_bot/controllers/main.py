# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers import main
from odoo import http
from odoo.http import request

class MailbotController(main.MailController):
    @http.route()
    def mail_init_messaging(self):
        values = super(MailbotController, self).mail_init_messaging()
        values['odoobot_initialized'] = request.env.user.odoobot_state not in [False, 'not_initialized']
        return values
