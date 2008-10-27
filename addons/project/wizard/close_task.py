# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import wizard
from tools import email_send as email
import pooler
from osv import osv

mail_form = """<?xml version="1.0" ?>
<form string="Send mail to customer">
    <field name="email" colspan="4"/>
    <field name="description" colspan="4"/>
</form>"""

mail_fields = {
    'email': {'string': 'E-Mails', 'type': 'char', 'required': 'True', 'size':64},
    'description': {'string':'Description', 'type':'text', 'required':'True'},
}

def email_send(cr, uid, ids, to_adr, description, context={}):
    for task in pooler.get_pool(cr.dbname).get('project.task').browse(cr, uid, ids, context):
        project = task.project_id
        subject = "Task '%s' closed" % task.name
        if task.user_id and task.user_id.address_id and task.user_id.address_id.email:
            from_adr = task.user_id.address_id.email
            signature = task.user_id.signature
        else:
            raise osv.except_osv(_('Error'), _("Couldn't send mail because your email address is not configured!"))

        if to_adr:
            val = {
                'name': task.name,
                'user_id': task.user_id.name,
                'task_id': "%d/%d" % (project.id, task.id),
                'date_start': task.date_start,
                'date_close': task.date_close,
                'state': task.state
            }
            header = (project.warn_header or '') % val
            footer = (project.warn_footer or '') % val
            body = u'%s\n%s\n%s\n\n-- \n%s' % (header, description, footer, signature)
            email(from_adr, [to_adr], subject, body.encode('utf-8'), email_bcc=[from_adr])
        else:
            raise osv.except_osv(_('Error'), _("Couldn't send mail because the contact for this task (%s) has no email address!") % contact.name)

class wizard_close(wizard.interface):
    def _check_complete(self, cr, uid, data, context):
        task = pooler.get_pool(cr.dbname).get('project.task').browse(cr, uid, data['ids'])[0]
        if not (task.project_id and task.project_id.warn_customer):
            return 'close'
        return 'mail_ask'

    def _get_data(self, cr, uid, data, context):
        email = ''
        task = pooler.get_pool(cr.dbname).get('project.task').browse(cr, uid, data['ids'][0])
        partner_id = task.partner_id or task.project_id.partner_id
        if partner_id and partner_id.address[0].email:
            email = partner_id.address[0].email
        return {'description': task.description, 'email':email}
        
    def _data_send(self, cr, uid, data, context):
        task_obj = pooler.get_pool(cr.dbname).get('project.task')
        if data['form']['email']:
            description = data['form'].get('description', False)
            email_send(cr, uid, data['ids'], data['form']['email'], data['form']['description'])
        return {}

    def _do_close(self, cr, uid, data, context):
        task_obj = pooler.get_pool(cr.dbname).get('project.task')
        task_obj.do_close(cr, uid, data['ids'], context)
        return {}

    states = {
        'init': {
            'actions': [],
            'result': {'type':'choice', 'next_state':_check_complete}
        },
        'mail_ask': {
            'actions': [_get_data],
            'result': {'type':'form', 'arch':mail_form, 'fields':mail_fields, 'state':[('end', 'Cancel'), ('close', 'Quiet close'), ('mail_send', 'Send Message')]},
        },
        'mail_send': {
            'actions': [_data_send],
            'result': {'type':'state', 'state':'close'},
        },
        'close': {
            'actions': [_do_close],
            'result': {'type':'state', 'state':'end'},
        },
    }
wizard_close('project.task.close')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

