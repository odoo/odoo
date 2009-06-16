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

import time
import mx.DateTime
from report import report_sxw
from osv import osv
import pooler
import rml_parse

class event_certificate(rml_parse.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(event_certificate, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
            'get_date':self.get_date,
        })
        
    def get_date(self,st_date,end_date):
        date_res = ''
        print "st_date::end_date",str(st_date),str(end_date)
        try:
            d1 = mx.DateTime.strptime(str(st_date),'%d/%m/%Y %H:%M:%S')
            d2 = mx.DateTime.strptime(str(end_date),'%d/%m/%Y %H:%M:%S')
            print "d1:::d2",d1,d2
            new_d1 = d1.strftime('%d %B %Y %H:%M:%S')
            new_d2 = d2.strftime('%d %B %Y %H:%M:%S')
            print "new_d1:::new_d2",new_d1,new_d2
            date_res = str(new_d1) +" "+ 'To' +" "+ str(new_d2)
            print "date_res:::",date_res
        except Exception,e:
            print "e:::",e
            pass
        return date_res
            
    
report_sxw.report_sxw('report.event.certificate','event.registration','event_certificate/report/event_certificate.rml',parser=event_certificate)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
