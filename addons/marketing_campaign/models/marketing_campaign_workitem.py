# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from sys import exc_info
from traceback import format_exception

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval as eval


class MarketingCampaignWorkitem(models.Model):
    _name = "marketing.campaign.workitem"
    _description = "Campaign Workitem"

    segment_id = fields.Many2one(
        'marketing.campaign.segment', string='Segment', readonly=True)
    activity_id = fields.Many2one(
        'marketing.campaign.activity', string='Activity', readonly=True, required=True)
    campaign_id = fields.Many2one(
        related='activity_id.campaign_id', string='Campaign', readonly=True, store=True)
    object_id = fields.Many2one(
        related='activity_id.campaign_id.object_id', string='Resource', index=True, readonly=True, store=True)
    res_id = fields.Integer(string='Resource ID', index=True, readonly=True)
    res_name = fields.Char(
        compute='_compute_res_name_get', string='Resource Name', search='_resource_search')
    date = fields.Datetime(
        string='Execution Date', help='If date is not set, this workitem has to be run manually', readonly=True)
    partner_id = fields.Many2one(
        'res.partner', string='Partner', index=True, readonly=True)
    state = fields.Selection([('todo', 'To Do'),
                              ('cancelled', 'Cancelled'),
                              ('exception', 'Exception'),
                              ('done', 'Done'),
                              ], default='todo', string='Status', readonly=True, copy=False)
    error_msg = fields.Text(string='Error Message', readonly=True)

    def _compute_res_name_get(self):
        for wi in self.filtered('res_id'):
            proxy = self.env[wi.object_id.model].browse(wi.res_id)
            if not proxy.exists():
                continue
            ng = proxy.name_get()
            if ng:
                wi.res_name = ng[0][1]
            else:
                wi.res_name = proxy.display_name or '/'

    def _resource_search(self, args):
        """Returns id of workitem whose resource_name matches  with the given name"""
        if not args:
            return []

        condition_name = None
        for domain_item in args:
            # we only use the first domain criterion and ignore all the rest including operators
            if isinstance(domain_item, (list, tuple)) and len(domain_item) == 3 and domain_item[0] == 'res_name':
                condition_name = [None, domain_item[1], domain_item[2]]
                break

        assert condition_name, (_("Invalid search domain for marketing_campaign_workitem.res_name. It should use 'res_name'"))

        self.env.cr.execute("""SELECT w.id, w.res_id, m.model  \
                                FROM marketing_campaign_workitem w \
                                    LEFT JOIN marketing_campaign_activity a ON (a.id=w.activity_id)\
                                    LEFT JOIN marketing_campaign c ON (c.id=a.campaign_id)\
                                    LEFT JOIN ir_model m ON (m.id=c.object_id)
                                    """)
        res = self.env.cr.fetchall()
        workitem_map = {}
        matching_workitems = []
        for id, res_id, model in res:
            workitem_map.setdefault(model, {}).setdefault(res_id, set()).add(id)
        for model, id_map in workitem_map.iteritems():
            Model = self.env[model]
            condition_name[0] = Model._rec_name
            condition = [('id', 'in', id_map.keys()), condition_name]
            for resource in Model.search(condition):
                matching_workitems.extend(id_map[resource.id])
        return [('id', 'in', list(set(matching_workitems)))]

    @api.multi
    def button_draft(self):
        self.ensure_one()
        return self.filtered(lambda wi: wi.state in ('exception', 'cancelled')).write({'state': 'todo'})

    @api.multi
    def button_cancel(self):
        self.ensure_one()
        return self.filtered(lambda wi: wi.state in ('todo', 'exception')).write({'state': 'cancelled'})

    @api.multi
    def _process_one(self):
        self.ensure_one()
        if self.state != 'todo':
            return False

        activity = self.activity_id
        Model = self.env[self.object_id.model].browse(self.res_id)
        eval_context = {
            'activity': activity,
            'workitem': self,
            'object': Model,
            'resource': Model,
            'transitions': activity.to_ids,
            're': re,
        }
        try:
            condition = activity.condition
            campaign_mode = self.campaign_id.mode
            if condition:
                if not eval(condition, eval_context):
                    if activity.keep_if_condition_not_met:
                        self.write({'state': 'cancelled'})
                    else:
                        self.unlink()
                    return
            result = True
            if campaign_mode in ('manual', 'active'):
                result = activity.process(self)
            values = dict(state='done')
            if not self.date:
                values['date'] = fields.Datetime.now()
            self.write(values)

            if result:
                # process _chain
                date = fields.Datetime.from_string(self.date)
                for transition in activity.to_ids:
                    if transition.trigger == 'cosmetic':
                        continue
                    launch_date = False
                    if transition.trigger == 'auto':
                        launch_date = date
                    elif transition.trigger == 'time':
                        launch_date = date + transition._delta()

                    if launch_date:
                        launch_date = fields.Datetime.to_string(launch_date)
                    values = {
                        'date': launch_date,
                        'segment_id': self.segment_id.id,
                        'activity_id': transition.activity_to_id.id,
                        'partner_id': self.partner_id.id,
                        'res_id': self.res_id,
                        'state': 'todo',
                    }
                    new_wi = self.create(values)

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
                        new_wi._process_one()
        except Exception:
            tb = "".join(format_exception(*exc_info()))
            self.write({'state': 'exception', 'error_msg': tb})

    @api.multi
    def process(self):
        for wi in self:
            wi._process_one()

    @api.model
    def process_all(self, campaign=None):
        if campaign is None:
            campaign = self.env['marketing.campaign'].search([('state', '=', 'running')])
        for camp in campaign.filtered(lambda rec: rec.mode != 'manual'):
            while True:
                domain = [('campaign_id', '=', camp.id), ('state', '=', 'todo'), ('date', '!=', False)]
                if camp.mode in ('test_realtime', 'active'):
                    domain += [('date', '<=', fields.Date.today())]
                    workitems = self.search(domain)
                    if not workitems:
                        break
                    workitems.process()

    @api.multi
    def preview(self):
        self.ensure_one()
        res = {}
        view = self.env.ref('mail.email_template_preview_form')
        if self.activity_id.type == 'email':
            res = {
                'name': _('Email Preview'),
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'email_template.preview',
                'view_id': False,
                'context': self.env.context,
                'views': [(view and view.id or 0, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': "{'template_id':%d,'default_res_id':%d}"%
                (self.activity_id.email_template_id.id,
                    self.res_id)
            }

        elif self.activity_id.type == 'report':
            datas = {
                'ids': [self.res_id],
                'model': self.object_id.model
            }
            res = {
                'type': 'ir.actions.report.xml',
                'report_name': self.activity_id.report_id.report_name,
                'datas': datas,
            }
        else:
            raise ValidationError(_('The current step for this item has no email or report to preview.'))
        return res
