# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class MailAddressMixin(models.AbstractModel):
    """ Purpose of this mixing is to store a normalized email based on the primary email field.
        A normalized email is considered as :
            - having a left part + @ + a right part (the domain can be without '.something')
            - being lower case
            - having no name before the address. Typically, having no 'Name <>'
            Ex:
            - Formatted Email : 'Name <NaMe@DoMaIn.CoM>'
            - Normalized Email : 'name@domain.com'
        The primary email field can be specified on the parent model, if it differs from the default one ('email')
        The email_normalized field can than be used on that model to search quickly on emails (by simple comparison
        and not using time consuming regex anymore).
        """
    _name = 'mail.address.mixin'
    _description = 'Email address mixin'
    _primary_email = ['email']

    email_normalized = fields.Char(string='Normalized email address', compute="_compute_email_normalized", invisible=True,
                                  compute_sudo=True, store=True, help="""This field is used to search on email address,
                                  as the primary email field can contain more than strictly an email address.""")

    @api.depends(lambda self: self._primary_email)
    def _compute_email_normalized(self):
        self._assert_primary_email()
        [email_field] = self._primary_email
        for record in self:
            record.email_normalized = self._normalize_email(record[email_field])

    def _normalize_email(self, email):
        """ Sanitize and standardize email address entries: all emails should be
        only real email extracted from strings (A <a@a> -> a@a)  and should be
        lower case. """
        emails = tools.email_split(email)
        if not emails or len(emails) != 1:
            return False
        return emails[0].lower()

    def _assert_primary_email(self):
        if not hasattr(self, "_primary_email") or \
                not isinstance(self._primary_email, (list, tuple)) or \
                not len(self._primary_email) == 1:
            raise UserError(_('Invalid primary email field on model %s') % self._name)
        field_name = self._primary_email[0]
        if field_name not in self._fields or self._fields[field_name].type != 'char':
            raise UserError(_('Invalid primary email field on model %s') % self._name)
