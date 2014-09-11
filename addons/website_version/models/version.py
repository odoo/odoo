# -*- coding: utf-8 -*-
from openerp.osv import osv,fields
from openerp.http import request


class ViewVersion(osv.Model):
    _inherit = "ir.ui.view"
    
    _columns = {
        'snapshot_id' : fields.many2one('website_version.snapshot',ondelete='cascade', string="Snapshot_id"),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        try:
            iter(ids)
        except:
            ids=[ids]
        
        snapshot_id=context.get('snapshot_id')

        if snapshot_id and not context.get('mykey'):
            ctx = dict(context, mykey=True)
            snap = self.pool['website_version.snapshot']
            snapshot=snap.browse(cr, uid, [snapshot_id], context=ctx)[0]
            website_id=snapshot.website_id.id
            snap_ids = []
            for current in self.browse(cr, uid, ids, context=context):
                #check if current is in snapshot
                if current.snapshot_id.id == snapshot_id:
                    snap_ids.append(current.id)
                else:
                    new_id = self.search(cr, uid, [('website_id', '=', website_id),('snapshot_id', '=', snapshot_id), ('key', '=', current.key)], context=context)
                    if new_id:
                        snap_ids.append(new_id[0])
                    else:
                        copy_id=self.copy(cr,uid, current.id,{'snapshot_id':snapshot_id, 'website_id':website_id},context=ctx)
                        snap_ids.append(copy_id)
            super(ViewVersion, self).write(cr, uid, snap_ids, vals, context=ctx)
        else:
            ctx = dict(context, mykey=True)
            super(ViewVersion, self).write(cr, uid, ids, vals, context=context)
    
    #To make a snapshot of a snapshot
    def copy_snapshot(self,cr, uid, snapshot_id,new_snapshot_id, context=None):
        if context is None:
            context = {}
        ctx = dict(context, mykey=True)
        snap = self.pool['website_version.snapshot']
        snapshot=snap.browse(cr, uid, [snapshot_id],ctx)[0]
        for view in snapshot.view_ids:
            copy_id=self.copy(cr,uid,view.id,{'snapshot_id':new_snapshot_id},context=ctx)

    #To publish a master view
    def action_publish(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        ctx = dict(context, mykey=True)
        snap = self.pool['website_version.snapshot']
        all_snapshot_ids = snap.search(cr, uid, [],context=context)
        all_snapshots = snap.browse(cr, uid, all_snapshot_ids, context=context)
        view_id = context.get('active_id')
        view = self.browse(cr, uid, [view_id],ctx)[0]
        key = view.key
        deleted_ids = self.search(cr, uid, [('key','=',key),('website_id','!=',False)],context=context)
        if view.website_id:
            master_id = self.search(cr, uid, [('key','=',key),('website_id','=',False),('snapshot_id','=',False)],context=context)[0]
            deleted_ids.remove(view.id)
            super(ViewVersion, self).write(cr, uid,[master_id], {'arch': view.arch}, context=ctx)
            self.unlink(cr, uid, deleted_ids, context=context)
        else:
            self.unlink(cr, uid, deleted_ids, context=context)

        
                