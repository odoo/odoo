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
    container_id = fields.Many2one('mail.test.container', tracking=True)
    company_id = fields.Many2one('res.company')

    def _get_share_url(self, redirect, signup_partner, share_token):
        """This function is required for a test on 'mail.mail_notification_paynow' template (test_message_post/test_mail_add_signature),
        another model should be created in master"""
        return '/mail/view'


class MailTestActivity(models.Model):
    """ This model can be used to test activities in addition to simple chatter
    features. """
    _description = 'Activity Model'
    _name = 'mail.test.activity'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    date = fields.Date()
    email_from = fields.Char()
    active = fields.Boolean(default=True)

    def action_start(self, action_summary):
        return self.activity_schedule(
            'test_mail.mail_act_test_todo',
            summary=action_summary
        )

    def action_close(self, action_feedback):
        self.activity_feedback(['test_mail.mail_act_test_todo'], feedback=action_feedback)


class MailTestTicket(models.Model):
    """ This model can be used in tests when complex chatter features are
    required like modeling tasks or tickets. """
    _description = 'Ticket-like model'
    _name = 'mail.test.ticket'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char(tracking=True)
    count = fields.Integer(default=1)
    datetime = fields.Datetime(default=fields.Datetime.now)
    mail_template = fields.Many2one('mail.template', 'Template')
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=2)
    user_id = fields.Many2one('res.users', 'Responsible', tracking=1)
    container_id = fields.Many2one('mail.test.container', tracking=True)

    def _track_template(self, changes):
        res = super(MailTestTicket, self)._track_template(changes)
        record = self[0]
        if 'customer_id' in changes and record.mail_template:
            res['customer_id'] = (record.mail_template, {'composition_mode': 'mass_mail'})
        elif 'datetime' in changes:
            res['datetime'] = ('test_mail.mail_test_ticket_tracking_view', {'composition_mode': 'mass_mail'})
        return res

    def _creation_subtype(self):
        if self.container_id:
            return self.env.ref('test_mail.st_mail_test_ticket_container_upd')
        return super(MailTestTicket, self)._creation_subtype()

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'container_id' in init_values and self.container_id:
            return self.env.ref('test_mail.st_mail_test_ticket_container_upd')
        return super(MailTestTicket, self)._track_subtype(init_values)


class MailTestContainer(models.Model):
    """ This model can be used in tests when container records like projects
    or teams are required. """
    _description = 'Project-like model with alias'
    _name = 'mail.test.container'
    _mail_post_access = 'read'
    _inherit = ['mail.thread', 'mail.alias.mixin']

    name = fields.Char()
    description = fields.Text()
    customer_id = fields.Many2one('res.partner', 'Customer')
    alias_id = fields.Many2one(
        'mail.alias', 'Alias',
        delegate=True)

    def _alias_get_creation_values(self):
        values = super(MailTestContainer, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('mail.test.container').id
        if self.id:
            values['alias_force_thread_id'] = self.id
            values['alias_parent_thread_id'] = self.id
        return values

class MailTestComposerMixin(models.Model):
    """ A simple invite-like wizard using the composer mixin, rendering on
    itself. """
    _description = 'Invite-like Wizard'
    _name = 'mail.test.composer.mixin'
    _inherit = ['mail.composer.mixin']

    name = fields.Char('Name')
    author_id = fields.Many2one('res.partner')
    description = fields.Html('Description', render_engine="qweb", render_options={"post_process": True}, sanitize=False)

    def _compute_render_model(self):
        self.render_model = self._name
