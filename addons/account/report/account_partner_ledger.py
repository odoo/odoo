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

from openerp.tools.translate import _
from openerp import api, models
from common_report_header import common_report_header

class PartnerLedgerReport(models.AbstractModel, common_report_header):
    _name = 'report.account.report_partnerledger'

    @api.model
    def _get_lines(self, partner):
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']

        full_account = []
        if self.reconcil:
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND l.reconciled IS FALSE"
        self._cr.execute(
            "SELECT l.id, l.date, j.code, acc.code as a_code, acc.name as a_name, l.ref, m.name as move_name, l.name, l.debit, l.credit, l.amount_currency,l.currency_id, c.symbol AS currency_code " \
            "FROM account_move_line l " \
            "LEFT JOIN account_journal j " \
                "ON (l.journal_id = j.id) " \
            "LEFT JOIN account_account acc " \
                "ON (l.account_id = acc.id) " \
            "LEFT JOIN res_currency c ON (l.currency_id=c.id)" \
            "LEFT JOIN account_move m ON (m.id=l.move_id)" \
            "WHERE l.partner_id = %s " \
                "AND l.account_id IN %s " + self.query +" " \
                "AND m.state IN %s " \
                " " + RECONCILE_TAG + " "\
                "ORDER BY l.date",
                (partner.id, tuple(self.account_ids), tuple(move_state)))
        res = self._cr.dictfetchall()
        sum = 0.0
        if self.initial_balance:
            sum = self.init_bal_sum
        for r in res:
            sum += r['debit'] - r['credit']
            r['progress'] = sum
            full_account.append(r)
        return full_account

    @api.model
    def _get_intial_balance(self, partner):
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']
        if self.reconcil:
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND l.reconciled IS FALSE"
        self._cr.execute(
            "SELECT COALESCE(SUM(l.debit),0.0), COALESCE(SUM(l.credit),0.0), COALESCE(sum(debit-credit), 0.0) " \
            "FROM account_move_line AS l,  " \
            "account_move AS m "
            "WHERE l.partner_id = %s " \
            "AND m.id = l.move_id " \
            "AND m.state IN %s "
            "AND account_id IN %s" \
            " " + RECONCILE_TAG + " "\
            " " + self.init_query + " ",
            (partner.id, tuple(move_state), tuple(self.account_ids)))
        res = self._cr.fetchall()
        self.init_bal_sum = res[0][2]
        return res

    @api.model
    def _sum_debit_partner(self, partner):
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']

        result_tmp = 0.0
        result_init = 0.0
        if self.reconcil:
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND reconciled IS FALSE"
        if self.initial_balance:
            self._cr.execute(
                    "SELECT sum(debit) " \
                    "FROM account_move_line AS l, " \
                    "account_move AS m "
                    "WHERE l.partner_id = %s" \
                        "AND m.id = l.move_id " \
                        "AND m.state IN %s "
                        "AND account_id IN %s" \
                        " " + RECONCILE_TAG + " " \
                        " " + self.init_query + " ",
                    (partner.id, tuple(move_state), tuple(self.account_ids)))
            contemp = self._cr.fetchone()
            if contemp != None:
                result_init = contemp[0] or 0.0
            else:
                result_init = result_init + 0.0

        self._cr.execute(
                "SELECT sum(debit) " \
                "FROM account_move_line AS l, " \
                "account_move AS m "
                "WHERE l.partner_id = %s " \
                    "AND m.id = l.move_id " \
                    "AND m.state IN %s "
                    "AND account_id IN %s" \
                    " " + RECONCILE_TAG + " " \
                    " " + self.query + " ",
                (partner.id, tuple(move_state), tuple(self.account_ids),))
        contemp = self._cr.fetchone()
        if contemp != None:
            result_tmp = contemp[0] or 0.0
        else:
            result_tmp = result_tmp + 0.0

        return result_tmp  + result_init

    @api.model
    def _sum_credit_partner(self, partner):
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']

        result_tmp = 0.0
        result_init = 0.0
        if self.reconcil:
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND reconciled IS FALSE"
        if self.initial_balance:
            self._cr.execute(
                    "SELECT sum(credit) " \
                    "FROM account_move_line AS l, " \
                    "account_move AS m  "
                    "WHERE l.partner_id = %s" \
                        "AND m.id = l.move_id " \
                        "AND m.state IN %s "
                        "AND account_id IN %s" \
                        " " + RECONCILE_TAG + " " \
                        " " + self.init_query + " ",
                    (partner.id, tuple(move_state), tuple(self.account_ids)))
            contemp = self._cr.fetchone()
            if contemp != None:
                result_init = contemp[0] or 0.0
            else:
                result_init = result_tmp + 0.0

        self._cr.execute(
                "SELECT sum(credit) " \
                "FROM account_move_line AS l, " \
                "account_move AS m "
                "WHERE l.partner_id=%s " \
                    "AND m.id = l.move_id " \
                    "AND m.state IN %s "
                    "AND account_id IN %s" \
                    " " + RECONCILE_TAG + " " \
                    " " + self.query + " ",
                (partner.id, tuple(move_state), tuple(self.account_ids),))
        contemp = self._cr.fetchone()
        if contemp != None:
            result_tmp = contemp[0] or 0.0
        else:
            result_tmp = result_tmp + 0.0
        return result_tmp  + result_init

    @api.model
    def _get_partners(self):
        # TODO: deprecated, to remove in trunk
        if self.result_selection == 'customer':
            return _('Receivable Accounts')
        elif self.result_selection == 'supplier':
            return _('Payable Accounts')
        elif self.result_selection == 'customer_supplier':
            return _('Receivable and Payable Accounts')
        return ''

    @api.multi
    def render_html(self, data=None):
        obj_move = self.env['account.move.line']
        obj_partner = self.env['res.partner']
        self.init_bal_sum = 0.0
        ctx = data['form'].get('used_context',{})
        self.query = obj_move.with_context(ctx)._query_get(obj='l')
        self.initial_balance = data['form'].get('initial_balance', True)
        if self.initial_balance:
            ctx['initial_bal'] = True
            self.init_query = obj_move.with_context(ctx)._query_get(obj='l')
        self.reconcil = True
        if data['form']['filter'] == 'unreconciled':
            self.reconcil = False
        self.result_selection = data['form'].get('result_selection', 'customer')
        self.amount_currency = data['form'].get('amount_currency', False)
        self.target_move = data['form'].get('target_move', 'all')
        PARTNER_REQUEST = ''
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']
        if self.result_selection == 'supplier':
            self.ACCOUNT_TYPE = ['payable']
        elif self.result_selection == 'customer':
            self.ACCOUNT_TYPE = ['receivable']
        else:
            self.ACCOUNT_TYPE = ['payable','receivable']

        self._cr.execute(
            "SELECT a.id " \
            "FROM account_account a " \
            "LEFT JOIN account_account_type t " \
                "ON (a.user_type = t.id) " \
                "WHERE t.type IN %s" \
                "AND a.deprecated = 'f'", (tuple(self.ACCOUNT_TYPE), ))
        self.account_ids = [a for (a,) in self._cr.fetchall()]
        params = [tuple(move_state), tuple(self.account_ids)]
        #if we print from the partners, add a clause on active_ids
        if (data['model'] == 'res.partner') and self.ids:
            PARTNER_REQUEST =  "AND l.partner_id IN %s"
            params += [tuple(self.ids)]

        self._cr.execute("SELECT DISTINCT l.partner_id \
                FROM account_move_line AS l, account_account AS account,\
                account_move AS am \
                WHERE l.partner_id IS NOT NULL \
                    AND l.account_id = account.id \
                    AND am.id = l.move_id \
                    AND am.state IN %s \
                    " + self.query + "\
                    AND l.account_id IN %s \
                    " + PARTNER_REQUEST + " \
                    AND account.deprecated = 'f'", tuple(params))
        self.partner_ids = [res['partner_id'] for res in self._cr.dictfetchall()]
        objects = obj_partner.browse(self.partner_ids)

        report_obj = self.env['report']
        module_report = report_obj._get_report_from_name('account.report_partnerledger')
        docargs = {
            'doc_ids': self.ids,
            'doc_model': module_report.model,
            'docs': objects,
            'data': data,
            'get_account': self._get_account,
            'get_fiscalyear': self._get_fiscalyear,
            'get_journal': self._get_journal,
            'get_partners': self._get_partners,
            'get_start_date': self._get_start_date,
            'get_end_date': self._get_end_date,
            'get_target_move': self._get_target_move,
            'sum_debit_partner': self._sum_debit_partner,
            'sum_credit_partner': self._sum_credit_partner,
            'get_intial_balance': self._get_intial_balance,
            'get_lines': self._get_lines
        }
        return report_obj.render('account.report_partnerledger', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
