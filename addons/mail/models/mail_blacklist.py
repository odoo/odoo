# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.pycompat import izip


class MailBlackList(models.Model):
    """ Model of blacklisted email addresses to stop sending emails."""
    _name = 'mail.blacklist'
    _inherit = ['mail.thread']
    _description = 'Mail Blacklist'
    _rec_name = 'email'

    email = fields.Char(string='Email Address', required=True, index=True, help='This field is case insensitive.',
                        track_visibility=True)
    active = fields.Boolean(default=True, track_visibility=True)

    _sql_constraints = [
        ('unique_email', 'unique (email)', 'Email address already exists!')
    ]

    @api.model_create_multi
    def create(self, values):
        """ To avoid crash during import due to unique email, return the existing records if any """
        sql = '''SELECT id, email FROM mail_blacklist
                WHERE LOWER(email) = any (array[%s])
                ''' % (', '.join(['%s'] * len(values)))
        params = [value['email'].lower() for value in values]
        self._cr.execute(sql, params)
        records = self._cr.fetchall()

        bl_ids = bl_emails = []
        if records:
            bl_ids, bl_emails = list(izip(*records))
        non_blacklisted_records = [value for value in values if value['email'] not in bl_emails]

        # TODO DBE Fixme : reorder ids according to incoming ids.
        results = super(MailBlackList, self).create(non_blacklisted_records)
        return self.env['mail.blacklist'].browse(bl_ids) | results

    def _add(self, email):
        record = self.env["mail.blacklist"].with_context(active_test=False).search([('email', '=', email)])
        if len(record) > 0:
            record.write({'active': True})
        else:
            record = self.create({'email': email})
        return record

    def _remove(self, email):
        record = self.env["mail.blacklist"].with_context(active_test=False).search([('email', '=', email)])
        if len(record) > 0:
            record.write({'active': False})
        else:
            record = record.create({'email': email, 'active': False})
        return record


class MailBlackListMixin(models.AbstractModel):
    """ Mixin that is inherited by all model with opt out.
        USAGE : the field '_primary_email' must be overridden in the model that inherit the mixin
        and must contain the email field of the model.
        """
    _name = 'mail.blacklist.mixin'
    _description = 'Mail Blacklist mixin'
    _primary_email = ['email']

    # Note : is_blacklisted sould only be used for display. As the compute is not depending on the blacklist,
    # once read, it won't be re-computed again if the blacklist is modified in the same request.
    is_blacklisted = fields.Boolean(string='Blacklist', compute="_compute_is_blacklisted", compute_sudo=True,
        store=False, search="_search_is_blacklisted", groups="base.group_user",
        help="If the email address is on the blacklist, the contact won't receive mass mailing anymore, from any list")

    @api.model
    def _search_is_blacklisted(self, operator, value):
        if not hasattr(self.env[self._name], "_primary_email"):
            raise UserError(_('Invalid primary email field on model %s') % self._name)
        [email_field] = self._primary_email
        join_condition = 'INNER' if value else 'RIGHT'
        where_clause = '' if value else ' where b.id is null'
        blacklisted_sql = '''SELECT a.id FROM mail_blacklist b 
            %s JOIN %s a 
            ON b.email = a.%s AND b.active = True%s''' % (join_condition, self._table, email_field, where_clause)
        self._cr.execute(blacklisted_sql)
        res = self._cr.fetchall()
        if not res:
            return [(0, '=', 1)]
        return [('id', 'in', [r[0] for r in res])]

    @api.depends(lambda self: self._primary_email)
    def _compute_is_blacklisted(self):
        [email_field] = self._primary_email
        # TODO : Should remove the sudo as compute_sudo defined on methods.
        # But if user doesn't have access to mail.blacklist, doen't work without sudo().
        blacklist = self.env['mail.blacklist'].sudo().search([('email', 'in', self.mapped(email_field))]).mapped('email')
        for record in self:
            record.is_blacklisted = record[email_field] in blacklist
