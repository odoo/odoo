from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import Form, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestStandardFlows(L10nInTestInvoicingCommon):
    """ Tests for standard flows not related to PoS but that can be impacted by it """

    def test_open_payment_register_with_upi_qr_method(self):
        self.env.company.l10n_in_upi_id = 12345
        self.env['res.partner.bank'].create({
            'account_number': '0144748555',
            'partner_id': self.partner_a.id,
            'allow_out_payment': True,
        })
        bill = self._create_invoice('in_invoice', post=True)

        # the wizard should be created without error
        Form(self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=bill.ids))
