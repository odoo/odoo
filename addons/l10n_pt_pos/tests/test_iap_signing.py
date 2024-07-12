from odoo.tests import tagged

from odoo.addons.l10n_pt_certification.tests.common import L10nPtRealSigningMixin
from odoo.addons.l10n_pt_pos.tests.common import TestL10nPtPosCommon


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestL10nPtPosIapSigning(L10nPtRealSigningMixin, TestL10nPtPosCommon):
    """
    Smoke test of PoS sales against the signing service itself: the IAP's test signer, or the
    endpoint given by the `L10N_PT_IAP_ENDPOINT` environment variable (e.g. a local stand-in).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.session = cls.open_session()

    def test_sign_chain_and_verify(self):
        """
        Two anonymous sales (FS), a sale to a customer (FR) and a refund (NC) are signed as they are
        synced, in their chains, which the service's keys verify.
        """
        simplified = self.sell() + self.sell()
        invoice_receipt = self.sell(partner=self.partner_pt)
        refund = self.refund(simplified[0])
        invoices = (simplified + invoice_receipt + refund).account_move
        for invoice in invoices:
            self.assertRegex(invoice.inalterable_hash, r'^\$\d+\$[A-Za-z0-9+/=]{100,}$')
        self.assertChainVerified(invoices)
        self.tamper(simplified[1].account_move, 'amount_total_signed', 1.0)
        self.assertEqual(self.integrity_results(invoices)[self.series_fs]['status'], 'corrupted')
