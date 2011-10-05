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

from osv import fields, osv
import re
import logging

_logger = logging.getLogger('mass.mailing')

class partner_massmail_wizard(osv.osv_memory):
    """ Mass Mailing """

    _name = "partner.massmail.wizard"
    _description = "Mass Mailing"

    _columns = {
        'email_from': fields.char("Sender's email", size=256, required=True),
        'subject': fields.char('Subject', size=256,required=True),
        'text': fields.text('Message',required=True),
    }

    def mass_mail_send(self, cr, uid, ids, context):
        """Send the given mail to all partners whose ids
           are present in ``context['active_ids']``, to
           all addresses with an email set.

           :param dict context: ``context['active_ids']``
                                should contain the list of
                                ids of the partners who should
                                receive the mail.
        """
        nbr = 0
        partner_pool = self.pool.get('res.partner')
        data = self.browse(cr, uid, ids[0], context=context)
        event_pool = self.pool.get('res.partner.event')
        assert context['active_model'] == 'res.partner', 'This wizard must be started on a list of Partners'
        active_ids = context.get('active_ids', [])
        partners = partner_pool.browse(cr, uid, active_ids, context)
        subtype = 'plain'
        if re.search('(<(pre)|[pubi].*>)', data.text):
            subtype = 'html'
        ir_mail_server = self.pool.get('ir.mail_server')
        emails_seen = set()
        for partner in partners:
            for adr in partner.address:
                if adr.email and not adr.email in emails_seen:
                    try:
                        emails_seen.add(adr.email)
                        name = adr.name or partner.name
                        to = '"%s" <%s>' % (name, adr.email)
                        msg = ir_mail_server.build_email(data.email_from, [to], data.subject, data.text, subtype=subtype)
                        if ir_mail_server.send_email(cr, uid, msg):
                            nbr += 1
                    except Exception:
                        #ignore failed deliveries, will be logged anyway
                        pass
            event_pool.create(cr, uid,
                    {'name': 'Email(s) sent through mass mailing',
                     'partner_id': partner.id,
                     'description': data.text })
        _logger.info('Mass-mailing wizard sent %s emails', nbr)
        return {'email_sent': nbr}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
