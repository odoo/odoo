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

    def test_res_partner_search_vat_with_colon(self):
        """VAT matching and creation should handle colons as separators in VAT numbers."""
        partner_al = self.env['res.partner'].create({
            'name': 'AL Partner',
            'country_id': self.ref('base.al'),
            'vat': 'ALK12345678A',
        })
        # Should match when imported VAT has a colon separator
        self.assertEqual(partner_al, self.env['res.partner']._retrieve_partner(vat='AL:K12345678A'))

        # Also match when the partner's stored VAT has no country prefix
        partner_al_no_prefix = self.env['res.partner'].create({
            'name': 'AL Partner No Prefix',
            'country_id': self.ref('base.al'),
            'vat': 'J98765432C',
        })
        self.assertEqual(partner_al_no_prefix, self.env['res.partner']._retrieve_partner(vat='AL:J98765432C'))

        # Creating partner with colon in VAT should format and store without colon
        partner_al_colon = self.env['res.partner'].create({
            'name': 'AL Partner with Colon',
            'country_id': self.ref('base.al'),
            'vat': 'AL:M12345678B',
        })
        self.assertEqual(partner_al_colon.vat, 'ALM12345678B')
        self.assertEqual(partner_al_colon, self.env['res.partner']._retrieve_partner(vat='AL:M12345678B'))

        # Also test non-Albanian partner with colon
        partner_be = self.env['res.partner'].create({
            'name': 'BE Partner',
            'country_id': self.ref('base.be'),
            'vat': 'BE:0477472701',
        })
        self.assertEqual(partner_be.vat, 'BE0477472701')
        self.assertEqual(partner_be, self.env['res.partner']._retrieve_partner(vat='BE:0477472701'))
