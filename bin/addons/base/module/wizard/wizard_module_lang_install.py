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

view_form_end = """<?xml version="1.0"?>
<form string="Language file loaded.">
	<image name="gtk-info" size="64" colspan="2"/>
	<group colspan="2" col="4">
		<separator string="Installation done" colspan="4"/>
		<label align="0.0" string="The selected language has been successfully installed.\nYou must change the preferences of the user and open a new menu to view changes." colspan="4"/>
	</group>
</form>"""

view_form = """<?xml version="1.0"?>
<form string="System Upgrade">
	<image name="gtk-info" size="64" colspan="2"/>
	<group colspan="2" col="4">
	<separator string="System Upgrade" colspan="4"/>
		<label align="0.0" string="Choose a language to install:" colspan="4"/>
		<field name="lang" colspan="4"/>
		<label align="0.0" string="Note that this operation may take a few minutes." colspan="4"/>
	</group>
</form>"""


class wizard_lang_install(wizard.interface):
	def _lang_install(self, cr, uid, data, context):
		print cr, uid, data, context

		lang = data['form']['lang']
		if lang and lang != 'en_EN':
			filename = tools.config["root_path"] + "/i18n/" + lang + ".csv"
			tools.trans_load(cr.dbname, filename, lang)
		return {}

	def _get_language(sel, cr, uid, context):
		return tools.scan_languages()

	fields_form = {
		'lang': {'string':'Language', 'type':'selection', 'selection':_get_language,
		},
	}

	states = {
		'init': {
			'actions': [], 
			'result': {'type':'form', 'arch':view_form, 'fields': fields_form, 'state':[('end','Cancel','gtk-cancel'),('start','Start installation','gtk-ok')]}
		},
		'start': {
			'actions': [_lang_install],
			'result': {'type':'form', 'arch':view_form_end, 'fields': {}, 'state':[('end','Ok','gtk-ok')]}
		},
	}
wizard_lang_install('module.lang.install')

