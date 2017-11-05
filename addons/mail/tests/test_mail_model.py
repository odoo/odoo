# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailTestSimple(models.Model):
    _description = 'Test Simple Chatter Record'
    _name = 'mail.test.simple'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()
    description = fields.Text()


class MailTest(models.Model):
    _description = 'Test Mail Model'
    _name = 'mail.test'
    _mail_post_access = 'read'
    _inherit = ['mail.thread', 'mail.alias.mixin']

    name = fields.Char()
    description = fields.Text()
    alias_id = fields.Many2one(
        'mail.alias', 'Alias',
        delegate=True)

    def get_alias_model_name(self, vals):
        return vals.get('alias_model', 'mail.test')

    def get_alias_values(self):
        self.ensure_one()
        res = super(MailTest, self).get_alias_values()
        res['alias_force_thread_id'] = self.id
        res['alias_parent_thread_id'] = self.id
        return res
