##############################################################################
#
# Copyright (c) 2005 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
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

import tarfile
import re
import urllib
import os
import tools
from osv import fields, osv, orm
import zipfile

class module_repository(osv.osv):
	_name = "ir.module.repository"
	_description = "Module Repository"
	_columns = {
		'name': fields.char('Name', size=128),
		'url': fields.char('Url', size=256, required=True),
	}
module_repository()

class module_category(osv.osv):
	_name = "ir.module.category"
	_description = "Module Category"
	
	def _module_nbr(self,cr,uid, ids, prop, unknow_none,context):
		cr.execute('select category_id,count(*) from ir_module_module where category_id in ('+','.join(map(str,ids))+') or category_id in (select id from ir_module_category where parent_id in ('+','.join(map(str,ids))+')) group by category_id')
		result = dict(cr.fetchall())
		for id in ids:
			cr.execute('select id from ir_module_category where parent_id=%d', (id,))
			childs = [c for c, in cr.fetchall()]
			result[id] = reduce(lambda x,y:x+y, [result.get(c, 0) for c in childs], result.get(id, 0))
		return result
		
	_columns = {
		'name': fields.char("Name", size=128, required=True),
		'parent_id': fields.many2one('ir.module.category', 'Parent Category', select=True),
		'child_ids': fields.one2many('ir.module.category', 'parent_id', 'Parent Category'),
		'module_nr': fields.function(_module_nbr, method=True, string='# of Modules', type='integer')
	}
	_order = 'name'
module_category()

class module(osv.osv):
	_name = "ir.module.module"
	_description = "Module"

	def get_module_info(self, name):
		try:
			f = tools.file_open(os.path.join(tools.config['addons_path'], name, '__terp__.py'))
			data = f.read()
			info = eval(data)
			f.close()
		except:
			return {}
		return info

	def _get_installed_version(self, cr, uid, ids, field_name=None, arg=None, context={}):
		res = {}
		for m in self.browse(cr, uid, ids):
			res[m.id] = self.get_module_info(m.name).get('version', False)
		return res

	_columns = {
		'name': fields.char("Name", size=128, readonly=True, required=True),
		'category_id': fields.many2one('ir.module.category', 'Category', readonly=True),
		'shortdesc': fields.char('Short description', size=256, readonly=True),
		'description': fields.text("Description", readonly=True),
		'author': fields.char("Author", size=128, readonly=True),
		'website': fields.char("Website", size=256, readonly=True),
		'installed_version': fields.function(_get_installed_version, method=True, string='Installed version', type='char'),
		'latest_version': fields.char('Latest version', size=64, readonly=True),
		'url': fields.char('URL', size=128, readonly=True),
		'dependencies_id': fields.one2many('ir.module.module.dependency', 'module_id', 'Dependencies'),
		'state': fields.selection([
			('uninstallable','Uninstallable'),
			('uninstalled','Not Installed'),
			('installed','Installed'),
			('to upgrade','To be upgraded'),
			('to remove','To be removed'),
			('to install','To be installed')
		], string='State', readonly=True),
		'demo': fields.boolean('Demo data'),
	}
	
	_defaults = {
		'state': lambda *a: 'uninstalled',
		'demo': lambda *a: False,
	}
	_order = 'name'

	def state_change(self, cr, uid, ids, newstate, context={}, level=50):
		if level<1:
			raise 'Recursion error in modules dependencies !'
		demo = True
		for module in self.browse(cr, uid, ids):
			mdemo = True
			for dep in module.dependencies_id:
				ids2 = self.search(cr, uid, [('name','=',dep.name)])
				mdemo = self.state_change(cr, uid, ids2, newstate, context, level-1) and mdemo
			if not module.dependencies_id:
				mdemo = module.demo
			if module.state=='uninstalled':
				self.write(cr, uid, [module.id], {'state': newstate, 'demo':mdemo})
			demo = demo and mdemo
		return demo

	def button_install(self, cr, uid, ids, context={}):
		return self.state_change(cr, uid, ids, 'to install', context)

	def button_install_cancel(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state': 'uninstalled', 'demo':False})
		return True

	def button_uninstall(self, cr, uid, ids, context={}):
		for module in self.browse(cr, uid, ids):
			cr.execute('''select m.state,m.name
				from
					ir_module_module_dependency d 
				join 
					ir_module_module m on (d.module_id=m.id)
				where
					d.name=%s and
					m.state not in ('uninstalled','uninstallable','to remove')''', (module.name,))
			res = cr.fetchall()
			if res:
				raise orm.except_orm('Error', 'The module you are trying to remove depends on installed modules :\n' + '\n'.join(map(lambda x: '\t%s: %s' % (x[0], x[1]), res)))
		self.write(cr, uid, ids, {'state': 'to remove'})
		return True

	def button_remove_cancel(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state': 'installed'})
		return True
	def button_upgrade(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state': 'to upgrade'})
		return True
	def button_upgrade_cancel(self, cr, uid, ids, context={}):
		self.write(cr, uid, ids, {'state': 'installed'})
		return True
	def button_update_translations(self, cr, uid, ids, context={}):
		cr.execute('select code from res_lang where translatable=TRUE')
		langs = [l[0] for l in cr.fetchall()]
		modules = self.read(cr, uid, ids, ['name'])
		for module in modules: 
			files = self.get_module_info(module['name']).get('translations', {})
			for lang in langs:
				if files.has_key(lang):
					filepath = files[lang]
					# if filepath does not contain :// we prepend the path of the module
					if filepath.find('://') == -1:
						filepath = os.path.join(tools.config['addons_path'], module['name'], filepath)
					tools.trans_load(filepath, lang)
		return True

	# update the list of available packages
	def update_list(self, cr, uid, context={}):
		robj = self.pool.get('ir.module.repository')
		adp = tools.config['addons_path']

		# iterate through installed modules and mark them as being so
		for name in os.listdir(adp):
			mod_name = name
			if name[-4:]=='.zip':
				mod_name=name[:-4]
			ids = self.search(cr, uid, [('name','=',mod_name)])
			if ids:
				terp = self.get_module_info(mod_name)
				if terp.get('installable', True) and self.read(cr, uid, ids, ['state'])[0]['state'] == 'uninstallable':
					self.write(cr, uid, [ids], {'state': 'uninstalled'})
				continue
			terp_file = os.path.join(adp, name, '__terp__.py')
			mod_path = os.path.join(adp, name)
			if os.path.isdir(mod_path) or zipfile.is_zipfile(mod_path):
				terp = self.get_module_info(mod_name)
				if not terp or not terp.get('installable', True):
					continue
				try:
					import imp
					# XXX must restrict to only addons paths
					imp.load_module(name, *imp.find_module(name))
				except ImportError:
					import zipimport
					mod_path = os.path.join(adp, name)
					zimp = zipimport.zipimporter(mod_path)
					zimp.load_module(mod_name)
				version = terp.get('version', False)
				id = self.create(cr, uid, {
					'name': mod_name,
					'state': 'uninstalled',
					'description': terp.get('description', ''),
					'shortdesc': terp.get('name', ''),
					'author': terp.get('author', 'Unknown')
				})
				for d in terp.get('depends', []):
					cr.execute('INSERT INTO ir_module_module_dependency (module_id, name) values (%s, %s)', (id, d))
		
		# make the list of all installable modules
		for repository in robj.browse(cr, uid, robj.search(cr, uid, [])):
			index_page = urllib.urlopen(repository.url).read()
			modules = re.findall('.*<a href="([a-zA-Z0-9.\-]+)_([a-zA-Z0-9.\-]+)\.tar\.gz">.*', index_page)
			for name, version in modules:
				# TODO: change this using urllib
				url = os.path.join(repository.url, name + '_' + version + ".tar.gz")
				ids = self.search(cr, uid, [('name','=',name)])
				if not ids:
					self.create(cr, uid, {
						'name': name,
						'latest_version': version,
						'url': url,
						'state': 'uninstalled',
					})
				else:
					for r in self.read(cr, uid, ids, ['latest_version']):
						if r['latest_version'] < version:
							self.write(cr, uid, [r['id']], {'latest_version': version, 'url':url})
		return True

	#
	# TODO: update dependencies
	#
	def info_get(self, cr, uid, ids, context={}):
		categ_obj = self.pool.get('ir.module.category')
		
		for module in self.browse(cr, uid, ids, context):
			url = module.url
			adp = tools.config['addons_path']
			info = False
			if url:
				tar = tarfile.open(mode="r|gz", fileobj=urllib.urlopen(url))
				for tarinfo in tar:
					if tarinfo.name.endswith('__terp__.py'):
						info = eval(tar.extractfile(tarinfo).read())
			elif os.path.isdir(os.path.join(adp, module.name)):
				info = self.get_module_info(module.name)
			if info:
				categ = info.get('category', 'Unclassified')
				parent = False
				for c in categ.split('/'):
					ids = categ_obj.search(cr, uid, [('name','=',c), ('parent_id','=',parent)])
					if not ids:
						parent = categ_obj.create(cr, uid, {'name':c, 'parent_id':parent})
					else:
						parent = ids[0]
				self.write(cr, uid, [module.id], {
					'author': info.get('author',False),
					'website': info.get('website',False),
					'shortdesc': info.get('name',False),
					'description': info.get('description',False),
					'category_id': parent
				})
		return True
module()

class module_dependency(osv.osv):
	_name = "ir.module.module.dependency"
	_description = "Module dependency"
	_columns = {
		'name': fields.char('Name',  size=128),
		'module_id': fields.many2one('ir.module.module', 'Module', select=True),
		#'module_dest_id': fields.many2one('ir.module.module', 'Module'),
		'version_pattern': fields.char('Required Version', size=128),
	}
	# returns the ids of module version records which match all dependencies
	# [version_id, ...]
	def resolve(self, cr, uid, ids):
		vobj = self.pool.get('ir.module.module.version')
		objs = self.browse(cr, uid, ids)
		res = {}
		for o in objs:
			pattern = o.version_pattern and eval(o.version_pattern) or []
			res[o.id] = vobj.search(cr, uid, [('module','=',o.module.id)]+pattern)
		#TODO: add smart dependencies resolver here
		# it should compute the best version for each module
		return [r[0] for r in res.itervalues()]
module_dependency()

