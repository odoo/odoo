# -*- coding: utf-8 -*-

import time
from openerp import api, models
from common_report_header import CommonReportHeader

class ReportPartnerLedger(models.AbstractModel, CommonReportHeader):

    _name = 'report.account.report_partnerledger'


    def _get_partners(self):
        if self.result_selection == 'customer':
            return 'Receivable Accounts'
        elif self.result_selection == 'supplier':
            return 'Payable Accounts'
        elif self.result_selection == 'customer_supplier':
            return 'Receivable and Payable Accounts'
        return ''

    def lines(self, partner):

        full_account = []
        RECONCILE_TAG = " "
        if not self.reconcil:
            RECONCILE_TAG = "AND l.reconciled IS False"
        filters = self.filters.replace('account_move_line__move_id', 'm').replace('account_move_line', 'l')
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
                "AND l.account_id IN %s " + filters +" " \
                + RECONCILE_TAG + " "\
                "ORDER BY l.date",
                ((partner.id, tuple(self.account_ids),) + tuple(self.where_params)))
        res = self._cr.dictfetchall()
        sum = 0.0
        if self.initial_balance:
            sum = self.init_bal_sum
        for r in res:
            sum += r['debit'] - r['credit']
            r['progress'] = sum
            full_account.append(r)
        return full_account

    def _sum_debit_partner(self, partner):

        result_tmp = 0.0
        result_init = 0.0
        RECONCILE_TAG = " "
        if not self.reconcil:
            RECONCILE_TAG = "AND reconciled IS False"
        if self.initial_balance:
            self._cr.execute(
                "SELECT sum(debit) FROM " + self.tables + \
                " WHERE account_move_line.partner_id = %s " \
                "AND account_id IN %s" \
                " " + RECONCILE_TAG + " " \
                + self.init_filters + " ",
                ((partner.id, tuple(self.account_ids),) + tuple(self.init_where_params)))
            contemp = self._cr.fetchone()
            if contemp != None:
                result_init = contemp[0] or 0.0
            else:
                result_init = result_tmp + 0.0

        self._cr.execute(
                "SELECT sum(debit) FROM " + self.tables + \
                " WHERE account_move_line.partner_id = %s " \
                "AND account_id IN %s" \
                " " + RECONCILE_TAG + " " \
                + self.filters + " ",
                ((partner.id, tuple(self.account_ids),) + tuple(self.where_params)))

        contemp = self._cr.fetchone()
        if contemp != None:
            result_tmp = contemp[0] or 0.0
        else:
            result_tmp = result_tmp + 0.0

        return result_tmp  + result_init

    def _sum_credit_partner(self, partner):

        result_tmp = 0.0
        result_init = 0.0
        RECONCILE_TAG = " "
        if not self.reconcil:
            RECONCILE_TAG = "AND reconciled IS NULL"
        if self.initial_balance:
            self._cr.execute(
                "SELECT sum(credit) FROM " + self.tables + \
                " WHERE account_move_line.partner_id = %s " \
                "AND account_id IN %s" \
                " " + RECONCILE_TAG + " " \
                + self.init_filters + " ",
                ((partner.id, tuple(self.account_ids),) + tuple(self.init_where_params)))
            contemp = self._cr.fetchone()
            if contemp != None:
                result_init = contemp[0] or 0.0
            else:
                result_init = result_tmp + 0.0

        self._cr.execute(
                "SELECT sum(credit) FROM " + self.tables + \
                " WHERE account_move_line.partner_id = %s " \
                "AND account_id IN %s" \
                " " + RECONCILE_TAG + " " \
                + self.filters + " ",
                ((partner.id, tuple(self.account_ids),) + tuple(self.where_params)))

        contemp = self._cr.fetchone()
        if contemp != None:
            result_tmp = contemp[0] or 0.0
        else:
            result_tmp = result_tmp + 0.0
        return result_tmp  + result_init

    def _sum_balance_partner(self, partner):

        result_tmp = 0.0
        result_init = 0.0
        RECONCILE_TAG = " "
        if not self.reconcil:
            RECONCILE_TAG = "AND reconciled IS NULL"
        if self.initial_balance:
            self._cr.execute(
                "SELECT (sum(debit) - sum(credit)) as tot_balance FROM " + self.tables + \
                " WHERE account_move_line.partner_id = %s " \
                "AND account_id IN %s" \
                " " + RECONCILE_TAG + " " \
                + self.init_filters + " ",
                ((partner.id, tuple(self.account_ids),) + tuple(self.init_where_params)))
            contemp = self._cr.fetchone()
            if contemp != None:
                result_init = contemp[0] or 0.0
            else:
                result_init = result_tmp + 0.0

        self._cr.execute(
                "SELECT (sum(debit) - sum(credit)) as tot_balance FROM " + self.tables + \
                " WHERE account_move_line.partner_id = %s " \
                "AND account_id IN %s" \
                " " + RECONCILE_TAG + " " \
                + self.filters + " ",
                ((partner.id, tuple(self.account_ids),) + tuple(self.where_params)))

        contemp = self._cr.fetchone()
        if contemp != None:
            result_tmp = contemp[0] or 0.0
        else:
            result_tmp = result_tmp + 0.0
        return result_tmp  + result_init

    def _get_intial_balance(self, partner):

        RECONCILE_TAG = " "
        if not self.reconcil:
            RECONCILE_TAG = "AND reconciled IS False"
        self._cr.execute(
            "SELECT COALESCE(SUM(debit),0.0), COALESCE(SUM(credit),0.0), COALESCE(sum(debit-credit), 0.0) FROM " \
            + self.tables +
            " WHERE account_move_line.partner_id = %s " \
            "AND account_id IN %s" \
            " " + RECONCILE_TAG + " "\
            + self.init_filters + "  ",
            ((partner.id, tuple(self.account_ids),) + tuple(self.init_where_params)))
        res = self._cr.fetchall()
        self.init_bal_sum = res[0][2]
        return res

    @api.multi
    def render_html(self, data):
        MoveLine = self.env['account.move.line']
        self.model = self._context.get('active_model')
        docs = self.env[self.model].browse(self._context.get('active_id'))
        self.amount_currency = {}
        self.init_bal_sum = 0.0
        self.reconcil = True
        if data['options']['form']['filters'] == 'unreconciled':
            self.reconcil = False
        tables, where_clause, self.where_params = MoveLine.with_context(data['options']['form'].get('used_context', {}))._query_get()
        self.tables = tables.replace('"','')
        self.wheres = [""]
        if where_clause.strip():
            self.wheres.append(where_clause.strip())
        self.filters = " AND ".join(self.wheres)
        ctx2 = data['options']['form'].get('used_context',{}).copy()
        self.initial_balance = data['options']['form'].get('initial_balance', True)

        if self.initial_balance:
            ctx2.update({'initial_bal': True})
            init_tables, init_where_clause, self.init_where_params = MoveLine.with_context(ctx2)._query_get()
            self.init_wheres = [""]
            if init_where_clause.strip():
                self.init_wheres.append(init_where_clause.strip())
            self.init_filters = " AND ".join(self.init_wheres)

        self.result_selection = data['options']['form'].get('result_selection', 'customer')
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
                "ON (a.internal_type=t.type) " \
                "WHERE a.internal_type IN %s", (tuple(self.ACCOUNT_TYPE), ))
        self.account_ids = [a for (a,) in self._cr.fetchall()]

        reconcile = "" if self.reconcil else "AND reconciled IS False "
        self._cr.execute(
                "SELECT DISTINCT account_move_line.partner_id FROM account_account AS account, " + self.tables +\
                " WHERE account_move_line.partner_id IS NOT NULL " \
                    "AND account_id = account.id " \
                    "AND account_id IN %s " \
                    + self.filters +" " \
                    + reconcile + " ", ((tuple(self.account_ids),) + tuple(self.where_params)))
        self.partner_ids = [res['partner_id'] for res in self._cr.dictfetchall()]
        self.partners = sorted(self.env['res.partner'].sudo().browse(self.partner_ids), key=lambda x: (x.ref, x.name))

        docargs = {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'data': data['options']['form'],
            'docs': docs,
            'time': time,
            'partners': self.partners,
            'lines': self.lines,
            'get_journal': self._get_journal,
            'get_partners': self._get_partners,
            'get_target_move': self._get_target_move,
            'sum_debit_partner': self._sum_debit_partner,
            'sum_credit_partner': self._sum_credit_partner,
            'sum_balance_partner': self._sum_balance_partner,
            'get_intial_balance': self._get_intial_balance,
        }
        if data['options']['form'].get('page_split'):
            return self.env['report'].render('account.report_partnerledgerother', docargs)
        return self.env['report'].render('account.report_partnerledger', docargs)
