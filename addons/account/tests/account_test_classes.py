# -*- coding: utf-8 -*-

import logging
_logger = logging.getLogger(__name__)

from odoo.tests.common import HttpCase, tagged


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
