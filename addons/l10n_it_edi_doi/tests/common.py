# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiDoi(TestItEdi):

    @classmethod
    @TestItEdi.setup_country('it')
    def setUpClass(cls):
        super().setUpClass()

        cls.declaration_1000 = cls.env['l10n_it_edi_doi.declaration_of_intent'].create({
            'company_id': cls.company.id,
            'partner_id': cls.italian_partner_a.id,
            'issue_date': '2019-01-01',
            'start_date': '2019-01-01',
            'end_date': '2019-12-31',
            'threshold': 1000,
            'protocol_number_part1': 'test 2019',
            'protocol_number_part2': 'threshold 1000',
        })
        cls.declaration_1000.action_validate()

        cls.product_1 = cls.env['product.product'].create([{'name': 'test product 1'}])

        cls.pricelist = cls.env['product.pricelist'].with_company(cls.company).create({
            'name': 'EUR pricelist',
            'currency_id': cls.company.currency_id.id,
            'company_id': False,
        })
