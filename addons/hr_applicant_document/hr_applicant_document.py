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
from openerp.osv import fields, osv

class hr_applicant(osv.osv):
    _inherit = 'hr.applicant'

    def _get_index_content(self, cr, uid, ids, fields, args, context=None):
        res = {}
        attachment_pool = self.pool.get('ir.attachment')
        for id in ids:
            res[id] = 0
            attachment_ids = attachment_pool.search(cr, uid, [('res_model','=','hr.applicant'),('res_id','=',id)], context=context)
            if attachment_ids:
                for attachment in attachment_pool.browse(cr, uid, attachment_ids, context=context):
                    res[id] = attachment.index_content
        return res

    def _content_search(self, cursor, user, obj, name, args, context=None):
        record_ids = []
        attachment_pool = self.pool.get('ir.attachment')
        args += [('res_model','=','hr.applicant')]
        attachment_ids = attachment_pool.search(cursor, user, args, context=context)
        for attachment in attachment_pool.browse(cursor, user, attachment_ids, context=context):
            if attachment.res_id not in record_ids:
                record_ids.append(attachment.res_id)
        return [('id', 'in', record_ids)]

    _columns = {
        'index_content': fields.function(_get_index_content, string='Index Content', \
                                 fnct_search=_content_search, type="text"),
    }

