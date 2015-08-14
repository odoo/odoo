# -*- coding: utf-8 -*-


class CommonReportHeader(object):

    def _compute(self, accounts):
        """ compute the balance, debit and credit for the provided
        accounts
        Arguments:
        `accounts`: accounts 
        """
        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = dict((fn, 0.0) for fn in mapping.keys())
        if accounts:
            tables, where_clause, where_params = self.env['account.move.line']._query_get()
            tables = tables.replace('"','') if tables else "account_move_line"
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())
            filters = " AND ".join(wheres)
            request = ("SELECT account_id as id, " +\
                       ', '.join(mapping.values()) +
                       " FROM " + tables +
                       " WHERE account_id IN %s " \
                            + filters +
                       " GROUP BY account_id")
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row
        return res

    def _get_target_move(self, data):
        if data.get('target_move', False):
            if data['target_move'] == 'all':
                return 'All Entries'
            return 'All Posted Entries'
        return ''

    def _get_sortby(self):
        raise ('Error!', 'Not implemented.')

    def _get_journal(self, data):
        codes = []
        if data.get('journal_ids', False):
            self.env.cr.execute('select code from account_journal where id IN %s',(tuple(data['journal_ids']),))
            codes = [x for x, in self.env.cr.fetchall()]
        return codes
