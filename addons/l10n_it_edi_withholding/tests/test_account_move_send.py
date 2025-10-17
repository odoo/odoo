from odoo.tests import tagged
from odoo.addons.l10n_it_edi.tests.test_account_move_send import TestItAccountMoveSend


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItWithholdingAccountMoveSend(TestItAccountMoveSend):

    def test_enasarco_no_warnings(self):
        self.proxy_user.edi_mode = 'demo'
        ref = self.env['account.chart.template'].with_company(self.proxy_user.company_id).ref
        self.partner_a.write({
            "l10n_it_codice_fiscale": "PERTLELPALQZRTSN",
            'country_id': self.env.ref('base.it').id,
            'street': 'Test street',
            'city': 'Test town',
            'zip': '32121',
        })
        invoice = self.init_invoice(partners=self.partner_a, taxes=ref('22v') | ref('23vwo') | ref('enasarcov'))
        wizard = self.create_send_and_print(invoice, sending_methods=['l10n_it_edi'])
        self.assertFalse(wizard.alerts)
