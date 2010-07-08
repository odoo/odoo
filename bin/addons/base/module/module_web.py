from osv import fields, osv, orm

class module_web(osv.osv):
    _name = "ir.module.web"
    _description = "Web Module"
    
    _columns = {
        'name': fields.char("Name", size=128, readonly=True, required=True),
        'module': fields.char("Module", size=128, readonly=True, required=True),
        'description': fields.text("Description", readonly=True, translate=True),
        'author': fields.char("Author", size=128, readonly=True),
        'website': fields.char("Website", size=256, readonly=True),
        'state': fields.selection([
            ('uninstallable','Uninstallable'),
            ('uninstalled','Not Installed'),
            ('installed','Installed')
            ], string='State', readonly=True)
    }
    
    _defaults = {
        'state': lambda *a: 'uninstalled',
    }
    _order = 'name'

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the module must be unique !'),
    ]
    
    def update_module_list(self, cr, uid, modules, context={}):
        
        for module in modules:
            mod_name = module['name']
            ids = self.search(cr, uid, [('name','=',mod_name)])
            if ids:
                self.write(cr, uid, ids, module)
            else:
                self.create(cr, uid, module)
                
    def button_install(self, cr, uid, ids, context={}):
        res = self.write(cr, uid, ids, {'state': 'installed'}, context)
        if res:
            return "Installed"
    
    def button_uninstall(self, cr, uid, ids, context={}):
        res = self.write(cr, uid, ids, {'state': 'uninstalled'}, context)
        if res:
            return "Uninstalled"
                
module_web()

