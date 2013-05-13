# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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

from openerp.osv import osv, orm
from openerp.tools.translate import _


class mail_message(osv.Model):
    """ Update of mail_message class, to restrict mail access. """
    _inherit = 'mail.message'

    def _search(self, cr, uid, args, offset=0, limit=None, order=None,
        context=None, count=False, access_rights_uid=None):
        """ Override that adds specific access rights of mail.message, to remove
            all no discussion message if uid is a portal user.
        """
        group_ids = self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id
        if any(group.is_portal for group in group_ids):
            subtype_id = self.pool.get("ir.model.data").get_object_reference(cr, uid, 'mail', 'mt_comment')[1]
            args = ['&', ('subtype_id', '=', subtype_id)] + args

        return super(mail_message, self)._search(cr, uid, args, offset=offset, limit=limit, order=order,
            context=context, count=False, access_rights_uid=access_rights_uid)

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        """ Add Access rules of mail.message for portal user:
            - read:
                - raise if the type is not 'comment' or 'email'
        """
        group_ids = self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id
        if any(group.is_portal for group in group_ids):
            subtype_id = self.pool.get("ir.model.data").get_object_reference(cr, uid, 'mail', 'mt_comment')[1]
            cr.execute('SELECT DISTINCT id FROM "%s" WHERE subtype_id != %s AND id = ANY (%%s)' % (self._table, subtype_id), (ids,))
            if cr.fetchall():
                raise orm.except_orm(_('Access Denied'),
                        _('The requested operation cannot be completed due to security restrictions. Please contact your system administrator.\n\n(Document type: %s, Operation: %s)') % \
                        (self._description, operation))

        return super(mail_message, self).check_access_rule(cr, uid, ids=ids, operation=operation, context=context)
