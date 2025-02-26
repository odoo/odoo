import hashlib
import math
from base64 import b64encode, encodebytes
from pytz import timezone

from copy import deepcopy
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree
from uuid import uuid4

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import cleanup_xml_node, float_repr, float_round
import odoo.release

VERIFACTU_VERSION = "1.0"

NS_MAP = {
    'ds': "http://www.w3.org/2000/09/xmldsig#",
    'soapenv': "http://schemas.xmlsoap.org/soap/envelope/",
}

def _sha256(string):
    hash_string = hashlib.sha256(string.encode('utf-8'))
    return hash_string.hexdigest().upper()

def _path_get(dictionary, slash_path, default=None):
    x = dictionary
    for field in slash_path.split('/'):
        if field not in x:
            return default
        x = x[field]
    return x

def _canonicalize_node(node, **kwargs):
    """
    Returns the canonical representation of node.
    Specified in: https://www.w3.org/TR/2001/REC-xml-c14n-20010315
    Required for computing digests and signatures.
    Returns an UTF-8 encoded bytes string.
    """
    return etree.tostring(node, method="c14n", with_comments=False, **kwargs)

def _get_uri(uri, reference, base_uri=""):
    """
    Returns the content within `reference` that is identified by `uri`.
    Canonicalization is used to convert node reference to an octet stream.
    - URIs starting with # are same-document references
    https://www.w3.org/TR/xmldsig-core/#sec-URI
    - Empty URIs point to the whole document tree, without the signature
    https://www.w3.org/TR/xmldsig-core/#sec-EnvelopedSignature
    Returns an UTF-8 encoded bytes string.
    """
    transform_nodes = reference.findall(".//{*}Transform")
    # handle exclusive canonization
    exc_c14n = bool(transform_nodes) and transform_nodes[0].attrib.get('Algorithm') == 'http://www.w3.org/2001/10/xml-exc-c14n#'
    prefix_list = []
    if exc_c14n:
        inclusive_ns_node = transform_nodes[0].find(".//{*}InclusiveNamespaces")
        if inclusive_ns_node is not None and inclusive_ns_node.attrib.get('PrefixList'):
            prefix_list = inclusive_ns_node.attrib.get('PrefixList').split(' ')

    node = deepcopy(reference.getroottree().getroot())
    if uri == base_uri:
        # Base URI: whole document, without signature (default is empty URI)
        for signature in node.findall('.//ds:Signature', namespaces=NS_MAP):
            if signature.tail:
                # move the tail to the previous node or to the parent
                if (previous := signature.getprevious()) is not None:
                    previous.tail = "".join([previous.tail or "", signature.tail or ""])
                else:
                    signature.getparent().text = "".join([signature.getparent().text or "", signature.tail or ""])
            signature.getparent().remove(signature)  # we can only remove a node from its direct parent
        return _canonicalize_node(node, exclusive=exc_c14n, inclusive_ns_prefixes=prefix_list)

    if uri.startswith("#"):
        path = "//*[@*[local-name() = '{}' ]=$uri]"
        results = node.xpath(path.format("Id"), uri=uri.lstrip("#"))  # case-sensitive 'Id'
        if len(results) == 1:
            return _canonicalize_node(results[0], exclusive=exc_c14n, inclusive_ns_prefixes=prefix_list)
        if len(results) > 1:
            raise UserError(f"Ambiguous reference URI {uri} resolved to {len(results)} nodes")

    raise UserError(f'URI {uri} not found')

def _reference_digests(node, base_uri=""):
    """
    Processes the references from node and computes their digest values as specified in
    https://www.w3.org/TR/xmldsig-core/#sec-DigestMethod
    https://www.w3.org/TR/xmldsig-core/#sec-DigestValue
    """
    for reference in node.findall("ds:Reference", namespaces=NS_MAP):
        ref_node = _get_uri(reference.get("URI", ""), reference, base_uri=base_uri)
        lib = hashlib.new("sha256", ref_node)
        reference.find("ds:DigestValue", namespaces=NS_MAP).text = b64encode(lib.digest())

def _int_to_bytes(number):
    """ Converts an integer to a byte string (in smallest big-endian form). """
    return number.to_bytes((number.bit_length() + 7) // 8, byteorder='big')


class L10nEsEdiVerifactuXml(models.AbstractModel):
    _name = 'l10n_es_edi_verifactu.xml'
    _description = "Handles the generation of XML strings for Veri*Factu records ('l10n_es_edi_verifactu.record_document' and 'l10n_es_edi_verifactu.document')"

    @api.model
    def _format_date_fecha_type(self, date):
        # Format as 'fecha' type from xsd
        return date.strftime('%d-%m-%Y')

    @api.model
    def _round_format_number_2(self, number):
        # Round and format as number with 2 precision digits
        if number is None:
            return None
        rounded = float_round(number, precision_digits=2)
        return float_repr(rounded, precision_digits=2)

    # We do not check / fix the number of digits in front of the decimal separator
    _format_number_ImporteSgn12_2 = _round_format_number_2
    _format_number_Tipo2_2 = _round_format_number_2

    @api.model
    def _render_vals(self, vals, previous_record_identifier=None):

        cancellation = vals['cancellation']
        company = vals['company']
        record_type = 'RegistroAnulacion' if cancellation else 'RegistroAlta'
        render_vals = {
            '_path_get': _path_get,
            'company': company,
            'record_type': record_type,
            'vals': {
                record_type: {},
            },
            'record': vals['record'],
            'record_identifier': vals['identifier'],
            'cancellation': cancellation,
            'errors': [],
        }
        main_render_vals = render_vals['vals'][record_type]
        errors = render_vals['errors']

        company_values = company._get_l10n_es_edi_verifactu_values()
        company_name = company_values['name']
        render_vals['company'] = company

        generation_time_string = fields.Datetime.now(timezone('Europe/Madrid')).astimezone(timezone('Europe/Madrid')).isoformat()

        main_render_vals.update({
            'IDVersion': VERIFACTU_VERSION,
            'NombreRazonEmisor': company_name,
            'FechaHoraHusoGenRegistro': generation_time_string,
        })

        main_render_vals_functions = [
            self._render_vals_operation,
            self._render_vals_previous_submissions,
            self._render_vals_dsig,
            self._render_vals_SistemaInformatico,
            self._render_vals_Destinatarios,
            self._render_vals_monetary_amounts,
            self._render_vals_dsig,
            self._render_vals_SistemaInformatico,
        ]
        for function in main_render_vals_functions:
            new_render_vals, new_errors = function(vals)
            errors.extend(new_errors)
            if not new_errors:
                main_render_vals.update(new_render_vals)

        self._update_render_vals_with_chaining_info(
            render_vals, previous_record_identifier=previous_record_identifier
        )

        return render_vals, errors

    @api.model
    def _get_tipos(self, vals):
        errors = []
        result = {
            'TipoFactura': None,
            'TipoRectificativa': None,
        }
        move_type = vals['move_type']
        is_simplified = vals['is_simplified']
        if move_type == 'out_invoice':
            result['TipoFactura'] = 'F2' if is_simplified else 'F1'
        elif move_type == 'out_refund':
            result.update({
                'TipoFactura': 'R5' if is_simplified else 'R1',
                'TipoRectificativa': 'I',
            })
        else:
            errors.append(_("Could not determine TipoFactura / TipoRectificativa for move_type %s", move_type))
        return result, errors

    @api.model
    def _render_vals_operation(self, vals):
        render_vals = {}
        errors = []

        cancellation = vals['cancellation']

        identifier = vals['identifier']
        invoice_date = identifier['FechaExpedicionFactura']

        delivery_date = vals['delivery_date']
        if delivery_date:
            delivery_date = self._format_date_fecha_type(delivery_date)

        if cancellation:
            render_vals.update({
                'IDFactura': {
                    'IDEmisorFacturaAnulada': identifier['IDEmisorFactura'],
                    'NumSerieFacturaAnulada': identifier['NumSerieFactura'],
                    'FechaExpedicionFacturaAnulada': identifier['FechaExpedicionFactura'],
                },
            })
        else:
            tipos, tipos_errors = self._get_tipos(vals)
            errors.extend(tipos_errors)
            render_vals.update({
                'IDFactura': {
                    'IDEmisorFactura': identifier['IDEmisorFactura'],
                    'NumSerieFactura': identifier['NumSerieFactura'],
                    'FechaExpedicionFactura': identifier['FechaExpedicionFactura'],
                },
                'TipoFactura': tipos['TipoFactura'],
                'TipoRectificativa': tipos['TipoRectificativa'],  # may be None
                'FechaOperacion': delivery_date if delivery_date and delivery_date != invoice_date else None,
                'DescripcionOperacion': vals['description'] or 'manual',
                # TODO: simplified invoices and no recipient identification
                # 'FacturaSimplificadaArt7273': Sólo se podrá rellenar con “S” si TipoFactura=“F1” o “F3” o “R1” o “R2” o “R3” o “R4”
                # ?: 'FacturaSimplificadaArt7273' for simplified invoice with recipient
                # 'FacturaSinIdentifDestinatarioArt61d': Sólo se podrá rellenar con “S” si TipoFactura=”F2” o “R5”
                # ?: 'FacturaSinIdentifDestinatarioArt61d' also for not simplified invoices w/o NIF?
                'FacturaSimplificadaArt7273': None,
                'FacturaSinIdentifDestinatarioArt61d': 'S' if vals['is_simplified'] else None,
            })

            refunded_record = vals['refunded_record']
            refunded_record_identifier = refunded_record and refunded_record.l10n_es_edi_verifactu_record_identifier
            if refunded_record_identifier and refunded_record_identifier['errors']:
                errors.extend(refunded_record_identifier['errors'])
            elif refunded_record:
                render_vals.update({
                    'FacturasRectificadas': {
                        'IDFacturaRectificada': {
                            'IDEmisorFactura': refunded_record_identifier['IDEmisorFactura'],
                            'NumSerieFactura': refunded_record_identifier['NumSerieFactura'],
                            'FechaExpedicionFactura': refunded_record_identifier['FechaExpedicionFactura'],
                        },
                    },
                })

        return render_vals, errors

    @api.model
    def _render_vals_previous_submissions(self, vals):
        # See "Sistemas Informáticos de Facturación y Sistemas VERI*FACTU" Version 1.0.0 - "Validaciones" p. 22 f.
        render_vals = {}
        errors = []

        verifactu_state = vals['verifactu_state']
        submission_rejected_before = vals['rejected_before']
        # `record_exists_at_AEAT` means the move / pos order is known at the AEAT
        record_exists_at_AEAT = verifactu_state in ('registered_with_errors', 'accepted')

        if vals['cancellation']:
            render_vals = {
                # A cancelled record can e.g. not exist at the AEAT when we switch to Veri*Factu after the original invoice was created
                'SinRegistroPrevio': 'S' if not record_exists_at_AEAT else 'N',
                'RechazoPrevio': 'S' if submission_rejected_before else 'N',
            }
        else:
            substitution = record_exists_at_AEAT  # TODO: case correction of record that does not exist at aeat yet
            if substitution and not record_exists_at_AEAT:
                # cases: ALTA DE SUBSANACIÓN SIN REGISTRO PREVIO, ALTA POR RECHAZO DE SUBSANACIÓN SIN REGISTRO PREVIO
                # This can i.e. happen when switching to Veri*Factu after the original invoice was created
                previously_rejected_state = 'X'
            elif submission_rejected_before:
                # cases: ALTA POR RECHAZO, ALTA POR RECHAZO DE SUBSANACIÓN
                previously_rejected_state = 'S' if substitution else 'X'
            else:
                # cases: ALTA, ALTA DE SUBSANACIÓN
                previously_rejected_state = None  # 'N'
            render_vals = {
                # We only put 'N' for 'Subsanacion' in case ALTA (we also put 'S' in case ALTA POR RECHAZO)
                'Subsanacion': 'S' if substitution or submission_rejected_before else 'N',
                'RechazoPrevio': previously_rejected_state,
            }

        return render_vals, errors

    @api.model
    def _render_vals_Destinatarios(self, vals):
        errors = []
        if vals['cancellation'] or vals['is_simplified']:
            return {}, errors

        partner = vals['partner']
        if not partner.name:
            errors.append(_("The partner does not have a name."))

        render_vals = {
            'Destinatarios': {
                'IDDestinatario': {
                    'NombreRazon': (partner.name or '')[:120],
                    ** partner._l10n_es_edi_get_partner_info(),
                }
            }
        }

        return render_vals, errors

    @api.model
    def _render_vals_monetary_amounts(self, vals):
        errors = []
        if vals['cancellation']:
            return {}, errors

        detalles = []
        tax_details = vals['tax_details']

        recargo_tax_details_key = {}  # dict (tax_key -> recargo_tax_key)
        for tax_details_per_record in tax_details['tax_details_per_record'].values():
            record_tax_details = tax_details_per_record['tax_details']
            main_key = None
            recargo_key = None
            # NOTE: we assume there is only a single (main_tax, recargo_tax) on a single line
            for key in record_tax_details:
                if key['with_recargo']:
                    main_key = key
                if key['l10n_es_type'] == 'recargo':
                    recargo_key = key
                if main_key and recargo_key:
                    break
            recargo_tax_details_key[main_key] = recargo_key

        sign = -1 if vals['move_type'] in ('out_refund', 'in_refund') else 1
        for key, tax_detail in tax_details['tax_details'].items():
            tax_type = tax_detail['l10n_es_type']
            if tax_type in ('recargo', 'ignore'):
                # Recargo taxes are only used in combination with another tax (a sujeto tax)
                # They will be handled when processing the remaining taxes
                continue

            exempt_reason = tax_detail['l10n_es_exempt_reason']  # only set if exempt

            tax_percentage = tax_detail['amount']
            base_amount = sign * tax_detail['base_amount']
            tax_amount = math.copysign(tax_detail['tax_amount'], base_amount)

            verifactu_tax_type = tax_detail['l10n_es_edi_verifactu_tax_type']
            clave_regimen = tax_detail['ClaveRegimen']
            if clave_regimen == '06' or verifactu_tax_type in ('02', '05'):
                base_amount_no_sujeto = 0
                base_amount_sujeto = base_amount
            else:
                base_amount_no_sujeto = base_amount
                base_amount_sujeto = None

            calificacion_operacion = None  # Reported if not tax-exempt;
            recargo_equivalencia = {}
            tax_type = tax_detail['l10n_es_type']
            if tax_type in ('sujeto', 'sujeto_agricultura', 'sujeto_isp'):
                calificacion_operacion = 'S2' if tax_type == 'sujeto_isp' else 'S1'
                if tax_detail['with_recargo']:
                    recargo_key = recargo_tax_details_key.get(key)
                    recargo_tax_detail = tax_details['tax_details'][recargo_key]
                    recargo_tax_percentage = recargo_tax_detail['amount']
                    recargo_tax_amount = math.copysign(recargo_tax_detail['tax_amount'], base_amount)
                    recargo_equivalencia.update({
                        'tax_percentage': recargo_tax_percentage,
                        'tax_amount': recargo_tax_amount,
                    })
            elif tax_type in ('no_sujeto', 'no_sujeto_loc'):
                calificacion_operacion = 'N2' if tax_type == 'no_sujeto_loc' else 'N1'
            elif tax_type == 'exento':
                pass  # exempt_reason set already
            else:
                # tax_type in ('no_deducible', 'retencion', 'dua')
                # TODO: subtract 'retencion' from total?
                pass

            recargo_percentage = recargo_equivalencia.get("tax_percentage")
            recargo_amount = recargo_equivalencia.get("tax_amount")

            detalle = {
                'Impuesto': verifactu_tax_type,
                'ClaveRegimen': clave_regimen,
                'CalificacionOperacion': calificacion_operacion,
                'OperacionExenta': exempt_reason,
                'TipoImpositivo': self._format_number_Tipo2_2(tax_percentage),
                'BaseImponibleOimporteNoSujeto': self._format_number_ImporteSgn12_2(base_amount_no_sujeto),
                'BaseImponibleACoste': self._format_number_ImporteSgn12_2(base_amount_sujeto),
                'CuotaRepercutida': self._format_number_ImporteSgn12_2(tax_amount),
                'TipoRecargoEquivalencia': self._format_number_Tipo2_2(recargo_percentage),
                'CuotaRecargoEquivalencia': self._format_number_ImporteSgn12_2(recargo_amount),
            }

            detalles.append(detalle)

        total_amount = sign * (tax_details['base_amount'] + tax_details['tax_amount'])
        tax_amount = sign * (tax_details['tax_amount'])

        total_amount_formatted = self._format_number_ImporteSgn12_2(total_amount)
        if total_amount_formatted != vals['identifier']['ImporteTotal']:
            errors.append(_("The computed 'ImporteTotal' does not match the 'Total Signed' amount on the invoice."))

        render_vals = {
            'Macrodato': 'S' if abs(total_amount) >= 100000000 else None,
            'Desglose': {
                'DetalleDesglose': detalles,
            },
            'CuotaTotal': self._format_number_ImporteSgn12_2(tax_amount),
            'ImporteTotal': total_amount_formatted,
        }

        return render_vals, errors

    @api.model
    def _get_db_identifier(self):
        database_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        return _sha256(database_uuid)

    @api.model
    def _render_vals_SistemaInformatico(self, vals):
        errors = []

        spanish_companies_on_db_count = self.env['res.company'].search_count([
            ('account_fiscal_country_id.code', '=', 'ES'),
        ], limit=2)

        render_vals = {
            'SistemaInformatico': {
                'NombreRazon': 'ODOO ERP SP SL',
                'NIF': 'B72659014',
                'NombreSistemaInformatico': odoo.release.product_name,
                'IdSistemaInformatico': '00',  # identifies Odoo the software as product of Odoo the company
                'Version': odoo.release.version,
                'NumeroInstalacion':  self._get_db_identifier(),
                'TipoUsoPosibleSoloVerifactu': 'S',
                'TipoUsoPosibleMultiOT': 'S',
                'IndicadorMultiplesOT': 'S' if spanish_companies_on_db_count > 1 else 'N',
            },
        }

        return render_vals, errors

    @api.model
    def _render_vals_dsig(self, vals):
        errors = []
        company = vals['company']
        record_uuid = str(uuid4())

        # Ensure a certificate is available.
        certificate = company.l10n_es_edi_verifactu_certificate_id
        if not certificate:
            errors.append(_("There is no certificate configured for Veri*Factu on the company."))
            return {'dsig': {}}, errors
        _cert_private, cert_public = certificate._decode_certificate()
        public_key_numbers = cert_public.public_key().public_numbers()

        # For e.g. facturae and tbai the authorities requirerd a specific order of the elements
        rfc4514_attr = dict(element.rfc4514_string().split("=", 1) for element in cert_public.issuer.rdns)
        # TODO: check; we may need to add other keys ('L', '2.5.4.97')
        #       ?: common function for l10n_es*?
        cert_issuer = ", ".join([f"{key}={rfc4514_attr[key]}" for key in ['CN', 'OU', 'O', 'C'] if key in rfc4514_attr])
        render_vals = {
            'dsig': {
                'signature_id': f"signature-{record_uuid}",
                'xmldsig_reference_id': f"xmldsig_reference_id-{record_uuid}",
                'signed_properties_id': f"signed_properties-{record_uuid}",
                'key_info_id': f"key_info_id-{record_uuid}",
                'x509_certificate': encodebytes(cert_public.public_bytes(encoding=serialization.Encoding.DER)).decode(),
                'rsa_key_modulus': encodebytes(_int_to_bytes(public_key_numbers.n)).decode(),
                'rsa_key_exponent': encodebytes(_int_to_bytes(public_key_numbers.e)).decode(),
                'signing_time': fields.Datetime.now().isoformat(),
                'signing_certificate_digest': b64encode(cert_public.fingerprint(hashes.SHA256())).decode(),
                'x509_issuer_name': cert_issuer,
                'x509_serial_number': cert_public.serial_number,
                'sigpolicy_url': "https://sede.administracion.gob.es/politica_de_firma_anexo_1.pdf",
                'sigpolicy_digest': b64encode(cert_public.fingerprint(hashes.SHA256())).decode(),
            }
        }

        return render_vals, errors

    @api.model
    def _update_render_vals_with_chaining_info(self, render_vals, previous_record_identifier=None):
        encadenamiento = {}
        predecessor = (previous_record_identifier or {})
        if predecessor:
            encadenamiento['RegistroAnterior'] = {
                'IDEmisorFactura': predecessor['IDEmisorFactura'],
                'NumSerieFactura': predecessor['NumSerieFactura'],
                'FechaExpedicionFactura': predecessor['FechaExpedicionFactura'],
                'Huella': predecessor['Huella'],
            }
        else:
            encadenamiento['PrimerRegistro'] = "S"

        main_render_vals = render_vals['vals'][render_vals['record_type']]
        main_render_vals['Encadenamiento'] = encadenamiento

        # During the `_fingerprint` computation the 'Encadenamiento' info needs to be set already
        main_render_vals.update({
            'TipoHuella': "01",  # "01" means SHA-256
            'Huella': self._fingerprint(render_vals['vals']),
        })

        return render_vals

    @api.model
    def _fingerprint(self, render_values):
        """
        Documentation: "Detalle de las especificaciones técnicas para generación de la huella o hash de los registros de facturación"
        """
        cancellation = "RegistroAnulacion" in render_values
        if cancellation:
            fingerprint_values = [
                ("IDEmisorFacturaAnulada", render_values["RegistroAnulacion"]["IDFactura"]["IDEmisorFacturaAnulada"]),
                ("NumSerieFacturaAnulada", render_values["RegistroAnulacion"]["IDFactura"]["NumSerieFacturaAnulada"]),
                ("FechaExpedicionFacturaAnulada", render_values["RegistroAnulacion"]["IDFactura"]["FechaExpedicionFacturaAnulada"]),
                ("Huella", _path_get(render_values, "RegistroAnulacion/Encadenamiento/RegistroAnterior/Huella") or ''),
                ("FechaHoraHusoGenRegistro", render_values["RegistroAnulacion"]["FechaHoraHusoGenRegistro"]),
            ]
            string = "&".join([f"{field}={value.strip()}" for (field, value) in fingerprint_values])
        else:
            fingerprint_values = [
                ("IDEmisorFactura", render_values["RegistroAlta"]["IDFactura"]["IDEmisorFactura"]),
                ("NumSerieFactura", render_values["RegistroAlta"]["IDFactura"]["NumSerieFactura"]),
                ("FechaExpedicionFactura", render_values["RegistroAlta"]["IDFactura"]["FechaExpedicionFactura"]),
                ("TipoFactura", render_values["RegistroAlta"]["TipoFactura"]),
                ("CuotaTotal", render_values["RegistroAlta"]["CuotaTotal"]),
                ("ImporteTotal", render_values["RegistroAlta"]["ImporteTotal"]),
                ("Huella", _path_get(render_values, "RegistroAlta/Encadenamiento/RegistroAnterior/Huella") or ''),
                ("FechaHoraHusoGenRegistro", render_values["RegistroAlta"]["FechaHoraHusoGenRegistro"]),
            ]
            string = "&".join([f"{field}={value.strip()}" for (field, value) in fingerprint_values])
        return _sha256(string)

    @api.model
    def _render_xml_node(self, render_vals):
        errors = []

        # Render
        try:
            xml = self.env['ir.qweb']._render('l10n_es_edi_verifactu.verifactu_registro_factura', render_vals)
        except Exception as e:
            errors.append(_("Error during the rendering of the XML document: %s", e))
            return None, errors
        xml_node = cleanup_xml_node(xml, remove_blank_nodes=False, indent_space="    ")

        # Sign the rendered XML (modify <ds:Signature> node appropriately)
        company = render_vals['company']
        certificate = company.l10n_es_edi_verifactu_certificate_id
        if not certificate:
            errors.append(_("There is no certificate configured for Veri*Factu on the company."))
            return None, errors
        cert_private, _cert_public = certificate._decode_certificate()
        signature_node = xml_node.find('*/ds:Signature', namespaces=NS_MAP)
        signature_node = cleanup_xml_node(signature_node, remove_blank_nodes=False)
        signed_info_node = signature_node.find('ds:SignedInfo', namespaces=NS_MAP)
        _reference_digests(signed_info_node)
        signature = cert_private.sign(_canonicalize_node(signed_info_node), padding.PKCS1v15(), hashes.SHA256())
        signature_node.find('ds:SignatureValue', namespaces=NS_MAP).text = encodebytes(signature)

        return xml_node, errors

    @api.model
    def _batch_record_xmls(self, xml_list, incident=False):
        errors = []

        company = self.env.company
        company_values = company._get_l10n_es_edi_verifactu_values()
        company_NIF = company_values['NIF']
        if not company_NIF or len(company_NIF) != 9:  # NIFType
            errors.append(_("The NIF '%(company_nif)s' of the company is not exactly 9 characters long",
                            company_nif=company_NIF))
        cabecera = {
            'ObligadoEmision': {
                'NombreRazon': company_values['name'],
                'NIF': company_NIF,
            },
            'RemisionVoluntaria': {
                'Incidencia': 'S' if incident else 'N',
            },
        }

        vals = {
            'vals': {'Cabecera': cabecera},
            '_path_get': _path_get,
        }
        batch_xml = self.env['ir.qweb']._render('l10n_es_edi_verifactu.verifactu_record_registration', vals)
        batch_xml_node = cleanup_xml_node(batch_xml, remove_blank_nodes=False, indent_space="    ")
        for xml in xml_list:
            batch_xml_node.append(etree.fromstring(xml))

        if errors:
            return None, errors

        batch_xml = etree.tostring(batch_xml_node, xml_declaration=True, encoding='UTF-8')
        return batch_xml, errors

    @api.model
    def _build_soap_request_xml(self, edi_xml):
        envelope_string = self.env['ir.qweb']._render('l10n_es_edi_verifactu.soap_request_verifactu')
        envelope = etree.fromstring(envelope_string)
        body = envelope.find(".//soapenv:Body", namespaces=NS_MAP)
        body.append(etree.fromstring(edi_xml))
        return etree.tostring(envelope)
