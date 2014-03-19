import logging
from os.path import join as opj

import openerp
from openerp.osv import osv, fields
from openerp.tools import convert_file

_logger = logging.getLogger(__name__)

class view(osv.osv):
    _inherit = "ir.module.module"
    _columns = {
        'is_theme': fields.boolean('Theme'),
    }
    _defaults = {
        'is_theme': False,
    }

    def import_module(self, cr, uid, module, path, context=None):
        known_mods = self.browse(cr, uid, self.search(cr, uid, []))
        known_mods_names = dict([(m.name, m) for m in known_mods])

        mod = known_mods_names.get(module)
        terp = openerp.modules.load_information_from_description_file(module, mod_path=path)
        values = self.get_values_from_terp(terp)

        unmet_dependencies = set(terp['depends']).difference(known_mods_names.keys())
        if unmet_dependencies:
            raise Exception("Unmet module dependencies: %s" % ', '.join(unmet_dependencies))

        if mod:
            self.write(cr, uid, mod.id, values)
            mode = 'update'
        else:
            assert terp.get('installable', True), "Module not installable"
            self.create(cr, uid, dict(name=module, state='uninstalled', **values))
            mode = 'init'

        for kind in ['data', 'init_xml', 'update_xml']:
            for filename in terp[kind]:
                _logger.info("module %s: loading %s", module, filename)
                noupdate = False
                if filename.endswith('.csv') and kind in ('init', 'init_xml'):
                    noupdate = True
                pathname = opj(path, filename)
                idref = {}
                convert_file(cr, module, filename, idref, mode=mode, noupdate=noupdate, kind=kind, pathname=pathname)

        return True
