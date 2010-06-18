# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 OpenERP SA (<http://openerp.com>).
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

import time
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta

from osv import fields, osv
import netsvc
import tools
from tools.translate import _

_intervalTypes = {
    'hours': lambda interval: relativedelta(hours=interval),
    'days': lambda interval: relativedelta(days=interval),
    'months': lambda interval: relativedelta(months=interval),
    'years': lambda interval: relativedelta(years=interval),
}

class marketing_campaign(osv.osv):
    _name = "marketing.campaign"
    _description = "Marketing Campaign"

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'object_id': fields.many2one('ir.model', 'Object', required=True,
                                      help="Choose the Object on which you want \
this campaign to be run"),
        'mode':fields.selection([('test', 'Test Directly'),
                                ('test_realtime', 'Test in Realtime'),
                                ('manual', 'With Manual Confirmation'),
                                ('active', 'Normal')],
                                 'Mode', required=True, help= \
"""Test - It creates and process all the workitems directly (without waiting for the delay on transitions) but do not send emails or produce reports.
Test in Realtime - It creates and process all the workitems directly but do not send emails or produce reports.
With Manual Confirmation - the campaigns runs normally, but the user has to validate all workitem manually.
Normal - the campaign runs normally and automatically sends all emails and reports"""),
        'state': fields.selection([('draft', 'Draft'),
                                   ('running', 'Running'),
                                   ('done', 'Done'),
                                   ('cancelled', 'Cancelled'),],
                                   'State',),
        'activity_ids': fields.one2many('marketing.campaign.activity',
                                       'campaign_id', 'Activities'),
        'fixed_cost': fields.float('Fixed Cost', help="The fixed cost is cost\
you required for the campaign"),
    }
    _defaults = {
        'state': lambda *a: 'draft',
        'mode': lambda *a: 'test',
    }

    def state_running_set(self, cr, uid, ids, *args):
        campaign = self.browse(cr, uid, ids[0])
        if not campaign.activity_ids :
            raise osv.except_osv("Error", "There is no activitity in the campaign")
        act_ids = [ act_id.id for act_id in campaign.activity_ids]
        act_ids  = self.pool.get('marketing.campaign.activity').search(cr, uid,
                                [('id', 'in', act_ids), ('start', '=', True)])
        if not act_ids :
            raise osv.except_osv("Error", "There is no starting activitity in the campaign")
        self.write(cr, uid, ids, {'state': 'running'})
        return True

    def state_done_set(self, cr, uid, ids, *args):
        segment_ids = self.pool.get('marketing.campaign.segment').search(cr, uid,
                                            [('campaign_id', 'in', ids),
                                            ('state', '=', 'running')])
        if segment_ids :
            raise osv.except_osv("Error", "Campaign cannot be marked as done before all segments are done")
        self.write(cr, uid, ids, {'state': 'done'})
        return True

    def state_cancel_set(self, cr, uid, ids, *args):
        self.write(cr, uid, ids, {'state': 'cancelled'})
        return True
marketing_campaign()

class marketing_campaign_segment(osv.osv):
    _name = "marketing.campaign.segment"
    _description = "Campaign Segment"

    _columns = {
        'name': fields.char('Name', size=64,required=True),
        'campaign_id': fields.many2one('marketing.campaign', 'Campaign',
             required=True, select=1),
        'object_id': fields.related('campaign_id','object_id',
                                      type='many2one', relation='ir.model',
                                      string='Object'),
        'ir_filter_id': fields.many2one('ir.filters', 'Filter', help=""),
        'sync_last_date': fields.datetime('Latest Synchronization'),
        'sync_mode': fields.selection([('create_date', 'Sync only on creation'),
                                      ('write_date', 'Sync at each modification')],
                                      'Synchronization Mode'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('running', 'Running'),
                                   ('done', 'Done'),
                                   ('cancelled', 'Cancelled')],
                                   'State',),
        'date_run': fields.datetime('Launching Date'),
        'date_done': fields.datetime('End Date'),
    }

    _defaults = {
        'state': lambda *a: 'draft',
        'sync_mode': lambda *a: 'create_date',
    }

    def state_running_set(self, cr, uid, ids, *args):
        segment = self.browse(cr, uid, ids[0])
        curr_date = time.strftime('%Y-%m-%d %H:%M:%S')
        vals = {'state': 'running'}
        if not segment.date_run:
            vals['date_run'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.write(cr, uid, ids, vals)
        return True

    def state_done_set(self, cr, uid, ids, *args):
        wi_ids = self.pool.get("marketing.campaign.workitem").search(cr, uid,
                                [('state', '=', 'todo'), ('segment_id', 'in', ids)])
        self.pool.get("marketing.campaign.workitem").write(cr, uid, wi_ids, {'state':'cancelled'})
        self.write(cr, uid, ids, {'state': 'done','date_done': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True

    def state_cancel_set(self, cr, uid, ids, *args):
        wi_ids = self.pool.get("marketing.campaign.workitem").search(cr, uid,
                                [('state', '=', 'todo'), ('segment_id', 'in', ids)])
        self.pool.get("marketing.campaign.workitem").write(cr, uid, wi_ids, {'state':'cancelled'})
        self.write(cr, uid, ids, {'state': 'cancelled','date_done': time.strftime('%Y-%m-%d %H:%M:%S')})
        return True

    def synchroniz(self, cr, uid, ids, *args):
        self.process_segment(cr, uid, ids)
        return True
    
    def process_segment(self, cr, uid, segment_ids=None, context={}):
        if not segment_ids:
            segment_ids = self.search(cr, uid, [('state', '=', 'running')], context=context)

        action_date = time.strftime('%Y-%m-%d %H:%M:%S')
        campaigns = {}
        for segment in self.browse(cr, uid, segment_ids, context=context):
            campaigns[segment.campaign_id.id] = True
            act_ids = self.pool.get('marketing.campaign.activity').search(cr,
                  uid, [('start', '=', True), ('campaign_id', '=', segment.campaign_id.id)])

            model_obj = self.pool.get(segment.object_id.model)
            criteria = []
            if segment.sync_last_date:
                criteria += [(segment.sync_mode, '>', segment.sync_last_date)]
            if segment.ir_filter_id:
                criteria += eval(segment.ir_filter_id.domain)
            object_ids = model_obj.search(cr, uid, criteria, context=context)

            for o_ids in  model_obj.browse(cr, uid, object_ids, context=context) :
                # avoid duplicated workitem for the same resource
                if segment.sync_mode == 'write_date':
                    segids = self.pool.get('marketing.campaign.workitem').search(cr, uid, [('res_id','=',o_ids.id),('segment_id','=',segment.id)])
                    if segids:
                        continue
                for act_id in act_ids:
                    wi_vals = {
                        'segment_id': segment.id,
                        'activity_id': act_id,
                        'date': action_date,
                        'partner_id': o_ids.partner_id and o_ids.partner_id.id or False,
                        'state': 'todo',
                        'res_id': o_ids.id
                    }
                    self.pool.get('marketing.campaign.workitem').create(cr, uid, wi_vals)
            self.write(cr, uid, segment.id, {'sync_last_date':action_date})
        self.pool.get('marketing.campaign.workitem').process_all(cr, uid, campaigns.keys(), context=context)
        return True

marketing_campaign_segment()

class marketing_campaign_activity(osv.osv):
    _name = "marketing.campaign.activity"
    _description = "Campaign Activity"
    _actions_type = [('email', 'E-mail'), ('paper', 'Paper'), ('action', 'Action'),
                        ('subcampaign', 'Sub-Campaign')]
    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'campaign_id': fields.many2one('marketing.campaign', 'Campaign',
                                            required = True, ondelete='cascade', select=1),
        'object_id': fields.related('campaign_id','object_id',
                                      type='many2one', relation='ir.model',
                                      string='Object'),
        'start': fields.boolean('Start',help= "This activity is launched when the campaign starts."),
        'condition': fields.char('Condition', size=256, required=True,
                                 help="Python condition to know if the activity can be launched"),
        'type': fields.selection(_actions_type,
                                  'Type', required=True,
                                  help="Describe type of action to be performed on the Activity.Eg : Send email,Send paper.."),
        'email_template_id': fields.many2one('email.template','Email Template'),
        'report_id': fields.many2one('ir.actions.report.xml', 'Reports', ),
        'report_directory_id': fields.many2one('document.directory','Directory',
                                help="Folder is used to store the generated reports"),
        'server_action_id': fields.many2one('ir.actions.server', string='Action',
                                help= "Describes the action name.\n"
                                "eg:On which object which action to be taken on basis of which condition"),
        'to_ids': fields.one2many('marketing.campaign.transition',
                                            'activity_from_id',
                                            'Next Activities'),
        'from_ids': fields.one2many('marketing.campaign.transition',
                                            'activity_to_id',
                                            'Previous Activities'),
        'subcampaign_id': fields.many2one('marketing.campaign', 'Sub-Campaign'),
        'subcampaign_segment_id': fields.many2one('marketing.campaign.segment',
                                                   'Sub Campaign Segment'),
        'variable_cost': fields.float('Variable Cost'),
        'revenue': fields.float('Revenue')
    }

    _defaults = {
        'type': lambda *a: 'email',
        'condition': lambda *a: 'True',
        'object_id' : lambda obj, cr, uid, context  : context.get('object_id',False),
    }
    def __init__(self, *args):
        self._actions = {'paper' : self.process_wi_report,
                    'email' : self.process_wi_email,
                    'server_action' : self.process_wi_action,
        }
        return super(marketing_campaign_activity, self).__init__(*args)

    def search(self, cr, uid, args, offset=0, limit=None, order=None,
                                        context=None, count=False):
        if context == None:
            context = {}
        if 'segment_id' in context  and context['segment_id']:
            segment_obj = self.pool.get('marketing.campaign.segment').browse(cr,
                                                    uid, context['segment_id'])
            act_ids = []
            for activity in segment_obj.campaign_id.activity_ids:
                act_ids.append(activity.id)
            return act_ids
        return super(marketing_campaign_activity, self).search(cr, uid, args,
                                           offset, limit, order, context, count)

    def process_wi_report(self, cr, uid, activity, workitem, context={}):
        service = netsvc.LocalService('report.%s'%activity.report_id.report_name)
        (report_data, format) = service.create(cr, uid, [], {}, {})
        attach_vals = {
                'name': '%s_%s_%s'%(activity.report_id.report_name,
                                    activity.name,workitem.partner_id.name),
                'datas_fname': '%s.%s'%(activity.report_id.report_name,
                                            activity.report_id.report_type),
                'parent_id': activity.report_directory_id.id,
                'datas': base64.encodestring(report_data),
                'file_type': format
                }
        self.pool.get('ir.attachment').create(cr, uid, attach_vals)
        return True

    def process_wi_email(self, cr, uid, activity, workitem, context=None):
        print 'Sending Email Init', activity.name
        return self.pool.get('email.template').generate_mail(cr, uid, activity.email_template_id.id, [workitem.res_id], context=context)

    def process_wi_action(self, cr, uid, activity, workitem, context={}):
        context = {}
        server_obj = self.pool.get('ir.actions.server')
        server_obj.run(cr, uid, [activity.server_action_id.id], context)
        return True

    def process(self, cr, uid, act_id, wi_id, context={}):
        activity = self.browse(cr, uid, act_id)
        print 'Process', activity.name
        workitem_obj = self.pool.get('marketing.campaign.workitem')
        workitem = workitem_obj.browse(cr, uid, wi_id, context=context)
        print 'WI', workitem, activity.type
        return self._actions[activity.type](cr, uid, activity, workitem, context)

marketing_campaign_activity()

class marketing_campaign_transition(osv.osv):
    _name = "marketing.campaign.transition"
    _description = "Campaign Transition"
    _rec_name = "interval_type"

    _columns = {
        'activity_from_id': fields.many2one('marketing.campaign.activity',
                                                             'Source Activity', select=1),
        'activity_to_id': fields.many2one('marketing.campaign.activity',
                                                        'Destination Activity'),
        'interval_nbr': fields.integer('Interval No.'),
        'interval_type': fields.selection([('hours', 'Hours'), ('days', 'Days'),
                                           ('months', 'Months'),
                                            ('years','Years')],'Interval Type')
    }

    def default_get(self, cr, uid, fields, context={}):
        value = super(marketing_campaign_transition, self).default_get(cr, uid,
                                                                fields, context)
        if context.has_key('type_id'):
            value[context['type_id']] = context['activity_id']
        return value

marketing_campaign_transition()

class marketing_campaign_workitem(osv.osv):
    _name = "marketing.campaign.workitem"
    _description = "Campaign Workitem"

    def _res_name_get(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.res_id:
                try:
                    res[obj.id] = self.pool.get(obj.object_id.model).name_get(cr, uid, [obj.res_id], context=context)[0][1]
                except:
                    res[obj.id] = '/'
            else:
                res[obj.id] = '/'
        return res

    _columns = {
        'segment_id': fields.many2one('marketing.campaign.segment', 'Segment',
             required=True),
        'activity_id': fields.many2one('marketing.campaign.activity','Activity',
             required=True),
        'campaign_id': fields.related('segment_id', 'campaign_id',
             type='many2one', relation='marketing.campaign', string='Campaign', readonly=True),
        'object_id': fields.related('segment_id', 'campaign_id', 'object_id',
             type='many2one', relation='ir.model', string='Object', select=1),
        'res_id': fields.integer('Resource ID', select=1),
        'res_name': fields.function(_res_name_get, method=True, string='Resource Name', type="char", size=64),
        'date': fields.datetime('Execution Date'),
        'partner_id': fields.many2one('res.partner', 'Partner', select=1),
        'state': fields.selection([('todo', 'To Do'), ('inprogress', 'In Progress'),
                                   ('exception', 'Exception'), ('done', 'Done'),
                                   ('cancelled', 'Cancelled')], 'State'),

        'error_msg' : fields.text('Error Message')
    }
    _defaults = {
        'state': lambda *a: 'todo',
    }

    def process_chain(self, cr, uid, workitem_id, context={}):
        workitem = self.browse(cr, uid, workitem_id)
        for mct_id in workitem.activity_id.to_ids:
            launch_date = time.strftime('%Y-%m-%d %H:%M:%S')
            if mct_id.interval_type and mct_id.interval_nbr :
                launch_date = (datetime.now() + _intervalTypes[ \
                                mct_id.interval_type](mct_id.interval_nbr) \
                                ).strftime('%Y-%m-%d %H:%M:%S')
            workitem_vals = {
                'segment_id': workitem.segment_id.id,
                'activity_id': mct_id.activity_to_id.id,
                'date': launch_date,
                'partner_id': workitem.partner_id.id,
                'res_id': workitem.res_id,
                'state': 'todo',
            }
            self.create(cr, uid, workitem_vals)
        return True

    def button_draft(self, cr, uid, workitem_ids, context={}):
        for wi in self.browse(cr, uid, workitem_ids, context=context):
            if wi.state=='exception':
                self.write(cr, uid, [wi.id], {'state':'todo'}, context=context)
        return True

    def button_cancel(self, cr, uid, workitem_ids, context={}):
        for wi in self.browse(cr, uid, workitem_ids, context=context):
            if wi.state in ('todo','exception'):
                self.write(cr, uid, [wi.id], {'state':'cancelled'}, context=context)
        return True

    def process(self, cr, uid, workitem_ids, context={}):
        for wi in self.browse(cr, uid, workitem_ids):
            if wi.state == 'todo':
                eval_context = {
                    'pool': self.pool,
                    'cr': cr,
                    'uid': uid,
                    'wi': wi,
                    'object': wi.activity_id,
                    'transition': wi.activity_id.to_ids
                }
                expr = eval(str(wi.activity_id.condition), eval_context)
                if expr:
                    try:
                        result = True
                        if wi.campaign_id.mode in ('manual','active'):
                            result = self.pool.get('marketing.campaign.activity').process(
                                cr, uid, wi.activity_id.id, wi.id, context)
                        if result:
                            self.write(cr, uid, wi.id, {'state': 'done'})
                            self.process_chain(cr, uid, wi.id, context)
                        else:
                            vals = {'state': 'exception'}
                            if type(result) == type({}) and 'error_msg' in result:
                               vals['error_msg'] = result['error_msg']
                            self.write(cr, uid, wi.id, vals)
                    except Exception,e:
                        self.write(cr, uid, wi.id, {'state': 'exception', 'error_msg': str(e)})
                else :
                    self.write(cr, uid, wi.id, {'state': 'cancelled'})

        return True

    def process_all(self, cr, uid, camp_ids=None, context={}):
        camp_obj = self.pool.get('marketing.campaign')
        if not camp_ids:
            camp_ids = camp_obj.search(cr, uid, [('state','=','running')], context=context)
        for camp in camp_obj.browse(cr, uid, camp_ids, context=context):
            if camp.mode in ('test_realtime','active'):
                workitem_ids = self.search(cr, uid, [('state', '=', 'todo'),
                        ('date','<=', time.strftime('%Y-%m-%d %H:%M:%S'))])
            elif camp.mode == 'test':
                workitem_ids = self.search(cr, uid, [('state', '=', 'todo')])
            else:
                # manual states are not processed automatically
                workitem_ids = []
            if workitem_ids:
                self.process(cr, uid, workitem_ids, context)

    def preview(self, cr, uid, ids, context):
        res = {}
        wi_obj = self.browse(cr, uid, ids)[0]
        if wi_obj.activity_id.type == 'email':
            data_obj = self.pool.get('ir.model.data')
            data_id = data_obj._get_id(cr, uid, 'email_template', 'email_template_preview_form')
            if data_id:
                view_id = data_obj.browse(cr, uid, data_id, context=context).res_id
            res = {
                'name': _('Email Preview'),
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'email_template.preview',
                'view_id': False,
                'context': context,
                'views': [(view_id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'nodestroy':True,
                'context': "{'template_id':%d,'rel_model_ref':%d}"%
                                (wi_obj.activity_id.email_template_id.id,
                                 wi_obj.res_id)
                                 
            }

        elif wi_obj.activity_id.type == 'paper':
            datas = {'ids': [wi_obj.res_id],
                     'model': wi_obj.object_id.model}
            res = { 
                'type' : 'ir.actions.report.xml',
                'report_name': wi_obj.activity_id.report_id.report_name,
                'datas' : datas,
                'nodestroy': True, 
                }
        return res

marketing_campaign_workitem()

class email_template(osv.osv):
    _inherit = "email.template"
    _defaults = {
        'object_name': lambda obj, cr, uid, context: context.get('object_id',False),
    }
email_template()
    
class email_template_preview(osv.osv_memory):
    _inherit = "email_template.preview"
    
    def _default_rel_model(self, cr, uid, context=None):
        if 'rel_model_ref' in context :
            return context['rel_model_ref']
        else :
            return False
            
    _defaults = {
        'rel_model_ref' : _default_rel_model
    }

email_template_preview()

class report_xml(osv.osv):
    _inherit = 'ir.actions.report.xml'
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        if context and 'object_id' in context and context['object_id']:
            model = self.pool.get('ir.model').browse(cr, uid,
                                                    context['object_id']).model
            args.append(('model', '=', model))
        return super(report_xml, self).search(cr, uid, args, offset, limit, order, context, count)

report_xml()

