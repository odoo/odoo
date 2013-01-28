# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import os
import glob
import imp
import zipfile

from openerp import tools
from openerp.osv import osv

class base_module_scan(osv.osv_memory):
    """ scan module """

    _name = "base.module.scan"
    _description = "scan module"

    def watch_dir(self, cr, uid, ids, context):
        mod_obj = self.pool.get('ir.module.module')
        all_mods = mod_obj.read(cr, uid, mod_obj.search(cr, uid, []), ['name', 'state'])
        known_modules = [x['name'] for x in all_mods]
        ls_ad = glob.glob(os.path.join(tools.config['addons_path'], '*', '__terp__.py'))
        modules = [module_name_re.match(name).group(1) for name in ls_ad]
        for fname in os.listdir(tools.config['addons_path']):
            if zipfile.is_zipfile(fname):
                modules.append( fname.split('.')[0])
        for module in modules:
            if module in known_modules:
                continue
            terp = mod_obj.get_module_info(module)
            if not terp.get('installable', True):
                continue

            # XXX check if this code is correct...
            fm = imp.find_module(module)
            try:
                imp.load_module(module, *fm)
            finally:
                if fm[0]:
                    fm[0].close()

            values = mod_obj.get_values_from_terp(terp)
            mod_id = mod_obj.create(cr, uid, dict(name=module, state='uninstalled', **values))
            dependencies = terp.get('depends', [])
            for d in dependencies:
                cr.execute('insert into ir_module_module_dependency (module_id,name) values (%s, %s)', (mod_id, d))
        for module in known_modules:
            terp = mod_obj.get_module_info(module)
            if terp.get('installable', True):
                for mod in all_mods:
                    if mod['name'] == module and mod['state'] == 'uninstallable':
                        mod_obj.write(cr, uid, [mod['id']], {'state': 'uninstalled'})
        return {}

base_module_scan()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
