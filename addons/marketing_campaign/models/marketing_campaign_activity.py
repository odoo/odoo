# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# import time
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


class marketing_campaign_activity(osv.osv):
    _name = "marketing.campaign.activity"
    _order = "name"
    _description = "Campaign Activity"

    _action_types = [
        ('email', 'Email'),
        ('report', 'Report'),
        ('action', 'Custom Action'),
        # TODO implement the subcampaigns.
        # TODO implement the subcampaign out. disallow out transitions from
        # subcampaign activities ?
        #('subcampaign', 'Sub-Campaign'),
    ]

    _columns = {
        'name': fields.char('Name', required=True),
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
        'email_template_id': fields.many2one('mail.template', "Email Template", help='The email to send when this activity is activated'),
        'report_id': fields.many2one('ir.actions.report.xml', "Report", help='The report to generate when this activity is activated', ),
        'server_action_id': fields.many2one('ir.actions.server', string='Action',
                                help= "The action to perform when this activity is activated"),
        'to_ids': fields.one2many('marketing.campaign.transition',
                                            'activity_from_id',
                                            'Next Activities'),
        'from_ids': fields.one2many('marketing.campaign.transition',
                                            'activity_to_id',
                                            'Previous Activities'),
        'variable_cost': fields.float('Variable Cost', help="Set a variable cost if you consider that every campaign item that has reached this point has entailed a certain cost. You can get cost statistics in the Reporting section", digits_compute=dp.get_precision('Product Price')),
        'revenue': fields.float('Revenue', help="Set an expected revenue if you consider that every campaign item that has reached this point has generated a certain revenue. You can get revenue statistics in the Reporting section", digits=0),
        'signal': fields.char('Signal', 
                              help='An activity with a signal can be called programmatically. Be careful, the workitem is always created when a signal is sent'),
        'keep_if_condition_not_met': fields.boolean("Don't Delete Workitems",
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
        report_data, format = render_report(cr, uid, [], activity.report_id.report_name, {}, context=context)
        attach_vals = {
            'name': '%s_%s_%s'%(activity.report_id.report_name,
                                activity.name,workitem.partner_id.name),
            'datas_fname': '%s.%s'%(activity.report_id.report_name,
                                        activity.report_id.report_type),
            'datas': base64.encodestring(report_data),
        }
        self.pool.get('ir.attachment').create(cr, uid, attach_vals)
        return True

    def _process_wi_email(self, cr, uid, activity, workitem, context=None):
        return self.pool.get('mail.template').send_mail(cr, uid,
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
        server_obj.run(cr, uid, [activity.server_action_id.id],
                             context=action_context)
        return True

    def process(self, cr, uid, act_id, wi_id, context=None):
        activity = self.browse(cr, uid, act_id, context=context)
        method = '_process_wi_%s' % (activity.type,)
        action = getattr(self, method, None)
        if not action:
            raise NotImplementedError('Method %r is not implemented on %r object.' % (method, self))

        workitem_obj = self.pool.get('marketing.campaign.workitem')
        workitem = workitem_obj.browse(cr, uid, wi_id, context=context)
        return action(cr, uid, activity, workitem, context=context)

