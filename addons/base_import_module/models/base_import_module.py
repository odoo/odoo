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
        'import_message': fields.char('Import message'),
        'force': fields.boolean('Force init', help="Force init mode even if installed. (will update `noupdate='1'` records)"),
    }

    _defaults = {
        'state': 'init',
        'force': False,
    }

    def import_module(self, cr, uid, ids, context=None):
        module_obj = self.pool.get('ir.module.module')
        data = self.browse(cr, uid, ids[0] , context=context)
        zip_data = base64.decodestring(data.module_file)
        fp = BytesIO()
        fp.write(zip_data)
        res = module_obj.import_zipfile(cr, uid, fp, force=data.force, context=context)
        self.write(cr, uid, ids, {'state': 'done', 'import_message': res[0]}, context=context)
        context = dict(context, module_name=res[1])
        # Return wizard otherwise it will close wizard and will not show result message to user. 
        return {
            'name': 'Import Module',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_id': ids[0],
            'res_model': 'base.import.module',
            'type': 'ir.actions.act_window',
            'context': context,
        }

    def action_module_open(self, cr, uid, ids, context):
        return {
            'domain': [('name', 'in', context.get('module_name',[]))],
            'name': 'Modules',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'ir.module.module',
            'view_id': False,
            'type': 'ir.actions.act_window',
        }
