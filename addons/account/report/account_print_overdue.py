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
from openerp import api, models

class Overdue(models.AbstractModel):
    _name = 'report.account.report_overdue'

    @api.model
    def _lines_get(self, partner):
        return self.env['account.move.line'].search(
                [('partner_id', '=', partner.id),
                  ('account_id.internal_type', 'in', ['receivable', 'payable']),
                  ('reconciled', '=', False)])

    @api.model
    def _message(self, obj, company):
        message = company.with_context({'lang':obj.lang}).overdue_msg
        return message.split('\n')
    
    @api.model
    def get_amount(self, partner):
        move_line_ids = self._lines_get(partner)
        res = {}
        res['due_amount'] = reduce(lambda x, y: x + ((y.account_id.internal_type == 'receivable' and y.debit or 0) or (y.account_id.internal_type == 'payable' and y.credit * -1 or 0)), move_line_ids, 0)
        res['paid_amount'] = reduce(lambda x, y: x + ((y.account_id.internal_type == 'receivable' and y.credit or 0) or (y.account_id.internal_type == 'payable' and y.debit * -1 or 0)),  move_line_ids, 0)
        res['mat_amount'] = reduce(lambda x, y: x + (y.debit - y.credit), filter(lambda x: x.date_maturity < time.strftime('%Y-%m-%d'), move_line_ids), 0)
        return res

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        overdue_report = report_obj._get_report_from_name('account.report_overdue')
        docargs = {
            'doc_ids': self._ids,
            'time': time,
            'doc_model': overdue_report.model,
            'docs': self,
            'data': data,
            'message': self._message,
            'get_amount': self.get_amount,
            'getLines': self._lines_get
        }
        return report_obj.render('account.report_overdue', docargs)

