# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import unquote

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon

from .test_l10n_id_ebupot import TestEBupot


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestEBupotDownload(TestEBupot, AccountTestInvoicingHttpCommon):

    def test_ebupot_download_one_document(self):
        """ Ensure that downloading a payment yields an xml file named (payment_month)_ebupot_(index).xml """

        payment = self._pay_bill()

        # Download
        action = payment.download_ebupot()

        # Verify the result of download
        self.authenticate(self.env.user.login, self.env.user.login)
        result = self.url_open(url=action['url'])
        self.assertRegex(
            unquote(result.headers['Content-Disposition'].split("filename*=UTF-8''")[-1]),
            r"ebupot_.*\.xml"
        )

    def test_ebupot_download_multiple(self):
        """ Ensure that several files are zipped together, in an zip named after the document type. """
        payment_1 = self._pay_bill(ref='BILL1')
        payment_2 = self._pay_bill(ref='BILL2', invoice_date='2026-05-01', payment_date='2026-05-01')
        payment_1.download_ebupot()
        payment_2.download_ebupot()

        documents = (payment_1 | payment_2).l10n_id_coretax_document
        self.assertEqual(len(documents), 2)

        action = documents.action_download()
        self.authenticate(self.env.user.login, self.env.user.login)
        result = self.url_open(url=action['url'])
        self.assertRegex(result.headers['Content-Disposition'], r"ebupot\.zip")
