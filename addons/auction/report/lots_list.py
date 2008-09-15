# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import pooler
import time
from report import report_sxw

class lots_list(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(lots_list, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'bid_line' : self.bid_line
        })
    def bid_line(self, lot_id):
        res = self.pool.get('auction.bid.lines').read(self.cr,self.uid,[lot_id])
        return True
report_sxw.report_sxw('report.lots.list', 'auction.lots', 'addons/auction/report/lots_list.rml', parser=lots_list)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

