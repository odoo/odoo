# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailTest(models.Model):
    """ A mail.channel is a discussion group that may behave like a listener
    on documents. """
    _description = 'Test Mail Model'
    _name = 'mail.test'
    _mail_post_access = 'read'
    # _mail_flat_thread = False
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
