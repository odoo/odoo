# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MailBlackList(models.Model):
    """ Model of blacklisted email addresses to stop sending emails."""
    _name = 'mail.blacklist'
    _inherit = ['mail.thread']
    _description = 'Mail Blacklist'
    _rec_name = 'email'

    email = fields.Char(string='Email Address', required=True, index=True, help='This field is case insensitive.',
                        tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [
        ('unique_email', 'unique (email)', 'Email address already exists!')
    ]

    @api.model_create_multi
    def create(self, values):
        # First of all, extract values to ensure emails are really unique (and don't modify values in place)
        new_values = []
        all_emails = []
        for value in values:
            email = tools.email_normalize(value.get('email'))
            if not email:
                raise UserError(_('Invalid email address %r') % value['email'])
            if email in all_emails:
                continue
            all_emails.append(email)
            new_value = dict(value, email=email)
            new_values.append(new_value)

        """ To avoid crash during import due to unique email, return the existing records if any """
        sql = '''SELECT email, id FROM mail_blacklist WHERE email = ANY(%s)'''
        emails = [v['email'] for v in new_values]
        self._cr.execute(sql, (emails,))
        bl_entries = dict(self._cr.fetchall())
        to_create = [v for v in new_values if v['email'] not in bl_entries]

        # TODO DBE Fixme : reorder ids according to incoming ids.
        results = super(MailBlackList, self).create(to_create)
        return self.env['mail.blacklist'].browse(bl_entries.values()) | results

    def write(self, values):
        if 'email' in values:
            values['email'] = tools.email_normalize(values['email'])
        return super(MailBlackList, self).write(values)

    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override _search in order to grep search on email field and make it
        lower-case and sanitized """
        if args:
            new_args = []
            for arg in args:
                if isinstance(arg, (list, tuple)) and arg[0] == 'email' and isinstance(arg[2], str):
                    normalized = tools.email_normalize(arg[2])
                    if normalized:
                        new_args.append([arg[0], arg[1], normalized])
                    else:
                        new_args.append(arg)
                else:
                    new_args.append(arg)
        else:
            new_args = args
        return super(MailBlackList, self)._search(new_args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    def _add(self, email):
        normalized = tools.email_normalize(email)
        record = self.env["mail.blacklist"].with_context(active_test=False).search([('email', '=', normalized)])
        if len(record) > 0:
            record.write({'active': True})
        else:
            record = self.create({'email': email})
        return record

    def _remove(self, email):
        normalized = tools.email_normalize(email)
        record = self.env["mail.blacklist"].with_context(active_test=False).search([('email', '=', normalized)])
        if len(record) > 0:
            record.write({'active': False})
        else:
            record = record.create({'email': email, 'active': False})
        return record


class MailBlackListMixin(models.AbstractModel):
    """ Mixin that is inherited by all model with opt out. This mixin inherits from
    mail.address.mixin which defines the _primary_email variable and the email_normalized
    field that are mandatory to use the blacklist mixin. Mail Thread capabilities
    are required for this mixin. """
    _name = 'mail.thread.blacklist'
    _description = 'Mail Blacklist mixin'
    _inherit = ['mail.thread', 'mail.address.mixin']

    # Note : is_blacklisted sould only be used for display. As the compute is not depending on the blacklist,
    # once read, it won't be re-computed again if the blacklist is modified in the same request.
    is_blacklisted = fields.Boolean(
        string='Blacklist', compute="_compute_is_blacklisted", compute_sudo=True, store=False,
        search="_search_is_blacklisted", groups="base.group_user",
        help="If the email address is on the blacklist, the contact won't receive mass mailing anymore, from any list")
    # messaging
    message_bounce = fields.Integer('Bounce', help="Counter of the number of bounced emails for this contact", default=0)

    @api.model
    def _search_is_blacklisted(self, operator, value):
        # Assumes operator is '=' or '!=' and value is True or False
        self._assert_primary_email()
        if operator != '=':
            if operator == '!=' and isinstance(value, bool):
                value = not value
            else:
                raise NotImplementedError()

        if value:
            query = """
                SELECT m.id
                    FROM mail_blacklist bl
                    JOIN %s m
                    ON m.email_normalized = bl.email AND bl.active
            """
        else:
            query = """
                SELECT m.id
                    FROM %s m
                    LEFT JOIN mail_blacklist bl
                    ON m.email_normalized = bl.email AND bl.active
                    WHERE bl.id IS NULL
            """
        self._cr.execute(query % self._table)
        res = self._cr.fetchall()
        if not res:
            return [(0, '=', 1)]
        return [('id', 'in', [r[0] for r in res])]

    @api.depends('email_normalized')
    def _compute_is_blacklisted(self):
        # TODO : Should remove the sudo as compute_sudo defined on methods.
        # But if user doesn't have access to mail.blacklist, doen't work without sudo().
        blacklist = set(self.env['mail.blacklist'].sudo().search([
            ('email', 'in', self.mapped('email_normalized'))]).mapped('email'))
        for record in self:
            record.is_blacklisted = record.email_normalized in blacklist

    def _message_receive_bounce(self, email, partner, mail_id=None):
        """ Override of mail.thread generic method. Purpose is to increment the
        bounce counter of the record. """
        super(MailBlackListMixin, self)._message_receive_bounce(email, partner, mail_id=mail_id)
        for record in self:
            record.message_bounce = record.message_bounce + 1
