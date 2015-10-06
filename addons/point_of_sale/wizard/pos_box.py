# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, _
from openerp.exceptions import UserError

from openerp.addons.account.wizard.pos_box import CashBox


class PosBox(CashBox):
    _register = False

    @api.multi
    def run(self):

        active_model = self.env.context.get('active_model', False) or False
        active_ids = self.env.context.get('active_ids', []) or []

        if active_model == 'pos.session':
            bank_statements = [session.cash_register_id for session in self.env[active_model].browse(active_ids) if session.cash_register_id]
            if not bank_statements:
                raise UserError(_("There is no cash register for this PoS Session"))
            return self._run(bank_statements)
        else:
            return super(PosBox, self).run()


class PosBoxIn(PosBox):
    _inherit = 'cash.box.in'

    def _compute_values_for_statement_line(self, box, record):
        values = super(PosBoxIn, self)._compute_values_for_statement_line(box=box, record=record)
        active_model = self.env.context.get('active_model', False) or False
        active_ids = self.env.context.get('active_ids', []) or []
        if active_model == 'pos.session':
            values['ref'] = self.env[active_model].browse(active_ids)[0].name
        return values


class PosBoxOut(PosBox):
    _inherit = 'cash.box.out'

    def _compute_values_for_statement_line(self, box, record):
        values = super(PosBoxOut, self)._compute_values_for_statement_line(box=box, record=record)
        active_model = self.env.context.get('active_model', False) or False
        active_ids = self.env.context.get('active_ids', []) or []
        if active_model == 'pos.session':
            values['ref'] = self.env[active_model].browse(active_ids)[0].name
        return values
