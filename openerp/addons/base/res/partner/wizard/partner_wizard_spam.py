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

import netsvc
import tools
from osv import fields, osv
import re

class partner_wizard_spam(osv.osv_memory):
    """ Mass Mailing """

    _name = "partner.wizard.spam"
    _description = "Mass Mailing"

    _columns = {
        'email_from': fields.char("Sender's email", size=256, required=True),
        'subject': fields.char('Subject', size=256,required=True),
        'text': fields.text('Message',required=True),
    }

    def mass_mail_send(self, cr, uid, ids, context):
        """
            Send Email

            @param cr: the current row, from the database cursor.
            @param uid: the current user’s ID for security checks.
            @param ids: the ID or list of IDs
            @param context: A standard dictionary
        """

        nbr = 0
        partner_pool = self.pool.get('res.partner')
        data = self.browse(cr, uid, ids[0], context=context)
        event_pool = self.pool.get('res.partner.event')
        active_ids = context and context.get('active_ids', [])
        partners = partner_pool.browse(cr, uid, active_ids, context)
        type_ = 'plain'
        if re.search('(<(pre)|[pubi].*>)', data.text):
            type_ = 'html'
        for partner in partners:
            for adr in partner.address:
                if adr.email:
                    name = adr.name or partner.name
                    to = '"%s" <%s>' % (name, adr.email)
    #TODO: add some tests to check for invalid email addresses
    #CHECKME: maybe we should use res.partner/email_send
                    smtp_server_pool = self.pool.get('ir.mail_server')
                    msg = smtp_server_pool.pack_message(cr, uid, data.subject, data.text, subtype=type_)
                    smtp_server_pool.send_email(cr, uid, data.email_from, [to], msg)
                    nbr += 1
            event_pool.create(cr, uid,
                    {'name': 'Email(s) sent through mass mailing',
                     'partner_id': partner.id,
                     'description': data.text })
    #TODO: log number of message sent
        return {'email_sent': nbr}

partner_wizard_spam()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
