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

from openerp.addons.base_status.base_state import base_state
from openerp.addons.base_status.base_stage import base_stage
from openerp.addons.crm import crm
from openerp.osv import fields, osv
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import html2plaintext

CRM_HELPDESK_STATES = (
    crm.AVAILABLE_STATES[2][0], # Cancelled
    crm.AVAILABLE_STATES[3][0], # Done
    crm.AVAILABLE_STATES[4][0], # Pending
)

class crm_helpdesk(base_state, base_stage, osv.osv):
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
                            select=True, help='Responsible sales team. Define Responsible user and Email account for mail gateway.'),
            'company_id': fields.many2one('res.company', 'Company'),
            'date_closed': fields.datetime('Closed', readonly=True),
            'partner_id': fields.many2one('res.partner', 'Partner'),
            'email_cc': fields.text('Watchers Emails', size=252 , help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
            'email_from': fields.char('Email', size=128, help="Destination email for email gateway"),
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
            'state': fields.selection(crm.AVAILABLE_STATES, 'Status', size=16, readonly=True,
                                  help='The status is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the status is set to \'Open\'.\
                                  \nWhen the case is over, the status is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the status is set to \'Pending\'.'),
    }

    _defaults = {
        'active': lambda *a: 1,
        'user_id': lambda s, cr, uid, c: s._get_default_user(cr, uid, c),
        'partner_id': lambda s, cr, uid, c: s._get_default_partner(cr, uid, c),
        'email_from': lambda s, cr, uid, c: s._get_default_email(cr, uid, c),
        'state': lambda *a: 'draft',
        'date': lambda *a: fields.datetime.now(),
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.helpdesk', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
    }

    # -------------------------------------------------------
    # Mail gateway
    # -------------------------------------------------------

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None: custom_values = {}
        desc = html2plaintext(msg.get('body')) if msg.get('body') else ''
        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'description': desc,
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'user_id': False,
            'partner_id': msg.get('author_id', False),
        }
        defaults.update(custom_values)
        return super(crm_helpdesk,self).message_new(cr, uid, msg, custom_values=defaults, context=context)

    def message_update(self, cr, uid, ids, msg, update_vals=None, context=None):
        """ Overrides mail_thread message_update that is called by the mailgateway
            through message_process.
            This method updates the document according to the email.
        """
        if isinstance(ids, (str, int, long)):
            ids = [ids]
        if update_vals is None: update_vals = {}

        if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
            update_vals['priority'] = msg.get('priority')

        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability'
        }
        for line in msg['body'].split('\n'):
            line = line.strip()
            res = tools.command_re.match(line)
            if res and maps.get(res.group(1).lower()):
                key = maps.get(res.group(1).lower())
                update_vals[key] = res.group(2).lower()

        return super(crm_helpdesk,self).message_update(cr, uid, ids, msg, update_vals=update_vals, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
