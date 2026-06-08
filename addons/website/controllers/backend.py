# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home


class WebsiteBackend(http.Controller):

    @http.route('/website/fetch_dashboard_data', type="jsonrpc", auth='user', readonly=True)
    def fetch_dashboard_data(self, website_id):
        Website = request.env['website']
        has_group_system = request.env.user.has_group('base.group_system')
        has_group_designer = request.env.user.has_group('website.group_website_designer')
        dashboard_data = {
            'groups': {
                'system': has_group_system,
                'website_designer': has_group_designer
            },
            'dashboards': {}
        }

        current_website = website_id and Website.browse(website_id) or self.env.website
        multi_website = request.env.user.has_group('website.group_multi_website')
        websites = multi_website and request.env['website'].search([]) or current_website
        dashboard_data['websites'] = websites.read(['id', 'name'])
        for website in dashboard_data['websites']:
            if website['id'] == current_website.id:
                website['selected'] = True

        if has_group_designer:
            dashboard_data['dashboards']['plausible_share_url'] = current_website._get_plausible_share_url()
        return dashboard_data

    @http.route('/website/iframefallback', type="http", auth='user', website=True, readonly=True)
    def get_iframe_fallback(self):
        return request.render('website.iframefallback')


class WebsiteBackendHome(Home):

    @http.route()
    def web_client(self, s_action=None, **kw):
        website_actions = ('website.website_configurator', 'website.website_preview', 'website.action_website_configuration')
        subpath = kw.get('subpath', '')
        is_website_action = False
        if subpath.startswith('action-'):
            action = subpath[7:]
            is_website_action = action in website_actions
            for website_action in website_actions:
                is_website_action = is_website_action or action == str(self.env['ir.model.data']._xmlid_to_res_id(website_action))

        if (is_website_action
            and not self.env.context.get('website_id')
            and (website_id := request.session.get('force_website_id') or self.env.context.get('host_id'))
            and website_id in self.env['website'].get_all().ids):
            request.update_context(website_id=website_id)

        return super().web_client(s_action, **kw)
