from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CashBox(models.TransientModel):
    _register = False

    name = fields.Char(string='Reason', required=True)
    # Attention, we don't set a domain, because there is a journal_type key 
    # in the context of the action
    amount = fields.Float(string='Amount', digits=0, required=True)

    def run(self):
        context = dict(self._context or {})
        active_model = context.get('active_model', False)
        active_ids = context.get('active_ids', [])

        records = self.env[active_model].browse(active_ids)

        return self._run(records)

    def _run(self, records):
        for box in self:
            for record in records:
                if not record.journal_id:
                    raise UserError(_("Please check that the field 'Journal' is set on the Bank Statement"))
                if not record.journal_id.company_id.transfer_account_id:
                    raise UserError(_("Please check that the field 'Transfer Account' is set on the company."))
                box._create_bank_statement_line(record)
        return {}

    def _create_bank_statement_line(self, record):
        for box in self:
            if record.state == 'confirm':
                raise UserError(_("You cannot put/take money in/out for a bank statement which is closed."))
            values = box._calculate_values_for_statement_line(record)
            record.write({'line_ids': [(0, False, values)]})


class CashBoxIn(CashBox):
    _name = 'cash.box.in'
    _description = 'Cash Box In'

    ref = fields.Char('Reference')

    def _calculate_values_for_statement_line(self, record):
        if not record.journal_id.company_id.transfer_account_id:
            raise UserError(_("You have to define an 'Internal Transfer Account' in your cash register's journal."))
        return {
            'date': record.date,
            'statement_id': record.id,
            'journal_id': record.journal_id.id,
            'amount': self.amount or 0.0,
            'account_id': record.journal_id.company_id.transfer_account_id.id,
            'ref': '%s' % (self.ref or ''),
            'name': self.name,
        }


class CashBoxOut(CashBox):
    _name = 'cash.box.out'
    _description = 'Cash Box Out'

    def _calculate_values_for_statement_line(self, record):
        if not record.journal_id.company_id.transfer_account_id:
            raise UserError(_("You have to define an 'Internal Transfer Account' in your cash register's journal."))
        amount = self.amount or 0.0
        return {
            'date': record.date,
            'statement_id': record.id,
            'journal_id': record.journal_id.id,
            'amount': -amount if amount > 0.0 else amount,
            'account_id': record.journal_id.company_id.transfer_account_id.id,
            'name': self.name,
        }
