# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp import api, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        session_id = self.env.context.get('pos_session_id', False) or False
        if session_id:
            session = self.env['pos.session'].browse(session_id)
            if session:
                journal_ids = [journal.id for journal in session.config_id.journal_ids]
                args += [('id', 'in', journal_ids)]
        return super(AccountJournal, self).search(args=args, offset=offset, limit=limit, order=order, count=count)
