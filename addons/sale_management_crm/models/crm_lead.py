# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_new_quotation(self):
        action = super().action_new_quotation()
        if not action:
            action = self.env.ref("sale_management_crm.new_quotation_action").read()[0]
            action['context'] = self._get_quotation_action_context()
        return action

    def action_view_order(self):
        action = super().action_view_order()
        if not action:
            if self.env.context.get('order_status') == 'quotation':
                action_id = 'sale.action_quotations_with_onboarding'
                order_states = ('draft', 'sent')
            else:
                action_id = 'sale.action_orders'
                order_states = ('sale', 'done')
            action = self.env.ref(action_id).read()[0]
            action.update(self._get_base_view_order_action(states=order_states))
            if action.get('res_id'):
                action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        return action
