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
    def create_snapshot(self,name):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        if name == "":
            name = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        snapshot_id = context.get('snapshot_id')
        iuv = request.registry['ir.ui.view']
        snap = request.registry['website_version.snapshot']
        website_id = request.website.id
        if not snapshot_id:
            new_snapshot_id = snap.create(cr, uid,{'name':name, 'website_id':website_id}, context=context)
        else:
            new_snapshot_id = snap.create(cr, uid,{'name':name, 'website_id':website_id}, context=context)
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
    
    @http.route(['/website_version/all_snapshots'], type = 'json', auth = "public", website = True)
    def get_all_snapshots(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        view = request.registry['ir.ui.view']
        v = view.browse(cr,uid,[int(view_id)],context=context)
        snap = request.registry['website_version.snapshot']
        website_id = request.website.id
        ids = snap.search(cr, uid, [('website_id','=',website_id),('view_ids.key','=',v.key)],context=context)
        result = snap.read(cr, uid, ids,['id','name'],context=context)
        return result

    @http.route(['/website_version/is_master'], type = 'json', auth = "public", website = True)
    def is_master(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        obj = request.registry['ir.ui.view']
        view = obj.browse(cr,uid,[int(view_id)],context=context)
        if view.snapshot_id:
            result = False
        else:
            result = True
        return result

    @http.route(['/website_version/publish'], type = 'json', auth = "public", website = True)
    def publish(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        obj = request.registry['ir.ui.view']
        view = obj.browse(cr, uid, [int(view_id)],context)[0]
        key = view.key
        if view.website_id and view.snapshot_id:
            master_id = obj.search(cr, uid, [('key','=',key),('snapshot_id', '=', False),('website_id', '=', view.website_id.id)],context=context)
            if master_id:
                obj.unlink(cr, uid, master_id, context=context)
            obj.copy(cr, uid, view_id, {'key':key, 'website_id': view.website_id.id, 'snapshot_id': None}, context=context)
        request.session['snapshot_id'] = 0
        request.session['master'] = 1
        return view.snapshot_id.id

    @http.route(['/website_version/publish_version'], type = 'json', auth = "public", website = True)
    def publish_version(self, snapshot_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        obj = request.registry['website_version.snapshot']
        snapshot = obj.browse(cr, uid, [int(snapshot_id)],context)[0]
        for view in snapshot.view_ids:
            self.publish(view.id)
        return snapshot.id

    @http.route(['/website_version/get_analytics'], type = 'json', auth = "public", website = True)
    def get_analytics(self, view_id):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        result = {'snapshot_id': 0, 'experiment_id': 0}
        obj_v = request.registry['ir.ui.view']
        view = obj_v.browse(cr, uid, [int(view_id)],context)[0]
        if view.snapshot_id:
            result['snapshot_id'] = view.snapshot_id.id
            obj_es = request.registry['website_version.experiment_snapshot']
            exp_snap_id = obj_es.search(cr, uid, [('snapshot_id', '=', view.snapshot_id.id)],context=context)        
            if exp_snap_id:
                exp_snap = obj_es.browse(cr, uid, [exp_snap_id[0]],context)[0]
                result['experiment_id'] = exp_snap.experiment_id.id
        return result

    @http.route(['/set_context'], type = 'json', auth = "public", website = True)
    def set_context(self):
        cr, uid, context = request.cr, openerp.SUPERUSER_ID, request.context
        snapshot_id = context.get('snapshot_id')
        return snapshot_id
