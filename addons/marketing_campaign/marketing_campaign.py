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
from operator import itemgetter
from traceback import format_exception
from sys import exc_info

from osv import fields, osv
import netsvc
from tools.translate import _

_intervalTypes = {
    'hours': lambda interval: relativedelta(hours=interval),
    'days': lambda interval: relativedelta(days=interval),
    'months': lambda interval: relativedelta(months=interval),
    'years': lambda interval: relativedelta(years=interval),
}

DT_FMT = '%Y-%m-%d %H:%M:%S'

def dict_map(f, d):
    return dict((k, f(v)) for k,v in d.items())

def _find_fieldname(model, field):
    inherit_columns = dict_map(itemgetter(2), model._inherit_fields)
    all_columns = dict(inherit_columns, **model._columns)
    for fn in all_columns:
        if all_columns[fn] is field:
            return fn
    raise ValueError('field not found: %r' % (field,))

class selection_converter(object):
    """Format the selection in the browse record objects"""
    def __init__(self, value):
        self._value = value
        self._str = value

    def set_value(self, cr, uid, _self_again, record, field, lang):
        # this design is terrible
        # search fieldname from the field
        fieldname = _find_fieldname(record._table, field)
        context = dict(lang=lang.code)
        fg = record._table.fields_get(cr, uid, [fieldname], context=context)
        selection = dict(fg[fieldname]['selection'])
        self._str = selection[self.value]

    @property
    def value(self):
        return self._value

    def __str__(self):
        return self._str

translate_selections = {
    'selection': selection_converter,
}


class marketing_campaign(osv.osv):
    _name = "marketing.campaign"
    _description = "Marketing Campaign"

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'object_id': fields.many2one('ir.model', 'Object', required=True,
                                      help="Choose the Object on which you want \
this campaign to be run"),
        'partner_field_id': fields.many2one('ir.model.fields', 'Partner Field',
                                            domain="[('model_id', '=', object_id), ('ttype', '=', 'many2one'), ('relation', '=', 'res.partner')]",
                                            help="The generated workitems will be linked to the partner related to the record"),
        'mode':fields.selection([('test', 'Test Directly'),
                                ('test_realtime', 'Test in Realtime'),
                                ('manual', 'With Manual Confirmation'),
                                ('active', 'Normal')],
                                 'Mode', required=True, help= \
"""Test - It creates and process all the activities directly (without waiting for the delay on transitions) but do not send emails or produce reports.
Test in Realtime - It creates and process all the activities directly but do not send emails or produce reports.
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
        actvity_ids = [ act_id.id for act_id in campaign.activity_ids]
        act_obj = self.pool.get('marketing.campaign.activity')
        act_ids  = act_obj.search(cr, uid, [('id', 'in', actvity_ids),
                                                    ('start', '=', True)])
        if not act_ids :
            raise osv.except_osv("Error", "There is no starting activitity in the campaign")
        act_ids = act_obj.search(cr, uid, [('id', 'in', actvity_ids),
                                            ('type', '=', 'email')])
        for activity in act_obj.browse(cr, uid, act_ids):
            if not activity.email_template_id.enforce_from_account :
                raise osv.except_osv("Error", "Campaign cannot be start : Email Account is missing in email activity")
            if activity.email_template_id.enforce_from_account.state != 'approved' :
                raise osv.except_osv("Error", "Campaign cannot be start : Email Account is not approved for email activity")
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


    def signal(self, cr, uid, model, res_id, signal, context=None):
        if not signal:
            raise ValueError('signal cannot be False')

        Workitems = self.pool.get('marketing.campaign.workitem')
        domain = [('object_id.model', '=', model),
                  ('state', '=', 'running')]
        campaign_ids = self.search(cr, uid, domain, context=context)
        for campaign in self.browse(cr, uid, campaign_ids, context):
            for activity in campaign.activity_ids:
                if activity.signal != signal:
                    continue
                wi_domain = [('activity_id', '=', activity.id),
                             ('res_id', '=', res_id),
                             ('state', '=', 'todo'),
                             ('date', '=', False),
                            ]
                wi_ids = Workitems.search(cr, uid, wi_domain, context=context)
                Workitems.process(cr, uid, wi_ids, context=context)
        return True

    def _signal(self, cr, uid, record, signal, context=None):
        return self.signal(cr, uid, record._table._name,
                           record.id, signal, context)

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

    def process_segment(self, cr, uid, segment_ids=None, context=None):
        Workitems = self.pool.get('marketing.campaign.workitem')
        if not segment_ids:
            segment_ids = self.search(cr, uid, [('state', '=', 'running')], context=context)

        action_date = time.strftime('%Y-%m-%d %H:%M:%S')
        campaigns = set()
        for segment in self.browse(cr, uid, segment_ids, context=context):
            campaigns.add(segment.campaign_id.id)
            act_ids = self.pool.get('marketing.campaign.activity').search(cr,
                  uid, [('start', '=', True), ('campaign_id', '=', segment.campaign_id.id)], context=context)

            model_obj = self.pool.get(segment.object_id.model)
            partner_field = segment.campaign_id.partner_field_id.name
            criteria = []
            if segment.sync_last_date:
                criteria += [(segment.sync_mode, '>', segment.sync_last_date)]
            if segment.ir_filter_id:
                criteria += eval(segment.ir_filter_id.domain)
            object_ids = model_obj.search(cr, uid, criteria, context=context)

            for o_ids in model_obj.browse(cr, uid, object_ids, context=context):
                # avoid duplicated workitem for the same resource
                if segment.sync_mode == 'write_date':
                    wi_ids = Workitems.search(cr, uid, [('res_id','=',o_ids.id),('segment_id','=',segment.id)], context=context)
                    if wi_ids:
                        continue

                wi_vals = {
                    'segment_id': segment.id,
                    'date': action_date,
                    'state': 'todo',
                    'res_id': o_ids.id
                }
                if partner_field:
                    partner = getattr(o_ids, partner_field)
                    if partner:
                        wi_vals['partner_id'] = partner.id

                for act_id in act_ids:
                    wi_vals['activity_id'] = act_id
                    Workitems.create(cr, uid, wi_vals, context=context)

            self.write(cr, uid, segment.id, {'sync_last_date':action_date}, context=context)
        Workitems.process_all(cr, uid, list(campaigns), context=context)
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
                                      string='Object', readonly=True),
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
        'revenue': fields.float('Revenue'),
        'signal': fields.char('Signal', size=128,
                              help='An activity with a signal can be called \
                                      programmatically'),
    }

    _defaults = {
        'type': lambda *a: 'email',
        'condition': lambda *a: 'True',
    }

    def _check_signal(self, cr, uid, ids, context=None):
        return all(activity.signal
                   for activity in self.browse(cr, uid, ids, context)
                   for transition in activity.from_ids
                   if transition.trigger == 'signal')

    _constraints = [
        (_check_signal,
         "An incoming transition is triggered by a signal but this transition \
                doesn't have one",
         ['signal', 'from_ids']
        ),
    ]

    def __init__(self, *args):
        # FIXME use self._process_wi_<type>
        self._actions = {'paper' : self.process_wi_report,
                    'email' : self.process_wi_email,
                    'action' : self.process_wi_action,
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
        return self.pool.get('email.template').generate_mail(cr, uid,
                                            activity.email_template_id.id,
                                            [workitem.res_id], context=context)

    def process_wi_action(self, cr, uid, activity, workitem, context={}):
        context = {}
        server_obj = self.pool.get('ir.actions.server')
        context['active_id'] = workitem.res_id
        res = server_obj.run(cr, uid, [activity.server_action_id.id], context)
        #server action return False if the action is perfomed except client_action,other and python code
        return res==False and True or res

    def process(self, cr, uid, act_id, wi_id, context={}):
        activity = self.browse(cr, uid, act_id)
        workitem_obj = self.pool.get('marketing.campaign.workitem')
        workitem = workitem_obj.browse(cr, uid, wi_id, context=context)
        return self._actions[activity.type](cr, uid, activity, workitem, context)

marketing_campaign_activity()

class marketing_campaign_transition(osv.osv):
    _name = "marketing.campaign.transition"
    _description = "Campaign Transition"

    _interval_units = [('hours', 'Hour(s)'), ('days', 'Day(s)'),
                       ('months', 'Month(s)'), ('years','Year(s)')]


    def _get_name(self, cr, uid, ids, fn, args, context=None):
        result = dict.fromkeys(ids, False)
        formatters = {
            'auto': _('Automatic transition'),
            'time': _('After %(interval_nbr)d %(interval_type)s'),
            'signal': _('On signal'),
        }
        for tr in self.browse(cr, uid, ids, context=context,
                              fields_process=translate_selections):
            result[tr.id] = formatters[tr.trigger.value] % tr
        return result


    def _delta(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        transition = self.browse(cr, uid, ids[0], context)
        if transition.trigger != 'time':
            raise ValueError('Delta is only relevant for timed transiton')
        return relativedelta(**{transition.interval_type: transition.interval_nbr})


    _columns = {
        'name': fields.function(_get_name, method=True, string='Name',
                                type='char', size=128),
        'activity_from_id': fields.many2one('marketing.campaign.activity',
                                            'Source Activity', select=1,
                                            required=True),
        'activity_to_id': fields.many2one('marketing.campaign.activity',
                                          'Destination Activity',
                                          required=True),
        'interval_nbr': fields.integer('Interval Value', required=True),
        'interval_type': fields.selection(_interval_units, 'Interval Unit',
                                          required=True),

        'trigger': fields.selection([('auto', 'Automatic'),
                                     ('time', 'Time'),
                                     ('signal','Signal')],
                                    'Trigger', required=True,
                                    help="How is trigger the destination workitem"),
    }

    _defaults = {
        'interval_nbr': 1,
        'interval_type': 'days',
        'trigger': 'time',
    }

    _sql_constraints = [
        ('interval_positive', 'CHECK(interval_nbr >= 0)', 'The interval must be positive or zero')
    ]

    def _check_signal(self, cr, uid, ids, context=None):
        return all(tr.activity_to_id.signal
                   for tr in self.browse(cr, uid, ids, context)
                   if tr.trigger == 'signal')

    _constraints = [
        (_check_signal,
         "The transition is triggered by a signal but destination activity \
                doesn't have one",
         ['trigger', 'activity_to_ids']
        ),
    ]


marketing_campaign_transition()

class marketing_campaign_workitem(osv.osv):
    _name = "marketing.campaign.workitem"
    _description = "Campaign Workitem"

    def _res_name_get(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, '/')
        for wi in self.browse(cr, uid, ids, context=context):
            if not wi.res_id:
                continue

            proxy = self.pool.get(wi.object_id.model)
            ng = proxy.name_get(cr, uid, [wi.res_id], context=context)
            if ng:
                res[wi.id] = ng[0][1]
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
        'res_id': fields.integer('Resource ID', select=1, readonly=1),
        'res_name': fields.function(_res_name_get, method=True, string='Resource Name', type="char", size=64),
        'date': fields.datetime('Execution Date', help='If date is not set, this workitem have to be run manually'),
        'partner_id': fields.many2one('res.partner', 'Partner', select=1),
        'state': fields.selection([('todo', 'To Do'),
                                   ('exception', 'Exception'), ('done', 'Done'),
                                   ('cancelled', 'Cancelled')], 'State'),

        'error_msg' : fields.text('Error Message')
    }
    _defaults = {
        'state': lambda *a: 'todo',
        'date': False,
    }

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

    def _process_one(self, cr, uid, workitem, context=None):
        if workitem.state != 'todo':
            return

        activity = workitem.activity_id

        eval_context = {
            'pool': self.pool,
            'cr': cr,
            'uid': uid,
            'wi': workitem,
            'object': activity,
            'transition': activity.to_ids
        }
        try:
            condition = activity.condition
            campaign_mode = workitem.campaign_id.mode
            if condition:
                if not eval(condition, eval_context):
                    workitem.write({'state': 'cancelled'}, context=context)
                    return
            result = True
            if campaign_mode in ('manual', 'active'):
                Activities = self.pool.get('marketing.campaign.activity')
                result = Activities.process(cr, uid, activity.id, workitem.id,
                                            context=context)

            values = dict(state='done')
            if not workitem.date:
                values['date'] = datetime.now().strftime(DT_FMT)
            workitem.write(values, context=context)

            if result:
                # process _chain
                for transition in activity.to_ids:
                    launch_date = False
                    if transition.trigger == 'auto':
                        launch_date = datetime.now()
                    elif transition.trigger == 'time':
                        launch_date = datetime.now() + transition._delta()

                    if launch_date:
                        launch_date = launch_date.strftime(DT_FMT)
                    values = {
                        'date': launch_date,
                        'segment_id': workitem.segment_id.id,
                        'activity_id': transition.activity_to_id.id,
                        'partner_id': workitem.partner_id.id,
                        'res_id': workitem.res_id,
                        'state': 'todo',
                    }
                    wi_id = self.create(cr, uid, values, context=context)

                    # Now, depending of the trigger and the campaign mode 
                    # we now if must run the newly created workitem.
                    #
                    # rows = transition trigger \ colums = campaign mode
                    #
                    #           test    test_realtime     manual      normal (active)
                    # time       Y            N             N           N
                    # signal     N            N             N           N
                    # auto       Y            Y             Y           Y
                    # 

                    run = transition.trigger == 'auto' \
                          or (transition.trigger == 'time' \
                              and campaign_mode == 'test')
                    if run:
                        new_wi = self.browse(cr, uid, wi_id, context)
                        self._process_one(cr, uid, new_wi, context)

        except Exception:
            tb = "".join(format_exception(*exc_info()))
            workitem.write({'state': 'exception', 'error_msg': tb},
                     context=context)

    def process(self, cr, uid, workitem_ids, context=None):
        for wi in self.browse(cr, uid, workitem_ids, context):
            self._process_one(cr, uid, wi, context)
        return True

    def process_all(self, cr, uid, camp_ids=None, context=None):
        camp_obj = self.pool.get('marketing.campaign')
        if camp_ids is None:
            camp_ids = camp_obj.search(cr, uid, [('state','=','running')], context=context)
        for camp in camp_obj.browse(cr, uid, camp_ids, context=context):
            if camp.mode == 'manual':
                # manual states are not processed automatically
                continue
            while True:
                domain = [('state', '=', 'todo'), ('date', '!=', False)]
                if camp.mode in ('test_realtime', 'active'):
                    domain += [('date','<=', time.strftime('%Y-%m-%d %H:%M:%S'))]

                workitem_ids = self.search(cr, uid, domain, context=context)
                if not workitem_ids:
                    break

                self.process(cr, uid, workitem_ids, context)
        return True

    def preview(self, cr, uid, ids, context):
        res = {}
        wi_obj = self.browse(cr, uid, ids[0], context)
        if wi_obj.activity_id.type == 'email':
            data_obj = self.pool.get('ir.model.data')
            data_id = data_obj._get_id(cr, uid, 'email_template', 'email_template_preview_form')
            view_id = 0
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
        if context is None:
            context = {}
        object_id = context.get('object_id')
        if object_id:
            model = self.pool.get('ir.model').browse(cr, uid, object_id).model
            args.append(('model', '=', model))
        return super(report_xml, self).search(cr, uid, args, offset, limit, order, context, count)

report_xml()

