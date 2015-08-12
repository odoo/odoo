# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval as eval


class MarketingCampaignSegment(models.Model):
    _name = "marketing.campaign.segment"
    _description = "Campaign Segment"
    _order = "name"


    name = fields.Char(required=True)
    campaign_id = fields.Many2one(
        'marketing.campaign', string='Campaign', required=True, index=True, ondelete="cascade")
    object_id = fields.Many2one(
        related='campaign_id.object_id', string='Resource')
    ir_filter_id = fields.Many2one('ir.filters', string='Filter', ondelete="restrict",
                                   help="Filter to select the matching resource records that belong to this segment. "
                                   "New filters can be created and saved using the advanced search on the list view of the Resource. "
                                   "If no filter is set, all records are selected without filtering. "
                                   "The synchronization mode may also add a criterion to the filter.")
    sync_last_date = fields.Datetime(
        string='Last Synchronization', help="Date on which this segment was synchronized last time (automatically or manually)")
    sync_mode = fields.Selection([('create_date', 'Only records created after last sync'),
                                  ('write_date',
                                   'Only records modified after last sync (no duplicates)'),
                                  ('all', 'All records (no duplicates)')],
                                 string='Synchronization mode', default='create_date', help="Determines an additional criterion to add to the filter when selecting new records to inject in the campaign. "
                                 '"No duplicates" prevents selecting records which have already entered the campaign previously.'
                                 'If the campaign has a "unique field" set, "no duplicates" will also prevent selecting records which have '
                                 'the same value for the unique field as other records that already entered the campaign.')
    state = fields.Selection([('draft', 'New'),
                              ('cancelled', 'Cancelled'),
                              ('running', 'Running'),
                              ('done', 'Done')],
                             'Status', copy=False, default='draft')
    date_run = fields.Datetime(
        string='Launch Date', help="Initial start date of this segment.")
    date_done = fields.Datetime(
        string='End Date', help="Date this segment was last closed or cancelled.")
    date_next_sync = fields.Datetime(compute='_compute_next_sync', string='Next Synchronization',
                                     help="Next time the synchronization job is scheduled to run automatically")

    def _compute_next_sync(self):
        # next auto sync date is same for all segments
        sync_job = self.env.ref('marketing_campaign.ir_cron_marketing_campaign_every_day', False)
        self.date_next_sync = sync_job and sync_job.nextcall or False

    @api.constrains('ir_filter_id', 'campaign_id')
    def _check_model(self):
        for obj in self:
            if self.ir_filter_id and self.campaign_id.object_id.model != self.ir_filter_id.model_id:
                raise ValidationError(_('Model of filter must be same as resource model of Campaign.'))

    @api.onchange('campaign_id')
    def onchange_campaign_id(self):
        res = {'domain': {'ir_filter_id': []}}
        if self.campaign_id:
            campaign = self.campaign_id
            if campaign.object_id:
                mod_name = campaign.object_id.model
                res['domain'] = {'ir_filter_id': [('model_id', '=', mod_name)]}
        else:
            self.ir_filter_id = False
        return res

    @api.multi
    def state_running_set(self):
        self.ensure_one()
        vals = {'state': 'running'}
        if not self.date_run:
            vals['date_run'] = fields.Datetime.now()
        return self.write(vals)

    @api.multi
    def state_done_set(self):
        self.ensure_one()
        workitems = self.env['marketing.campaign.workitem'].search(
            [('state', '=', 'todo'), ('segment_id', 'in', self.ids)])
        workitems.write({'state': 'cancelled'})
        return self.write(
            {'state': 'done', 'date_done': fields.Datetime.now()})

    @api.multi
    def state_cancel_set(self):
        self.ensure_one()
        workitems = self.env['marketing.campaign.workitem'].search(
            [('state', '=', 'todo'), ('segment_id', 'in', self.ids)])
        workitems.write({'state': 'cancelled'})
        return self.write(
            {'state': 'cancelled', 'date_done': fields.Datetime.now()})

    @api.multi
    def synchroniz(self):
        return True if self.process_segment() else False

    @api.model
    def process_segment(self):
        Workitem = self.env['marketing.campaign.workitem']
        campaign = self.env['marketing.campaign']
        segments = self.search([('state', '=', 'running')])

        action_date = fields.Datetime.now()
        for segment in segments.filtered(lambda x: x.campaign_id.state == 'running'):
            campaign |= segment.campaign_id
            activities = segment.campaign_id.activity_ids.filtered(lambda activity: (activity.start == True))
            Model = self.env[segment.object_id.model]
            criteria = []
            if segment.sync_last_date and segment.sync_mode != 'all':
                criteria += [(segment.sync_mode, '>', segment.sync_last_date)]
            if segment.ir_filter_id:
                criteria += eval(segment.ir_filter_id.domain)
            objects = Model.search(criteria)

            for record in objects:
                # avoid duplicate workitem for the same resource
                if segment.sync_mode in ('write_date', 'all'):
                    if campaign._find_duplicate_workitems(record):
                        continue

                wi_vals = {
                    'segment_id': segment.id,
                    'date': action_date,
                    'state': 'todo',
                    'res_id': record.id
                }

                partner = campaign._get_partner_for(record)
                if partner:
                    wi_vals['partner_id'] = partner.id

                for activity in activities:
                    wi_vals['activity_id'] = activity.id
                    Workitem.create(wi_vals)

            self.write({'sync_last_date': action_date})
        Workitem.process_all(campaign)
