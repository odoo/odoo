# -*- coding: utf-8 -*-
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

from report.interface import report_rml

class report_custom(report_rml):
    def create(self, uid, ids, datas, context):
        datas.setdefault('form', {})
        datas['form'].setdefault('weight', 3.0)

        datas['model'] = 'stock.move.lot'
        datas['ids'] = ids
        del datas['id']

        return (super(report_custom, self).create(uid, ids, datas, context), 'pdf')

report_custom('report.stock.move.lot.ups_xml', 'stock.move.lot', 'addons/stock/report/UPS.xml', None)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

