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
from osv import osv, fields
from tools.translate import _

class account_journal_common_default(object):

    def _sum_debit(self, period_id, journal_id=False):
        if isinstance(journal_id, int):
            journal_id = [journal_id]
        if not journal_id:
            journal_id = self.journal_ids
        self.cr.execute('SELECT SUM(debit) FROM account_move_line l WHERE period_id=%s AND journal_id IN %s '+self.query_get_clause+' ', (period_id, tuple(journal_id)))
        res = self.cr.fetchone()[0]
        return res or 0.0

    def _sum_credit(self, period_id, journal_id=False):
        if isinstance(journal_id, int):
            journal_id = [journal_id]
        if not journal_id:
            journal_id = self.journal_ids
        self.cr.execute('SELECT SUM(credit) FROM account_move_line l WHERE period_id=%s AND journal_id IN %s '+self.query_get_clause+'', (period_id, tuple(journal_id)))
        return self.cr.fetchone()[0] or 0.0

    def get_start_date(self, form):
        return pooler.get_pool(self.cr.dbname).get('account.period').browse(self.cr,self.uid,form['period_from']).name

    def get_end_date(self, form):
        return pooler.get_pool(self.cr.dbname).get('account.period').browse(self.cr,self.uid,form['period_to']).name

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: