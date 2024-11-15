from werkzeug.urls import url_quote_plus
from lxml import etree

from odoo import _, api, fields, models


class L10nEsEdiVerifactuRecordMixin(models.AbstractModel):
    """"Veri*Factu Record Mixin"
    It can be added to models from which we want to create Veri*Factu records ("Veri*Factu Record Document" / 'l10n_es_edi_verifactu.recorddocument'):
    I.e. it can be added to Invoices ('account.move') and PoS Orders ('pos.order')"""
    _name = 'l10n_es_edi_verifactu.record_mixin'
    _description = "Veri*Factu Record Mixin"

    l10n_es_edi_verifactu_required = fields.Boolean(
        string="Veri*Factu Required",
        compute='_compute_l10n_es_edi_verifactu_required',
    )
    l10n_es_edi_verifactu_record_identifier = fields.Json(
        string="Veri*Factu Record Identifier",
        compute='_compute_l10n_es_edi_verifactu_record_identifier',
        help="Technical field containing the values used to identify records in the Veri*Factu system.",
    )
    l10n_es_edi_verifactu_record_document_ids = fields.One2many(
        comodel_name='l10n_es_edi_verifactu.record_document',
        inverse_name='res_id',
        string="Veri*Factu Records",
    )
    l10n_es_edi_verifactu_state = fields.Selection(
        string="Veri*Factu Status",
        selection=[
            ('sending_failed', 'Sending Failed'),
            ('parsing_failed', 'Error while Parsing the Response'),
            ('rejected', 'Rejected'),
            ('registered_with_errors', 'Registered with Errors'),
            ('accepted', 'Accepted'),
            ('cancelled', 'Cancelled'),
        ],
        compute='_compute_l10n_es_edi_verifactu_info_from_record_document_ids',
        help="""- Sending Failed: Tried to send to the AEAT but failed
                - Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent record
                - Accepted: Registered by the AEAT without errors
                - Cancelled: Registered by the AEAT as cancelled""",
        store=True,
    )
    l10n_es_edi_verifactu_last_erroneous_record_document_id = fields.Many2one(
        comodel_name='l10n_es_edi_verifactu.record_document',
        compute='_compute_l10n_es_edi_verifactu_info_from_record_document_ids',
        string="Last Erroneous Veri*Factu Record Document",
        help="This QR code is mandatory for Veri*Factu invoices.",
        store=True,
    )
    l10n_es_edi_verifactu_error_level = fields.Selection(
        string="Veri*Factu Error Level",
        related="l10n_es_edi_verifactu_last_erroneous_record_document_id.state",
        store=True,
    )
    l10n_es_edi_verifactu_errors = fields.Html(
        compute='_compute_l10n_es_edi_verifactu_errors',
        string="Veri*Factu Errors",
        related="l10n_es_edi_verifactu_last_erroneous_record_document_id.errors",
    )
    l10n_es_edi_verifactu_qr_code = fields.Char(
        string="Veri*Factu QR Code",
        compute='_compute_l10n_es_edi_verifactu_qr_code',
        help="This QR code is mandatory for Veri*Factu invoices.",
    )

    def _compute_l10n_es_edi_verifactu_required(self):
        # To override
        self.l10n_es_edi_verifactu_required = False

    def _compute_l10n_es_edi_verifactu_record_identifier(self):
        # To override
        self.l10n_es_edi_verifactu_record_identifier = False

    @api.depends('l10n_es_edi_verifactu_record_document_ids', 'l10n_es_edi_verifactu_record_document_ids.state')
    def _compute_l10n_es_edi_verifactu_info_from_record_document_ids(self):
        for record in self:
            last_sent_document = False
            last_succesful_document = False
            last_erroneous_document = False  # only after `last_succesful_document`
            for document in record.l10n_es_edi_verifactu_record_document_ids.sorted():
                if document.record_type not in ('submission', 'cancellation'):
                    continue
                if not last_sent_document and document.response_time and document.state:
                    last_sent_document = document
                if not last_erroneous_document and document.state != 'accepted':
                    last_erroneous_document = document  # only after `last_succesful_document`
                if document.response_time and document.state in ('registered_with_errors', 'accepted'):
                    last_succesful_document = document
                    # We must have found `last_sent_document` already.
                    # We do not care about erroneous documents before the last succesful one.
                    break

            state = False
            if last_succesful_document:
                if last_succesful_document.record_type == 'cancellation':
                    state = 'cancelled'
                else:
                    state = last_succesful_document.state
            elif last_sent_document:
                state = last_sent_document.state

            record.l10n_es_edi_verifactu_last_erroneous_record_document_id = last_erroneous_document
            record.l10n_es_edi_verifactu_state = state

    @api.depends('l10n_es_edi_verifactu_required', 'company_id.l10n_es_edi_verifactu_endpoints', 'l10n_es_edi_verifactu_record_identifier')
    def _compute_l10n_es_edi_verifactu_qr_code(self):
        for record in self:
            record_identifier = record.l10n_es_edi_verifactu_record_identifier
            if not record.l10n_es_edi_verifactu_required or not record_identifier or record_identifier['errors']:
                record.l10n_es_edi_verifactu_qr_code = False
                continue
            url = url_quote_plus(
                f"{record.company_id.l10n_es_edi_verifactu_endpoints['QR']}?"
                f"nif={record_identifier['IDEmisorFactura']}&"
                f"numserie={record_identifier['NumSerieFactura']}&"
                f"fecha={record_identifier['FechaExpedicionFactura']}&"
                f"importe={record_identifier['ImporteTotal']}"
            )
            qr_code = url and f'/report/barcode/?barcode_type=QR&value={url}&barLevel=M&width=180&height=180'
            record.l10n_es_edi_verifactu_qr_code = qr_code

    def _l10n_es_edi_verifactu_get_record_values(self, cancellation=False):
        # To extend
        self.ensure_one()
        errors = []

        rejected_before = False
        record_type = 'cancellation' if cancellation else 'submission'
        for record_document in self.l10n_es_edi_verifactu_record_document_ids.sorted():
            if record_document.state in ('registered_with_errors', 'accepted'):
                # We do not care about record documents sent / generated before the last succesful one
                break
            if record_document.record_type == record_type and record_document.state == 'rejected':
                rejected_before = True
                break

        vals = {
            'rejected_before': rejected_before,
        }
        return vals, errors

    def _l10n_es_edi_verifactu_get_render_vals(self, cancellation=False, previous_record_identifier=None):
        self.ensure_one()
        record_values, errors = self._l10n_es_edi_verifactu_get_record_values(cancellation)
        if errors:
            return {}, errors
        return self.env['l10n_es_edi_verifactu.xml']._render_vals(
            record_values, previous_record_identifier=previous_record_identifier
        )

    def _l10n_es_edi_verifactu_render_xml_node(self, cancellation=False, previous_record_identifier=None):
        self.ensure_one()
        render_info = {
            'render_vals': None,
            'xml_node': None,
            'errors': [],
        }

        render_vals, errors = self._l10n_es_edi_verifactu_get_render_vals(
            cancellation=cancellation, previous_record_identifier=previous_record_identifier
        )
        render_info['render_vals'] = render_vals
        if errors:
            render_info['errors'] = errors
            return render_info

        xml_node, errors = self.env['l10n_es_edi_verifactu.xml']._render_xml_node(render_vals)
        render_info['xml_node'] = xml_node
        if errors:
            render_info['errors'] = errors
            return render_info
        return render_info

    def _l10n_es_edi_verifactu_create_record_document(self, cancellation=False, previous_record_identifier=None):
        """Note: In case we succesfully create an XML we delete all linked record documents that failed the XML creation."""
        self.ensure_one()

        render_info = self._l10n_es_edi_verifactu_render_xml_node(
            cancellation=cancellation, previous_record_identifier=previous_record_identifier,
        )

        record_document_vals = {
            'res_id': self.id,
            'res_model': self._name,
            'company_id': self.company_id.id,
            'record_type': 'cancellation' if cancellation else 'submission',
        }

        generation_errors = render_info['errors']
        if generation_errors:
            xml = None
            error = {
                'error_title': _("The Veri*Factu record could not be created"),
                'errors': generation_errors,
            }
            record_document_vals['errors'] = self.env['account.move.send']._format_error_html(error)
        else:
            render_vals = render_info['render_vals']
            xml = etree.tostring(render_info['xml_node'], xml_declaration=False, encoding='UTF-8')
            record_identifier = render_vals['record_identifier']
            record_identifier['Huella'] = render_vals['vals'][render_vals['record_type']]['Huella']
            record_document_vals['record_identifier'] = record_identifier

        record_document = self.env['l10n_es_edi_verifactu.record_document'].create(record_document_vals)

        if xml:
            record_document.xml_attachment_id = self.env['ir.attachment'].create({
                'raw': xml,
                'name': record_document.xml_attachment_filename,
                'res_id': self.id,
                'res_model': self._name,
                'mimetype': 'application/xml',
            })
            self.l10n_es_edi_verifactu_record_document_ids.filtered(lambda rd: rd.state == 'creating_failed').unlink()

        return record_document

    def l10n_es_edi_verifactu_mark_for_next_batch(self, cancellation=False):
        result = {}
        # TODO:?: lock company / l10n_es_edi_verifactu_last_record_document field
        if self:
            for record in self:
                waiting_record_documents = record.l10n_es_edi_verifactu_record_document_ids.filtered(lambda rd: not rd.state)
                if waiting_record_documents:
                    continue

                company = record.company_id
                previous_record = company.l10n_es_edi_verifactu_last_record_document
                record_document = record._l10n_es_edi_verifactu_create_record_document(
                    cancellation=cancellation, previous_record_identifier=previous_record.record_identifier
                )
                if record_document.state != 'creating_failed':
                    company.l10n_es_edi_verifactu_last_record_document = record_document
                result[record] = record_document
            self.env['l10n_es_edi_verifactu.document'].trigger_next_batch()
        return result
