# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_compact_identifiers(self):
        partner = self.env['res.partner'].create({
            'name': 'French partner',
            'country_id': self.env.ref('base.fr').id,
            'company_registry': '334 175 221',
            'siret': '732.829.320.00074',
        })
        self.assertEqual(partner.company_registry, '334175221')
        self.assertEqual(partner.siret, '73282932000074')

        partner.write({
            'company_registry': '732.829.320.00074',
            'siret': '732 829 320 00074',
        })
        self.assertEqual(partner.company_registry, '73282932000074')
        self.assertEqual(partner.siret, '73282932000074')

    def test_keep_other_identifiers(self):
        french_partner = self.env['res.partner'].create({
            'name': 'French partner',
            'country_id': self.env.ref('base.fr').id,
            'company_registry': '.',
            'siret': '/',
        })
        self.assertEqual(french_partner.company_registry, '.')
        self.assertEqual(french_partner.siret, '/')

        foreign_partner = self.env['res.partner'].create({
            'name': 'Danish partner',
            'country_id': self.env.ref('base.dk').id,
            'company_registry': '123.456.78',
        })
        self.assertEqual(foreign_partner.company_registry, '123.456.78')

        foreign_partner.company_registry = '334 175 221'
        self.assertEqual(foreign_partner.company_registry, '334 175 221')
        french_partner.siret = '.'
        self.assertEqual(french_partner.siret, '.')

    def test_company_related_identifiers(self):
        company = self.env['res.company'].create({
            'name': 'French company',
            'country_id': self.env.ref('base.fr').id,
            'company_registry': '334 175 221',
            'siret': '732 829 320 00074',
        })
        self.assertEqual(company.company_registry, '334175221')
        self.assertEqual(company.siret, '73282932000074')

        company.write({
            'company_registry': '732.829.320',
            'siret': '732.829.320.00074',
        })
        self.assertEqual(company.company_registry, '732829320')
        self.assertEqual(company.siret, '73282932000074')
        self.assertEqual(company.partner_id.company_registry, company.company_registry)
        self.assertEqual(company.partner_id.siret, company.siret)
