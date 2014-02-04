# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tools.translate import _
from openerp.osv import osv, fields


class MailMessage(osv.Model):
    _inherit = 'mail.message'

    _columns = {
        'website_published': fields.boolean(
            'Publish', help="Publish on the website as a blog"
        ),
    }

    _defaults = {
        'website_published': True,
    }

    def _search(self, cr, uid, args, offset=0, limit=None, order=None,
                context=None, count=False, access_rights_uid=None):
        """ Override that adds specific access rights of mail.message, to restrict
        messages to published messages for public users. """
        group_ids = self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id
        group_user_id = self.pool.get("ir.model.data").get_object_reference(cr, uid, 'base', 'group_public')[1]
        if group_user_id in [group.id for group in group_ids]:
            args = ['&', ('website_published', '=', True)] + list(args)

        return super(MailMessage, self)._search(cr, uid, args, offset=offset, limit=limit, order=order,
                                                context=context, count=False, access_rights_uid=access_rights_uid)

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        """ Add Access rules of mail.message for non-employee user:
            - read:
                - raise if the type is comment and subtype NULL (internal note)
        """
        group_ids = self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id
        group_user_id = self.pool.get("ir.model.data").get_object_reference(cr, uid, 'base', 'group_public')[1]
        if group_user_id in [group.id for group in group_ids]:
            cr.execute('SELECT id FROM "%s" WHERE website_published IS FALSE AND id = ANY (%%s)' % (self._table), (ids,))
            if cr.fetchall():
                raise osv.except_osv(
                    _('Access Denied'),
                    _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % (self._description, operation))

        return super(MailMessage, self).check_access_rule(cr, uid, ids=ids, operation=operation, context=context)
