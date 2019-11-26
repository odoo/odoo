# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailTestSimple(models.Model):
    """ A very simple model only inheriting from mail.thread when only
    communication history is necessary. """
    _description = 'Simple Chatter Model'
    _name = 'mail.test.simple'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()


class MailTestGateway(models.Model):
    """ A very simple model only inheriting from mail.thread to test pure mass
    mailing features and base performances. """
    _description = 'Simple Chatter Model for Mail Gateway'
    _name = 'mail.test.gateway'
    _inherit = ['mail.thread.blacklist']
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    custom_field = fields.Char()


class MailTestStandard(models.Model):
    """ This model can be used in tests when automatic subscription and simple
    tracking is necessary. Most features are present in a simple way. """
    _description = 'Standard Chatter Model'
    _name = 'mail.test.track'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True)
    umbrella_id = fields.Many2one('mail.test', tracking=True)
    company_id = fields.Many2one('res.company')


class MailTestActivity(models.Model):
    """ This model can be used to test activities in addition to simple chatter
    features. """
    _description = 'Activity Model'
    _name = 'mail.test.activity'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    email_from = fields.Char()
    active = fields.Boolean(default=True)

    def action_start(self, action_summary):
        return self.activity_schedule(
            'test_mail.mail_act_test_todo',
            summary=action_summary
        )

    def action_close(self, action_feedback):
        self.activity_feedback(['test_mail.mail_act_test_todo'], feedback=action_feedback)


class MailTestFull(models.Model):
    """ This model can be used in tests when complex chatter features are
    required like modeling tasks or tickets. """
    _description = 'Full Chatter Model'
    _name = 'mail.test.full'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char(tracking=True)
    count = fields.Integer(default=1)
    datetime = fields.Datetime(default=fields.Datetime.now)
    mail_template = fields.Many2one('mail.template', 'Template')
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=2)
    user_id = fields.Many2one('res.users', 'Responsible', tracking=1)
    umbrella_id = fields.Many2one('mail.test', tracking=True)

    def _track_template(self, changes):
        res = super(MailTestFull, self)._track_template(changes)
        record = self[0]
        if 'customer_id' in changes and record.mail_template:
            res['customer_id'] = (record.mail_template, {'composition_mode': 'mass_mail'})
        elif 'datetime' in changes:
            res['datetime'] = ('test_mail.mail_test_full_tracking_view', {'composition_mode': 'mass_mail'})
        return res

    def _creation_subtype(self):
        if self.umbrella_id:
            return self.env.ref('test_mail.st_mail_test_full_umbrella_upd')
        return super(MailTestFull, self)._creation_subtype()

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'umbrella_id' in init_values and self.umbrella_id:
            return self.env.ref('test_mail.st_mail_test_full_umbrella_upd')
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
    customer_id = fields.Many2one('res.partner', 'Customer')
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


class MailModel(models.Model):
    _name = 'test_performance.mail'
    _description = 'Test Performance Mail'
    _inherit = 'mail.thread'

    name = fields.Char()
    value = fields.Integer()
    value_pc = fields.Float(compute="_value_pc", store=True)
    track = fields.Char(default='test', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer')

    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value_pc = float(record.value) / 100


class MailCC(models.Model):
    _name = 'mail.test.cc'
    _description = "Test Email CC Thread"
    _inherit = ['mail.thread.cc']

    name = fields.Char()


class MailMultiCompany(models.Model):
    """ This model can be used in multi company tests"""
    _name = 'mail.test.multi.company'
    _description = "Test Multi Company Mail"
    _inherit = 'mail.thread'

    name = fields.Char()
    company_id = fields.Many2one('res.company')


class MailTrackingModel(models.Model):
    _description = 'Test Tracking Model'
    _name = 'mail.test.tracking'
    _inherit = ['mail.thread']

    name = fields.Char(required=True, tracking=True)
    field_0 = fields.Char(tracking=True)
    field_1 = fields.Char(tracking=True)
    field_2 = fields.Char(tracking=True)


class MailCompute(models.Model):
    _name = 'mail.test.compute'
    _description = "Test model with several tracked computed fields"
    _inherit = ['mail.thread']

    partner_id = fields.Many2one('res.partner', tracking=True)
    partner_name = fields.Char(related='partner_id.name', store=True, tracking=True)
    partner_email = fields.Char(related='partner_id.email', store=True, tracking=True)
    partner_phone = fields.Char(related='partner_id.phone', tracking=True)
