from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from . import common


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestResPartner(common.TestArCommon):

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
