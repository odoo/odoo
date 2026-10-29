# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io

from PIL import Image

from odoo import api, fields, models

# Width of the paper of the ePOS printers, in dots.
EPOS_PAPER_WIDTH = 576
MM_PER_INCH = 25.4
CSS_PIXELS_PER_INCH = 96


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    printer_ids = fields.Many2many(
        'printer.printer', 'printer_printer_ir_actions_report_rel', 'report_id', 'printer_id',
        string="Printers",
        help="When the report is printed, it is sent to these printers instead of being downloaded.")

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {'printer_ids'}

    def report_action(self, docids, data=None, config=True):
        action = super().report_action(docids, data=data, config=config)
        if action.get('type') == 'ir.actions.report':
            action['printer_ids'] = self.sudo().printer_ids.ids
        return action

    @api.model
    def _render_printer_documents(self, report_ref, printers, res_ids, data=None):
        """ Render a report for printers.

        Each kind of printer gets its own documents, rendered by the method
        ``_render_printer_documents_<kind>``, that a module adding a kind of
        printer implements.

        :param report_ref: the report, as accepted by :meth:`_get_report`
        :param printers: the ``printer.printer`` records to print to
        :param list[int] res_ids: the ids of the records to print
        :param dict data: the data of the report action
        :return: the documents to send to each kind of printer, in order
        :rtype: dict[str, list]
        """
        report_sudo = self._get_report(report_ref)
        return {
            kind: getattr(self, f'_render_printer_documents_{kind}')(report_sudo, res_ids, data)
            for kind in set(printers.mapped('kind'))
        }

    @api.model
    def _render_printer_documents_zpl(self, report_sudo, res_ids, data=None):
        """ ZPL printers print the text reports holding ZPL code, sent as is. """
        if report_sudo.report_type != 'qweb-text' or 'ZPL' not in report_sudo.with_context(lang='en_US').name:
            return []
        return [self._render_qweb_text(report_sudo, res_ids, data=data)[0].decode()]

    @api.model
    def _render_printer_documents_epos(self, report_sudo, res_ids, data=None):
        """ ePOS printers print the PDF reports, as one image per page. """
        if not report_sudo.report_type.startswith('qweb-pdf'):
            return []
        data = dict(data or {}, report_type='pdf', debug=False)
        # Render the pages the way the PDF engine does: each page is a complete
        # HTML document, with a <base> so that its relative links (assets,
        # barcode images, ...) resolve when the image engine renders it.
        html = self.with_context(debug=False)._render_qweb_html(report_sudo, res_ids, data=data)[0]
        bodies = report_sudo.with_context(debug=False)._prepare_html(html, report_model=report_sudo.model)[0]
        paperformat = report_sudo.get_paperformat()
        width, height = (
            round(size / MM_PER_INCH * CSS_PIXELS_PER_INCH)
            for size in (paperformat.print_page_width, paperformat.print_page_height)
        )
        images = self._run_image_engine('wkhtmltopdf', bodies, width, height, image_format='png')
        return [self._convert_image_to_epos_document(image) for image in images if image]

    @api.model
    def _convert_image_to_epos_document(self, image):
        """ Turn an image into a raster an ePOS printer can print.

        The image is turned to portrait, scaled to the width of the paper and
        made black and white, with dithering.

        :param bytes image: the content of the image, in any format PIL reads
        :return: a dict with the ``width`` and ``height`` of the raster, in
            dots, and the ``raster`` itself: the rows of the image from the top,
            8 dots per byte, a set bit printing black, encoded in base64
        """
        img = Image.open(io.BytesIO(image))
        # Transparent areas are printed white.
        img = img.convert('RGBA')
        background = Image.new('RGBA', img.size, 'white')
        img = Image.alpha_composite(background, img)
        if img.width > img.height:
            img = img.transpose(Image.Transpose.ROTATE_270)
        height = max(1, round(img.height * EPOS_PAPER_WIDTH / img.width))
        img = img.convert('L').resize((EPOS_PAPER_WIDTH, height), Image.Resampling.LANCZOS)
        # Floyd-Steinberg dithering. In mode '1', a set bit is white: invert
        # the bits so that a set bit prints black.
        raster = bytes(byte ^ 0xFF for byte in img.convert('1').tobytes())
        return {
            'width': EPOS_PAPER_WIDTH,
            'height': height,
            'raster': base64.b64encode(raster).decode(),
        }
