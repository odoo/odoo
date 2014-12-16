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
        result = Exp.search(cr, uid, ['|',('state','=','running'),('state','=','paused'),('experiment_version_ids.version_id', 'in', ids)],context=context)
        if result:
            raise Warning(_("You cannot delete a version which is in a running or paused experiment."))
        #To avoid problem when we delete versions in Backend
        if request:
            request.session['version_id'] = 0
        return super(version, self).unlink(cr, uid, ids, context=context)

    def action_publish(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        version_id = context.get('active_id')
        if version_id:
            view_ids = self.pool['ir.ui.view'].search(cr, uid, [('version_id','=',version_id)], context=context)
            if view_ids:
                self.pool['ir.ui.view'].publish(cr,uid, view_ids, context=context)

    def publish_version(self, cr, uid, version_id, save_master, copy_master_name, context = None):
        #Info: there were some cache problems with browse, this is why the code is so long
        version = self.browse(cr, uid, [int(version_id)],context)[0]
        del_l = []
        copy_l = []
        for view in version.view_ids:
            master_id = self.pool['ir.ui.view'].search(cr, uid, [('key','=',view.key),('version_id', '=', False),('website_id', '=', view.website_id.id)],context=context)
            if master_id:
                #Delete all the website views having a key which is in the version published
                del_l += master_id
                copy_l+= master_id
            else:
                #Views that have no website_id, must be copied because they can be shared with another website
                master_id = self.pool['ir.ui.view'].search(cr, uid, [('key','=',view.key),('version_id', '=', False),('website_id', '=', False)],context=context)
                copy_l+= master_id
        if copy_l:
            if save_master:
                #To check if the name of the version to copy master already exists
                check_id = self.search(cr, uid, [('name','=', copy_master_name),('website_id', '=', version.website_id.id)],context=context)
                #If it already exists, we delete the old to make the new
                if check_id:
                    self.unlink(cr, uid, check_id, context=context)
                copy_version_id = self.create(cr, uid, {'name' : copy_master_name, 'website_id' : version.website_id.id}, context=context)
                for view in request.registry['ir.ui.view'].browse(cr, uid, copy_l, context=context):
                    view.copy({'version_id': copy_version_id, 'website_id' : version.website_id.id})
            #Here, instead of deleting all the views we can just change the version_id BUT I've got some cache problems
            self.pool['ir.ui.view'].unlink(cr, uid, del_l, context=context)
        #All the views in the version published are copied without version_id   
        for view in self.browse(cr, uid, [int(version_id)],context).view_ids:
            view.copy({'version_id': None}, context=context)
        return version.name

