from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestL10nSaAdditionalIdentifiers(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.saudi_arabia = cls.env.ref('base.sa')
        cls.partner_sa = cls.env['res.partner'].create({
            'name': 'Test Saudi Partner',
            'country_id': cls.saudi_arabia.id,
        })

    def test_sa_identifier_metadata_exists(self):
        """'SA' identifiers should be present in the available metadata for Saudi Arabia."""
        metadata = self.env['res.partner']._get_all_additional_identifiers_metadata()
        keys = metadata.keys()
        self.assertIn('SA_TIN', keys)
        self.assertIn('SA_CRN', keys)
        self.assertIn('SA_MOM', keys)
        self.assertIn('SA_MLS', keys)
        self.assertIn('SA_700', keys)
        self.assertIn('SA_SAG', keys)
        self.assertIn('SA_NAT', keys)
        self.assertIn('SA_GCC', keys)
        self.assertIn('SA_IQA', keys)
        self.assertIn('SA_PAS', keys)
        self.assertIn('SA_OTH', keys)

    def test_sa_mutual_exclusivity(self):
        """Only one 'SA' identifier should be active at a time."""
        self.partner_sa._set_additional_identifier('SA_CRN', '2525252525252')
        with self.assertRaisesRegex(ValidationError, "Only one Saudi Arabia identifier can be set at a time."):
            self.partner_sa._set_additional_identifier('SA_MOM', '1234567890')
        self.assertEqual(self.partner_sa.additional_identifiers.get('SA_CRN'), '2525252525252')
        self.assertNotIn('SA_MOM', self.partner_sa.additional_identifiers)

    def test_computed_scheme_and_number(self):
        """Computed fields should reflect the active 'SA' identifier."""
        self.partner_sa._set_additional_identifier('SA_CRN', '2525252525252')
        self.assertEqual(self.partner_sa.l10n_sa_edi_additional_identification_scheme, 'CRN')
        self.assertEqual(self.partner_sa.l10n_sa_edi_additional_identification_number, '2525252525252')

    def test_inverse_scheme_and_number(self):
        """Inverse fields should update the 'SA' additional identifiers"""
        self.partner_sa.l10n_sa_edi_additional_identification_scheme = 'CRN'
        self.partner_sa.l10n_sa_edi_additional_identification_number = '2525252525252'
        self.assertIn('SA_CRN', self.partner_sa.additional_identifiers)
        self.assertEqual(self.partner_sa.additional_identifiers['SA_CRN'], '2525252525252')
