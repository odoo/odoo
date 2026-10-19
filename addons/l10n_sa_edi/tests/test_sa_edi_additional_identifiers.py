from odoo.addons.l10n_sa.tests.test_sa_additional_identifiers import TestL10nSaAdditionalIdentifiers
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestL10nSaEdiAdditionalIdentifiers(TestL10nSaAdditionalIdentifiers):

    def test_computed_scheme_and_number(self):
        self.partner_sa._set_additional_identifier('SA_CRN', '2525252525252')
        self.assertEqual(self.partner_sa.l10n_sa_edi_additional_identification_scheme, 'CRN')
        self.assertEqual(self.partner_sa.l10n_sa_edi_additional_identification_number, '2525252525252')

    def test_inverse_scheme_and_number(self):
        self.partner_sa.l10n_sa_edi_additional_identification_scheme = 'CRN'
        self.partner_sa.l10n_sa_edi_additional_identification_number = '2525252525252'
        self.assertIn('SA_CRN', self.partner_sa.additional_identifiers)
        self.assertEqual(self.partner_sa.additional_identifiers['SA_CRN'], '2525252525252')

    def test_multiple_schemes_raise_warning(self):
        self.partner_sa.l10n_sa_edi_additional_identification_scheme = 'CRN'
        self.partner_sa.l10n_sa_edi_additional_identification_number = '2525252525252'
        with self.assertRaisesRegex(ValidationError, "Only one Saudi Arabia identifier can be set at a time."):
            self.partner_sa.l10n_sa_edi_additional_identification_scheme = 'OTH'
        self.assertEqual(self.partner_sa.additional_identifiers.get('SA_CRN'), '2525252525252')
        self.assertNotIn('SA_OTH', self.partner_sa.additional_identifiers)
