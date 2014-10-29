from openerp import models, fields, api, _
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp

class CashBox(models.TransientModel):
    _register = False


    name = fields.Char(string='Reason', required=True)
    # Attention, we don't set a domain, because there is a journal_type key 
    # in the context of the action
    amount = fields.Float(string='Amount', digits = dp.get_precision('Account'), required=True)


    @api.multi
    def run(self):
        active_model = self._context.get('active_model', False) or False
        active_ids = self._context.get('active_ids', []) or []

        records = self.env[active_model].browse(active_ids)

        return self._run(records)

    @api.multi
    def _run(self, records):
        for box in self:
            for record in records:
                if not record.journal_id:
                    raise Warning(_("Please check that the field 'Journal' is set on the Bank Statement"))
                    
                if not record.journal_id.internal_account_id:
                    raise Warning(_("Please check that the field 'Internal Transfers Account' is set on the payment method '%s'.") % (record.journal_id.name,))

                box._create_bank_statement_line(record)

        return {}

    @api.one
    def _create_bank_statement_line(self, record):
        values = self._compute_values_for_statement_line(record)
        return self.env['account.bank.statement.line'].create(values)


class CashBoxIn(CashBox):
    _name = 'cash.box.in'

    ref = fields.Char('Reference')

    @api.one
    def _compute_values_for_statement_line(self, record):
        if not record.journal_id.internal_account_id.id:
            raise Warning(_("You should have defined an 'Internal Transfer Account' in your cash register's journal!"))
        return {
            'statement_id': record.id,
            'journal_id': record.journal_id.id,
            'amount': self.amount or 0.0,
            'account_id': record.journal_id.internal_account_id.id,
            'ref': '%s' % (self.ref or ''),
            'name': self.name,
        }


class CashBoxOut(CashBox):
    _name = 'cash.box.out'

    @api.one
    def _compute_values_for_statement_line(self, record):
        if not record.journal_id.internal_account_id.id:
            raise Warning(_("You should have defined an 'Internal Transfer Account' in your cash register's journal!"))
        amount = self.amount or 0.0
        return {
            'statement_id': record.id,
            'journal_id': record.journal_id.id,
            'amount': -amount if amount > 0.0 else amount,
            'account_id': record.journal_id.internal_account_id.id,
            'name': self.name,
        }
