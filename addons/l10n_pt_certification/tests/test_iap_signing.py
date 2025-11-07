import os
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.l10n_pt_certification.tests.common import (
    AT_DEMO_PUBLIC_KEY,
    REAL_SIGNING,
    TestL10nPtCommon,
)
from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils

# The IAP's test signer, which signs with the AT's demo key.
IAP_TEST_ENDPOINT = 'https://iap-services-test.odoo.com/api/l10n_pt/1'


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestL10nPtIapSigning(TestL10nPtCommon):
    """
    Smoke test against the signing service itself: the IAP's test signer, or the endpoint given by
    the `L10N_PT_IAP_ENDPOINT` environment variable (e.g. a local stand-in).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for name, function in REAL_SIGNING.items():
            cls.startClassPatcher(patch.object(pt_hash_utils, name, function))
        endpoint = os.environ.get('L10N_PT_IAP_ENDPOINT', IAP_TEST_ENDPOINT)
        cls.env['ir.config_parameter'].sudo().set_param('l10n_pt.iap_endpoint', endpoint)

    def test_sign_chain_and_verify(self):
        """Two invoices issued apart, and two together, are signed in one chain the service's keys verify."""
        first = self.issue(self.post(self.make_invoice()))
        batch = self.issue(self.post(self.make_invoice() + self.make_invoice()))
        invoices = first + batch
        for invoice in invoices:
            self.assertRegex(invoice.inalterable_hash, r'^\$\d+\$[A-Za-z0-9+/=]{100,}$')
        self.assertChainVerified(invoices)
        self.tamper(batch[0], 'amount_total_signed', 1.0)
        self.assertEqual(self.integrity_results(invoices)[self.series_ft]['status'], 'corrupted')

    def test_at_sample_documents(self):
        """
        The documents of the AT's demo SAF-T (saft_idemo599999999.xml), rebuilt as invoices and
        signed by a service holding the AT's demo key (the IAP's test signer), get the signatures the
        AT published for them, byte for byte: the values sent, the message the service builds and
        the chaining are the AT's (Despacho 8632/2014 2.1).
        """
        def bare(key):
            return ''.join(key.split())

        if bare(AT_DEMO_PUBLIC_KEY) not in map(bare, REAL_SIGNING['get_public_keys'](self.env).values()):
            self.skipTest("The signing service does not sign with the AT's demo key")
        with self.at_sample_documents() as signatures:
            for invoice, signature in signatures.items():
                self.assertEqual(invoice.inalterable_hash.split('$')[2], signature, invoice.name)
            self.assertChainVerified(self.env['account.move'].concat(*signatures))
