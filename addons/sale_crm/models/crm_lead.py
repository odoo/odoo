# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    sale_amount_total = fields.Monetary(compute='_compute_sale_data', string="Sum of Orders", help="Untaxed Total of Confirmed Orders", currency_field='company_currency')
    quotation_count = fields.Integer(compute='_compute_sale_data', string="Number of Quotations")
    sale_order_count = fields.Integer(compute='_compute_sale_data', string="Number of Sales Orders")
    order_ids = fields.One2many('sale.order', 'opportunity_id', string='Orders')

    @api.depends('order_ids.state', 'order_ids.currency_id', 'order_ids.amount_untaxed', 'order_ids.date_order', 'order_ids.company_id')
    def _compute_sale_data(self):
        for lead in self:
            total = 0.0
            quotation_cnt = 0
            sale_order_cnt = 0
            company_currency = lead.company_currency or self.env.company.currency_id
            for order in lead.order_ids:
                if order.state in ('draft', 'sent'):
                    quotation_cnt += 1
                if order.state not in ('draft', 'sent', 'cancel'):
                    sale_order_cnt += 1
                    total += order.currency_id._convert(
                        order.amount_untaxed, company_currency, order.company_id, order.date_order or fields.Date.today())
            lead.sale_amount_total = total
            lead.quotation_count = quotation_cnt
            lead.sale_order_count = sale_order_cnt

    def _get_quotation_action_context(self):
        return {
            'search_default_opportunity_id': self.id,
            'default_opportunity_id': self.id,
            'search_default_partner_id': self.partner_id.id,
            'default_partner_id': self.partner_id.id,
            'default_team_id': self.team_id.id,
            'default_campaign_id': self.campaign_id.id,
            'default_medium_id': self.medium_id.id,
            'default_origin': self.name,
            'default_name': self.name,
            'default_source_id': self.source_id.id,
            'default_company_id': self.company_id.id or self.env.company.id,
        }

    def action_new_quotation_handle_partner(self):
        """ Check whether a partner is set or not and return the appropriate action. """
        if not self.partner_id:
            return self.env.ref("sale_crm.crm_quotation_partner_action").read()[0]
        else:
            return self.action_new_quotation()

    def _get_base_view_order_action(self, states=()):
        """
        Return the base action to display sales orders. Extended by inheriting modules.
        :param tuple states: The states to use as filter for sales orders
        """
        action = {
            'context': {
                'search_default_draft': 'draft' in states,
                'search_default_partner_id': self.partner_id.id,
                'default_partner_id': self.partner_id.id,
                'default_opportunity_id': self.id
            },
            'domain': [('opportunity_id', '=', self.id), ('state', 'in', states)]
        }
        orders = self.mapped('order_ids').filtered(lambda l: l.state in states)
        if len(orders) == 1:
            action['res_id'] = orders.id
        return action

    def action_new_quotation(self):
        """
        Return a falsy action to be tested by inheriting modules and used as a beacon in the
        inheritance chain so that they don't need to rely on the (non-deterministic) loading order.
        :rtype: None
        """
        return None

    def action_view_order(self):
        """
        Return a falsy action to be tested by inheriting modules and used as a beacon in the
        inheritance chain so that they don't need to rely on the (non-deterministic) loading order.
        :rtype: None
        """
        return None
