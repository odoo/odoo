# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP S.A. <http://www.odoo.com>
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
from openerp.osv import fields, osv


class product_category(osv.osv):
    _name = "product.category"
    _inherit = "product.category"

    _columns = {
        'intrastat_id': fields.many2one('report.intrastat.code', 'Intrastat code'),
    }

    def get_intrastat_recursively(self, cr, uid, ids, context=None):
        if not hasattr(ids, '__iter__'):
            lstids = [ids,]
        else:
            lstids = ids
        res=[]
        categories = self.browse(cr, uid, lstids)
        for category in categories:
            if category.intrastat_id:
                res.append(category.intrastat_id.id)
            elif category.parent_id:
                res.append(self.get_intrastat_recursively(cr, uid, category.parent_id.id))
            else:
                res.append(None)
        if not hasattr(ids, '__iter__'):
            return res[0]
        return res
