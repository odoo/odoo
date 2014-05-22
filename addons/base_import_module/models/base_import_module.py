import base64
from StringIO import StringIO
from io import BytesIO
from openerp.osv import osv, fields

class base_import_module(osv.TransientModel):
    """ Import Module """
    _name = "base.import.module"
    _description = "Import Module"

    _columns = {
        'module_file': fields.binary('Module .ZIP file', required=True),
        'state':fields.selection([('init','init'),('done','done')], 'Status', readonly=True),
        'module_name': fields.char('Module Name', size=128),
    }

    _defaults = {  
        'state': 'init',
    }

    def import_module(self, cr, uid, ids, context=None):
        module_obj = self.pool.get('ir.module.module')
        data = self.browse(cr, uid, ids[0] , context=context)
        zip_data = base64.decodestring(data.module_file)
        fp = BytesIO()
        fp.write(zip_data)
        module_obj.import_zipfile(cr, uid, fp, context=context)
        fp.close()
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return False

    def action_module_open(self, cr, uid, ids, context):
        data = self.browse(cr, uid, ids[0] , context=context)
        return {
            'domain': str([('name', '=', data.module_name)]),
            'name': 'Modules',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'ir.module.module',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
