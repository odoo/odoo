# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-TODAY OpenERP S.A (<http://www.openerp.com>).
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

from openerp import SUPERUSER_ID
from openerp.osv import osv


class mail_thread(osv.AbstractModel):
    """ Update of mail_mail class, to add the signin URL to notifications. """
    _inherit = 'mail.thread'

    def _get_inbox_action_xml_id(self, cr, uid, context=None):
        """ For a given message, return an action that either
            - opens the form view of the related document if model, res_id, and
              read access to the document
            - opens the Inbox with a default search on the conversation if model,
              res_id
            - opens the Inbox with context propagated
        """
        cur_user = self.pool.get('res.users').browse(cr, SUPERUSER_ID, uid, context=context)
        # if uid is a portal user -> action is different
        if any(group.is_portal for group in cur_user.groups_id):
            return ('portal', 'action_mail_inbox_feeds_portal')
        else:
            return super(mail_thread, self)._get_inbox_action_xml_id(cr, uid, context=context)
