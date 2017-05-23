# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import http
from odoo.http import request


class WebsiteBackend(http.Controller):

    @http.route('/website/fetch_dashboard_data', type="json", auth='user')
    def fetch_dashboard_data(self, date_from, date_to):
        has_group_system = request.env['res.users'].has_group('base.group_system')
        has_group_designer = request.env['res.users'].has_group('website.group_website_designer')
        if has_group_system:
            apps_data = dict((app['name'], app) for app in request.env['ir.module.module'].sudo().search_read(
                ['|', ('name', 'ilike', 'website'), ('application', '=', True)],
                ['id', 'sequence', 'name', 'shortdesc', 'state'],
                order='sequence ASC'))
        else:
            apps_data = {}
        dashboard_data = {
            'groups': {
                'system': has_group_system,
                'website_designer': has_group_designer
            },
            'currency': request.env.user.company_id.currency_id.id,
            'dashboards': {
                'apps_data': apps_data,
                'visits': {},
            }
        }
        if has_group_designer:
            ga_dashboard = request.env['ir.values'].sudo().get_default('website.config.settings', 'has_google_analytics_dashboard')
            if ga_dashboard:
                ga_client_id = request.env['ir.config_parameter'].sudo().get_param('google_management_client_id', default='')
                dashboard_data['dashboards']['visits']['ga_client_id'] = ga_client_id

        website_planner = request.env.ref('website.planner_website')
        if website_planner.active:
            self._update_config_step(dashboard_data)

        return dashboard_data

    @http.route('/website/dashboard/config/step', type="json", auth='user')
    def dashboard_config_step(self, step):
        return getattr(self, '_on_action_%s' % step)(step)

    def _on_action_close(self, step):
        planner = request.env.ref('website.planner_website')
        planner.active = False
        return 'website.backend_dashboard'

    def _on_action_homepage(self, step):
        return 'website.action_website'

    def _on_action_company_data(self, step):
        company = request.env['res.company']._company_default_get()
        view_id = request.env.ref('base.view_company_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.company',
            'target': 'new',
            'view_mode': 'form',
            'res_id': company.id,
            'views': [[view_id, 'form']]
        }

    def _on_action_website_feature(self, step):
        website_categ_id = request.env.ref('base.module_category_website').id
        self._mark_step_complete(step)
        action = request.env.ref('base.open_module_tree').read()[0]
        action['context'] = {'search_default_category_id': website_categ_id, 'search_default_app': True}
        return action

    def _on_action_domain(self, step):
        self._mark_step_complete(step)
        return 'website.action_domain_name'

    def _mark_step_complete(self, step):
        website_planner = request.env.ref('website.planner_website')
        data = website_planner.data and json.loads(website_planner.data) or {}
        data[step] = True
        website_planner.data = json.dumps(data)

    def _update_config_step(self, dashboard_data):
        website_planner = request.env.ref('website.planner_website')
        data = website_planner.data and json.loads(website_planner.data) or {}
        company = request.env.user.company_id

        if 'company_data' not in data:
            is_company_data_set = (company.street or company.street2) and company.name and company.city and company.zip and company.country_id.code
            if is_company_data_set:
                data['company_data'] = True
        if 'homepage' not in data:
            is_website_tour_finish = request.env['web_tour.tour'].search_count([('name', '=', 'banner')])
            if is_website_tour_finish:
                data['homepage'] = True
        dashboard_data['website_step'] = data
