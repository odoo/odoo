from odoo.tests.common import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_l10n_ar_is_company(self):
        """Check that `is_company` is computed correctly for AR and non-AR partners."""
        it_cuit_id = self.env.ref('l10n_ar.it_cuit').id  # Tax Identification Number
        it_dni_id = self.env.ref('l10n_ar.it_dni').id  # ID card
        it_fid = self.env.ref('l10n_latam_base.it_fid')  # Foreign passport
        self.assertTrue(it_fid.l10n_ar_afip_code)

        ar_id = self.env.ref('base.ar').id
        us_id = self.env.ref('base.us').id
        ar_company, ar_person_1, ar_person_2, foreign_company, foreign_person = self.env['res.partner'].create([
            {
                'name': "AR Company",
                'country_id': ar_id,
                'l10n_latam_identification_type_id': it_cuit_id,
                'vat': '30-71429569-8',  # prefix associated to companies
            },
            {
                'name': "AR Person case 1",
                'country_id': ar_id,
                'l10n_latam_identification_type_id': it_cuit_id,
                'vat': '20-05536168-2',  # prefix not associated to companies
            },
            {
                'name': "AR Person case 2",
                'country_id': ar_id,
                'l10n_latam_identification_type_id': it_dni_id,
                'vat': '20.123.456',
            },
            {
                'name': "Foreign Company",
                'country_id': us_id,
                'l10n_latam_identification_type_id': False,
                'vat': '1234567890',
            },
            {
                'name': "Foreign Person",
                'country_id': us_id,
                'l10n_latam_identification_type_id': it_fid.id,
                'vat': '1234567890',
            },
        ])
        self.assertTrue(ar_company.is_company)
        self.assertFalse(ar_person_1.is_company)
        self.assertFalse(ar_person_2.is_company)
        self.assertTrue(foreign_company.is_company)
        # Note this last case is poorly handled in Odoo and should be fixed in future versions.
        # One could expect to have is_company False for this case, but the visibility of l10n_latam_identifier_type_id
        # in a multi company setup make it not so straightforward.
        # For now, the identification_type is ignored for such partners.
        self.assertTrue(foreign_person.is_company)
