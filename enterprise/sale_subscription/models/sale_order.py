# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from dateutil.relativedelta import relativedelta
from markupsafe import escape, Markup
from psycopg2.extensions import TransactionRollbackError
from collections import defaultdict
import traceback

from odoo import fields, models, _, api, Command, SUPERUSER_ID, modules
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_is_zero
from odoo.osv import expression
from odoo.tools import config, format_amount, format_list, plaintext2html, split_every, str2bool
from odoo.tools.misc import format_date

_logger = logging.getLogger(__name__)

SUBSCRIPTION_DRAFT_STATE = ['1_draft', '2_renewal']
SUBSCRIPTION_PROGRESS_STATE = ['3_progress', '4_paused']
SUBSCRIPTION_CLOSED_STATE = ['6_churn', '5_renewed']

SUBSCRIPTION_STATES = [
    ('1_draft', 'Quotation'),  # Quotation for a new subscription
    ('2_renewal', 'Renewal Quotation'),  # Renewal Quotation for existing subscription
    ('3_progress', 'In Progress'),  # Active Subscription or confirmed renewal for active subscription
    ('4_paused', 'Paused'),  # Active subscription with paused invoicing
    ('5_renewed', 'Renewed'),  # Active or ended subscription that has been renewed
    ('6_churn', 'Churned'),  # Closed or ended subscription
    ('7_upsell', 'Upsell'),  # Quotation or SO upselling a subscription
]


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["rating.mixin", "sale.order"]

    def _get_default_starred_user_ids(self):
        return [(4, self.env.uid)]

    ###################
    # Recurring order #
    ###################
    is_subscription = fields.Boolean("Recurring", compute='_compute_is_subscription', store=True, index=True)
    plan_id = fields.Many2one('sale.subscription.plan', compute='_compute_plan_id', string='Recurring Plan',
                              ondelete='restrict', readonly=False, store=True, index='btree_not_null', tracking=True)
    subscription_state = fields.Selection(
        string='Subscription Status',
        selection=SUBSCRIPTION_STATES, readonly=False,
        compute='_compute_subscription_state', store=True, index='btree_not_null', tracking=True, group_expand='_group_expand_states',
    )

    subscription_id = fields.Many2one('sale.order', string='Parent Contract', ondelete='restrict', copy=False, index='btree_not_null')
    origin_order_id = fields.Many2one('sale.order', string='First contract', ondelete='restrict', store=True, copy=False,
                                      compute='_compute_origin_order_id', index='btree_not_null')
    subscription_child_ids = fields.One2many('sale.order', 'subscription_id')

    start_date = fields.Date(string='Start Date',
                             compute='_compute_start_date',
                             readonly=False,
                             store=True,
                             tracking=True,
                             help="The start date indicate when the subscription periods begin.")
    last_invoice_date = fields.Date(string='Last invoice date', compute='_compute_last_invoice_date')
    next_invoice_date = fields.Date(
        string='Next Invoice',
        compute='_compute_next_invoice_date',
        store=True, copy=False,
        readonly=False,
        tracking=True,
        help="The next invoice will be created on this date then the period will be extended.")
    end_date = fields.Date(string='End Date', tracking=True,
                           help="If set in advance, the subscription will be set to renew 1 month before the date and will be closed on the date set in this field.")
    first_contract_date = fields.Date(
        compute='_compute_first_contract_date',
        store=True,
        help="The first contract date is the start date of the first contract of the sequence. It is common across a subscription and its renewals.")
    close_reason_id = fields.Many2one("sale.order.close.reason", string="Close Reason", copy=False, tracking=True)

    #############
    # Invoicing #
    #############
    payment_token_id = fields.Many2one('payment.token', 'Payment Token', check_company=True, help='If not set, the automatic payment will fail.',
                                       domain="[('partner_id', 'child_of', commercial_partner_id), ('company_id', '=', company_id)]", copy=False)
    # technical, flag the contract failing for unknown reason (!= payment_exception) to avoid process them again and again
    is_batch = fields.Boolean(default=False, copy=False) # technical, batch of invoice processed at the same time
    # technical flag to avoid process the same subscription in several parallel crons
    is_invoice_cron = fields.Boolean(string='Is a Subscription invoiced in cron', default=False, copy=False)
    payment_exception = fields.Boolean("Contract in exception",
                                       help="Automatic payment with token failed. The payment provider configuration and token should be checked",
                                       copy=False)
    pending_transaction = fields.Boolean(help="The last transaction of the order is currently pending",
                                        copy=False)
    payment_term_id = fields.Many2one(tracking=True)
    currency_id = fields.Many2one(tracking=True)
    last_reminder_date = fields.Date(help="Last time when we sent a payment reminder")

    ###################
    # KPI / reporting #
    ###################
    kpi_1month_mrr_delta = fields.Float('KPI 1 Month MRR Delta')
    kpi_1month_mrr_percentage = fields.Float('KPI 1 Month MRR Percentage')
    kpi_3months_mrr_delta = fields.Float('KPI 3 months MRR Delta')
    kpi_3months_mrr_percentage = fields.Float('KPI 3 Months MRR Percentage')

    team_user_id = fields.Many2one('res.users', string="Team Leader", related="team_id.user_id", readonly=False)
    commercial_partner_id = fields.Many2one('res.partner', related='partner_id.commercial_partner_id')

    recurring_total = fields.Monetary(compute='_compute_recurring_total', string="Total Recurring", store=True)
    recurring_monthly = fields.Monetary(compute='_compute_recurring_monthly', string="Monthly Recurring",
                                        store=True, tracking=True)
    non_recurring_total = fields.Monetary(compute='_compute_non_recurring_total', string="Total Non Recurring Revenue")
    order_log_ids = fields.One2many('sale.order.log', 'order_id', string='Subscription Logs', readonly=True, copy=False)
    percentage_satisfaction = fields.Integer(
        compute="_compute_percentage_satisfaction",
        string="% Happy", store=True, compute_sudo=True, default=-1,
        help="Calculate the ratio between the number of the best ('great') ratings and the total number of ratings")
    health = fields.Selection([('normal', 'Neutral'), ('done', 'Good'), ('bad', 'Bad')], string="Health", copy=False,
                              default='normal', help="Show the health status")

    ###########
    #  Notes  #
    ###########
    note_order = fields.Many2one('sale.order', compute='_compute_note_order', search='_search_note_order')
    internal_note = fields.Html()
    internal_note_display = fields.Html(compute='_compute_internal_note_display', inverse='_inverse_internal_note_display')

    ###########
    # UI / UX #
    ###########
    recurring_details = fields.Html(compute='_compute_recurring_details')
    is_renewing = fields.Boolean(compute='_compute_is_renewing')
    is_upselling = fields.Boolean(compute='_compute_is_upselling')
    display_late = fields.Boolean(compute='_compute_display_late')
    history_count = fields.Integer(compute='_compute_history_count')
    upsell_count = fields.Integer(compute='_compute_upsell_count')
    renewal_count = fields.Integer(compute="_compute_renewal_count")
    has_recurring_line = fields.Boolean(compute='_compute_has_recurring_line')

    starred_user_ids = fields.Many2many('res.users', 'sale_order_starred_user_rel', 'order_id', 'user_id',
                                        default=lambda s: s._get_default_starred_user_ids(), string='Members')
    starred = fields.Boolean(compute='_compute_starred', inverse='_inverse_starred',
                             string='Show Subscription on dashboard',
                             help="Whether this subscription should be displayed on the dashboard or not")

    user_closable = fields.Boolean(related="plan_id.user_closable")
    user_quantity = fields.Boolean(related="plan_id.user_quantity")
    user_extend = fields.Boolean(related="plan_id.user_extend")

    _sql_constraints = [
        ('sale_subscription_state_coherence',
         "CHECK(NOT (is_subscription=TRUE AND state = 'sale' AND subscription_state='1_draft'))",
         "You cannot set to draft a confirmed subscription. Please create a new quotation"),
        ('sale_subscription_state_coherence_2',
         "CHECK(NOT (is_subscription=TRUE AND state in ('draft', 'sent') AND subscription_state in ('3_progress', '4_paused')) )",
         "You cannot have a draft SO be a confirmed subscription."),
        ('check_start_date_lower_next_invoice_date', 'CHECK((next_invoice_date IS NULL OR start_date IS NULL) OR (next_invoice_date >= start_date))',
         'The next invoice date of a sale order should be after its start date.'),
    ]

    @api.constrains('subscription_state', 'subscription_id', 'pricelist_id')
    def _constraint_subscription_upsell_multi_currency(self):
        for so in self:
            if so.subscription_state == '7_upsell' and so.subscription_id.pricelist_id.currency_id != so.pricelist_id.currency_id:
                raise ValidationError(_('You cannot upsell a subscription using a different currency.'))

    @api.constrains('plan_id', 'state', 'order_line')
    def _constraint_subscription_plan(self):
        recurring_product_orders = self.order_line.filtered(lambda l: l.product_id.recurring_invoice).order_id
        for so in self:
            if so.state in ['draft', 'cancel'] or so.subscription_state == '7_upsell':
                continue
            if so.subscription_id and not so.subscription_state:
                # so created before merge sale.subscription into sale.order upgrade.
                # This is the so that created the sale.subscription records.
                continue

            if so.has_recurring_line and not so.plan_id:
                raise UserError(_('Please add a recurring plan on the subscription or remove the recurring product.'))
            if so.plan_id and not so.has_recurring_line:
                raise UserError(_('Please add a recurring product in the subscription or remove the recurring plan.'))

    @api.constrains('subscription_state', 'state')
    def _constraint_canceled_subscription(self):
        incompatible_states = SUBSCRIPTION_PROGRESS_STATE + ['5_renewed']
        for so in self:
            if so.state == 'cancel' and so.subscription_state in incompatible_states:
                raise ValidationError(_(
                    'A cancelled SO cannot be in progress. You should close %s before cancelling it.',
                    so.name))

    @api.depends('plan_id')
    def _compute_is_subscription(self):
        for order in self:
            # upsells have recurrence but are not considered subscription. The method don't depend on subscription_state
            # to avoid recomputing the is_subscription value each time the sub_state is updated. it would trigger
            # other recompute we want to avoid
            if not order.plan_id or order.subscription_state == '7_upsell':
                order.is_subscription = False
                continue
            order.is_subscription = True
        # is_subscription value is not always updated in this method but subscription_state should always
        # be recomputed when this method is triggered.
        # without this call, subscription_state is not updated when it should and
        self.env.add_to_compute(self.env['sale.order']._fields['subscription_state'], self)

    @api.depends('is_subscription')
    def _compute_subscription_state(self):
        for order in self:
            if order.state not in ['draft', 'sent']:
                continue
            elif order.subscription_state in ['2_renewal', '7_upsell']:
                continue
            elif order.is_subscription:
                order.subscription_state = '2_renewal' if order.subscription_id else '1_draft'
            else:
                order.subscription_state = False

    def _compute_sale_order_template_id(self):
        if not self.env.context.get('default_is_subscription', False):
            return super(SaleOrder, self)._compute_sale_order_template_id()
        for order in self:
            if not order._origin.id and order.company_id.sale_order_template_id.is_subscription:
                order.sale_order_template_id = order.company_id.sale_order_template_id

    def _compute_type_name(self):
        other_orders = self.env['sale.order']
        for order in self:
            if order.is_subscription and order.state == 'sale':
                order.type_name = _('Subscription')
            elif order.subscription_state == '2_renewal':
                order.type_name = _('Renewal Quotation')
            else:
                other_orders |= order

        super(SaleOrder, other_orders)._compute_type_name()

    @api.depends('rating_percentage_satisfaction')
    def _compute_percentage_satisfaction(self):
        for subscription in self:
            subscription.percentage_satisfaction = int(subscription.rating_percentage_satisfaction)

    @api.depends('starred_user_ids')
    @api.depends_context('uid')
    def _compute_starred(self):
        for subscription in self:
            subscription.starred = self.env.user in subscription.starred_user_ids

    def _inverse_starred(self):
        starred_subscriptions = not_star_subscriptions = self.env['sale.order'].sudo()
        for subscription in self:
            if self.env.user in subscription.starred_user_ids:
                starred_subscriptions |= subscription
            else:
                not_star_subscriptions |= subscription
        not_star_subscriptions.write({'starred_user_ids': [(4, self.env.uid)]})
        starred_subscriptions.write({'starred_user_ids': [(3, self.env.uid)]})

    @api.depends('subscription_state', 'state', 'is_subscription', 'amount_untaxed')
    def _compute_recurring_monthly(self):
        """ Compute the amount monthly recurring revenue. When a subscription has a parent still ongoing.
        Depending on invoice_ids force the recurring monthly to be recomputed regularly, even for the first invoice
        where confirmation is set the next_invoice_date and first invoice do not update it (in automatic mode).
        """
        for order in self:
            if order.is_subscription or order.subscription_state == '7_upsell':
                order.recurring_monthly = sum(order.order_line.mapped('recurring_monthly'))
                continue
            order.recurring_monthly = 0

    @api.depends('subscription_state', 'state', 'is_subscription', 'order_line.price_subtotal', 'currency_id', 'company_id')
    def _compute_recurring_total(self):
        """ Compute the amount monthly recurring revenue. When a subscription has a parent still ongoing.
        Depending on invoice_ids force the recurring monthly to be recomputed regularly, even for the first invoice
        where confirmation is set the next_invoice_date and first invoice do not update it (in automatic mode).
        """
        for order in self:
            if order.is_subscription or order.subscription_state == '7_upsell':
                # Taken from module sale, method _compute_amounts
                AccountTax = self.env['account.tax']
                order_lines = order.order_line.filtered(lambda x: x.recurring_invoice and not x.display_type)
                base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
                AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
                AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
                tax_totals = AccountTax._get_tax_totals_summary(
                    base_lines=base_lines,
                    currency=order.currency_id or order.company_id.currency_id,
                    company=order.company_id,
                )
                order.recurring_total = tax_totals['base_amount_currency']
                continue
            order.recurring_total = 0

    @api.depends('amount_untaxed', 'recurring_total')
    def _compute_non_recurring_total(self):
        for order in self:
            order.non_recurring_total = order.amount_untaxed - order.recurring_total

    @api.depends('is_subscription', 'recurring_total')
    def _compute_recurring_details(self):
        subscription_orders = self.filtered(lambda sub: sub.is_subscription or sub.subscription_id)
        self.recurring_details = ""
        if subscription_orders.ids:
            for so in subscription_orders:
                lang_code = so.partner_id.lang
                recurring_amount = so.recurring_total
                non_recurring_amount = so.amount_untaxed - recurring_amount
                recurring_formatted_amount = so.currency_id and format_amount(self.env, recurring_amount, so.currency_id, lang_code) or recurring_amount
                non_recurring_formatted_amount = so.currency_id and format_amount(self.env, non_recurring_amount, so.currency_id, lang_code) or non_recurring_amount
                rendering_values = [{
                    'non_recurring': non_recurring_formatted_amount,
                    'recurring': recurring_formatted_amount,
                }]
                so.recurring_details = self.env['ir.qweb']._render('sale_subscription.recurring_details', {'rendering_values': rendering_values})

    def _compute_access_url(self):
        super()._compute_access_url()
        for order in self:
            # Quotations are handled in the quotation menu
            if order.is_subscription and order.subscription_state in SUBSCRIPTION_PROGRESS_STATE + SUBSCRIPTION_CLOSED_STATE and not self._context.get('force_sale_url'):
                order.access_url = '/my/subscriptions/%s' % order.id

    def _compute_start_date(self):
        for so in self:
            if not so.is_subscription:
                so.start_date = False
            elif not so.start_date:
                so.start_date = fields.Date.today()

    @api.depends('origin_order_id.start_date', 'origin_order_id', 'start_date')
    def _compute_first_contract_date(self):
        for so in self:
            if so.origin_order_id:
                so.first_contract_date = so.origin_order_id.start_date
            else:
                # First contract of the sequence
                so.first_contract_date = so.start_date

    @api.depends('subscription_child_ids', 'origin_order_id')
    def _get_invoiced(self):
        """
        Compute the invoices and their counts
        For subscription, we find all the invoice lines related to the orders
        descending from the origin_order_id
        """
        subscription_ids = []
        so_by_origin = defaultdict(lambda: self.env['sale.order'])
        parent_order_ids = []
        for order in self:
            if order.is_subscription and not isinstance(order.id, models.NewId):
                subscription_ids.append(order.id)
                origin_key = order.origin_order_id.id if order.origin_order_id else order.id
                parent_order_ids.append(origin_key)
                so_by_origin[origin_key] += order

        subscriptions = self.browse(subscription_ids)
        res = super(SaleOrder, self - subscriptions)._get_invoiced()
        if not subscriptions:
            return res
        # Ensure that we give value to everyone
        subscriptions.update({
            'invoice_ids': [],
            'invoice_count': 0
        })

        if not so_by_origin or not subscription_ids:
            return res

        self.flush_recordset(fnames=['origin_order_id'])
        all_subscription_ids = self.search([('origin_order_id', 'in', parent_order_ids)]).ids + parent_order_ids

        # We have two ways to access the account.move from the sale.order.
        # First we get the invoices using the subscription_id value on the account.move.line.
        # It is useful if the sale.order.line are deleted and replaced by others during the subscription life.
        subscription_move_lines = self.env['account.move.line'].search([('subscription_id', 'in', all_subscription_ids)])
        subscription_move_lines.fetch(['subscription_id', 'move_id'])
        subscription_move_lines.subscription_id.fetch(['origin_order_id'])
        move_by_origin = defaultdict(list)
        for aml in subscription_move_lines:
            origin_order = aml.subscription_id.origin_order_id.id or aml.subscription_id.id
            move_by_origin[origin_order].append(aml.move_id.id)

        # Secondly we get the invoices using the relationship between account.move.line and sale.order.line of sale module.
        query = """
            SELECT COALESCE(origin_order_id, so.id),
                   array_agg(DISTINCT am.id) AS move_ids
              FROM sale_order so
              JOIN sale_order_line sol ON sol.order_id = so.id
              JOIN sale_order_line_invoice_rel solam ON sol.id = solam.order_line_id
              JOIN account_move_line aml ON aml.id = solam.invoice_line_id
              JOIN account_move am ON am.id = aml.move_id
             WHERE am.company_id IN %s
               AND so.id IN %s
               AND am.move_type IN ('out_invoice', 'out_refund')
          GROUP BY COALESCE(origin_order_id, so.id)
        """

        self.env.cr.execute(query, [tuple(self.env.companies.ids), tuple(all_subscription_ids)])
        orders_vals = self.env.cr.fetchall()
        for origin_order_id, invoices_ids in orders_vals + list(move_by_origin.items()):
            other_move_ids = move_by_origin[origin_order_id]
            all_move_ids = set(invoices_ids + other_move_ids)
            so_by_origin[origin_order_id].update({
                'invoice_ids': [Command.set(all_move_ids)],
                'invoice_count': len(all_move_ids)
            })
        return res

    @api.depends('is_subscription', 'state', 'start_date', 'subscription_state')
    def _compute_next_invoice_date(self):
        for so in self:
            if not so.is_subscription and so.subscription_state != '7_upsell':
                so.next_invoice_date = False
            elif not so.next_invoice_date and so.state == 'sale':
                # Define a default next invoice date.
                # It is increased by _update_next_invoice_date or when posting a invoice when when necessary
                so.next_invoice_date = so.start_date or fields.Date.today()

    @api.depends('start_date', 'state', 'next_invoice_date')
    def _compute_last_invoice_date(self):
        for order in self:
            last_date = order.next_invoice_date and order.plan_id.billing_period and order.next_invoice_date - order.plan_id.billing_period
            start_date = order.start_date or fields.Date.today()
            if order.state == 'sale' and last_date and last_date >= start_date:
                order.last_invoice_date = last_date
            else:
                order.last_invoice_date = False

    @api.depends('subscription_child_ids')
    def _compute_renewal_count(self):
        self.renewal_count = 0
        if not any(self.mapped('subscription_state')):
            return
        result = self.env['sale.order']._read_group([
                ('subscription_state', '=', '2_renewal'),
                ('state', 'in', ['draft', 'sent']),
                ('subscription_id', 'in', self.ids)
            ],
            ['subscription_id'],
            ['__count'],
        )
        counters = {subscription.id: count for subscription, count in result}
        for so in self:
            so.renewal_count = counters.get(so.id, 0)

    @api.depends('subscription_child_ids')
    def _compute_upsell_count(self):
        self.upsell_count = 0
        if not any(self.mapped('subscription_state')):
            return
        result = self.env['sale.order']._read_group([
                ('subscription_state', '=', '7_upsell'),
                ('state', 'in', ['draft', 'sent']),
                ('subscription_id', 'in', self.ids)
            ],
            ['subscription_id'],
            ['__count'],
        )
        counters = {subscription.id: count for subscription, count in result}
        for so in self:
            so.upsell_count = counters.get(so.id, 0)

    @api.depends('origin_order_id')
    def _compute_history_count(self):
        if not any(self.mapped('subscription_state')):
            self.history_count = 0
            return
        origin_ids = self.origin_order_id.ids + self.ids
        result = self.env['sale.order']._read_group([
                ('state', 'not in', ['cancel', 'draft']),
                ('origin_order_id', 'in', origin_ids)
            ],
            ['origin_order_id'],
            ['__count'],
        )
        counters = {origin_order.id: count + 1 for origin_order, count in result}
        for so in self:
            so.history_count = counters.get(so.origin_order_id.id or so.id, 0)

    @api.depends('is_subscription', 'subscription_state')
    def _compute_origin_order_id(self):
        for order in self:
            if (order.is_subscription or order.subscription_state == '7_upsell') and not order.origin_order_id:
                order.origin_order_id = order.subscription_id.origin_order_id or order.subscription_id

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'subscription_state' in init_values:
            return self.env.ref('sale_subscription.subtype_state_change')
        return super()._track_subtype(init_values)

    @api.depends('sale_order_template_id')
    def _compute_plan_id(self):
        for order in self:
            order.plan_id = None
            if order.sale_order_template_id and order.sale_order_template_id.plan_id:
                order.plan_id = order.sale_order_template_id.plan_id

    def _compute_is_renewing(self):
        self.is_renewing = False
        renew_order_ids = self.env['sale.order'].search([
            ('id', 'in', self.subscription_child_ids.ids),
            ('subscription_state', '=', '2_renewal'),
            ('state', 'in', ['draft', 'sent']),
        ]).subscription_id
        renew_order_ids.is_renewing = True

    def _compute_is_upselling(self):
        self.is_upselling = False
        upsell_order_ids = self.env['sale.order'].search([
            ('id', 'in', self.subscription_child_ids.ids),
            ('state', 'in', ['draft', 'sent']),
            ('subscription_state', '=', '7_upsell')
        ]).subscription_id
        upsell_order_ids.is_upselling = True

    def _compute_display_late(self):
        today = fields.Date.today()
        for order in self:
            order.display_late = order.subscription_state in SUBSCRIPTION_PROGRESS_STATE and order.next_invoice_date and order.next_invoice_date < today

    @api.depends('order_line', 'order_line.recurring_invoice')
    def _compute_has_recurring_line(self):
        recurring_product_orders = self.order_line.filtered(lambda l: l.product_id.recurring_invoice).order_id
        recurring_product_orders.has_recurring_line = True
        (self - recurring_product_orders).has_recurring_line = False

    @api.depends('subscription_id')
    def _compute_note_order(self):
        for order in self:
            if order.internal_note or not order.subscription_id:
                order.note_order = order
            else:
                order.note_order = order.subscription_id.note_order

    def _search_note_order(self, operator, value):
        if operator not in ['in', '=']:
            return NotImplemented
        ooids = self.search_read([('id', operator, value)], ['origin_order_id', 'id'], load=None)
        ooids = [v['origin_order_id'] or v['id'] for v in ooids]
        return [('origin_order_id', 'in', ooids), ('internal_note', '=', False)]

    @api.depends('note_order.internal_note')
    def _compute_internal_note_display(self):
        for order in self:
            order.internal_note_display = order.note_order.internal_note

    def _inverse_internal_note_display(self):
        for order in self:
            order.note_order.internal_note = order.internal_note_display

    def _mail_track(self, tracked_fields, initial_values):
        res = super()._mail_track(tracked_fields, initial_values)
        if self.is_subscription:
            self.env['sale.order.log']._create_log(self, initial_values.copy())
        return res

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.sale_order_template_id.journal_id:
            vals['journal_id'] = self.sale_order_template_id.journal_id.id
        return vals

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        if not kwargs.get('model_description') and self.is_subscription:
            kwargs['model_description'] = _("Subscription")
        super()._notify_thread(message, msg_vals=msg_vals, **kwargs)

    ###########
    # CRUD    #
    ###########

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order, vals in zip(orders, vals_list):
            if order.is_subscription and not order.subscription_state:
                order.subscription_state = vals.get('subscription_state', '1_draft')
        return orders

    def write(self, vals):
        res = super().write(vals)
        self._reset_sub_salesperson(vals)
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for order in self:
            if order.state not in ['draft', 'sent'] and order.subscription_state and order.subscription_state not in SUBSCRIPTION_DRAFT_STATE + SUBSCRIPTION_CLOSED_STATE:
                raise UserError(_('You can not delete a confirmed subscription. You must first close and cancel it before you can delete it.'))
        return super(SaleOrder, self)._unlink_except_draft_or_cancel()

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for order, vals in zip(self, vals_list):
            if order.subscription_state == '7_upsell':
                vals.update({
                    "client_order_ref": order.client_order_ref,
                    "subscription_id": order.subscription_id.id,
                    "origin_order_id": order.origin_order_id.id,
                    'subscription_state': '7_upsell'
                })
            elif (not order.subscription_state and order.plan_id) or (order.subscription_state and 'subscription_state' not in default):
                vals.update({
                    'subscription_state': '1_draft'
                })
        return vals_list

    ###########
    # Actions #
    ###########

    def action_update_prices(self):
        # Resetting the price_unit will break the link to the parent_line_id. action_update_prices will recompute
        # the price and _compute_parent_line_id will be recomputed.
        self.order_line.price_unit = False
        super(SaleOrder, self).action_update_prices()

    def action_draft(self):
        for order in self:
            if (order.state == 'cancel'
                and order.is_subscription
                and any(state in ['draft', 'posted'] for state in order.order_line.invoice_lines.move_id.mapped('state'))):
                raise UserError(
                    _('You cannot set to draft a cancelled quotation linked to invoiced subscriptions. Please create a new quotation.'))
        res = super().action_draft()
        for order in self:
            if order.is_subscription:
                order.subscription_state = '2_renewal' if order.subscription_id else '1_draft'
        return res

    def _action_cancel(self):
        to_open_ids = []
        for order in self:
            # Get the moves in sudo to be able to get moves in companies the user can't access.
            related_move = order.sudo()._get_subscription_invoices()
            if order.subscription_state == '7_upsell':
                if order.state in ['sale', 'done']:
                    cancel_message_body = _("The upsell %s has been cancelled. Please recheck the quantities as they may have been affected by this cancellation.", order._get_html_link())
                else:
                    cancel_message_body = _("The upsell %s has been cancelled.", order._get_html_link())
                order.subscription_id.message_post(body=cancel_message_body)
            elif order.subscription_state == '2_renewal':
                cancel_message_body = _("The renewal %s has been cancelled.", order._get_html_link())
                order.subscription_id.message_post(body=cancel_message_body)
            elif (order.subscription_state in SUBSCRIPTION_PROGRESS_STATE + SUBSCRIPTION_DRAFT_STATE
                  and not any(state in ['draft', 'posted'] for state in related_move.mapped('state'))):
                # subscription_id means a renewal because no upsell could enter this condition
                # When we cancel a quote or a confirmed subscription that was not invoiced, we remove the order logs and
                # reopen the parent order if the conditions are met.
                # We know if the order is a renewal with transfer log by looking at the logs of the parent and the log of the order.
                parent_last_log = order.subscription_id and \
                                  order.subscription_id.order_log_ids.sorted(
                                      lambda log: (log.event_date, log.id), reverse=True
                                  )[:1]
                if (parent_last_log and
                    parent_last_log.event_type == '3_transfer' and
                    parent_last_log.amount_signed <= 0):
                    # Reopen the parent order
                    to_open_ids.append(order.subscription_id.id)
                    parent_link = order.subscription_id._get_html_link()
                    cancel_activity_body = _("""Subscription %(link)s has been cancelled. The parent order %(parent_link)s has been reopened.
                                                You should close %(parent_link)s if the customer churned, or renew it if the customer continue the service.
                                                Note: if you already created a new subscription instead of renewing it, please cancel your newly
                                                created subscription and renew %(parent_link)s instead""", link=order._get_html_link(),
                                                                                                parent_link=parent_link)
                    order.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_("Check reopened subscription"),
                        note=cancel_activity_body,
                        user_id=order.subscription_id.user_id.id
                    )
                order.subscription_state = False
            elif (order.subscription_state in SUBSCRIPTION_PROGRESS_STATE + SUBSCRIPTION_CLOSED_STATE
                  and any(state in ['draft', 'posted'] for state in related_move.mapped('state'))):
                raise ValidationError(_('You cannot cancel a subscription that has been invoiced.'))
            elif order.subscription_id and order.subscription_state == '6_churn':
                raise ValidationError(_("You cannot cancel a churned renewed subscription."))
            if order.is_subscription:
                order.subscription_state = False
        res = super()._action_cancel()
        self.browse(to_open_ids).set_open()
        return res



    def _prepare_confirmation_values(self):
        """
        Override of the sale method. sale.order in self should have the same subscription_state in order to process
        them in batch.
        :return: dict of values
        """
        values = super()._prepare_confirmation_values()
        if all(self.mapped('is_subscription')):
            values['subscription_state'] = '3_progress'
        return values

    def action_confirm(self):
        """Update and/or create subscriptions on order confirmation."""
        recurring_order = self.env['sale.order']
        upsell = self.env['sale.order']
        renewal = self.env['sale.order']
        post_paid = self.env['sale.order']

        # The sale_subscription override of `_compute_discount` added `order_id.start_date` and
        # `order_id.subscription_state` to `api.depends`; as this method modifies these fields,
        # the discount field requires protection to avoid overwriting manually applied discounts
        with self.env.protecting([self.order_line._fields['discount']], self.order_line):
            for order in self:
                if order.subscription_id:
                    if order.subscription_state == '7_upsell' and order.state in ['draft', 'sent']:
                        upsell |= order
                    elif order.subscription_state == '2_renewal':
                        renewal |= order
                if order.is_subscription:
                    recurring_order |= order
                    if not order.subscription_state:
                        order.subscription_state = '1_draft'
                elif order.subscription_state != '7_upsell':
                    order.subscription_state = False
                if order.order_line._is_all_postpaid():
                    post_paid |= order

            # _prepare_confirmation_values will update subscription_state for all confirmed subscription.
            res_sub = super(SaleOrder, recurring_order).action_confirm()
            res_other = super(SaleOrder, self - recurring_order).action_confirm()
            recurring_order._confirm_subscription()
            renewal._confirm_renewal()
            upsell._confirm_upsell()
            # Update the next_invoice_date if all the lines are postpaid
            # _update_next_invoice_date method is called after the confirmation of the SO.
            # so that we can get the order.next_invoice_date or order.start_date from the SO.
            post_paid._update_next_invoice_date()

        return res_sub and res_other

    def action_quotation_send(self):
        if len(self) == 1:
            # Raise error before other popup if used on one SO.
            has_recurring_line = self.order_line.filtered(lambda l: l.product_id.recurring_invoice)
            if has_recurring_line and not self.plan_id:
                raise UserError(_('Please set a recurring plan on the subscription before sending the email.'))
            if self.plan_id and not has_recurring_line:
                raise UserError(_('Please remove the recurring plan on the subscription before sending the email.'))
        return super().action_quotation_send()

    def _confirm_subscription(self):
        today = fields.Date.today()
        for sub in self:
            sub._portal_ensure_token()
            # We set the start date and invoice date at the date of confirmation
            if not sub.start_date:
                sub.start_date = today
            if sub.plan_id.billing_period_value <= 0:
                raise UserError(_("Recurring period must be a positive number. Please ensure the input is a valid positive numeric value."))
            sub._set_deferred_end_date_from_template()
            sub.order_line._reset_subscription_qty_to_invoice()
            if sub._check_token_saving_conditions():
                sub._save_token_from_payment()

    def _set_deferred_end_date_from_template(self):
        self.ensure_one()
        if self.sale_order_template_id and not self.sale_order_template_id.is_unlimited and not self.end_date:
            self.write({'end_date': self.start_date + self.sale_order_template_id.duration - relativedelta(days=1)})

    def _confirm_upsell(self):
        """
        When confirming an upsell order, the recurring product lines must be updated
        """
        today = fields.Date.today()
        for so in self:
            # We check the subscription direct invoice and not the one related to the whole SO
            if (so.start_date or today) >= so.subscription_id.next_invoice_date:
                raise ValidationError(
                    _(
                        "The start date of an upsell cannot be greater or equal to the next invoice date of the subscription %s.\n"
                        "You should first invoice the original subscription, use an earlier start date for the upsell or create a renewal quotation.",
                        so.subscription_id.name
                    )
                )

        existing_line_ids = self.subscription_id.order_line
        dummy, update_values = self.update_existing_subscriptions()
        updated_line_ids = self.env['sale.order.line'].browse({val[1] for val in update_values})
        new_lines_ids = self.subscription_id.order_line - existing_line_ids
        # Example: with a new yearly line starting in june when the expected next invoice date is december,
        # discount is 50% and the default next_invoice_date will be in june too.
        # We need to get the default next_invoice_date that was saved on the upsell because the compute has no way
        # to differentiate new line created by an upsell and new line created by the user.
        for upsell in self:
            upsell.subscription_id.message_post(body=_("The upsell %s has been confirmed.", upsell._get_html_link()))
        for line in (updated_line_ids | new_lines_ids).with_context(skip_line_status_compute=True):
            # The upsell invoice will take care of the invoicing for this period
            line.qty_to_invoice = 0
            line.qty_invoiced = line.product_uom_qty
            # We force the invoice status because the current period will be invoiced by the upsell flow
            # when the upsell so is invoiced
            line.invoice_status = 'no'

    def _confirm_renewal(self):
        """
        When confirming a renewal order, the recurring product lines must be updated
        """
        today = fields.Date.today()
        for renew in self:
            # When parent subscription reaches his end_date, it will be closed with a close_reason_renew, so it won't be considered as a simple churn.
            parent = renew.subscription_id
            if renew.start_date < parent.next_invoice_date:
                raise ValidationError(_("You cannot validate a renewal quotation starting before the next invoice date "
                                        "of the parent contract. Please update the start date after the %s.", format_date(self.env, parent.next_invoice_date)))
            elif parent.start_date == parent.next_invoice_date:
                raise ValidationError(_("You can not upsell or renew a subscription that has not been invoiced yet. "
                                        "Please, update directly the %s contract or invoice it first.", parent.name))
            elif parent.subscription_state == '5_renewed':
                raise ValidationError(_("You cannot renew a subscription that has been renewed. "))
            elif self.search_count([('origin_order_id', '=', renew.origin_order_id.id),
                                    ('subscription_state', 'in', SUBSCRIPTION_PROGRESS_STATE),
                                    ('id', 'not in', [parent.id, renew.id])], limit=1):
                raise ValidationError(_("You cannot renew a contract that already has an active subscription. "))
            other_renew_so_ids = parent.subscription_child_ids.filtered(lambda so: so.subscription_state == '2_renewal' and so.state != 'cancel') - renew
            if other_renew_so_ids:
                other_renew_so_ids._action_cancel()

            renew_msg_body = _("This subscription is renewed in %s with a change of plan.", renew._get_html_link())
            parent.message_post(body=renew_msg_body)
            renew_close_reason_id = self.env.ref('sale_subscription.close_reason_renew')
            end_of_contract_reason_id = self.env.ref('sale_subscription.close_reason_end_of_contract')
            close_reason_id = renew_close_reason_id if parent.subscription_state != "6_churn" else end_of_contract_reason_id
            parent.set_close(close_reason_id=close_reason_id.id, renew=True)
            parent.update({'end_date': parent.next_invoice_date})
            # This can create hole that are not taken into account by progress_sub upselling, it's an assumed choice over more upselling complexity
            start_date = renew.start_date or parent.next_invoice_date
            renew.write({'date_order': today, 'start_date': start_date})
            if renew._check_token_saving_conditions():
                renew._save_token_from_payment()

    def _check_token_saving_conditions(self):
        """ Check if all conditions match for saving the payment token on the subscription. """
        self.ensure_one()
        last_transaction = self.transaction_ids.sudo()._get_last()
        last_token = last_transaction.token_id
        subscription_fully_paid = self.currency_id.compare_amounts(last_transaction.amount, self.amount_total) >= 0
        transaction_authorized = last_transaction and last_transaction.renewal_state == "authorized"
        return last_token and last_transaction and subscription_fully_paid and transaction_authorized

    def _save_token_from_payment(self):
        self.ensure_one()
        last_token = self.transaction_ids.sudo()._get_last().token_id.id
        if last_token:
            self.payment_token_id = last_token

    def _group_expand_states(self, states, domain):
        return sorted(set(states).union({'3_progress', '4_paused'}))

    @api.model
    def _get_associated_so_action(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[self.env.ref('sale_subscription.sale_subscription_view_tree').id, "list"],
                      [self.env.ref('sale_subscription.sale_subscription_primary_form_view').id, "form"],
                      [False, "kanban"], [False, "calendar"], [False, "pivot"], [False, "graph"]],
        }

    def open_subscription_history(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[self.env.ref('sale_subscription.sale_subscription_quotation_tree_view').id, "list"],
                      [self.env.ref('sale_subscription.sale_subscription_primary_form_view').id, "form"]]
        }
        origin_order_id = self.origin_order_id.id or self.id
        action['name'] = _("History")
        action['domain'] = [('state', 'not in', ['cancel', 'draft']),
                            '|',
                            ('id', '=', origin_order_id),
                            ('origin_order_id', '=', origin_order_id)
                            ]
        action['context'] = {
            **action.get('context', {}),
            'create': False,
        }
        return action

    def open_subscription_renewal(self):
        self.ensure_one()
        action = self._get_associated_so_action()
        action['name'] = _("Renewal Quotations")
        renewal = self.subscription_child_ids.filtered(lambda so: so.subscription_state == '2_renewal')
        if len(renewal) == 1:
            action['res_id'] = renewal.id
            action['views'] = [(self.env.ref('sale_subscription.sale_subscription_primary_form_view').id, 'form')]
        else:
            action['domain'] = [('subscription_id', '=', self.id), ('subscription_state', '=', '2_renewal'), ('state', 'in', ['draft', 'sent'])]
            action['views'] = [(self.env.ref('sale.view_quotation_tree').id, 'list'),
                               (self.env.ref('sale_subscription.sale_subscription_primary_form_view').id, 'form')]

        action['context'] = {
            **action.get('context', {}),
            'create': False,
        }
        return action

    def open_subscription_upsell(self):
        self.ensure_one()
        action = self._get_associated_so_action()
        action['name'] = _("Upsell Quotations")
        upsell = self.subscription_child_ids.filtered(lambda so: so.subscription_state == '7_upsell' and so.state in ['draft', 'sent'])
        if len(upsell) == 1:
            action['res_id'] = upsell.id
            action['views'] = [(self.env.ref('sale_subscription.sale_subscription_primary_form_view').id, 'form')]
        else:
            action['domain'] = [('subscription_id', '=', self.id), ('subscription_state', '=', '7_upsell'), ('state', 'in', ['draft', 'sent'])]
            action['views'] = [(self.env.ref('sale.view_quotation_tree').id, 'list'),
                               (self.env.ref('sale_subscription.sale_subscription_primary_form_view').id, 'form')]
        action['context'] = {
            **action.get('context', {}),
            'create': False,
        }
        return action

    def action_sale_order_log(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("sale_subscription.sale_order_log_analysis_action")
        origin_order_ids = self.origin_order_id.ids + self.ids
        genealogy_orders_ids = self.search(['|', ('id', 'in', origin_order_ids), ('origin_order_id', 'in', origin_order_ids)])
        action.update({
            'name': _('MRR changes'),
            'domain': [('order_id', 'in', genealogy_orders_ids.ids)],
        })
        return action

    def _create_renew_upsell_order(self, subscription_state, message_body):
        self.ensure_one()
        if self.start_date == self.next_invoice_date:
            raise ValidationError(_("You can not upsell or renew a subscription that has not been invoiced yet. "
                                    "Please, update directly the %s contract or invoice it first.", self.name))
        values = self._prepare_upsell_renew_order_values(subscription_state)
        order = self.env['sale.order'].create(values)
        self._subscribe_followers_to_new_order(order)
        self.subscription_child_ids = [Command.link(order.id)]
        order.message_post(body=message_body)
        if subscription_state == '7_upsell':
            parent_message_body = _("An upsell quotation %s has been created", order._get_html_link())
        else:
            parent_message_body = _("A renewal quotation %s has been created", order._get_html_link())
        self.message_post(body=parent_message_body)
        order.order_line._compute_tax_id()
        return order

    def _prepare_renew_upsell_order(self, subscription_state, message_body):
        order = self._create_renew_upsell_order(subscription_state, message_body)
        action = self._get_associated_so_action()
        action['name'] = _('Upsell') if subscription_state == '7_upsell' else _('Renew')
        action['views'] = [(self.env.ref('sale_subscription.sale_subscription_primary_form_view').id, 'form')]
        action['res_id'] = order.id
        return action

    def _get_order_digest(self, origin='', template='sale_subscription.sale_order_digest', lang=None):
        self.ensure_one()
        values = {'origin': origin,
                  'record_url': self._get_html_link(),
                  'start_date': self.start_date,
                  'next_invoice_date': self.next_invoice_date,
                  'recurring_monthly': self.recurring_monthly,
                  'untaxed_amount': self.amount_untaxed,
                  'quotation_template': self.sale_order_template_id.name} # see if we don't want plan instead
        return self.env['ir.qweb'].with_context(lang=lang)._render(template, values)

    def prepare_renewal_order(self):
        self.ensure_one()
        lang = self.partner_id.lang or self.env.user.lang
        renew_msg_body = self._get_order_digest(origin='renewal', lang=lang)
        action = self._prepare_renew_upsell_order('2_renewal', renew_msg_body)

        return action

    def prepare_upsell_order(self):
        self.ensure_one()
        lang = self.partner_id.lang or self.env.user.lang
        upsell_msg_body = self._get_order_digest(origin='upsell', lang=lang)
        action = self._prepare_renew_upsell_order('7_upsell', upsell_msg_body)
        return action

    def reopen_order(self):
        if self and set(self.mapped('subscription_state')) != {'6_churn'}:
            raise UserError(_("You cannot reopen a subscription that isn't closed."))
        self.set_open()

    def pause_subscription(self):
        with self.env.protecting([self.order_line._fields['discount']], self.order_line):
            self.filtered(lambda so: so.subscription_state == '3_progress').write({'subscription_state': '4_paused'})

    def resume_subscription(self):
        with self.env.protecting([self.order_line._fields['discount']], self.order_line):
            self.filtered(lambda so: so.subscription_state == '4_paused').write({'subscription_state': '3_progress'})

    def create_alternative(self):
        self.ensure_one()
        alternative_so = self.copy({
            'origin_order_id': self.origin_order_id.id,
            'subscription_id': self.subscription_id.id,
            'subscription_state': self.env.context.get('default_subscription_state', '2_renewal'),
            'next_invoice_date': self.next_invoice_date,
        })
        action = alternative_so._get_associated_so_action()
        action['views'] = [(self.env.ref('sale_subscription.sale_subscription_primary_form_view').id, 'form')]
        action['res_id'] = alternative_so.id
        return action

    def _should_be_locked(self):
        self.ensure_one()
        should_lock = super()._should_be_locked()
        return should_lock and not self.is_subscription

    ####################
    # Business Methods #
    ####################

    def _upsell_context(self):
        return {"skip_next_invoice_update": True}

    def update_existing_subscriptions(self):
        """
        Update subscriptions already linked to the order by updating or creating lines.
        This method is only called on upsell confirmation
        :rtype: list(integer)
        :return: ids of modified subscriptions
        """
        create_values, update_values = [], []
        context = self._upsell_context()
        for order in self:
            # We don't propagate the line description from the upsell order to the subscription
            create_values, update_values = order.order_line.filtered(lambda sol: not sol.display_type)._subscription_update_line_data(order.subscription_id)
            order.subscription_id.with_context(**context).write({'order_line': create_values + update_values})
        return create_values, update_values

    def _get_closing_end_date(self):
        """
        Get the end date for a subscription that is being closed.
        :return: date
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.end_date and self.end_date <= today:
            return self.end_date
        if self.plan_id.user_closable and self.plan_id.user_closable_options == 'end_of_period' and self.env.context.get("allow_future_end_date"):
            return self.next_invoice_date - relativedelta(days=1)
        return today

    def _set_closed_state(self, renew=False):
        renewal_order = self.subscription_child_ids.filtered(lambda s: s.subscription_state in SUBSCRIPTION_PROGRESS_STATE)
        if renew and renewal_order and self.state == 'sale':
            self.subscription_state = '5_renewed'
            self.locked = True
        else:
            self.subscription_state = '6_churn'

    def set_close(self, close_reason_id=None, renew=False):
        """
        Close subscriptions.
        :param int close_reason_id: The ID of the sale.order.close.reason.
        :param bool renew: Indicates whether the subscription is being renewed.
        :return: True
        """
        today = fields.Date.context_today(self)
        if not close_reason_id:
            renew_close_reason_id = self.env.ref('sale_subscription.close_reason_renew').id
            end_of_contract_reason_id = self.env.ref('sale_subscription.close_reason_end_of_contract').id
            close_reason_unknown_id = self.env.ref('sale_subscription.close_reason_unknown').id
        for sub in self:
            end_date = sub._get_closing_end_date()
            if renew or end_date <= today:
                sub._set_closed_state(renew)
            values = {'end_date': end_date}
            if not close_reason_id and not (close_reason_id := sub.close_reason_id):
                if renew:
                    close_reason_id = renew_close_reason_id
                elif sub.end_date and sub.end_date <= end_date:
                    close_reason_id = end_of_contract_reason_id
                else:
                    close_reason_id = close_reason_unknown_id
            sub.update(dict(**values, close_reason_id=close_reason_id))
        return True

    def set_open(self):
        all_origin_order_ids = self.origin_order_id.ids + self.ids
        incompatible_origin = self.env['sale.order'].search([
            ('origin_order_id', 'in', all_origin_order_ids),
            ('subscription_state', 'in', SUBSCRIPTION_PROGRESS_STATE)
        ]).origin_order_id
        to_open_ids = []
        for order in self:
            if order.subscription_state == '6_churn' and order.end_date:
                order.end_date = False
                reopen_activity_body = _("Subscription %s has been reopened. The end date has been removed", order._get_html_link())
                order.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_("Check reopened subscription"),
                    note=reopen_activity_body,
                    user_id=order.user_id.id
                )
            if order.is_subscription and not (order in incompatible_origin or order.origin_order_id in incompatible_origin):
                to_open_ids.append(order.id)
        self.browse(to_open_ids).update({'state': 'sale', 'subscription_state': '3_progress', 'close_reason_id': False, 'locked': False})

    @api.model
    def _cron_update_kpi(self):
        subscriptions = self.search([('subscription_state', '=', '3_progress'), ('is_subscription', '=', True)])
        subscriptions._compute_kpi()

    def _prepare_upsell_renew_order_values(self, subscription_state):
        """
        Create a new draft order with the same lines as the parent subscription. All recurring lines are linked to their parent lines
        :return: dict of new sale order values
        """
        self.ensure_one()
        today = fields.Date.today()
        if subscription_state == '7_upsell' and self.next_invoice_date and self.next_invoice_date <= max(self.first_contract_date or today, today):
            raise UserError(_('You cannot create an upsell for this subscription because it :\n'
                              ' - Has not started yet.\n'
                              ' - Has no invoiced period in the future.'))
        lang_code = self.partner_id.lang
        subscription = self.with_company(self.company_id)
        order_lines = self.with_context(lang=lang_code).order_line._get_renew_upsell_values(subscription_state)
        is_subscription = subscription_state == '2_renewal'
        option_lines_data = [Command.link(option.copy().id) for option in subscription.with_context(lang=lang_code).sale_order_option_ids]
        if subscription_state == '7_upsell':
            start_date = fields.Date.today()
            next_invoice_date = self.next_invoice_date
        else:
            # renewal
            start_date = self.next_invoice_date
            next_invoice_date = self.next_invoice_date # the next invoice date is the start_date for new contract
        values = {
            'is_subscription': is_subscription,
            'subscription_id': subscription.id,
            'pricelist_id': subscription.pricelist_id.id,
            'partner_id': subscription.partner_id.id,
            'partner_invoice_id': subscription.partner_invoice_id.id,
            'partner_shipping_id': subscription.partner_shipping_id.id,
            'order_line': order_lines,
            'subscription_state': subscription_state,
            'origin': subscription.client_order_ref,
            'client_order_ref': subscription.client_order_ref,
            'origin_order_id': subscription.origin_order_id.id,
            'note': subscription.note,
            'user_id': subscription.user_id.id,
            'payment_term_id': subscription.payment_term_id.id,
            'company_id': subscription.company_id.id,
            'sale_order_template_id': self.sale_order_template_id.id,
            'sale_order_option_ids': option_lines_data,
            'payment_token_id': False,
            'start_date': start_date,
            'next_invoice_date': next_invoice_date,
            'plan_id': subscription.plan_id.id,
        }
        if subscription_state == '2_renewal':
            values.update({'tag_ids': subscription.tag_ids.ids})
        return values

    def _compute_kpi(self):
        for subscription in self:
            delta_1month = subscription._get_subscription_delta(fields.Date.today() - relativedelta(months=1))
            delta_3months = subscription._get_subscription_delta(fields.Date.today() - relativedelta(months=3))
            subscription.write({
                'kpi_1month_mrr_delta': delta_1month['delta'],
                'kpi_1month_mrr_percentage': delta_1month['percentage'],
                'kpi_3months_mrr_delta': delta_3months['delta'],
                'kpi_3months_mrr_percentage': delta_3months['percentage'],
            })

    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        if self.is_subscription:
            return self.env.ref('sale_subscription.sale_subscription_action')
        else:
            return super(SaleOrder, self)._get_portal_return_action()

    def _reset_sub_salesperson(self, vals):
        """update salesperson on customer if salesperson on subscription is get changed."""
        new_user_id = vals.get('user_id')
        valid_state_update = vals.get('subscription_state') in SUBSCRIPTION_PROGRESS_STATE
        if new_user_id or valid_state_update:
            for order in self:
                if not order.is_subscription or order.subscription_state not in SUBSCRIPTION_PROGRESS_STATE:
                    continue
                # Update the user responsible of the contact to align the values
                current_partner_user = order.partner_id.user_id
                subscription_user = order.user_id
                if subscription_user != current_partner_user:
                    partner_to_remove = current_partner_user.partner_id - order.partner_id
                    order.message_unsubscribe(partner_ids=partner_to_remove.ids)
                    partners_to_update = order.partner_id
                    # If the partner is a company, keep all child contacts in sync so
                    # portal users see the updated salesperson as well.
                    if order.partner_id.is_company:
                        partners_to_update |= order.partner_id.child_ids
                    partners_to_update.sudo().write({'user_id': subscription_user.id})

    ####################
    # Invoicing Methods #
    ####################

    @api.model
    def _cron_recurring_create_invoice(self):
        deferred_account = self.env.company.deferred_revenue_account_id
        deferred_journal = self.env.company.deferred_revenue_journal_id
        if not deferred_account or not deferred_journal:
            raise ValidationError(_("The deferred settings are not properly set. Please complete them to generate subscription deferred revenues"))
        return self._create_recurring_invoice()

    def _get_invoiceable_lines(self, final=False):
        date_from = self.env.context.get('invoiceable_date_from', fields.Date.today())
        res = super()._get_invoiceable_lines(final=final)
        res = res.filtered(lambda l: not l.recurring_invoice or l.order_id.subscription_state == '7_upsell')
        invoiceable_line_ids = []
        downpayment_line_ids = []
        pending_section = None
        for line in self.order_line:
            if line.display_type == 'line_section':
                # Only add section if one of its lines is invoiceable
                pending_section = line
                continue

            if line.state != 'sale':
                continue

            line_to_invoice = False
            if line in res:
                # Line was already marked as to be invoiced
                line_to_invoice = True
            else:
                line_to_invoice = line._is_subscription_line_to_invoice()

            if line_to_invoice:
                if line.is_downpayment:
                    # downpayment line must be kept at the end in its dedicated section
                    downpayment_line_ids.append(line.id)
                    continue
                if pending_section:
                    invoiceable_line_ids.append(pending_section.id)
                    pending_section = False
                invoiceable_line_ids.append(line.id)

        return self.env["sale.order.line"].browse(invoiceable_line_ids + downpayment_line_ids)

    def _subscription_post_success_free_renewal(self):
        """ Action done after the successful payment has been performed """
        self.ensure_one()
        msg_body = _(
            'Automatic renewal succeeded. Free subscription. Next Invoice: %(inv)s. No email sent.',
            inv=self.next_invoice_date
        )
        self.message_post(body=msg_body)

    def _subscription_post_success_payment(self, transaction, invoices, automatic=True):
        """
         Action done after the successful payment has been performed
        :param transaction: single payment.transaction record
        :param invoices: account.move recordset
        :param automatic: True if the transaction was created during the subscription invoicing cron
        """
        self.ensure_one()
        transaction.ensure_one()
        for invoice in invoices:
            invoice.write({'payment_reference': transaction.reference, 'ref': transaction.reference})
            if automatic:
                msg_body = _(
                    'Automatic payment succeeded. Payment reference: %(ref)s. Amount: %(amount)s. Contract set to: In Progress, Next Invoice: %(inv)s. Email sent to customer.',
                    ref=transaction._get_html_link(title=transaction.reference),
                    amount=transaction.amount,
                    inv=self.next_invoice_date,
                )
            else:
                msg_body = _(
                    'Manual payment succeeded. Payment reference: %(ref)s. Amount: %(amount)s. Contract set to: In Progress, Next Invoice: %(inv)s. Email sent to customer.',
                    ref=transaction._get_html_link(title=transaction.reference),
                    amount=transaction.amount,
                    inv=self.next_invoice_date,
                )
            self.message_post(body=msg_body)
            if invoice.state != 'posted':
                invoice.with_context(ocr_trigger_delta=15)._post()
        AccountMoveSend = self.env['account.move.send']
        if moves_to_send := invoices.filtered(
            lambda move: not move.is_move_sent and AccountMoveSend._get_default_extra_edis(move),
        ):
            AccountMoveSend._generate_and_send_invoices(moves=moves_to_send)

    def _get_subscription_mail_payment_context(self, mail_ctx=None):
        self.ensure_one()
        if not mail_ctx:
            mail_ctx = {}
        billing_details = self._next_billing_details()
        return {**self._context, **mail_ctx, **{'next_invoice_amount': billing_details['next_invoice_amount'],
                                                'total_amount': self.amount_total,
                                                'currency_name': self.currency_id.name,
                                                'responsible_email': self.user_id.email,
                                                'code': self.client_order_ref}}

    def _update_next_invoice_date(self):
        """ Update the next_invoice_date according to the periodicity of the order.
            At quotation confirmation, last_invoice_date is false, next_invoice is start date and start_date is today
            by default. The next_invoice_date should be bumped up each time an invoice is created except for the
            first period.

            The next invoice date should be updated according to these rules :
            -> If the trigger is manuel : We should always increment the next_invoice_date
            -> If the trigger is automatic & date_next_invoice < today :
                    -> If there is a payment_token : We should increment at the payment reconciliation
                    -> If there is no token : We always increment the next_invoice_date even if there is nothing to invoice
            """
        for order in self:
            if not order.is_subscription:
                continue
            last_invoice_date = order.next_invoice_date or order.start_date
            if last_invoice_date:
                order.next_invoice_date = last_invoice_date + order.plan_id.billing_period
                order.last_reminder_date = False

    def _update_subscription_payment_failure_values(self):
        # allow to override the subscription values in case of payment failure
        return {}

    def _post_invoice_hook(self):
        # This method allow a hook after invoicing
        self.order_line._reset_subscription_quantity_post_invoice()

    def _handle_post_invoice_hook_exception(self):
        # Method to overwrite to handle SaleOrderLine._reset_subscription_quantity_post_invoice exceptions.
        return

    def _handle_subscription_payment_failure(self, invoice, transaction):
        current_date = fields.Date.today()
        reminder_mail_template = self.env.ref('sale_subscription.email_payment_reminder', raise_if_not_found=False)
        close_mail_template = self.env.ref('sale_subscription.email_payment_close', raise_if_not_found=False)
        invoice.unlink()
        self.pending_transaction = False
        for order in self:
            auto_close_days = self.plan_id.auto_close_limit or 15
            date_close = order.next_invoice_date + relativedelta(days=auto_close_days)
            close_contract = current_date >= date_close
            email_context = order._get_subscription_mail_payment_context()
            _logger.info('Failed to create recurring invoice for contract %s', order.client_order_ref or order.name)
            if close_contract:
                close_mail_template.with_context(email_context).send_mail(order.id)
                _logger.debug("Sending Contract Closure Mail to %s for contract %s and closing contract",
                              order.partner_id.email, order.id)
                msg_body = _("Automatic payment failed after multiple attempts. Contract closed automatically.")
                order.message_post(body=msg_body)
                subscription_values = {'payment_exception': False}
                # close the contract as needed
                order.set_close(close_reason_id=order.env.ref('sale_subscription.close_reason_auto_close_limit_reached').id)
            else:
                msg_body = _('Automatic payment failed. No email sent this time. Error: %s', transaction and transaction.state_message or _('No valid Payment Method'))
                if (fields.Date.today() - order.next_invoice_date).days in [2, 7, 14]:
                    email_context.update({'date_close': date_close, 'payment_token': order.payment_token_id.display_name, 'payment_link': order.get_portal_url()})
                    reminder_mail_template.with_context(email_context).send_mail(order.id)
                    _logger.debug("Sending Payment Failure Mail to %s for contract %s and setting contract to pending", order.partner_id.email, order.id)
                    msg_body = _('Automatic payment failed. Email sent to customer. Error: %s', transaction and transaction.state_message or _('No Payment Method'))
                order.message_post(body=msg_body)
                # payment failed (not catched in exception) but we should not retry directly.
                # flag with is_batch to avoid processing it again in another batch
                subscription_values = {'payment_exception': False, 'is_batch': True}
            subscription_values.update(order._update_subscription_payment_failure_values())
            order.write(subscription_values)

    def _invoice_is_considered_free(self, invoiceable_lines):
        """
        In some case, we want to skip the invoice generation for subscription.
        By default, we only consider it free if the amount is 0, but we could use other criterion
        :return: bool: true if the contract is free
        :return: bool: true if the contract should be in exception
        """
        # By design if self is a recordset, all currency are similar
        currency = self.currency_id[:1]
        amount_total = sum(invoiceable_lines.mapped('price_total'))
        non_recurring_line = invoiceable_lines.filtered(lambda l: not l.recurring_invoice)
        delivery_invoiceable_lines = invoiceable_lines.filtered(lambda l: l._is_postpaid_line() and l.qty_delivered)
        is_free, is_exception = False, False
        mrr = sum(self.mapped('recurring_monthly'))
        if currency.compare_amounts(mrr, 0) < 0 and non_recurring_line:
            # We have a mix of recurring lines whose sum is negative and non-recurring lines to invoice
            # We don't know what to do
            is_free = True
            is_exception = True
        elif currency.compare_amounts(amount_total, 0) < 1 and not delivery_invoiceable_lines:
            # We can't create an invoice, it will be impossible to validate
            is_free = True
        elif currency.compare_amounts(mrr, 0) < 1 and not non_recurring_line and not delivery_invoiceable_lines:
            # We have a recurring null/negative amount. It is not desired even if we have a non-recurring positive amount
            is_free = True
        return is_free, is_exception

    def _recurring_invoice_domain(self, extra_domain=None):
        if not extra_domain:
            extra_domain = []
        current_date = fields.Date.today()
        search_domain = [('is_batch', '=', False),
                         ('is_invoice_cron', '=', False),
                         ('is_subscription', '=', True),
                         ('subscription_state', '=', '3_progress'),
                         ('payment_exception', '=', False),
                         ('pending_transaction', '=', False),
                         ('company_id.active', '=', True),
                         '|', ('next_invoice_date', '<=', current_date), ('end_date', '<=', current_date)]
        if extra_domain:
            search_domain = expression.AND([search_domain, extra_domain])
        return search_domain

    def _get_invoice_grouping_keys(self):
        if any(self.mapped('is_subscription')):
            return super()._get_invoice_grouping_keys() + ['payment_token_id', 'partner_invoice_id']
        else:
            return super()._get_invoice_grouping_keys()

    def _get_auto_invoice_grouping_keys(self):
        grouping_keys = super()._get_invoice_grouping_keys() + ['payment_token_id', 'partner_invoice_id']
        grouping_keys = list(set(grouping_keys))
        grouping_keys.remove('partner_id')
        return grouping_keys

    def _get_invoiced_subscriptions(self):
        """ return invoiced subscriptions """
        return set(self.env['account.move.line'].search([
            ('subscription_id', 'in', self.ids),
            ('move_type', '=', 'out_invoice'),
            ('move_id.state', 'in', ["draft", "posted"])
        ]).subscription_id.ids)

    def _get_subscriptions_to_invoice(self):
        """ remove subscriptions that should send a reminder instead of invoicing. """
        invoiced_sub_ids = self._get_invoiced_subscriptions()
        # remove subscriptions which have no payment token and online payment true
        # only when prepayment_per is 100 or if there is no invoice in case prepayment_per < 100
        to_invoice_ids = []
        limit = self.env.context.get('limit')
        for sub in self:
            if (sub.payment_token_id or not sub.require_payment
                or (sub.id not in invoiced_sub_ids and sub.prepayment_percent != 1)
                or sub._invoice_is_considered_free(sub.with_context(recurring_automatic=True)._get_invoiceable_lines())[0]):
                to_invoice_ids.append(sub.id)
            if limit and len(to_invoice_ids) >= limit:
                break
        return self.browse(to_invoice_ids)

    def _recurring_invoice_get_subscriptions(self, grouped=False, batch_size=30):
        """ Return a boolean and an iterable of recordsets.
        The boolean is true if batch_size is smaller than the number of remaining records
        If grouped, each recordset contains SO with the same grouping keys.
        """
        need_cron_trigger = False
        limit = False
        if self:
            domain = [('id', 'in', self.ids), ('subscription_state', 'in', SUBSCRIPTION_PROGRESS_STATE), ('company_id.active', '=', True)]
            batch_size = False
        else:
            domain = self._recurring_invoice_domain()
            limit = batch_size and batch_size + 1

        if grouped:
            all_subscriptions = self.read_group(
                domain,
                ['id:array_agg'],
                self._get_auto_invoice_grouping_keys(),
                limit=limit, lazy=False)
            all_subscriptions = [self.browse(res['id']) for res in all_subscriptions]
            need_cron_trigger = batch_size and len(all_subscriptions) > batch_size
            # We get a list of record sets when grouped is true. For each record set in all_subscriptions,
            # we call the '_get_subscriptions_to_invoice' method to process them.
            all_subscriptions = [subscription._get_subscriptions_to_invoice() for subscription in all_subscriptions]
        else:
            all_subscriptions = self.search(domain).with_context(limit=limit)._get_subscriptions_to_invoice()
            need_cron_trigger = batch_size and len(all_subscriptions) > batch_size

        if batch_size:
            all_subscriptions = all_subscriptions[:batch_size]

        return all_subscriptions, need_cron_trigger

    def _subscription_commit_cursor(self, auto_commit):
        if auto_commit:
            self.env.cr.commit()
        else:
            self.env.flush_all()
            self.env.cr.flush()

    def _subscription_rollback_cursor(self, auto_commit):
        if auto_commit:
            self.env.cr.rollback()

    # The following function is used so that it can be overwritten in test files
    def _subscription_launch_cron_parallel(self, batch_size):
        self.env.ref('sale_subscription.account_analytic_cron_for_invoice')._trigger()

    def _get_subscription_payment_exception_condition(self):
        """ Return a boolean if we agree that the payment_exception should be reset.
        This is needed for being able to inherit easily for other use cases than implemented by now.
        """
        return False

    def _create_recurring_invoice(self, batch_size=30):
        today = fields.Date.today()
        auto_commit = not bool(config['test_enable'] or config['test_file'])
        grouped_invoice = self.env['ir.config_parameter'].get_param('sale_subscription.invoice_consolidation', False)
        all_subscriptions, need_cron_trigger = self._recurring_invoice_get_subscriptions(grouped=grouped_invoice, batch_size=batch_size)
        if not all_subscriptions:
            return self.env['account.move']

        # We mark current batch as having been seen by the cron
        all_invoiceable_lines = self.env['sale.order.line']
        order_to_remove_ids = []
        for subscription in all_subscriptions:
            subscription.is_invoice_cron = True
            # Don't spam sale with assigned emails.
            subscription = subscription.with_context(mail_auto_subscribe_no_notify=True)
            # Close ending subscriptions
            auto_close_subscription = subscription.filtered_domain([('end_date', '!=', False)])
            closed_contract = auto_close_subscription._subscription_auto_close()
            subscription -= closed_contract
            order_to_remove_ids += closed_contract.ids
            all_invoiceable_lines += subscription.with_context(recurring_automatic=True)._get_invoiceable_lines()

        if not isinstance(all_subscriptions, list):
            # when all_subscription is a recordset, we remove the closed contracts from it here.
            # When it is a list, we are creating consolidated invoices and they are removed in the
            # `subscription -= closed_contract`` instruction above.
            all_subscriptions -= self.env['sale.order'].browse(order_to_remove_ids)
        lines_to_reset_qty = self.env['sale.order.line']
        account_moves = self.env['account.move']
        move_to_send_ids = []
        # Set quantity to invoice before the invoice creation. If something goes wrong, the line will appear as "to invoice"
        # It prevents the use of _compute method and compare the today date and the next_invoice_date in the compute which would be bad for perfs
        all_invoiceable_lines._reset_subscription_qty_to_invoice()
        self._subscription_commit_cursor(auto_commit)
        for subscription in all_subscriptions:
            if len(subscription) == 1:
                subscription = subscription[0]  # Trick to not prefetch other subscriptions is all_subscription is recordset, as the cache is currently invalidated at each iteration

            # We check that the subscription should not be processed or that it has not already been set to "in exception" by previous cron failure
            # We only invoice contract in sale state. Locked contracts are invoiced in advance. They are frozen.
            subscription = subscription.filtered(lambda sub: sub.subscription_state == '3_progress' and not sub.payment_exception)
            if not subscription:
                continue
            try:
                self._subscription_commit_cursor(auto_commit)  # To avoid a rollback in case something is wrong, we create the invoices one by one
                draft_invoices = subscription.invoice_ids.filtered(lambda am: am.state == 'draft')
                if subscription.payment_token_id and draft_invoices:
                    draft_invoices.button_cancel()
                elif draft_invoices:
                    # Skip subscription if no payment_token, and it has a draft invoice
                    continue
                invoiceable_lines = all_invoiceable_lines.filtered(lambda l: l.order_id.id in subscription.ids)
                invoice_is_free, is_exception = subscription._invoice_is_considered_free(invoiceable_lines)
                if not invoiceable_lines or invoice_is_free:
                    updatable_invoice_date = subscription.filtered(lambda sub: sub.next_invoice_date and sub.next_invoice_date <= today)
                    if is_exception:
                        for sub in subscription:
                            # Mix between recurring and non-recurring lines. We let the contract in exception, it should be
                            # handled manually
                            msg_body = _(
                                "Mix of negative recurring lines and non-recurring line. The contract should be fixed manually",
                                inv=sub.next_invoice_date
                            )
                            sub.message_post(body=msg_body)
                        subscription.payment_exception = True
                    # We still update the next_invoice_date if it is due
                    elif updatable_invoice_date:
                        updatable_invoice_date._update_next_invoice_date()
                        if invoice_is_free:
                            for line in invoiceable_lines:
                                line.qty_invoiced = line.product_uom_qty
                            updatable_invoice_date._subscription_post_success_free_renewal()
                    continue

                try:
                    invoice = subscription.with_context(recurring_automatic=True)._create_invoices(final=True)
                    lines_to_reset_qty |= invoiceable_lines
                except Exception as e:
                    # We only raise the error in test, if the transaction is broken we should raise the exception
                    if not auto_commit and isinstance(e, TransactionRollbackError):
                        raise
                    # we suppose that the payment is run only once a day
                    self._subscription_rollback_cursor(auto_commit)
                    for sub in subscription:
                        email_context = sub._get_subscription_mail_payment_context()
                        error_message = _("Error during renewal of contract %s (Payment not recorded)", sub.name)
                        _logger.exception(error_message)
                        body = self._get_traceback_body(e, error_message)
                        mail = self.env['mail.mail'].sudo().create(
                            {'body_html': body, 'subject': error_message,
                             'email_to': email_context['responsible_email'], 'auto_delete': True})
                        mail.send()
                    continue
                self._subscription_commit_cursor(auto_commit)
                # Handle automatic payment or invoice posting
                existing_invoices = subscription.with_context(recurring_automatic=True)._handle_automatic_invoices(invoice, auto_commit) or self.env['account.move']
                account_moves |= existing_invoices
                if subscription._get_subscription_payment_exception_condition() or all(inv.state != 'draft' for inv in existing_invoices):
                    # when the invoice is not confirmed, we keep it and keep the payment_exception flag
                    # Failed payment that delete the invoice will also be handled here and the flag will be removed
                    subscription.with_context(mail_notrack=True).payment_exception = False
                if not subscription.mapped('payment_token_id'): # _get_auto_invoice_grouping_keys groups by token too
                    move_to_send_ids += existing_invoices.ids
                self._subscription_commit_cursor(auto_commit)
            except Exception:
                name_list = [f"{sub.name} {sub.client_order_ref}" for sub in subscription]
                _logger.exception("Error during renewal of contract %s", "; ".join(name_list))
                self._subscription_rollback_cursor(auto_commit)
        self._subscription_commit_cursor(auto_commit)
        self._process_invoices_to_send(self.env['account.move'].browse(move_to_send_ids))
        self._subscription_commit_cursor(auto_commit)
        # There is still some subscriptions to process. Then, make sure the CRON will be triggered again asap.
        if need_cron_trigger:
            self._subscription_launch_cron_parallel(batch_size)
        else:
            if self:
                invoice_sub = self.filtered('is_subscription')
            else:
                invoice_sub = self.search([('is_invoice_cron', '=', True)])

            try:
                invoice_sub._post_invoice_hook()
                self._subscription_commit_cursor(auto_commit)
            except Exception as e:
                self._subscription_rollback_cursor(auto_commit)
                _logger.exception("Error during post invoice action: %s", e)
                invoice_sub._handle_post_invoice_hook_exception()

            failing_subscriptions = self.search([('is_batch', '=', True)])
            (failing_subscriptions | invoice_sub).write({'is_batch': False, 'is_invoice_cron': False})
            self._subscription_commit_cursor(auto_commit)
        return account_moves

    def _create_invoices(self, grouped=False, final=False, date=None):
        """ Override to increment periods when needed """
        order_already_invoiced = self.env['sale.order']
        for order in self:
            if order.is_subscription and order.order_line.invoice_lines.move_id.filtered(
                    lambda r: r.move_type in ('out_invoice', 'out_refund') and r.state == 'draft'
            ):
                order_already_invoiced |= order
        if order_already_invoiced:
            order_error = ", ".join(order_already_invoiced.mapped('name'))
            raise ValidationError(_("The following recurring orders have draft invoices. Please Confirm them or cancel them "
                                    "before creating new invoices. %s.", order_error))
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)
        return invoices

    def _subscription_auto_close(self):
        """ Handle contracts that need to be automatically closed/set to renews.
        This method is only called during a cron
        """
        current_date = fields.Date.context_today(self)
        close_contract_ids = self.filtered(lambda contract: contract.end_date and contract.end_date <= current_date)
        close_contract_ids.set_close()
        return close_contract_ids

    def _should_post_invoice(self):
        """ This method define the conditions if an invoice should be posted inside the cron creating the subscription invoices.
        It can be overriden to fit other needs
        """
        # We post if we have several different token (for several orders in self) or no token at all
        return not self.payment_token_id or len(self.payment_token_id) > 1

    def _process_auto_invoice(self, invoice):
        """ Hook for extension, to support different invoice states """
        invoice.action_post()
        return

    def _handle_automatic_invoices(self, invoice, auto_commit):
        """ This method handle the subscription with or without payment token """
        Mail = self.env['mail.mail']
        # Set the contract in exception. If something go wrong, the exception remains.
        self.with_context(mail_notrack=True).write({'payment_exception': True})
        payment_token = self.payment_token_id
        if self._should_post_invoice():
            self._process_auto_invoice(invoice)
            return invoice

        if not payment_token.partner_id.country_id:
            msg_body = _('Automatic payment failed. No country specified on payment_token\'s partner')
            for order in self:
                order.message_post(body=msg_body)
            invoice.unlink()
            self._subscription_commit_cursor(auto_commit)
            return

        existing_transactions = self.transaction_ids
        try:
            # execute payment
            self.pending_transaction = True
            if invoice.currency_id.compare_amounts(invoice.amount_total_signed, 0) < 0:
                # Something is wrong, we are trying to create a negative transaction. probably because a manual change in the order
                # payment_exception is still true. We keep the draft invoice to allow salesmen understand what is going on.
                self.pending_transaction = False
                msg_body = _("Automatic payment failed. Check the corresponding invoice %s. We can't automatically process negative payment",
                             invoice._get_html_link())
                for order in self:
                    order.message_post(body=msg_body)
                self._subscription_commit_cursor(auto_commit)
                # We return the draft invoice because it should be analyzed by the accounting to understand the issue
                return invoice
            transaction = self._do_payment(payment_token, invoice, auto_commit=auto_commit)
            # commit change as soon as we try the payment, so we have a trace in the payment_transaction table

            # if no transaction or failure, log error, rollback and remove invoice
            if not transaction or transaction.renewal_state == 'cancel':
                self._handle_subscription_payment_failure(invoice, transaction)
                self._subscription_commit_cursor(auto_commit)
                return
            elif transaction.renewal_state == 'pending':
                self.payment_exception = False
                self._subscription_commit_cursor(auto_commit)
            # if transaction is a success, post a message
            elif transaction.renewal_state == 'authorized':
                self.payment_exception = False
                self._subscription_commit_cursor(auto_commit)
                invoice._post()
                self._subscription_commit_cursor(auto_commit)

        except Exception as e:
            last_tx_sudo = (self.transaction_ids - existing_transactions).sudo()
            if last_tx_sudo and last_tx_sudo.renewal_state in ['pending', 'done']:
                payment_state = _("Payment recorded: %s", last_tx_sudo.reference)
            else:
                payment_state = _("Payment not recorded")
            error_message = _("Error during renewal of contract %(order_ids)s %(order_refs)s %(payment_state)s",
                             order_ids=self.ids,
                             order_refs=format_list(self.env, self.mapped(lambda order: order.client_order_ref or order.name)),
                             payment_state=payment_state)
            body = self._get_traceback_body(e, error_message)
            _logger.exception(error_message)
            self._subscription_rollback_cursor(auto_commit)
            mail = Mail.sudo().create([{
                'body_html': body, 'subject': error_message,
                'email_to': order._get_subscription_mail_payment_context().get('responsible_email'), 'auto_delete': True
            } for order in self])
            mail.send()
            if invoice.state == 'draft':
                if not last_tx_sudo or last_tx_sudo.renewal_state in ['pending', 'authorized']:
                    invoice.unlink()
                    return
        return invoice

    def _get_traceback_body(self, exc, body):
        if not str2bool(self.env['ir.config_parameter'].sudo().get_param('sale_subscription.full_mail_traceback')):
            return plaintext2html("%s\n\n%s" % (body, str(exc)))
        return plaintext2html("%s\n\n%s\n%s" % (
            body,
            ''.join(traceback.format_tb(exc.__traceback__)),
            str(exc)),
        )

    def _get_expired_subscriptions(self):
        # We don't use CURRENT_DATE to allow using freeze_time in tests.
        today = fields.Datetime.today()
        self.env.cr.execute(
            """
                SELECT (so.next_invoice_date + INTERVAL '1 day' * COALESCE(ssp.auto_close_limit,15)) AS "payment_limit",
                           so.next_invoice_date,
                           so.id AS so_id
                  FROM sale_order so
             LEFT JOIN sale_subscription_plan ssp ON ssp.id=so.plan_id
                 WHERE so.is_subscription
                   AND so.state = 'sale'
                   AND so.subscription_state = '3_progress'
                AND (so.next_invoice_date + INTERVAL '1 day' * COALESCE(ssp.auto_close_limit,15))< %s
            """, [today.strftime('%Y-%m-%d')]
        )
        return self.env.cr.dictfetchall()

    def _get_unpaid_subscriptions(self):
        # TODO FLDA SEE THAT O_O
        # We don't use CURRENT_DATE to allow using freeze_time in tests.
        today = fields.Datetime.today()
        self.env.cr.execute(
            """
                WITH payment_limit_query AS (
                      SELECT (aml2.dm + INTERVAL '1 day' * COALESCE(ssp.auto_close_limit,15) ) AS "payment_limit",
                              aml2.dm AS date_maturity,
                              ssp.billing_period_unit AS unit,
                              ssp.billing_period_value AS duration,
                              CASE
                                WHEN ssp.billing_period_unit='week' THEN INTERVAL '1 day' * 7 * ssp.billing_period_value
                                WHEN ssp.billing_period_unit='month' THEN INTERVAL '1 day' * 30 * ssp.billing_period_value
                                WHEN ssp.billing_period_unit='year' THEN INTERVAL '1 day' * 365 * ssp.billing_period_value
                              END AS conversion,
                              ssp.billing_period_value || ' ' || ssp.billing_period_unit AS recurrence,
                              am.payment_state AS payment_state,
                              am.id AS am_id,
                              so.id AS so_id,
                              so.next_invoice_date AS next_invoice_date
                        FROM sale_order so
                        JOIN sale_order_line sol ON sol.order_id = so.id
                        JOIN account_move_line aml ON aml.subscription_id = so.id
                        JOIN account_move am ON am.id = aml.move_id
                        JOIN sale_subscription_plan ssp ON ssp.id=so.plan_id
                        JOIN sale_order_line_invoice_rel rel ON rel.invoice_line_id=aml.id
           LEFT JOIN LATERAL ( SELECT MAX(date_maturity) AS dm FROM account_move_line aml WHERE aml.move_id = am.id) AS aml2 ON TRUE
                      WHERE so.is_subscription
                        AND so.state = 'sale'
                        AND so.subscription_state ='3_progress'
                        AND am.payment_state = 'not_paid'
                        AND am.move_type = 'out_invoice'
                        AND am.state = 'posted'
                        AND rel.order_line_id=sol.id
                   GROUP BY so_id, am_id, ssp.auto_close_limit, payment_state, aml2.dm, ssp.billing_period_unit, ssp.billing_period_value
               )
              SELECT payment_limit::DATE,
                     date_maturity,
                     recurrence,
                     next_invoice_date - plq.conversion AS last_invoice_date,
                     payment_state,
                     am_id,
                     so_id,
                     next_invoice_date
                FROM
                    payment_limit_query plq
                    WHERE payment_limit < %s and payment_limit >= (next_invoice_date - plq.conversion)::DATE
            """, [today.strftime('%Y-%m-%d')]
        )
        return self.env.cr.dictfetchall()

    def _handle_unpaid_subscriptions(self):
        unpaid_result = self._get_unpaid_subscriptions()
        return {res['so_id']: res['am_id'] for res in unpaid_result}

    def _cron_subscription_expiration(self):
        # Flush models according to following SQL requests
        self.env['sale.order'].flush_model(
            fnames=['order_line', 'plan_id', 'state', 'subscription_state', 'next_invoice_date'])
        self.env['account.move'].flush_model(fnames=['payment_state', 'line_ids'])
        self.env['account.move.line'].flush_model(fnames=['move_id', 'sale_line_ids'])
        self.env['sale.subscription.plan'].flush_model(fnames=['auto_close_limit'])
        today = fields.Date.today()
        # set to close if date is passed or if renewed sale order passed
        domain_close = [
            ('is_subscription', '=', True),
            ('end_date', '<', today),
            ('state', '=', 'sale'),
            ('subscription_state', 'in', SUBSCRIPTION_PROGRESS_STATE)]
        subscriptions_close = self.search(domain_close)
        unpaid_results = self._handle_unpaid_subscriptions()
        unpaid_ids = unpaid_results.keys()
        expired_result = self._get_expired_subscriptions()
        expired_ids = [r['so_id'] for r in expired_result]
        subscriptions_close |= self.env['sale.order'].browse(unpaid_ids) | self.env['sale.order'].browse(expired_ids)
        auto_commit = not bool(config['test_enable'] or config['test_file'])
        expired_close_reason = self.env.ref('sale_subscription.close_reason_auto_close_limit_reached')
        unpaid_close_reason = self.env.ref('sale_subscription.close_reason_unpaid_subscription')
        for batched_to_close in split_every(30, subscriptions_close.ids, self.env['sale.order'].browse):
            unpaid_so = self.env['sale.order']
            expired_so = self.env['sale.order']
            for so in batched_to_close:
                if so.subscription_state not in SUBSCRIPTION_PROGRESS_STATE:
                    continue
                if so.id in unpaid_ids:
                    unpaid_so |= so
                    account_move = self.env['account.move'].browse(unpaid_results[so.id])
                    so.message_post(
                        body=_("The last invoice (%s) of this subscription is unpaid after the due date.",
                               account_move._get_html_link()),
                        partner_ids=so.team_user_id.partner_id.ids,
                    )
                elif so.id in expired_ids:
                    expired_so |= so

            unpaid_so.set_close(close_reason_id=unpaid_close_reason.id)
            expired_so.set_close(close_reason_id=expired_close_reason.id)
            (batched_to_close - unpaid_so - expired_so).set_close()
            if auto_commit:
                self.env.cr.commit()
        return dict(closed=subscriptions_close.ids)

    def _get_subscription_delta(self, date):
        self.ensure_one()
        delta, percentage = False, False
        subscription_log = self.env['sale.order.log'].search([
            ('order_id', '=', self.id),
            ('event_type', 'in', ['0_creation', '1_expansion', '15_contraction', '2_transfer']),
            ('event_date', '<=', date)],
            order='event_date desc',
            limit=1)
        if subscription_log:
            delta = self.recurring_monthly - subscription_log.recurring_monthly
            percentage = delta / subscription_log.recurring_monthly if subscription_log.recurring_monthly != 0 else 100
        return {'delta': delta, 'percentage': percentage}

    def _nothing_to_invoice_error_message(self):
        error_message = super()._nothing_to_invoice_error_message()
        if any(self.mapped('is_subscription')):
            error_message += _(
                "\n- You are trying to invoice recurring orders. "
                "Please verify the delivered quantity of product based on invoicing policy, "
                "next invoice date and end date of the contract."
            )
        return error_message

    def _do_payment(self, payment_token, invoice, auto_commit=False):
        values = [{
            'provider_id': payment_token.provider_id.id,
            'payment_method_id': payment_token.payment_method_id.id,
            'sale_order_ids': self.ids,
            'amount': invoice.amount_total,
            'currency_id': invoice.currency_id.id,
            'partner_id': invoice.partner_id.id,
            'token_id': payment_token.id,
            'operation': 'offline',
            'invoice_ids': [(6, 0, [invoice.id])],
            'subscription_action': 'automatic_send_mail',
        }]
        transactions_sudo = self.env['payment.transaction'].sudo().create(values)
        self._subscription_commit_cursor(auto_commit)
        for tx_sudo in transactions_sudo:
            # Protect the transaction row to prevent sql concurrent updates.
            # This cron is having the lead and can update the transaction values from the value returned from the API.
            # No other cursor should be able to update the transaction while this cron is handling this TX
            self.env.cr.execute("SELECT 1 FROM payment_transaction WHERE id=%s FOR NO KEY UPDATE", [tx_sudo.id])
            tx_sudo._send_payment_request()
        return transactions_sudo

    @api.model
    def _process_invoices_to_send(self, account_moves):
        for invoice in account_moves:
            if not invoice.is_move_sent and invoice._is_ready_to_be_sent() and invoice.state == 'posted':
                subscription = invoice.line_ids.subscription_id
                subscription.validate_and_send_invoice(invoice)
                invoice.message_subscribe(subscription.user_id.partner_id.ids)
            elif invoice.line_ids.subscription_id:
                invoice.message_subscribe(invoice.line_ids.subscription_id.user_id.partner_id.ids)

    def validate_and_send_invoice(self, invoice):
        email_context = {**self.env.context.copy(), **{
            'total_amount': invoice.amount_total,
            'email_to': invoice.partner_id.email,
            'code': ', '.join(subscription.client_order_ref or subscription.name for subscription in self),
            'currency': invoice.currency_id.name,
            'no_new_invoice': True}}
        auto_commit = not bool(config['test_enable'] or config['test_file'])
        self._subscription_commit_cursor(auto_commit)
        if self.plan_id.invoice_mail_template_id:
            _logger.debug("Sending Invoice Mail to %s for subscription %s", self.partner_id.mapped('email'), self.ids)
            self.env['account.move.send'].with_context(email_context)._generate_and_send_invoices(
                invoice,
                allow_raising=False,
                allow_fallback_pdf=True,
                mail_template=self.plan_id.invoice_mail_template_id,
            )

    def _assign_token(self, tx):
        """ Callback method to assign a token after the validation of a transaction.
        Note: self.ensure_one()
        :param recordset tx: The validated transaction, as a `payment.transaction` record
        :return: Whether the conditions were met to execute the callback
        """
        if tx.renewal_state == 'authorized':
            self.payment_token_id = tx.token_id.id
            return True
        return False

    def _get_name_portal_content_view(self):
        return 'sale_subscription.subscription_portal_content' if self.is_subscription else super()._get_name_portal_content_view()

    def _get_upsell_portal_url(self):
        self.ensure_one()
        upsell = self.subscription_child_ids.filtered(lambda so: so.subscription_state == '7_upsell' and so.state == 'sent')[:1]
        return upsell and upsell.get_portal_url()

    def _get_renewal_portal_url(self):
        self.ensure_one()
        renewal = self.subscription_child_ids.filtered(lambda so: so.subscription_state == '2_renewal' and so.state == 'sent')[:1]
        return renewal and renewal.get_portal_url()

    def _can_be_edited_on_portal(self):
        self.ensure_one()
        if self.is_subscription:
            return (not self.next_invoice_date or self.next_invoice_date == self.start_date) and \
                self.subscription_state in SUBSCRIPTION_DRAFT_STATE + SUBSCRIPTION_PROGRESS_STATE
        else:
            return super()._can_be_edited_on_portal()

    def _next_billing_details(self):
        """ Prepare the dictionary of next invoice's details i.e product, tax and amount.

        :return: The values of upcoming bill.
        :rtype: dict
        """
        self.ensure_one()
        AccountTax = self.env['account.tax']

        def get_tax_totals(display_lines):
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in display_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
            return AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=self.currency_id or self.company_id.currency_id,
                company=self.company_id,
            )

        display_lines = self._get_invoiceable_lines()
        amount_to_pay = get_tax_totals(display_lines) if display_lines else dict()

        # Considering the product having delivery policy but not deliver
        undelivered_lines = self.order_line.filtered(lambda line: line.product_uom_qty and not line.qty_delivered and line.product_id.invoice_policy == "delivery")
        if undelivered_lines:
            display_lines += undelivered_lines
        # We always display recurring product
        if not display_lines:
            display_lines = self.order_line.filtered(lambda line: line.product_id.recurring_invoice)
        if self.subscription_state == '5_renewed':
            display_lines = self.order_line

        tax_totals = get_tax_totals(display_lines)
        return {
            'sale_order': self,
            'display_lines': display_lines,
            'next_invoice_amount': amount_to_pay.get('total_amount_currency') or 0.0,
            'tax_totals': tax_totals
        }

    def _upsell_activity_line(self):
        self.ensure_one()
        return Markup('&nbsp;<br>').join(
            escape(self.env._('- You delivered %(delivered)s %(name)s and invoiced %(invoiced)s', delivered=line.qty_delivered, name=line.name, invoiced=line.qty_invoiced))
            for line in self.order_line if line.invoice_status == 'upselling'
        )

    def _create_upsell_activity(self):
        subscription = self.filtered('is_subscription')
        super(SaleOrder, self - subscription)._create_upsell_activity()

        for sub in subscription:
            order_ref = sub._get_html_link()
            customer_ref = sub.partner_id._get_html_link()
            lines = sub._upsell_activity_line()
            sub.activity_schedule(
                'sale.mail_act_sale_upsell',
                user_id=sub.user_id.id or sub.partner_id.user_id.id,
                note=_(
                    "Upsell %(order)s for customer %(customer)s for the period %(date_start)s to %(date_end)s %(nl)s%(lines)s",
                    order=order_ref, customer=customer_ref, lines=lines, date_start=sub.last_invoice_date,
                    date_end=sub.next_invoice_date, nl=Markup('&nbsp;<br>')
                )
            )

    def _subscription_reminder_parameters(self):
        """ Compute domain and next invoices dates for subscriptions for which we should send a payment reminder.
            These subscription have no payment token set and online payment is required.
        :return: dict of reminder parameters:
                    Search domain for subscriptions for which we need to send payment reminders.
                    Next invoice dates for which we need to send a
        """
        current_date = fields.Date.today()
        reminder_days = [0, 2, 7, 14, -2, -7, -14]
        reminder_cron = self.env.ref('sale_subscription.send_payment_reminder', raise_if_not_found=False)
        if not reminder_cron:
            return
        last_call = reminder_cron.lastcall
        next_invoice_dates = [current_date + relativedelta(days=x) for x in reminder_days]
        cron_call_shift = last_call and (current_date - last_call.date()).days
        if cron_call_shift and cron_call_shift > 1 and not self.env.context.get('subscription_no_lost_reminder'):
            # if we are the 1st of the month, we want to send reminder for subscriptions whose next_invoice date occurs on
            # - today (1st), 3rd, 8th, 15th of the current month.
            # When the cron is stopped for a few days, we may want to send reminder instead of closing contrats
            # We loop over all the dates when the cron should have run
            check_date = last_call.date() + relativedelta(days=1)
            while check_date < current_date:
                next_invice_date_with_delay = [check_date + relativedelta(days=x) for x in reminder_days]
                check_date += relativedelta(days=1)
                next_invoice_dates += next_invice_date_with_delay
        search_domain = [
            ('is_subscription', '=', True),
            ('subscription_state', '=', '3_progress'),
            ('pending_transaction', '=', False),
            ('payment_token_id', '=', False),
            ('require_payment', '=', True),
            ('last_reminder_date', '!=', current_date),
            # either next invoice date is upcoming (send reminder) or passed (close contract)
            '|', ('next_invoice_date', 'in', list(set(next_invoice_dates))), ('next_invoice_date', '<=', current_date),
        ]
        return {'domain': search_domain, 'next_invoice_dates': set(next_invoice_dates)}

    def _cron_recurring_send_payment_reminder(self):
        """ Sends payment reminders and closes subscriptions nearing auto-close limit.
        Processes subscriptions without payment tokens and requiring online payment.
        """
        today = fields.Date.today()
        parameters = self._subscription_reminder_parameters()
        if not parameters:
            return
        all_subscriptions = self.search(parameters['domain'])
        invoiced_sub_ids = all_subscriptions._get_invoiced_subscriptions()
        for subscription in all_subscriptions:
            if subscription.prepayment_percent != 1 and not subscription.id in invoiced_sub_ids:
                # don't send reminder when prepayment_per <100 and there is no invoice created
                continue
            auto_close_days = subscription.plan_id.auto_close_limit or 15
            date_close = subscription.next_invoice_date + relativedelta(days=auto_close_days)
            close_contract = today >= date_close
            email_context = subscription._get_subscription_mail_payment_context()
            if close_contract and subscription.next_invoice_date not in parameters['next_invoice_dates']:
                # Auto close expired contrat, customer did not paid in time
                close_mail_template = self.env.ref('sale_subscription.email_payment_close', raise_if_not_found=False)
                if close_mail_template:
                    close_mail_template.with_context(email_context).send_mail(subscription.id)
                subscription.set_close(close_reason_id=self.env.ref('sale_subscription.close_reason_auto_close_limit_reached').id)
            else:
                # Send the reminder
                if (not subscription.last_reminder_date or subscription.last_reminder_date != today) and subscription.next_invoice_date in parameters['next_invoice_dates']:
                    reminder_mail_template = self.env.ref('sale_subscription.email_payment_reminder', raise_if_not_found=False)
                    email_context.update({'date_close': date_close, 'payment_link': subscription.get_portal_url()})
                    if reminder_mail_template:
                        reminder_mail_template.with_context(email_context).send_mail(subscription.id)
                        subscription.last_reminder_date = today

    def _get_subscription_invoices(self):
        """
        Return the invoices linked to an order.
        get_invoiced will return the invoices linked to all sale.order of the subscription hierarchy:
         - origin order invoices
         - upsells invoices
         - renewals invoices
        This helper is useful to only get the invoices linked to the current subscription.
        """
        self.ensure_one()
        move = self.env['account.move']
        if self.subscription_state == '7_upsell':
            move = self.order_line.invoice_lines.move_id
        elif self.subscription_state:
            subscription_move_lines = self.env['account.move.line'].search([('subscription_id', 'in', self.ids)])
            move = subscription_move_lines.move_id
        return move

    def _subscribe_followers_to_new_order(self, order):
        """
        Subscribe followers of the subscription to the new order.
        :param order: the new order
        """
        for follower in self.message_follower_ids:
            if follower.partner_id not in order.message_follower_ids.partner_id:
                order.message_subscribe(
                    partner_ids=follower.partner_id.ids,
                    subtype_ids=follower.subtype_ids.ids
                )
