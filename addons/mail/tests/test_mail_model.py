# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailTestUmbrella(models.Model):
    """ Generic test model, acting like an umbrella for other test records
    like a project for tasks, or a sales team for sale orders. """
    _description = 'Test Mail Umbrella Model'
    _name = 'mail.test.umbrella'
    _inherit = ['mail.thread', 'mail.alias.mixin']

    name = fields.Char()
    description = fields.Text()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, track_visibility="onchange")
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

    @api.multi
    def _track_template(self, tracking):
        res = super(MailTest, self)._track_template(tracking)
        test_task = self[0]
        changes, tracking_value_ids = tracking[test_task.id]
        if 'user_id' in changes and test_task.user_id:
            res['stage_id'] = ('mail.message_origin_link', {'composition_mode': 'mass_mail', 'values': {'self': test_task}})
        return res

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'user_id' in init_values and self.user_id:
            return 'mail.mt_comment'
        return super(MailTest, self)._track_subtype(init_values)


class MailTest(models.Model):
    """ Generic test model, acting like a subrecord for an umbrella test record
    like a task for a project, or a sale order for a sales team. """
    _description = 'Test Mail Model'
    _name = 'mail.test'
    _mail_post_access = 'read'
    _inherit = ['mail.thread', 'mail.alias.mixin']

    name = fields.Char()
    description = fields.Text()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, track_visibility="onchange")
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

    @api.multi
    def _track_template(self, tracking):
        res = super(MailTest, self)._track_template(tracking)
        test_task = self[0]
        changes, tracking_value_ids = tracking[test_task.id]
        if 'user_id' in changes and test_task.user_id:
            res['stage_id'] = ('mail.message_origin_link', {'composition_mode': 'mass_mail', 'values': {'self': test_task}})
        return res

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'user_id' in init_values and self.user_id:
            return 'mail.mt_comment'
        return super(MailTest, self)._track_subtype(init_values)
