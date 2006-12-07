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

from osv import fields, osv
from osv.osv  import Cacheable

class ir_translation(osv.osv, Cacheable):
	_name = "ir.translation"
	_log_access = False
	_columns = {
		'name': fields.char('Field Name', size=128, required=True),
		'res_id': fields.integer('Resource ID'),
		'lang': fields.char('Language', size=5),
		'type': fields.char('Type', size=16),
		'src': fields.text('Source'),
		'value': fields.text('Translation Value'),
	}
	_sql = """
		create index ir_translation_ltn on ir_translation (lang,type,name);
		create index ir_translation_res_id on ir_translation (res_id);
	"""

	def _get_ids(self, cr, uid, name, tt, lang, ids):
		translations, to_fetch = {}, []
		for id in ids:
			trans = self.get((lang, name, id))
			if trans:
				translations[id] = trans
			else:
				to_fetch.append(id)
		if to_fetch:
			cr.execute('select res_id,value from ir_translation where lang=%s and type=%s and name=%s and res_id in ('+','.join(map(str, to_fetch))+')', (lang,tt,name))
			for res_id, value in cr.fetchall():
				self.add((lang, tt, name, res_id), value)
				translations[res_id] = value
		return translations

	def _set_ids(self, cr, uid, name, tt, lang, ids, value):
		cr.execute('delete from ir_translation where lang=%s and type=%s and name=%s and res_id in ('+','.join(map(str,ids))+')', (lang,tt,name))
		for id in ids:
			self.create(cr, uid, {'lang':lang, 'type':tt, 'name':name, 'res_id':id, 'value':value})
		return len(ids)

	def _get_source(self, cr, uid, name, tt, lang, source=None):
		trans = self.get((lang, tt, name, source))
		if trans:
			return trans
		
		if source:
			source = source.strip().replace('\n',' ')
			if isinstance(source, unicode):
				source = source.encode('utf8')	
			cr.execute('select value from ir_translation where lang=%s and type=%s and name=%s and src=%s', (lang, tt, str(name), source))
		else:
			cr.execute('select value from ir_translation where lang=%s and type=%s and name=%s', (lang, tt, str(name)))
		res = cr.fetchone()
		if res:
			self.add((lang, tt, name, source), res[0])
			return res[0]
		else:
			self.add((lang, tt, name, source), False)
			return False
ir_translation()
