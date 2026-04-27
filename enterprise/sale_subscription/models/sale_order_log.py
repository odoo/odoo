# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.addons.sale_subscription.models.sale_order import SUBSCRIPTION_STATES, SUBSCRIPTION_PROGRESS_STATE, SUBSCRIPTION_CLOSED_STATE


class SaleOrderLog(models.Model):
    _name = 'sale.order.log'
    _description = 'Sale Order Log'
    _order = 'id desc'

    # Order related
    order_id = fields.Many2one(
        'sale.order', string='Sale Order',
        required=True, ondelete='cascade', readonly=True,
        auto_join=True
    )
    user_id = fields.Many2one('res.users', related='order_id.user_id', string='Salesperson', store=True, precompute=True, depends=[])
    team_id = fields.Many2one('crm.team', related='order_id.team_id', string='Sales Team', store=True, precompute=True, depends=[])
    plan_id = fields.Many2one('sale.subscription.plan', related='order_id.plan_id', string='Recurring Plan', store=True, precompute=True, depends=[])
    company_id = fields.Many2one('res.company', related='order_id.company_id', string='Company', store=True, precompute=True, depends=[])
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', string='Currency', store=True, precompute=True, depends=[], readonly=False)
    origin_order_id = fields.Many2one('sale.order', string='Origin Contract', store=True, index=True, precompute=True,
                                      compute='_compute_origin_order_id')

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
    event_date = fields.Date(string='Event Date', required=True, index=True, default=fields.Date.today)
    recurring_monthly = fields.Monetary(string='New MRR', required=True,
                                        help="MRR, after applying the changes of that particular event", readonly=True)
    amount_signed = fields.Monetary(string='MRR change', required=True, readonly=True)
    subscription_state = fields.Selection(selection=SUBSCRIPTION_STATES, help="Subscription stage when the change occurred")

    @api.depends('order_id')
    def _compute_origin_order_id(self):
        for log in self:
            log.origin_order_id = log.order_id.origin_order_id or log.order_id

    def _compute_display_name(self):
        for log in self:
            log.display_name = _("Sale order log: %s", log.id)

    #######################
    #       LOG GEN       #
    #######################

    @api.model
    def _create_log(self, order, initial_values):
        old_state = initial_values.get('subscription_state', order.subscription_state) or '1_draft'
        new_state = order.subscription_state

        # Cancelling a running or churned renewal
        if (order.state == 'cancel' and order.subscription_id
                and old_state in SUBSCRIPTION_PROGRESS_STATE + SUBSCRIPTION_CLOSED_STATE):
            return self._cancel_renewal_logs(order, initial_values)

        # Cancelling anything else
        if order.state == 'cancel':
            return self._cancel_logs(order, initial_values)

        # Confirm subscription SO
        if new_state in SUBSCRIPTION_PROGRESS_STATE and old_state == '1_draft':
            return self._create_creation_log(order, initial_values)

        # Confirm renewal SO
        if new_state in SUBSCRIPTION_PROGRESS_STATE and old_state == '2_renewal':
            return self._create_renewal_transfer_log(order, initial_values)

        # Reopen churned SO
        if new_state in SUBSCRIPTION_PROGRESS_STATE and old_state == '6_churn':
            return self._unlink_churn_log(order, initial_values)

        # Churn SO
        if old_state in SUBSCRIPTION_PROGRESS_STATE and new_state == '6_churn':
            return self._create_churn_log(order, initial_values)

        # SO is not in progress
        if new_state not in SUBSCRIPTION_PROGRESS_STATE and old_state not in SUBSCRIPTION_PROGRESS_STATE:
            return self.env['sale.order.log']

        # Currency change
        if 'currency_id' in initial_values and initial_values['currency_id'] != order.currency_id:
            return self._create_currency_transfer_log(order, initial_values)

        # MRR change
        return self._create_mrr_change_log(order, initial_values)

    @api.model
    def _cancel_renewal_logs(self, order, initial_values):
        order.order_log_ids.unlink()
        # Delete the transfer from the parent to the renewal that is cancelled
        self.search(
            [('order_id', '=', order.subscription_id.id),
             ('event_type', '=', '3_transfer'),
             ('amount_signed', '<', 0)
        ], order='id desc', limit=1).unlink()
        return self.env['sale.order.log']

    @api.model
    def _cancel_logs(self, order, initial_values):
        order.order_log_ids.unlink()
        return self.env['sale.order.log']

    @api.model
    def _create_creation_log(self, order, initial_values):
        return self.create({
            'order_id': order.id,
            'event_type': '0_creation',
            'amount_signed': max(order.recurring_monthly, 0),
            'recurring_monthly': max(order.recurring_monthly, 0),
            'subscription_state': initial_values.get('subscription_state') or '1_draft',
        })

    @api.model
    def _create_renewal_transfer_log(self, order, initial_values):
        result = self.env['sale.order.log']
        parent_order = order.subscription_id
        parent_churn = parent_order.order_log_ids.filtered(lambda log: log.event_type == '2_churn')

        # If at least 30 days between next invoice date and start_date, churn and creation instead of transfer
        if parent_order.next_invoice_date + timedelta(days=30) < order.start_date:
            if not parent_churn:
                result += self._create_churn_log(parent_order, {})
            return result + self._create_creation_log(order, initial_values)

        parent_churn[:1].unlink()

        parent_transfer_amount = sum(parent_order.order_log_ids.mapped('amount_signed'))
        parent_transfer = self.create({
            'order_id': parent_order.id,
            'event_type': '3_transfer',
            'amount_signed': -parent_transfer_amount,
            'recurring_monthly': 0,
            'subscription_state': parent_order.subscription_state,
        })

        renewal_transfer_amount = parent_transfer.currency_id._convert(parent_transfer_amount,
                                                          to_currency=order.currency_id,
                                                          company=order.company_id, round=False)
        renewal_transfer = self.create({
            'order_id': order.id,
            'event_type': '3_transfer',
            'amount_signed': renewal_transfer_amount,
            'recurring_monthly': renewal_transfer_amount,
            'subscription_state': initial_values.get('subscription_state', order.subscription_state),
        })

        initial_values['recurring_monthly'] = renewal_transfer_amount
        return parent_transfer + renewal_transfer + self._create_mrr_change_log(order, initial_values)

    @api.model
    def _unlink_churn_log(self, order, initial_values):
        order.order_log_ids.filtered(lambda log: log.event_type == '2_churn').unlink()
        initial_values['recurring_monthly'] = sum(order.order_log_ids.mapped('amount_signed'))
        return self._create_mrr_change_log(order, initial_values)

    @api.model
    def _create_churn_log(self, order, initial_values):
        return self.create({
            'order_id': order.id,
            'event_type': '2_churn',
            'amount_signed': -sum(order.order_log_ids.mapped('amount_signed')),
            'recurring_monthly': 0,
            'subscription_state': initial_values.get('subscription_state', order.subscription_state),
        })

    @api.model
    def _create_currency_transfer_log(self, order, initial_values):
        new_mrr = max(order.recurring_monthly, 0)
        old_mrr = max(initial_values.get('recurring_monthly', new_mrr), 0)
        old_mrr_new_currency = initial_values['currency_id']._convert(old_mrr,
                                                          to_currency=order.currency_id,
                                                          company=order.company_id, round=False)
        result = self.create([{
            'order_id': order.id,
            'event_type': '3_transfer',
            'amount_signed': -old_mrr,
            'currency_id': initial_values['currency_id'].id,
            'recurring_monthly': 0,
            'subscription_state': initial_values.get('subscription_state', order.subscription_state),
        }, {
            'order_id': order.id,
            'event_type': '3_transfer',
            'amount_signed': old_mrr_new_currency,
            'recurring_monthly': old_mrr_new_currency,
            'subscription_state': initial_values.get('subscription_state', order.subscription_state),
        }])

        if old_mrr_new_currency != new_mrr:
            initial_values['recurring_monthly'] = old_mrr_new_currency
            result += self._create_mrr_change_log(order, initial_values)

        return result

    @api.model
    def _create_mrr_change_log(self, order, initial_values):
        new_mrr = max(order.recurring_monthly, 0)
        old_mrr = max(initial_values.get('recurring_monthly', new_mrr), 0)

        if order.currency_id.compare_amounts(old_mrr, new_mrr) == 0:
            return self.env['sale.order.log']

        return self.create({
            'order_id': order.id,
            'event_type': '1_expansion' if new_mrr > old_mrr else '15_contraction',
            'amount_signed': new_mrr - old_mrr,
            'recurring_monthly': new_mrr,
            'subscription_state': order.subscription_state,
        })
