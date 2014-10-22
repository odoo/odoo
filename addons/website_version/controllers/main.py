import openerp
from openerp import http
from openerp.http import request
import datetime

class TableExporter(http.Controller):
        
    @http.route(['/website_version/change_snapshot'], type = 'json', auth = "user", website = True)
    def change_snapshot(self, snapshot_id):
        request.session['snapshot_id'] = int(snapshot_id)
        request.session['master'] = 0
        return snapshot_id

    @http.route(['/website_version/master'], type = 'json', auth = "user", website = True)
    def master(self):
        request.session['snapshot_id'] = 0
        request.session['master'] = 1
        snap = request.registry['website_version.snapshot']
        return 0

    @http.route(['/website_version/create_snapshot'], type = 'json', auth = "user", website = True)
    def create_snapshot(self,name,copy):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        if name == "":
            name = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        snapshot_id = context.get('snapshot_id')
        iuv = request.registry['ir.ui.view']
        snap = request.registry['website_version.snapshot']
        website_id = request.website.id
        new_snapshot_id = snap.create(cr, uid,{'name':name, 'website_id':website_id}, context=context)
        if snapshot_id and copy:
            iuv.copy_snapshot(cr, uid, snapshot_id,new_snapshot_id,context=context)
        request.session['snapshot_id'] = new_snapshot_id
        request.context['snapshot_id'] = new_snapshot_id
        request.session['master'] = 0
        return new_snapshot_id

    @http.route(['/website_version/delete_snapshot'], type = 'json', auth = "user", website = True)
    def delete_snapshot(self, snapshot_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snap = request.registry['website_version.snapshot']
        snap.unlink(cr, uid, [int(snapshot_id)], context=context)
        current_id = request.context.get('snapshot_id')
        if int(snapshot_id)== current_id:
            request.session['snapshot_id'] = 0
            request.session['master'] = 1
        return snapshot_id

    @http.route(['/website_version/check_snapshot'], type = 'json', auth = "user", website = True)
    def check_snapshot(self, snapshot_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        Exp = request.registry['website_version.experiment']
        return bool(Exp.search(cr, uid, [('state','=','running'),('experiment_snapshot_ids.snapshot_id', '=', int(snapshot_id))],context=context))
    
    @http.route(['/website_version/all_snapshots'], type = 'json', auth = "public", website = True)
    def get_all_snapshots(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        view = request.registry['ir.ui.view']
        v = view.browse(cr,uid,[int(view_id)],context=context)
        snap = request.registry['website_version.snapshot']
        website_id = request.website.id
        ids = snap.search(cr, uid, [('website_id','=',website_id),'|',('view_ids.key','=',v.key),('view_ids.key','=','website.footer_default')],context=context)
        result = snap.read(cr, uid, ids,['id','name'],context=context)
        snap_id = request.context.get('snapshot_id')
        for x in result:
            if x['id'] == snap_id:
                x['bold'] = 1
            else:
                x['bold'] = 0 
        return result

    @http.route(['/website_version/has_experiments'], type = 'json', auth = "public", website = True)
    def has_experiments(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        v = request.registry['ir.ui.view'].browse(cr, uid, [int(view_id)],context)[0]
        website_id = context.get('website_id')
        return bool(request.registry["website_version.experiment_snapshot"].search(cr, uid, [('snapshot_id.view_ids.key', '=', v.key),('experiment_id.website_id.id','=',website_id),'|',('experiment_id.state','=','draft'),('experiment_id.state','=','running')], context=context))

    @http.route(['/website_version/publish_version'], type = 'json', auth = "public", website = True)
    def publish_version(self, snapshot_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        obj = request.registry['website_version.snapshot']
        snapshot = obj.browse(cr, uid, [int(snapshot_id)],context)[0]
        del_l = []
        for view in snapshot.view_ids:
            master_id = request.registry['ir.ui.view'].search(cr, uid, [('key','=',view.key),('snapshot_id', '=', False),('website_id', '=', view.website_id.id)],context=context)
            del_l += master_id
        if del_l:
            request.registry['ir.ui.view'].unlink(cr, uid, del_l, context=context)        
        for view in obj.browse(cr, uid, [int(snapshot_id)],context).view_ids:
            view.copy({'snapshot_id': None})
        request.session['snapshot_id'] = 0
        request.session['master'] = 1
        return snapshot.name

    @http.route(['/website_version/get_analytics'], type = 'json', auth = "public", website = True)
    def get_analytics(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        result = {'ExpId':False, 'VarId': 0}
        obj_v = request.registry['ir.ui.view']
        view = obj_v.browse(cr, uid, [int(view_id)],context)[0]
        #search all the running experiemnts with the key of view
        exp_ids = request.registry['website_version.experiment'].search(cr, uid, [('experiment_snapshot_ids.snapshot_id.view_ids.key', '=', view.key),('state','=','running'),('experiment_snapshot_ids.snapshot_id.website_id', '=',request.context['website_id'])],context=context)
        if exp_ids:
            x = request.registry['website_version.experiment'].browse(cr, uid, [exp_ids[0]],context)[0]
            result['ExpId'] = x.google_id
            if view.snapshot_id:
                exp_snap_ids = request.registry['website_version.experiment_snapshot'].search(cr, uid, [('experiment_id','=',exp_ids[0]),('snapshot_id','=',view.snapshot_id.id)],context=context)
                if exp_snap_ids:
                    y = request.registry['website_version.experiment_snapshot'].browse(cr, uid, [exp_snap_ids[0]],context)[0]
                    result['VarId'] = y.google_index  
        return result

    @http.route(['/website_version/google_access'], type='json', auth="user")
    def google_authorize(self, **kw):
        #Check if client_id and client_secret are set to get the authorization from Google
        gs_obj = request.registry['google.service']
        gm_obj = request.registry['google.management']

        client_id = gs_obj.get_client_id(request.cr, request.uid, 'management', context=kw.get('local_context'))
        client_secret = gs_obj.get_client_secret(request.cr, request.uid, 'management', context=None)
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


    @http.route(['/website_version/all_snapshots_all_goals'], type = 'json', auth = "public", website = True)
    def get_all_snapshots_all_goals(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        view = request.registry['ir.ui.view']
        snap = request.registry['website_version.snapshot']
        goal = request.registry['website_version.goals']
        website = request.registry['website']
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
    def create_experiment(self, name, snapshot_ids, objectives):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        tab = []
        for x in snapshot_ids:
            tab.append([0, False, {'frequency': '50', 'snapshot_id': int(x)}])
        vals = {'name':name, 'google_id': False, 'state': 'draft', 'website_id':context.get('website_id'), 'experiment_snapshot_ids':tab, 'objectives': int(objectives)}
        exp_obj = request.registry['website_version.experiment']
        exp_obj.create(cr, uid, vals, context=None)

    def check_view(self, snapshot_ids):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snapshot_keys = set()
        for s in request.registry['website_version.snapshot'].browse(cr, uid, snapshot_ids,context):
            for v in s.view_ids:
                snapshot_keys.add(v.key)
        exp_mod = request.registry['website_version.experiment']
        exp_ids = exp_mod.search(cr,uid,[('state','=','running')],context=context)
        exps = exp_mod.browse(cr,uid,exp_ids,context=context)
        for exp in exps:
            for exp_snap in exp.experiment_snapshot_ids:
                for view in exp_snap.snapshot_id.view_ids:
                    if view.key in snapshot_keys:
                        return False           
        return True

    @http.route(['/website_version/launch_experiment'], type = 'json', auth = "public", website = True)
    def launch_experiment(self, name, snapshot_ids, objectives):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        tab = []
        check = self.check_view(snapshot_ids)
        if check:
            for x in snapshot_ids:
                tab.append([0, False, {'frequency': '50', 'snapshot_id': int(x)}])
            vals = {'name':name, 'google_id': False, 'state': 'running', 'website_id':context.get('website_id'), 'experiment_snapshot_ids':tab, 'objectives': int(objectives)}
            exp_obj = request.registry['website_version.experiment']
            exp_obj.create(cr, uid, vals, context=None)
            return True
        else:
            return False




