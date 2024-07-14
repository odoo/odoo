# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.sale_subscription.models.sale_order import SUBSCRIPTION_STATES, SUBSCRIPTION_PROGRESS_STATE, SUBSCRIPTION_CLOSED_STATE
from odoo.tools.float_utils import float_is_zero


class SaleOrderLog(models.Model):
    _name = 'sale.order.log'
    _description = 'Sale Order Log'
    _order = 'event_date desc, id desc'

    order_id = fields.Many2one(
        'sale.order', string='Sale Order',
        required=True, ondelete='cascade', readonly=True,
        auto_join=True
    )
    create_date = fields.Datetime(string='Date', readonly=True)
    event_type = fields.Selection(
        string='Type of event',
        selection=[('0_creation', 'New'),
                   ('1_expansion', 'Expansion'),
                   ('15_contraction', 'Contraction'),
                   ('2_churn', 'Churn'),
                   ('3_transfer', 'Transfer')],
        required=True,
        readonly=True,
        index=True,
    )
    recurring_monthly = fields.Monetary(string='New MRR', required=True,
                                        help="MRR, after applying the changes of that particular event", readonly=True)
    subscription_state = fields.Selection(selection=SUBSCRIPTION_STATES, required=True, help="Subscription stage category when the change occurred")
    user_id = fields.Many2one('res.users', string='Salesperson')
    team_id = fields.Many2one('crm.team', string='Sales Team', ondelete="set null")
    amount_signed = fields.Monetary(index=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True)
    event_date = fields.Date(string='Event Date', required=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', related='order_id.company_id', store=True, readonly=True)
    origin_order_id = fields.Many2one('sale.order', string='Origin Contract', store=True, index=True,
                                      compute='_compute_origin_order_id')


    @api.depends('order_id')
    def _compute_origin_order_id(self):
        for log in self:
            log.origin_order_id = log.order_id.origin_order_id or log.order_id

    #######################
    #       LOG GEN       #
    #######################

    @api.model
    def _get_change_event_type(self, currency, mrr_difference):
        if currency.compare_amounts(mrr_difference, 0) <= 0:
            return '15_contraction'
        return '1_expansion'

    @api.model
    def _create_starting_transfer_log(self, values):
        event_date = fields.Date.today()
        sub = self.env['sale.order'].browse(values['order_id'])
        new_currency = sub.currency_id
        parent_currency = sub.subscription_id.currency_id
        parent_recurring_monthly = max(sub.subscription_id.recurring_monthly, 0)
        parent_mrr = parent_currency._convert(parent_recurring_monthly,
                                              to_currency=new_currency,
                                              company=sub.env.company,
                                              date=fields.Date.today(), round=False)
        parent_transfer_log = sub.subscription_id.order_log_ids.filtered(
            lambda l: l.subscription_state == '5_renewed')
        transfer_date = parent_transfer_log and parent_transfer_log.sorted('event_date')[-1].event_date or event_date
        # Creation of renewal: transfer and MRR change
        transfer_values = values.copy()
        transfer_values.update({
            'event_type': '3_transfer',
            'amount_signed': parent_mrr,
            'recurring_monthly': parent_mrr,
            'event_date': transfer_date,
        })
        log = self.sudo().create(transfer_values)
        if not float_is_zero(values['recurring_monthly'] - parent_mrr, precision_rounding=new_currency.rounding):
            values.update({
                'event_type': self._get_change_event_type(new_currency, sub.recurring_monthly - parent_mrr),
                'recurring_monthly': values['recurring_monthly'],
                'amount_signed': values['recurring_monthly'] - parent_mrr,
                'event_date': transfer_date,
            })
            self.sudo().create(values)
        return log

    @api.model
    def _create_reopen_log(self, values):
        # We reopened a churned contract. We delete the churn log to keep the formal MRR.
        sub = self.env['sale.order'].browse(values['order_id'])
        churn_logs = sub.order_log_ids.filtered(lambda log: log.event_type == '2_churn').sorted('event_date', reverse=True)
        churn_log = churn_logs[:1]
        previous_mrr = 0
        if churn_log:
            previous_mrr = - churn_log.amount_signed
            churn_log.unlink()
        mrr_difference = values['recurring_monthly']  - previous_mrr # arj todo reopen with negative values
        if not float_is_zero(mrr_difference, precision_rounding=sub.currency_id.rounding):
            values.update({
                'event_type': self._get_change_event_type(sub.currency_id, mrr_difference),
                'amount_signed': mrr_difference,
            })
            return self.sudo().create(values)

    @api.model
    def _create_mrr_log(self, values, initial_values):
        sub = self.env['sale.order'].browse(values['order_id'])
        if sub.subscription_state not in SUBSCRIPTION_PROGRESS_STATE:
            return
        mrr_difference = values.get('amount_signed', 0)
        if sub.origin_order_id: # Is a confirmed renewal ( origin_order_id and category in progress)
            existing_transfer_log = sub.order_log_ids.filtered(lambda ev: ev.event_type == '3_transfer')
            # Warning, sometimes we don't have transfer log but we have similar log:
            # new or expansion going from 0 to RM. We don't want to create transfer in that case.
            similar_log = sub.order_log_ids.filtered(lambda ev: ev.amount_signed == ev.recurring_monthly)
            if not existing_transfer_log and not similar_log and sub.subscription_id.subscription_state == '5_renewed':
                return self._create_starting_transfer_log(values.copy())

        if not float_is_zero(mrr_difference, precision_rounding=sub.currency_id.rounding):
            values.update({'amount_signed': mrr_difference,
                           'recurring_monthly': values['recurring_monthly']})
            if sub.order_log_ids:
                # Simple contraction or extension
                values['event_type'] = self._get_change_event_type(sub.currency_id, mrr_difference)
            else:
                order_start_date = sub.start_date or fields.Date.today()
                values.update({'event_type': '0_creation',
                               'event_date': min(fields.Date.today(), order_start_date)})
            return self.sudo().create(values)

    def _create_stage_log(self, values, initial_values):
        old_state = initial_values['subscription_state']
        new_state = values['subscription_state']
        values['event_date'] = fields.Date.today()
        if not (old_state not in SUBSCRIPTION_PROGRESS_STATE and new_state in SUBSCRIPTION_PROGRESS_STATE) and \
            not (old_state not in SUBSCRIPTION_CLOSED_STATE and new_state in SUBSCRIPTION_CLOSED_STATE):
            return
        # subscription started, churned or transferred to renew
        sub = self.env['sale.order'].browse(values['order_id'])
        if new_state in SUBSCRIPTION_PROGRESS_STATE:
            if old_state == '6_churn':
                # We reopened a churned contract. We delete the churn log to keep the formal MRR.
                return self._create_reopen_log(values)
            if sub.subscription_id and sub.subscription_id.subscription_state != '6_churn':
                # Changed order, old order may create error for reopen renewal
                # Transfer for the renewed value and MRR change for the rest
                return self._create_starting_transfer_log(values)
            else:
                values['event_type'] = '0_creation'
                return self.sudo().create(values)
        else:
            # Closing a subscription: transfer or churn
            if sub.subscription_child_ids.filtered(lambda s: s.subscription_state == '3_progress'):
                values['event_type'] = '3_transfer'
            else:
                values['event_type'] = '2_churn'
                # All logs are stacked today. In the future, there should not be any log in the future
                event_date = fields.Date.today()
                sub.order_log_ids.filtered(lambda l: l.event_date > event_date).event_date = event_date
            return self.sudo().create(values)

    @api.model
    def _create_log(self, values, initial_values):
        log = None
        initial_state = initial_values.get('subscription_state')
        if initial_state and initial_state != values.get('subscription_state'):
            log = self._create_stage_log(values.copy(), initial_values)
        if not log and values.get('amount_signed') and initial_state != '6_churn':  # If we reopen, we don't want addition mrr log
            log = self._create_mrr_log(values.copy(), initial_values)
        return log
