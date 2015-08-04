# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import base64
import itertools
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from traceback import format_exception
from sys import exc_info
from openerp.tools.safe_eval import safe_eval as eval
import re
from openerp.addons.decimal_precision import decimal_precision as dp

from openerp import api
from openerp.osv import fields, osv
from openerp.report import render_report
from openerp.tools.translate import _
from openerp.exceptions import UserError

_intervalTypes = {
    'hours': lambda interval: relativedelta(hours=interval),
    'days': lambda interval: relativedelta(days=interval),
    'months': lambda interval: relativedelta(months=interval),
    'years': lambda interval: relativedelta(years=interval),
}

DT_FMT = '%Y-%m-%d %H:%M:%S'


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
        'name': fields.char('Name', required=True),
        'campaign_id': fields.many2one('marketing.campaign', 'Campaign', required=True, select=1, ondelete="cascade"),
        'object_id': fields.related('campaign_id','object_id', type='many2one', relation='ir.model', string='Resource'),
        'ir_filter_id': fields.many2one('ir.filters', 'Filter', ondelete="restrict",
                            domain=lambda self: [('model_id', '=', self.object_id._name)],
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
                                   ('cancelled', 'Cancelled'),
                                   ('running', 'Running'),
                                   ('done', 'Done')],
                                   'Status', copy=False),
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

    @api.cr_uid_ids_context
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

            model_obj = self.pool[segment.object_id.model]
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
