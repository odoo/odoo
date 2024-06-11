# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestImportVendorBill(AccountTestInvoicingCommon):

    def test_retrieve_partner(self):

        def retrieve_partner(vat, import_vat):
            self.partner_a.with_context(no_vat_validation=True).vat = vat
            return self.env['res.partner']._retrieve_partner(vat=import_vat)

        self.assertEqual(self.partner_a, retrieve_partner('BE0477472701', 'BE0477472701'))
        self.assertEqual(self.partner_a, retrieve_partner('BE0477472701', '0477472701'))
        self.assertEqual(self.partner_a, retrieve_partner('BE0477472701', '477472701'))
        self.assertEqual(self.partner_a, retrieve_partner('0477472701', 'BE0477472701'))
        self.assertEqual(self.partner_a, retrieve_partner('477472701', 'BE0477472701'))
        self.assertEqual(self.env['res.partner'], retrieve_partner('DE0477472701', 'BE0477472701'))
        self.assertEqual(self.partner_a, retrieve_partner('CHE-107.787.577 IVA', 'CHE-107.787.577 IVA'))  # note that base_vat forces the space
