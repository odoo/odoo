import io

from odoo import Command
from odoo.tests import tagged
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

from odoo.addons.l10n_sa_edi.tests.common import TestSaEdiCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nSaInvoice(TestSaEdiCommon):
    def test_invoice_section_lines_rendering(self):
        invoice = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_sa_simplified.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "tax_ids": self.tax_15.ids,
                                "price_unit": 100.0,
                            }
                        ),
                        Command.create(
                            {
                                "display_type": "line_section",
                                "name": "section line",
                            }
                        ),
                        Command.create(
                            {
                                "product_id": self.product_b.id,
                                "tax_ids": self.tax_15.ids,
                                "price_unit": 200.0,
                            }
                        ),
                    ],
                }
            ]
        )
        invoice.action_post()
        html = self.env["ir.actions.report"]._render_qweb_html(
            "account.report_invoice_with_payments", invoice.ids
        )[0]
        self.assertTrue(html)

    def test_the_invoice_report_embeds_the_zatca_xml_as_pdfa(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_sa_simplified.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "tax_ids": self.tax_15.ids,
                            "price_unit": 100.0,
                        }
                    )
                ],
            }
        )
        attachment = self.env["ir.attachment"].create(
            {"name": "zatca.xml", "raw": b"<Invoice/>"}
        )
        edi_document = self.env["account.edi.document"].create(
            {
                "move_id": invoice.id,
                "edi_format_id": self.edi_format.id,
                "attachment_id": attachment.id,
                "state": "sent",
            }
        )

        source = OdooPdfFileWriter()
        source.add_blank_page(100, 100)
        source_buffer = io.BytesIO()
        source.write(source_buffer)
        writer = OdooPdfFileWriter()
        writer.clone_reader_document_root(
            OdooPdfFileReader(io.BytesIO(source_buffer.getvalue()), strict=False)
        )
        self.assertFalse(writer.is_pdfa)

        self.edi_format._prepare_invoice_report(writer, edi_document)

        output = io.BytesIO()
        writer.write(output)
        reader = OdooPdfFileReader(io.BytesIO(output.getvalue()), strict=False)
        self.assertEqual(list(reader.get_attachments()), [("zatca.xml", b"<Invoice/>")])
        reread = OdooPdfFileWriter()
        reread.clone_reader_document_root(reader)
        self.assertTrue(reread.is_pdfa, "the report does not declare PDF/A")
