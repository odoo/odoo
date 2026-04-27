# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib

import psycopg2

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base_import.models.base_import import FIELDS_RECURSION_LIMIT


class AccountBankStmtImportCSV(models.TransientModel):

    _inherit = 'base_import.import'

    @api.model
    def get_fields_tree(self, model, depth=FIELDS_RECURSION_LIMIT):
        fields_list = super(AccountBankStmtImportCSV, self).get_fields_tree(model, depth=depth)
        if self._context.get('bank_stmt_import', False):
            add_fields = [{
                'id': 'balance',
                'name': 'balance',
                'string': 'Cumulative Balance',
                'required': False,
                'fields': [],
                'type': 'monetary',
                'model_name': model,
            }, {
                'id': 'debit',
                'name': 'debit',
                'string': 'Debit',
                'required': False,
                'fields': [],
                'type': 'monetary',
                'model_name': model,
            }, {
                'id': 'credit',
                'name': 'credit',
                'string': 'Credit',
                'required': False,
                'fields': [],
                'type': 'monetary',
                'model_name': model,
            }]
            fields_list.extend(add_fields)
        return fields_list

    def _convert_to_float(self, value):
        return float(value) if value else 0.0

    def _parse_import_data(self, data, import_fields, options):
        # EXTENDS base
        data = super()._parse_import_data(data, import_fields, options)
        journal_id = self._context.get('default_journal_id')
        bank_stmt_import = options.get('bank_stmt_import')
        if not journal_id or not bank_stmt_import:
            return data

        has_amount = 'amount' in import_fields
        has_credit = 'credit' in import_fields
        has_debit = 'debit' in import_fields
        if (has_debit ^ has_credit) or not (has_amount ^ has_debit):
            raise ValidationError(_("Make sure that an Amount or Debit and Credit is in the file."))
        statement_vals = options['statement_vals'] = {}
        ret_data = []

        import_fields.append('sequence')
        index_balance = False
        convert_to_amount = False

        # check that the rows are sorted by date (ascending or descending) as we assume they are in the following code
        # we can't order the rows for the user as two rows could have the same date
        # and we don't have a way to know which one should be first
        if 'date' in import_fields:
            index_date = import_fields.index('date')
            dates = [fields.Date.from_string(line[index_date]) for line in data if line[index_date]]
            sorted_dates_asc = sorted(dates)
            if dates != sorted_dates_asc:  # If dates are not in ascending order, check if they are in descending order
                sorted_dates_desc = sorted_dates_asc[::-1]
                if dates == sorted_dates_desc:
                    data = data[::-1]  # reverse data if dates are in descending order to make them ascending
                else:  # If dates are not sorted at all, we throw an error
                    raise UserError(_('Rows must be sorted by date.'))

        if 'debit' in import_fields and 'credit' in import_fields:
            index_debit = import_fields.index('debit')
            index_credit = import_fields.index('credit')
            self._parse_float_from_data(data, index_debit, 'debit', options)
            self._parse_float_from_data(data, index_credit, 'credit', options)
            import_fields.append('amount')
            convert_to_amount = True

        # add starting balance and ending balance to context
        if 'balance' in import_fields:
            index_balance = import_fields.index('balance')
            self._parse_float_from_data(data, index_balance, 'balance', options)
            statement_vals['balance_start'] = self._convert_to_float(data[0][index_balance])
            statement_vals['balance_start'] -= self._convert_to_float(data[0][import_fields.index('amount')]) \
                                            if not convert_to_amount \
                                            else abs(self._convert_to_float(data[0][index_credit]))-abs(self._convert_to_float(data[0][index_debit]))
            statement_vals['balance_end_real'] = data[len(data)-1][index_balance]
            import_fields.remove('balance')

        if convert_to_amount:
            import_fields.remove('debit')
            import_fields.remove('credit')

        for index, line in enumerate(data):
            line.append(index)
            remove_index = []
            if convert_to_amount:
                line.append(
                    abs(self._convert_to_float(line[index_credit]))
                    - abs(self._convert_to_float(line[index_debit]))
                )
                remove_index.extend([index_debit, index_credit])
            if index_balance:
                remove_index.append(index_balance)
            # Remove added field debit/credit/balance
            for index in sorted(remove_index, reverse=True):
                del line[index]
            if line[import_fields.index('amount')]:
                ret_data.append(line)

        return ret_data

    def parse_preview(self, options, count=10):
        if options.get('bank_stmt_import', False):
            self = self.with_context(bank_stmt_import=True)
        return super(AccountBankStmtImportCSV, self).parse_preview(options, count=count)

    def execute_import(self, fields, columns, options, dryrun=False):
        if options.get('bank_stmt_import'):
            with self.env.cr.savepoint(flush=False) as sp:
                res = super().execute_import(fields, columns, options, dryrun=dryrun)

                if not 'statement_id' in fields:
                    statement = self.env['account.bank.statement'].create({
                        'reference': self.file_name,
                        'line_ids': [Command.set(res.get('ids', []))],
                        **options.get('statement_vals', {}),
                    })

                with contextlib.suppress(psycopg2.InternalError):
                    sp.close(rollback=dryrun)

                return res
        else:
            return super(AccountBankStmtImportCSV, self).execute_import(fields, columns, options, dryrun=dryrun)
