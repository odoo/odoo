# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models,fields, api, _


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    def _compute_dashboard_button_name(self):
        super(CrmTeam, self)._compute_dashboard_button_name()
        teams_with_opp = self.filtered(lambda team: team.use_opportunities)
        if self._context.get('in_sales_app'):
            teams_with_opp.update({'dashboard_button_name': _("Sales Analysis")})

    def action_primary_channel_button(self):
        if self._context.get('in_sales_app') and self.use_opportunities:
            return self.env["ir.actions.actions"]._for_xml_id("sale.action_order_report_so_salesteam")
        return super(CrmTeam,self).action_primary_channel_button()

    def _graph_get_model(self):
        if self.use_opportunities and self._context.get('in_sales_app') :
            return 'sale.report'
        return super(CrmTeam,self)._graph_get_model()

    def _graph_date_column(self):
        if self.use_opportunities and self._context.get('in_sales_app'):
            return 'date'
        return super(CrmTeam,self)._graph_date_column()

    def _graph_y_query(self):
        if self.use_opportunities and self._context.get('in_sales_app'):
            return 'SUM(price_subtotal)'
        return super(CrmTeam,self)._graph_y_query()

    def _graph_title_and_key(self):
        if self.use_opportunities and self._context.get('in_sales_app'):
            return ['', _('Sales: Untaxed Total')]
        return super(CrmTeam,self)._graph_title_and_key()

    def _extra_sql_conditions(self):
        if self.use_opportunities and self._context.get('in_sales_app'):
            return "AND state = 'sale'"
        return super(CrmTeam,self)._extra_sql_conditions()
