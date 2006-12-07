##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#					Fabien Pinckaers <fp@tiny.Be>
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
from osv import fields, osv

#---------------------------------------------------------
# Type of hardware: Printers, Screens, HD, ....
#---------------------------------------------------------
class network_hardware_type(osv.osv):
	_name = "network.hardware.type"
	_description = "Hardware type"
	_columns = {
		'name': fields.char('Type of material', size=64, required=True),
		'networkable': fields.boolean('Networkable hardware'),
	}
	_defaults = {
		'networkable': lambda *a: False,
	}
network_hardware_type()

#--------------------------------------------------------------
# A network is composed of all kind of networkable materials
#--------------------------------------------------------------
class network_network(osv.osv):
	_name = 'network.network'
	_description = 'Network'
	_columns = {
		'name': fields.char('Network name', size=64, required=True),
		'range': fields.char('Address range', size=128),
		'user_id': fields.many2one('res.users','Onsite Contact person'),
		'contact_id': fields.many2one('res.partner', 'Partner', required=True),
		'material_ids': fields.one2many('network.material', 'network_id', 'Members'),
	}
network_network()

def _calc_warranty(*args):
	now = list(time.localtime())
	now[0] += 1
	return time.strftime('%Y-%m-%d', tuple(now))

#----------------------------------------------------------
# Materials; computer, printer, switch, ...
#----------------------------------------------------------
class network_material(osv.osv):
	_name = "network.material"
	_description = "Material"
	_columns = {
		'name': fields.char('Device Name', size=64, required=True),
		'ip_addr': fields.char('IP Address', size=16),
		'network_id': fields.many2one('network.network', 'Network'),
		'supplier': fields.many2one('res.partner', 'Supplier'),
		'date': fields.date('Installation Date'),
		'warranty': fields.date('Warranty deadline'),
		'type': fields.many2one('network.hardware.type',
								'Hardware type', required=True),
		'note': fields.text('Notes'),
		'parent_id': fields.many2one('network.material',
									 'Parent Material'),
		'child_id': fields.one2many('network.material', 'parent_id', 
									'Childs Materials'),
		'software_id': fields.one2many('network.software',
									   'material_id', 
									   'Installed Software'),
		'change_id': fields.one2many('network.changes',
								     'machine_id',
									 'Changes on this machine'),
	}
	_defaults = {
		 'date': lambda *a: time.strftime('%Y-%m-%d'),
		 'warranty': _calc_warranty,
	}
network_material()

#----------------------------------------------------------
# Changes on this machine
#----------------------------------------------------------
class network_changes(osv.osv):
	_name = 'network.changes'
	_description = 'Network changes'
	_columns = {
		'name': fields.char('Short Description', size=64,
							 required=True),
		'description': fields.text('Long Description'),
		'date': fields.date('Change date'),
		'machine_id': fields.many2one('network.material',
									   'Machine'),
	}
	_defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
	}
network_changes()

#----------------------------------------------------------
# Type of Software; LDAP, Tiny ERP, Postfix
#----------------------------------------------------------
class network_soft_type(osv.osv):
	_name = "network.software.type"
	_description = "Software type"
	_columns = {
		'name': fields.char('Composant Name', size=64, required=True),
		'note': fields.text('Notes'),
	}
network_soft_type()

#----------------------------------------------------------
# A software installed on a material
#----------------------------------------------------------
class network_software(osv.osv):
	_name = "network.software"
	_description = "Software"
	_columns = {
		'name': fields.char('Composant Name', size=64, required=True),
		'material_id': fields.many2one('network.material', 'Material'),
		'type': fields.many2one('network.software.type',
								'Software Type', required=True),
		'version': fields.char('Software version', size=32),
		'logpass': fields.one2many('network.software.logpass',
									'software_id', 'Login / Password'),
		'email': fields.char('Contact Email', size=32),
		'date': fields.date('Installation Date', size=32),
		'note': fields.text('Notes'),
	}
network_software()

#------------------------------------------------------------
# Couples of login/password
#------------------------------------------------------------
class network_software_logpass(osv.osv):
	_name = "network.software.logpass"
	_description = "Software login"
	_rec_name = 'login'
	_columns = {
		'login': fields.char('Login', size=64, required=True),
		'password': fields.char('Password', size=64, required=True),
		'software_id': fields.many2one('network.software',
									'Software', required=True),
	}
network_software_logpass()
