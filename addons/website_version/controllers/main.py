import openerp
from openerp import http
from openerp.http import request
import datetime
from openerp.addons.website.controllers.main import Website

class Versioning_Controller(Website):
        
    @http.route(['/website_version/change_version'], type = 'json', auth = "user", website = True)
    def change_version(self, version_id):
        request.session['version_id'] = int(version_id)
        request.session['master'] = 0
        return version_id

    @http.route(['/website_version/master'], type = 'json', auth = "user", website = True)
    def master(self):
        request.session['version_id'] = 0
        request.session['master'] = 1
        return 0

    @http.route(['/website_version/create_version'], type = 'json', auth = "user", website = True)
    def create_version(self,name,version_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        if name == "":
            name = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        iuv = request.registry['ir.ui.view']
        ver = request.registry['website_version.version']
        website_id = request.website.id
        new_version_id = ver.create(cr, uid,{'name':name, 'website_id':website_id}, context=context)
        if version_id:
            iuv.copy_version(cr, uid, version_id,new_version_id,context=context)
        request.session['version_id'] = new_version_id
        request.context['version_id'] = new_version_id
        request.session['master'] = 0
        return new_version_id

    @http.route(['/website_version/delete_version'], type = 'json', auth = "user", website = True)
    def delete_version(self, version_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        ver = request.registry['website_version.version']
        version_name = ver.browse(cr, uid, int(version_id), context=context).name
        ver.unlink(cr, uid, [int(version_id)], context=context)
        current_id = request.context.get('version_id')
        if int(version_id)== current_id:
            request.session['version_id'] = 0
            request.session['master'] = 1
        return version_name

    @http.route(['/website_version/check_version'], type = 'json', auth = "user", website = True)
    def check_version(self, version_id):
        #To check if the version is in a running or paused experiment
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        Exp = request.registry['website_version.experiment']
        return bool(Exp.search(cr, uid, ['|',('state','=','running'),('state','=','paused'),('experiment_version_ids.version_id', '=', int(version_id))],context=context))
    
    @http.route(['/website_version/all_versions'], type = 'json', auth = "public", website = True)
    def get_all_versions(self, view_id):
        #To get all versions in the menu
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        v = request.registry['ir.ui.view'].browse(cr,uid, int(view_id), context=context)
        ver = request.registry['website_version.version']
        website_id = request.website.id
        ids = ver.search(cr, uid, [('website_id','=',website_id),'|',('view_ids.key','=',v.key),('view_ids.key','=','website.footer_default')],context=context)
        result = ver.read(cr, uid, ids,['id','name'],context=context)
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
            result.append({'id':version_id, 'name':ver.browse(cr, uid, version_id, context=context).name, 'bold':1})
        return result

    @http.route(['/website_version/has_experiments'], type = 'json', auth = "public", website = True)
    def has_experiments(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        v = request.registry['ir.ui.view'].browse(cr, uid, int(view_id),context)
        website_id = context.get('website_id')
        return bool(request.registry["website_version.experiment_version"].search(cr, uid, [('version_id.view_ids.key', '=', v.key),('experiment_id.website_id.id','=',website_id)], context=context))

    @http.route(['/website_version/publish_version'], type = 'json', auth = "public", website = True)
    def publish_version(self, version_id, save_master, copy_master_name):
        #Info: there were some cache problems with browse, this is why the code is so long
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        obj_view = request.registry['ir.ui.view']
        obj = request.registry['website_version.version']
        version = obj.browse(cr, uid, int(version_id),context)
        del_l = []
        copy_l = []
        for view in version.view_ids:
            master_id = obj_view.search(cr, uid, [('key','=',view.key),('version_id', '=', False),('website_id', '=', view.website_id.id)],context=context)
            if master_id:
                #Delete all the website views having a key which is in the version published
                del_l += master_id
                copy_l+= master_id
            else:
                #Views that have no website_id, must be copied because they can be shared with another website
                master_id = obj_view.search(cr, uid, [('key','=',view.key),('version_id', '=', False),('website_id', '=', False)],context=context)
                copy_l+= master_id
        if copy_l:
            if save_master:
                #To check if the name of the version to copy master already exists
                check_id = obj.search(cr, uid, [('name','=', copy_master_name),('website_id', '=', version.website_id.id)],context=context)
                #If it already exists, we delete the old to make the new
                if check_id:
                    obj.unlink(cr, uid, check_id, context=context)
                copy_version_id = obj.create(cr, uid, {'name' : copy_master_name, 'website_id' : version.website_id.id}, context=context)
                for view in obj_view.browse(cr, uid, copy_l, context=context):
                    view.copy({'version_id': copy_version_id, 'website_id' : version.website_id.id})
            #Here, instead of deleting all the views we can just change the version_id BUT I've got some cache problems
            obj_view.unlink(cr, uid, del_l, context=context)
        #All the views in the version published are copied without version_id   
        for view in obj.browse(cr, uid, int(version_id),context).view_ids:
            view.copy({'version_id': None}, context=context)
        request.session['version_id'] = 0
        request.session['master'] = 1
        return version.name

    @http.route(['/website_version/diff_version'], type = 'json', auth = "public", website = True)
    def diff_version(self, version_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        mod_version = request.registry['website_version.version']
        version = mod_version.browse(cr, uid, int(version_id),context)
        name_list = []
        for view in version.view_ids:
            name_list.append(view.name)
        return name_list

    @http.route(['/website_version/get_analytics'], type = 'json', auth = "public", website = True)
    def get_analytics(self, view_id):
        #To get the ExpId and the VarId of the view if it is in a running experiment
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        result = {'ExpId':False, 'VarId': 0}
        obj_v = request.registry['ir.ui.view']
        view = obj_v.browse(cr, uid, int(view_id), context)
        #search all the running experiments with the key of view
        exp_ids = request.registry['website_version.experiment'].search(cr, uid, [('experiment_version_ids.version_id.view_ids.key', '=', view.key),('state','=','running'),('experiment_version_ids.version_id.website_id', '=',request.context['website_id'])],context=context)
        if exp_ids:
            #No overlap between running experiments then we can take the first one
            x = request.registry['website_version.experiment'].browse(cr, uid, exp_ids[0],context)
            result['ExpId'] = x.google_id
            if view.version_id:
                exp_ver_ids = request.registry['website_version.experiment_version'].search(cr, uid, [('experiment_id','=',exp_ids[0]),('version_id','=',view.version_id.id)],context=context)
                if exp_ver_ids:
                    y = request.registry['website_version.experiment_version'].browse(cr, uid, exp_ver_ids[0],context)
                    result['VarId'] = y.google_index  
        return result

    @http.route(['/website_version/google_access'], type='json', auth="user")
    def google_authorize(self, **kw):
        #Check if client_id and client_secret are set to get the authorization from Google
        gs_obj = request.registry['google.service']
        gm_obj = request.registry['google.management']

        client_id = gs_obj.get_client_id(request.cr, request.uid, 'management', context=kw.get('local_context'))
        client_secret = gs_obj.get_client_secret(request.cr, request.uid, 'management', context=kw.get('local_context'))
        if not client_id or not client_secret:
            dummy, action = request.registry.get('ir.model.data').get_object_reference(request.cr, request.uid, 'website_version', 'action_config_settings_google_management')
            return {
                "status": "need_config_from_admin",
                "url": '',
                "action": action
            }
        url = gm_obj.authorize_google_uri(request.cr, request.uid, from_url=kw.get('fromurl'), context=kw.get('local_context'))
        return {
            "status": "need_auth",
            "url": url
        }

    @http.route(['/website_version/set_google_access'], type = 'json', auth = "public", website = True)
    def set_google_access(self, ga_key, view_id, client_id, client_secret):
        #To set ga_key, view_id, client_id, client_secret
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        website_id = context.get('website_id')
        request.registry['website'].write(cr, uid, [website_id], {'google_analytics_key':ga_key, 'google_analytics_view_id':view_id}, context=context)
        icp = request.registry['ir.config_parameter']
        icp.set_param(cr, uid, 'google_management_client_id', client_id or '', groups=['base.group_system'], context=context)
        icp.set_param(cr, uid, 'google_management_client_secret', client_secret or '', groups=['base.group_system'], context=context)


    @http.route(['/website_version/all_versions_all_goals'], type = 'json', auth = "public", website = True)
    def get_all_versions_all_goals(self, view_id):
        #To get all versions and all goals to create an experiment
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        view = request.registry['ir.ui.view']
        version = request.registry['website_version.version']
        goal = request.registry['website_version.goals']
        icp = request.registry['ir.config_parameter']
        v = view.browse(cr,uid, int(view_id), context=context)
        website_id = request.website.id
        version_ids = version.search(cr, uid, [('website_id','=',website_id),'|',('view_ids.key','=',v.key),('view_ids.key','=','website.footer_default')],context=context)
        r1 = version.read(cr, uid, version_ids,['id','name'],context=context)
        goal_ids = goal.search(cr, uid, [],context=context)
        r2 = goal.read(cr, uid, goal_ids,['id','name'],context=context)
        #Check if all the parameters are set to communicate with Google analytics
        if request.website.google_analytics_key and request.website.google_analytics_view_id and icp.get_param(cr, 1, 'google_%s_token' % 'management'):
            r3 = 1
        else:
            r3 = 0
        return {'tab_version':r1, 'tab_goal':r2, 'check_conf': r3}

    @http.route(['/website_version/create_experiment'], type = 'json', auth = "public", website = True)
    def create_experiment(self, name, version_ids, objectives):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        tab = []
        tab = [[0, False, {'frequency': '50', 'version_id': int(x)}] for x in version_ids]
        vals = {'name':name, 'google_id': False, 'state': 'draft', 'website_id':context.get('website_id'), 'experiment_version_ids':tab, 'objectives': int(objectives)}
        exp_obj = request.registry['website_version.experiment']
        exp_obj.create(cr, uid, vals, context=None)

    def check_view(self, version_ids):
        #Check if version_ids don't overlap with running experiments
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        version_keys = set([v['key'] for v in request.registry['ir.ui.view'].search_read(cr, uid, [('version_id', 'in', version_ids)], ['key'], context=context)])
        exp_mod = request.registry['website_version.experiment']
        exp_ids = exp_mod.search(cr,uid,[('state','=','running'),('website_id','=',context.get('website_id'))],context=context)
        exps = exp_mod.browse(cr,uid,exp_ids,context=context)
        for exp in exps:
            for exp_ver in exp.experiment_version_ids:
                for view in exp_ver.version_id.view_ids:
                    if view.key in version_keys:
                        return (False,exp.name)           
        return (True,"")

    @http.route(['/website_version/launch_experiment'], type = 'json', auth = "public", website = True)
    def launch_experiment(self, name, version_ids, objectives):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        tab = []
        check = self.check_view(version_ids)
        if check[0]:
            for x in version_ids:
                tab.append([0, False, {'frequency': '50', 'version_id': int(x)}])
            vals = {'name':name, 'google_id': False, 'state': 'running', 'website_id':context.get('website_id'), 'experiment_version_ids':tab, 'objectives': int(objectives)}
            exp_obj = request.registry['website_version.experiment']
            exp_obj.create(cr, uid, vals, context=None)
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
        




