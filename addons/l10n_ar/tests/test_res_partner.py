from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import tagged
from . import common


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(common.TestArCommon):

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
        # Note this last case is poorly handled in Odoo and should be fixed in future versions.
        # One could expect to have is_company False for this case, but the visibility of l10n_latam_identifier_type_id
        # in a multi company setup make it not so straightforward.
        # For now, the identification_type is ignored for such partners.
        self.assertTrue(foreign_person.is_company)

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

    def test_l10n_ar_cuit_number(self):
        with self.assertRaisesRegex(ValidationError, 'Invalid length for "CUIT"'):
            self.partner_ri.vat = "BE0477472701"

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
