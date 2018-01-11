# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from openerp.osv import fields, osv


class res_partner_mail(osv.Model):
    """ Update partner to add a field about notification preferences """
    _name = "res.partner"
    _inherit = ['res.partner', 'mail.thread']
    _mail_flat_thread = False
    _mail_mass_mailing = _('Customers')

    _columns = {
        'notify_email': fields.selection([
            ('none', 'Never'),
            ('always', 'All Messages'),
            ], 'Receive Inbox Notifications by Email', required=True,
            oldname='notification_email_send',
            help="Policy to receive emails for new messages pushed to your personal Inbox:\n"
                    "- Never: no emails are sent\n"
                    "- All Messages: for every notification you receive in your Inbox"),
    }

    _defaults = {
        'notify_email': lambda *args: 'always'
    }

    def message_get_suggested_recipients(self, cr, uid, ids, context=None):
        recipients = super(res_partner_mail, self).message_get_suggested_recipients(cr, uid, ids, context=context)
        for partner in self.browse(cr, uid, ids, context=context):
            self._message_add_suggested_recipient(cr, uid, recipients, partner, partner=partner, reason=_('Partner Profile'))
        return recipients

    def message_get_default_recipients(self, cr, uid, ids, context=None):
        return dict((id, {'partner_ids': [id], 'email_to': False, 'email_cc': False}) for id in ids)
