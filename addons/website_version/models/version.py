# -*- coding: utf-8 -*-
from openerp.osv import osv, fields
from openerp.exceptions import Warning
from openerp.http import request
from openerp.tools.translate import _

class version(osv.Model):
    _name = "website_version.version"
    
    _columns = {
        'name' : fields.char(string="Title", required=True),
        'view_ids': fields.one2many('ir.ui.view', 'version_id',string="view_ids",copy=True),
        'website_id': fields.many2one('website',ondelete='cascade', string="Website"),
        'create_date': fields.datetime('Create Date'),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name, website_id)', _('You cannot have multiple versions with the same name in the same domain!')),
    ]

    def unlink(self, cr, uid, ids, context=None):
        Exp = self.pool['website_version.experiment']
        for id in ids:
            result = Exp.search(cr, uid, [('state','=','running'),('experiment_version_ids.version_id', '=', id)],context=context)
            if result:
                raise Warning(_("You cannot delete a version which is in a running experiment."))
            #To avoid problem when we delete versions in Backend
            if request:
                request.session['version_id'] = 0
                request.session['master'] = 1
        return super(version, self).unlink(cr, uid, ids, context=context)

    def action_publish(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        version_id = context.get('active_id')
        if version_id:
            version = self.browse(cr, uid, [version_id],context)[0]
            del_l = []
            for view in version.view_ids:
                #To delete and replace views which are in the website( in fact with website_id)
                master_id = self.pool['ir.ui.view'].search(cr, uid, [('key','=',view.key),('version_id', '=', False),('website_id', '=', view.website_id.id)],context=context)
                del_l += master_id
            if del_l:
                self.pool['ir.ui.view'].unlink(cr, uid, del_l, context=context)        
            for view in self.browse(cr, uid, [version_id],context).view_ids:
                view.copy({'version_id': None})