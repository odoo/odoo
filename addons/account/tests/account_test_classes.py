# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

from odoo.tests.common import HttpCase, tagged
from odoo.exceptions import ValidationError
from odoo.tools import float_is_zero


class AccountingTestCase(HttpCase):
    """ This class extends the base TransactionCase, in order to test the
    accounting with localization setups. It is configured to run the tests after
    the installation of all modules, and will SKIP TESTS if it  cannot find an already
    configured accounting (which means no localization module has been installed).
    """

    def setUp(self):
        super(AccountingTestCase, self).setUp()
        domain = [('company_id', '=', self.env.ref('base.main_company').id)]
        if not self.env['account.account'].search_count(domain):
            _logger.warn('Test skipped because there is no chart of account defined ...')
            self.skipTest("No Chart of account found")

    def check_complete_move(self, move, theorical_lines, fields_name=None):
        ''' Compare the account.move lines with theorical_lines represented
        as a list of lines containing values sorted using fields_name.

        :param move:                An account.move record.
        :param theorical_lines:     A list of lines. Each line is itself a list of values.
                                    N.B: relational fields are represented using their ids.
        :param fields_name:         An optional list of field's names to perform the comparison.
                                    By default, this param is considered as ['name', 'debit', 'credit'].
        :return:                    True if success. Otherwise, a ValidationError is raised.
        '''
        def _get_theorical_line(aml, theorical_lines, fields_list):
            # Search for a line matching the aml parameter.
            aml_currency = aml.currency_id or aml.company_currency_id
            for line in theorical_lines:
                field_index = 0
                match = True
                for f in fields_list:
                    line_value = line[field_index]
                    aml_value = getattr(aml, f.name)

                    if f.ttype == 'float':
                        if not float_is_zero(aml_value - line_value):
                            match = False
                            break
                    elif f.ttype == 'monetary':
                        if aml_currency.compare_amounts(aml_value, line_value):
                            match = False
                            break
                    elif f.ttype in ('one2many', 'many2many'):
                        if not sorted(aml_value.ids) == sorted(line_value or []):
                            match = False
                            break
                    elif f.ttype == 'many2one':
                        if (line_value or aml_value) and aml_value.id != line_value:
                            match = False
                            break
                    elif (line_value or aml_value) and line_value != aml_value:
                        match = False
                        break

                    field_index += 1
                if match:
                    return line
            return None

        if not fields_name:
            # Handle the old behavior by using arbitrary these 3 fields by default.
            fields_name = ['name', 'debit', 'credit']

        if len(move.line_ids) != len(theorical_lines):
            raise ValidationError('Too many lines to compare: %d != %d.' % (len(move.line_ids), len(theorical_lines)))

        fields = self.env['ir.model.fields'].search([('name', 'in', fields_name), ('model', '=', 'account.move.line')])
        fields_map = dict((f.name, f) for f in fields)
        fields_list = [fields_map[f] for f in fields_name]

        for aml in move.line_ids:
            line = _get_theorical_line(aml, theorical_lines, fields_list)

            if line:
                theorical_lines.remove(line)
            else:
                raise ValidationError('Unexpected journal item. %s' % str([getattr(aml, f) for f in fields_name]))

        if theorical_lines:
            raise ValidationError('Remaining theorical line (not found). %s)' % str(theorical_lines))
        return True

    def ensure_account_property(self, property_name):
        '''Ensure the ir.property targeting an account.account passed as parameter exists.
        In case it's not: create it with a random account. This is useful when testing with
        partially defined localization (missing stock properties for example)

        :param property_name: The name of the property.
        '''
        company_id = self.env.user.company_id
        field_id = self.env['ir.model.fields'].search(
            [('model', '=', 'product.template'), ('name', '=', property_name)], limit=1)
        property_id = self.env['ir.property'].search([
            ('company_id', '=', company_id.id),
            ('name', '=', property_name),
            ('res_id', '=', None),
            ('fields_id', '=', field_id.id)], limit=1)
        account_id = self.env['account.account'].search([('company_id', '=', company_id.id)], limit=1)
        value_reference = 'account.account,%d' % account_id.id
        if property_id and not property_id.value_reference:
            property_id.value_reference = value_reference
        else:
            self.env['ir.property'].create({
                'name': property_name,
                'company_id': company_id.id,
                'fields_id': field_id.id,
                'value_reference': value_reference,
            })
