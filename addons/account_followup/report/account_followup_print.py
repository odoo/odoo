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
from collections import defaultdict

from openerp import pooler
from openerp.report import report_sxw

class report_rappel(report_sxw.rml_parse):
    _name = "account_followup.report.rappel"

    def __init__(self, cr, uid, name, context=None):
        super(report_rappel, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'ids_to_objects': self._ids_to_objects,
            'getLines': self._lines_get,
            'get_text': self._get_text
        })

    def _ids_to_objects(self, ids):
        pool = pooler.get_pool(self.cr.dbname)
        all_lines = []
        for line in pool.get('account_followup.stat.by.partner').browse(self.cr, self.uid, ids):
            if line not in all_lines:
                all_lines.append(line)
        return all_lines

    def _lines_get(self, stat_by_partner_line):
        return self._lines_get_with_partner(stat_by_partner_line.partner_id, stat_by_partner_line.company_id.id)

    def _lines_get_with_partner(self, partner, company_id):
        pool = pooler.get_pool(self.cr.dbname)
        moveline_obj = pool.get('account.move.line')
        moveline_ids = moveline_obj.search(self.cr, self.uid, [
                            ('partner_id', '=', partner.id),
                            ('account_id.type', '=', 'receivable'),
                            ('reconcile_id', '=', False),
                            ('state', '!=', 'draft'),
                            ('company_id', '=', company_id),
                        ])

        # lines_per_currency = {currency: [line data, ...], ...}
        lines_per_currency = defaultdict(list)
        for line in moveline_obj.browse(self.cr, self.uid, moveline_ids):
            currency = line.currency_id or line.company_id.currency_id
            line_data = {
                'name': line.move_id.name,
                'ref': line.ref,
                'date': line.date,
                'date_maturity': line.date_maturity,
                'balance': line.amount_currency if currency != line.company_id.currency_id else line.debit - line.credit,
                'blocked': line.blocked,
                'currency_id': currency,
            }
            lines_per_currency[currency].append(line_data)

        return [{'line': lines} for lines in lines_per_currency.values()]

    def _get_text(self, stat_line, followup_id, context=None):
        if context is None:
            context = {}
        fp_obj = pooler.get_pool(self.cr.dbname).get('account_followup.followup')
        fp_line = fp_obj.browse(self.cr, self.uid, followup_id).followup_line
        li_delay = []
        for line in fp_line:
            li_delay.append(line.delay)
        li_delay.sort(reverse=True)
        text = ""
        a = {}
        partner_line_ids = pooler.get_pool(self.cr.dbname).get('account.move.line').search(self.cr, self.uid, [('partner_id','=',stat_line.partner_id.id),('reconcile_id','=',False),('company_id','=',stat_line.company_id.id),('blocked','=',False)])
        partner_delay = []
        context.update({'lang': stat_line.partner_id.lang})
        for i in pooler.get_pool(self.cr.dbname).get('account.move.line').browse(self.cr, self.uid, partner_line_ids, context):
            for delay in li_delay:
                if  i.followup_line_id and str(i.followup_line_id.delay)==str(delay):
                    text = i.followup_line_id.description
                    a[delay] = text
                    partner_delay.append(delay)
        text = partner_delay and a[max(partner_delay)] or ''
        if text:
            text = text % {
                'partner_name': stat_line.partner_id.name,
                'date': time.strftime('%Y-%m-%d'),
                'company_name': stat_line.company_id.name,
                'user_signature': pooler.get_pool(self.cr.dbname).get('res.users').browse(self.cr, self.uid, self.uid, context).signature or '',
            }
        return text

report_sxw.report_sxw('report.account_followup.followup.print',
        'account_followup.stat.by.partner', 'addons/account_followup/report/account_followup_print.rml',
        parser=report_rappel)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
