# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from datetime import date

from odoo import api, fields, models, tools
from odoo.osv import expression

from odoo.addons.resource.models.utils import filter_domain_leaf
from odoo.addons.sale.models.sale_order import SALE_ORDER_STATE
from odoo.addons.sale_subscription.models.sale_order import SUBSCRIPTION_PROGRESS_STATE, SUBSCRIPTION_STATES



class SaleOrderLogReport(models.Model):
    _name = "sale.order.log.report"
    _description = "Sales Log Analysis Report"
    _order = 'order_id desc, event_date desc, id desc'
    _auto = False

    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', readonly=True)
    client_order_ref = fields.Char(string="Customer Reference", readonly=True)
    event_type = fields.Selection(
        string='Type of event',
        selection=[('0_creation', 'New'),
                   ('1_expansion', 'Expansion'),
                   ('15_contraction', 'Contraction'),
                   ('2_churn', 'Churn'),
                   ('3_transfer', 'Transfer')],
        readonly=True
    )
    event_date = fields.Date(readonly=True)
    contract_number = fields.Integer("Active Subscriptions Change", readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    amount_signed = fields.Monetary("MRR Change", readonly=True, currency_field='log_currency_id')
    mrr_change_normalized = fields.Monetary('MRR Change (normalized)', readonly=True)
    arr_change_normalized = fields.Monetary('ARR Change (normalized)', readonly=True)
    recurring_monthly = fields.Monetary('Monthly Recurring Revenue', readonly=True, currency_field='log_currency_id')
    recurring_yearly = fields.Monetary('Annual Recurring Revenue', readonly=True, currency_field='log_currency_id')
    template_id = fields.Many2one('sale.order.template', 'Subscription Template', readonly=True)
    plan_id = fields.Many2one('sale.subscription.plan', 'Plan', readonly=True)
    country_id = fields.Many2one('res.country', 'Customer Country', readonly=True)
    industry_id = fields.Many2one('res.partner.industry', 'Customer Industry', readonly=True)
    commercial_partner_id = fields.Many2one('res.partner', 'Customer Entity', readonly=True)
    subscription_state = fields.Selection(SUBSCRIPTION_STATES, readonly=True)
    state = fields.Selection(selection=SALE_ORDER_STATE, string="Status", readonly=True)
    health = fields.Selection([
        ('normal', 'Neutral'),
        ('done', 'Good'),
        ('bad', 'Bad')], string="Health", readonly=True)
    campaign_id = fields.Many2one('utm.campaign', 'Campaign', readonly=True)
    origin_order_id = fields.Many2one('sale.order', 'First Order', readonly=True)
    order_id = fields.Many2one('sale.order', 'Sale Order', readonly=True)
    first_contract_date = fields.Date('First Contract Date', readonly=True)
    end_date = fields.Date(readonly=True)
    close_reason_id = fields.Many2one("sale.order.close.reason", string="Close Reason", readonly=True)
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id')
    log_currency_id = fields.Many2one('res.currency')

    @api.depends_context('allowed_company_ids')
    def _compute_currency_id(self):
        self.currency_id = self.env.company.currency_id

    def _with(self):
        companies = self.env['res.company'].search([], order='id asc')
        main_company_id = companies[:1]
        return f"""
        rate_query AS(
            SELECT DISTINCT ON (rc.id)
                   rc.id AS currency_id,
                   COALESCE(rcr.name, CURRENT_DATE) AS rate_date,
                   COALESCE(rcr.rate, 1) AS rate
              FROM res_currency rc
              LEFT JOIN res_currency_rate rcr ON rc.id = rcr.currency_id
             WHERE rc.active = true 
               AND (rcr.company_id IS NULL OR (rcr.company_id = {main_company_id.id} AND rcr.name <= CURRENT_DATE))
          ORDER BY rc.id, rcr.name DESC
        )
        """

    def _select(self):
        select = """
            log.id AS id,
            so.client_order_ref AS client_order_ref,
            log.order_id AS order_id,
            log.event_type AS event_type,
            log.event_date AS event_date,
            log.currency_id AS currency_id,
            so.user_id AS user_id,
            so.team_id AS team_id,
            so.partner_id AS partner_id,
            partner.country_id AS country_id,
            partner.industry_id AS industry_id,
            so.sale_order_template_id AS template_id,
            so.plan_id AS plan_id,
            so.health AS health,
            log.company_id,
            partner.commercial_partner_id AS commercial_partner_id,
            so.subscription_state AS subscription_state,
            so.state AS state,
            so.pricelist_id AS pricelist_id,
            log.origin_order_id AS origin_order_id,
            log.amount_signed AS amount_signed,
            log.recurring_monthly AS recurring_monthly,
            log.recurring_monthly * 12 AS recurring_yearly,
            log.amount_signed * r2.rate/r1.rate AS mrr_change_normalized,
            log.amount_signed * 12 * r2.rate/r1.rate AS arr_change_normalized,
            r1.rate AS currency_rate,
            r2.rate AS user_rate,
            log.currency_id AS log_currency_id,
            log.company_id AS log_cmp,
            CASE
                WHEN event_type = '0_creation' THEN 1
                WHEN event_type = '2_churn' THEN -1
                ELSE 0
            END as contract_number,
            so.campaign_id AS campaign_id,
            so.first_contract_date AS first_contract_date,
            so.end_date AS end_date,
            so.close_reason_id AS close_reason_id
        """
        return select

    def _from(self):
        # To avoid looking at the res_currency table for all records, we build a small table with one line per
        # activated currency. Joining on these values will be faster.
        currency_id = self.env.company.currency_id.id
        active_id = self.env.context.get('active_model') == 'sale.order' and self.env.context.get('active_id')
        if active_id:
            currency_id = self.env['sale.order'].browse(active_id).currency_id.id
        return f"""
            sale_order_log log
            JOIN sale_order so ON so.id = log.order_id
            JOIN res_partner partner ON so.partner_id = partner.id
            LEFT JOIN sale_order_close_reason close ON close.id=so.close_reason_id
            JOIN rate_query r1 ON r1.currency_id=log.currency_id
            JOIN rate_query r2 ON r2.currency_id={currency_id}
        """

    def _where(self):
        return """
            so.is_subscription
        """

    def _group_by(self):
        return """
            log.id,
            log.order_id,
            log.event_type,
            log.event_date,
            so.name,
            so.client_order_ref,
            so.date_order,
            so.partner_id,
            so.sale_order_template_id,
            so.user_id,
            so.subscription_state,
            so.state,
            so.first_contract_date,
            so.end_date,
            log.origin_order_id,
            so.plan_id,
            so.company_id,
            so.health,
            so.campaign_id,
            so.pricelist_id,
            so.currency_rate,
            r1.rate,
            r2.rate,
            so.team_id,
            partner.country_id,
            partner.industry_id,
            partner.commercial_partner_id,
            log.company_id,
            so.close_reason_id
        """

    @property
    def _table_query(self):
        return self._query()

    def _query(self):
        return f"""
              WITH {self._with()}
            SELECT {self._select()}
              FROM {self._from()}
             WHERE {self._where()}
          GROUP BY {self._group_by()}
        """

    def action_open_sale_order(self):
        self.ensure_one()
        if self.origin_order_id:
            action = self.order_id._get_associated_so_action()
            action['views'] = [(self.env.ref('sale_subscription.sale_subscription_primary_form_view').id, 'form')]
            orders = self.env['sale.order'].search(['|', ('origin_order_id', '=', self.origin_order_id.id), ('id', '=', self.origin_order_id.id)]).\
                filtered(lambda so: so.subscription_state in SUBSCRIPTION_PROGRESS_STATE + ['churn'])
            order_id = orders and max(orders.ids) or self.order_id.id
            action['res_id'] = order_id
            return action
        return {
            'res_model': self._name,
            'type': 'ir.actions.act_window',
            'views': [[False, "form"]],
            'res_id': self.id,
        }

    def _convert_range_to_datetime(self, group_res):
        if group_res.get('__range'):
            date_strs = re.findall(r'\b[0-9]{4}-[0-9]{2}-[0-9]{2}', str(group_res['__range']))
            min_date = date_strs and min(date_strs)
            max_date = date_strs and max(date_strs)
            return fields.Datetime.from_string(min_date), fields.Datetime.from_string(max_date)
        return None, None
