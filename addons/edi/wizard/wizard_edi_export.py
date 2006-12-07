##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: wizard_edi_export.py 2071 2006-01-09 16:37:25Z nicoe $
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

_export_form = '''<?xml version="1.0"?>
<form string="EDI file export">
	<separator string="Export to the following directory" colspan="4" />
	<field name="ediexportdir" colspan="4" />
</form>'''

_export_fields = { 	'ediexportdir' : {	'string' : 'EDI Import Dir', 
										'type' : 'char', 
										'size' : 100, 
										'default' : lambda *a: '/edi/reception', 
										'required' : True 
									},
				}

_export_done_form = '''<?xml version="1.0"?>
<form string="EDI file exported">
	<separator string="EDI file exported" colspan="4" />
</form>'''

_export_done_fields = {}

def _do_export(self, cr, uid, data, context):
	return {}

class wiz_edi_export(wizard.interface):
	states = {
		'init' : {
			'actions' : [],
			'result' : { 'type' : 'form', 'arch' : _import_form, 'fields' : _import_fields, 'state' : (('end', 'Cancel'),('export', 'Export Sales') )},
			},
		'export' : {
			'actions' : [_do_export],
			'result' : { 'type' : 'form', 'arch' : _export_done_form, 'fields' : _export_done_fields, 'state' : (('end', 'Ok'),)},
			},
	}

wiz_edi_export('edi.export')
# vim:noexpandtab:
