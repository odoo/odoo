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
from datetime import datetime
import crm
import time
from tools.translate import _
from crm import crm_case
import binascii
import tools


CRM_LEAD_PENDING_STATES = (
    crm.AVAILABLE_STATES[2][0], # Cancelled
    crm.AVAILABLE_STATES[3][0], # Done
    crm.AVAILABLE_STATES[4][0], # Pending
)

class crm_lead(crm_case, osv.osv):
    """ CRM Lead Case """
    _name = "crm.lead"
    _description = "Lead/Opportunity"
    _order = "date_action, priority, id desc"
    _inherit = ['email.thread','res.partner.address']
    def _compute_day(self, cr, uid, ids, fields, args, context=None):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Openday’s IDs
        @return: difference between current date and log date
        @param context: A standard dictionary for contextual values
        """
        cal_obj = self.pool.get('resource.calendar')
        res_obj = self.pool.get('resource.resource')

        res = {}
        for lead in self.browse(cr, uid, ids, context=context):
            for field in fields:
                res[lead.id] = {}
                duration = 0
                ans = False
                if field == 'day_open':
                    if lead.date_open:
                        date_create = datetime.strptime(lead.create_date, "%Y-%m-%d %H:%M:%S")
                        date_open = datetime.strptime(lead.date_open, "%Y-%m-%d %H:%M:%S")
                        ans = date_open - date_create
                        date_until = lead.date_open
                elif field == 'day_close':
                    if lead.date_closed:
                        date_create = datetime.strptime(lead.create_date, "%Y-%m-%d %H:%M:%S")
                        date_close = datetime.strptime(lead.date_closed, "%Y-%m-%d %H:%M:%S")
                        date_until = lead.date_closed
                        ans = date_close - date_create
                if ans:
                    resource_id = False
                    if lead.user_id:
                        resource_ids = res_obj.search(cr, uid, [('user_id','=',lead.user_id.id)])
                        if len(resource_ids):
                            resource_id = resource_ids[0]

                    duration = float(ans.days)
                    if lead.section_id and lead.section_id.resource_calendar_id:
                        duration =  float(ans.days) * 24
                        new_dates = cal_obj.interval_get(cr,
                            uid,
                            lead.section_id.resource_calendar_id and lead.section_id.resource_calendar_id.id or False,
                            datetime.strptime(lead.create_date, '%Y-%m-%d %H:%M:%S'),
                            duration,
                            resource=resource_id
                        )
                        no_days = []
                        date_until = datetime.strptime(date_until, '%Y-%m-%d %H:%M:%S')
                        for in_time, out_time in new_dates:
                            if in_time.date not in no_days:
                                no_days.append(in_time.date)
                            if out_time > date_until:
                                break
                        duration =  len(no_days)
                res[lead.id][field] = abs(int(duration))
        return res

    _columns = {
        # Overridden from res.partner.address:
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='set null',
            select=True, help="Optional linked partner, usually after conversion of the lead"),

        # From crm.case
        'id': fields.integer('ID'),
        'name': fields.char('Name', size=64),
        'active': fields.boolean('Active', required=False),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'email_from': fields.char('Email', size=128, help="E-mail address of the contact"),
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help='Sales team to which this case belongs to. Defines responsible user and e-mail address for the mail gateway.'),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'email_cc': fields.text('Global CC', size=252 , help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'description': fields.text('Notes'),
        'write_date': fields.datetime('Update Date' , readonly=True),

        # Lead fields
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]"),
        'type_id': fields.many2one('crm.case.resource.type', 'Campaign', \
            domain="['|',('section_id','=',section_id),('section_id','=',False)]"),
        'channel_id': fields.many2one('res.partner.canal', 'Channel'),

        'contact_name': fields.char('Contact Name', size=64),
        'partner_name': fields.char("Customer Name", size=64,help='The name of the future partner that will be created while converting the into opportunity'),
        'optin': fields.boolean('Opt-In', help="If opt-in is checked, this contact has accepted to receive emails."),
        'optout': fields.boolean('Opt-Out', help="If opt-out is checked, this contact has refused to receive emails or unsubscribed to a campaign."),
        'type':fields.selection([
            ('lead','Lead'),
            ('opportunity','Opportunity'),

        ],'Type', help="Type is used to separate Leads and Opportunities"),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'stage_id': fields.many2one('crm.case.stage', 'Stage', domain="[('type','=','lead')]"),
        'user_id': fields.many2one('res.users', 'Salesman'),
        'referred': fields.char('Referred By', size=64),
        'date_open': fields.datetime('Opened', readonly=True),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                method=True, multi='day_open', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                method=True, multi='day_close', type="float", store=True),
        'state': fields.selection(crm.AVAILABLE_STATES, 'State', size=16, readonly=True,
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'),
        'message_ids': fields.one2many('email.message', 'res_id', 'Messages', domain=[('model','=',_name)]),
    }


    _defaults = {
        'active': lambda *a: 1,
        'user_id': crm_case._get_default_user,
        'email_from': crm_case._get_default_email,
        'state': lambda *a: 'draft',
        'type': lambda *a: 'lead',
        'section_id': crm_case._get_section,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.lead', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
        #'stage_id': _get_stage_id,
    }



    def onchange_partner_address_id(self, cr, uid, ids, add, email=False):
        """This function returns value of partner email based on Partner Address
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case IDs
        @param add: Id of Partner's address
        @email: Partner's email ID
        """
        if not add:
            return {'value': {'email_from': False, 'country_id': False}}
        address = self.pool.get('res.partner.address').browse(cr, uid, add)
        return {'value': {'email_from': address.email, 'phone': address.phone, 'country_id': address.country_id.id}}

    def case_open(self, cr, uid, ids, *args):
        """Overrides cancel for crm_case for setting Open Date
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case's Ids
        @param *args: Give Tuple Value
        """
        leads = self.browse(cr, uid, ids)



        for i in xrange(0, len(ids)):
            if leads[i].state == 'draft':
                value = {}
                if not leads[i].stage_id :
                    stage_id = self._find_first_stage(cr, uid, leads[i].type, leads[i].section_id.id or False)
                    value.update({'stage_id' : stage_id})
                value.update({'date_open': time.strftime('%Y-%m-%d %H:%M:%S')})
                self.write(cr, uid, [ids[i]], value)
            self.log_open( cr, uid, leads[i])
        res = super(crm_lead, self).case_open(cr, uid, ids, *args)
        return res

    def log_open(self, cr, uid, case):
        if case.type == 'lead':
            message = _("The lead '%s' has been opened.") % case.name
        elif case.type == 'opportunity':
            message = _("The opportunity '%s' has been opened.") % case.name
        else:
            message = _("The case '%s' has been opened.") % case.name
        self.log(cr, uid, case.id, message)

    def case_close(self, cr, uid, ids, *args):
        """Overrides close for crm_case for setting close date
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        res = super(crm_lead, self).case_close(cr, uid, ids, *args)
        self.write(cr, uid, ids, {'date_closed': time.strftime('%Y-%m-%d %H:%M:%S')})
        for case in self.browse(cr, uid, ids):
            if case.type == 'lead':
                message = _("The lead '%s' has been closed.") % case.name
            elif case.type == 'opportunity':
                message = _("The opportunity '%s' has been closed.") % case.name
            else:
                message = _("The case '%s' has been closed.") % case.name
            self.log(cr, uid, case.id, message)
        return res

    def convert_opportunity(self, cr, uid, ids, context=None):
        """ Precomputation for converting lead to opportunity
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of closeday’s IDs
        @param context: A standard dictionary for contextual values
        @return: Value of action in dict
        """
        if context is None:
            context = {}
        context.update({'active_ids': ids})

        data_obj = self.pool.get('ir.model.data')
        value = {}

        view_id = False

        for case in self.browse(cr, uid, ids, context=context):
            context.update({'active_id': case.id})
            data_id = data_obj._get_id(cr, uid, 'crm', 'view_crm_lead2opportunity_partner')
            view_id1 = False
            if data_id:
                view_id1 = data_obj.browse(cr, uid, data_id, context=context).res_id
            value = {
                    'name': _('Create Partner'),
                    'view_type': 'form',
                    'view_mode': 'form,tree',
                    'res_model': 'crm.lead2opportunity.partner',
                    'view_id': False,
                    'context': context,
                    'views': [(view_id1, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'nodestroy': True
            }
        return value

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}

        if 'date_closed' in vals:
            return super(crm_lead,self).write(cr, uid, ids, vals, context=context)

        if 'stage_id' in vals and vals['stage_id']:
            stage_obj = self.pool.get('crm.case.stage').browse(cr, uid, vals['stage_id'], context=context)
            self.history(cr, uid, ids, _("Changed Stage to: %s") % stage_obj.name, details=_("Changed Stage to: %s") % stage_obj.name)
            message=''
            for case in self.browse(cr, uid, ids, context=context):
                if case.type == 'lead' or  context.get('stage_type',False)=='lead':
                    message = _("The stage of lead '%s' has been changed to '%s'.") % (case.name, stage_obj.name)
                elif case.type == 'opportunity':
                    message = _("The stage of opportunity '%s' has been changed to '%s'.") % (case.name, stage_obj.name)
                self.log(cr, uid, case.id, message)
        return super(crm_lead,self).write(cr, uid, ids, vals, context)

    def stage_historize(self, cr, uid, ids, stage, context=None):
        stage_obj = self.pool.get('crm.case.stage').browse(cr, uid, stage, context=context)
        self.history(cr, uid, ids, _('Stage'), details=stage_obj.name)
        for case in self.browse(cr, uid, ids, context=context):
            if case.type == 'lead':
                message = _("The stage of lead '%s' has been changed to '%s'.") % (case.name, stage_obj.name)
            elif case.type == 'opportunity':
                message = _("The stage of opportunity '%s' has been changed to '%s'.") % (case.name, stage_obj.name)
            self.log(cr, uid, case.id, message)
        return True

    def stage_next(self, cr, uid, ids, context=None):
        stage = super(crm_lead, self).stage_next(cr, uid, ids, context=context)
        if stage:
            stage_obj = self.pool.get('crm.case.stage').browse(cr, uid, stage, context=context)
            if stage_obj.on_change:
                data = {'probability': stage_obj.probability}
                self.write(cr, uid, ids, data)
        return stage

    def stage_previous(self, cr, uid, ids, context=None):
        stage = super(crm_lead, self).stage_previous(cr, uid, ids, context=context)
        if stage:
            stage_obj = self.pool.get('crm.case.stage').browse(cr, uid, stage, context=context)
            if stage_obj.on_change:
                data = {'probability': stage_obj.probability}
                self.write(cr, uid, ids, data)
        return stage

    def message_new(self, cr, uid, msg, context=None):
        """
        Automatically calls when new email message arrives

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks
        @param msg: dictionary object to contain email message data
        """
        thread_pool = self.pool.get('email.thread')

        subject = msg.get('subject')
        body = msg.get('body')
        msg_from = msg.get('from')
        priority = msg.get('priority')

        vals = {
            'name': subject,
            'email_from': msg_from,
            'email_cc': msg.get('cc'),
            'description': body,
            'user_id': False,
        }
        if msg.get('priority', False):
            vals['priority'] = priority

        res = thread_pool.get_partner(cr, uid, msg.get('from', False))
        if res:
            vals.update(res)

        res = self.create(cr, uid, vals, context)
        attachents = msg.get('attachments', [])
        for attactment in attachents or []:
            data_attach = {
                'name': attactment,
                'datas':binascii.b2a_base64(str(attachents.get(attactment))),
                'datas_fname': attactment,
                'description': 'Mail attachment',
                'res_model': self._name,
                'res_id': res,
            }
            self.pool.get('ir.attachment').create(cr, uid, data_attach)

        return res

    def message_update(self, cr, uid, ids, msg, vals={}, default_act='pending', context=None):
        """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of update mail’s IDs
        """
        if isinstance(ids, (str, int, long)):
            ids = [ids]

        if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
            vals['priority'] = msg.get('priority')

        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability'
        }
        vls = {}
        for line in msg['body'].split('\n'):
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
            if case.state in CRM_LEAD_PENDING_STATES:
                values.update(state=crm.AVAILABLE_STATES[1][0]) #re-open
            res = self.write(cr, uid, [case.id], values, context=context)
        return res

    def on_change_optin(self, cr, uid, ids, optin):
        return {'value':{'optin':optin,'optout':False}}

    def on_change_optout(self, cr, uid, ids, optout):
        return {'value':{'optout':optout,'optin':False}}

crm_lead()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
