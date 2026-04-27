# -*- coding: utf-8 -*-

import base64
import logging
import re
import hashlib
import requests
import urllib.parse
from lxml import etree
from json.decoder import JSONDecodeError
from markupsafe import Markup
from pytz import timezone
from datetime import datetime

from odoo import api, models, fields
from odoo.exceptions import UserError
from odoo.tools import _, LazyTranslate

_lt = LazyTranslate(__name__)
_logger = logging.getLogger(__name__)

DEFAULT_PE_DATE_FORMAT = '%Y-%m-%d'
PE_TRANSFER_REASONS = [
    ('01', 'Sale'),
    ('03', 'Sale with delivery to third parties'),
    ('04', 'Transfer between establishments of the same company'),
    ('05', 'Consignment'),
    ('13', 'Others'),
    ('14', "Sale subject to buyer's confirmation"),
    ('17', 'Transfer of goods for transformation'),
    ('18', 'Itinerant issuer transfer CP'),
]
PE_RELATED_DOCUMENT = [
    ('01', 'Factura'),
    ('03', 'Boleta de Venta'),
    ('04', 'Liquidación de Compra'),
    ('09', 'Guía de Remisión Remitente'),
    ('12', 'Ticket o cinta emitido por máquina registradora'),
    ('31', 'Guía de Remisión Transportista'),
    ('48', 'Comprobante de Operaciones - Ley N° 29972'),
    ('49', 'Constancia de Depósito - IVAP (Ley 28211)'),
    ('50', 'Declaración Aduanera de Mercancías'),
    ('52', 'Declaración Simplificada (DS)'),
    ('65', 'Autorización de Circulación para transportar MATPEL - Callao'),
    ('66', 'Autorización de Circulación para transporte de carga y mercancías en Lima Metropolitana'),
    ('67', 'Permiso de Operación Especial para el servicio de transporte de MATPEL - MTC'),
    ('68', 'Habilitación Sanitaria de Transporte Terrestre de Productos Pesqueros y Acuícolas'),
    ('69', 'Permiso / Autorización de operación de transporte de mercancías'),
    ('71', 'Resolución de Adjudicación de bienes - SUNAT'),
    ('72', 'Resolución de Comiso de bienes - SUNAT'),
    ('73', 'Guía de Transporte Forestal o de Fauna - SERFOR'),
    ('74', 'Guía de Tránsito - SUCAMEC'),
    ('75', 'Autorización para operar como empresa de Saneamiento Ambiental - MINSA'),
    ('76', 'Autorización para manejo y recojo de residuos sólidos peligrosos y no peligrosos'),
    ('77', 'Certificado fitosanitario la movilización de plantas, productos vegetales, y otros artículos reglamentados'),
    ('78', 'Registro Único de Usuarios y Transportistas de Alcohol Etílico'),
    ('80', 'Constancia de Depósito - Detracción'),
    ('81', 'Código de autorización emitida por el SCOP'),
    ('82', 'Declaración jurada de mudanza'),
]
ERROR_MESSAGES = {
    "request": _lt("There was an error communicating with the SUNAT service. Details:"),
    "json_decode": _lt("Could not decode the response received from SUNAT. Details:"),
    "unzip": _lt("Could not decompress the ZIP file received from SUNAT."),
    "processing": _lt("The delivery guide is being processed by SUNAT. Click on 'Retry' to refresh the state."),
    "duplicate": _lt("A delivery guide with this number is already registered with SUNAT. Click on 'Retry' to try sending with a new number."),
    "response_code": _lt("SUNAT returned an error code. Details:"),
    "response_unknown": _lt("Could not identify content in the response retrieved from SUNAT. Details:"),
}


class Picking(models.Model):
    _inherit = 'stock.picking'

    l10n_pe_edi_transport_type = fields.Selection(
        string='Transport type',
        selection=[
            ('01', 'Public transport'),
            ('02', 'Private transport'),
        ],
        copy=False,
        help="Peru: Select if transport is internal (private: own company) or external (public: transport company).",
    )
    l10n_pe_edi_status = fields.Selection(
        selection=[
            ('to_send', 'To Send'),
            ('sent', 'Sent'),
        ],
        string='Delivery Guide Status (PE)',
        copy=False)
    country_code = fields.Char(
        related='company_id.country_id.code',
        depends=['company_id.country_id'])
    l10n_pe_edi_error = fields.Html(
        string="EDI error details",
        copy=False)
    l10n_pe_edi_ticket_number = fields.Char(
        string="Ticket Number",
        readonly=True, tracking=True, copy=False,
        help="Number issued by SUNAT when sending the delivery guide, used to retrieve the CDR.",
    )
    l10n_pe_edi_reason_for_transfer = fields.Selection(
        selection=PE_TRANSFER_REASONS,
        string='Reason for transfer',
        # Used compute method instead of a default to only set the value if the transport type is set
        compute='_compute_l10n_pe_edi_reason_for_transfer',
        store=True,
        readonly=False)
    l10n_pe_edi_departure_start_date = fields.Date(
        string='Transfer Start Date',
        help='The date when the transfer is expected to start.'
    )
    l10n_pe_edi_vehicle_id = fields.Many2one(
        string='Vehicle',
        comodel_name='l10n_pe_edi.vehicle',
        copy=False,
        check_company=True)
    l10n_pe_edi_operator_id = fields.Many2one(
        string='Operator',
        comodel_name='res.partner',
        compute='_compute_l10n_pe_edi_operator',
        store=True,
        readonly=False,
        check_company=True,
        help='The transport provider in case of public transport, else the internal operator.',
    )
    l10n_latam_document_number = fields.Char(
        string='Delivery Guide Number',
        copy=False,
        help="The number of the related document.")
    l10n_pe_edi_observation = fields.Text(
        string='Observation',
        help='Additional information to be displayed in the Delivery Slip in order to clarify or '
             'complement information about the transferred products. Maximum length: 250 characters.'
    )
    l10n_pe_edi_document_number = fields.Char(
        string="Related Document Number",
        copy=False,
    )
    l10n_pe_edi_related_document_type = fields.Selection(
        selection=PE_RELATED_DOCUMENT,
        string="Related Document Type",
        copy=False,
        help="The type of the related document."
    )
    l10n_pe_edi_content = fields.Binary(
        string="Delivery guide content",
        compute='_l10n_pe_edi_compute_edi_content',
        compute_sudo=True)

    def _l10n_pe_edi_compute_edi_content(self):
        for picking in self:
            picking.l10n_pe_edi_content = base64.b64encode(picking._l10n_pe_edi_create_delivery_guide())

    def l10n_pe_edi_action_clear_error(self):
        for record in self:
            record.l10n_pe_edi_error = False

    def l10n_pe_edi_action_download(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url':  '/web/content/stock.picking/%s/l10n_pe_edi_content' % self.id
        }

    @api.depends('l10n_pe_edi_vehicle_id')
    def _compute_l10n_pe_edi_operator(self):
        for record in self:
            record.l10n_pe_edi_operator_id = record.l10n_pe_edi_vehicle_id.operator_id or record.l10n_pe_edi_operator_id

    @api.depends('l10n_pe_edi_transport_type')
    def _compute_l10n_pe_edi_reason_for_transfer(self):
        """ We use a compute to avoid setting 01 where the delivery guide is not applied """
        for record in self:
            record.l10n_pe_edi_reason_for_transfer = record.l10n_pe_edi_reason_for_transfer or '01'

    # Validation

    def _l10n_pe_edi_check_required_data(self):
        """Some attributes are required to allow generate the XML file, that attributes are review here to avoid SUNAT
        errors."""
        for record in self:
            errors = record._l10n_pe_edi_generate_missing_data_error_list()
            if not errors:
                continue
            raise UserError('%s\n\n%s' % (_("Invalid picking configuration:"), '\n'.join(errors)))

    def _l10n_pe_edi_generate_missing_data_error_list(self):
        """ Check that all the required data is present before generating the delivery guide.
            Based on SUNAT resolution 000123-2022 (published 2022-07-12), pages 48-54,
            and on the list of checks published at
            https://cpe.sunat.gob.pe/sites/default/files/inline-files/ValidacionesGREv20221020_publicacion.xlsx
        """
        errors = []
        if not self.partner_id:
            errors.append(_('Please set a Delivery Address as the delivery guide needs one.'))
        if not self.partner_id.l10n_pe_district:
            errors.append(_('The client must have a defined district.'))
        if not self.l10n_pe_edi_transport_type:
            errors.append(_('You must select a transport type to generate the delivery guide.'))
        if not self.l10n_pe_edi_reason_for_transfer:
            errors.append(_('You must choose the reason for the transfer.'))
        if not self.l10n_pe_edi_departure_start_date:
            errors.append(_('You must choose the start date of the transfer.'))
        if self.l10n_pe_edi_transport_type == '02' and not self.l10n_pe_edi_vehicle_id:
            errors.append(_('You must choose the transfer vehicle.'))
        if not self.company_id.partner_id.l10n_latam_identification_type_id:
            errors.append(_('A document type is required for the company.'))
        if not self.company_id.partner_id.vat:
            errors.append(_('An identification number is required for the company.'))
        warehouse_address = self.picking_type_id.warehouse_id.partner_id or self.company_id.partner_id
        if not warehouse_address.l10n_pe_district:
            errors.append(_('The origin address must have a defined district.'))
        if not warehouse_address.street:
            errors.append(_('The origin address must have a defined street.'))
        if self.company_id.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code != "6":
            errors.append(_("The company's ID type must be set to RUC on the company contact page."))
        if (self.l10n_pe_edi_transport_type == '02' and not self.l10n_pe_edi_operator_id and not self.l10n_pe_edi_vehicle_id.is_m1l
            or self.l10n_pe_edi_transport_type == '01' and not self.l10n_pe_edi_operator_id):
            errors.append(_("You must choose the transfer operator."))
        return errors

    def button_validate(self):
        picking = super().button_validate()
        self.l10n_pe_edi_departure_start_date = fields.Datetime.now()
        return picking

    def _l10n_pe_edi_create_delivery_guide(self):
        """ Generate the delivery guide XML. """
        values = self._l10n_pe_edi_get_delivery_guide_values()
        return self.env['ir.qweb']._render('l10n_pe_edi_stock.sunat_guiaremision', values).encode()

    def _l10n_pe_edi_get_delivery_guide_values(self):
        """ Used to generate the XML file that will be send to stamp in SUNAT
        The document number comes from the sequence with code "l10n_pe_edi_stock.stock_picking_sunat_sequence", and
        will be generated automatically if this not exists."""
        self.ensure_one()

        def format_date(date):
            return date.strftime(DEFAULT_PE_DATE_FORMAT) if date else ''

        def format_float(val, digits=2):
            return '%.*f' % (digits, val)

        date_pe = datetime.now(tz=timezone('America/Lima')).date()
        return {
            'date_issue': date_pe.strftime(DEFAULT_PE_DATE_FORMAT),
            'time_issue': date_pe.strftime("%H:%M:%S"),
            'l10n_pe_edi_observation': self.l10n_pe_edi_observation or 'Guía',
            'record': self,
            'weight_uom': self.env['product.template']._get_weight_uom_id_from_ir_config_parameter(),
            'warehouse_address': self.picking_type_id.warehouse_id.partner_id or self.company_id.partner_id,
            'document_number': self.l10n_latam_document_number,
            'format_date': format_date,
            'moves': self.move_ids.filtered(lambda ml: ml.quantity > 0),
            'reason_for_transfer': dict(PE_TRANSFER_REASONS)[self.l10n_pe_edi_reason_for_transfer],
            'format_float': format_float,
            'related_document': dict(PE_RELATED_DOCUMENT)[self.l10n_pe_edi_related_document_type] if self.l10n_pe_edi_related_document_type else False,
        }

    def action_send_delivery_guide(self):
        """Check required fields, generate the XML delivery guide, and send it to SUNAT"""
        self._check_company()
        self._l10n_pe_edi_check_required_data()
        for record in self:
            # == Generate a document number ==
            if not record.l10n_latam_document_number:
                sunat_sequence = self.env['ir.sequence'].search([
                    ('code', '=', 'l10n_pe_edi_stock.stock_picking_sunat_sequence'),
                    ('company_id', '=', record.company_id.id)], limit=1)
                if not sunat_sequence:
                    sunat_sequence = self.env['ir.sequence'].sudo().create({
                        'name': 'Stock Picking Sunat Sequence %s' % record.company_id.name,
                        'code': 'l10n_pe_edi_stock.stock_picking_sunat_sequence',
                        'padding': 8,
                        'company_id': record.company_id.id,
                        'prefix': 'T001-',
                        'number_next': 1,
                    })
                record.l10n_latam_document_number = sunat_sequence.next_by_id()

            # == Send the delivery guide ==
            record.l10n_pe_edi_status = 'to_send'
            edi_str = record._l10n_pe_edi_create_delivery_guide()
            res = record._l10n_pe_edi_sign(edi_str)

            if 'error' in res:
                record.l10n_pe_edi_error = res['error']
                continue

            # == Create the attachments ==
            if res.get('cdr'):
                attachments = self.env['ir.attachment'].create([
                    {
                        'name': '%s-09-%s.xml' % (record.company_id.vat, record.l10n_latam_document_number),
                        'res_model': record._name,
                        'res_id': record.id,
                        'type': 'binary',
                        'raw': edi_str,
                        'mimetype': 'application/xml',
                        'description': _('Delivery Guide for transfer %s', record.name),
                    },
                    {
                        'name': 'cdr-%s-09-%s.xml' % (record.company_id.vat, record.l10n_latam_document_number),
                        'res_model': record._name,
                        'res_id': record.id,
                        'type': 'binary',
                        'raw': res['cdr'],
                        'mimetype': 'application/xml',
                        'description': _('Delivery guide receipt (CDR) for transfer %s', record.name)
                    }
                ])
                message = _("The Delivery Guide was successfully signed by SUNAT.")
                record._message_log(body=message, attachment_ids=attachments.ids)
                record.write({'l10n_pe_edi_error': False, 'l10n_pe_edi_status': 'sent'})

    def _l10n_pe_edi_get_serie_folio(self):
        number_match = [rn for rn in re.finditer(r'\d+', (self.l10n_latam_document_number or '').replace(' ', ''))]
        serie = self.l10n_latam_document_number[:number_match[-1].start()].replace('-', '').replace(' ', '') or None
        folio = number_match[-1].group() or None
        return {'serie': serie, 'folio': folio}

    def _l10n_pe_edi_sign(self, edi_str):
        """ Send a delivery guide to SUNAT, and retrieve the CDR.
            This method implements the retry mechanism for an invalid token.

            The method uses the cached authentication token returned by
            _l10n_pe_edi_get_token. If either the sending or the retrieving fails due
            to an expired token, a new token is requested and we retry.

            :param edi_str: the content of the XML file containing the delivery guide """
        res_get_token = self._l10n_pe_edi_get_token()
        if "error" in res_get_token:
            return res_get_token
        token = res_get_token.get("token")
        result = self._l10n_pe_edi_sign_steps(edi_str, token)

        # If the token has expired, the error returned is 401 Client Error: clear the token and retry again.
        if result.get("error_reason") == "unauthorized":
            res_get_token = self._l10n_pe_edi_get_token(force_request=True)
            if "error" in res_get_token:
                return res_get_token
            token = res_get_token.get("token")
            return self._l10n_pe_edi_sign_steps(edi_str, token)
        return result

    def _l10n_pe_edi_sign_steps(self, edi_str, token):
        """ Send the delivery guide to SUNAT, then retrieve the CDR.

            :param edi_str: the content of the XML file containing the delivery guide
            :param token: the SUNAT authentication token """
        # Step 1: send the delivery guide, unless we already sent it and are still waiting for a response.
        if not self.l10n_pe_edi_ticket_number:
            res_send_delivery_guide = self._l10n_pe_edi_send_delivery_guide(edi_str, token)
            if "error" in res_send_delivery_guide:
                return res_send_delivery_guide
            else:
                self.l10n_pe_edi_ticket_number = res_send_delivery_guide["ticket_number"]

        # Step 2: retrieve the CDR using the ticket number.
        res_get_cdr = self._l10n_pe_edi_get_cdr(self.l10n_pe_edi_ticket_number, token)
        if "error" in res_get_cdr:
            # If the delivery guide was rejected by SUNAT, set the ticket number to False. In all other
            # error cases (e.g. connection errors), keep the ticket number as we may still retrieve the CDR.
            if res_get_cdr.get("error_reason") in ("rejected", "duplicate"):
                self.l10n_pe_edi_ticket_number = False
            if res_get_cdr.get("error_reason") == "duplicate":
                self.l10n_latam_document_number = False
            return res_get_cdr

        return {"cdr": res_get_cdr["cdr"]}

    def _l10n_pe_edi_get_sunat_guia_credentials(self):
        """ Returns the credentials to be used with the SUNAT authentication service. """
        company = self.company_id.sudo()
        if not company.l10n_pe_edi_stock_client_id:
            return {"error": _("No Client ID found for company %s.", company.display_name)}
        credentials = {
            "access_id": company.l10n_pe_edi_stock_client_id,
            "access_key": company.l10n_pe_edi_stock_client_secret,
            "client_id": company.l10n_pe_edi_stock_client_username,
            "password": company.l10n_pe_edi_stock_client_password,
            "login_url": "https://api-seguridad.sunat.gob.pe/v1/clientessol/%s/oauth2/token/",
        }
        return credentials

    def _l10n_pe_edi_request_token(self, credentials):
        """ Request an authentication token from the SUNAT authentication service.
            The token can then be used in requests to the endpoints for sending the
            delivery guide and for requesting the CDR. """
        headers = {
            "Accept": "application/json",
        }
        data = {
            "grant_type": "password",
            "scope": "https://api-cpe.sunat.gob.pe",
            "client_id": credentials["access_id"],
            "client_secret": credentials["access_key"],
            "username": credentials["client_id"],
            "password": credentials["password"],
        }
        try:
            response = requests.post(credentials["login_url"] % urllib.parse.quote_plus(credentials["access_id"]), data=data, headers=headers, timeout=20)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return {"error": str(Markup("%s<br/>%s") % (str(ERROR_MESSAGES["request"]), e))}

        try:
            response_json = response.json()
        except JSONDecodeError as e:
            return {"error": str(Markup("%s<br/>%s") % (str(ERROR_MESSAGES["json_decode"]), e))}

        if "error" in response_json or "error_description" in response_json:
            error_msg = str(Markup("%s<br/>%s: %s") % (str(ERROR_MESSAGES["response_code"]), response_json.get("error", ""), response_json.get("error_description", "")))
            return {"error": error_msg}
        if not response_json.get("access_token"):
            return {"error": str(Markup("%s<br/>%s") % (str(ERROR_MESSAGES["response_unknown"]), response_json))}

        token = response_json["access_token"]
        return {"token": token}

    def _l10n_pe_edi_get_token(self, force_request=False):
        """ Return the authentication token for the SUNAT delivery guide service.

            The token is cached in `company.l10n_pe_edi_stock_token`.

            :param force_request: if True, will request a new token. """
        existing_token = self.sudo().company_id.l10n_pe_edi_stock_token
        if not force_request and existing_token:
            return {"token": existing_token}

        credentials = self._l10n_pe_edi_get_sunat_guia_credentials()
        if "error" in credentials:
            return credentials
        res_request_token = self._l10n_pe_edi_request_token(credentials)
        if "error" in res_request_token:
            return res_request_token

        token = res_request_token.get("token")
        self.sudo().company_id.l10n_pe_edi_stock_token = token
        return res_request_token

    def _l10n_pe_edi_send_delivery_guide(self, edi_str, token):
        """ Send a delivery guide to SUNAT via the REST API.

            SUNAT provides a ticket number in its response, which can be used to
            retrieve the CDR once the SUNAT service has finished processing the
            delivery guide.

            :param edi_str: the content of the XML file containing the delivery guide
            :param token: the SUNAT authentication token """
        self.ensure_one()
        headers = {
            'Authorization': "Bearer " + token,
            'Content-Type': "Application/json",
        }
        edi_filename = "%s-09-%s" % (self.company_id.vat, self.l10n_latam_document_number)
        url = "https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/%s" % urllib.parse.quote_plus(edi_filename)

        # SUNAT expects the XML to be encoded using ISO-8859-1.
        edi_str = etree.tostring(etree.fromstring(edi_str), xml_declaration=True, encoding='ISO-8859-1')
        zip_file = self.env.ref('l10n_pe_edi.edi_pe_ubl_2_1')._l10n_pe_edi_zip_edi_document([('%s.xml' % edi_filename, edi_str)])
        data = {
            "archivo": {
                "nomArchivo": "%s.zip" % edi_filename,
                "arcGreZip": base64.b64encode(zip_file).decode(),
                "hashZip": hashlib.sha256(zip_file).hexdigest(),
            }
        }
        try:
            response = requests.post(url, json=data, headers=headers, verify=True, timeout=20)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            to_return = {"error": str(Markup("%s<br/>%s") % (str(ERROR_MESSAGES["request"]), e))}
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 401:
                to_return.update({"error_reason": "unauthorized"})
            return to_return
        try:
            response_json = response.json()
        except JSONDecodeError as e:
            return {"error": str(Markup("%s<br/>%s") % (str(ERROR_MESSAGES["json_decode"]), e))}

        if isinstance(response_json.get("errors"), list) and len(response_json["errors"]) > 0 and isinstance(response_json["errors"][0], dict):
            code = response_json["errors"][0].get("cod", "")
            msg = response_json["errors"][0].get("msg", "")
            return {"error": str(Markup("%s<br/>%s: %s") % (str(ERROR_MESSAGES["response_code"]), code, msg))}
        if not response_json.get("numTicket"):
            return {"error": str(Markup("%s<br/>%s") % (str(ERROR_MESSAGES["response_unknown"]), response_json))}

        return {"ticket_number": response_json["numTicket"]}

    def _l10n_pe_edi_get_cdr(self, ticket_number, token):
        """ Retrieve the CDR (confirmation of receipt) for a delivery guide that was sent.

            :param ticket_number: the ticket number obtained when sending the delivery guide
            :param token: the SUNAT authentication token """
        headers = {
            'Authorization': "Bearer " + token,
            'Content-Type': "Application/json",
        }
        url = 'https://api-cpe.sunat.gob.pe/v1/contribuyente/gem/comprobantes/envios/%s' % urllib.parse.quote_plus(ticket_number)
        try:
            response = requests.get(url, params={'numTicket': ticket_number}, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            to_return = {"error": str(Markup("%s<br/>%s") % (str(ERROR_MESSAGES["request"]), e))}
            if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 401:
                to_return.update({"error_reason": "unauthorized"})
            return to_return
        try:
            response_json = response.json()
        except JSONDecodeError as e:
            return {"error": str(Markup("%s<br/>%s") % (str(ERROR_MESSAGES["json_decode"]), e))}

        if response_json.get("codRespuesta") == "98":
            error_msg = str(ERROR_MESSAGES["processing"])
            return {"error": error_msg, "error_reason": "processing"}
        if response_json.get("error"):
            code = response_json["error"].get("numError", "")
            msg = response_json["error"].get("desError", "")
            if code == "1033":
                error_msg = str(ERROR_MESSAGES["duplicate"])
                return {"error": error_msg, "error_reason": "duplicate"}
            else:
                return {"error": str(Markup("%s %s: %s") % (str(ERROR_MESSAGES["response_code"]), code, msg)), "error_reason": "rejected"}
        if not response_json.get("arcCdr") or response_json.get("codRespuesta") != "0":
            if "codRespuesta" in response_json:
                return {"error": str(Markup("%s %s") % (str(ERROR_MESSAGES["request"]), response_json["codRespuesta"])), "error_reason": "rejected"}
            else:
                return {"error": str(Markup("%s<br/>%s") % (str(ERROR_MESSAGES["response_unknown"]), response_json))}

        cdr_zip = response_json["arcCdr"]

        try:
            cdr = self.env["account.edi.format"]._l10n_pe_edi_unzip_edi_document(base64.b64decode(cdr_zip))
        except Exception as e:
            return {"error": str(Markup("%s<br/>%s") % (str(ERROR_MESSAGES["unzip"]), e))}

        return {"cdr": cdr}

    def _l10n_pe_edi_get_qr(self):
        """ Retrieve the CDR's QR code. """
        self.ensure_one()
        edi_filename = 'cdr-%s-09-%s.xml' % (
            self.company_id.vat,
            (self.l10n_latam_document_number or '').replace(' ', ''),
        )
        attachment = self.env['ir.attachment'].search([
            ('name', '=', edi_filename),
            ('res_id', '=', self.id),
            ('res_model', '=', self._name)])
        if not attachment:
            return ''
        edi_attachment_str = attachment.raw
        edi_tree = etree.fromstring(edi_attachment_str)
        element = edi_tree.xpath('//cbc:DocumentDescription',
                                 namespaces={'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2'})
        if not element:
            return ''
        return element[0].text
