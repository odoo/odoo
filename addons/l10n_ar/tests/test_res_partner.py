from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from . import common


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(common.TestArCommon):

    def test_l10n_ar_is_company(self):
        """Check that `is_company` is computed correctly for AR and non-AR partners."""
        ar_id = self.env.ref('base.ar').id
        us_id = self.env.ref('base.us').id
        ar_company, ar_person_1, ar_person_2, foreign_company, foreign_person = self.env['res.partner'].create([
            {
                'name': "AR Company",
                'country_id': ar_id,
                'vat': '30-71429569-8',  # prefix associated to companies
            },
            {
                'name': "AR Person case 1",
                'country_id': ar_id,
                'vat': '20-05536168-2',  # prefix not associated to companies
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

        partner.state_id = santa_fe
        self.assertEqual(partner.l10n_ar_afip_code, '12')

    def test_l10n_ar_identifier_precedence(self):
        """The AFIP identification follows the document precedence (DNI, then CUIL, then the
        rest) and not the order the identifiers were entered in."""
        ar_id = self.env.ref('base.ar').id
        partner = self.env['res.partner'].create({
            'name': "AR Person many IDs",
            'country_id': ar_id,
            'additional_identifiers': {
                'PASSPORT': 'AAB4587345',
                'AR_CUIL': '20348204263',
                'AR_DNI': '34654873',
            },
        })
        self.assertEqual(partner.l10n_ar_afip_code, '96')
        self.assertEqual(partner.l10n_ar_afip_id_value, '34654873')
        self.assertEqual(partner._get_id_number_sanitize(), 34654873)

        partner = self.env['res.partner'].create({
            'name': "AR Person no DNI",
            'country_id': ar_id,
            'additional_identifiers': {
                'PASSPORT': 'AAB4587345',
                'AR_CUIL': '20348204263',
            },
        })
        self.assertEqual(partner.l10n_ar_afip_code, '86')
        self.assertEqual(partner.l10n_ar_afip_id_value, '20348204263')

    def test_l10n_ar_state_required_for_ci(self):
        """`_check_l10n_ar_state`: `AR_CI` requires a state that issues a state ID,
        and that holds both when setting the identifier and when editing the state."""
        ar_id = self.env.ref('base.ar').id
        cordoba = self.env.ref('base.state_ar_x')
        caba = self.env.ref('base.state_ar_c')  # does not issue a state ID (uses CPF)

        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': "AR State ID no state",
                'country_id': ar_id,
                'additional_identifiers': {'AR_CI': '1234567'},
            })

        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': "AR State ID CABA",
                'country_id': ar_id,
                'state_id': caba.id,
                'additional_identifiers': {'AR_CI': '1234567'},
            })

        partner = self.env['res.partner'].create({
            'name': "AR State ID",
            'country_id': ar_id,
            'state_id': cordoba.id,
            'additional_identifiers': {'AR_CI': '1234567'},
        })
        with self.assertRaises(ValidationError):
            partner.state_id = False

        partner = self.env['res.partner'].create({
            'name': "AR State ID 2",
            'country_id': ar_id,
            'state_id': cordoba.id,
            'additional_identifiers': {'AR_CI': '1234567'},
        })
        with self.assertRaises(ValidationError):
            partner.state_id = caba

    def test_prevent_arca_responsibility_change(self):
        """ Test that changing the ARCA responsibility is blocked for a company
        if accounting entries already exist, but allowed for standard partners."""

        invoice = self._create_invoice_ar(
            partner_id=self.res_partner_adhoc,
            company_id=self.company_ri,
        )
        self._post(invoice)
        self.assertTrue(self.company_ri._existing_accounting())

        new_responsibility = self.env.ref("l10n_ar.res_IVAE")

        # Try to change responsibility type for the company partner, should raise error
        with self.assertRaisesRegex(UserError, 'Could not change the ARCA Responsibility'):
            self.partner_ri.l10n_ar_afip_responsibility_type_id = new_responsibility

        # Try to change responsibility type via the company itself, should raise error
        with self.assertRaisesRegex(UserError, 'Could not change the ARCA Responsibility'):
            self.company_ri.l10n_ar_afip_responsibility_type_id = new_responsibility

        # Try to change responsibility type for a normal partner, should succeed
        self.res_partner_adhoc.l10n_ar_afip_responsibility_type_id = new_responsibility
        self.assertEqual(self.res_partner_adhoc.l10n_ar_afip_responsibility_type_id, new_responsibility)

    def test_arca_responsibility_change_branch_without_entries(self):
        """ Test that a branch company with no accounting entries can change its ARCA
        responsibility type even if the parent company already has accounting entries."""

        branch = self.company_ri.create({
            'name': 'Branch RI',
            'parent_id': self.company_ri.id,
            'country_id': self.company_ri.country_id.id,
        })

        invoice = self._create_invoice_ar(
            partner_id=self.res_partner_adhoc,
            company_id=self.company_ri,
        )
        self._post(invoice)

        # Parent has accounting entries, branch does not
        self.assertTrue(self.company_ri._existing_accounting())
        self.assertFalse(branch._existing_accounting())

        # Branch can change its ARCA responsibility type
        new_responsibility = self.env.ref("l10n_ar.res_IVAE")
        branch.partner_id.l10n_ar_afip_responsibility_type_id = new_responsibility
        self.assertEqual(branch.l10n_ar_afip_responsibility_type_id, new_responsibility)

        # Parent cannot change its ARCA responsibility type
        with self.assertRaisesRegex(UserError, 'Could not change the ARCA Responsibility'):
            self.partner_ri.l10n_ar_afip_responsibility_type_id = new_responsibility

    def test_create_parent_keeps_afip_responsibility(self):
        """A company created from a contact's company name keeps the contact's ARCA responsibility."""
        ri = self.env.ref('l10n_ar.res_IVARI')
        contact = self.env['res.partner'].create({
            'name': "AR Contact",
            'l10n_ar_afip_responsibility_type_id': ri.id,
        })
        company = contact._create_parent_from_name("AR Company")
        self.assertEqual(company.l10n_ar_afip_responsibility_type_id, ri)
        self.assertEqual(contact.l10n_ar_afip_responsibility_type_id, ri)
