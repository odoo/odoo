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
            return "AND state in ('sale', 'done', 'pos_done')"
        return super(CrmTeam,self)._extra_sql_conditions()

    def _merge_leads(self, leads, values):
        """ Remove opportunities or leads from ["leads_dups_dict"] that
        have sale orders and the company of the sale order is not the same
        as the company of the head lead, its sale order, or current company.
        :param leads: recordset of leads to assign to current team;
        :param values: dictionary in the following form
                       {
                            'leads_assigned': crm.lead(),
                            'leads_dups_dict': {crm.lead(): crm.lead()}
                       };
        :return: Opportunities or leads that have sale orders, and the company
        of the sale order is not the same as the company of the head lead, its
        sale order, or current company.
        """
        new_leads = self.env['crm.lead']
        for lead, lead_dups_dict in values['leads_dups_dict'].items():
            if lead_dups_dict.order_ids \
               and len(lead_dups_dict.order_ids.company_id + lead_dups_dict.company_id) > 1:

                opportunities = lead_dups_dict._sort_by_confidence_level(reverse=True)
                head_opportunity = opportunities[0]
                current_company = head_opportunity.company_id or head_opportunity.order_ids.company_id or self.env['res.company']
                leads_with_so_different_company = opportunities.filtered(
                    lambda lead: lead.order_ids and lead.order_ids.company_id != current_company
                )
                if not leads_with_so_different_company:
                    continue
                leads_compatible_with_head_opportunity = lead_dups_dict - leads_with_so_different_company

                if len(leads_compatible_with_head_opportunity) >= 2:
                    if lead in leads_with_so_different_company:
                        new_leads += head_opportunity
                    values['leads_dups_dict'] = {new_leads or lead: leads_compatible_with_head_opportunity}
                    opportunities = values['different_company'] = leads_with_so_different_company
                separator = ', ' if len(opportunities) > 2 else ' and '
                body = _('%s could not be merged because at least one of their Sales Orders (%s) is linked to another Company.',
                         separator.join(opportunities.mapped(lambda o: f'{o.name}(ID#{o.id})')),
                         ", ".join(opportunities.order_ids.mapped('name')))

                opportunities._message_merging_leads_failed(body)
                if len(leads_compatible_with_head_opportunity) < 2:
                    return {
                        'different_company': set(opportunities.ids),
                    }

        return super(CrmTeam, self)._merge_leads(new_leads or leads, values)
