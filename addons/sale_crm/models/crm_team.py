# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.addons import base
from odoo.addons import sale


class CrmLead(sale.models.Lead):

    def _compute_dashboard_button_name(self):
        super()._compute_dashboard_button_name()
        teams_with_opp = self.filtered(lambda team: team.use_opportunities)
        if self._context.get('in_sales_app'):
            teams_with_opp.update({'dashboard_button_name': _("Sales Analysis")})

    def action_primary_channel_button(self):
        if self._context.get('in_sales_app') and self.use_opportunities:
            return base.IrActions(self.env)._for_xml_id("sale.action_order_report_so_salesteam")
        return super().action_primary_channel_button()

    def _graph_get_model(self):
        if self.use_opportunities and self._context.get('in_sales_app') :
            return 'sale.report'
        return super()._graph_get_model()

    def _graph_date_column(self):
        if self.use_opportunities and self._context.get('in_sales_app'):
            return 'date'
        return super()._graph_date_column()

    def _graph_y_query(self):
        if self.use_opportunities and self._context.get('in_sales_app'):
            return 'SUM(price_subtotal)'
        return super()._graph_y_query()

    def _graph_title_and_key(self):
        if self.use_opportunities and self._context.get('in_sales_app'):
            return ['', _('Sales: Untaxed Total')]
        return super()._graph_title_and_key()

    def _extra_sql_conditions(self):
        if self.use_opportunities and self._context.get('in_sales_app'):
            return "AND state = 'sale'"
        return super()._extra_sql_conditions()
