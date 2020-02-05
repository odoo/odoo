# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    order_ids = fields.One2many('sale.order', 'opportunity_id', string='Orders')

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

    def _get_filtered_sale_order(self, sale_order=False):
        """Override in sale_renting_crm to return non rental orders"""
        return sale_order

    def action_new_quotation_handle_partner(self):
        """ Check whether a partner is set or not and return the appropriate action. """
        if not self.partner_id:
            return self.env.ref("sale_crm.crm_quotation_partner_action").read()[0]
        else:
            return self.action_new_quotation()

    def _get_base_view_order_action(self, states=(), sale_orders=False):
        """
        Return the base action to display sales orders. Extended by inheriting modules.
        :param tuple states: The states to use as filter for sales orders
        """
        orders = sale_orders.filtered(lambda so: so.state in states)
        domain = [('opportunity_id', '=', self.id), ('state', 'in', states), ('id', 'in', orders.ids)]
        action = {
            'context': {
                'search_default_draft': 'draft' in states,
                'search_default_partner_id': self.partner_id.id,
                'default_partner_id': self.partner_id.id,
                'default_opportunity_id': self.id
            },
            'domain': domain
        }
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
