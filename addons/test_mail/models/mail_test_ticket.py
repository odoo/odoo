import ast

from odoo import api, fields, models, _
from odoo.tools import email_normalize


class MailTestTicket(models.Model):
    """ This model can be used in tests when complex chatter features are
    required like modeling tasks or tickets. """
    _description = 'Ticket-like model'
    _name = "mail.test.ticket"
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
        return {
            record.id:  {
                'email_cc': False,
                'email_to': record.email_from if not record.customer_id.ids else False,
                'partner_ids': record.customer_id.ids,
            } for record in self
        }

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        # Activate more groups to test query counters notably (and be backward compatible for tests)
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        for group_name, _group_method, group_data in groups:
            if group_name == 'portal':
                group_data['active'] = True
            elif group_name == 'customer':
                group_data['active'] = True
                group_data['has_button_access'] = True

        return groups

    def _track_template(self, changes):
        res = super()._track_template(changes)
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
            self._message_add_suggested_recipient(
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


class MailTestTicketEl(models.Model):
    """ Just mail.test.ticket, but exclusion-list enabled. Kept as different
    model to avoid messing with existing tests, notably performance, and ease
    backward comparison. """
    _description = 'Ticket-like model with exclusion list'
    _name = "mail.test.ticket.el"
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


class MailTestTicketMc(models.Model):
    """ Just mail.test.ticket, but multi company. Kept as different model to
    avoid messing with existing tests, notably performance, and ease backward
    comparison. """
    _description = 'Ticket-like model'
    _name = "mail.test.ticket.mc"
    _inherit = ['mail.test.ticket']
    _primary_email = 'email_from'

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    container_id = fields.Many2one('mail.test.container.mc', tracking=True)

    def _notify_get_reply_to(self, default=None):
        # Override to use alias of the parent container
        aliases = self.sudo().mapped('container_id')._notify_get_reply_to(default=default)
        res = {ticket.id: aliases.get(ticket.container_id.id) for ticket in self}
        leftover = self.filtered(lambda rec: not rec.container_id)
        if leftover:
            res.update(super()._notify_get_reply_to(default=default))
        return res


class MailTestContainer(models.Model):
    """ This model can be used in tests when container records like projects
    or teams are required. """
    _description = 'Project-like model with alias'
    _name = "mail.test.container"
    _mail_post_access = 'read'
    _inherit = ['mail.thread', 'mail.alias.mixin']

    name = fields.Char()
    description = fields.Text()
    customer_id = fields.Many2one('res.partner', 'Customer')

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']

    def _message_get_default_recipients(self):
        return {
            record.id: {
                'email_cc': False,
                'email_to': False,
                'partner_ids': record.customer_id.ids,
            } for record in self
        }

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        # Activate more groups to test query counters notably (and be backward compatible for tests)
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


class MailTestContainerMc(models.Model):
    """ Just mail.test.container, but multi company. Kept as different model to
    avoid messing with existing tests, notably performance, and ease backward
    comparison. """
    _description = 'Project-like model with alias (MC)'
    _name = "mail.test.container.mc"
    _mail_post_access = 'read'
    _inherit = ['mail.test.container']

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('mail.test.ticket.mc').id
        return values
