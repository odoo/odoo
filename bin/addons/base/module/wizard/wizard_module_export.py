##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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


import wizard
import osv
import pooler
import os
import tools

from zipfile import PyZipFile, ZIP_DEFLATED
import StringIO
import base64

finish_form ='''<?xml version="1.0"?>
<form string="Finish">
	<separator string="Module successfully exported !" colspan="4"/>
	<field name="module_file"/>
	<newline/>
	<field name="module_filename"/>
</form>
'''

finish_fields = {
	'module_file': {'string': 'Module .ZIP file', 'type':'binary', 'readonly':True},
	'module_filename': {'string': 'Filename', 'type':'char', 'size': 64, 'readonly':True},
}

class move_module_wizard(wizard.interface):
	def zippy(self, archive, fromurl, path):
		url = os.path.join(fromurl, path)
		if os.path.isdir(url):
			if path.split('/')[-1]=='.svn':
				return False
			for fname in os.listdir(url):
				self.zippy(archive, fromurl, path and os.path.join(path, fname) or fname)
		else:
			if (path.split('.')[-1] not in ['py','pyo','pyc']) or (os.path.basename(path)=='__terp__.py'):
				print 'Adding', os.path.join(fromurl, path), 'as', path
				archive.write(os.path.join(fromurl, path), path)
		return True

	def createzip(self, cr, uid, data, context):
		module_obj=pooler.get_pool(cr.dbname).get('ir.module.module')
		module_name = module_obj.browse(cr, uid, data['id']).name

		ad = tools.config['addons_path']
		if os.path.isdir(os.path.join(ad,module_name)):
			archname = StringIO.StringIO('wb')
			archive = PyZipFile(archname, "w", ZIP_DEFLATED)
			archive.writepy(os.path.join(ad,module_name))
			self.zippy(archive, ad, module_name)
			archive.close()
			val =base64.encodestring(archname.getvalue())
			archname.close()
		elif os.path.isfile(os.path.join(ad,module_name+'.zip')):
			val = file(os.path.join(ad,module_name+'.zip'),'rb').read()
			val =base64.encodestring(val)
		else:
			raise wizard.except_wizard('Error !', 'Could not find the module to export !')
		return {'module_file':val, 'module_filename': module_name+'.zip'}

	states = {
		'init': {
			'actions': [createzip],
			'result': {
				'type':'form',
				'arch':finish_form,
				'fields':finish_fields,
				'state':[('end','Close')]
			}
		}
	}
move_module_wizard('base.module.export')
