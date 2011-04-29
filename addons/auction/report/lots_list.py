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

import time
from report import report_sxw

class lots_list(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(lots_list, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'bid_line' : self.bid_line
        })
    def bid_line(self, lot_id):
        res = self.pool.get('auction.bid.lines').read(self.cr, self.uid, [lot_id])
        return True
report_sxw.report_sxw('report.lots.list', 'auction.lots', 'addons/auction/report/lots_list.rml', parser=lots_list)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

