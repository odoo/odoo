# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
            return 'portal.action_mail_inbox_feeds_portal'
        else:
            return super(mail_thread, self)._get_inbox_action_xml_id(cr, uid, context=context)
