from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPkIdentifiers(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'PK Partner',
            'country_id': cls.env.ref('base.pk').id,
        })

    def test_business_identification(self):
        """Business Identification: relabeled Tax ID validating the NTN/CNIC formats."""
        self.assertEqual(self.env.ref('base.pk').vat_label, 'Business Identification')
        for value in ('4174942', '1234567-8', '12345-1234567-8'):
            self.partner.vat = value
            self.assertEqual(self.partner.vat, value)
        for value in ('12345', '1234abc'):
            with self.assertRaises(ValidationError):
                self.partner.vat = value
        # A rejection reports the accepted formats back to the user.
        with self.assertRaisesRegex(ValidationError, '12345-1234567-8'):
            self.partner.vat = '123'

    def test_consumer_identification(self):
        """Consumer Identification: offered for PK only, stored normalized."""
        metadata = self.partner.available_additional_identifiers_metadata
        self.assertIn('PK_CN', metadata)
        self.assertFalse(metadata['PK_CN'].get('display_optional'))
        self.partner._set_additional_identifier('PK_CN', '4210112345678')
        self.assertEqual(self.partner.additional_identifiers.get('PK_CN'), '42101-1234567-8')
        for value in ('12345', '4210112345abc'):
            with self.assertRaises(ValidationError):
                self.partner._set_additional_identifier('PK_CN', value)

        be_partner = self.env['res.partner'].create({
            'name': 'BE Partner',
            'country_id': self.env.ref('base.be').id,
        })
        self.assertNotIn('PK_CN', be_partner.available_additional_identifiers_metadata)
