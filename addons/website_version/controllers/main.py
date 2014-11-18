import openerp
from openerp import http
from openerp.http import request
import datetime
from openerp.addons.website.controllers.main import Website

class Versioning_Controller(Website):
        
    @http.route(['/website_version/change_version'], type = 'json', auth = "user", website = True)
    def change_version(self, version_id):
        request.session['version_id'] = int(version_id)
        return version_id

    @http.route(['/website_version/create_version'], type = 'json', auth = "user", website = True)
    def create_version(self, name, version_id):
        if name == "":
            name = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        website_id = request.website.id
        new_version = request.env['website_version.version'].create({'name':name, 'website_id':website_id})
        if version_id:
            request.env['ir.ui.view'].copy_version(version_id, new_version.id)
        request.session['version_id'] = new_version.id
        return new_version.id

    @http.route(['/website_version/delete_version'], type = 'json', auth = "user", website = True)
    def delete_version(self, version_id):
        version_id = int(version_id)
        name = request.env['website_version.version'].browse(version_id).name
        request.env['website_version.version'].unlink([version_id])
        current_id = request.context.get('version_id')
        if version_id== current_id:
            request.session['version_id'] = 0
        return name

    @http.route(['/website_version/check_version'], type = 'json', auth = "user", website = True)
    def check_version(self, version_id):
        #To check if the version is in a running or paused experiment
        Exp = request.env['website_version.experiment']
        return bool(Exp.search(['|',('state','=','running'),('state','=','paused'),('experiment_version_ids.version_id', '=', int(version_id))]))
    
    @http.route(['/website_version/all_versions'], type = 'json', auth = "public", website = True)
    def get_all_versions(self, view_id):
        #To get all versions in the menu
        v = request.env['ir.ui.view'].browse(int(view_id))
        ver = request.env['website_version.version']
        website_id = request.website.id
        result = ver.search_read([('website_id','=',website_id),'|',('view_ids.key','=',v.key),('view_ids.key','=','website.footer_default')],['id','name'])
        version_id = request.context.get('version_id')
        check = False
        for x in result:
            if x['id'] == version_id:
                x['bold'] = 1
                check = True
            else:
                x['bold'] = 0 
        #To always show in the menu the current version
        if not check and version_id:
            result.append({'id':version_id, 'name':ver.browse(version_id).name, 'bold':1})
        return result

    @http.route(['/website_version/has_experiments'], type = 'json', auth = "public", website = True)
    def has_experiments(self, view_id):
        v = request.env['ir.ui.view'].browse(int(view_id))
        website_id = request.context.get('website_id')
        return bool(request.env["website_version.experiment_version"].search([('version_id.view_ids.key', '=', v.key),('experiment_id.website_id.id','=',website_id)]))

    @http.route(['/website_version/publish_version'], type = 'json', auth = "public", website = True)
    def publish_version(self, version_id, save_master, copy_master_name):
        #Info: there were some cache problems with browse, this is why the code is so long
        obj_view = request.env['ir.ui.view']
        obj = request.env['website_version.version']
        version = obj.browse(int(version_id))
        del_l = []
        copy_l = []
        for view in version.view_ids:
            master = obj_view.search([('key','=',view.key),('version_id', '=', False),('website_id', '=', view.website_id.id)])
            if master:
                #Delete all the website views having a key which is in the version published
                del_l += [master.id]
                copy_l+= [master.id]
            else:
                #Views that have no website_id, must be copied because they can be shared with another website
                master = obj_view.search([('key','=',view.key),('version_id', '=', False),('website_id', '=', False)])
                copy_l+= [master.id]
        if copy_l:
            if save_master:
                #To check if the name of the version to copy master already exists
                check = obj.search([('name','=', copy_master_name),('website_id', '=', version.website_id.id)])
                #If it already exists, we delete the old to make the new
                if check:
                    obj.unlink(check.id)
                from pudb import set_trace; set_trace()
                copy_version_id = obj.create({'name' : copy_master_name, 'website_id' : version.website_id.id})
                for view in obj_view.browse(copy_l):
                    view.copy({'version_id': copy_version_id, 'website_id' : version.website_id.id})
            #Here, instead of deleting all the views we can just change the version_id BUT I've got some cache problems
            obj_view.unlink(del_l)
        #All the views in the version published are copied without version_id   
        for view in obj.browse(int(version_id)).view_ids:
            view.copy({'version_id': None})
        request.session['version_id'] = 0
        return version.name

    @http.route(['/website_version/diff_version'], type = 'json', auth = "public", website = True)
    def diff_version(self, version_id):
        mod_version = request.env['website_version.version']
        version = mod_version.browse(int(version_id))
        name_list = []
        for view in version.view_ids:
            name_list.append(view.name)
        return name_list

    @http.route(['/website_version/get_analytics'], type = 'json', auth = "public", website = True)
    def get_analytics(self, view_id):
        #To get the ExpId and the VarId of the view if it is in a running experiment
        result = {'ExpId':False, 'VarId': 0}
        obj_v = request.env['ir.ui.view']
        view = obj_v.browse(int(view_id))
        #search all the running experiments with the key of view
        exp_ids = request.env['website_version.experiment'].search([('experiment_version_ids.version_id.view_ids.key', '=', view.key),('state','=','running'),('experiment_version_ids.version_id.website_id', '=',request.context['website_id'])])
        if exp_ids:
            #No overlap between running experiments then we can take the first one
            x = request.env['website_version.experiment'].browse(exp_ids[0])
            result['ExpId'] = x.google_id
            if view.version_id:
                exp_ver_ids = request.env['website_version.experiment_version'].search([('experiment_id','=',exp_ids[0]),('version_id','=',view.version_id.id)])
                if exp_ver_ids:
                    y = request.env['website_version.experiment_version'].browse(exp_ver_ids[0])
                    result['VarId'] = y.google_index  
        return result

    @http.route(['/website_version/google_access'], type='json', auth="user")
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

    @http.route(['/website_version/set_google_access'], type = 'json', auth = "public", website = True)
    def set_google_access(self, ga_key, view_id, client_id, client_secret):
        #To set ga_key, view_id, client_id, client_secret
        website_id = request.context.get('website_id')
        request.env['website'].write([website_id], {'google_analytics_key':ga_key, 'google_analytics_view_id':view_id})
        icp = request.env['ir.config_parameter']
        icp.set_param('google_management_client_id', client_id or '', groups=['base.group_system'])
        icp.set_param('google_management_client_secret', client_secret or '', groups=['base.group_system'])


    @http.route(['/website_version/all_versions_all_goals'], type = 'json', auth = "public", website = True)
    def get_all_versions_all_goals(self, view_id):
        #To get all versions and all goals to create an experiment
        view = request.env['ir.ui.view']
        version = request.env['website_version.version']
        goal = request.env['website_version.goals']
        icp = request.env['ir.config_parameter']
        v = view.browse(int(view_id))
        website_id = request.website.id
        version_ids = version.search([('website_id','=',website_id),'|',('view_ids.key','=',v.key),('view_ids.key','=','website.footer_default')])
        r1 = version.read(version_ids,['id','name'])
        goal_ids = goal.search([])
        r2 = goal.read(goal_ids,['id','name'])
        #Check if all the parameters are set to communicate with Google analytics
        if request.website.google_analytics_key and request.website.google_analytics_view_id and icp.get_param('google_%s_token' % 'management'):
            r3 = 1
        else:
            r3 = 0
        return {'tab_version':r1, 'tab_goal':r2, 'check_conf': r3}

    @http.route(['/website_version/create_experiment'], type = 'json', auth = "public", website = True)
    def create_experiment(self, name, version_ids, objectives):
        tab = []
        tab = [[0, False, {'frequency': '50', 'version_id': int(x)}] for x in version_ids]
        vals = {'name':name, 'google_id': False, 'state': 'draft', 'website_id':request.context.get('website_id'), 'experiment_version_ids':tab, 'objectives': int(objectives)}
        exp_obj = request.env['website_version.experiment']
        exp_obj.create(vals)

    def check_view(self, version_ids):
        #Check if version_ids don't overlap with running experiments
        version_keys = set([v['key'] for v in request.env['ir.ui.view'].search_read([('version_id', 'in', version_ids)], ['key'])])
        exp_mod = request.registry['website_version.experiment']
        exp_ids = exp_mod.search([('state','=','running'),('website_id','=',request.context.get('website_id'))])
        exps = exp_mod.browse(exp_ids)
        for exp in exps:
            for exp_ver in exp.experiment_version_ids:
                for view in exp_ver.version_id.view_ids:
                    if view.key in version_keys:
                        return (False,exp.name)           
        return (True,"")

    @http.route(['/website_version/launch_experiment'], type = 'json', auth = "public", website = True)
    def launch_experiment(self, name, version_ids, objectives):
        tab = []
        check = self.check_view(version_ids)
        if check[0]:
            for x in version_ids:
                tab.append([0, False, {'frequency': '50', 'version_id': int(x)}])
            vals = {'name':name, 'google_id': False, 'state': 'running', 'website_id':request.context.get('website_id'), 'experiment_version_ids':tab, 'objectives': int(objectives)}
            exp_obj = request.env['website_version.experiment']
            exp_obj.create(vals)
        return check

    @http.route('/website_version/customize_template_get', type='json', auth='user', website=True)
    def customize_template_get(self, key, **kw):
        result = Website.customize_template_get(self, key, full=False, bundles=False)
        check = []
        res = []
        for data in result:
            if data['name'] not in check:
                check.append(data['name'])
                res.append(data)
        return res
        




