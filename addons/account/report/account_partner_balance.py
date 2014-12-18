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

from openerp import models, api
from openerp.tools.translate import _
from common_report_header import common_report_header

class PartnerBalanceReport(models.AbstractModel, common_report_header):
    _name = 'report.account.report_partnerbalance'

    @api.model
    def _lines(self, data):
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']

        full_account = []
        self._cr.execute(
            "SELECT p.ref,l.account_id,ac.name AS account_name,ac.code AS code,p.name, sum(debit) AS debit, sum(credit) AS credit, " \
                    "CASE WHEN sum(debit) > sum(credit) " \
                        "THEN sum(debit) - sum(credit) " \
                        "ELSE 0 " \
                    "END AS sdebit, " \
                    "CASE WHEN sum(debit) < sum(credit) " \
                        "THEN sum(credit) - sum(debit) " \
                        "ELSE 0 " \
                    "END AS scredit, " \
                    "(SELECT sum(debit-credit) " \
                        "FROM account_move_line l " \
                        "WHERE partner_id = p.id " \
                            "" + self.query + " " \
                            "AND blocked = TRUE " \
                    ") AS enlitige " \
            "FROM account_move_line l LEFT JOIN res_partner p ON (l.partner_id=p.id) " \
            "JOIN account_account ac ON (l.account_id = ac.id)" \
            "JOIN account_account_type at ON (ac.user_type = at.id)" \
            "JOIN account_move am ON (am.id = l.move_id)" \
            "WHERE at.type IN %s " \
            "AND am.state IN %s " \
            "" + self.query + "" \
            "GROUP BY p.id, p.ref, p.name,l.account_id,ac.name,ac.code " \
            "ORDER BY l.account_id,p.name",
            (self.ACCOUNT_TYPE, tuple(move_state)))
        res = self._cr.dictfetchall()

        if self.display_partner == 'non-zero_balance':
            full_account = [r for r in res if r['sdebit'] > 0 or r['scredit'] > 0]
        else:
            full_account = [r for r in res]

        for rec in full_account:
            if not rec.get('name', False):
                rec['name'] = _('Unknown Partner')

        ## We will now compute Total
        subtotal_row = self._add_subtotal(full_account)
        return subtotal_row

    @api.model
    def _add_subtotal(self, cleanarray):
        i = 0
        completearray = []
        tot_debit = 0.0
        tot_credit = 0.0
        tot_scredit = 0.0
        tot_sdebit = 0.0
        tot_enlitige = 0.0
        for r in cleanarray:
            # For the first element we always add the line
            # type = 1 is the line is the first of the account
            # type = 2 is an other line of the account
            if i==0:
                # We add the first as the header
                #
                ##
                new_header = {}
                new_header['ref'] = ''
                new_header['name'] = r['account_name']
                new_header['code'] = r['code']
                new_header['debit'] = r['debit']
                new_header['credit'] = r['credit']
                new_header['scredit'] = tot_scredit
                new_header['sdebit'] = tot_sdebit
                new_header['enlitige'] = tot_enlitige
                new_header['balance'] = r['debit'] - r['credit']
                new_header['type'] = 3
                ##
                completearray.append(new_header)
                #
                r['type'] = 1
                r['balance'] = float(r['sdebit']) - float(r['scredit'])

                completearray.append(r)
                #
                tot_debit = r['debit']
                tot_credit = r['credit']
                tot_scredit = r['scredit']
                tot_sdebit = r['sdebit']
                tot_enlitige = (r['enlitige'] or 0.0)
                #
            else:
                if cleanarray[i]['account_id'] <> cleanarray[i-1]['account_id']:

                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3
                    # we reset the counter
                    tot_debit = r['debit']
                    tot_credit = r['credit']
                    tot_scredit = r['scredit']
                    tot_sdebit = r['sdebit']
                    tot_enlitige = (r['enlitige'] or 0.0)
                    #
                    ##
                    new_header = {}
                    new_header['ref'] = ''
                    new_header['name'] = r['account_name']
                    new_header['code'] = r['code']
                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3
                    ##get_fiscalyear
                    ##

                    completearray.append(new_header)
                    ##
                    #
                    r['type'] = 1
                    #
                    r['balance'] = float(r['sdebit']) - float(r['scredit'])

                    completearray.append(r)

                if cleanarray[i]['account_id'] == cleanarray[i-1]['account_id']:
                    # we reset the counter

                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)
                    new_header['type'] = 3

                    tot_debit = tot_debit + r['debit']
                    tot_credit = tot_credit + r['credit']
                    tot_scredit = tot_scredit + r['scredit']
                    tot_sdebit = tot_sdebit + r['sdebit']
                    tot_enlitige = tot_enlitige + (r['enlitige'] or 0.0)

                    new_header['debit'] = tot_debit
                    new_header['credit'] = tot_credit
                    new_header['scredit'] = tot_scredit
                    new_header['sdebit'] = tot_sdebit
                    new_header['enlitige'] = tot_enlitige
                    new_header['balance'] = float(tot_sdebit) - float(tot_scredit)

                    #
                    r['type'] = 2
                    #
                    r['balance'] = float(r['sdebit']) - float(r['scredit'])
                    #

                    completearray.append(r)

            i = i + 1
        return completearray

    @api.model
    def _sum_debit(self, data):
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']
        if not data.get('form', False) and data['form'].get('ids'):
            return 0.0
        self._cr.execute(
                "SELECT sum(debit) " \
                "FROM account_move_line AS l " \
                "JOIN account_move am ON (am.id = l.move_id)" \
                "WHERE l.account_id IN %s"  \
                    "AND am.state IN %s" \
                    "" + self.query + "",
                    (tuple(self.account_ids), tuple(move_state)))
        temp_res = float(self._cr.fetchone()[0] or 0.0)
        return temp_res

    @api.model
    def _sum_credit(self, data):
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']
        if not data.get('form', False) and data['form'].get('ids'):
            return 0.0
        self._cr.execute(
                "SELECT sum(credit) " \
                "FROM account_move_line AS l " \
                "JOIN account_move am ON (am.id = l.move_id)" \
                "WHERE l.account_id IN %s" \
                    "AND am.state IN %s" \
                    "" + self.query + "",
                    (tuple(self.account_ids), tuple(move_state)))
        temp_res = float(self._cr.fetchone()[0] or 0.0)
        return temp_res

    @api.model
    def _sum_litige(self, data):
        #gives the total of move lines with blocked boolean set to TRUE for the report selection
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted']

        if not data.get('form', False) and data['form'].get('ids'):
            return 0.0
        self._cr.execute(
                "SELECT sum(debit-credit) " \
                "FROM account_move_line AS l " \
                "JOIN account_move am ON (am.id = l.move_id)" \
                "WHERE l.account_id IN %s" \
                    "AND am.state IN %s" \
                    "" + self.query + " " \
                    "AND l.blocked=TRUE ",
                    (tuple(self.account_ids), tuple(move_state), ))
        temp_res = float(self._cr.fetchone()[0] or 0.0)
        return temp_res

    @api.model
    def _get_partners(self, data):
        if self.result_selection == 'customer':
            return _('Receivable Accounts')
        elif self.result_selection == 'supplier':
            return _('Payable Accounts')
        elif self.result_selection == 'customer_supplier':
            return _('Receivable and Payable Accounts')
        return ''

    @api.multi
    def render_html(self, data=None):
        self.target_move = data['form'].get('target_move', 'all')
        self.display_partner = data['form'].get('display_partner', 'non-zero_balance')
        self.result_selection = data['form'].get('result_selection')
        self.query = self.env['account.move.line']._query_get(obj='l')
        if (self.result_selection == 'customer'):
            self.ACCOUNT_TYPE = ('receivable',)
        elif (self.result_selection == 'supplier'):
            self.ACCOUNT_TYPE = ('payable',)
        else:
            self.ACCOUNT_TYPE = ('payable', 'receivable')
        self._cr.execute("SELECT a.id " \
                "FROM account_account a " \
                "LEFT JOIN account_account_type t " \
                    "ON (a.user_type = t.id) " \
                    "WHERE t.type IN (%s) " \
                    "AND a.deprecated = 'f'", (self.ACCOUNT_TYPE))
        self.account_ids = [a for (a,) in self._cr.fetchall()]

        report_obj = self.env['report']
        module_report = report_obj._get_report_from_name('account.report_partnerbalance')
        docargs = {
            'doc_ids': self.ids,
            'doc_model': module_report.model,
            'docs': self,
            'data': data,
            'get_start_date': self._get_start_date,
            'get_end_date': self._get_end_date,
            'get_account': self._get_account,
            'get_fiscalyear': self._get_fiscalyear,
            'get_journal': self._get_journal,
            'get_target_move': self._get_target_move,
            'get_partners':self._get_partners,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'sum_litige': self._sum_litige,
            'lines': self._lines
        }
        return report_obj.render('account.report_partnerbalance', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
