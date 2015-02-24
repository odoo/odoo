# -*- coding: utf-8 -*-
import datetime
from openerp import http
from openerp.http import request
from openerp.addons.website.controllers.main import Website
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

GOOGLE_ANALYTICS_CONFIGURED = 2
GOOGLE_ANALYTICS_PARTIALLY_CONFIGURED = 1
GOOGLE_ANALYTICS_NOT_CONFIGURED = 0


class Versioning_Controller(Website):

    @http.route('/website_version/change_version', type='json', auth="user", website=True)
    def change_version(self, version_id):
        request.session['version_id'] = version_id
        return version_id

    @http.route('/website_version/create_version', type='json', auth="user", website=True)
    def create_version(self, name, version_id=None):
        if not name:
            name = datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        new_version = request.env['website_version.version'].create({'name': name, 'website_id': request.website.id})
        if version_id:
            request.env['website_version.version'].browse(version_id).copy_version(new_version.id)
        request.session['version_id'] = new_version.id
        return new_version.id

    @http.route('/website_version/delete_version', type='json', auth="user", website=True)
    def delete_version(self, version_id):
        version = request.env['website_version.version'].browse(version_id)
        name = version.name
        version.unlink()
        current_id = request.context.get('version_id')
        if version_id == current_id:
            request.session['version_id'] = 0
        return name

    @http.route('/website_version/check_version', type='json', auth="user", website=True)
    def check_version(self, version_id):
        #To check if the version is in a running or paused experiment
        Exp = request.env['website_version.experiment']
        return bool(Exp.search(['|', ('state', '=', 'running'), ('state', '=', 'paused'), ('experiment_version_ids.version_id', '=', version_id)], limit=1))

    @http.route('/website_version/all_versions', type='json', auth="public", website=True)
    def all_versions(self, view_id):
        #To get all versions in the menu
        view = request.env['ir.ui.view'].browse(view_id)
        Version = request.env['website_version.version']
        website_id = request.website.id
        versions = Version.search([('website_id', '=', website_id), '|', ('view_ids.key', '=', view.key), ('view_ids.key', '=', 'website.footer_default')])
        current_version_id = request.context.get('version_id')
        check = False
        result = []
        for ver in versions:
            if ver.id == current_version_id:
                #To show in bold the current version in the menu
                result.append({'id': ver.id, 'name': ver.name, 'bold': 1})
                check = True
            else:
                result.append({'id': ver.id, 'name': ver.name, 'bold': 0})
        #To always show in the menu the current version
        if not check and current_version_id:
            result.append({'id': current_version_id, 'name': Version.browse(current_version_id).name, 'bold': 1})
        return result

    @http.route('/website_version/has_experiments', type='json', auth="user", website=True)
    def has_experiments(self, view_id):
        v = request.env['ir.ui.view'].browse(view_id)
        website_id = request.context.get('website_id')
        return bool(request.env["website_version.experiment.version"].search([('version_id.view_ids.key', '=', v.key), ('experiment_id.website_id.id', '=', website_id)], limit=1))

    @http.route('/website_version/publish_version', type='json', auth="user", website=True)
    def publish_version(self, version_id, save_master, copy_master_name):
        request.session['version_id'] = 0
        return request.env['website_version.version'].browse(version_id).publish_version(save_master, copy_master_name)

    @http.route('/website_version/diff_version', type='json', auth="user", website=True)
    def diff_version(self, version_id):
        mod_version = request.env['website_version.version']
        version = mod_version.browse(version_id)
        name_list = []
        for view in version.view_ids:
            name_list.append({'name': view.name, 'url': '/page/' + view.name.replace(' ', '').lower()})
        return name_list

    @http.route('/website_version/google_access', type='json', auth="user")
    def google_authorize(self, **kw):
        #Check if client_id and client_secret are set to get the authorization from Google
        gs_obj = request.env['google.service']
        gm_obj = request.env['google.management']

        client_id = gs_obj.get_client_id('management', context=kw.get('local_context'))
        client_secret = gs_obj.get_client_secret('management', context=kw.get('local_context'))
        if not client_id or not client_secret:
            dummy, action = request.registry.get('ir.model.data').get_object_reference(request.cr, request.uid, 'website_version', 'action_config_settings_google_management')
            return {
                "status": "need_config_from_admin",
                "url": '',
                "action": action
            }
        url = gm_obj.authorize_google_uri(from_url=kw.get('fromurl'), context=kw.get('local_context'))
        return {
            "status": "need_auth",
            "url": url
        }

    @http.route('/website_version/set_google_access', type='json', auth="user", website=True)
    def set_google_access(self, ga_key, view_id, client_id, client_secret):
        #To set ga_key, view_id, client_id, client_secret
        website_id = request.context.get('website_id')
        web = request.env['website'].browse(website_id)
        web.write({'google_analytics_key': ga_key.strip(), 'google_analytics_view_id': view_id.strip()})
        if client_id and client_secret:
            icp = request.env['ir.config_parameter']
            icp.set_param('google_management_client_id', client_id.strip() or '', groups=['base.group_system'])
            icp.set_param('google_management_client_secret', client_secret.strip() or '', groups=['base.group_system'])

    @http.route('/website_version/all_versions_all_goals', type='json', auth="user", website=True)
    def all_versions_all_goals(self, view_id):
        #To get all versions and all goals to create an experiment
        view = request.env['ir.ui.view']
        version = request.env['website_version.version']
        goal = request.env['website_version.goals']
        icp = request.env['ir.config_parameter']
        v = view.browse(view_id)
        website_id = request.website.id
        tab_version = version.search_read([('website_id', '=', website_id), '|', ('view_ids.key', '=', v.key), ('view_ids.key', '=', 'website.footer_default')], ['id', 'name'])
        tab_goal = goal.search_read([], ['id', 'name'])
        #Check if all the parameters are set to communicate with Google analytics
        if icp.get_param('google_management_token'):
            check_conf = GOOGLE_ANALYTICS_CONFIGURED
            if request.website.google_analytics_key and request.website.google_analytics_view_id:
                check_conf = GOOGLE_ANALYTICS_PARTIALLY_CONFIGURED
        else:
            check_conf = GOOGLE_ANALYTICS_NOT_CONFIGURED
        return {'tab_version': tab_version, 'tab_goal': tab_goal, 'check_conf': check_conf}

    @http.route('/website_version/launch_experiment', type='json', auth="user", website=True)
    def launch_experiment(self, name, version_ids, goal_id):
        existing_experiment = request.env['website_version.experiment'].check_no_overlap(version_ids)
        if not existing_experiment['existing']:
            vals = {'name': name, 'google_id': False, 'state': 'running', 'website_id': request.context.get('website_id'), 'experiment_version_ids': [[0, False, {'frequency': '50', 'version_id': int(version_ids[i]), 'google_index': i+1}] for i in range(len(version_ids))], 'goal_id': int(goal_id)}
            exp_obj = request.env['website_version.experiment']
            exp_obj.create(vals)
        return existing_experiment
