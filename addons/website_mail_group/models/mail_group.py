# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.http_routing.models.ir_http import slug


class MailGroup(models.Model):
    _name = 'mail.group'
    _inherit = 'mail.group'

    def action_go_to_website(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/groups/%s' % slug(self),
        }
