# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from odoo.fields import Domain


class MailBlacklist(models.Model):
    """ Model of blacklisted email addresses to stop sending emails."""
    _name = 'mail.blacklist'
    _inherit = ['mail.thread']
    _description = 'Mail Blacklist'
    _rec_name = 'email'

    email = fields.Char(string='Email Address', required=True, index='trigram', help='This field is case insensitive.',
                        tracking=1)
    active = fields.Boolean(default=True, tracking=2)

    _unique_email = models.Constraint(
        'unique (email)',
        'Email address already exists!',
    )

    @api.model_create_multi
    def create(self, vals_list):
        # First of all, extract values to ensure emails are really unique (and don't modify values in place)
        new_values = []
        all_emails = []
        for value in vals_list:
            email = tools.email_normalize(value.get('email'))
            if not email:
                raise UserError(_('Invalid email address “%s”', value['email']))
            if email in all_emails:
                continue
            all_emails.append(email)
            new_value = dict(value, email=email)
            new_values.append(new_value)

        """ To avoid crash during import due to unique email, return the existing records if any """
        to_create = []
        bl_entries = {}
        if new_values:
            sql = '''SELECT email, id FROM mail_blacklist WHERE email = ANY(%s)'''
            emails = [v['email'] for v in new_values]
            self.env.cr.execute(sql, (emails,))
            bl_entries = dict(self.env.cr.fetchall())
            to_create = [v for v in new_values if v['email'] not in bl_entries]

        # TODO DBE Fixme : reorder ids according to incoming ids.
        results = super().create(to_create)
        return self.env['mail.blacklist'].browse(bl_entries.values()) | results

    def write(self, vals):
        if 'email' in vals:
            vals['email'] = tools.email_normalize(vals['email'])
        return super().write(vals)

    def _search(self, domain, *args, **kwargs):
        """ Override _search in order to grep search on email field and make it
        lower-case and sanitized """
        domain = Domain(domain).map_conditions(
            lambda cond: Domain(cond.field_expr, cond.operator, norm_value)
            if cond.field_expr == 'email'
            and isinstance(cond.value, str)
            and (norm_value := tools.email_normalize(cond.value))
            else cond
        )
        return super()._search(domain, *args, **kwargs)

    def _add(self, email, message=None):
        normalized = tools.email_normalize(email)
        record = self.env["mail.blacklist"].with_context(active_test=False).search([('email', '=', normalized)])
        if len(record) > 0:
            if message:
                record._track_set_log_message(message)
            record.action_unarchive()
        else:
            record = self.create({'email': email})
            if message:
                record.with_context(mail_post_autofollow_author_skip=True).message_post(
                    body=message,
                    subtype_xmlid='mail.mt_note',
                )
        return record

    def _remove(self, email, message=None):
        normalized = tools.email_normalize(email)
        record = self.env["mail.blacklist"].with_context(active_test=False).search([('email', '=', normalized)])
        if len(record) > 0:
            if message:
                record._track_set_log_message(message)
            record.action_archive()
        else:
            record = record.create({'email': email, 'active': False})
            if message:
                record.with_context(mail_post_autofollow_author_skip=True).message_post(
                    body=message,
                    subtype_xmlid='mail.mt_note',
                )
        return record

    def mail_action_blacklist_remove(self):
        return {
            'name': _('Are you sure you want to unblacklist this email address?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.blacklist.remove',
            'target': 'new',
            'context': {'dialog_size': 'medium'},
        }

    def action_add(self):
        self._add(self.email)
