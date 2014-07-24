# -*- coding: utf-8 -*-

import logging
import base64
import os

from openerp.osv import fields, osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

_IMPORT_FILE_TYPE = []
try:
    from ofxparse import OfxParser as ofxparser
    _IMPORT_FILE_TYPE = [('ofx', 'OFX')]
except ImportError:
    _logger.warning("OFX parser partially unavailable because the `ofxparse` Python library cannot be found. "
                    "It can be easily download and install from this `https://pypi.python.org/pypi/ofxparse`.")
    ofxparser = None


class account_bank_statement_import(osv.TransientModel):
    _name = 'account.bank.statement.import'
    _description = 'Import Bank Statement'
    _columns = {
        'data_file': fields.binary('Bank Statement File', required=True, help='Select bank statement file to import in OpenERP. .OFX, .QIF or CODA are accepted.'),
        'file_type': fields.selection(_IMPORT_FILE_TYPE, 'File Type'),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True),
    }

    def _get_default_journal(self, cr, uid, context=None):
        company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'account.bank.statement', context=context)
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'bank'), ('company_id', '=', company_id)], context=context)
        return journal_ids and journal_ids[0] or False

    _defaults = {
        'file_type': _IMPORT_FILE_TYPE and 'ofx' or False,
        'journal_id': _get_default_journal,
    }

    def import_bank_statement(self, cr, uid, bank_statement_vals=False, context=None):
        statement_ids = []
        for vals in bank_statement_vals:
            statement_ids.append(self.pool.get('account.bank.statement').create(cr, uid, vals, context=context))
        return statement_ids

    def process_ofx(self, cr, uid, data_file, journal_id=False, context=None):
        try:
            tempfile = open("temp.ofx", "w+")
            tempfile.write(base64.decodestring(data_file))
            tempfile.read()
            pathname = os.path.dirname('temp.ofx')
            path = os.path.join(os.path.abspath(pathname), 'temp.ofx')
            ofx = ofxparser.parse(file(path))
        except:
            raise osv.except_osv(_('Import Error!'), _('Please check OFX file format is proper or not.'))
        line_ids = []
        total_amt = 0.00
        try:
            for transaction in ofx.account.statement.transactions:
                vals_line = {
                    'date': transaction.date,
                    'name': transaction.memo,
                    'ref': transaction.id,
                    'amount': transaction.amount,
                }
                total_amt += float(transaction.amount)
                line_ids.append((0, 0, vals_line))
        except Exception, e:
            raise osv.except_osv(_('Error!'), _("Following problem has been occurred while importing your file, Please verify the file is proper or not.\n\n %s" % e.message))
        st_start_date = ofx.account.statement.start_date or False
        st_end_date = ofx.account.statement.end_date or False
        period_obj = self.pool.get('account.period')
        if st_end_date:
            period_ids = period_obj.find(cr, uid, st_end_date, context=context)
        else:
            period_ids = period_obj.find(cr, uid, st_start_date, context=context)
        vals_bank_statement = {
            'name': ofx.account.routing_number,
            'balance_start': ofx.account.statement.balance,
            'balance_end_real': float(ofx.account.statement.balance) + total_amt,
            'period_id': period_ids and period_ids[0] or False,
            'journal_id': journal_id
        }
        vals_bank_statement.update({'line_ids': line_ids})
        os.remove(path)
        return [vals_bank_statement]

    def parse_file(self, cr, uid, ids, context=None):
        data = self.browse(cr, uid, ids[0], context=context)
        vals = getattr(self, "process_%s" % data.file_type)(cr, uid, data.data_file, data.journal_id.id, context=context)
        statement_ids = self.import_bank_statement(cr, uid, vals, context=context)
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'action_bank_statement_tree')
        action = self.pool[model].read(cr, uid, action_id, context=context)
        action['domain'] = "[('id', 'in', [" + ', '.join(map(str, statement_ids)) + "])]"
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
