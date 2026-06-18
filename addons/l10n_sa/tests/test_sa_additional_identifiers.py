from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import ValidationError


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

    def test_tin_populated_from_vat_onchange(self):
        """Selecting SA_TIN should get pre-populated by the onchange with the first 10 digits of VAT."""
        partner = self.env['res.partner'].new({
            'name': 'New Saudi Partner',
            'country_id': self.saudi_arabia.id,
            'vat': '311111111111113',
        })
        partner.additional_identifiers = {'SA_TIN': ''}
        partner._onchange_populate_sa_tin_from_vat()
        self.assertEqual(partner.additional_identifiers.get('SA_TIN'), '3111111111')
        self.assertEqual(len(partner.additional_identifiers.get('SA_TIN')), 10)
