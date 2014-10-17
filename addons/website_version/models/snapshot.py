# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.exceptions import Warning


class Snapshot(osv.Model):
    _name = "website_version.snapshot"
    
    _columns = {
        'name' : fields.char(string="Title", required=True),
        'view_ids': fields.one2many('ir.ui.view', 'snapshot_id',string="view_ids",copy=True),
        'website_id': fields.many2one('website',ondelete='cascade', string="Website"),
        'create_date': fields.datetime('Create Date'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'You cannot have multiple snapshots with the same name!'),
    ]

    def unlink(self, cr, uid, ids, context=None):
        Exp = self.pool['website_version.experiment']
        for id in ids:
            result = Exp.search(cr, uid, [('state','=','running'),('experiment_snapshot_ids.snapshot_id', '=', id)],context=context)
            if result:
                raise Warning("You cannot delete a version which is in a running experiment.")
        return super(Snapshot, self).unlink(cr, uid, ids, context=context)

    def action_publish(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        snapshot_id = context.get('active_id')
        print snapshot_id
        if snapshot_id:
            snapshot = self.browse(cr, uid, [snapshot_id],context)[0]
            del_l = []
            for view in snapshot.view_ids:
                master_id = self.pool['ir.ui.view'].search(cr, uid, [('key','=',view.key),('snapshot_id', '=', False),('website_id', '=', view.website_id.id)],context=context)
                del_l += master_id
            if del_l:
                self.pool['ir.ui.view'].unlink(cr, uid, del_l, context=context)        
            for view in self.browse(cr, uid, [snapshot_id],context).view_ids:
                view.copy({'snapshot_id': None})