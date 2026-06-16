from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_l10n_ar_is_company(self):
        """Check that `is_company` is computed correctly for AR and non-AR partners."""
        ar_id = self.env.ref('base.ar').id
        us_id = self.env.ref('base.us').id
        ar_company, ar_person_1, ar_person_2, foreign_company, foreign_person = self.env['res.partner'].create([
            {
                'name': "AR Company",
                'country_id': ar_id,
                'vat': '30-71429569-8',  # CUIT, prefix associated to companies
            },
            {
                'name': "AR Person case 1",
                'country_id': ar_id,
                'vat': '20-05536168-2',  # CUIT, prefix not associated to companies
            },
            {
                'name': "AR Person case 2",
                'country_id': ar_id,
                'additional_identifiers': {'AR_DNI': '20.123.456'},
            },
            {
                'name': "Foreign Company",
                'country_id': us_id,
                'vat': '1234567890',
            },
            {
                'name': "Foreign Person",
                'country_id': us_id,
                'additional_identifiers': {'PASSPORT': '1234567890'},
            },
        ])
        ar_contact = self.env['res.partner'].create({
            'name': "AR Contact",
            'country_id': ar_id,
            'parent_id': ar_company.id,
        })
        self.assertTrue(ar_company.is_company)
        self.assertFalse(ar_contact.is_company)
        self.assertFalse(ar_person_1.is_company)
        self.assertFalse(ar_person_2.is_company)
        self.assertTrue(foreign_company.is_company)
        # A foreign person identified only by a passport-like document has no `vat`,
        # so the base heuristic correctly classifies them as a person, not a company.
        self.assertFalse(foreign_person.is_company)

    def test_l10n_ar_state_afip_code(self):
        """The generic state ID (`AR_CI`) derives its AFIP document type from the state."""
        ar_id = self.env.ref('base.ar').id
        cordoba = self.env.ref('base.state_ar_x')   # AFIP code 3
        santa_fe = self.env.ref('base.state_ar_s')  # AFIP code 12

        partner = self.env['res.partner'].create({
            'name': "AR State ID",
            'country_id': ar_id,
            'state_id': cordoba.id,
            'additional_identifiers': {'AR_CI': '1234567'},
        })
        self.assertEqual(partner.l10n_ar_afip_code, '3')

        # Changing to another state that issues a state ID re-derives the AFIP code.
        partner.state_id = santa_fe
        self.assertEqual(partner.l10n_ar_afip_code, '12')

    def test_l10n_ar_state_required_for_ci(self):
        """`_check_l10n_ar_state`: `AR_CI` requires a state that issues a state ID,
        and that holds both when setting the identifier and when editing the state."""
        ar_id = self.env.ref('base.ar').id
        cordoba = self.env.ref('base.state_ar_x')
        caba = self.env.ref('base.state_ar_c')  # does not issue a state ID (uses CPF)

        # Creating with AR_CI but no state is rejected.
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': "AR State ID no state",
                'country_id': ar_id,
                'additional_identifiers': {'AR_CI': '1234567'},
            })

        # CABA does not issue a state ID, so it is rejected too.
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': "AR State ID CABA",
                'country_id': ar_id,
                'state_id': caba.id,
                'additional_identifiers': {'AR_CI': '1234567'},
            })

        # Clearing the state of a partner that has AR_CI is rejected.
        partner = self.env['res.partner'].create({
            'name': "AR State ID",
            'country_id': ar_id,
            'state_id': cordoba.id,
            'additional_identifiers': {'AR_CI': '1234567'},
        })
        with self.assertRaises(ValidationError):
            partner.state_id = False

        # Changing the state to one that does not issue a state ID is rejected.
        partner = self.env['res.partner'].create({
            'name': "AR State ID 2",
            'country_id': ar_id,
            'state_id': cordoba.id,
            'additional_identifiers': {'AR_CI': '1234567'},
        })
        with self.assertRaises(ValidationError):
            partner.state_id = caba
