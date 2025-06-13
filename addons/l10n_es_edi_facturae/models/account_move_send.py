import logging

from odoo import _, api, models, SUPERUSER_ID
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_es_facturae_applicable(self, move) -> bool:
        """Check if the Factura-e applies to the given move."""
        return move._l10n_es_edi_facturae_get_default_enable() and move.partner_id.country_code == 'ES'

    def _get_all_extra_edis(self) -> dict:
        """Extend the EDI providers with the Factura-e option."""
        res = super()._get_all_extra_edis()
        res.update({
            'es_facturae': {
                'label': _("Factura-e"),
                'is_applicable': self._is_es_facturae_applicable,
            },
        })
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if es_moves := moves.filtered(lambda m:
            'es_facturae' in moves_data[m]['extra_edis']
            or moves_data[m]['invoice_edi_format'] == 'es_facturae'
        ):
            if es_alerts := es_moves._l10n_es_edi_facturae_export_data_check():
                alerts.update(**es_alerts)
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(move) + move.l10n_es_edi_facturae_xml_id

    def _get_placeholder_mail_attachments_data(self, move, invoice_edi_format=None, extra_edis=None):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move, invoice_edi_format=invoice_edi_format, extra_edis=extra_edis)

        if (
            ('es_facturae' in extra_edis or invoice_edi_format == 'es_facturae')
            and move._l10n_es_edi_facturae_get_default_enable()
        ):
            filename = f'{move.name.replace("/", "_")}_facturae_signed.xml'
            results.append({
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/xml',
                'placeholder': True,
            })

        return results

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)

        if (
            ('es_facturae' in invoice_data['extra_edis'] or invoice_data['invoice_edi_format'] == 'es_facturae')
            and invoice._l10n_es_edi_facturae_get_default_enable()
        ):
            try:
                xml_content, errors = invoice._l10n_es_edi_facturae_render_facturae()
                if errors:
                    invoice_data['error'] = {
                        'error_title': _("Errors occurred while creating the EDI document (format: %s):", "Facturae"),
                        'errors': errors,
                    }
                else:
                    invoice_data['l10n_es_edi_facturae_attachment_values'] = {
                        'name': invoice._l10n_es_edi_facturae_get_filename(),
                        'raw': xml_content,
                        'mimetype': 'application/xml',
                        'res_model': invoice._name,
                        'res_id': invoice.id,
                        'res_field': 'l10n_es_edi_facturae_xml_file',  # Binary field
                    }
            except UserError as e:
                if self.env.context.get('forced_invoice'):
                    _logger.warning(
                        'An error occured during generation of Facturae EDI of %s: %s',
                        invoice.name,
                        e.args[0]
                    )
                else:
                    raise

    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)

        attachments_vals = [
            invoice_data.get('l10n_es_edi_facturae_attachment_values')
            for invoice_data in invoices_data.values()
            if invoice_data.get('l10n_es_edi_facturae_attachment_values')
        ]
        if attachments_vals:
            attachments = self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachments_vals)
            res_ids = attachments.mapped('res_id')
            self.env['account.move'].browse(res_ids).invalidate_recordset(fnames=['l10n_es_edi_facturae_xml_id', 'l10n_es_edi_facturae_xml_file'])
