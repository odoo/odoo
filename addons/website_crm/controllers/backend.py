# -*- coding: utf-8 -*-
from datetime import timedelta

import babel

from odoo import fields, http
from odoo.http import request
from odoo.addons.website.controllers.backend import WebsiteBackend


class WebsiteCrmBackend(WebsiteBackend):

    @http.route()
    def fetch_dashboard_data(self, date_from, date_to):

        results = super(WebsiteCrmBackend, self).fetch_dashboard_data(date_from, date_to)

        lead_domain = [
            ('team_id.website_ids', '!=', False),
        ]

        leads = request.env['crm.lead'].search(
            lead_domain + [
                ('create_date', '>=', date_from),
                ('create_date', '<=', date_to)],
            )

        leads_data = [{
            'create_date': fields.Date.to_string(fields.Date.from_string(lead.create_date)),  # convert Datetime to Date
            'campaign_id': lead.campaign_id.name,
            'medium_id': lead.medium_id.name,
            'source_id': lead.source_id.name,
        } for lead in leads]

        py_obj_date_from = fields.Date.from_string(date_from)
        py_obj_date_to = fields.Date.from_string(date_to)

        leads_graph = self._compute_lead_graph(py_obj_date_from, py_obj_date_to, lead_domain)
        previous_leads_graph = self._compute_lead_graph(py_obj_date_from - timedelta(days=(py_obj_date_to - py_obj_date_from).days), py_obj_date_from, lead_domain, previous=True)

        results['dashboards']['leads'] = {
            'graph': [
                {
                    'values': leads_graph,
                    'key': 'Leads',
                },
                {
                    'values': previous_leads_graph,
                    'key': 'Previous Leads',
                },
            ],
            'leads': leads_data,
        }

        return results

    def _compute_lead_graph(self, date_from, date_to, lead_domain, previous=False):

        days_between = (date_to - date_from).days
        date_list = [(date_from + timedelta(days=x)) for x in range(days_between + 1)]

        daily_leads = request.env['crm.lead'].read_group(
            domain=lead_domain + [
                ('create_date', '>=', fields.Date.to_string(date_from)),
                ('create_date', '<=', fields.Date.to_string(date_to))],
            fields=['create_date'],
            groupby='create_date:day')

        daily_leads_dict = {l['create_date:day']: l['create_date_count'] for l in daily_leads}

        leads_graph = [{
            '0': fields.Date.to_string(d) if not previous else fields.Date.to_string(d + timedelta(days=days_between)),
            # Respect read_group format in models.py
            '1': daily_leads_dict.get(babel.dates.format_date(d, format='dd MMM yyyy', locale=request.env.context.get('lang', 'en_US')), 0)
        } for d in date_list]
        return leads_graph
