# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from traceback import format_exception
from sys import exc_info

import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

import odoo.addons.decimal_precision as dp

_intervalTypes = {
    'hours': lambda interval: relativedelta(hours=interval),
    'days': lambda interval: relativedelta(days=interval),
    'months': lambda interval: relativedelta(months=interval),
    'years': lambda interval: relativedelta(years=interval),
}


class MarketingCampaign(models.Model):
    _name = "marketing.campaign"
    _description = "Marketing Campaign"

    name = fields.Char('Name', required=True)
    object_id = fields.Many2one('ir.model', 'Resource', required=True,
        help="Choose the resource on which you want this campaign to be run")
    partner_field_id = fields.Many2one('ir.model.fields', 'Partner Field',
        domain="[('model_id', '=', object_id), ('ttype', '=', 'many2one'), ('relation', '=', 'res.partner')]",
        help="The generated workitems will be linked to the partner related to the record. "
             "If the record is the partner itself leave this field empty. "
             "This is useful for reporting purposes, via the Campaign Analysis or Campaign Follow-up views.")
    unique_field_id = fields.Many2one('ir.model.fields', 'Unique Field',
        domain="[('model_id', '=', object_id), ('ttype', 'in', ['char','int','many2one','text','selection'])]",
        help='If set, this field will help segments that work in "no duplicates" mode to avoid '
             'selecting similar records twice. Similar records are records that have the same value for '
             'this unique field. For example by choosing the "email_from" field for CRM Leads you would prevent '
             'sending the same campaign to the same email address again. If not set, the "no duplicates" segments '
             "will only avoid selecting the same record again if it entered the campaign previously. "
             "Only easily comparable fields like textfields, integers, selections or single relationships may be used.")
    mode = fields.Selection([
        ('test', 'Test Directly'),
        ('test_realtime', 'Test in Realtime'),
        ('manual', 'With Manual Confirmation'),
        ('active', 'Normal')
        ], 'Mode', required=True, default="test",
        help="Test - It creates and process all the activities directly (without waiting "
             "for the delay on transitions) but does not send emails or produce reports. \n"
             "Test in Realtime - It creates and processes all the activities directly but does "
             "not send emails or produce reports.\n"
             "With Manual Confirmation - the campaigns runs normally, but the user has to \n "
             "validate all workitem manually.\n"
             "Normal - the campaign runs normally and automatically sends all emails and "
             "reports (be very careful with this mode, you're live!)")
    state = fields.Selection([
        ('draft', 'New'),
        ('running', 'Running'),
        ('cancelled', 'Cancelled'),
        ('done', 'Done')
        ], 'Status', copy=False, default="draft")
    activity_ids = fields.One2many('marketing.campaign.activity', 'campaign_id', 'Activities')
    fixed_cost = fields.Float('Fixed Cost',
        help="Fixed cost for running this campaign. You may also specify variable cost and revenue on each "
             "campaign activity. Cost and Revenue statistics are included in Campaign Reporting.",
        digits=dp.get_precision('Product Price'))
    segment_ids = fields.One2many('marketing.campaign.segment', 'campaign_id', 'Segments', readonly=False)
    segments_count = fields.Integer(compute='_compute_segments_count', string='Segments')

    @api.multi
    def _compute_segments_count(self):
        for campaign in self:
            campaign.segments_count = len(campaign.segment_ids)

    @api.multi
    def state_draft_set(self):
        return self.write({'state': 'draft'})

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
            if activity.signal and len(activity.from_ids) == 0:
                has_signal_without_from = True

        if not has_start and not has_signal_without_from:
            raise UserError(_("The campaign cannot be started. It does not have any starting activity. Modify campaign's activities to mark one as the starting point."))

        return self.write({'state': 'running'})

    @api.multi
    def state_done_set(self):
        # TODO check that this campaign is not a subcampaign in running mode.
        if self.mapped('segment_ids').filtered(lambda segment: segment.state == 'running'):
            raise UserError(_("The campaign cannot be marked as done before all segments are closed."))
        return self.write({'state': 'done'})

    @api.multi
    def state_cancel_set(self):
        # TODO check that this campaign is not a subcampaign in running mode.
        return self.write({'state': 'cancelled'})

    def _get_partner_for(self, record):
        partner_field = self.partner_field_id.name
        if partner_field:
            return record[partner_field]
        elif self.object_id.model == 'res.partner':
            return record
        return None

    # prevent duplication until the server properly duplicates several levels of nested o2m
    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        raise UserError(_('Duplicating campaigns is not supported.'))

    def _find_duplicate_workitems(self, record):
        """Finds possible duplicates workitems for a record in this campaign, based on a uniqueness
           field.

           :param record: browse_record to find duplicates workitems for.
           :param campaign_rec: browse_record of campaign
        """
        self.ensure_one()
        duplicate_workitem_domain = [('res_id', '=', record.id), ('campaign_id', '=', self.id)]
        unique_field = self.unique_field_id
        if unique_field:
            unique_value = getattr(record, unique_field.name, None)
            if unique_value:
                if unique_field.ttype == 'many2one':
                    unique_value = unique_value.id
                similar_res_ids = self.env[self.object_id.model].search([(unique_field.name, '=', unique_value)])
                if similar_res_ids:
                    duplicate_workitem_domain = [
                        ('res_id', 'in', similar_res_ids.ids),
                        ('campaign_id', '=', self.id)
                    ]
        return self.env['marketing.campaign.workitem'].search(duplicate_workitem_domain)


class MarketingCampaignSegment(models.Model):
    _name = "marketing.campaign.segment"
    _description = "Campaign Segment"
    _order = "name"

    name = fields.Char('Name', required=True)
    campaign_id = fields.Many2one('marketing.campaign', 'Campaign', required=True, index=True, ondelete="cascade")
    object_id = fields.Many2one('ir.model', related='campaign_id.object_id', string='Resource')
    ir_filter_id = fields.Many2one('ir.filters', 'Filter', ondelete="restrict",
        domain=lambda self: [('model_id', '=', self.object_id._name)],
        help="Filter to select the matching resource records that belong to this segment. "
             "New filters can be created and saved using the advanced search on the list view of the Resource. "
             "If no filter is set, all records are selected without filtering. "
             "The synchronization mode may also add a criterion to the filter.")
    sync_last_date = fields.Datetime('Last Synchronization',
        help="Date on which this segment was synchronized last time (automatically or manually)")
    sync_mode = fields.Selection([
        ('create_date', 'Only records created after last sync'),
        ('write_date', 'Only records modified after last sync (no duplicates)'),
        ('all', 'All records (no duplicates)')],
        'Synchronization mode', default='create_date',
        help="Determines an additional criterion to add to the filter when selecting new records to inject in the campaign. "
             '"No duplicates" prevents selecting records which have already entered the campaign previously.'
             'If the campaign has a "unique field" set, "no duplicates" will also prevent selecting records which have '
             'the same value for the unique field as other records that already entered the campaign.')
    state = fields.Selection([
        ('draft', 'New'),
        ('cancelled', 'Cancelled'),
        ('running', 'Running'),
        ('done', 'Done')],
        'Status', copy=False, default='draft')
    date_run = fields.Datetime('Launch Date', help="Initial start date of this segment.")
    date_done = fields.Datetime('End Date', help="Date this segment was last closed or cancelled.")
    date_next_sync = fields.Datetime(compute='_compute_date_next_sync', string='Next Synchronization',
        help="Next time the synchronization job is scheduled to run automatically")

    def _compute_date_next_sync(self):
        # next auto sync date is same for all segments
        sync_job = self.sudo().env.ref('marketing_campaign.ir_cron_marketing_campaign_every_day')
        self.date_next_sync = sync_job and sync_job.nextcall or False

    @api.constrains('ir_filter_id', 'campaign_id')
    def _check_model(self):
        if self.filtered(lambda segment: segment.ir_filter_id and
                segment.campaign_id.object_id.model != segment.ir_filter_id.model_id):
            raise ValidationError(_('Model of filter must be same as resource model of Campaign'))

    @api.onchange('campaign_id')
    def onchange_campaign_id(self):
        res = {'domain': {'ir_filter_id': []}}
        model = self.campaign_id.object_id.model
        if model:
            res['domain']['ir_filter_id'] = [('model_id', '=', model)]
        else:
            self.ir_filter_id = False
        return res

    @api.multi
    def state_draft_set(self):
        return self.write({'state': 'draft'})

    @api.multi
    def state_running_set(self):
        self.ensure_one()
        vals = {'state': 'running'}
        if not self.date_run:
            vals['date_run'] = fields.Datetime.now()
        return self.write(vals)

    @api.multi
    def state_done_set(self):
        self.env["marketing.campaign.workitem"].search([
            ('state', '=', 'todo'),
            ('segment_id', 'in', self.ids)
        ]).write({'state': 'cancelled'})
        return self.write({'state': 'done', 'date_done': fields.Datetime.now()})

    @api.multi
    def state_cancel_set(self):
        self.env["marketing.campaign.workitem"].search([
            ('state', '=', 'todo'),
            ('segment_id', 'in', self.ids)
        ]).write({'state': 'cancelled'})
        return self.write({'state': 'cancelled', 'date_done': fields.Datetime.now()})

    @api.multi
    def process_segment(self):
        Workitems = self.env['marketing.campaign.workitem']
        Activities = self.env['marketing.campaign.activity']
        if not self:
            self = self.search([('state', '=', 'running')])

        action_date = fields.Datetime.now()
        campaigns = self.env['marketing.campaign']
        for segment in self:
            if segment.campaign_id.state != 'running':
                continue

            campaigns |= segment.campaign_id
            activity_ids = Activities.search([('start', '=', True), ('campaign_id', '=', segment.campaign_id.id)]).ids

            criteria = []
            if segment.sync_last_date and segment.sync_mode != 'all':
                criteria += [(segment.sync_mode, '>', segment.sync_last_date)]
            if segment.ir_filter_id:
                criteria += safe_eval(segment.ir_filter_id.domain)

            # XXX TODO: rewrite this loop more efficiently without doing 1 search per record!
            for record in self.env[segment.object_id.model].search(criteria):
                # avoid duplicate workitem for the same resource
                if segment.sync_mode in ('write_date', 'all'):
                    if segment.campaign_id._find_duplicate_workitems(record):
                        continue

                wi_vals = {
                    'segment_id': segment.id,
                    'date': action_date,
                    'state': 'todo',
                    'res_id': record.id
                }

                partner = segment.campaign_id._get_partner_for(record)
                if partner:
                    wi_vals['partner_id'] = partner.id

                for activity_id in activity_ids:
                    wi_vals['activity_id'] = activity_id
                    Workitems.create(wi_vals)

            segment.write({'sync_last_date': action_date})
        Workitems.process_all(campaigns.ids)
        return True


class MarketingCampaignActivity(models.Model):
    _name = "marketing.campaign.activity"
    _order = "name"
    _description = "Campaign Activity"

    name = fields.Char('Name', required=True)
    campaign_id = fields.Many2one('marketing.campaign', 'Campaign', required=True, ondelete='cascade', index=True)
    object_id = fields.Many2one(related='campaign_id.object_id', relation='ir.model', string='Object', readonly=True)
    start = fields.Boolean('Start', help="This activity is launched when the campaign starts.", index=True)
    condition = fields.Text('Condition', required=True, default="True",
        help="Python expression to decide whether the activity can be executed, otherwise it will be deleted or cancelled."
        "The expression may use the following [browsable] variables:\n"
        "   - activity: the campaign activity\n"
        "   - workitem: the campaign workitem\n"
        "   - resource: the resource object this campaign item represents\n"
        "   - transitions: list of campaign transitions outgoing from this activity\n"
        "...- re: Python regular expression module")
    action_type = fields.Selection([
        ('email', 'Email'),
        ('report', 'Report'),
        ('action', 'Custom Action'),
    ], 'Type', required=True, oldname="type", default="email",
        help="The type of action to execute when an item enters this activity, such as:\n"
             "- Email: send an email using a predefined email template \n"
             "- Report: print an existing Report defined on the resource item and save it into a specific directory \n"
             "- Custom Action: execute a predefined action, e.g. to modify the fields of the resource record")
    email_template_id = fields.Many2one('mail.template', "Email Template", help='The email to send when this activity is activated')
    report_id = fields.Many2one('ir.actions.report.xml', "Report", help='The report to generate when this activity is activated')
    server_action_id = fields.Many2one('ir.actions.server', string='Action',
        help="The action to perform when this activity is activated")
    to_ids = fields.One2many('marketing.campaign.transition', 'activity_from_id', 'Next Activities')
    from_ids = fields.One2many('marketing.campaign.transition', 'activity_to_id', 'Previous Activities')
    variable_cost = fields.Float('Variable Cost', digits=dp.get_precision('Product Price'),
        help="Set a variable cost if you consider that every campaign item that has reached this point has entailed a "
             "certain cost. You can get cost statistics in the Reporting section")
    revenue = fields.Float('Revenue', digits=0,
        help="Set an expected revenue if you consider that every campaign item that has reached this point has generated "
             "a certain revenue. You can get revenue statistics in the Reporting section")
    signal = fields.Char('Signal',
        help="An activity with a signal can be called programmatically. Be careful, the workitem is always created when "
             "a signal is sent")
    keep_if_condition_not_met = fields.Boolean("Don't Delete Workitems",
        help="By activating this option, workitems that aren't executed because the condition is not met are marked as "
             "cancelled instead of being deleted.")

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if 'segment_id' in self.env.context:
            return self.env['marketing.campaign.segment'].browse(self.env.context['segment_id']).campaign_id.activity_ids
        return super(MarketingCampaignActivity, self).search(args, offset, limit, order, count)

    @api.multi
    def _process_wi_email(self, workitem):
        self.ensure_one()
        return self.email_template_id.send_mail(workitem.res_id)

    @api.multi
    def process(self, workitem):
        self.ensure_one()
        method = '_process_wi_%s' % (self.action_type,)
        action = getattr(self, method, None)
        if not action:
            raise NotImplementedError('Method %r is not implemented on %r object.' % (method, self._name))
        return action(workitem)


class MarketingCampaignTransition(models.Model):
    _name = "marketing.campaign.transition"
    _description = "Campaign Transition"

    _interval_units = [
        ('hours', 'Hour(s)'),
        ('days', 'Day(s)'),
        ('months', 'Month(s)'),
        ('years', 'Year(s)'),
    ]

    name = fields.Char(compute='_compute_name', string='Name')
    activity_from_id = fields.Many2one('marketing.campaign.activity', 'Previous Activity', index=1, required=True, ondelete="cascade")
    activity_to_id = fields.Many2one('marketing.campaign.activity', 'Next Activity', required=True, ondelete="cascade")
    interval_nbr = fields.Integer('Interval Value', required=True, default=1)
    interval_type = fields.Selection(_interval_units, 'Interval Unit', required=True, default='days')
    trigger = fields.Selection([
        ('auto', 'Automatic'),
        ('time', 'Time'),
        ('cosmetic', 'Cosmetic'),  # fake plastic transition
        ], 'Trigger', required=True, default='time',
        help="How is the destination workitem triggered")

    _sql_constraints = [
        ('interval_positive', 'CHECK(interval_nbr >= 0)', 'The interval must be positive or zero')
    ]

    def _compute_name(self):
        # name formatters that depend on trigger
        formatters = {
            'auto': _('Automatic transition'),
            'time': _('After %(interval_nbr)d %(interval_type)s'),
            'cosmetic': _('Cosmetic'),
        }
        # get the translations of the values of selection field 'interval_type'
        model_fields = self.fields_get(['interval_type'])
        interval_type_selection = dict(model_fields['interval_type']['selection'])

        for transition in self:
            values = {
                'interval_nbr': transition.interval_nbr,
                'interval_type': interval_type_selection.get(transition.interval_type, ''),
            }
            transition.name = formatters[transition.trigger] % values

    @api.constrains('activity_from_id', 'activity_to_id')
    def _check_campaign(self):
        if self.filtered(lambda transition: transition.activity_from_id.campaign_id != transition.activity_to_id.campaign_id):
            return ValidationError(_('The To/From Activity of transition must be of the same Campaign'))

    def _delta(self):
        self.ensure_one()
        if self.trigger != 'time':
            raise ValueError('Delta is only relevant for timed transition.')
        return relativedelta(**{str(self.interval_type): self.interval_nbr})


class MarketingCampaignWorkitem(models.Model):
    _name = "marketing.campaign.workitem"
    _description = "Campaign Workitem"

    segment_id = fields.Many2one('marketing.campaign.segment', 'Segment', readonly=True)
    activity_id = fields.Many2one('marketing.campaign.activity', 'Activity', required=True, readonly=True)
    campaign_id = fields.Many2one('marketing.campaign', related='activity_id.campaign_id', string='Campaign', readonly=True, store=True)
    object_id = fields.Many2one('ir.model', related='activity_id.campaign_id.object_id', string='Resource', index=1, readonly=True, store=True)
    res_id = fields.Integer('Resource ID', index=1, readonly=True)
    res_name = fields.Char(compute='_compute_res_name', string='Resource Name', search='search_res_name')
    date = fields.Datetime('Execution Date', readonly=True, default=False,
        help='If date is not set, this workitem has to be run manually')
    partner_id = fields.Many2one('res.partner', 'Partner', index=1, readonly=True)
    state = fields.Selection([
        ('todo', 'To Do'),
        ('cancelled', 'Cancelled'),
        ('exception', 'Exception'),
        ('done', 'Done'),
        ], 'Status', readonly=True, copy=False, default='todo')
    error_msg = fields.Text('Error Message', readonly=True)

    def _compute_res_name(self):
        for workitem in self:
            proxy = self.env[workitem.object_id.model]
            record = proxy.browse(workitem.res_id)
            if not workitem.res_id or not record:
                workitem.res_name = '/'
                continue
            workitem.res_name = record.name_get()[0][1]

    def _search_res_name(self, operator, operand):
        """Returns a domain with ids of workitem whose `operator` matches  with the given `operand`"""
        if not operand:
            return []

        condition_name = [None, operator, operand]

        self.env.cr.execute("""
            SELECT w.id, w.res_id, m.model
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
            for record in Model.search(condition):
                matching_workitems.extend(id_map[record.id])
        return [('id', 'in', list(set(matching_workitems)))]

    @api.multi
    def button_draft(self):
        return self.filtered(lambda workitem: workitem.state in ('exception', 'cancelled')).write({'state': 'todo'})

    @api.multi
    def button_cancel(self):
        return self.filtered(lambda workitem: workitem.state in ('todo', 'exception')).write({'state': 'cancelled'})

    @api.multi
    def _process_one(self):
        self.ensure_one()
        if self.state != 'todo':
            return False

        activity = self.activity_id
        resource = self.env[self.object_id.model].browse(self.res_id)

        eval_context = {
            'activity': activity,
            'workitem': self,
            'object': resource,
            'resource': resource,
            'transitions': activity.to_ids,
            're': re,
        }
        try:
            condition = activity.condition
            campaign_mode = self.campaign_id.mode
            if condition:
                if not safe_eval(condition, eval_context):
                    if activity.keep_if_condition_not_met:
                        self.write({'state': 'cancelled'})
                    else:
                        self.unlink()
                    return
            result = True
            if campaign_mode in ('manual', 'active'):
                result = activity.process(self)

            values = {'state': 'done'}
            if not self.date:
                values['date'] = fields.Datetime.now()
            self.write(values)

            if result:
                # process _chain
                self.refresh()  # reload
                execution_date = fields.Datetime.from_string(self.date)

                for transition in activity.to_ids:
                    if transition.trigger == 'cosmetic':
                        continue
                    launch_date = False
                    if transition.trigger == 'auto':
                        launch_date = execution_date
                    elif transition.trigger == 'time':
                        launch_date = execution_date + transition._delta()

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
                    workitem = self.create(values)

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

                    run = (transition.trigger == 'auto' and campaign_mode != 'manual') or (transition.trigger == 'time' and campaign_mode == 'test')
                    if run:
                        workitem._process_one()

        except Exception:
            tb = "".join(format_exception(*exc_info()))
            self.write({'state': 'exception', 'error_msg': tb})

    @api.multi
    def process(self):
        for workitem in self:
            workitem._process_one()
        return True

    @api.model
    def process_all(self, camp_ids=None):
        if camp_ids is None:
            campaigns = self.env['marketing.campaign'].search([('state', '=', 'running')])
        else:
            campaigns = self.env['marketing.campaign'].browse(camp_ids)
        for campaign in campaigns.filtered(lambda campaign: campaign.mode != 'manual'):
            while True:
                domain = [('campaign_id', '=', campaign.id), ('state', '=', 'todo'), ('date', '!=', False)]
                if campaign.mode in ('test_realtime', 'active'):
                    domain += [('date', '<=', fields.Datetime.now())]
                workitems = self.search(domain)
                if not workitems:
                    break
                workitems.process()
        return True

    @api.multi
    def preview(self):
        self.ensure_one()
        res = {}
        if self.activity_id.action_type == 'email':
            view_ref = self.env.ref('mail.email_template_preview_form')
            res = {
                'name': _('Email Preview'),
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'email_template.preview',
                'view_id': False,
                'context': self.env.context,
                'views': [(view_ref and view_ref.id or False, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': "{'template_id': %d,'default_res_id': %d}" % (self.activity_id.email_template_id.id, self.res_id)
            }

        elif self.activity_id.action_type == 'report':
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
            raise UserError(_('The current step for this item has no email or report to preview.'))
        return res
