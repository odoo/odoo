# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv


class account_journal(osv.osv):
    _inherit = 'account.journal'

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        session_id = context.get('pos_session_id', False) or False

        if session_id:
            session = self.pool.get('pos.session').browse(cr, uid, session_id, context=context)

            if session:
                journal_ids = [journal.id for journal in session.config_id.journal_ids]
                args += [('id', 'in', journal_ids)]

        return super(account_journal, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)