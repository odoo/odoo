# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from openerp import tools
from openerp.addons.base_status.base_stage import base_stage
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import html2plaintext
class applicant_document(osv.osv):
	_name = 'hr.applicant'
	_inherit = 'hr.applicant'
	def _get_index_content(self, cr, uid, ids, fields, args, context=None):
		res = {}
		attachment_pool = self.pool.get('ir.attachment')
		for issue in self.browse(cr, uid, ids, context=context):
			res[issue.id] = 0
			attach_id = attachment_pool.search(cr, uid, [('res_model','=','hr.applicant'),('res_id','=',issue.id)])
			if attach_id:
				for attach in attachment_pool.browse(cr, uid, attach_id, context):
					res[issue.id] = attach.index_content
		return res

	_columns = {
	'index_content': fields.function(_get_index_content, string='Index Content', \
                                 type="char",store=True),
	}
applicant_document()	

