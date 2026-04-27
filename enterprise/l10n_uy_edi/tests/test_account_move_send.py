from odoo.addons.account.tests.common import AccountTestInvoicingCommon, AccountTestMockOnlineSyncCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountMoveSend(TestAccountMoveSendCommon, AccountTestMockOnlineSyncCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('uy')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'name': 'UY Test Company',
            'vat': '218296790015',
            'state_id': cls.env.ref('base.state_uy_10').id,
            'city': 'Montevideo',
            'street': 'Calle Falsa 123',
        })
        cls.tax_0 = cls.env['account.tax'].create({
            'name': '0% Exempt',
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': 0,
            'l10n_uy_tax_category': 'vat',
        })

    def test_download_with_existing_cfe(self):
        """ Test that we can download attachment if CFE document has been generated"""
        invoice = self.init_invoice('out_invoice', products=[self.product_a], taxes=[self.tax_0], post=False)
        invoice.write({
            'invoice_incoterm_id': self.env.ref('account.incoterm_EXW').id,
            'l10n_uy_edi_cfe_sale_mode': '1',
            'l10n_uy_edi_cfe_transport_route': '1',
        })
        invoice.action_post()
        wizard = self.create_send_and_print(invoice, sending_methods=['manual'], extra_edis=['uy_cfe'])
        url = wizard.action_send_and_print()['url']
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
