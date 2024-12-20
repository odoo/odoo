import io

from odoo import models
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _embed_edi_attachments(self, order, collected_streams):
        """
        Adds EDI builder attachments to the given PDF writer.

        :param order: The order object.
        :param collected_streams: Dictionary of collected PDF streams by order ID.
        :return: Updated collected_streams with EDI attachments embedded.
        """

        builders = order._get_edi_builders()

        if len(builders) == 0:
            return collected_streams

        # Read pdf content.
        pdf_stream = collected_streams[order.id]['stream']
        pdf_content = pdf_stream.getvalue()
        reader_buffer = io.BytesIO(pdf_content)
        reader = OdooPdfFileReader(reader_buffer, strict=False)
        writer = OdooPdfFileWriter()
        writer.cloneReaderDocumentRoot(reader)

        # Generate and attach EDI documents from builders
        for builder in builders:
            xml_content = builder._export_order(order)

            writer.addAttachment(
                builder._export_order_filename(order),
                xml_content,
                subtype='text/xml'
            )

        # Replace the current content.
        pdf_stream.close()
        new_pdf_stream = io.BytesIO()
        writer.write(new_pdf_stream)
        collected_streams[order.id]['stream'] = new_pdf_stream
        return collected_streams
