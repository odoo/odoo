from datetime import datetime, timedelta
from psycopg2 import OperationalError
from pytz import timezone
from werkzeug.urls import url_quote_plus, url_encode

import hashlib
import logging
import math
import requests.exceptions
import json

from odoo import _, api, fields, models
from odoo.addons.certificate.tools import CertificateAdapter
from odoo.exceptions import UserError
from odoo.tools import float_repr, float_round, frozendict, zeep

import odoo.release

_logger = logging.getLogger(__name__)

# Custom patches to perform the WSDL requests.
# Avoid failure on servers where the DH key is too small
EUSKADI_CIPHERS = "DEFAULT:!DH"

VERIFACTU_VERSION = "1.0"

BATCH_LIMIT = 1000


def _sha256(string):
    hash_string = hashlib.sha256(string.encode('utf-8'))
    return hash_string.hexdigest().upper()


def _get_zeep_operation(company, operation):
    """The creation of the zeep client may raise (in case of networking issues)."""
    if operation not in ('registration', 'registration_xml'):
        raise NotImplementedError(_("Unsupported `operation` '%s'", operation))

    session = requests.Session()

    info = {}

    def response_hook(resp, *args, **kwargs):
        info['raw_response'] = resp.text

    session.hooks['response'] = response_hook

    settings = zeep.Settings(forbid_entities=False, strict=False)
    wsdl = company._l10n_es_edi_verifactu_get_endpoints()['wsdl']
    client = zeep.Client(
        wsdl['url'], session=session, settings=settings,
        operation_timeout=20, timeout=20,
    )

    if operation == 'registration':
        # Note: using the "certificate" before creating `client` causes an error during the `client` creation
        session.cert = company.sudo()._l10n_es_edi_verifactu_get_certificate()
        session.mount('https://', CertificateAdapter(ciphers=EUSKADI_CIPHERS))

        service = client.bind(wsdl['service'], wsdl['port'])
        function = service[wsdl[operation]]
    else:
        # operation == 'registration_xml'
        zeep_client = client._Client__obj  # get the "real" zeep client from the odoo specific wrapper
        service = zeep_client.bind(wsdl['service'], wsdl['port'])

        def function(*args, **kwargs):
            return zeep_client.create_message(service, wsdl['registration'], *args, **kwargs)

    return function, info


class L10nEsEdiVerifactuDocument(models.Model):
    """Veri*Factu Document
    It represents a billing record with the necessary data specified by the AEAT.
    It i.e. ...
      * stores the data as JSON
      * handles the sending of the data as XML to the AEAT
      * stores information extracted from the received response

    The main functions are
      1. `_create_for_record` to generate Veri*Factu Documents (submission or cancellation):
         * The documents form a chain in generation order by including a reference to the preceding document.
         * The function handles the correct chaining.
      2. `trigger_next_batch` to send all waiting documents (now if possible or via a cron as soon as possible)

    We can not necessarily send the documents directly after generation.
    This is because the AEAT requires a waiting time between shipments (or reaching 1000 new records to send).
    The waiting time is usually 60 seconds.
    In case we cannot send the records directly a cron will be triggered at the next possible time.

    Note that (succesfully generated) Documents can not be deleted.
    This is since the Documents form a chain (in generation order) by including a reference to the preceding document.
    The chain also includes documents that are (/ possibly will be) rejected by the AEAT.
    """
    _name = 'l10n_es_edi_verifactu.document'
    _description = "Veri*Factu Document"
    _order = 'create_date DESC, id DESC'

    company_id = fields.Many2one(
        string="Company",
        comodel_name='res.company',
        required=True,
        readonly=True,
    )
    move_id = fields.Many2one(
        string="Journal Entry",
        comodel_name='account.move',
        readonly=True,
    )
    chain_index = fields.Integer(
        string="Chain Index",
        copy=False,
        readonly=True,
        help="Index in the chain of Veri*Factu Documents. It is only set if the generation was succesful.",
    )
    document_type = fields.Selection(
        string="Document Type",
        selection=[
            ('submission', "Submission"),
            ('cancellation', "Cancellation"),
        ],
        readonly=True,
        required=True,
    )
    # Note: Noone has write access of any kind to the model 'verifactu.document' (see ir.model.access.csv)
    json_attachment_id = fields.Many2one(
        string="JSON Attachment",
        comodel_name='ir.attachment',
        readonly=True,
        copy=False,
    )
    # To use the binary widget in the form view to download the attachment
    json_attachment_base64 = fields.Binary(
        string="JSON",
        related='json_attachment_id.datas',
    )
    json_attachment_filename = fields.Char(
        string="JSON Filename",
        compute='_compute_json_attachment_filename',
    )
    errors = fields.Html(
        string="Errors",
        copy=False,
        readonly=True,
    )
    response_csv = fields.Char(
        string="Response CSV",
        copy=False,
        readonly=True,
        help="The CSV of the response from the tax agency. There may not be one in case all documents of the batch were rejected.",
    )
    state = fields.Selection(
        string="Status",
        selection=[
            ('rejected', "Rejected"),
            ('registered_with_errors', "Registered with Errors"),
            ('accepted', "Accepted"),
        ],
        copy=False,
        readonly=True,
        help="""- Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent record
                - Accepted: Registered by the AEAT without errors""",
    )

    @api.depends('document_type')
    def _compute_display_name(self):
        for document in self:
            document.display_name = _("Veri*Factu Document %s", document.id)

    @api.depends('chain_index', 'document_type')
    def _compute_json_attachment_filename(self):
        for document in self:
            document_type = 'anulacion' if document.document_type == 'cancellation' else 'alta'
            name = f"verifactu_registro_{document.chain_index}_{document_type}.json"
            document.json_attachment_filename = name

    @api.ondelete(at_uninstall=False)
    def _never_unlink_chained_documents(self):
        for document in self:
            if document.chain_index:
                raise UserError(_("You cannot delete Veri*Factu Documents that are part of the chain of all Veri*Factu Documents."))

    def _get_document_dict(self):
        self.ensure_one()
        if not self.json_attachment_id:
            return {}
        json_data = self.json_attachment_id.raw
        return json.loads(json_data)

    def _get_record_identifier(self):
        if not self:
            return False
        return self._extract_record_identifiers(self._get_document_dict())

    @api.model
    def _extract_record_identifiers(self, document_dict):
        """Return a dictionary that includes:
          * the IDFactura fields
          * the fields used for the fingerprint generation of this document and the next one
            (The fingerprint of this record is part of the fingerprint generation of the next record)
          * the fields used for QR code generation
          * the fields used for ImporteRectificacion (in case of rectification by substitutuion)
        """
        cancellation = 'RegistroAnulacion' in document_dict
        record_type = 'RegistroAnulacion' if cancellation else 'RegistroAlta'
        record_type_vals = document_dict[record_type]
        id_factura = record_type_vals['IDFactura']

        identifiers = {
            'FechaHoraHusoGenRegistro': record_type_vals['FechaHoraHusoGenRegistro'],
            'Huella': record_type_vals['Huella'],
        }
        if cancellation:
            identifiers.update({
                'IDEmisorFactura': id_factura['IDEmisorFacturaAnulada'],
                'NumSerieFactura': id_factura['NumSerieFacturaAnulada'],
                'FechaExpedicionFactura': id_factura['FechaExpedicionFacturaAnulada'],
            })
        else:
            identifiers.update({
                **{key: id_factura[key] for key in ['IDEmisorFactura', 'NumSerieFactura', 'FechaExpedicionFactura']},
                **{key: record_type_vals[key] for key in ['TipoFactura', 'CuotaTotal', 'ImporteTotal']},
                'FechaOperacion': record_type_vals.get('FechaOperacion'),  # optional
            })
        return identifiers

    @api.model
    def _format_errors(self, title, errors):
        error = {
            'error_title': title,
            'errors': errors,
        }
        return self.env['account.move.send']._format_error_html(error)

    ####################################################################
    # Helpers to be used on the records ('account.move' / 'pos.order') #
    ####################################################################

    @api.model
    def _get_tax_details(self, base_lines, company, tax_lines=None):
        AccountTax = self.env['account.tax']
        tax_details_functions = AccountTax._l10n_es_edi_verifactu_get_tax_details_functions(company)
        base_line_filter = tax_details_functions['base_line_filter']
        total_grouping_function = tax_details_functions['total_grouping_function']
        tax_details_grouping_function = tax_details_functions['tax_details_grouping_function']

        base_lines = [base_line for base_line in base_lines if base_line_filter(base_line)]

        AccountTax._add_tax_details_in_base_lines(base_lines, company)
        AccountTax._round_base_lines_tax_details(base_lines, company, tax_lines=tax_lines)

        # Totals
        base_lines_aggregated_values_for_totals = AccountTax._aggregate_base_lines_tax_details(base_lines, total_grouping_function)
        totals = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values_for_totals)[True]

        # Tax details
        base_lines_aggregated_values_for_tax_details = AccountTax._aggregate_base_lines_tax_details(base_lines, tax_details_grouping_function)
        tax_details = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values_for_tax_details)

        return {
            'base_amount': totals['base_amount'],
            'tax_amount': totals['tax_amount'],
            'tax_details': {key: tax_detail for key, tax_detail in tax_details.items() if key},
            'tax_details_per_record': {
                frozendict(base_line): {key: tax_detail for key, tax_detail in tax_details.items() if key}
                for base_line, tax_details in base_lines_aggregated_values_for_tax_details
            },
        }

    def _filter_waiting(self):
        return self.filtered(lambda doc: not doc.state and doc.json_attachment_id)

    def _get_last(self, document_type):
        return self.filtered(lambda doc: doc.document_type == document_type and doc.json_attachment_id).sorted()[:1]

    def _get_state(self):
        # Helper method to get the most recent state from a set of documents.
        # It should only be used on all the documents associated with a move or pos order.
        last_registered_document = self.filtered(lambda doc: doc.state in ('registered_with_errors', 'accepted')).sorted()[:1]
        if last_registered_document:
            cancellation = last_registered_document.document_type == 'cancellation'
            return 'cancelled' if cancellation else last_registered_document.state

        rejected_document = self.filtered(lambda doc: doc.state == 'rejected')[:1]
        if rejected_document:
            return 'rejected'

        return False

    def _get_qr_code_img_url(self):
        self.ensure_one()
        record_identifier = self._get_record_identifier()
        if not record_identifier or self.document_type != 'submission':
            # We take the values from the record identifier.
            # And only the 'submission' has all the necessary values ('ImporteTotal').
            return False
        # Documentation: "Detalle de las especificaciones técnicas del código «QR» de la factura y de la «URL» del
        # servicio de cotejo o remisión de información por parte del receptor de la factura"
        # https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/DetalleEspecificacTecnCodigoQRfactura.pdf
        endpoint_url = self.company_id._l10n_es_edi_verifactu_get_endpoints()['QR']
        url_params = url_encode({
            'nif': record_identifier['IDEmisorFactura'],
            'numserie': record_identifier['NumSerieFactura'],
            'fecha': record_identifier['FechaExpedicionFactura'],
            'importe': record_identifier['ImporteTotal'],
        })
        url = url_quote_plus(f"{endpoint_url}?{url_params}")
        return f'/report/barcode/?barcode_type=QR&value={url}&barLevel=M&width=180&height=180'

    @api.model
    def _check_record_values(self, vals):
        errors = []

        company_NIF = vals['company'].partner_id._l10n_es_edi_verifactu_get_values()['NIF']
        if not company_NIF or len(company_NIF) != 9:  # NIFType
            errors.append(_("The NIF '%(company_NIF)s' of the company is not exactly 9 characters long.",
                            company_NIF=company_NIF))

        if not vals['name'] or len(vals['name']) > 60:
            errors.append(_("The name of the record is not between 1 and 60 characters long: %(name)s.",
                            name=vals['name']))

        if vals['documents'] and vals['documents']._filter_waiting():
            errors.append(_("We are waiting to send a Veri*Factu record to the AEAT already."))

        verifactu_registered = vals['verifactu_state'] in ('registered_with_errors', 'accepted')
        # We currently do not support updating registered records (resending).
        if not vals['cancellation'] and verifactu_registered:
            errors.append(_("The record is Veri*Factu registered already."))
        # We currently do not support cancelling records that are not registered or were registered outside odoo.
        if vals['cancellation'] and not verifactu_registered:
            errors.append(_("The cancelled record is not Veri*Factu registered (inside Odoo)."))

        certificate = vals['company'].sudo()._l10n_es_edi_verifactu_get_certificate()
        if not certificate:
            errors.append(_("There is no certificate configured for Veri*Factu on the company."))

        if not vals['invoice_date']:
            errors.append(_("The invoice date is missing."))

        if vals['verifactu_move_type'] == 'correction_substitution' and not vals['substituted_document']:
            errors.append(_("There is no Veri*Factu document for the substituted record."))

        if vals['verifactu_move_type'] == 'correction_substitution' and not vals['substituted_document_reversal_document']:
            errors.append(_("There is no Veri*Factu document for the reversal of the substituted record."))

        if vals['verifactu_move_type'] in ('correction_incremental', 'reversal_for_substitution') and not vals['refunded_document']:
            errors.append(_("There is no Veri*Factu document for the refunded record."))

        need_refund_reason = vals['verifactu_move_type'] in ('correction_incremental', 'correction_substitution')
        if need_refund_reason and not vals['refund_reason']:
            errors.append(_("The refund reason is not specified."))

        simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
        partner_specified = vals['partner'] and vals['partner'] != simplified_partner
        if need_refund_reason and vals['refund_reason'] != 'R5' and vals['is_simplified']:
            errors.append(_("A refund with Refund Reason %(refund_reason)s is not simplified (it needs a partner).",
                            refund_reason=vals['refund_reason']))

        if vals['verifactu_move_type'] == 'invoice' and not partner_specified and not vals['is_simplified']:
            errors.append(_("A non-simplified invoice needs a partner."))

        if not vals['l10n_es_applicability']:
            errors.append(_("Missing Veri*Factu Tax Applicability (Impuesto)."))

        if vals['l10n_es_applicability'] in ('01', '03') and not vals['clave_regimen']:
            errors.append(_("Missing Veri*Factu Regime Key (ClaveRegimen)."))

        sujeto_tax_types = self.env['account.tax']._l10n_es_get_sujeto_tax_types()
        ignored_tax_types = ['ignore', 'retencion']
        supported_tax_types = sujeto_tax_types + ignored_tax_types + ['no_sujeto', 'no_sujeto_loc', 'recargo', 'exento']
        tax_type_description = self.env['account.tax']._fields['l10n_es_type'].get_description(self.env)
        if not vals['tax_details']['tax_details']:
            errors.append(_("There are no taxes set on the invoice"))
        for key, tax_detail in vals['tax_details']['tax_details'].items():
            tax_type = key['l10n_es_type']
            if tax_type not in supported_tax_types:
                # tax_type in ('no_deducible', 'dua')
                # The remaining tax types are purchase taxes (for vendor bills).
                errors.append(_("A tax with value '%(tax_type)s' as %(field)s is not supported.",
                                field=tax_type_description['string'],
                                tax_type=dict(tax_type_description['selection'])[tax_type]))
            elif tax_type in ('no_sujeto', 'no_sujeto_loc'):
                tax_percentage = key['amount']
                tax_amount = tax_detail['tax_amount']
                if float_round(tax_percentage, precision_digits=2) or float_round(tax_amount, precision_digits=2):
                    errors.append(_("No Sujeto VAT taxes must have 0 amount."))
            if len(key['recargo_taxes']) > 1:
                errors.append(_("Only a single recargo tax may be used per \"main\" tax."))

        main_tax_types = self.env['account.tax']._l10n_es_get_main_tax_types()
        tax_applicabilities = {
            grouping_key['l10n_es_applicability']
            for grouping_key in vals['tax_details']['tax_details']
            if grouping_key['l10n_es_type'] in main_tax_types
        }
        if len(tax_applicabilities) > 1:
            name_map = self.env['account.tax']._l10n_es_edi_verifactu_get_applicability_name_map()
            errors.append(_("We only allow a single Veri*Factu Tax Applicability (Impuesto) per document: %(applicabilities)s.",
                            applicabilities=', '.join([name_map[t] for t in tax_applicabilities])))

        for record_detail in vals['tax_details']['tax_details_per_record'].values():
            main_tax_details = [
                tax_detail for key, tax_detail in record_detail.items()
                if key['l10n_es_type'] in main_tax_types
            ]
            if len(main_tax_details) > 1:
                errors.append(_("We only allow a single \"main\" tax per line."))
                break  # Giving the errors once should be enough

        return errors

    #####################
    # Document Creation #
    #####################

    def _create_for_record(self, record_values):
        """Create Veri*Factu documents for input `record_values`.
        Return the created document.
        The documents are also created in case the JSON generation fails; to inspect the errors.
        Such documents are deleted in case the JSON generation succeeds for a record at a later time.
        (In case we succesfully create a JSON we delete all linked documents that failed the JSON creation.)
        :param list record_values: record values dictionary
        """
        document_vals = record_values['document_vals']
        error_title = _("The Veri*Factu document could not be created")

        if not record_values['errors']:
            record_values['errors'] = self._check_record_values(record_values)

        if record_values['errors']:
            document_vals['errors'] = self._format_errors(error_title, record_values['errors'])
        else:
            previous_document = record_values['company']._l10n_es_edi_verifactu_get_last_document()
            render_vals = self._render_vals(
                record_values, previous_record_identifier=previous_document._get_record_identifier(),
            )
            document_dict = {render_vals['record_type']: render_vals[render_vals['record_type']]}

            # We check whether zeep can generate a valid XML (according to the information from the WSDL / XSD)
            # from the `document_dict`.
            # Otherwise this may happen at sending. But then the issue may be hard to resolve:
            # - Each generated document should also be sent to the AEAT.
            # - Documents must not be altered after generation.
            # The created XML (`create_message`) is just discarded.
            create_message = None
            try:
                # We only generate the XML; nothing is sent at this point.
                create_message, _zeep_info = _get_zeep_operation(record_values['company'], 'registration_xml')
            except (zeep.exceptions.Error, requests.exceptions.RequestException) as error:
                # The zeep client creation may cause a networking error
                errors = [_("Networking error: %s", error)]
                document_vals['errors'] = self._format_errors(error_title, errors)
                _logger.error("%s\n%s\n%s", error_title, errors[0], json.dumps(document_dict, indent=4))

            if create_message:
                batch_dict = self.with_company(record_values['company'])._get_batch_dict([document_dict])
                try:
                    _xml_node = create_message(batch_dict['Cabecera'], batch_dict['RegistroFactura'])
                except zeep.exceptions.ValidationError as error:
                    errors = [_("Validation error: %s", error)]
                    document_vals['errors'] = self._format_errors(error_title, errors)
                    _logger.error("%s\n%s\n%s", error_title, errors[0], json.dumps(batch_dict, indent=4))
                except zeep.exceptions.Error as error:
                    errors = [error]
                    document_vals['errors'] = self._format_errors(error_title, errors)
                    _logger.error("%s\n%s\n%s", error_title, errors[0], json.dumps(batch_dict, indent=4))

            if not document_vals.get('errors'):
                chain_sequence = record_values['company'].sudo()._l10n_es_edi_verifactu_get_chain_sequence()
                try:
                    document_vals['chain_index'] = chain_sequence.next_by_id()
                except OperationalError as e:
                    # We chain all the created documents per company in generation order.
                    # (indexed by `chain_index`).
                    # Thus we can not generate multiple documents for the same company at the same time.
                    # Function `next_by_id` effectively locks `company.l10n_es_edi_verifactu_chain_sequence_id`
                    # to prevent different transactions from chaining documents at the same time.
                    errors = [_("Error while chaining the document: %s", e)]
                    document_vals['errors'] = self._format_errors(error_title, errors)
                    _logger.error("%s\n%s\n%s", error_title, errors[0], json.dumps(batch_dict, indent=4))

        document = self.sudo().create(document_vals)

        if document.chain_index:
            attachment = self.env['ir.attachment'].sudo().create({
                'raw': json.dumps(document_dict, indent=4).encode(),
                'name': document.json_attachment_filename,
                'res_id': document.id,
                'res_model': document._name,
                'mimetype': 'application/json',
            })
            document.sudo().json_attachment_id = attachment
            # Remove (previously generated) documents that failed to generate a (valid) JSON
            record_values['documents'].filtered(lambda rd: not rd.json_attachment_id).sudo().unlink()

        return document

    #################
    # JSON Creation #
    #################

    @api.model
    def _format_date_type(self, date):
        if not date:
            return None
        # Format as 'fecha' type from xsd
        return date.strftime('%d-%m-%Y')

    @api.model
    def _round_format_number_2(self, number):
        # Round and format as number with 2 precision digits
        # I.e. used for 'ImporteSgn12.2Type' and 'Tipo2.2Type' XSD types.
        # We do not check / fix the number of digits in front of the decimal separator
        if number is None:
            return None
        rounded = float_round(number, precision_digits=2)
        return float_repr(rounded, precision_digits=2)

    @api.model
    def _render_vals(self, vals, previous_record_identifier=None):
        def remove_None_and_False(value):
            # Remove `None` and `False` from dictionaries
            if isinstance(value, dict):
                return {
                    key: remove_None_and_False(value)
                    for key, value in value.items()
                    if value is not None and value is not False
                }
            elif isinstance(value, list):
                return [remove_None_and_False(v) for v in value]
            else:
                return value

        record_type = 'RegistroAnulacion' if vals['cancellation'] else 'RegistroAlta'
        render_vals = {
            'company': vals['company'],
            'record_type': record_type,
            'record': vals['record'],
            'cancellation': vals['cancellation'],
            'vals': vals,
            'previous_record_identifier': previous_record_identifier,
        }

        generation_time_string = fields.Datetime.now(timezone('Europe/Madrid')).astimezone(timezone('Europe/Madrid')).isoformat()

        record_type_vals = {
            'IDVersion': VERIFACTU_VERSION,
            'FechaHoraHusoGenRegistro': generation_time_string,
            **self._render_vals_operation(vals),
            **self._render_vals_previous_submissions(vals),
            **self._render_vals_monetary_amounts(vals),
            **self._render_vals_SistemaInformatico(vals),
        }
        render_vals[record_type] = remove_None_and_False(record_type_vals)

        self._update_render_vals_with_chaining_info(render_vals)

        return render_vals

    @api.model
    def _render_vals_operation(self, vals):
        company_values = vals['company'].partner_id._l10n_es_edi_verifactu_get_values()
        invoice_date = self._format_date_type(vals['invoice_date'])

        if vals['cancellation']:
            render_vals = {
                'IDFactura': {
                    'IDEmisorFacturaAnulada': company_values['NIF'],
                    'NumSerieFacturaAnulada': vals['name'],
                    'FechaExpedicionFacturaAnulada': invoice_date,
                }
            }
            return render_vals

        render_vals = {
            'NombreRazonEmisor': company_values['NombreRazon'],
            'IDFactura': {
                'IDEmisorFactura': company_values['NIF'],
                'NumSerieFactura': vals['name'],
                'FechaExpedicionFactura': invoice_date,
            }
        }

        rectified_document = vals['refunded_document'] or vals['substituted_document']
        if vals['verifactu_move_type'] == 'invoice':
            tipo_rectificativa = None
            tipo_factura = 'F2' if vals['is_simplified'] else 'F1'
            delivery_date = self._format_date_type(vals['delivery_date'])
            fecha_operacion = delivery_date if delivery_date and delivery_date != invoice_date else None
        elif vals['verifactu_move_type'] == 'reversal_for_substitution':
            tipo_rectificativa = None
            tipo_factura = 'F2' if vals['is_simplified'] else 'F1'
            fecha_operacion = None
        elif vals['verifactu_move_type'] == 'correction_substitution':
            tipo_rectificativa = 'S'
            tipo_factura = vals['refund_reason']
            rectified = rectified_document._get_record_identifier()
            fecha_operacion = rectified['FechaOperacion'] or rectified['FechaExpedicionFactura']
        else:
            # vals['verifactu_move_type'] == 'correction_incremental':
            tipo_rectificativa = 'I'
            tipo_factura = vals['refund_reason']
            rectified = rectified_document._get_record_identifier()
            fecha_operacion = rectified['FechaOperacion'] or rectified['FechaExpedicionFactura']

        # Note: Error [1189]
        # Si TipoFactura es F1 o F3 o R1 o R2 o R3 o R4 el bloque Destinatarios tiene que estar cumplimentado.

        if not vals['is_simplified']:
            render_vals['Destinatarios'] = {
                'IDDestinatario': [vals['partner']._l10n_es_edi_verifactu_get_values()]
            }

        render_vals.update({
            'TipoFactura': tipo_factura,
            'TipoRectificativa': tipo_rectificativa,  # may be None
            'FechaOperacion': fecha_operacion,
            'DescripcionOperacion': vals['description'] or 'manual',
        })

        if vals['verifactu_move_type'] in ('correction_incremental', 'correction_substitution'):
            rectified_record_identifier = rectified_document._get_record_identifier()
            render_vals.update({
                'FacturasRectificadas': [{
                    'IDFacturaRectificada': {
                        key: rectified_record_identifier[key]
                        for key in ['IDEmisorFactura', 'NumSerieFactura', 'FechaExpedicionFactura']
                    }
                }],
            })
        # [1118] Si la factura es de tipo rectificativa por sustitución el bloque ImporteRectificacion es obligatorio.
        if vals['verifactu_move_type'] == 'correction_substitution':
            # We only support substitution if we also send an invoice that cancels out the amounts of the original invoice.
            # ('Opción 2' in the FAQ under '¿Cómo registra el emisor una factura rectificativa por sustitución “S”?')
            render_vals.update({
                'ImporteRectificacion': {
                    'BaseRectificada': self._round_format_number_2(0),
                    'CuotaRectificada': self._round_format_number_2(0),
                },
            })

        return render_vals

    @api.model
    def _render_vals_previous_submissions(self, vals):
        """
        See "Sistemas Informáticos de Facturación y Sistemas VERI*FACTU" Version 1.1.1 - "Validaciones" p. 22 f.
        https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Validaciones_Errores_Veri-Factu.pdf
        For submissions (ALTA) we do not support any subsanación cases (update of a previously sent invoice).
        (Instead the user can issue a credit note and possibly a new substituting invoice).
        With the nomenclature from the Validations document above the following cases are supported (✓) / unsupported (✗):
          ✓ ALTA (new record)
          ✓ ALTA POR RECHAZO (new record, previously rejected)
          ✗ ALTA DE SUBSANACIÓN (update, previously rejected)
          ✗ ALTA POR RECHAZO DE SUBSANACIÓN (update, previously rejected)
          ✗ ALTA DE SUBSANACIÓN SIN REGISTRO PREVIO (update, record not known to the AEAT)
          ✗ ALTA POR RECHAZO DE SUBSANACIÓN SIN REGISTRO PREVIO (update, record not known to the AEAT, previously rejected)
          ✓ ANULACIÓN (cancellation)
          ✓ ANULACIÓN POR RECHAZO (cancellation, previously rejected)
          ✓ ANULACIÓN SIN REGISTRO PREVIO (cancellation, record not known to the AEAT)
          ✓ ANULACIÓN POR RECHAZO SIN REGISTRO PREVIO  (cancellation, record not known to the AEAT, previously rejected)
        """
        render_vals = {}
        verifactu_registered = vals['verifactu_state'] in ('registered_with_errors', 'accepted')

        if vals['cancellation']:
            render_vals = {
                # A cancelled record can e.g. not exist at the AEAT when we switch to Veri*Factu after the original invoice was created
                'SinRegistroPrevio': 'S' if not verifactu_registered else 'N',
                'RechazoPrevio': 'S' if vals['rejected_before'] else 'N',
            }
        else:
            render_vals = {
                'Subsanacion': 'S' if vals['rejected_before'] else 'N',
                'RechazoPrevio': 'X' if vals['rejected_before'] else None,
            }

        return render_vals

    @api.model
    def _render_vals_monetary_amounts(self, vals):
        # Note: We only support a single verifactu tax applicabilty, clave regimen pair per record.
        # For moves the clave regime is stored on each move in field `l10n_es_edi_verifactu_clave_regimen`
        if vals['cancellation']:
            return {}

        sign = vals['sign']
        sujeto_tax_types = self.env['account.tax']._l10n_es_get_sujeto_tax_types()

        recargo_tax_details_key = {}  # dict (tax_key -> recargo_tax_key)
        for record_tax_details in vals['tax_details']['tax_details_per_record'].values():
            main_key = None
            recargo_key = None
            # Note: There is only a single (main tax, recargo tax) pair on a single invoice line
            #       (if any; see `_check_record_values`)
            for key in record_tax_details:
                if key['recargo_taxes']:
                    main_key = key
                if key['l10n_es_type'] == 'recargo':
                    recargo_key = key
                if main_key and recargo_key:
                    break
            recargo_tax_details_key[main_key] = recargo_key

        detalles = []
        for key, tax_detail in vals['tax_details']['tax_details'].items():
            tax_type = key['l10n_es_type']
            # Tax types 'ignore' and 'retencion' are ignored when generating the `tax_details`
            # See `filter_to_apply` in function `_l10n_es_edi_verifactu_get_tax_details_functions` on 'account.tax'
            if tax_type == 'recargo':
                # Recargo taxes are only used in combination with another tax (a sujeto tax)
                # They will be handled when processing the remaining taxes
                continue

            exempt_reason = key['l10n_es_exempt_reason']  # only set if exempt

            tax_percentage = key['amount']
            base_amount = sign * tax_detail['base_amount']
            tax_amount = math.copysign(tax_detail['tax_amount'], base_amount)

            calificacion_operacion = None  # Reported if not tax-exempt;
            recargo_equivalencia = {}
            if tax_type in sujeto_tax_types:
                calificacion_operacion = 'S2' if tax_type == 'sujeto_isp' else 'S1'
                if key['recargo_taxes']:
                    recargo_key = recargo_tax_details_key.get(key)
                    recargo_tax_detail = vals['tax_details']['tax_details'][recargo_key]
                    recargo_tax_percentage = recargo_key['amount']
                    recargo_tax_amount = math.copysign(recargo_tax_detail['tax_amount'], base_amount)
                    recargo_equivalencia.update({
                        'tax_percentage': recargo_tax_percentage,
                        'tax_amount': recargo_tax_amount,
                    })
            elif tax_type in ('no_sujeto', 'no_sujeto_loc'):
                calificacion_operacion = 'N2' if tax_type == 'no_sujeto_loc' else 'N1'
            else:
                # tax_type == 'exento' (see `_check_record_values`)
                # exempt_reason set already
                # [1238]
                #     Si la operacion es exenta no se puede informar ninguno de los campos
                #     TipoImpositivo, CuotaRepercutida, TipoRecargoEquivalencia y CuotaRecargoEquivalencia.
                tax_percentage = None
                tax_amount = None
                recargo_percentage = None
                recargo_amount = None

            recargo_percentage = recargo_equivalencia.get('tax_percentage')
            recargo_amount = recargo_equivalencia.get('tax_amount')

            # Note on the TipoImpositivo and CuotaRepercutida tags.
            # In some cases it makes a difference for the validation whether the tags are output with 0
            # or not at all:
            # - In the no sujeto cases (calification_operacion in ('N1', 'N2')) we may not include them.
            # - In the (calification_operacion == S2) case the tags have to be included with value 0.
            #
            # See the following errors:
            # [1198]
            #     Si CalificacionOperacion es S2 TipoImpositivo y CuotaRepercutida deberan tener valor 0.
            # [1237]
            #     El valor del campo CalificacionOperacion está informado como N1 o N2 y el impuesto es IVA.
            #     No se puede informar de los campos TipoImpositivo, CuotaRepercutida, TipoRecargoEquivalencia y CuotaRecargoEquivalencia.
            if calificacion_operacion in ('N1', 'N2') and vals['l10n_es_applicability'] == '01':
                tax_percentage = None
                tax_amount = None

            detalle = {
                'Impuesto': vals['l10n_es_applicability'],
                'ClaveRegimen': vals['clave_regimen'],
                'CalificacionOperacion': calificacion_operacion,
                'OperacionExenta': exempt_reason,
                'TipoImpositivo': self._round_format_number_2(tax_percentage),
                'BaseImponibleOimporteNoSujeto': self._round_format_number_2(base_amount),
                'CuotaRepercutida': self._round_format_number_2(tax_amount),
                'TipoRecargoEquivalencia': self._round_format_number_2(recargo_percentage),
                'CuotaRecargoEquivalencia': self._round_format_number_2(recargo_amount),
            }

            detalles.append(detalle)

        total_amount = sign * (vals['tax_details']['base_amount'] + vals['tax_details']['tax_amount'])
        tax_amount = sign * (vals['tax_details']['tax_amount'])

        render_vals = {
            'Macrodato': 'S' if abs(total_amount) >= 100000000 else None,
            'Desglose': {
                'DetalleDesglose': detalles
            },
            'CuotaTotal': self._round_format_number_2(tax_amount),
            'ImporteTotal': self._round_format_number_2(total_amount),
        }

        return render_vals

    @api.model
    def _get_db_identifier(self):
        database_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        return _sha256(database_uuid)

    @api.model
    def _render_vals_SistemaInformatico(self, vals):
        spanish_companies_on_db_count = self.env['res.company'].sudo().search_count([
            ('account_fiscal_country_id.code', '=', 'ES'),
        ], limit=2)

        # Note: We have to declare (self-certify) that we meet the Veri*Factu spec.
        # (DECLARACIÓN RESPONSABLE DE SISTEMAS INFORMÁTICOS DE FACTURACIÓN)
        # The values should match the values given in the declaration.
        render_vals = {
            'SistemaInformatico': {
                'NombreRazon': 'Odoo SA',
                'IDOtro': {
                    'CodigoPais': 'BE',
                    'IDType': '02',  # NIF-IVA
                    'ID': 'BE0477472701',
                },
                'NombreSistemaInformatico': 'Odoo',
                'IdSistemaInformatico': '00',  # identifies Odoo the software as product of Odoo the company
                'Version': odoo.release.version,
                'NumeroInstalacion':  self._get_db_identifier(),
                'TipoUsoPosibleSoloVerifactu': 'S',
                'TipoUsoPosibleMultiOT': 'S',
                'IndicadorMultiplesOT': 'S' if spanish_companies_on_db_count > 1 else 'N',
            },
        }

        return render_vals

    @api.model
    def _update_render_vals_with_chaining_info(self, render_vals):
        record_type_vals = render_vals[render_vals['record_type']]
        predecessor = (render_vals['previous_record_identifier'] or {})
        first_registration = not bool(predecessor)

        if first_registration:
            encadenamiento = {
                'PrimerRegistro': 'S',
            }
        else:
            encadenamiento = {
                'RegistroAnterior': {
                    'IDEmisorFactura': predecessor['IDEmisorFactura'],
                    'NumSerieFactura': predecessor['NumSerieFactura'],
                    'FechaExpedicionFactura': predecessor['FechaExpedicionFactura'],
                    'Huella': predecessor['Huella'],
                }
            }
        # The 'Encadenamiento' info needs to be set already during the `_fingerprint` computation
        record_type_vals['Encadenamiento'] = encadenamiento

        record_type_vals.update({
            'TipoHuella': "01",  # "01" means SHA-256
            'Huella': self._fingerprint(render_vals),
        })

        return render_vals

    @api.model
    def _fingerprint(self, render_vals):
        """
        Documentation: "Detalle de las especificaciones técnicas para generación de la huella o hash de los registros de facturación"
        https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/Veri-Factu_especificaciones_huella_hash_registros.pdf
        """
        record_type_vals = render_vals[render_vals['record_type']]
        id_factura = record_type_vals['IDFactura']
        registro_anterior = record_type_vals['Encadenamiento'].get('RegistroAnterior')  # does not exist for the first document
        record_type_vals_keys = [] if render_vals['cancellation'] else ['TipoFactura', 'CuotaTotal', 'ImporteTotal']
        fingerprint_values = [
            *list(id_factura.items()),
            *[(key, record_type_vals[key]) for key in record_type_vals_keys],
            ('Huella', registro_anterior['Huella'] if registro_anterior else ''),
            ('FechaHoraHusoGenRegistro', record_type_vals['FechaHoraHusoGenRegistro']),
        ]
        string = "&".join([f"{field}={value.strip()}" for (field, value) in fingerprint_values])
        return _sha256(string)

    ###########
    # Sending #
    ###########

    @api.model
    def trigger_next_batch(self):
        """
        1. Send all waiting documents that we can send
        2. Trigger the cron again at a later date to send the documents we could not send
        """
        unsent_domain = [
            ('json_attachment_id', '!=', False),
            ('state', '=', False),
        ]
        documents_per_company = self.sudo()._read_group(
            unsent_domain,
            groupby=['company_id'],
            aggregates=['id:recordset'],
        )

        if not documents_per_company:
            return

        next_trigger_time = None
        for company, documents in documents_per_company:
            # Avoid sending a document twice due to concurrent calls to `trigger_next_batch`.
            # This should also avoid concurrently sending in general since the set of documents
            # in both calls should overlap. (Since we always include all previously unsent documents.)
            try:
                self.env['res.company']._with_locked_records(documents)
            except UserError:
                # We will later make sure that we trigger the cron again
                continue

            # We sort the `documents` to batch them in the order they were chained
            documents = documents.sorted('chain_index')

            # Send batches with size BATCH_LIMIT; they are not restricted by the waiting time
            next_batch = documents[:BATCH_LIMIT]
            start_index = 0
            while len(next_batch) == BATCH_LIMIT:
                next_batch.with_company(company)._send_as_batch()
                start_index += BATCH_LIMIT
                next_batch = documents[start_index:start_index + BATCH_LIMIT]
            # Now: len(next_batch) < BATCH_LIMIT ; we need to respect the waiting time

            if not next_batch:
                continue

            next_batch_time = company.l10n_es_edi_verifactu_next_batch_time
            if not next_batch_time or fields.Datetime.now() >= next_batch_time:
                next_batch.with_company(company)._send_as_batch()
            else:
                # Since we have a `next_batch_time` the `next_trigger_time` will be set to a datetime
                # We set it to the minimum of all the already encountered `next_batch_time`
                next_trigger_time = min(next_trigger_time or datetime.max, next_batch_time)

        # In case any of the documents were not successfully sent we trigger the cron again in 60s
        # (or at the next batch time if the 60s is earlier)
        for company, documents in documents_per_company:
            unsent_documents = documents.filtered_domain(unsent_domain)
            next_batch_time = company.l10n_es_edi_verifactu_next_batch_time
            if unsent_documents:
                # Trigger in 60s or at the next batch time (except if there is an earlier trigger already)
                in_60_seconds = fields.Datetime.now() + timedelta(seconds=60)
                company_next_trigger_time = max(in_60_seconds, next_batch_time or datetime.min)
                # Set `next_trigger_time` to the minimum of all the already encountered trigger times
                next_trigger_time = min(next_trigger_time or datetime.max, company_next_trigger_time)

        if next_trigger_time:
            cron = self.env.ref('l10n_es_edi_verifactu.cron_verifactu_batch', raise_if_not_found=False)
            if cron:
                cron._trigger(at=next_trigger_time)

    @api.model
    def _send_batch(self, batch_dict):
        info = {
            'errors': [],
            'record_info': {},
            'soap_fault': False,
        }
        errors = info['errors']
        record_info = info['record_info']

        try:
            register, zeep_info = _get_zeep_operation(self.env.company, 'registration')
        except (zeep.exceptions.Error, requests.exceptions.RequestException) as error:
            errors.append(_("Networking error:\n%s", error))
            return info

        try:
            res = register(batch_dict['Cabecera'], batch_dict['RegistroFactura'])
            # `res` is of type 'zeep.client.SerialProxy'
        except requests.exceptions.SSLError:
            errors.append(_("The SSL certificate could not be validated."))
        except zeep.exceptions.TransportError as error:
            certificate_error = "No autorizado. Se ha producido un error al verificar el certificado presentado"
            if certificate_error in error.message:
                errors.append(_("The document could not be sent; the access was denied due to a problem with the certificate."))
            else:
                errors.append(_("Networking error while sending the document:\n%s", error))
        except requests.exceptions.ReadTimeout as error:
            # The error is only partially translated since we check for this message for the timeout duplicate handling.
            # (See `_send_as_batch`)
            error_description = _("Timeout while waiting for the response from the server:\n%s", error)
            errors.append(f"[Read-Timeout] {error_description}")
        except requests.exceptions.RequestException as error:
            errors.append(_("Networking error while sending the document:\n%s", error))
        except zeep.exceptions.Fault as soapfault:
            info['soap_fault'] = True
            errors.append(f"[{soapfault.code}] {soapfault.message}")
        except zeep.exceptions.XMLSyntaxError as error:
            _logger.error("raw zeep response:\n%s", zeep_info.get('raw_response'))
            certificate_error = "The root element found is html"
            if certificate_error in error.message:
                errors.append(_("The response of the server had the wrong format (HTML instead of XML). It is most likely a problem with the certificate."))
            else:
                errors.append(_("Error while sending the batch document:\n%s", error))
        except zeep.exceptions.Error as error:
            _logger.error("raw zeep response:\n%s", zeep_info.get('raw_response'))
            errors.append(_("Error while sending the batch document:\n%s", error))

        if errors:
            return info

        info.update({
            'response_csv': res['CSV'] if 'CSV' in res else None,  # noqa: SIM401 - `res` is of type 'zeep.client.SerialProxy'
            'waiting_time_seconds': int(res['TiempoEsperaEnvio']),
        })

        # EstadoRegistroType
        state_map = {
            'Incorrecto': 'rejected',
            'AceptadoConErrores': 'registered_with_errors',
            'Correcto': 'accepted',
        }
        # EstadoRegistroSFType
        duplicate_state_map = {
            'AceptadaConErrores': 'registered_with_errors',
            'Correcta': 'accepted',
            'Anulada': 'cancelled',
        }

        for response_line in res['RespuestaLinea']:
            record_id = response_line['IDFactura']
            invoice_issuer = record_id['IDEmisorFactura'].strip()
            invoice_name = record_id['NumSerieFactura'].strip()
            record_key = str((invoice_issuer, invoice_name))

            operation_type = response_line['Operacion']['TipoOperacion']
            received_state = response_line['EstadoRegistro']
            # In case of a duplicate the response supplies information about the original invoice.
            duplicate_info = response_line['RegistroDuplicado']
            duplicate = {}
            if duplicate_info:
                duplicate_state = duplicate_state_map[duplicate_info['EstadoRegistroDuplicado']]
                duplicate = {
                    'state': duplicate_state,
                    'errors': [],
                }
                if duplicate_state in ('rejected', 'registered_with_errors'):
                    error_code = duplicate_info['CodigoErrorRegistro']
                    error_description = duplicate_info['DescripcionErrorRegistro']
                    duplicate['errors'].append(f"[{error_code}] {error_description}")

            state = state_map[received_state]
            errors = []
            if state in ('rejected', 'registered_with_errors'):
                error_code = response_line['CodigoErrorRegistro']
                error_description = response_line['DescripcionErrorRegistro']
                errors.append(f"[{error_code}] {error_description}")

            record_info[record_key] = {
                'state': state,
                'cancellation': operation_type == 'Anulacion',
                'errors': errors,
                'duplicate': duplicate,
            }

        return info

    def _send_as_batch(self):
        # Documents in `self` should all belong to `self.env.company`.
        # For the cron we specifically set the `self.env.company` on some functions we call.
        sender_company = self.env.company

        batch_errors = self.with_company(sender_company)._send_as_batch_check()
        if batch_errors:
            error_title = _("The batch document could not be created")
            self.errors = self._format_errors(error_title, batch_errors)
            info = {'errors': batch_errors}
            return None, info

        # When the document is sent more than 240s after its creation the AEAT registers the document only with an error
        # See error with code 2004:
        #   El valor del campo FechaHoraHusoGenRegistro debe ser la fecha actual del sistema de la AEAT,
        #   admitiéndose un margen de error de: 240 segundos.
        incident = any(document.create_date > fields.Datetime.now() + timedelta(seconds=240) for document in self)

        document_dict_list = [document._get_document_dict() for document in self]
        batch_dict = self.with_company(sender_company)._get_batch_dict(document_dict_list, incident=incident)

        info = self.with_company(sender_company)._send_batch(batch_dict)

        batch_failure_info = {}
        if info['soap_fault'] or info['errors']:
            # Handle SOAP fault or the case that something went wrong while sending or parsing the respone.
            batch_failure_info = {
                'errors': info['errors'],
                'state': 'rejected' if info['soap_fault'] else False
            }

        # Store the information from the response split over the individual documents
        for document, document_dict in zip(self, document_dict_list):
            response_info = (
                batch_failure_info
                or info['record_info'].get(self._extract_record_key(document_dict), None)
                or {'errors': [_("We could not find any information about the record in the linked batch document.")]}
            )

            # In case of a timeout the document may have reached the AEAT but
            # we have not received the response. That is why we take the
            # duplicate information in case of timeout.
            duplicate_info = response_info.get('duplicate', {})
            if (not document.state
                and duplicate_info
                and document.errors
                and "[Read-Timeout] " in document.errors):
                if document.document_type == 'submission' and duplicate_info['state'] in ('accepted', 'registered_with_errors'):
                    response_info.update({
                        'state': duplicate_info['state'],
                        'errors': duplicate_info['errors'],
                    })
                elif document.document_type == 'cancellation' and duplicate_info['state'] == 'cancelled':
                    response_info.update({
                        'state': 'accepted',
                        'errors': duplicate_info['errors'],
                    })

            # Add some information from the batch level in any case.
            response_info.update({
                'waiting_time_seconds': info.get('waiting_time_seconds', False),
                'response_csv': info.get('response_csv', False),
            })

            # The errors have to be formatted (as HTML) before storing them on the document
            errors_html = False
            error_list = response_info.get('errors', [])
            if error_list:
                error_title = _("Error")
                if response_info.get('state', False):
                    error_title = _("The Veri*Factu document contains the following errors according to the AEAT")
                errors_html = self._format_errors(error_title, error_list)
            document.errors = errors_html

            # All other values can be stored directly on the document
            keys = ['response_csv', 'state']
            for key in keys:
                new_value = response_info.get(key, False)
                if new_value or document[key]:
                    document[key] = new_value

            # To avoid losing data we commit after every document
            if self.env['account.move']._can_commit():
                self.env.cr.commit()

        waiting_time_seconds = info.get('waiting_time_seconds')
        if waiting_time_seconds:
            now = fields.Datetime.to_datetime(fields.Datetime.now())
            next_batch_time = now + timedelta(seconds=waiting_time_seconds)
            self.env.company.l10n_es_edi_verifactu_next_batch_time = next_batch_time

        self._cancel_after_sending(info)

        if self.env['account.move']._can_commit():
            self.env.cr.commit()

        return batch_dict, info

    @api.model
    def _send_as_batch_check(self):
        # The batching / sending may happen after the initial check
        errors = []
        company = self.env.company  # sending company

        company_NIF = company.partner_id._l10n_es_edi_verifactu_get_values()['NIF']
        if not company_NIF or len(company_NIF) != 9:  # NIFType
            errors.append(_("The NIF '%(company_NIF)s' of the company is not exactly 9 characters long.",
                            company_NIF=company_NIF))

        certificate = company.sudo()._l10n_es_edi_verifactu_get_certificate()
        if not certificate:
            errors.append(_("There is no certificate configured for Veri*Factu on the company."))

        if len(self) != len(self._filter_waiting()):
            errors.append(_("Some of the documents can not be sent. They were sent already or could not be generated correctly."))

        return errors

    @api.model
    def _get_batch_dict(self, document_dict_list, incident=False):
        company = self.env.company
        company_values = company.partner_id._l10n_es_edi_verifactu_get_values()

        batch_dict = {
          "Cabecera": {
              "ObligadoEmision": {
                  "NombreRazon": company_values['NombreRazon'],
                  "NIF": company_values['NIF'],
              },
              "RemisionVoluntaria": {
                  "Incidencia": 'S' if incident else 'N',
              },
          },
            "RegistroFactura": document_dict_list,
        }

        return batch_dict

    @api.model
    def _extract_record_key(self, document_dict):
        record_identifier = self._extract_record_identifiers(document_dict)
        return str((record_identifier['IDEmisorFactura'], record_identifier['NumSerieFactura']))

    def _cancel_after_sending(self, info):
        # This function should not raise since it may be called "in the middle" of the sending process
        for document in self:
            invoice = document.move_id
            if invoice.l10n_es_edi_verifactu_state == 'cancelled' and invoice.state != 'cancel':
                try:
                    invoice.button_cancel()
                except UserError as error:
                    _logger.error("Error while canceling journal entry %(name)s (id %(record_id)s) after Veri*Factu cancellation:\n%(error)s",
                                  record_id=invoice.id, name=invoice.name, error=error)
