# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models, _
from odoo.tools import email_normalize


class MailTestSimple(models.Model):
    """ A very simple model only inheriting from mail.thread when only
    communication history is necessary. """
    _description = 'Simple Chatter Model'
    _name = 'mail.test.simple'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()

    def _message_compute_subject(self):
        """ To ease mocks """
        _a = super()._message_compute_subject()
        return _a

    def _notify_by_email_get_final_mail_values(self, *args, **kwargs):
        """ To ease mocks """
        _a = super()._notify_by_email_get_final_mail_values(*args, **kwargs)
        return _a

    def _notify_by_email_get_headers(self, headers=None):
        headers = super()._notify_by_email_get_headers(headers=headers)
        headers['X-Custom'] = 'Done'
        return headers


class MailTestSimpleWithMainAttachment(models.Model):
    _description = 'Simple Chatter Model With Main Attachment Management'
    _name = 'mail.test.simple.main.attachment'
    _inherit = ['mail.test.simple', 'mail.thread.main.attachment']


class MailTestSimpleUnfollow(models.Model):
    """ A very simple model only inheriting from mail.thread when only
    communication history is necessary with unfollow link enabled in
    notification emails even for non-internal user. """
    _description = 'Simple Chatter Model'
    _name = 'mail.test.simple.unfollow'
    _inherit = ['mail.thread']
    _partner_unfollow_enabled = True

    name = fields.Char()
    company_id = fields.Many2one('res.company')
    email_from = fields.Char()


class MailTestAliasOptional(models.Model):
    """ A chatter model inheriting from the alias mixin using optional alias_id
    field, hence no inherits. """
    _description = 'Chatter Model using Optional Alias Mixin'
    _name = 'mail.test.alias.optional'
    _inherit = ['mail.alias.mixin.optional']

    name = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    email_from = fields.Char()

    def _alias_get_creation_values(self):
        """ Updates itself """
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get_id('mail.test.alias.optional')
        if self.id:
            values['alias_force_thread_id'] = self.id
            values['alias_defaults'] = {'company_id': self.company_id.id}
        return values


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

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Check override of 'message_new' allowing to update record values
        base on incoming email. """
        defaults = {
            'email_from': msg_dict.get('from'),
        }
        defaults.update(custom_values or {})
        return super().message_new(msg_dict, custom_values=defaults)


class MailTestGatewayCompany(models.Model):
    """ A very simple model only inheriting from mail.thread to test pure mass
    mailing features and base performances, with a company field. """
    _description = 'Simple Chatter Model for Mail Gateway with company'
    _name = 'mail.test.gateway.company'
    _inherit = ['mail.test.gateway']

    company_id = fields.Many2one('res.company', 'Company')


class MailTestGatewayMainAttachment(models.Model):
    """ A very simple model only inheriting from mail.thread to test pure mass
    mailing features and base performances, with a company field and main
    attachment management. """
    _description = 'Simple Chatter Model for Mail Gateway with company'
    _name = 'mail.test.gateway.main.attachment'
    _inherit = ['mail.test.gateway', 'mail.thread.main.attachment']

    company_id = fields.Many2one('res.company', 'Company')


class MailTestGatewayGroups(models.Model):
    """ A model looking like discussion channels / groups (flat thread and
    alias). Used notably for advanced gatewxay tests. """
    _description = 'Channel/Group-like Chatter Model for Mail Gateway'
    _name = 'mail.test.gateway.groups'
    _inherit = ['mail.thread.blacklist', 'mail.alias.mixin']
    _mail_flat_thread = False
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    custom_field = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')

    def _alias_get_creation_values(self):
        values = super(MailTestGatewayGroups, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('mail.test.gateway.groups').id
        if self.id:
            values['alias_force_thread_id'] = self.id
            values['alias_parent_thread_id'] = self.id
        return values

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']

    def _message_get_default_recipients(self):
        return dict(
            (record.id, {
                'email_cc': False,
                'email_to': record.email_from if not record.customer_id.ids else False,
                'partner_ids': record.customer_id.ids,
            })
            for record in self
        )


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
    track_fields_tofilter = fields.Char()  # comma-separated list of field names
    track_enable_default_log = fields.Boolean(default=False)

    def _track_filter_for_display(self, tracking_values):
        values = super()._track_filter_for_display(tracking_values)
        filtered_fields = set(self.track_fields_tofilter.split(',') if self.track_fields_tofilter else '')
        return values.filtered(lambda val: val.field_id.name not in filtered_fields)

    def _track_get_default_log_message(self, changes):
        filtered_fields = set(self.track_fields_tofilter.split(',') if self.track_fields_tofilter else '')
        if self.track_enable_default_log and not all(change in filtered_fields for change in changes):
            return f'There was a change on {self.name} for fields "{",".join(changes)}"'
        return super()._track_get_default_log_message(changes)

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

    def action_close(self, action_feedback, attachment_ids=None):
        self.activity_feedback(['test_mail.mail_act_test_todo'],
                               feedback=action_feedback,
                               attachment_ids=attachment_ids)


class MailTestTicket(models.Model):
    """ This model can be used in tests when complex chatter features are
    required like modeling tasks or tickets. """
    _description = 'Ticket-like model'
    _name = 'mail.test.ticket'
    _inherit = ['mail.thread']
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char(tracking=True)
    mobile_number = fields.Char()
    phone_number = fields.Char()
    count = fields.Integer(default=1)
    datetime = fields.Datetime(default=fields.Datetime.now)
    mail_template = fields.Many2one('mail.template', 'Template')
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=2)
    user_id = fields.Many2one('res.users', 'Responsible', tracking=1)
    container_id = fields.Many2one('mail.test.container', tracking=True)

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']

    def _message_compute_subject(self):
        self.ensure_one()
        return f"Ticket for {self.name} on {self.datetime.strftime('%m/%d/%Y, %H:%M:%S')}"

    def _message_get_default_recipients(self):
        return dict(
            (record.id, {
                'email_cc': False,
                'email_to': record.email_from if not record.customer_id.ids else False,
                'partner_ids': record.customer_id.ids,
            })
            for record in self
        )

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """ Activate more groups to test query counters notably (and be backward
        compatible for tests). """
        local_msg_vals = dict(msg_vals or {})
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        for group_name, _group_method, group_data in groups:
            if group_name == 'portal':
                group_data['active'] = True
            elif group_name == 'customer':
                group_data['active'] = True
                group_data['has_button_access'] = True
                group_data['actions'] = [{
                    'url': self._notify_get_action_link(
                        'controller',
                        controller='/test_mail/do_stuff',
                        **local_msg_vals
                    ),
                    'title': _('NotificationButtonTitle')
                }]

        return groups

    def _track_template(self, changes):
        res = super(MailTestTicket, self)._track_template(changes)
        record = self[0]
        if 'customer_id' in changes and record.mail_template:
            res['customer_id'] = (
                record.mail_template,
                {
                    'composition_mode': 'mass_mail',
                    'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                }
            )
        elif 'datetime' in changes:
            res['datetime'] = (
                'test_mail.mail_test_ticket_tracking_view',
                {
                    'composition_mode': 'mass_mail',
                    'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                }
            )
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

    def _get_customer_information(self):
        email_normalized_to_values = super()._get_customer_information()

        for record in self.filtered('email_from'):
            email_from_normalized = email_normalize(record.email_from)
            if not email_from_normalized:  # do not fill Falsy with random data
                continue
            values = email_normalized_to_values.setdefault(email_from_normalized, {})
            if not values.get('mobile'):
                values['mobile'] = record.mobile_number
            if not values.get('phone'):
                values['phone'] = record.phone_number
        return email_normalized_to_values

    def _message_get_suggested_recipients(self):
        recipients = super()._message_get_suggested_recipients()
        if self.customer_id:
            self.customer_id._message_add_suggested_recipient(
                recipients,
                partner=self.customer_id,
                lang=None,
                reason=_('Customer'),
            )
        elif self.email_from:
            self._message_add_suggested_recipient(
                recipients,
                partner=None,
                email=self.email_from,
                lang=None,
                reason=_('Customer Email'),
            )
        return recipients


class MailTestTicketEL(models.Model):
    """ Just mail.test.ticket, but exclusion-list enabled. Kept as different
    model to avoid messing with existing tests, notably performance, and ease
    backward comparison. """
    _description = 'Ticket-like model with exclusion list'
    _name = 'mail.test.ticket.el'
    _inherit = [
        'mail.test.ticket',
        'mail.thread.blacklist',
    ]
    _primary_email = 'email_from'

    email_from = fields.Char(
        'Email',
        compute='_compute_email_from', readonly=False, store=True)

    @api.depends('customer_id')
    def _compute_email_from(self):
        for ticket in self.filtered(lambda r: r.customer_id and not r.email_from):
            ticket.email_from = ticket.customer_id.email_formatted


class MailTestTicketMC(models.Model):
    """ Just mail.test.ticket, but multi company. Kept as different model to
    avoid messing with existing tests, notably performance, and ease backward
    comparison. """
    _description = 'Ticket-like model'
    _name = 'mail.test.ticket.mc'
    _inherit = ['mail.test.ticket']
    _primary_email = 'email_from'

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    container_id = fields.Many2one('mail.test.container.mc', tracking=True)

    def _notify_get_reply_to(self, default=None):
        # Override to use alias of the parent container
        aliases = self.sudo().mapped('container_id')._notify_get_reply_to(default=default)
        res = {task.id: aliases.get(task.container_id.id) for task in self}
        leftover = self.filtered(lambda rec: not rec.container_id)
        if leftover:
            res.update(super(MailTestTicketMC, leftover)._notify_get_reply_to(default=default))
        return res


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

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']

    def _message_get_default_recipients(self):
        return dict(
            (record.id, {
                'email_cc': False,
                'email_to': False,
                'partner_ids': record.customer_id.ids,
            })
            for record in self
        )

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """ Activate more groups to test query counters notably (and be backward
        compatible for tests). """
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        for group_name, _group_method, group_data in groups:
            if group_name == 'portal':
                group_data['active'] = True

        return groups

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('mail.test.ticket').id
        values['alias_force_thread_id'] = False
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['container_id'] = self.id
        return values


class MailTestContainerMC(models.Model):
    """ Just mail.test.container, but multi company. Kept as different model to
    avoid messing with existing tests, notably performance, and ease backward
    comparison. """
    _description = 'Project-like model with alias (MC)'
    _name = 'mail.test.container.mc'
    _mail_post_access = 'read'
    _inherit = ['mail.test.container']

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('mail.test.ticket.mc').id
        return values


class MailTestComposerMixin(models.Model):
    """ A simple invite-like wizard using the composer mixin, rendering on
    composer source test model. Purpose is to have a minimal composer which
    runs on other records and check notably dynamic template support and
    translations. """
    _description = 'Invite-like Wizard'
    _name = 'mail.test.composer.mixin'
    _inherit = ['mail.composer.mixin']

    name = fields.Char('Name')
    author_id = fields.Many2one('res.partner')
    description = fields.Html('Description', render_engine="qweb", render_options={"post_process": True}, sanitize='email_outgoing')
    source_ids = fields.Many2many('mail.test.composer.source', string='Invite source')

    def _compute_render_model(self):
        self.render_model = 'mail.test.composer.source'


class MailTestComposerSource(models.Model):
    """ A simple model on which invites are sent. """
    _description = 'Invite-like Source'
    _name = 'mail.test.composer.source'
    _inherit = ['mail.thread.blacklist']
    _primary_email = 'email_from'

    name = fields.Char('Name')
    customer_id = fields.Many2one('res.partner', 'Main customer')
    email_from = fields.Char(
        'Email',
        compute='_compute_email_from', readonly=False, store=True)

    @api.depends('customer_id')
    def _compute_email_from(self):
        for source in self.filtered(lambda r: r.customer_id and not r.email_from):
            source.email_from = source.customer_id.email_formatted

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']


class MailTestMailTrackingDuration(models.Model):
    _description = 'Fake model to test the mixin mail.tracking.duration.mixin'
    _name = 'mail.test.mail.tracking.duration'
    _track_duration_field = 'customer_id'
    _inherit = ['mail.thread', 'mail.tracking.duration.mixin']

    name = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=True)

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']


class MailTestPublicThread(models.Model):
    """A model inheriting from mail.thread with public read and write access
    to test some public and guest interactions."""

    _description = "Portal Public Thread"
    _name = "mail.test.public"
    _inherit = ["mail.thread"]

    name = fields.Char("Name")
