from unittest.mock import patch, MagicMock

from odoo import tools
from odoo.tests import tagged
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyClientUser

def patch_proxy_user(func):
    @patch.object(AccountEdiProxyClientUser, '_make_request', MagicMock(spec=AccountEdiProxyClientUser._make_request))
    @patch.object(AccountEdiProxyClientUser, '_decrypt_data', MagicMock(spec=AccountEdiProxyClientUser._decrypt_data))
    @patch.object(AccountEdiProxyClientUser, '_get_demo_state', MagicMock(spec=AccountEdiProxyClientUser._get_demo_state))
    def patched(self, *args, **kwargs):
        return func(self, *args, **kwargs)
    return patched

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdi(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_it.l10n_it_chart_template_generic', edi_format_ref="l10n_it_edi.edi_fatturaPA"):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        # Company data ------
        cls.company = cls.company_data_2['company']
        cls.company.l10n_it_codice_fiscale = '01234560157'
        cls.company.partner_id.l10n_it_pa_index = "0803HR0"
        cls.company.vat = 'IT01234560157'

        cls.test_bank = cls.env['res.partner.bank'].with_company(cls.company).create({
                'partner_id': cls.company.partner_id.id,
                'acc_number': 'IT1212341234123412341234123',
                'bank_name': 'BIG BANK',
                'bank_bic': 'BIGGBANQ',
        })

        cls.company.l10n_it_tax_system = "RF01"
        cls.company.street = "1234 Test Street"
        cls.company.zip = "12345"
        cls.company.city = "Prova"
        cls.company.country_id = cls.env.ref('base.it')

        # We create this because we are unable to post without a proxy user existing
        cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
            'id_client': 'l10n_it_edi_test',
            'company_id': cls.company.id,
            'edi_format_id': cls.edi_format.id,
            'edi_identification': 'l10n_it_edi_test',
            'private_key': 'l10n_it_edi_test',
        })

        cls.standard_line = {
            'name': 'standard_line',
            'quantity': 1,
            'price_unit': 800.40,
            'tax_ids': [(6, 0, [cls.company.account_sale_tax_id.id])]
        }


    @classmethod
    def _get_test_file_content(cls, filename):
        """ Get the content of a test file inside this module """
        path = 'l10n_it_edi/tests/expected_xmls/' + filename
        with tools.file_open(path, mode='rb') as test_file:
            return test_file.read()
