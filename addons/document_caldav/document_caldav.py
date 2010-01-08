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

from osv import osv, fields
from osv.orm import except_orm
import os

from document.nodes import node_content

class document_directory_content(osv.osv):
    _inherit = 'document.directory.content'    
    _columns = {
        'object_id': fields.many2one('ir.model', 'Object', required=True),        
    }

    def process_write(self, cr, uid, node, data, context=None):
        if node.extension != '.ics':
            return super(document_directory_content, self).process_write(cr, uid, node, data, context)
        content = self.browse(cr, uid, node.cnt_id, context)
        fobj = self.pool.get(content.object_id.model)
        fobj.import_cal(cr, uid, base64.encodestring(data), context=ctx)

        return True

    def process_read(self, cr, uid, node, context=None):
        ctx = (context or {})
        ctx.update(node.context.context.copy())
        ctx.update(node.dctx)
        content = self.browse(cr, uid, node.cnt_id, ctx)
        obj_class = self.pool.get(content.object_id.model)
        domain = []
        if node.act_id:
            domain.append(('id','=',node.act_id))
        # print "process read clause:",domain
        ids = obj_class.search(cr, uid, domain, context=ctx)
        ctx.update({'model': content.object_id.model})
        s = obj_class.export_cal(cr, uid, ids, context=ctx)
        return s
document_directory_content()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

