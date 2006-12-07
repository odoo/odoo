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

from osv import osv,fields

# -------------------------------------------------------------------------
# Properties
# -------------------------------------------------------------------------

def _models_get2(self, cr, uid, context={}):
	obj = self.pool.get('ir.model.fields')
	ids = obj.search(cr, uid, [('view_load','=',1)])
	res = []
	done = {}
	for o in obj.browse(cr, uid, ids, context=context):
		if o.relation not in done:
			res.append( [o.relation, o.relation])
			done[o.relation] = True
	return res

def _models_get(self, cr, uid, context={}):
	obj = self.pool.get('ir.model.fields')
	ids = obj.search(cr, uid, [('view_load','=',1)])
	res = []
	done = {}
	for o in obj.browse(cr, uid, ids, context=context):
		if o.model_id.id not in done:
			res.append( [o.model_id.model, o.model_id.name])
			done[o.model_id.id] = True
	return res

class ir_property(osv.osv):
	_name = 'ir.property'
	_columns = {
		'name': fields.char('Name', size=128),
		'value': fields.reference('Value', selection=_models_get2, size=128),
		'res_id': fields.reference('Resource', selection=_models_get, size=128),
		'company_id': fields.many2one('res.company', 'Company'),
		'fields_id': fields.many2one('ir.model.fields', 'Fields', ondelete='cascade', required=True)
	}
	def get(self, cr, uid, name, model, res_id=False, context={}):
		cr.execute('select id from ir_model_fields where name=%s and model=%s', (name, model))
		res = cr.fetchone()
		if res:
			nid = self.search(cr, uid, [('fields_id','=',res[0]),('res_id','=',res_id)])
			if nid:
				d = self.browse(cr, uid, nid[0], context).value
				return (d and int(d.split(',')[1])) or False
		return False
ir_property()


