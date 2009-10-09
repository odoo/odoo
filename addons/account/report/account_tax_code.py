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
import pooler
import rml_parse
import copy
from report import report_sxw
import re

class account_tax_code_report(rml_parse.rml_parse):
    #_name = 'report.account.tax.code.entries'
    
    def __init__(self, cr, uid, name, context):
        super(account_tax_code_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_line':self.get_line,
        })
        
    def get_line(self,obj):
        res = {}
        result = []
        line_ids = self.pool.get('account.move.line').search(self.cr,self.uid,[('tax_code_id','=',obj.id)])
        if line_ids:
            move_line_objs = self.pool.get('account.move.line').browse(self.cr,self.uid,line_ids)
            for line in move_line_objs:
               res['date'] = line.date
               res['ref'] = line.ref
               res['acode'] = line.account_id.code
               res['pname'] = ''
               res['country'] = ''

               if line.partner_id:
                   res['pname'] = line.partner_id.name
                   if line.partner_id.address and line.partner_id.address[0].country_id:
                           res['country'] = line.partner_id.address[0].country_id.code
               res['name'] = line.name
               res['debit'] = line.debit
               res['credit'] = line.credit
               result.append(res)

        return result
        
report_sxw.report_sxw('report.account.tax.code.entries', 'account.tax.code',
    'addons/account/report/account_tax_code.rml', parser=account_tax_code_report, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
