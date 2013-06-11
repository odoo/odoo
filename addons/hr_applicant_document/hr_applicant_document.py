# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################


import time
from openerp import tools
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _

class applicant_document(osv.osv):
	_name = 'hr.applicant'
	_inherit = 'hr.applicant'

	def _get_index_content(self, cr, uid, ids, fields, args, context=None):
		res = {}
		attachment_pool = self.pool.get('ir.attachment')
		for applicant in self.browse(cr, uid, ids, context=context):
			res[applicant.id] = 0
			attach_id = attachment_pool.search(cr, uid, [('res_model','=','hr.applicant'),('res_id','=',applicant.id)])
			if attach_id:
				for attach in attachment_pool.browse(cr, uid, attach_id, context):
					res[applicant.id] = attach.index_content
		return res

	def _content_search(self, cursor, user, obj, name, args, context=None):
		record_ids = []
		attachment_pool = self.pool.get('ir.attachment')
		args += [('res_model','=','hr.applicant')]
		attach_ids = attachment_pool.search(cursor, user, args)
		for attach in attachment_pool.browse(cursor, user, attach_ids):
			record_ids.append(attach.res_id)			
		return [('id', 'in', record_ids)]

	_columns = {
	'index_content': fields.function(_get_index_content, string='Index Content', \
                                 fnct_search=_content_search,type="text"),
	}

