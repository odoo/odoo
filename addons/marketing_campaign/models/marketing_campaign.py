# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import base64
from datetime import datetime
from dateutil.relativedelta import relativedelta
from traceback import format_exception
from sys import exc_info
from openerp.tools.safe_eval import safe_eval as eval
import re
from openerp.addons.decimal_precision import decimal_precision as dp

from openerp import api, SUPERUSER_ID
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


class marketing_campaign(osv.osv):
    _name = "marketing.campaign"
    _description = "Marketing Campaign"

    def _count_segments(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        try:
            for segments in self.browse(cr, uid, ids, context=context):
                res[segments.id] = len(segments.segment_ids)
        except:
            pass
        return res

    _columns = {
        'name': fields.char('Name', required=True),
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
                                   'Status', copy=False),
        'activity_ids': fields.one2many('marketing.campaign.activity',
                                       'campaign_id', 'Activities'),
        'fixed_cost': fields.float('Fixed Cost', help="Fixed cost for running this campaign. You may also specify variable cost and revenue on each campaign activity. Cost and Revenue statistics are included in Campaign Reporting.", digits_compute=dp.get_precision('Product Price')),
        'segment_ids': fields.one2many('marketing.campaign.segment', 'campaign_id', 'Segments', readonly=False),
        'segments_count': fields.function(_count_segments, type='integer', string='Segments')
    }

    _defaults = {
        'state': lambda *a: 'draft',
        'mode': lambda *a: 'test',
    }

    def state_running_set(self, cr, uid, ids, *args):
        # TODO check that all subcampaigns are running
        campaign = self.browse(cr, uid, ids[0])

        if not campaign.activity_ids:
            raise UserError(_("The campaign cannot be started. There are no activities in it."))

        has_start = False
        has_signal_without_from = False

        for activity in campaign.activity_ids:
            if activity.start:
                has_start = True
            if activity.signal and len(activity.from_ids) == 0:
                has_signal_without_from = True

        if not has_start and not has_signal_without_from:
            raise UserError(_("The campaign cannot be started. It does not have any starting activity. Modify campaign's activities to mark one as the starting point."))

        return self.write(cr, uid, ids, {'state': 'running'})

    def state_done_set(self, cr, uid, ids, *args):
        # TODO check that this campaign is not a subcampaign in running mode.
        segment_ids = self.pool.get('marketing.campaign.segment').search(cr, uid,
                                            [('campaign_id', 'in', ids),
                                            ('state', '=', 'running')])
        if segment_ids :
            raise UserError(_("The campaign cannot be marked as done before all segments are closed."))
        self.write(cr, uid, ids, {'state': 'done'})
        return True

    def state_cancel_set(self, cr, uid, ids, *args):
        # TODO check that this campaign is not a subcampaign in running mode.
        self.write(cr, uid, ids, {'state': 'cancelled'})
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
        raise UserError(_('Duplicating campaigns is not supported.'))

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
                similar_res_ids = self.pool[campaign_rec.object_id.model].search(cr, uid,
                                    [(unique_field.name, '=', unique_value)], context=context)
                if similar_res_ids:
                    duplicate_workitem_domain = [('res_id','in', similar_res_ids),
                                                 ('campaign_id','=', campaign_rec.id)]
        return Workitems.search(cr, uid, duplicate_workitem_domain, context=context)
