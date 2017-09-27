# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import html2plaintext
from odoo.exceptions import AccessError


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model
    def default_get(self, fields_list):
        defaults = super(MailMessage, self).default_get(fields_list)

        # Note: explicitly implemented in default_get() instead of field default,
        # to avoid setting to True for all existing messages during upgrades.
        # TODO: this default should probably be dynamic according to the model
        # on which the messages are attached, thus moved to create().
        if 'website_published' in fields_list:
            defaults.setdefault('website_published', True)

        return defaults

    description = fields.Char(compute="_compute_description", help='Message description: either the subject, or the beginning of the body')
    website_published = fields.Boolean(string='Published', help="Visible on the website as a comment", copy=False)

    @api.multi
    def _compute_description(self):
        for message in self:
            if message.subject:
                message.description = message.subject
            else:
                plaintext_ct = '' if not message.body else html2plaintext(message.body)
                message.description = plaintext_ct[:30] + '%s' % (' [...]' if len(plaintext_ct) >= 30 else '')

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """ Override that adds specific access rights of mail.message, to restrict
        messages to published messages for public users. """
        if self.user_has_groups('base.group_public'):
            args = expression.AND([[('website_published', '=', True)], list(args)])

        return super(MailMessage, self)._search(args, offset=offset, limit=limit, order=order,
                                                count=count, access_rights_uid=access_rights_uid)

    @api.multi
    def check_access_rule(self, operation):
        """ Add Access rules of mail.message for non-employee user:
            - read:
                - raise if the type is comment and subtype NULL (internal note)
        """
        if self.user_has_groups('base.group_public'):
            self.env.cr.execute('SELECT id FROM "%s" WHERE website_published IS FALSE AND id = ANY (%%s)' % (self._table), (self.ids,))
            if self.env.cr.fetchall():
                raise AccessError(_('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % (self._description, operation))
        return super(MailMessage, self).check_access_rule(operation=operation)

    @api.multi
    def _portal_message_format(self, fields_list):
        fields_list += ['website_published']
        return super(MailMessage, self)._portal_message_format(fields_list)
