# -*- coding: utf-8 -*-
from openerp.exceptions import UserError
from openerp import api, _

from openerp.addons.account.wizard.pos_box import CashBox


class PosBox(CashBox):
    _register = False

    @api.multi
    def run(self):

        active_model = self.env.context.get('active_model', False) or False
        active_ids = self.env.context.get('active_ids', []) or []

        if active_model == 'pos.session':
            pos_session = self.env[active_model].browse(active_ids)
            bank_statements = [session.cash_register_id for session in pos_session if session.cash_register_id]

            if not bank_statements:
                raise UserError(_("There is no cash register for this PoS Session"))

            return self._run(bank_statements)
        else:
            return super(PosBox, self).run()


class PosBoxIn(PosBox):
    _inherit = 'cash.box.in'

    @api.model
    def _compute_values_for_statement_line(self, box, record):
        values = super(PosBoxIn, self)._compute_values_for_statement_line(box, record)
        active_model = self.env.context.get('active_model', False) or False
        active_ids = self.env.context.get('active_ids', []) or []
        if active_model == 'pos.session':
            session = self.env[active_model].browse(active_ids)[0]
            values['ref'] = session.name
        return values


class PosBoxOut(PosBox):
    _inherit = 'cash.box.out'

    @api.model
    def _compute_values_for_statement_line(self, box, record):
        values = super(PosBoxOut, self)._compute_values_for_statement_line(box, record)
        active_model = self.env.context.get('active_model', False) or False
        active_ids = self.env.context.get('active_ids', []) or []
        if active_model == 'pos.session':
            session = self.env[active_model].browse(active_ids)[0]
            values['ref'] = session.name
        return values
