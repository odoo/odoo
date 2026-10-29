# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import UserError

# The reports printing the attachments the carriers save in the chatter of the
# transfers, and the prefix of the names of these attachments.
SHIPPING_REPORT_PREFIXES = {
    'stock_printer.report_shipping_labels': 'Label',
    'stock_printer.report_shipping_documents': 'ShippingDoc',
}
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def _get_shipping_attachments(self, report_sudo, res_ids):
        """ The attachments of the transfers a shipping report prints, the most recent first. """
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'stock.picking'),
            ('res_id', 'in', res_ids),
            ('name', '=like', f"{SHIPPING_REPORT_PREFIXES[report_sudo.report_name]}%"),
        ], order='create_date desc, id desc')

    @api.model
    def _render_printer_documents_zpl(self, report_sudo, res_ids, data=None):
        if report_sudo.report_name not in SHIPPING_REPORT_PREFIXES:
            return super()._render_printer_documents_zpl(report_sudo, res_ids, data=data)
        return [
            attachment.raw.decode()
            for attachment in self._get_shipping_attachments(report_sudo, res_ids)
            if attachment.name.lower().endswith('.zpl')
        ]

    @api.model
    def _render_printer_documents_epos(self, report_sudo, res_ids, data=None):
        if report_sudo.report_name not in SHIPPING_REPORT_PREFIXES:
            return super()._render_printer_documents_epos(report_sudo, res_ids, data=data)
        return [
            self._convert_image_to_epos_document(attachment.raw.content)
            for attachment in self._get_shipping_attachments(report_sudo, res_ids)
            if attachment.name.lower().endswith(IMAGE_EXTENSIONS)
        ]

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """ Printed the usual way, a shipping report downloads the most recent
        attachment, when it is a PDF; its other attachments are meant for the
        printers.
        """
        report_sudo = self._get_report(report_ref)
        if report_sudo.report_name not in SHIPPING_REPORT_PREFIXES:
            return super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)
        if isinstance(res_ids, int):
            res_ids = [res_ids]
        attachment = self._get_shipping_attachments(report_sudo, res_ids or [])[:1]
        if not attachment:
            raise UserError(self.env._(
                "There is no %(report)s to print in the chatter of the transfer: they are saved there when"
                " the transfer is validated, if its carrier creates them.",
                report=report_sudo.name,
            ))
        if attachment.mimetype != 'application/pdf':
            if not report_sudo.printer_ids:
                raise UserError(self.env._(
                    "%(attachment)s is not a PDF, it can only be printed on a printer, and the report %(report)s"
                    " has no printer configured. Set a ZPL or ePOS printer on the report.",
                    attachment=attachment.name,
                    report=report_sudo.name,
                ))
            raise UserError(self.env._(
                "%(attachment)s is not a PDF, it cannot be downloaded. Configure the carrier to produce PDF"
                " documents, or print the report %(report)s on a ZPL or ePOS printer.",
                attachment=attachment.name,
                report=report_sudo.name,
            ))
        return attachment.raw.content, 'pdf'
