# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.fields import Datetime
from odoo.osv.expression import NEGATIVE_TERM_OPERATORS


class MarketingParticipant(models.Model):
    _name = 'marketing.participant'
    _description = 'Marketing Participant'
    _order = 'id ASC'
    _rec_name = 'resource_ref'

    @api.model
    def default_get(self, default_fields):
        defaults = super(MarketingParticipant, self).default_get(default_fields)
        if 'res_id' in default_fields and not defaults.get('res_id'):
            model_name = defaults.get('model_name')
            if not model_name and defaults.get('campaign_id'):
                model_name = self.env['marketing.campaign'].browse(defaults['campaign_id']).model_name
            if model_name and model_name in self.env:
                resource = self.env[model_name].search([], limit=1)
                defaults['res_id'] = resource.id
        return defaults

    @api.model
    def _selection_target_model(self):
        models = self.env['ir.model'].sudo().search([('is_mail_thread', '=', True)])
        return [(model.model, model.name) for model in models]

    def _search_resource_ref(self, operator, value):
        ir_models = set([model['model_name'] for model in self.env['marketing.campaign'].search([]).read(['model_name'])])
        ir_model_ids = []
        for model in ir_models:
            if model in self.env:
                ir_model_ids += self.env['marketing.participant'].search(['&', ('model_name', '=', model), ('res_id', 'in', [name[0] for name in self.env[model].name_search(name=value)])]).ids
        operator = 'not in' if operator in NEGATIVE_TERM_OPERATORS else 'in'
        return [('id', operator, ir_model_ids)]

    campaign_id = fields.Many2one(
        'marketing.campaign', string='Campaign',
        index=True, ondelete='cascade', required=True)
    model_id = fields.Many2one(
        'ir.model', string='Model', related='campaign_id.model_id',
        index=True, readonly=True, store=True)
    model_name = fields.Char(
        string='Record model', related='campaign_id.model_id.model',
        readonly=True, store=True)
    res_id = fields.Integer(string='Record ID', index=True)
    resource_ref = fields.Reference(
        string='Record', selection='_selection_target_model',
        compute='_compute_resource_ref', inverse='_set_resource_ref', search='_search_resource_ref')
    trace_ids = fields.One2many('marketing.trace', 'participant_id', string='Actions')
    state = fields.Selection([
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('unlinked', 'Removed'),
        ], default='running', index=True, required=True,
        help='Removed means the related record does not exist anymore.')
    is_test = fields.Boolean('Test Record', default=False)

    @api.depends('model_name', 'res_id')
    def _compute_resource_ref(self):
        for participant in self:
            if participant.model_name and participant.model_name in self.env:
                participant.resource_ref = '%s,%s' % (participant.model_name, participant.res_id or 0)
            else:
                participant.resource_ref = None

    def _set_resource_ref(self):
        for participant in self:
            if participant.resource_ref:
                participant.res_id = participant.resource_ref.id

    def check_completed(self):
        existing_traces = self.env['marketing.trace'].search([
            ('participant_id', 'in', self.ids),
            ('state', '=', 'scheduled'),
        ])
        (self - existing_traces.mapped('participant_id')).write({'state': 'completed'})

    @api.model_create_multi
    def create(self, vals_list):
        participants = super().create(vals_list)
        now = Datetime.now()
        cron_trigger_dates = set()
        for res in participants:
            # prepare first traces related to begin activities
            primary_activities = res.campaign_id.marketing_activity_ids.filtered(lambda act: act.trigger_type == 'begin')
            trace_ids = [
                (0, 0, {
                    'activity_id': activity.id,
                    'schedule_date': now + relativedelta(**{activity.interval_type: activity.interval_number}),
                }) for activity in primary_activities]
            res.write({'trace_ids': trace_ids})

            cron_trigger_dates |= set([
                now + relativedelta(**{activity.interval_type: activity.interval_number})
                for activity in primary_activities
            ])

        if cron_trigger_dates:
            # based on activities with 'begin' trigger_type, we schedule CRON triggers
            # that match the scheduled_dates of created marketing.traces
            # we use a set to only trigger the CRON once per timeslot event if there are multiple
            # marketing.participants
            cron = self.env.ref('marketing_automation.ir_cron_campaign_execute_activities')
            cron._trigger(cron_trigger_dates)

        return participants

    def action_set_completed(self):
        ''' Manually mark as a completed and cancel every scheduled trace '''
        # TDE TODO: delegate set Canceled to trace record
        self.write({'state': 'completed'})
        self.env['marketing.trace'].search([
            ('participant_id', 'in', self.ids),
            ('state', '=', 'scheduled')
        ]).write({
            'state': 'canceled',
            'schedule_date': Datetime.now(),
            'state_msg': _('Marked as completed')
        })

    def action_set_running(self):
        self.write({'state': 'running'})

    def action_set_unlink(self):
        self.write({'state': 'unlinked'})
        self.env['marketing.trace'].search([
            ('participant_id', 'in', self.ids),
            ('state', '=', 'scheduled')
        ]).write({
            'state': 'canceled',
            'state_msg': _('Record deleted'),
        })
        return True
