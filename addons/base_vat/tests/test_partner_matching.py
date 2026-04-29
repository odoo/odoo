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
            'CHE123456788', 'che123456788tva', 'CHE 123 456 788',
        ]
        for vat_to_test in variants:
            with self.subTest(vat=vat_to_test):
                partner = self.env['res.partner']._retrieve_partner(vat=vat_to_test)
                self.assertEqual(initial_partner, partner)

    def test_res_partner_search_swiss_vat_does_not_match_different_uid(self):
        initial_partner = self.env['res.partner'].create({
            'name': 'CH Test',
            'country_id': self.ref('base.ch'),
            'vat': 'CHE-123.456.788 TVA',
        })

        partner = self.env['res.partner']._retrieve_partner(vat='CHE123456780TVA')

        self.assertNotEqual(initial_partner, partner)
