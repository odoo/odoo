# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.decimal_precision import decimal_precision as dp


class MarketingCampaign(models.Model):
    _name = "marketing.campaign"
    _description = "Marketing Campaign"


    name = fields.Char(required=True)
    object_id = fields.Many2one('ir.model', string='Resource',
                                required=True, help="Choose the resource on which you want \ this campaign to be run")

    partner_field_id = fields.Many2one('ir.model.fields', string='Partner Field',
                                   domain="[('model_id', '=', object_id), ('ttype', '=', 'many2one'), ('relation', '=', 'res.partner')]",
                                   help="The generated workitems will be linked to the partner related to the record. "
                                   "If the record is the partner itself leave this field empty. "
                                   "This is useful for reporting purposes, via the Campaign Analysis or Campaign Follow-up views.")
    unique_field_id = fields.Many2one('ir.model.fields', string='Unique Field',
                                      domain="[('model_id', '=', object_id), ('ttype', 'in', ['char','int','many2one','text','selection'])]",
                                      help='If set, this field will help segments that work in "no duplicates" mode to avoid '
                                             'selecting similar records twice. Similar records are records that have the same value for '
                                             'this unique field. For example by choosing the "email_from" field for CRM Leads you would prevent '
                                             'sending the same campaign to the same email address again. If not set, the "no duplicates" segments '
                                             "will only avoid selecting the same record again if it entered the campaign previously. "
                                             "Only easily comparable fields like textfields, integers, selections or single relationships may be used.")

    mode = fields.Selection([('test', 'Test Directly'),
                         ('test_realtime', 'Test in Realtime'),
                         ('manual', 'With Manual Confirmation'),
                         ('active', 'Normal')], required=True, default='test', help="""Test - It creates and process all the activities directly (without waiting for the delay on transitions) but does not send emails or produce reports.
Test in Realtime - It creates and processes all the activities directly but does not send emails or produce reports.
With Manual Confirmation - the campaigns runs normally, but the user has to validate all workitem manually.
Normal - the campaign runs normally and automatically sends all emails and reports (be very careful with this mode, you're live!)""")
    state = fields.Selection([('draft', 'New'),
                            ('running', 'Running'),
                            ('cancelled', 'Cancelled'),
                            ('done', 'Done')], string='Status', copy=False, default='draft')
    activity_ids = fields.One2many('marketing.campaign.activity', inverse_name='campaign_id', string='Activities')
    fixed_cost = fields.Float(help="Fixed cost for running this campaign. You may also specify variable cost and revenue on each campaign activity. Cost and Revenue statistics are included in Campaign Reporting.", digits=dp.get_precision('Product Price'))
    segment_ids = fields.One2many('marketing.campaign.segment', inverse_name='campaign_id', string='Segments', readonly=False)
    segments_count = fields.Integer(compute='_compute_segments_count', string='Segments')

    def _compute_segments_count(self):
        segments = self.env['marketing.campaign.segment'].read_group([('campaign_id', 'in', self.ids)], ['campaign_id'], ['campaign_id'])
        mapped_data = dict([(m['campaign_id'][0], m['campaign_id_count']) for m in segments])
        for campaign in self:
            campaign.segments_count = mapped_data.get(campaign.id, 0)

    def _get_partner_for(self, record):
        partner_field = self.partner_field_id.name
        if partner_field:
            return getattr(record, partner_field)
        elif self.object_id.model == 'res.partner':
            return record

    @api.multi
    def state_running_set(self):
        # TODO check that all subcampaigns are running
        self.ensure_one()

        if not self.activity_ids:
            raise UserError(_("The campaign cannot be started. There are no activities in it."))

        has_start = False
        has_signal_without_from = False

        for activity in self.activity_ids:
            if activity.start:
                has_start = True
            if activity.signal and len(activity.from_ids):
                has_signal_without_from = True

        if not has_start and not has_signal_without_from:
            raise UserError(_("The campaign cannot be started. It does not have any starting activity. Modify campaign's activities to mark one as the starting point."))

        return self.write({'state': 'running'})

    @api.multi
    def state_done_set(self):
        # TODO check that this campaign is not a subcampaign in running mode.
        self.ensure_one()
        segments = self.segment_ids.filtered(lambda x: x.state == 'running')
        if segments:
            raise UserError(_("The campaign cannot be marked as done before all segments are closed."))
        return self.write({'state': 'done'})

    @api.multi
    def state_cancel_set(self):
        # TODO check that this campaign is not a subcampaign in running mode.
        self.ensure_one()
        return self.write({'state': 'cancelled'})

    # prevent duplication until the server properly duplicates several levels of nested o2m
    _sql_constraints = [
        ('campaign_uniq', 'unique (name)', 'Duplicating campaigns is not supported.')
    ]

    def _find_duplicate_workitems(self, record):
        """Finds possible duplicates workitems for a record in this campaign, based on a uniqueness
           field.
           :param record: browse_record to find duplicates workitems for.
           :param campaign_rec: browse_record of campaign
        """
        Workitems = self.env['marketing.campaign.workitem']
        duplicate_workitem_domain = [('res_id','=', record.id),
                                     ('campaign_id','=', self.id)]
        unique_field = self.unique_field_id
        if unique_field:
            unique_value = getattr(record, unique_field.name, None)
            if unique_value:
                if unique_field.ttype == 'many2one':
                    unique_value = unique_value.id
                similar_res = self.env[self.object_id.model].search(
                    [(unique_field.name, '=', unique_value)])
                if similar_res:
                    duplicate_workitem_domain = [('res_id','in', similar_res.ids),
                                                 ('campaign_id','=', self.id)]
        return Workitems.search(duplicate_workitem_domain)
