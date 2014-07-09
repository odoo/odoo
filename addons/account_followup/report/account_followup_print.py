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
from openerp.osv import osv
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
        all_lines = []
        for line in self.pool['account_followup.stat.by.partner'].browse(self.cr, self.uid, ids):
            if line not in all_lines:
                all_lines.append(line)
        return all_lines

    def _lines_get(self, stat_by_partner_line):
        return self._lines_get_with_partner(stat_by_partner_line.partner_id, stat_by_partner_line.company_id.id)

    def _lines_get_with_partner(self, partner, company_id):
        moveline_obj = self.pool['account.move.line']
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
        context = dict(context or {}, lang=stat_line.partner_id.lang)
        fp_obj = self.pool['account_followup.followup']
        fp_line = fp_obj.browse(self.cr, self.uid, followup_id, context=context).followup_line
        if not fp_line:
            raise osv.except_osv(_('Error!'),_("The followup plan defined for the current company does not have any followup action."))
        #the default text will be the first fp_line in the sequence with a description.
        default_text = ''
        li_delay = []
        for line in fp_line:
            if not default_text and line.description:
                default_text = line.description
            li_delay.append(line.delay)
        li_delay.sort(reverse=True)
        a = {}
        #look into the lines of the partner that already have a followup level, and take the description of the higher level for which it is available
        partner_line_ids = self.pool['account.move.line'].search(self.cr, self.uid, [('partner_id','=',stat_line.partner_id.id),('reconcile_id','=',False),('company_id','=',stat_line.company_id.id),('blocked','=',False),('state','!=','draft'),('debit','!=',False),('account_id.type','=','receivable'),('followup_line_id','!=',False)])
        partner_max_delay = 0
        partner_max_text = ''
        for i in self.pool['account.move.line'].browse(self.cr, self.uid, partner_line_ids, context=context):
            if i.followup_line_id.delay > partner_max_delay and i.followup_line_id.description:
                partner_max_delay = i.followup_line_id.delay
                partner_max_text = i.followup_line_id.description
        text = partner_max_delay and partner_max_text or default_text
        if text:
            text = text % {
                'partner_name': stat_line.partner_id.name,
                'date': time.strftime('%Y-%m-%d'),
                'company_name': stat_line.company_id.name,
                'user_signature': self.pool['res.users'].browse(self.cr, self.uid, self.uid, context).signature or '',
            }
        return text


class report_followup(osv.AbstractModel):
    _name = 'report.account_followup.report_followup'
    _inherit = 'report.abstract_report'
    _template = 'account_followup.report_followup'
    _wrapped_report_class = report_rappel

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
