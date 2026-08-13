from odoo.tests.common import TransactionCase


class TestPartnerMatching(TransactionCase):

    def test_res_partner_search_swiss_vat_consistency(self):
        """Swiss VAT matching should handle separators, casing, and language suffixes."""
        initial_partner = self.env['res.partner'].create({
            'name': 'CH Test',
            'country_id': self.ref('base.ch'),
            'vat': 'CHE-123.456.788 TVA',
        })

        variants = [
            'CHE-123.456.788 TVA', 'CHE-123.456.788 IVA', 'CHE-123.456.788 MWST',
            'CHE123456788TVA', 'CHE123456788IVA', 'CHE123456788MWST',
            'che123456788tva',
        ]
        for vat_to_test in variants:
            with self.subTest(vat=vat_to_test):
                partner = self.env['res.partner']._retrieve_partner(vat=vat_to_test)
                self.assertEqual(initial_partner, partner)

    def test_swiss_vat_variant_creation(self):
        """
        Ensure the Swiss VAT variants are correctly generated.
        For a valid UID, all language suffix variants (TVA/IVA/MWST) should be returned.
        For an invalid UID (bad checksum), no variants should be generated,
        though an exact match on the stored VAT remains possible.
        """
        variants = self.env['res.partner']._get_country_specific_vat_variants('CHE123456788TVA', 'CH')
        self.assertCountEqual(variants, ['CHE-123.456.788 IVA', 'CHE-123.456.788 MWST', 'CHE-123.456.788 TVA'])

        incorrect_variants = self.env['res.partner']._get_country_specific_vat_variants('CHE123456789TVA', 'CH')
        self.assertFalse(incorrect_variants)
