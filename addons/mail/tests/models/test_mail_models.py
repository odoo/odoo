# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailTestSimple(models.Model):
    """ A very simple model only inheriting from mail.thread when only
    communication history is necessary. """
    _description = 'Simple Chatter Model'
    _name = 'mail.test.simple'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()


class MailTestStandard(models.Model):
    """ This model can be used in tests when automatic subscription and simple
    tracking is necessary. Most features are present in a simple way. """
    _description = 'Standard Chatter Model'
    _name = 'mail.test.track'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()
    user_id = fields.Many2one('res.users', 'Responsible', track_visibility='onchange')
    umbrella_id = fields.Many2one('mail.test', track_visibility='onchange')


class MailTestActivity(models.Model):
    """ This model can be used to test activities in addition to simple chatter
    features. """
    _description = 'Activity Model'
    _name = 'mail.test.activity'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    email_from = fields.Char()


class MailTestFull(models.Model):
    """ This model can be used in tests when complex chatter features are
    required like modeling tasks or tickets. """
    _description = 'Full Chatter Model'
    _name = 'mail.test.full'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char(track_visibility='always')
    count = fields.Integer(default=1)
    datetime = fields.Datetime(default=fields.Datetime.now)
    mail_template = fields.Many2one('mail.template', 'Template')
    customer_id = fields.Many2one('res.partner', 'Customer', track_visibility='onchange')
    user_id = fields.Many2one('res.users', 'Responsible', track_visibility='onchange')
    umbrella_id = fields.Many2one('mail.test', track_visibility='onchange')

    def _track_template(self, tracking):
        res = super(MailTestFull, self)._track_template(tracking)
        record = self[0]
        changes, tracking_value_ids = tracking[record.id]
        if 'customer_id' in changes and record.mail_template:
            res['customer_id'] = (record.mail_template, {'composition_mode': 'mass_mail'})
        elif 'datetime' in changes:
            res['datetime'] = ('mail.track_template', {'composition_mode': 'mass_mail'})
        return res

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'umbrella_id' in init_values and self.umbrella_id:
            return 'mail.track_subtype_umbrella'
        return super(MailTestFull, self)._track_subtype(init_values)


class MailTestAlias(models.Model):
    """ This model can be used in tests when umbrella records like projects
    or teams are required. """
    _description = 'Alias Chatter Model'
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
        res = super(MailTestAlias, self).get_alias_values()
        res['alias_force_thread_id'] = self.id
        res['alias_parent_thread_id'] = self.id
        return res
