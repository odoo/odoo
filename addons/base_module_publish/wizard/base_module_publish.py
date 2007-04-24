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

import time
import wizard
import osv
import pooler

intro_form = '''<?xml version="1.0"?>
<form string="Module publication">
	<separator string="Publication information" colspan="4"/>
	<field name="text" colspan="4" nolabel="1"/>
</form>'''

intro_fields = {
	'text': {'string':'Introduction', 'type':'text', 'readonly':True, 'default': lambda *args: """
This system will automatically publish the selected module to the
Tiny ERP official website. You can use it to quickly publish a new
module or update an existing one (new version).

Make sure you read the publication manual and modules guidelines
before continuing:
  http://tinyerp.com

Thank you for contributing !
"""},
}

check_form = '''<?xml version="1.0"?>
<form string="Module publication">
	<separator string="Verify your module information" colspan="4"/>
	<field name="name"/>
	<field name="version"/>
	<field name="author"/>
	<field name="website" widget="url"/>
	<field name="shortdesc" colspan="3"/>
	<field name="description" colspan="3"/>
</form>'''

check_fields = {
	'name': {'string':'Name', 'type':'char', 'size':64, 'readonly':True},
	'shortdesc': {'string':'Small description', 'type':'char', 'size':200, 'readonly':True},
	'author': {'string':'Author', 'type':'char', 'size':128, 'readonly':True},
	'website': {'string':'Website', 'type':'char', 'size':200, 'readonly':True},
	'url': {'string':'Download URL', 'type':'char', 'size':200, 'readonly':True},
	'description': {'string':'Description', 'type':'text', 'readonly':True},
	'version': {'string':'Version', 'type':'char', 'readonly':True},
}


upload_info_form = '''<?xml version="1.0"?>
<form string="Module publication">
	<separator string="User information" colspan="4"/>
	<label align="0.0" string="Please provide here your login on the Tiny ERP website." colspan="4"/>
	<label align="0.0" string="If you don't have an access, you can create one online." colspan="4"/>
	<field name="login"/>
	<newline/>
	<field name="password"/>
	<separator string="Module information" colspan="4"/>
	<field name="category"/>
	<field name="licence"/>
	<field name="url_download"/>
	<label align="0.0" colspan="2" string="(Keep empty for an auto upload of the module)"/>
</form>'''

def _get_selection(*Args):
	import urllib
	a = urllib.urlopen('http://www.tinyerp.com/mtree_interface.php')
	res = filter(None, a.read().split('\n'))
	return map(lambda x:x.split('='), res)

upload_info_fields = {
	'login': {'string':'Login', 'type':'char', 'size':32, 'required':True},
	'password': {'string':'Password', 'type':'char', 'size':32, 'required':True},
	'category': {'string':'Category', 'type':'selection', 'size':64, 'required':True,
		'selection': _get_selection
	},
	'licence': {
		'string':'Licence', 'type':'selection', 'size':64, 'required':True,
		'selection': [('GPL', 'GPL'), ('Other proprietary','Other proprietary')],
		'default': lambda *args: 'GPL'
	},
	'url_download': {'string':'Download URL', 'type':'char', 'size':128},
}

end_form = '''<?xml version="1.0"?>
<form string="Module publication">
	<separator string="Publication result" colspan="4"/>
	<field name="text_end" colspan="4" nolabel="1"/>
</form>'''

end_fields = {
	'text_end': {'string':'Summary', 'type':'text', 'readonly':True, 'default': lambda *args: """
Thank you for contributing !

Your module has been successfully uploaded to the official website.
You must wait a few hours/days so that the Tiny ERP core team review
your module for approval on the website.
"""},
}


def module_check(self, cr, uid, data, context):
	pool = pooler.get_pool(cr.dbname)
	module = pool.get('ir.module.module').browse(cr, uid, data['id'], context)
	return {
		'name': module.name, 
		'shortdesc': module.shortdesc,
		'author': module.author,
		'website': module.website,
		'url': module.url,
		'description': module.description,
		'version': module.latest_version
	}

class base_module_publish(wizard.interface):
	states = {
		'init': {
			'actions': [], 
			'result': {
				'type':'form', 
				'arch':intro_form,
				'fields':intro_fields, 
				'state':[
					('end','Cancel'),
					('step1','Continue')
				]
			}
		},
		'step1': {
			'actions': [module_check],
			'result': {
				'type':'form', 
				'arch':check_form,
				'fields':check_fields, 
				'state':[
					('end','Cancel'),
					('init', 'Previous'),
					('step2','Continue')
				]
			}
		},
		'step2': {
			'actions': [],
			'result': {
				'type':'form', 
				'arch':upload_info_form,
				'fields':upload_info_fields, 
				'state':[
					('end','Cancel'),
					('step1', 'Previous'),
					('publish','Publish Now !')
				]
			}
		},
		'publish': {
			'actions': [], # Action to develop: upload method
			'result': {
				'type':'form', 
				'arch':end_form,
				'fields':end_fields, 
				'state':[
					('end','Close')
				]
			}
		}
	}
base_module_publish('base_module_publish.module_publish')

