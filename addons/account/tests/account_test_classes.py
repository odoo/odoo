# -*- coding: utf-8 -*-
from odoo.tests.common import HttpCase
from odoo.exceptions import ValidationError

class AccountingTestCase(HttpCase):
    """ This class extends the base TransactionCase, in order to test the
    accounting with localization setups. It is configured to run the tests after
    the installation of all modules, and will SKIP TESTS ifit  cannot find an already
    configured accounting (which means no localization module has been installed).
    """

    post_install = True
    at_install = False

    def setUp(self):
        super(AccountingTestCase, self).setUp()
        domain = [('company_id', '=', self.env.ref('base.main_company').id)]
        if not self.env['account.account'].search_count(domain):
            self.skipTest("No Chart of account found")

    def check_complete_move(self, move, theorical_lines):
        for aml in move.line_ids:
            line = (aml.name, round(aml.debit, 2), round(aml.credit, 2))
            if line in theorical_lines:
                theorical_lines.remove(line)
            else:
                raise ValidationError('Unexpected journal item. (label: %s, debit: %s, credit: %s)' % (aml.name, round(aml.debit, 2), round(aml.credit, 2)))
        if theorical_lines:
            raise ValidationError('Remaining theorical line (not found). %s)' % ([(aml[0], aml[1], aml[2]) for aml in theorical_lines]))
        return True
