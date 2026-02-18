import base64
from unittest.mock import patch

from odoo.fields import Command
from odoo.tests.common import HttpCase, tagged

from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDownloadDocs(HttpCase, TestItEdi):

    def test_download_invoice_documents_fatturapa(self):
        invoice = self._create_invoice(
            partner_id=self.italian_partner_a.id,
            company_id=self.company.id,
            invoice_line_ids=[Command.create({'price_unit': 100, 'tax_ids': [Command.set(self.default_tax.ids)]})],
            post=True,
        )
        with patch('odoo.addons.account.models.account_move_send.AccountMoveSend._get_default_extra_edis', return_value=[]):
            self.env['account.move.send']._generate_and_send_invoices(invoice)
        url = f'/account/download_invoice_documents/{invoice.id}/fatturapa'
        self.authenticate(self.env.user.login, self.env.user.login)
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content, base64.b64decode(invoice.l10n_it_edi_attachment_file))
