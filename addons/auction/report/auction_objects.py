# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import pooler
import time
from report import report_sxw

class auction_objects(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(auction_objects, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            #'lines': self.lines
            #'get_data' : self.get_data
        })

#   def lines(self, auction_id):
#
#        cr.execute('select ad.name from auction_dates ad, a1uction_lots al where ad.id=al.%d group by ad.name',(auction_id))
#        return self.cr.fetchone()[0]
#   def get_data(self, auction_id):
#       res = self.pool.get('auction.bid.lines').read(self.cr,self.uid,[lot_id])
#       return True



report_sxw.report_sxw('report.auction.objects', 'auction.lots', 'addons/auction/report/auction_objects.rml', parser=auction_objects)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

