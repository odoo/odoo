from odoo.exceptions import ValidationError, UserError
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

        # Try to change responsibility type for a normal partner, should succeed
        self.res_partner_adhoc.l10n_ar_afip_responsibility_type_id = new_responsibility
        self.assertEqual(self.res_partner_adhoc.l10n_ar_afip_responsibility_type_id, new_responsibility)
