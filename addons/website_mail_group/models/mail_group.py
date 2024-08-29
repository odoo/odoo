# -*- coding: utf-8 -*-
from odoo.addons import mail_group
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailGroup(models.Model, mail_group.MailGroup):

    def action_go_to_website(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/groups/%s' % self.env['ir.http']._slug(self),
        }
