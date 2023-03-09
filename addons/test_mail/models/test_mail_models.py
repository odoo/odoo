# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

    def _notify_by_email_get_headers(self):
        headers = super()._notify_by_email_get_headers()
        headers['X-Custom'] = 'Done'
        return headers


class MailTestSimpleWithMainAttachment(models.Model):
    _description = 'Simple Chatter Model With Main Attachment Management'
    _name = 'mail.test.simple.main.attachment'
    _inherit = ['mail.test.simple', 'mail.thread.main.attachment']


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

    def _mail_get_partner_fields(self):
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

    def _mail_get_partner_fields(self):
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
        for ticket in self:
            if ticket.customer_id:
                ticket.customer_id._message_add_suggested_recipient(
                    recipients,
                    partner=ticket.customer_id,
                    lang=None,
                    reason=_('Customer'),
                )
            elif ticket.email_from:
                ticket._message_add_suggested_recipient(
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

    def _mail_get_partner_fields(self):
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
        values = super(MailTestContainer, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('mail.test.container').id
        if self.id:
            values['alias_force_thread_id'] = self.id
            values['alias_parent_thread_id'] = self.id
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
    description = fields.Html('Description', render_engine="qweb", render_options={"post_process": True}, sanitize=False)
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

    def _mail_get_partner_fields(self):
        return ['customer_id']
