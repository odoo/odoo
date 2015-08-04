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


class marketing_campaign_workitem(osv.osv):
    _name = "marketing.campaign.workitem"
    _description = "Campaign Workitem"

    def _res_name_get(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, '/')
        for wi in self.browse(cr, uid, ids, context=context):
            if not wi.res_id:
                continue

            proxy = self.pool[wi.object_id.model]
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
            model_pool = self.pool[model]
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
        'state': fields.selection([ ('todo', 'To Do'),
                                    ('cancelled', 'Cancelled'),
                                    ('exception', 'Exception'),
                                    ('done', 'Done'),
                                   ], 'Status', readonly=True, copy=False),
        'error_msg' : fields.text('Error Message', readonly=True)
    }
    _defaults = {
        'state': lambda *a: 'todo',
        'date': False,
    }

    @api.cr_uid_ids_context
    def button_draft(self, cr, uid, workitem_ids, context=None):
        for wi in self.browse(cr, uid, workitem_ids, context=context):
            if wi.state in ('exception', 'cancelled'):
                self.write(cr, uid, [wi.id], {'state':'todo'}, context=context)
        return True

    @api.cr_uid_ids_context
    def button_cancel(self, cr, uid, workitem_ids, context=None):
        for wi in self.browse(cr, uid, workitem_ids, context=context):
            if wi.state in ('todo','exception'):
                self.write(cr, uid, [wi.id], {'state':'cancelled'}, context=context)
        return True

    def _process_one(self, cr, uid, workitem, context=None):
        if workitem.state != 'todo':
            return False

        activity = workitem.activity_id
        proxy = self.pool[workitem.object_id.model]
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
                        workitem.write({'state': 'cancelled'})
                    else:
                        workitem.unlink()
                    return
            result = True
            if campaign_mode in ('manual', 'active'):
                Activities = self.pool.get('marketing.campaign.activity')
                result = Activities.process(cr, uid, activity.id, workitem.id,
                                            context=context)

            values = dict(state='done')
            if not workitem.date:
                values['date'] = datetime.now().strftime(DT_FMT)
            workitem.write(values)

            if result:
                # process _chain
                workitem.refresh()       # reload
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
            workitem.write({'state': 'exception', 'error_msg': tb})

    @api.cr_uid_ids_context
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
            view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'mail', 'email_template_preview_form')
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
            raise UserError(_('The current step for this item has no email or report to preview.'))
        return res
