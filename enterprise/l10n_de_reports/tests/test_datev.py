from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDatevCSV(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('de_skr03')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a = cls.env['res.partner'].create({'name': 'Res Partner A'})
        cls.partner_b = cls.env['res.partner'].create({'name': 'Res Partner B'})

    def test_datev_partner_fields(self):
        """Test fields l10n_de_datev_identifier and l10n_de_datev_identifier_customer are unique per company
        """
        self.partner_a.l10n_de_datev_identifier = 120
        self.partner_a.l10n_de_datev_identifier = 123
        with self.assertRaises(ValidationError, msg='You have already defined a partner with the same Datev identifier. '):
            self.partner_b.l10n_de_datev_identifier = 123
        self.partner_b.l10n_de_datev_identifier = 120

        self.partner_a.l10n_de_datev_identifier_customer = 123
        with self.assertRaises(ValidationError, msg='You have already defined a partner with the same Datev Customer identifier'):
            self.partner_b.l10n_de_datev_identifier_customer = 123
        self.partner_b.l10n_de_datev_identifier_customer = 120

        # Fields must be unique even if partner is archived.
        self.partner_a.active = False

        with self.assertRaises(ValidationError, msg='A ValidationError should be raised when assigning a duplicate Datev identifier.'):
            self.partner_b.l10n_de_datev_identifier = 123

        with self.assertRaises(ValidationError, msg='A ValidationError should be raised when assigning a duplicate Datev Customer identifier.'):
            self.partner_b.l10n_de_datev_identifier_customer = 123

        company_b = self.env['res.company'].create({
            'name': 'Company B',
        })
        self.env.user.company_id = company_b
        self.partner_a.l10n_de_datev_identifier = 123
        self.partner_a.l10n_de_datev_identifier_customer = 123
