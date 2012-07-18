#!/usr/bin/env python

from tools.translate import _
from osv import osv, fields
from account.wizard.pos_box import CashBox

class PosBox(CashBox):
    _register = False

    def run(self, cr, uid, ids, context=None):
        if not context:
            context = dict()

        active_model = context.get('active_model', False) or False
        active_ids = context.get('active_ids', []) or []

        if active_model == 'pos.session':
            records = self.pool.get(active_model).browse(cr, uid, context.get('active_ids', []) or [], context=context)

            bank_statements = [record.cash_register_id for record in records if record.cash_register_id]

            if not bank_statements:
                raise osv.except_osv(_('Error !'),
                                     _("There is no cash register for this PoS Session"))

            return self._run(cr, uid, ids, bank_statements, context=context)
        else:
            return super(PosBox, self).run(cr, uid, ids, context=context)

class PosBoxIn(PosBox):
    _inherit = 'cash.box.in'

class PosBoxOut(PosBox):
    _inherit = 'cash.box.out'

