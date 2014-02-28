## -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.addons.web import http
from openerp.addons.web.http import request


class bom_structure(http.Controller):

    @http.route(['/report/mrp.report_mrpbomstructure/<docids>'], type='http', auth='user', website=True, multilang=True)
    def report_mrpbomstructure(self, docids):
        ids = [int(i) for i in docids.split(',')]
        ids = list(set(ids))
        report_obj = request.registry['mrp.bom']
        docs = report_obj.browse(request.cr, request.uid, ids, context=request.context)

        docargs = {
            'docs': docs,
            'get_children': self.get_children,
        }
        return request.registry['report'].render(request.cr, request.uid, [], 'mrp.report_mrpbomstructure', docargs)

    def get_children(self, object, level=0):
        result = []

        def _get_rec(object, level):
            for l in object:
                res = {}
                res['name'] = l.name
                res['pname'] = l.product_id.name
                res['pcode'] = l.product_id.default_code
                res['pqty'] = l.product_qty
                res['uname'] = l.product_uom.name
                res['code'] = l.code
                res['level'] = level
                result.append(res)
                if l.child_complete_ids:
                    if level<6:
                        level += 1
                    _get_rec(l.child_complete_ids,level)
                    if level>0 and level<6:
                        level -= 1
            return result

        children = _get_rec(object,level)

        return children

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
