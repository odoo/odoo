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
        email_keys_to_values = super()._get_customer_information()

        for ticket in self:
            email_key = email_normalize(ticket.email_from) or ticket.email_from
            # do not fill Falsy with random data, unless monorecord (= always correct)
            if not email_key and len(self) > 1:
                continue
            values = email_keys_to_values.setdefault(email_key, {})
            if not values.get('phone'):
                values['phone'] = ticket.phone_number
        return email_keys_to_values


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

    def _get_customer_information(self):
        email_keys_to_values = super()._get_customer_information()

        for ticket in self:
            email_key = email_normalize(ticket.email_from) or ticket.email_from
            # do not fill Falsy with random data, unless monorecord (= always correct)
            if not email_key and len(self) > 1:
                continue
            values = email_keys_to_values.setdefault(email_key, {})
            if not values.get('company_id'):
                values['company_id'] = ticket.company_id.id
        return email_keys_to_values

    def _notify_get_reply_to(self, default=None, author_id=False):
        # Override to use alias of the parent container
        aliases = self.sudo().mapped('container_id')._notify_get_reply_to(default=default, author_id=author_id)
        res = {ticket.id: aliases.get(ticket.container_id.id) for ticket in self}
        leftover = self.filtered(lambda rec: not rec.container_id)
        if leftover:
            res.update(super()._notify_get_reply_to(default=default, author_id=author_id))
        return res

    def _creation_subtype(self):
        if self.container_id:
            return self.env.ref('test_mail.st_mail_test_ticket_container_mc_upd')
        return super()._creation_subtype()

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'container_id' in init_values and self.container_id:
            return self.env.ref('test_mail.st_mail_test_ticket_container_mc_upd')
        return super()._track_subtype(init_values)


class MailTestTicketPartner(models.Model):
    """ Mail.test.ticket.mc, with complete partner support. More functional
    and therefore done in a separate model to avoid breaking other tests. """
    _description = 'MC ticket-like model with partner support'
    _name = "mail.test.ticket.partner"
    _inherit = [
        'mail.test.ticket.mc',
        'mail.thread.blacklist',
    ]
    _primary_email = 'email_from'

    # fields to mimic stage-based tracing
    state = fields.Selection(
        [('new', 'New'), ('open', 'Open'), ('close', 'Close'),],
        default='open', tracking=10)
    state_template_id = fields.Many2one('mail.template')

    def _message_post_after_hook(self, message, msg_vals):
        if self.email_from and not self.customer_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            new_partner = message.partner_ids.filtered(
                lambda partner: partner.email == self.email_from or (self.email_normalized and partner.email_normalized == self.email_normalized)
            )
            if new_partner:
                if new_partner[0].email_normalized:
                    email_domain = ('email_normalized', '=', new_partner[0].email_normalized)
                else:
                    email_domain = ('email_from', '=', new_partner[0].email)
                self.search([
                    ('customer_id', '=', False), email_domain,
                ]).write({'customer_id': new_partner[0].id})
        return super()._message_post_after_hook(message, msg_vals)

    def _creation_subtype(self):
        if self.state == 'new':
            return self.env.ref('test_mail.st_mail_test_ticket_partner_new')
        return super(MailTestTicket, self)._creation_subtype()

    def _track_template(self, changes):
        res = super()._track_template(changes)
        record = self[0]
        # acknowledgement-like email, like in project/helpdesk
        if 'state' in changes and record.state == 'new' and record.state_template_id:
            res['state'] = (
                record.state_template_id,
                {
                    'auto_delete_keep_log': False,
                    'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                    'email_layout_xmlid': 'mail.mail_notification_light'
                },
            )
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
