# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError


class MailAddressMixin(models.AbstractModel):
    """ Purpose of this mixin is to store a normalized email based on the primary email field.
    A normalized email is considered as :
        - having a left part + @ + a right part (the domain can be without '.something')
        - being lower case
        - having no name before the address. Typically, having no 'Name <>'
    Ex:
        - Formatted Email : 'Name <NaMe@DoMaIn.CoM>'
        - Normalized Email : 'name@domain.com'
    The primary email field can be specified on the parent model, if it differs from the default one ('email')
    The email_normalized field can than be used on that model to search quickly on emails (by simple comparison
    and not using time consuming regex anymore). """
    _name = 'mail.address.mixin'
    _description = 'Email Address Mixin'
    _primary_email = 'email'

    email_normalized = fields.Char(
        string='Normalized Email', compute="_compute_email_normalized", compute_sudo=True,
        store=True, invisible=True,
        help="This field is used to search on email address as the primary email field can contain more than strictly an email address.")

    @api.depends(lambda self: [self._primary_email])
    def _compute_email_normalized(self):
        self._assert_primary_email()
        for record in self:
            record.email_normalized = tools.email_normalize(record[self._primary_email])

    def _assert_primary_email(self):
        if not hasattr(self, "_primary_email") or not isinstance(self._primary_email, str):
            raise UserError(_('Invalid primary email field on model %s') % self._name)
        if self._primary_email not in self._fields or self._fields[self._primary_email].type != 'char':
            raise UserError(_('Invalid primary email field on model %s') % self._name)
