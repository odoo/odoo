from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nESTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_es_company = cls.env['res.partner'].create({
            'name': 'ES Company',
            'vat': 'ESA12345674',
            'country_id': cls.env.ref('base.es').id,
        })

        cls.partner_es_dni = cls.env['res.partner'].create({
            'name': 'ES Individual (DNI)',
            'vat': 'ES47857909S',
            'country_id': cls.env.ref('base.es').id,
        })

        cls.partner_es_nie = cls.env['res.partner'].create({
            'name': 'ES Individual (NIE)',
            'vat': 'ESX1234567L',
            'country_id': cls.env.ref('base.es').id,
        })

    def test_is_company_es(self):
        self.assertTrue(
            self.partner_es_company.is_company,
            "ES Partner with a CIF-formatted VAT (letter + 7 digits + checksum) should be treated as a company.",
        )
        self.assertFalse(
            self.partner_es_dni.is_company,
            "ES Partner with a DNI-formatted VAT (8 digits + checksum letter) should be treated as an individual.",
        )
        self.assertFalse(
            self.partner_es_nie.is_company,
            "ES Partner with a NIE-formatted VAT (X/Y/Z + 7 digits + checksum letter) should be treated as an individual.",
        )
