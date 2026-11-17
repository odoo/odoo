from odoo import Command
from odoo.addons.account_edi_ubl_cii.tests.common import TestCiiNlciusCommon, TestUblCiiBECommon

from odoo.tests import tagged

from lxml import etree

NS_MAP = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
}


@tagged('post_install_l10n', 'post_install', '-at_install', *TestCiiNlciusCommon.extra_tags)
class TestUblExportNlciusSelfInvoice(TestCiiNlciusCommon, TestUblCiiBECommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.self_billing_journal = cls.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
        })
        cls.self_billing_sale_journal = cls.env['account.journal'].create({
            'name': 'Self Billing Sale',
            'code': 'SBS',
            'type': 'sale',
            'is_self_billing': True,
        })

    def test_nlcius_self_billing_xml(self):
        self.partner_nl.invoice_edi_format = 'nlcius'
        for move_type, type_code, reimported_move_type in [
            ('in_invoice', '389', 'out_invoice'),
            ('in_refund', '261', 'out_refund'),
        ]:
            with self.subTest(move_type=move_type, type_code=type_code):
                invoice = self._create_invoice_one_line(
                    move_type=move_type,
                    journal_id=self.self_billing_journal.id,
                    product_id=self.product_a,
                    partner_id=self.partner_nl,
                    tax_ids=self.tax_purchase_a,
                    post=True,
                )

                self._generate_invoice_ubl_file(invoice)
                file = invoice.ubl_cii_xml_id.raw
                root = etree.fromstring(file)
                self.assertEqual(
                    root.xpath("cbc:CustomizationID/text()", namespaces=NS_MAP)[0],
                    'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0',
                )
                self.assertEqual(
                    root.xpath("cbc:ProfileID/text()", namespaces=NS_MAP)[0],
                    'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0',
                )
                move_type_node = 'cbc:InvoiceTypeCode/text()' if move_type == 'in_invoice' else 'cbc:CreditNoteTypeCode/text()'
                self.assertEqual(root.xpath(move_type_node, namespaces=NS_MAP)[0], type_code)

                attachment = self.env['ir.attachment'].create({
                    'name': f'{move_type}.xml',
                    'mimetype': 'application/xml',
                    'raw': file,
                })
                proxy_user = self.env['account_edi_proxy_client.user'].new({
                    'company_id': self.env.company.id,
                    'proxy_type': 'peppol',
                })
                reimported_move = proxy_user._peppol_import_invoice(attachment, None, 'done', f'djjdjdj-{move_type}')
                self.assertRecordValues(reimported_move, [{
                    'move_type': reimported_move_type,
                    'journal_id': self.self_billing_sale_journal.id,
                }])
