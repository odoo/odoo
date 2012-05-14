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

from crm import crm
from osv import fields, osv
import time
from crm import wizard
import tools
from tools.translate import _

CRM_HELPDESK_STATES = (
    crm.AVAILABLE_STATES[2][0], # Cancelled
    crm.AVAILABLE_STATES[3][0], # Done
    crm.AVAILABLE_STATES[4][0], # Pending
)

wizard.mail_compose_message.SUPPORTED_MODELS.append('crm.helpdesk')

class crm_helpdesk(crm.crm_case, osv.osv):
    """ Helpdesk Cases """

    _name = "crm.helpdesk"
    _description = "Helpdesk"
    _order = "id desc"
    _inherit = ['mail.thread']
    _columns = {
            'id': fields.integer('ID', readonly=True),
            'name': fields.char('Name', size=128, required=True),
            'active': fields.boolean('Active', required=False),
            'date_action_last': fields.datetime('Last Action', readonly=1),
            'date_action_next': fields.datetime('Next Action', readonly=1),
            'description': fields.text('Description'),
            'create_date': fields.datetime('Creation Date' , readonly=True),
            'write_date': fields.datetime('Update Date' , readonly=True),
            'date_deadline': fields.date('Deadline'),
            'user_id': fields.many2one('res.users', 'Responsible'),
            'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                            select=True, help='Sales team to which Case belongs to.\
                                 Define Responsible user and Email account for mail gateway.'),
            'company_id': fields.many2one('res.company', 'Company'),
            'date_closed': fields.datetime('Closed', readonly=True),
            'partner_id': fields.many2one('res.partner', 'Partner'),
            'email_cc': fields.text('Watchers Emails', size=252 , help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
            'email_from': fields.char('Email', size=128, help="These people will receive email."),
            'date': fields.datetime('Date'),
            'ref' : fields.reference('Reference', selection=crm._links_get, size=128),
            'ref2' : fields.reference('Reference 2', selection=crm._links_get, size=128),
            'channel_id': fields.many2one('crm.case.channel', 'Channel', help="Communication channel."),
            'planned_revenue': fields.float('Planned Revenue'),
            'planned_cost': fields.float('Planned Costs'),
            'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
            'probability': fields.float('Probability (%)'),
            'categ_id': fields.many2one('crm.case.categ', 'Category', \
                            domain="['|',('section_id','=',False),('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.helpdesk')]"), 
            'duration': fields.float('Duration', states={'done': [('readonly', True)]}), 
            'state': fields.selection(crm.AVAILABLE_STATES, 'State', size=16, readonly=True, 
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'),
            'message_ids': fields.one2many('mail.message', 'res_id', 'Messages', domain=[('model','=',_name)]),
    }

    _defaults = {
        'active': lambda *a: 1,
        'user_id': crm.crm_case._get_default_user,
        'partner_id': crm.crm_case._get_default_partner,
        'email_from': crm.crm_case. _get_default_email,
        'state': lambda *a: 'draft',
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'section_id': crm.crm_case. _get_section,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.helpdesk', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
    }

    def case_get_note_msg_prefix(self, cr, uid, id, context=None):
        return 'Case'

    def create(self, cr, uid, vals, context=None):
        obj_id = super(crm_helpdesk, self).create(cr, uid, vals, context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def create_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            msg = '%s has been <b>created</b>.' % (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=msg, context=context)
        return True

    def message_new(self, cr, uid, msg_dict, custom_values=None, context=None):
        """Automatically called when new email message arrives"""
        res_id = super(crm_helpdesk,self).message_new(cr, uid, msg_dict, custom_values=custom_values, context=context)
        subject = msg_dict.get('subject')  or _("No Subject")
        body = msg_dict.get('body_text')
        msg_from = msg_dict.get('from')
        vals = {
            'name': subject,
            'email_from': msg_from,
            'email_cc': msg_dict.get('cc'),
            'description': body,
            'user_id': False,
        }
        vals.update(self.message_partner_by_email(cr, uid, msg_from))
        self.write(cr, uid, [res_id], vals, context)
        return res_id

    def message_update(self, cr, uid, ids, msg, vals={}, default_act='pending', context=None):
        if isinstance(ids, (str, int, long)):
            ids = [ids]

        super(crm_helpdesk,self).message_update(cr, uid, ids, msg, context=context)

        if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
            vals['priority'] = msg.get('priority')

        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability'
        }
        vls = {}
        for line in msg['body_text'].split('\n'):
            line = line.strip()
            res = tools.misc.command_re.match(line)
            if res and maps.get(res.group(1).lower()):
                key = maps.get(res.group(1).lower())
                vls[key] = res.group(2).lower()
        vals.update(vls)

        # Unfortunately the API is based on lists
        # but we want to update the state based on the
        # previous state, so we have to loop:
        for case in self.browse(cr, uid, ids, context=context):
            values = dict(vals)
            if case.state in CRM_HELPDESK_STATES:
                values.update(state=crm.AVAILABLE_STATES[1][0]) #re-open
            res = self.write(cr, uid, [case.id], values, context=context)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

