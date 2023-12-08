# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.exceptions import UserError

import io
from PyPDF2 import PdfFileWriter, PdfFileReader
from PIL import Image, ImageFile
from collections import OrderedDict

# Allow truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True


class DuplicateKeyDict:
    def __init__(self) -> None:
        self._key_count = 0
        self._items = OrderedDict()

    def insert(self, key, value):
        cur_key_id = self._key_count
        self._items[f'{key}|{cur_key_id}'] = (key, value)
        self._key_count += 1
        return cur_key_id

    def items(self, include_key_id=False):
        for internal_key, (key, val) in self._items.items():
            _, key_id = internal_key.split('|')
            key_id = int(key_id)
            if include_key_id:
                yield (key, key_id, val)
            else:
                yield (key, val)

    def values(self):
        for (_, val) in self._items.values():
            yield val

    def __getitem__(self, key_tuple):
        key, key_id = key_tuple
        internal_key = f'{key}|{key_id}'
        return self._items[internal_key][1]


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def _get_rendering_context(self, report, docids, data):
        data = super()._get_rendering_context(report, docids, data)
        if report.report_name == 'stock.report_reception_report_label' and not docids:
            docids = data['docids']
            docs = self.env[report.model].browse(docids)
            data.update({
                'doc_ids': docids,
                'docs': docs,
            })
        return data

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        if self._get_report(report_ref).report_name != 'stock.report_lot_label':
            return super()._render_qweb_pdf_prepare_streams(report_ref, data, res_ids=res_ids)
        
        if not data:
            data = {}
        data.setdefault('report_type', 'pdf')

        # access the report details with sudo() but evaluation context as current user
        report_sudo = self._get_report(report_ref)

        collected_streams = DuplicateKeyDict()

        # Fetch the existing attachments from the database for later use.
        # Reload the stream from the attachment in case of 'attachment_use'.
        if res_ids:
            records = self.env[report_sudo.model].browse(res_ids)
            for record in records:
                stream = None
                attachment = None
                if report_sudo.attachment and not self._context.get("report_pdf_no_attachment"):
                    attachment = report_sudo.retrieve_attachment(record)

                    # Extract the stream from the attachment.
                    if attachment and report_sudo.attachment_use:
                        stream = io.BytesIO(attachment.raw)

                        # Ensure the stream can be saved in Image.
                        if attachment.mimetype.startswith('image'):
                            img = Image.open(stream)
                            new_stream = io.BytesIO()
                            img.convert("RGB").save(new_stream, format="pdf")
                            stream.close()
                            stream = new_stream

                collected_streams.insert(record.id, {
                    'stream': stream,
                    'attachment': attachment,
                })

        # Call 'wkhtmltopdf' to generate the missing streams.
        res_ids_wo_stream = [res_id for res_id, stream_data in collected_streams.items(
        ) if not stream_data['stream']]
        key_ids_wo_stream = [key_id for _, key_id, stream_data in collected_streams.items(
            include_key_id=True) if not stream_data['stream']]
        is_whtmltopdf_needed = not res_ids or res_ids_wo_stream

        if is_whtmltopdf_needed:

            if self.get_wkhtmltopdf_state() == 'install':
                # wkhtmltopdf is not installed
                # the call should be catched before (cf /report/check_wkhtmltopdf) but
                # if get_pdf is called manually (email template), the check could be
                # bypassed
                raise UserError(
                    _("Unable to find Wkhtmltopdf on this system. The PDF can not be created."))

            # Disable the debug mode in the PDF rendering in order to not split the assets bundle
            # into separated files to load. This is done because of an issue in wkhtmltopdf
            # failing to load the CSS/Javascript resources in time.
            # Without this, the header/footer of the reports randomly disappear
            # because the resources files are not loaded in time.
            # https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2083
            additional_context = {'debug': False}

            html = self.with_context(
                **additional_context)._render_qweb_html(report_ref, res_ids_wo_stream, data=data)[0]

            bodies, html_ids, header, footer, specific_paperformat_args = self.with_context(
                **additional_context)._prepare_html(html, report_model=report_sudo.model)

            if report_sudo.attachment and sorted(res_ids_wo_stream) != sorted(html_ids):
                raise UserError(_(
                    "The report's template %r is wrong, please contact your administrator. \n\n"
                    "Can not separate file to save as attachment because the report's template does not contains the"
                    " attributes 'data-oe-model' and 'data-oe-id' on the div with 'article' classname.",
                    self.name,
                ))

            pdf_content = self._run_wkhtmltopdf(
                bodies,
                report_ref=report_ref,
                header=header,
                footer=footer,
                landscape=self._context.get('landscape'),
                specific_paperformat_args=specific_paperformat_args,
                set_viewport_size=self._context.get('set_viewport_size'),
            )
            pdf_content_stream = io.BytesIO(pdf_content)

            # Printing a PDF report without any records. The content could be returned directly.
            if not res_ids:
                collected_streams = DuplicateKeyDict()
                collected_streams.insert(False, {
                    'stream': pdf_content_stream,
                    'attachment': None
                })
                return collected_streams

            # Split the pdf for each record using the PDF outlines.

            # Only one record: append the whole PDF.
            if len(res_ids_wo_stream) == 1:
                collected_streams[(res_ids_wo_stream[0], 0)]['stream'] = pdf_content_stream
                return collected_streams

            # In case of multiple docs, we need to split the pdf according the records.
            # In the simplest case of 1 res_id == 1 page, we use the PDFReader to print the
            # pages one by one.
            html_ids_wo_none = [x for x in html_ids if x]
            reader = PdfFileReader(pdf_content_stream)
            if reader.numPages == len(res_ids_wo_stream):
                for i in range(reader.numPages):
                    attachment_writer = PdfFileWriter()
                    attachment_writer.addPage(reader.getPage(i))
                    stream = io.BytesIO()
                    attachment_writer.write(stream)
                    collected_streams[(res_ids[i], i)]['stream'] = stream
                return collected_streams

            # In cases where the number of res_ids != the number of pages,
            # we split the pdf based on top outlines computed by wkhtmltopdf.
            # An outline is a <h?> html tag found on the document. To retrieve this table,
            # we look on the pdf structure using pypdf to compute the outlines_pages from
            # the top level heading in /Outlines.
            if len(res_ids_wo_stream) > 1 and set(res_ids_wo_stream) == set(html_ids_wo_none):
                root = reader.trailer['/Root']
                has_valid_outlines = '/Outlines' in root and '/First' in root['/Outlines']
                if not has_valid_outlines:
                    collected_streams = DuplicateKeyDict()
                    collected_streams.insert(False, {
                        'report_action': self,
                        'stream': pdf_content_stream,
                        'attachment': None,
                    })
                    return collected_streams

                outlines_pages = []
                node = root['/Outlines']['/First']
                while True:
                    outlines_pages.append(root['/Dests'][node['/Dest']][0])
                    if '/Next' not in node:
                        break
                    node = node['/Next']
                outlines_pages = sorted(set(outlines_pages))

                # The number of outlines must be equal to the number of records to be able to split the document.
                has_same_number_of_outlines = len(
                    outlines_pages) == len(res_ids)

                # There should be a top-level heading on first page
                has_top_level_heading = outlines_pages[0] == 0

                if has_same_number_of_outlines and has_top_level_heading:
                    # Split the PDF according to outlines.
                    for i, num in enumerate(outlines_pages):
                        to = outlines_pages[i + 1] if i + \
                            1 < len(outlines_pages) else reader.numPages
                        attachment_writer = PdfFileWriter()
                        for j in range(num, to):
                            attachment_writer.addPage(reader.getPage(j))
                        stream = io.BytesIO()
                        attachment_writer.write(stream)
                        collected_streams[(res_ids[i], i)]['stream'] = stream

                    return collected_streams

            collected_streams.insert(False, {
                'stream': pdf_content_stream, 'attachment': None})

        return collected_streams
