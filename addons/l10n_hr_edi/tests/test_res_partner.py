from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.l10n_hr_edi.tests.test_hr_edi_common import TestL10nHrEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nHrEdiPartner(TestL10nHrEdiCommon):

    def test_create_partner_with_mojeracun_info(self):
        """Check that a new contact without a country can be saved with MojEracun information filled in."""
        with Form(self.env['res.partner']) as partner_form:
            partner_form.invoice_sending_method = 'mojeracun'
            partner_form.invoice_edi_format = 'ubl_hr'
            partner_form.name = 'New MojEracun partner'
        self.assertRecordValues(partner_form.record, [{
            'invoice_sending_method': 'mojeracun',
            'invoice_edi_format': 'ubl_hr',
        }])

        with self.assertRaisesRegex(ValidationError, 'only the Croatian UBL format is supported'):
            self.env['res.partner'].create({
                'name': 'New MojEracun partner',
                'invoice_sending_method': 'mojeracun',
                'invoice_edi_format': 'ubl_bis3',
            })
