# -*- coding: iso-8859-1 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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
import tools
import base64
import StringIO
import csv
import pooler

view_form_init="""<?xml version="1.0"?>
<form string="Export language">
	<image name="gtk-info" size="64" colspan="2"/>
	<group colspan="2" col="4">
		<separator string="Export translation file" colspan="4"/>
		<label align="0.0" string="Choose a language to export:" colspan="4"/>
		<field name="lang" colspan="4"/>
	</group>
</form>"""

view_form_finish="""<?xml version="1.0"?>
<form string="Export language">
	<image name="gtk-info" size="64" colspan="2"/>
	<group colspan="2" col="4">
		<separator string="Export done" colspan="4"/>
		<field name="data" readonly="1" colspan="3"/>
		<label align="0.0" string="Save this document to a .CSV file and open it with\n your favourite spreadsheet software. The file\n encoding is UTF-8. You have to translate the latest\n column before reimporting it." colspan="4"/>
	</group>
</form>"""

class wizard_export_lang(wizard.interface):
	def _get_language(self, cr, uid, context):
		lang_obj=pooler.get_pool(cr.dbname).get('res.lang')
		ids=lang_obj.search(cr, uid, [('active', '=', True),])
		langs=lang_obj.browse(cr, uid, ids)
		return [(lang.code, lang.translatable and lang.name or 'New language') for lang in langs]

	def _get_file(self, cr, uid, data, context):
		file=tools.trans_generate(data['form']['lang'], 'all', dbname=cr.dbname)
		buf=StringIO.StringIO()
		writer=csv.writer(buf)
		for row in file:
			writer.writerow(row)
		del file
		out=base64.encodestring(buf.getvalue())
		buf.close()
		return {'data': out}

	fields_form={
		'lang': {'string':'Language', 'type':'selection', 'selection':_get_language,},
	}
	fields_form_finish={
		'data': {'string':'File', 'type':'binary', 'readonly': True,},
	}
	states={
		'init':{
			'actions':[],
			'result':{'type':'form', 'arch':view_form_init, 'fields': fields_form, 'state':[('end', 'Cancel', 'gtk-cancel'),('finish', 'Ok', 'gtk-ok')]}
		},
		'finish':{
			'actions':[_get_file],
			'result':{'type':'form', 'arch':view_form_finish, 'fields': fields_form_finish, 'state':[('end', 'Close', 'gtk-cancel')]}
		},
	}
wizard_export_lang('module.lang.export')
