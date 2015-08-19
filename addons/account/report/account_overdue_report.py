# -*- coding: utf-8 -*-

import time
from openerp import api, fields, models


class ReportOverdue(models.AbstractModel):
    _name = 'report.account.report_overdue'

    def _get_account_move_lines(self, partner_ids):
        res = dict(map(lambda x:(x,[]), partner_ids))
        self.env.cr.execute("SELECT l.date, l.name, l.ref, l.date_maturity, l.partner_id, l.blocked, "\
            "CASE WHEN at.type = 'receivable' " \
                "THEN SUM(l.debit) " \
                "ELSE SUM(l.credit * -1) " \
            "END AS debit, " \
            "CASE WHEN at.type = 'receivable' " \
                "THEN SUM(l.credit) " \
                "ELSE SUM(l.debit * -1) " \
            "END AS credit, " \
            "CASE WHEN l.date_maturity < %s " \
                "THEN SUM(l.debit - l.credit) " \
                "ELSE 0 " \
            "END AS mat " \
            "FROM account_move_line l "\
            "JOIN account_account_type at ON (l.user_type_id = at.id) "
            "WHERE partner_id IN %s AND at.type IN ('receivable', 'payable') GROUP BY l.date, l.name, l.ref, l.date_maturity, l.partner_id, at.type, l.blocked", (((fields.date.today(), ) + (tuple(partner_ids),))))
        for row in self.env.cr.dictfetchall():
            res[row.pop('partner_id')].append(row)
        return res

    @api.multi
    def render_html(self, data):
        totals = {}
        lines = self._get_account_move_lines(self.ids)
        for partner_id in self.ids:
            totals[partner_id] = dict((fn, 0.0) for fn in ['due', 'paid', 'mat', 'total'])
            for line in lines[partner_id]:
                totals[partner_id]['due'] += line['debit']
                totals[partner_id]['paid'] += line['credit']
                totals[partner_id]['mat'] += line['mat']
                totals[partner_id]['total'] += line['debit'] - line['credit']
        docargs = {
            'doc_ids': self.ids,
            'doc_model': 'res.partner',
            'docs': self.env['res.partner'].browse(self.ids),
            'time': time,
            'Lines': lines,
            'Totals': totals,
            'Date': fields.date.today(),
        }
        return self.env['report'].render('account.report_overdue', docargs)
