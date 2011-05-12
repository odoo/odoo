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

def _get_country(record):
    if record.partner_id \
            and record.partner_id.address \
            and record.partner_id.address[0].country_id:
        return record.partner_id.address[0].country_id.code
    else:
        return ''

def _record_to_report_line(record):
    return {'date': record.date,
            'ref': record.ref,
            'acode': record.account_id.code,
            'name': record.name,
            'debit': record.debit,
            'credit': record.credit,
            'pname': record.partner_id and record.partner_id.name or '',
            'country': _get_country(record)
            }

class account_tax_code_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(account_tax_code_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_line':self.get_line,
        })

    def get_line(self, obj):
        line_ids = self.pool.get('account.move.line').search(self.cr, self.uid, [('tax_code_id','=',obj.id)])
        if not line_ids: return []

        return map(_record_to_report_line,
                   self.pool.get('account.move.line')\
                       .browse(self.cr, self.uid, line_ids))

report_sxw.report_sxw('report.account.tax.code.entries', 'account.tax.code',
    'addons/account/report/account_tax_code.rml', parser=account_tax_code_report, header="internal")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
