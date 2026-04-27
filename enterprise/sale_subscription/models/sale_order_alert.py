# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, Command, fields, models, _
from odoo.addons.sale.models.sale_order import SALE_ORDER_STATE


class BaseAutomation(models.Model):
    _inherit = 'base.automation'

    is_sale_order_alert = fields.Boolean(readonly=True, default=False, copy=False, string='Is Sale Order Alert')


class SaleOrderAlert(models.Model):
    _name = 'sale.order.alert'
    _description = 'Sale Order Alert'
    _inherits = {'base.automation': 'automation_id'}
    _check_company_auto = True

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        if 'model_id' in default_fields:
            # model_id default cannot be specified at field level
            # because model_id is an inherited field from base.automation
            res['model_id'] = self.env['ir.model']._get_id('sale.order')
        return res

    automation_id = fields.Many2one('base.automation', 'Automation Rule', required=True, ondelete='restrict')
    action_id = fields.Many2one('ir.actions.server', string='Server Action', ondelete='restrict')

    template_id = fields.Many2one(related='action_id.template_id', readonly=False)
    sms_template_id = fields.Many2one(related='action_id.sms_template_id', readonly=False)
    activity_type_id = fields.Many2one(related='action_id.activity_type_id', readonly=False)
    activity_summary = fields.Char(related='action_id.activity_summary', readonly=False)
    activity_note = fields.Html(related='action_id.activity_note', readonly=False)
    activity_date_deadline_range = fields.Integer(related='action_id.activity_date_deadline_range', readonly=False)
    activity_date_deadline_range_type = fields.Selection(related='action_id.activity_date_deadline_range_type', readonly=False)
    activity_user_id = fields.Many2one(related='action_id.activity_user_id', readonly=False)

    action = fields.Selection([
        ('next_activity', 'Create next activity'),
        ('mail_post', 'Send an email to the customer'),
        ('sms', 'Send an SMS Text Message to the customer'),
        ('set_health_value', 'Set Contract Health value')
    ], string='Action To Do', required=True, default=None)
    trigger_condition = fields.Selection([
        ('on_create_or_write', 'Modification'), ('on_time', 'Timed Condition')], string='Trigger On', required=True, default='on_create_or_write')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    subscription_plan_ids = fields.Many2many('sale.subscription.plan', string='Subscription Plans', check_company=True)
    customer_ids = fields.Many2many('res.partner', string='Customers')
    company_id = fields.Many2one('res.company', string='Company')
    mrr_min = fields.Monetary('MRR Range Min', currency_field='currency_id')
    team_ids = fields.Many2many('crm.team', string='Sales Team')
    mrr_max = fields.Monetary('MRR Range Max', currency_field='currency_id')
    product_ids = fields.Many2many(
        'product.product', string='Specific Products',
        check_company=True,
        domain="[('product_tmpl_id.recurring_invoice', '=', True)]")
    mrr_change_amount = fields.Float('MRR Change Amount')
    mrr_change_unit = fields.Selection(selection='_get_selection_mrr_change_unit', string='MRR Change Unit', default='percentage')
    mrr_change_period = fields.Selection([('1month', '1 Month'), ('3months', '3 Months')], string='MRR Change Period',
                                         default='1month', help="Period over which the KPI is calculated")
    rating_percentage = fields.Integer('Rating Percentage', help="Rating Satisfaction is the ratio of positive rating to total number of rating.")
    rating_operator = fields.Selection([('>', 'greater than'), ('<', 'less than')], string='Rating Operator', default='>')
    subscription_state_from = fields.Selection(
        string='Stage from',
        selection=[
            ('1_draft', 'Quotation'),     # Quotation for a new subscription
            ('3_progress', 'In Progress'),    # Active Subscription or confirmed renewal for active subscription
            ('6_churn', 'Churned'),           # Closed or ended subscription
            ('2_renewal', 'Renewal Quotation'),         # Renewal Quotation for existing subscription
            ('5_renewed', 'Renewed'),         # Active or ended subscription that has been renewd
            ('4_paused', 'Paused'),           # Active subcription with paused invoicing
            ('7_upsell', 'Upsell'),           # Quotation or SO upselling a subscription
        ]
    )

    subscription_state = fields.Selection(
        string='Stage',
        selection=[
            ('1_draft', 'Quotation'),     # Quotation for a new subscription
            ('3_progress', 'In Progress'),    # Active Subscription or confirmed renewal for active subscription
            ('6_churn', 'Churned'),           # Closed or ended subscription
            ('2_renewal', 'Renewal Quotation'),         # Renewal Quotation for existing subscription
            ('5_renewed', 'Renewed'),         # Active or ended subscription that has been renewd
            ('4_paused', 'Paused'),           # Active subcription with paused invoicing
            ('7_upsell', 'Upsell'),           # Quotation or SO upselling a subscription
        ]
    )
    order_state = fields.Selection(selection=SALE_ORDER_STATE, string="Status")
    activity_user = fields.Selection([
        ('contract', 'Subscription Salesperson'),
        ('channel_leader', 'Sales Team Leader'),
        ('users', 'Specific Users'),
    ], string='Assign To')
    activity_user_ids = fields.Many2many('res.users', string='Specific Users')
    subscription_count = fields.Integer(compute='_compute_subscription_count')
    cron_nextcall = fields.Datetime(compute='_compute_nextcall', store=False)
    health = fields.Selection([('normal', 'Neutral'), ('done', 'Good'), ('bad', 'Bad')], string="Health", help="Show the health status")

    @api.onchange('trigger_condition', 'automation_id')
    def _onchange_automation_trigger(self):
        # This method is needed to force saving the automation_id.trigger according to trigger_condition value
        # Overriding create/write does is not sufficient anymore as the automation_id.trg_date_range_type is
        # evaluated before calling super/write.
        for alert in self:
            alert.automation_id.trigger = alert.trigger_condition

    def _get_action_activity_values(self):
        if self.activity_user == 'users':
            action_commands = [Command.create({
                'name': '%s-%s' % (self.name, seq),
                'sequence': seq,
                'state': 'next_activity',
                'model_id': self.model_id.id,
                'activity_summary': self.activity_summary,
                'activity_type_id': self.activity_type_id.id,
                'activity_note': self.activity_note,
                'activity_date_deadline_range': self.activity_date_deadline_range,
                'activity_date_deadline_range_type': self.activity_date_deadline_range_type,
                'activity_user_type': 'specific',
                'activity_user_id': user.id,
                'usage': 'base_automation',
            }) for seq, user in enumerate(self.activity_user_ids, 1)]
            return {
                'state': 'multi',
                'child_ids': action_commands
            }
        elif self.activity_user == 'contract':
            return {
                'state': 'next_activity',
                'activity_user_type': 'generic',
                'activity_user_field_name': 'user_id',
            }
        elif self.activity_user == 'channel_leader':
            return {
                'state': 'next_activity',
                'activity_user_type': 'generic',
                'activity_user_field_name': 'team_user_id',
            }

    def _get_alert_domain(self):
        domain = [('is_subscription', '=', True)]
        if self.subscription_plan_ids:
            domain += [('plan_id', 'in', self.subscription_plan_ids.ids)]
        if self.customer_ids:
            domain += [('partner_id', 'in', self.customer_ids.ids)]
        if self.team_ids:
            domain += [('team_id', 'in', self.team_ids.ids)]
        if self.company_id:
            domain += [('company_id', '=', self.company_id.id)]
        if self.mrr_min:
            domain += [('recurring_monthly', '>=', self.mrr_min)]
        if self.mrr_max:
            domain += [('recurring_monthly', '<=', self.mrr_max)]
        if self.product_ids:
            domain += [('order_line.product_id', 'in', self.product_ids.ids)]
        if self.mrr_change_amount:
            if self.mrr_change_unit == 'percentage':
                domain += [('kpi_%s_mrr_percentage' % self.mrr_change_period, '>', self.mrr_change_amount / 100)]
            else:
                domain += [('kpi_%s_mrr_delta' % self.mrr_change_period, '>', self.mrr_change_amount)]
        if self.rating_percentage:
            domain += [('percentage_satisfaction', self.rating_operator, self.rating_percentage)]
        if self.subscription_state:
            domain += [('subscription_state', '=', self.subscription_state)]
        elif self.subscription_state_from:
            domain += [('subscription_state', '!=', self.subscription_state_from)]
        if self.order_state:
            domain += [('state', '=', self.order_state)]
        return domain

    def _get_selection_mrr_change_unit(self):
        return [('percentage', '%'), ('currency', self.env.company.currency_id.symbol)]

    def _compute_subscription_count(self):
        for alert in self:
            domain = literal_eval(alert.filter_domain) if alert.filter_domain else []
            alert.subscription_count = self.env['sale.order'].search_count(domain)

    def _get_action_template_values(self):
        self.ensure_one()
        if self.action == 'mail_post':
            return {'template_id': self.template_id.id}
        elif self.action == 'sms':
            return {'sms_template_id': self.sms_template_id.id}
        elif self.action == 'next_activity':
            return {
                'activity_type_id': self.activity_type_id and self.activity_type_id.id,
                'activity_summary': self.activity_summary,
                'activity_note': self.activity_note,
                'activity_date_deadline_range': self.activity_date_deadline_range,
                'activity_date_deadline_range_type': self.activity_date_deadline_range_type,
                'activity_user_id': self.activity_user_id and self.activity_user_id.id,
            }
        return {}

    def _create_actions(self):
        action_values = [{
            'name': alert.name,
            'usage': 'base_automation',
            'model_id': alert.model_id.id,
            'base_automation_id': alert.automation_id.id,
            **alert._get_action_template_values()
        } for alert in self]

        actions = self.env['ir.actions.server'].create(action_values)

        for alert, action in zip(self, actions):
            alert.action_id = action
            alert.action_server_ids = [action.id]

    def _configure_alerts(self, vals_list):
        # Unlink the children server actions if not needed anymore
        self.filtered(lambda alert: alert.action != 'next_activity' and alert.action_id.child_ids).action_id.child_ids.unlink()

        field_names = ['subscription_state', 'health']
        tag_fields = self.env['ir.model.fields'].search([('model', 'in', self.mapped('model_name')), ('name', 'in', field_names)])

        for alert, vals in zip(self, vals_list):
            # Configure alert
            alert_values = {}
            if not vals.get('filter_domain'):
                alert_values['filter_domain'] = alert._get_alert_domain()
            if not vals.get('filter_pre_domain'):
                if alert.subscription_state_from:
                    alert_values['filter_pre_domain'] = [('subscription_state', '=', alert.subscription_state_from)]
                elif alert.subscription_state:
                    alert_values['filter_pre_domain'] = [('subscription_state', '!=', alert.subscription_state)]
                else:
                    alert_values['filter_pre_domain'] = []
            if alert_values:
                alert.with_context(skip_configure_alerts=True).write(alert_values)

            # Configure action
            action_values = {}
            field_name = None
            if alert.action == 'subscription_state' and alert.subscription_state:
                field_name = 'subscription_state'
                action_values['selection_value'] = alert.subscription_state
            elif alert.action == 'set_health_value' and alert.health:
                field_name = 'health'
                action_values['value'] = alert.health

            if field_name:
                tag_field = tag_fields.filtered(lambda t: t.name == field_name)
                action_values['state'] = 'object_write'
                action_values['update_path'] = tag_field.name
                action_values['evaluation_type'] = 'value'
            elif vals.get('action') in ('mail_post', 'sms'):
                action_values['state'] = vals['action']
            elif vals.get('action') == 'next_activity' or vals.get('activity_user_ids') or vals.get('activity_user'):
                self.action_id.child_ids.unlink()
                action_values = alert._get_action_activity_values()

            if action_values:
                alert.action_id.write(action_values)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['is_sale_order_alert'] = True
            if vals.get('trigger_condition'):
                vals['trigger'] = vals['trigger_condition']
        alerts = super().create(vals_list)
        alerts._create_actions()
        alerts._configure_alerts(vals_list)
        return alerts

    def write(self, vals):
        if vals.get('trigger_condition'):
            vals['trigger'] = vals['trigger_condition']
        res = super().write(vals)
        if not self._context.get('skip_configure_alerts'):
            self._configure_alerts([vals])
        return res

    def unlink(self):
        self.automation_id.active = False
        return super().unlink()

    def action_view_subscriptions(self):
        self.ensure_one()
        domain = literal_eval(self.filter_domain) if self.filter_domain else [('is_subscription', '=', True)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions'),
            'res_model': 'sale.order',
            'view_mode': 'kanban,list,form,pivot,graph,cohort,activity',
            'domain': domain,
            'context': {'create': False},
        }

    def run_cron_manually(self):
        self.ensure_one()
        domain = literal_eval(self.filter_domain)
        subs = self.env['sale.order'].search(domain)
        ctx = {
            'active_model': 'sale.order',
            'active_ids': subs.ids,
            'domain_post': domain,
        }
        for action_server in self.action_server_ids.with_context(**ctx):
            action_server.run()

    def _compute_nextcall(self):
        cron = self.env.ref('sale_subscription.ir_cron_sale_subscription_update_kpi', raise_if_not_found=False)
        self.cron_nextcall = cron.nextcall if cron else False
