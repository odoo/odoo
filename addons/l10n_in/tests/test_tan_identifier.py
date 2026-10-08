from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestTanIdentifier(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'TAN Company',
            'is_company': True,
            'country_id': cls.env.ref('base.in').id,
            'additional_identifiers': {'IN_TAN': ' abcd12345e ', 'OTHER': 'Company reference'},
        })

    def test_tan_edit_and_clear(self):
        self.assertEqual(self.partner._get_additional_identifier('IN_TAN'), 'ABCD12345E')
        self.partner._set_additional_identifier('IN_TAN', 'qwer12345t')
        self.assertEqual(self.partner._get_additional_identifier('IN_TAN'), 'QWER12345T')
        self.partner._set_additional_identifier('IN_TAN', False)
        self.assertEqual(self.partner.additional_identifiers, {'OTHER': 'Company reference'})

    def test_invalid_tan(self):
        for value in ('ABC12345E', 'ABCDE1234F', 'ABCD12345Eextra'):
            with self.subTest(value=value), self.assertRaises(ValidationError), self.cr.savepoint():
                self.partner.additional_identifiers = {'IN_TAN': value}

    def test_country_availability(self):
        self.assertIn('IN_TAN', self.partner.available_additional_identifiers_metadata)
        foreign_partner = self.env['res.partner'].create({
            'name': 'US Partner',
            'country_id': self.env.ref('base.us').id,
        })
        self.assertNotIn('IN_TAN', foreign_partner.available_additional_identifiers_metadata)
        self.partner.country_id = foreign_partner.country_id
        self.assertEqual(self.partner._get_additional_identifier('IN_TAN'), 'ABCD12345E')
        self.assertIn('IN_TAN', self.partner.available_additional_identifiers_metadata)

    def test_commercial_partner_sync(self):
        child = self.env['res.partner'].create({'name': 'Contact', 'parent_id': self.partner.id})
        self.assertEqual(child._get_additional_identifier('IN_TAN'), 'ABCD12345E')
        self.partner._set_additional_identifier('IN_TAN', 'QWER12345T')
        self.assertEqual(child._get_additional_identifier('IN_TAN'), 'QWER12345T')
        self.partner._set_additional_identifier('IN_TAN', False)
        self.assertFalse(child._get_additional_identifier('IN_TAN'))

    def test_settings_company_storage(self):
        company = self.env['res.company'].create({'name': 'TAN Company', 'partner_id': self.partner.id})
        settings = self.env['res.config.settings'].create({'company_id': company.id})
        self.assertEqual(settings.l10n_in_tan, 'ABCD12345E')
        settings.l10n_in_tan = 'qwer12345t'
        self.assertEqual(self.partner._get_additional_identifier('IN_TAN'), 'QWER12345T')
        self.partner.write({'additional_identifiers': {**self.partner.additional_identifiers, 'IN_TAN': 'ABCD12345E'}})
        settings.invalidate_recordset(['l10n_in_tan'])
        self.assertEqual(settings.l10n_in_tan, 'ABCD12345E')
        settings.l10n_in_tan = False
        self.assertEqual(self.partner.additional_identifiers, {'OTHER': 'Company reference'})

    def test_gstin_write_extracts_tan(self):
        self.partner.vat = '07DELN10357E1DH'
        self.assertEqual(self.partner._get_additional_identifier('IN_TAN'), 'DELN10357E')
        self.assertEqual(self.partner._get_additional_identifier('OTHER'), 'Company reference')
        self.assertFalse(self.partner.l10n_in_pan_entity_id)

    def test_tan_not_used_as_legal_entity_identifier(self):
        self.partner.additional_identifiers = {'IN_TAN': 'ABCD12345E'}
        self.assertFalse(self.partner._get_preferred_legal_entity_identifier_vals())
