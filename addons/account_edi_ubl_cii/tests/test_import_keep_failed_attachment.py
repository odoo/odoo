import io

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import pdf
from odoo.tools.misc import file_open


BROKEN_CII = b"""<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
                          xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
  <rsm:ExchangedDocument>
    <ram:ID>FH260800671901</ram:ID>
    <ram:TypeCode>380</ram:TypeCode>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:GrandTotalAmount>NOT_A_NUMBER</ram:GrandTotalAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>
"""


def _broken_facturx_pdf():
    with file_open('base/tests/minimal.pdf', 'rb') as pdf_file:
        reader = pdf.OdooPdfFileReader(io.BytesIO(pdf_file.read()))
    writer = pdf.OdooPdfFileWriter()
    writer.cloneReaderDocumentRoot(reader)
    writer.addAttachment('factur-x.xml', BROKEN_CII, subtype='text/xml')
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestImportKeepFailedAttachment(AccountTestInvoicingCommon):

    def _purchase_move(self):
        return self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self.company_data['default_journal_purchase'].id,
        })

    def test_failed_cii_import_keeps_xml_on_mail_alias(self):
        attachment = self.env['ir.attachment'].create({
            'name': 'factur-x.xml',
            'raw': BROKEN_CII,
            'mimetype': 'application/xml',
        })
        move = self._purchase_move()
        move.with_context(from_alias=True)._check_and_decode_attachment(attachment)
        self.assertTrue(attachment.exists())
        self.assertEqual(attachment.res_id, move.id)
        error_msgs = move.message_ids.filtered(lambda msg: 'Error importing attachment' in (msg.body or ''))
        self.assertTrue(error_msgs)
        self.assertTrue(error_msgs[0].attachment_ids & attachment)

    def test_failed_facturx_pdf_keeps_extracted_xml(self):
        pdf_attachment = self.env['ir.attachment'].create({
            'name': 'FH260800671901.pdf',
            'raw': _broken_facturx_pdf(),
            'mimetype': 'application/pdf',
        })
        move = self._purchase_move()
        move.with_context(from_alias=True)._check_and_decode_attachment(pdf_attachment)
        self.assertTrue(pdf_attachment.exists())
        xml_atts = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', move.id),
            ('name', '=', 'factur-x.xml'),
        ])
        self.assertTrue(xml_atts)
        error_msgs = move.message_ids.filtered(lambda msg: 'Error importing attachment' in (msg.body or ''))
        self.assertTrue(error_msgs)
        self.assertTrue(error_msgs[0].attachment_ids & xml_atts)
