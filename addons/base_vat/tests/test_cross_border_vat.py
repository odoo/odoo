from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestCrossBorderVat(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.country_fr = cls.env.ref('base.fr')
        cls.country_hu = cls.env.ref('base.hu')
        cls.country_be = cls.env.ref('base.be')
        cls.company_hu = cls.env.company
        cls.company_hu.country_id = cls.country_hu.id

    def test_foreign_partner_local_vat(self):
        """ Test that a French partner can hold a valid Hungarian VAT
            when the active company is Hungarian. """

        partner = self.env['res.partner'].create({
            'name': 'French Vendor',
            'country_id': self.country_fr.id,
            'vat': '10537914-4-44',  # valid Hungarian VAT
        })
        self.assertEqual(partner.vat, '10537914-4-44')

    def test_foreign_partner_invalid_vat_fails(self):
        """ Test that an invalid VAT string is still blocked. """

        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Bad Vendor',
                'country_id': self.country_fr.id,
                'vat': 'XYZ88472910',
            })
