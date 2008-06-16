##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be)
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contact a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os
import re
import glob
import time
import imp

import tools
import wizard
import pooler

import zipfile

module_name_re = re.compile('.*addons.(.*?).__terp__.py$')

_info_arch = '''<?xml version="1.0"?>
<form string="Scan for new modules">
  <label string="This function will check if you installed new modules in the 'addons' path of your server installation." colspan="4" />
</form>
'''
_info_fields = {}

class wizard_install_module(wizard.interface):
	def watch_dir(self, cr, uid, data, context):
		mod_obj = pooler.get_pool(cr.dbname).get('ir.module.module')
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
			imp.load_module(module, *imp.find_module(module))
			mod_id = mod_obj.create(cr, uid, {
				'name': module, 
				'state': 'uninstalled',
				'description': terp.get('description', ''),
				'shortdesc': terp.get('name', ''),
				'author': terp.get('author', 'Unknown')})
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

	states = {
		'init': {
			'actions': [], 
			'result': {'type':'form', 'arch': _info_arch, 'fields': _info_fields, 'state':[('end','Cancel','gtk-cancel'),('addmod','Check new modules','gtk-ok')]}
		},
		'addmod': {
			'actions': [watch_dir],
			'result': {'type':'state', 'state':'end'}
		},
	}
wizard_install_module('module.module.scan')

