# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.tools import html2plaintext
from openerp.tools.translate import _
from openerp.osv import osv, fields, expression
from openerp.exceptions import AccessError

class MailMessage(osv.Model):
    _inherit = 'mail.message'

    def _get_description_short(self, cr, uid, ids, name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for message in self.browse(cr, uid, ids, context=context):
            if message.subject:
                res[message.id] = message.subject
            else:
                plaintext_ct = '' if not message.body else html2plaintext(message.body)
                res[message.id] = plaintext_ct[:30] + '%s' % (' [...]' if len(plaintext_ct) >= 30 else '')
        return res

    _columns = {
        'description': fields.function(
            _get_description_short, type='char',
            help='Message description: either the subject, or the beginning of the body'
        ),
        'website_published': fields.boolean(
            'Published', help="Visible on the website as a comment", copy=False,
        ),
    }

    def default_get(self, cr, uid, fields_list, context=None):
        defaults = super(MailMessage, self).default_get(cr, uid, fields_list, context=context)

        # Note: explicitly implemented in default_get() instead of _defaults,
        # to avoid setting to True for all existing messages during upgrades.
        # TODO: this default should probably be dynamic according to the model
        # on which the messages are attached, thus moved to create().
        if 'website_published' in fields_list:
            defaults.setdefault('website_published', True)

        return defaults

    def _search(self, cr, uid, args, offset=0, limit=None, order=None,
                context=None, count=False, access_rights_uid=None):
        """ Override that adds specific access rights of mail.message, to restrict
        messages to published messages for public users. """
        if uid != SUPERUSER_ID:
            group_ids = self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id
            group_user_id = self.pool.get("ir.model.data").get_object_reference(cr, uid, 'base', 'group_public')[1]
            if group_user_id in [group.id for group in group_ids]:
                args = expression.AND([[('website_published', '=', True)], list(args)])

        return super(MailMessage, self)._search(cr, uid, args, offset=offset, limit=limit, order=order,
                                                context=context, count=count, access_rights_uid=access_rights_uid)

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        """ Add Access rules of mail.message for non-employee user:
            - read:
                - raise if the type is comment and subtype NULL (internal note)
        """
        if uid != SUPERUSER_ID:
            group_ids = self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id
            group_user_id = self.pool.get("ir.model.data").get_object_reference(cr, uid, 'base', 'group_public')[1]
            if group_user_id in [group.id for group in group_ids]:
                cr.execute('SELECT id FROM "%s" WHERE website_published IS FALSE AND id = ANY (%%s)' % (self._table), (ids,))
                if cr.fetchall():
                    raise AccessError(_('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % (self._description, operation))
        return super(MailMessage, self).check_access_rule(cr, uid, ids=ids, operation=operation, context=context)
