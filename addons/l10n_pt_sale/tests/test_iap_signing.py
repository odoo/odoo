import os
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.l10n_pt_certification.tests.common import AT_DEMO_PUBLIC_KEY, REAL_SIGNING
from odoo.addons.l10n_pt_certification.tests.test_iap_signing import IAP_TEST_ENDPOINT
from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils
from odoo.addons.l10n_pt_sale.tests.common import TestL10nPtSaleCommon


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestL10nPtSaleIapSigning(TestL10nPtSaleCommon):
    """
    Smoke test of quotations and sales orders against the signing service itself: the IAP's test
    signer, or the endpoint given by the `L10N_PT_IAP_ENDPOINT` environment variable (e.g. a local
    stand-in).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for name, function in REAL_SIGNING.items():
            cls.startClassPatcher(patch.object(pt_hash_utils, name, function))
        endpoint = os.environ.get('L10N_PT_IAP_ENDPOINT', IAP_TEST_ENDPOINT)
        cls.env['ir.config_parameter'].sudo().set_param('l10n_pt.iap_endpoint', endpoint)

    def test_sign_chain_and_verify(self):
        """
        A quotation issued alone, two together, and the sales order of one, are signed in their chains,
        which the service's keys verify.
        """
        first = self.issue(self.make_order())
        batch = self.issue(self.make_order() + self.make_order())
        quotations = first + batch
        sales_order = self.issue(self.confirm(first))
        for order in quotations + sales_order:
            self.assertRegex(order.l10n_pt_inalterable_hash, r'^\$\d+\$[A-Za-z0-9+/=]{100,}$')
        self.assertChainVerified(quotations + sales_order)
        self.tamper(batch[0], 'amount_total', 1.0)
        self.assertEqual(self.integrity_results(quotations)[self.series_or]['status'], 'corrupted')

    def test_at_sample_orders(self):
        """
        The working documents of the AT's demo SAF-T (saft_idemo599999999.xml), rebuilt as quotations
        and signed by a service holding the AT's demo key (the IAP's test signer), get the signatures
        the AT published for them, byte for byte (Despacho 8632/2014 2.1).
        """
        def bare(key):
            return ''.join(key.split())

        if bare(AT_DEMO_PUBLIC_KEY) not in map(bare, REAL_SIGNING['get_public_keys'](self.env).values()):
            self.skipTest("The signing service does not sign with the AT's demo key")
        with self.at_sample_orders() as signatures:
            for quotation, signature in signatures.items():
                self.assertEqual(quotation.l10n_pt_inalterable_hash.split('$')[2], signature, quotation.name)
            self.assertChainVerified(self.env['sale.order'].concat(*signatures))
