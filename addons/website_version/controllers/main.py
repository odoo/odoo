import openerp
from openerp import http
from openerp.http import request
import datetime

class TableExporter(http.Controller):
        
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
        snap = request.registry['website_version.version']
        website_id = request.website.id
        new_version_id = snap.create(cr, uid,{'name':name, 'website_id':website_id}, context=context)
        if version_id:
            iuv.copy_version(cr, uid, version_id,new_version_id,context=context)
        request.session['version_id'] = new_version_id
        request.context['version_id'] = new_version_id
        request.session['master'] = 0
        return new_version_id

    @http.route(['/website_version/delete_version'], type = 'json', auth = "user", website = True)
    def delete_version(self, version_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snap = request.registry['website_version.version']
        version_name = snap.browse(cr, uid, [int(version_id)], context=context)[0].name
        snap.unlink(cr, uid, [int(version_id)], context=context)
        current_id = request.context.get('version_id')
        if int(version_id)== current_id:
            request.session['version_id'] = 0
            request.session['master'] = 1
        return version_name

    @http.route(['/website_version/check_version'], type = 'json', auth = "user", website = True)
    def check_version(self, version_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        Exp = request.registry['website_version.experiment']
        return bool(Exp.search(cr, uid, [('state','=','running'),('experiment_version_ids.version_id', '=', int(version_id))],context=context))
    
    @http.route(['/website_version/all_versions'], type = 'json', auth = "public", website = True)
    def get_all_versions(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        view = request.registry['ir.ui.view']
        v = view.browse(cr,uid,[int(view_id)],context=context)
        snap = request.registry['website_version.version']
        website_id = request.website.id
        ids = snap.search(cr, uid, [('website_id','=',website_id),'|',('view_ids.key','=',v.key),('view_ids.key','=','website.footer_default')],context=context)
        result = snap.read(cr, uid, ids,['id','name'],context=context)
        snap_id = request.context.get('version_id')
        check = False
        for x in result:
            if x['id'] == snap_id:
                x['bold'] = 1
                check = True
            else:
                x['bold'] = 0 
        #To always show in the menu the current version
        if not check and snap_id:
            result.append({'id':snap_id, 'name':snap.browse(cr, uid, [snap_id],context=context)[0].name, 'bold':1})
        return result

    @http.route(['/website_version/has_experiments'], type = 'json', auth = "public", website = True)
    def has_experiments(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        v = request.registry['ir.ui.view'].browse(cr, uid, [int(view_id)],context)[0]
        website_id = context.get('website_id')
        return bool(request.registry["website_version.experiment_version"].search(cr, uid, [('version_id.view_ids.key', '=', v.key),('experiment_id.website_id.id','=',website_id)], context=context))

    @http.route(['/website_version/publish_version'], type = 'json', auth = "public", website = True)
    def publish_version(self, version_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        obj = request.registry['website_version.version']
        version = obj.browse(cr, uid, [int(version_id)],context)[0]
        del_l = []
        for view in version.view_ids:
            master_id = request.registry['ir.ui.view'].search(cr, uid, [('key','=',view.key),('version_id', '=', False),('website_id', '=', view.website_id.id)],context=context)
            del_l += master_id
        if del_l:
            request.registry['ir.ui.view'].unlink(cr, uid, del_l, context=context)        
        for view in obj.browse(cr, uid, [int(version_id)],context).view_ids:
            view.copy({'version_id': None})
        request.session['version_id'] = 0
        request.session['master'] = 1
        return version.name

    @http.route(['/website_version/get_analytics'], type = 'json', auth = "public", website = True)
    def get_analytics(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        result = {'ExpId':False, 'VarId': 0}
        obj_v = request.registry['ir.ui.view']
        view = obj_v.browse(cr, uid, [int(view_id)],context)[0]
        #search all the running experiemnts with the key of view
        exp_ids = request.registry['website_version.experiment'].search(cr, uid, [('experiment_version_ids.version_id.view_ids.key', '=', view.key),('state','=','running'),('experiment_version_ids.version_id.website_id', '=',request.context['website_id'])],context=context)
        if exp_ids:
            x = request.registry['website_version.experiment'].browse(cr, uid, [exp_ids[0]],context)[0]
            result['ExpId'] = x.google_id
            if view.version_id:
                exp_snap_ids = request.registry['website_version.experiment_version'].search(cr, uid, [('experiment_id','=',exp_ids[0]),('version_id','=',view.version_id.id)],context=context)
                if exp_snap_ids:
                    y = request.registry['website_version.experiment_version'].browse(cr, uid, [exp_snap_ids[0]],context)[0]
                    result['VarId'] = y.google_index  
        return result

    @http.route(['/website_version/google_access'], type='json', auth="user")
    def google_authorize(self, **kw):
        #Check if client_id and client_secret are set to get the authorization from Google
        gs_obj = request.registry['google.service']
        gm_obj = request.registry['google.management']

        client_id = gs_obj.get_client_id(request.cr, request.uid, 'management', context=kw.get('local_context'))
        client_secret = gs_obj.get_client_secret(request.cr, request.uid, 'management', context=kw.get('local_context'))
        if not client_id or client_id == '' or not client_secret or client_secret == '':
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
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        website_id = context.get('website_id')
        request.registry['website'].write(cr, uid, [website_id], {'google_analytics_key':ga_key, 'google_analytics_view_id':view_id}, context=context)
        icp = request.registry['ir.config_parameter']
        icp.set_param(cr, uid, 'google_management_client_id', client_id or '', groups=['base.group_system'], context=context)
        icp.set_param(cr, uid, 'google_management_client_secret', client_secret or '', groups=['base.group_system'], context=context)


    @http.route(['/website_version/all_versions_all_goals'], type = 'json', auth = "public", website = True)
    def get_all_versions_all_goals(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        view = request.registry['ir.ui.view']
        snap = request.registry['website_version.version']
        goal = request.registry['website_version.goals']
        icp = request.registry['ir.config_parameter']
        v = view.browse(cr,uid,[int(view_id)],context=context)
        website_id = request.website.id
        snap_ids = snap.search(cr, uid, [('website_id','=',website_id),'|',('view_ids.key','=',v.key),('view_ids.key','=','website.footer_default')],context=context)
        r1 = snap.read(cr, uid, snap_ids,['id','name'],context=context)
        goal_ids = goal.search(cr, uid, [],context=context)
        r2 = goal.read(cr, uid, goal_ids,['id','name'],context=context)
        if request.website.google_analytics_key and request.website.google_analytics_view_id and icp.get_param(cr, 1, 'google_%s_token' % 'management'):
            r3 = 1
        else:
            r3 = 0
        return {'tab_snap':r1, 'tab_goal':r2, 'check_conf': r3}

    @http.route(['/website_version/create_experiment'], type = 'json', auth = "public", website = True)
    def create_experiment(self, name, version_ids, objectives):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        tab = []
        for x in version_ids:
            tab.append([0, False, {'frequency': '50', 'version_id': int(x)}])
        vals = {'name':name, 'google_id': False, 'state': 'draft', 'website_id':context.get('website_id'), 'experiment_version_ids':tab, 'objectives': int(objectives)}
        exp_obj = request.registry['website_version.experiment']
        exp_obj.create(cr, uid, vals, context=None)

    def check_view(self, version_ids):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        version_keys = set()
        for s in request.registry['website_version.version'].browse(cr, uid, version_ids,context):
            for v in s.view_ids:
                version_keys.add(v.key)
        exp_mod = request.registry['website_version.experiment']
        exp_ids = exp_mod.search(cr,uid,[('state','=','running'),('website_id','=',context.get('website_id'))],context=context)
        exps = exp_mod.browse(cr,uid,exp_ids,context=context)
        for exp in exps:
            for exp_snap in exp.experiment_version_ids:
                for view in exp_snap.version_id.view_ids:
                    if view.key in version_keys:
                        return False           
        return True

    @http.route(['/website_version/launch_experiment'], type = 'json', auth = "public", website = True)
    def launch_experiment(self, name, version_ids, objectives):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        tab = []
        check = self.check_view(version_ids)
        if check:
            for x in version_ids:
                tab.append([0, False, {'frequency': '50', 'version_id': int(x)}])
            vals = {'name':name, 'google_id': False, 'state': 'running', 'website_id':context.get('website_id'), 'experiment_version_ids':tab, 'objectives': int(objectives)}
            exp_obj = request.registry['website_version.experiment']
            exp_obj.create(cr, uid, vals, context=None)
        return check

    @http.route('/website_version/customize_template_get', type='json', auth='user', website=True)
    def customize_template_get(self, xml_id, full=False, bundles=False):
        """ Lists the templates customizing ``xml_id``. By default, only
        returns optional templates (which can be toggled on and off), if
        ``full=True`` returns all templates customizing ``xml_id``
        ``bundles=True`` returns also the asset bundles
        """
        imd = request.registry['ir.model.data']
        view_model, view_theme_id = imd.get_object_reference(
            request.cr, request.uid, 'website', 'theme')

        user = request.registry['res.users']\
            .browse(request.cr, request.uid, request.uid, request.context)
        user_groups = set(user.groups_id)

        views = request.registry["ir.ui.view"]\
            ._views_get(request.cr, request.uid, xml_id, bundles=bundles, context=dict(request.context or {}, active_test=False))
        done = set()
        result = []
        check = []
        for v in views:
            if not user_groups.issuperset(v.groups_id):
                continue
            if full or (v.customize_show and v.inherit_id.id != view_theme_id) and not v.key in check :
                check.append(v.key)
                if v.inherit_id not in done:
                    result.append({
                        'name': v.inherit_id.name,
                        'id': v.id,
                        'xml_id': v.xml_id,
                        'inherit_id': v.inherit_id.id,
                        'header': True,
                        'active': False
                    })
                    done.add(v.inherit_id)
                result.append({
                    'name': v.name,
                    'id': v.id,
                    'xml_id': v.xml_id,
                    'inherit_id': v.inherit_id.id,
                    'header': False,
                    'active': v.active,
                })
        return result
        




