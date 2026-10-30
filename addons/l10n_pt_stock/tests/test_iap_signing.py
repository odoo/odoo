import os
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.l10n_pt_certification.tests.common import AT_DEMO_PUBLIC_KEY, REAL_SIGNING
from odoo.addons.l10n_pt_certification.tests.test_iap_signing import IAP_TEST_ENDPOINT
from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils
from odoo.addons.l10n_pt_stock.tests.common import TestL10nPtStockCommon


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestL10nPtStockIapSigning(TestL10nPtStockCommon):
    """
    Smoke test of transport documents against the signing service itself: the IAP's test signer, or
    the endpoint given by the `L10N_PT_IAP_ENDPOINT` environment variable (e.g. a local stand-in).
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
        A delivery validated alone, two together and a return to a supplier are signed in their chains,
        which the service's keys verify; a tampered date is detected.
        """
        first = self.deliver()
        batch = self.validate(self.make_transfer() + self.make_transfer())
        receipt = self.deliver(self.in_type, partner=self.partner_supplier)
        supplier_return = self.validate(self.make_return(receipt))
        pickings = first + batch + supplier_return
        for picking in pickings:
            self.assertRegex(picking.l10n_pt_inalterable_hash, r'^\$\d+\$[A-Za-z0-9+/=]{100,}$')
        self.assertChainVerified(pickings)
        self.tamper(batch[0], 'date_done', '2026-06-20 10:00:00')
        self.assertEqual(self.integrity_results(pickings)[self.series_gt]['status'], 'corrupted')

    def test_at_sample_transfers(self):
        """
        The transport guides of the AT's demo SAF-T (saft_idemo599999999.xml), rebuilt as deliveries and
        signed by a service holding the AT's demo key (the IAP's test signer), get the signatures the AT
        published for them, byte for byte (Despacho 8632/2014 2.1).
        """
        def bare(key):
            return ''.join(key.split())

        if bare(AT_DEMO_PUBLIC_KEY) not in map(bare, REAL_SIGNING['get_public_keys'](self.env).values()):
            self.skipTest("The signing service does not sign with the AT's demo key")
        with self.at_sample_transfers() as signatures:
            for picking, signature in signatures.items():
                self.assertEqual(picking.l10n_pt_inalterable_hash.split('$')[2], signature, picking.name)
            self.assertChainVerified(self.env['stock.picking'].concat(*signatures))
