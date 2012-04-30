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
import itertools
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from traceback import format_exception
from sys import exc_info
from tools.safe_eval import safe_eval as eval
import re
from decimal_precision import decimal_precision as dp

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
        'object_id': fields.many2one('ir.model', 'Resource', required=True,
                                      help="Choose the resource on which you want \
this campaign to be run"),
        'partner_field_id': fields.many2one('ir.model.fields', 'Partner Field',
                                            domain="[('model_id', '=', object_id), ('ttype', '=', 'many2one'), ('relation', '=', 'res.partner')]",
                                            help="The generated workitems will be linked to the partner related to the record. "\
                                                  "If the record is the partner itself leave this field empty. "\
                                                  "This is useful for reporting purposes, via the Campaign Analysis or Campaign Follow-up views."),
        'unique_field_id': fields.many2one('ir.model.fields', 'Unique Field',
                                            domain="[('model_id', '=', object_id), ('ttype', 'in', ['char','int','many2one','text','selection'])]",
                                            help='If set, this field will help segments that work in "no duplicates" mode to avoid '\
                                                 'selecting similar records twice. Similar records are records that have the same value for '\
                                                 'this unique field. For example by choosing the "email_from" field for CRM Leads you would prevent '\
                                                 'sending the same campaign to the same email address again. If not set, the "no duplicates" segments '\
                                                 "will only avoid selecting the same record again if it entered the campaign previously. "\
                                                 "Only easily comparable fields like textfields, integers, selections or single relationships may be used."),
        'mode': fields.selection([('test', 'Test Directly'),
                                ('test_realtime', 'Test in Realtime'),
                                ('manual', 'With Manual Confirmation'),
                                ('active', 'Normal')],
                                 'Mode', required=True, help= \
"""Test - It creates and process all the activities directly (without waiting for the delay on transitions) but does not send emails or produce reports.
Test in Realtime - It creates and processes all the activities directly but does not send emails or produce reports.
With Manual Confirmation - the campaigns runs normally, but the user has to validate all workitem manually.
Normal - the campaign runs normally and automatically sends all emails and reports (be very careful with this mode, you're live!)"""),
        'state': fields.selection([('draft', 'New'),
                                   ('running', 'Running'),
                                   ('cancelled', 'Cancelled'),
                                   ('done', 'Done')],
                                   'State',),
        'activity_ids': fields.one2many('marketing.campaign.activity',
                                       'campaign_id', 'Activities'),
        'fixed_cost': fields.float('Fixed Cost', help="Fixed cost for running this campaign. You may also specify variable cost and revenue on each campaign activity. Cost and Revenue statistics are included in Campaign Reporting.", digits_compute=dp.get_precision('Purchase Price')),
    }

    _defaults = {
        'state': lambda *a: 'draft',
        'mode': lambda *a: 'test',
    }

    def state_running_set(self, cr, uid, ids, *args):
        # TODO check that all subcampaigns are running
        campaign = self.browse(cr, uid, ids[0])

        if not campaign.activity_ids:
            raise osv.except_osv(_("Error"), _("The campaign cannot be started: there are no activities in it."))

        has_start = False
        has_signal_without_from = False

        for activity in campaign.activity_ids:
            if activity.start:
                has_start = True
            if activity.signal and len(activity.from_ids) == 0:
                has_signal_without_from = True

        if not has_start and not has_signal_without_from:
            raise osv.except_osv(_("Error"), _("The campaign cannot be started: it doesn't have any starting activity. Modify campaign's activities to mark one as the starting point."))

        return self.write(cr, uid, ids, {'state': 'running'})

    def state_done_set(self, cr, uid, ids, *args):
        # TODO check that this campaign is not a subcampaign in running mode.
        segment_ids = self.pool.get('marketing.campaign.segment').search(cr, uid,
                                            [('campaign_id', 'in', ids),
                                            ('state', '=', 'running')])
        if segment_ids :
            raise osv.except_osv(_("Error"), _("The campaign cannot be marked as done before all segments are closed."))
        self.write(cr, uid, ids, {'state': 'done'})
        return True

    def state_cancel_set(self, cr, uid, ids, *args):
        # TODO check that this campaign is not a subcampaign in running mode.
        self.write(cr, uid, ids, {'state': 'cancelled'})
        return True

    # dead code
    def signal(self, cr, uid, model, res_id, signal, run_existing=True, context=None):
        record = self.pool.get(model).browse(cr, uid, res_id, context)
        return self._signal(cr, uid, record, signal, run_existing, context)

    #dead code
    def _signal(self, cr, uid, record, signal, run_existing=True, context=None):
        if not signal:
            raise ValueError('signal cannot be False')

        Workitems = self.pool.get('marketing.campaign.workitem')
        domain = [('object_id.model', '=', record._table._name),
                  ('state', '=', 'running')]
        campaign_ids = self.search(cr, uid, domain, context=context)
        for campaign in self.browse(cr, uid, campaign_ids, context=context):
            for activity in campaign.activity_ids:
                if activity.signal != signal:
                    continue

                data = dict(activity_id=activity.id,
                            res_id=record.id,
                            state='todo')
                wi_domain = [(k, '=', v) for k, v in data.items()]

                wi_ids = Workitems.search(cr, uid, wi_domain, context=context)
                if wi_ids:
                    if not run_existing:
                        continue
                else:
                    partner = self._get_partner_for(campaign, record)
                    if partner:
                        data['partner_id'] = partner.id
                    wi_id = Workitems.create(cr, uid, data, context=context)
                    wi_ids = [wi_id]
                Workitems.process(cr, uid, wi_ids, context=context)
        return True

    def _get_partner_for(self, campaign, record):
        partner_field = campaign.partner_field_id.name
        if partner_field:
            return getattr(record, partner_field)
        elif campaign.object_id.model == 'res.partner':
            return record
        return None

    # prevent duplication until the server properly duplicates several levels of nested o2m
    def copy(self, cr, uid, id, default=None, context=None):
        raise osv.except_osv(_("Operation not supported"), _("You can not duplicate a campaign, it's not supported yet."))

    def _find_duplicate_workitems(self, cr, uid, record, campaign_rec, context=None):
        """Finds possible duplicates workitems for a record in this campaign, based on a uniqueness
           field.

           :param record: browse_record to find duplicates workitems for.
           :param campaign_rec: browse_record of campaign
        """
        Workitems = self.pool.get('marketing.campaign.workitem')
        duplicate_workitem_domain = [('res_id','=', record.id),
                                     ('campaign_id','=', campaign_rec.id)]
        unique_field = campaign_rec.unique_field_id
        if unique_field:
            unique_value = getattr(record, unique_field.name, None)
            if unique_value:
                if unique_field.ttype == 'many2one':
                    unique_value = unique_value.id
                similar_res_ids = self.pool.get(campaign_rec.object_id.model).search(cr, uid,
                                    [(unique_field.name, '=', unique_value)], context=context)
                if similar_res_ids:
                    duplicate_workitem_domain = [('res_id','in', similar_res_ids),
                                                 ('campaign_id','=', campaign_rec.id)]
        return Workitems.search(cr, uid, duplicate_workitem_domain, context=context)


marketing_campaign()

class marketing_campaign_segment(osv.osv):
    _name = "marketing.campaign.segment"
    _description = "Campaign Segment"
    _order = "name"

    def _get_next_sync(self, cr, uid, ids, fn, args, context=None):
        # next auto sync date is same for all segments
        sync_job = self.pool.get('ir.model.data').get_object(cr, uid, 'marketing_campaign', 'ir_cron_marketing_campaign_every_day', context=context)
        next_sync = sync_job and sync_job.nextcall or False
        return dict.fromkeys(ids, next_sync)

    _columns = {
        'name': fields.char('Name', size=64,required=True),
        'campaign_id': fields.many2one('marketing.campaign', 'Campaign', required=True, select=1, ondelete="cascade"),
        'object_id': fields.related('campaign_id','object_id', type='many2one', relation='ir.model', string='Resource'),
        'ir_filter_id': fields.many2one('ir.filters', 'Filter', ondelete="restrict",
                            help="Filter to select the matching resource records that belong to this segment. "\
                                 "New filters can be created and saved using the advanced search on the list view of the Resource. "\
                                 "If no filter is set, all records are selected without filtering. "\
                                 "The synchronization mode may also add a criterion to the filter."),
        'sync_last_date': fields.datetime('Last Synchronization', help="Date on which this segment was synchronized last time (automatically or manually)"),
        'sync_mode': fields.selection([('create_date', 'Only records created after last sync'),
                                      ('write_date', 'Only records modified after last sync (no duplicates)'),
                                      ('all', 'All records (no duplicates)')],
                                      'Synchronization mode',
                                      help="Determines an additional criterion to add to the filter when selecting new records to inject in the campaign. "\
                                           '"No duplicates" prevents selecting records which have already entered the campaign previously.'\
                                           'If the campaign has a "unique field" set, "no duplicates" will also prevent selecting records which have '\
                                           'the same value for the unique field as other records that already entered the campaign.'),
        'state': fields.selection([('draft', 'New'),
                                   ('running', 'Running'),
                                   ('cancelled', 'Cancelled'),
                                   ('done', 'Done')],
                                   'State',),
        'date_run': fields.datetime('Launch Date', help="Initial start date of this segment."),
        'date_done': fields.datetime('End Date', help="Date this segment was last closed or cancelled."),
        'date_next_sync': fields.function(_get_next_sync, string='Next Synchronization', type='datetime', help="Next time the synchronization job is scheduled to run automatically"),
    }

    _defaults = {
        'state': lambda *a: 'draft',
        'sync_mode': lambda *a: 'create_date',
    }

    def _check_model(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if not obj.ir_filter_id:
                return True
            if obj.campaign_id.object_id.model != obj.ir_filter_id.model_id:
                return False
        return True

    _constraints = [
        (_check_model, 'Model of filter must be same as resource model of Campaign ', ['ir_filter_id,campaign_id']),
    ]

    def onchange_campaign_id(self, cr, uid, ids, campaign_id):
        res = {'domain':{'ir_filter_id':[]}}
        campaign_pool = self.pool.get('marketing.campaign')
        if campaign_id:
            campaign = campaign_pool.browse(cr, uid, campaign_id)
            model_name = self.pool.get('ir.model').read(cr, uid, [campaign.object_id.id], ['model'])
            if model_name:
                mod_name = model_name[0]['model']
                res['domain'] = {'ir_filter_id': [('model_id', '=', mod_name)]}
        else:
            res['value'] = {'ir_filter_id': False}
        return res

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
        Campaigns = self.pool.get('marketing.campaign')
        if not segment_ids:
            segment_ids = self.search(cr, uid, [('state', '=', 'running')], context=context)

        action_date = time.strftime('%Y-%m-%d %H:%M:%S')
        campaigns = set()
        for segment in self.browse(cr, uid, segment_ids, context=context):
            if segment.campaign_id.state != 'running':
                continue

            campaigns.add(segment.campaign_id.id)
            act_ids = self.pool.get('marketing.campaign.activity').search(cr,
                  uid, [('start', '=', True), ('campaign_id', '=', segment.campaign_id.id)], context=context)

            model_obj = self.pool.get(segment.object_id.model)
            criteria = []
            if segment.sync_last_date and segment.sync_mode != 'all':
                criteria += [(segment.sync_mode, '>', segment.sync_last_date)]
            if segment.ir_filter_id:
                criteria += eval(segment.ir_filter_id.domain)
            object_ids = model_obj.search(cr, uid, criteria, context=context)

            # XXX TODO: rewrite this loop more efficiently without doing 1 search per record!
            for record in model_obj.browse(cr, uid, object_ids, context=context):
                # avoid duplicate workitem for the same resource
                if segment.sync_mode in ('write_date','all'):
                    if Campaigns._find_duplicate_workitems(cr, uid, record, segment.campaign_id, context=context):
                        continue

                wi_vals = {
                    'segment_id': segment.id,
                    'date': action_date,
                    'state': 'todo',
                    'res_id': record.id
                }

                partner = self.pool.get('marketing.campaign')._get_partner_for(segment.campaign_id, record)
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
    _order = "name"
    _description = "Campaign Activity"

    _action_types = [
        ('email', 'E-mail'),
        ('report', 'Report'),
        ('action', 'Custom Action'),
        # TODO implement the subcampaigns.
        # TODO implement the subcampaign out. disallow out transitions from
        # subcampaign activities ?
        #('subcampaign', 'Sub-Campaign'),
    ]

    _columns = {
        'name': fields.char('Name', size=128, required=True),
        'campaign_id': fields.many2one('marketing.campaign', 'Campaign',
                                            required = True, ondelete='cascade', select=1),
        'object_id': fields.related('campaign_id','object_id',
                                      type='many2one', relation='ir.model',
                                      string='Object', readonly=True),
        'start': fields.boolean('Start', help= "This activity is launched when the campaign starts.", select=True),
        'condition': fields.text('Condition', size=256, required=True,
                                 help="Python expression to decide whether the activity can be executed, otherwise it will be deleted or cancelled."
                                 "The expression may use the following [browsable] variables:\n"
                                 "   - activity: the campaign activity\n"
                                 "   - workitem: the campaign workitem\n"
                                 "   - resource: the resource object this campaign item represents\n"
                                 "   - transitions: list of campaign transitions outgoing from this activity\n"
                                 "...- re: Python regular expression module"),
        'type': fields.selection(_action_types, 'Type', required=True,
                                  help="""The type of action to execute when an item enters this activity, such as:
   - Email: send an email using a predefined email template
   - Report: print an existing Report defined on the resource item and save it into a specific directory
   - Custom Action: execute a predefined action, e.g. to modify the fields of the resource record
  """),
        'email_template_id': fields.many2one('email.template', "Email Template", help='The e-mail to send when this activity is activated'),
        'report_id': fields.many2one('ir.actions.report.xml', "Report", help='The report to generate when this activity is activated', ),
        'report_directory_id': fields.many2one('document.directory','Directory',
                                help="This folder is used to store the generated reports"),
        'server_action_id': fields.many2one('ir.actions.server', string='Action',
                                help= "The action to perform when this activity is activated"),
        'to_ids': fields.one2many('marketing.campaign.transition',
                                            'activity_from_id',
                                            'Next Activities'),
        'from_ids': fields.one2many('marketing.campaign.transition',
                                            'activity_to_id',
                                            'Previous Activities'),
        'variable_cost': fields.float('Variable Cost', help="Set a variable cost if you consider that every campaign item that has reached this point has entailed a certain cost. You can get cost statistics in the Reporting section", digits_compute=dp.get_precision('Purchase Price')),
        'revenue': fields.float('Revenue', help="Set an expected revenue if you consider that every campaign item that has reached this point has generated a certain revenue. You can get revenue statistics in the Reporting section", digits_compute=dp.get_precision('Sale Price')),
        'signal': fields.char('Signal', size=128,
                              help='An activity with a signal can be called programmatically. Be careful, the workitem is always created when a signal is sent'),
        'keep_if_condition_not_met': fields.boolean("Don't delete workitems",
                                                    help="By activating this option, workitems that aren't executed because the condition is not met are marked as cancelled instead of being deleted.")
    }

    _defaults = {
        'type': lambda *a: 'email',
        'condition': lambda *a: 'True',
    }

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

    #dead code
    def _process_wi_report(self, cr, uid, activity, workitem, context=None):
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

    def _process_wi_email(self, cr, uid, activity, workitem, context=None):
        return self.pool.get('email.template').send_mail(cr, uid,
                                            activity.email_template_id.id,
                                            workitem.res_id, context=context)

    #dead code
    def _process_wi_action(self, cr, uid, activity, workitem, context=None):
        if context is None:
            context = {}
        server_obj = self.pool.get('ir.actions.server')

        action_context = dict(context,
                              active_id=workitem.res_id,
                              active_ids=[workitem.res_id],
                              active_model=workitem.object_id.model,
                              workitem=workitem)
        res = server_obj.run(cr, uid, [activity.server_action_id.id],
                             context=action_context)
        # server action return False if the action is performed
        # except client_action, other and python code
        return res == False and True or res

    def process(self, cr, uid, act_id, wi_id, context=None):
        activity = self.browse(cr, uid, act_id, context=context)
        method = '_process_wi_%s' % (activity.type,)
        action = getattr(self, method, None)
        if not action:
            raise NotImplementedError('method %r in not implemented on %r object' % (method, self))

        workitem_obj = self.pool.get('marketing.campaign.workitem')
        workitem = workitem_obj.browse(cr, uid, wi_id, context=context)
        return action(cr, uid, activity, workitem, context=context)

marketing_campaign_activity()

class marketing_campaign_transition(osv.osv):
    _name = "marketing.campaign.transition"
    _description = "Campaign Transition"

    _interval_units = [
        ('hours', 'Hour(s)'), ('days', 'Day(s)'),
        ('months', 'Month(s)'), ('years','Year(s)')
    ]

    def _get_name(self, cr, uid, ids, fn, args, context=None):
        result = dict.fromkeys(ids, False)
        formatters = {
            'auto': _('Automatic transition'),
            'time': _('After %(interval_nbr)d %(interval_type)s'),
            'cosmetic': _('Cosmetic'),
        }
        for tr in self.browse(cr, uid, ids, context=context,
                              fields_process=translate_selections):
            result[tr.id] = formatters[tr.trigger.value] % tr
        return result


    def _delta(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        transition = self.browse(cr, uid, ids[0], context=context)
        if transition.trigger != 'time':
            raise ValueError('Delta is only relevant for timed transiton')
        return relativedelta(**{str(transition.interval_type): transition.interval_nbr})


    _columns = {
        'name': fields.function(_get_name, string='Name',
                                type='char', size=128),
        'activity_from_id': fields.many2one('marketing.campaign.activity',
                                            'Previous Activity', select=1,
                                            required=True, ondelete="cascade"),
        'activity_to_id': fields.many2one('marketing.campaign.activity',
                                          'Next Activity',
                                          required=True, ondelete="cascade"),
        'interval_nbr': fields.integer('Interval Value', required=True),
        'interval_type': fields.selection(_interval_units, 'Interval Unit',
                                          required=True),

        'trigger': fields.selection([('auto', 'Automatic'),
                                     ('time', 'Time'),
                                     ('cosmetic', 'Cosmetic'),  # fake plastic transition
                                    ],
                                    'Trigger', required=True,
                                    help="How is the destination workitem triggered"),
    }

    _defaults = {
        'interval_nbr': 1,
        'interval_type': 'days',
        'trigger': 'time',
    }
    def _check_campaign(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.activity_from_id.campaign_id != obj.activity_to_id.campaign_id:
                return False
        return True

    _constraints = [
            (_check_campaign, 'The To/From Activity of transition must be of the same Campaign ', ['activity_from_id,activity_to_id']),
        ]

    _sql_constraints = [
        ('interval_positive', 'CHECK(interval_nbr >= 0)', 'The interval must be positive or zero')
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
            if not proxy.exists(cr, uid, [wi.res_id]):
                continue
            ng = proxy.name_get(cr, uid, [wi.res_id], context=context)
            if ng:
                res[wi.id] = ng[0][1]
        return res

    def _resource_search(self, cr, uid, obj, name, args, domain=None, context=None):
        """Returns id of workitem whose resource_name matches  with the given name"""
        if not len(args):
            return []

        condition_name = None
        for domain_item in args:
            # we only use the first domain criterion and ignore all the rest including operators
            if isinstance(domain_item, (list,tuple)) and len(domain_item) == 3 and domain_item[0] == 'res_name':
                condition_name = [None, domain_item[1], domain_item[2]]
                break

        assert condition_name, "Invalid search domain for marketing_campaign_workitem.res_name. It should use 'res_name'"

        cr.execute("""select w.id, w.res_id, m.model  \
                                from marketing_campaign_workitem w \
                                    left join marketing_campaign_activity a on (a.id=w.activity_id)\
                                    left join marketing_campaign c on (c.id=a.campaign_id)\
                                    left join ir_model m on (m.id=c.object_id)
                                    """)
        res = cr.fetchall()
        workitem_map = {}
        matching_workitems = []
        for id, res_id, model in res:
            workitem_map.setdefault(model,{}).setdefault(res_id,set()).add(id)
        for model, id_map in workitem_map.iteritems():
            model_pool = self.pool.get(model)
            condition_name[0] = model_pool._rec_name
            condition = [('id', 'in', id_map.keys()), condition_name]
            for res_id in model_pool.search(cr, uid, condition, context=context):
                matching_workitems.extend(id_map[res_id])
        return [('id', 'in', list(set(matching_workitems)))]

    _columns = {
        'segment_id': fields.many2one('marketing.campaign.segment', 'Segment', readonly=True),
        'activity_id': fields.many2one('marketing.campaign.activity','Activity',
             required=True, readonly=True),
        'campaign_id': fields.related('activity_id', 'campaign_id',
             type='many2one', relation='marketing.campaign', string='Campaign', readonly=True, store=True),
        'object_id': fields.related('activity_id', 'campaign_id', 'object_id',
             type='many2one', relation='ir.model', string='Resource', select=1, readonly=True, store=True),
        'res_id': fields.integer('Resource ID', select=1, readonly=True),
        'res_name': fields.function(_res_name_get, string='Resource Name', fnct_search=_resource_search, type="char", size=64),
        'date': fields.datetime('Execution Date', help='If date is not set, this workitem has to be run manually', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', select=1, readonly=True),
        'state': fields.selection([('todo', 'To Do'),
                                   ('exception', 'Exception'), ('cancelled', 'Cancelled'),('done', 'Done'),
                                   ], 'State', readonly=True),

        'error_msg' : fields.text('Error Message', readonly=True)
    }
    _defaults = {
        'state': lambda *a: 'todo',
        'date': False,
    }

    def button_draft(self, cr, uid, workitem_ids, context=None):
        for wi in self.browse(cr, uid, workitem_ids, context=context):
            if wi.state in ('exception', 'cancelled'):
                self.write(cr, uid, [wi.id], {'state':'todo'}, context=context)
        return True

    def button_cancel(self, cr, uid, workitem_ids, context=None):
        for wi in self.browse(cr, uid, workitem_ids, context=context):
            if wi.state in ('todo','exception'):
                self.write(cr, uid, [wi.id], {'state':'cancelled'}, context=context)
        return True

    def _process_one(self, cr, uid, workitem, context=None):
        if workitem.state != 'todo':
            return False

        activity = workitem.activity_id
        proxy = self.pool.get(workitem.object_id.model)
        object_id = proxy.browse(cr, uid, workitem.res_id, context=context)

        eval_context = {
            'activity': activity,
            'workitem': workitem,
            'object': object_id,
            'resource': object_id,
            'transitions': activity.to_ids,
            're': re,
        }
        try:
            condition = activity.condition
            campaign_mode = workitem.campaign_id.mode
            if condition:
                if not eval(condition, eval_context):
                    if activity.keep_if_condition_not_met:
                        workitem.write({'state': 'cancelled'}, context=context)
                    else:
                        workitem.unlink(context=context)
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
                workitem = workitem.browse(context=context)[0] # reload
                date = datetime.strptime(workitem.date, DT_FMT)

                for transition in activity.to_ids:
                    if transition.trigger == 'cosmetic':
                        continue
                    launch_date = False
                    if transition.trigger == 'auto':
                        launch_date = date
                    elif transition.trigger == 'time':
                        launch_date = date + transition._delta()

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

                    # Now, depending on the trigger and the campaign mode
                    # we know whether we must run the newly created workitem.
                    #
                    # rows = transition trigger \ colums = campaign mode
                    #
                    #           test    test_realtime     manual      normal (active)
                    # time       Y            N             N           N
                    # cosmetic   N            N             N           N
                    # auto       Y            Y             N           Y
                    #

                    run = (transition.trigger == 'auto' \
                            and campaign_mode != 'manual') \
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
        for wi in self.browse(cr, uid, workitem_ids, context=context):
            self._process_one(cr, uid, wi, context=context)
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
                domain = [('campaign_id', '=', camp.id), ('state', '=', 'todo'), ('date', '!=', False)]
                if camp.mode in ('test_realtime', 'active'):
                    domain += [('date','<=', time.strftime('%Y-%m-%d %H:%M:%S'))]

                workitem_ids = self.search(cr, uid, domain, context=context)
                if not workitem_ids:
                    break

                self.process(cr, uid, workitem_ids, context=context)
        return True

    def preview(self, cr, uid, ids, context=None):
        res = {}
        wi_obj = self.browse(cr, uid, ids[0], context=context)
        if wi_obj.activity_id.type == 'email':
            view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'email_template', 'email_template_preview_form')
            res = {
                'name': _('Email Preview'),
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'email_template.preview',
                'view_id': False,
                'context': context,
                'views': [(view_id and view_id[1] or 0, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'nodestroy':True,
                'context': "{'template_id':%d,'default_res_id':%d}"%
                                (wi_obj.activity_id.email_template_id.id,
                                 wi_obj.res_id)
            }

        elif wi_obj.activity_id.type == 'report':
            datas = {
                'ids': [wi_obj.res_id],
                'model': wi_obj.object_id.model
            }
            res = {
                'type' : 'ir.actions.report.xml',
                'report_name': wi_obj.activity_id.report_id.report_name,
                'datas' : datas,
            }
        else:
            raise osv.except_osv(_('No preview'),_('The current step for this item has no email or report to preview.'))
        return res

marketing_campaign_workitem()

class email_template(osv.osv):
    _inherit = "email.template"
    _defaults = {
        'model_id': lambda obj, cr, uid, context: context.get('object_id',False),
    }

    # TODO: add constraint to prevent disabling / disapproving an email account used in a running campaign

email_template()

class report_xml(osv.osv):
    _inherit = 'ir.actions.report.xml'
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        object_id = context.get('object_id')
        if object_id:
            model = self.pool.get('ir.model').browse(cr, uid, object_id, context=context).model
            args.append(('model', '=', model))
        return super(report_xml, self).search(cr, uid, args, offset, limit, order, context, count)

report_xml()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
