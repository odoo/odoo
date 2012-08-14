#!/usr/bin/env python
from osv import osv, fields
import decimal_precision as dp
from tools.translate import _

class CashBox(osv.osv_memory):
    _register = False
    _columns = {
        'name' : fields.char('Reason', size=64, required=True),
        # Attention, we don't set a domain, because there is a journal_type key 
        # in the context of the action
        'amount' : fields.float('Amount',
                                digits_compute = dp.get_precision('Account'),
                                required=True),
    }

    def run(self, cr, uid, ids, context=None):
        if not context:
            context = dict()

        active_model = context.get('active_model', False) or False
        active_ids = context.get('active_ids', []) or []

        records = self.pool.get(active_model).browse(cr, uid, active_ids, context=context)

        return self._run(cr, uid, ids, records, context=None)

    def _run(self, cr, uid, ids, records, context=None):
        for box in self.browse(cr, uid, ids, context=context):
            for record in records:
                if not record.journal_id:
                    raise osv.except_osv(_('Error!'),
                                         _("Please check that the field 'Journal' is set on the Bank Statement"))
                    
                if not record.journal_id.internal_account_id:
                    raise osv.except_osv(_('Error!'),
                                         _("Please check that the field 'Internal Transfers Account' is set on the payment method '%s'.") % (record.journal_id.name,))

                self._create_bank_statement_line(cr, uid, box, record, context=context)

        return {}


class CashBoxIn(CashBox):
    _name = 'cash.box.in'

    _columns = CashBox._columns.copy()
    _columns.update({
        'ref' : fields.char('Reference', size=32),
    })

    def _create_bank_statement_line(self, cr, uid, box, record, context=None):
        absl_proxy = self.pool.get('account.bank.statement.line')

        values = {
            'statement_id' : record.id,
            'journal_id' : record.journal_id.id,
            'account_id' : record.journal_id.internal_account_id.id,
            'amount' : box.amount or 0.0,
            'ref' : "%s" % (box.ref or ''),
            'name' : box.name,
        }

        return absl_proxy.create(cr, uid, values, context=context)

CashBoxIn()

class CashBoxOut(CashBox):
    _name = 'cash.box.out'

    def _create_bank_statement_line(self, cr, uid, box, record, context=None):
        absl_proxy = self.pool.get('account.bank.statement.line')

        amount = box.amount or 0.0
        values = {
            'statement_id' : record.id,
            'journal_id' : record.journal_id.id,
            'account_id' : record.journal_id.internal_account_id.id,
            'amount' : -amount if amount > 0.0 else amount,
            'name' : box.name,
        }

        return absl_proxy.create(cr, uid, values, context=context)

CashBoxOut()
