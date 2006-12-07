##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from osv import fields,osv

class ir_attachment(osv.osv):
	_name = 'ir.attachment'
	_columns = {
		'name': fields.char('Attachment Name',size=64, required=True),
		'datas': fields.binary('Data'),
		'datas_fname': fields.char('Data Filename',size=64),
		'description': fields.text('Description'),
		'res_model': fields.char('Resource Model',size=64, required=True, readonly=True),
		'res_id': fields.integer('Resource ID', required=True, readonly=True),
		'link': fields.char('Link', size=256)
}
ir_attachment()

