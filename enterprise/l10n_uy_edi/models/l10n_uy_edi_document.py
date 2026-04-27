import base64
import logging
from lxml import etree
import re
from requests.exceptions import Timeout, ConnectionError, HTTPError
import textwrap

from odoo import _, api, fields, models, tools

from odoo.tools import float_compare
from odoo.tools.zeep import Client, Settings
from odoo.tools.zeep.wsse.username import UsernameToken


RESPONSE_CODE_TO_STATE = {
    # Irreversible states
    "00": "accepted",  # Petición aceptada y procesada
    "06": "accepted",  # CFE observado por DGI
    "11": "received",  # CFE aceptado por UCFE, en espera de respuesta de DGI
    "05": "rejected",  # CFE rechazado por DGI (Anulado). Do not sent again to UCFE neither create CREDIT NOTES

    # Errors
    "01": "error",  # Petición denegada

    # Related to configuration of UCFE. Please fix it and then try to send CFE again
    "03": "error",  # Comercio inválido
    "89": "error",  # Terminal inválida

    # UCFE does not receive the CFE
    "12": "error",  # Requerimiento inválido
    "94": "error",
    "99": "error",  # Sesión no iniciada

    "30": "error",  # Error en formato (Format error on the query)
    "31": "error",  # Error en formato de CFE (Fortmat error of the xml)
    "96": "error",  # Error en sistema (UFCE Internal error). Example: Bugs, down database, disk full, etc.
}

_logger = logging.getLogger(__name__)


class L10nUyEdiDocument(models.Model):
    _name = "l10n_uy_edi.document"
    _description = "Electronic Fiscal Document (CFE - UY)"
    _rec_name = "l10n_latam_document_number"

    uuid = fields.Char(
        string="Key or UUID CFE",
        copy=False,
        readonly=True,
        help="Unique identification per CFE in UCFE: concatenation of the model name initials plus the record id",
    )
    request_datetime = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    state = fields.Selection(
        string="CFE Status",
        selection=[
            ("received", "Waiting response from DGI"),
            ("accepted", "CFE Accepted by DGI"),
            ("rejected", "CFE Rejected by DGI"),
            ("error", "ERROR")
        ],
        copy=False,
        readonly=True,
        help="State of the electronic document",
    )
    move_id = fields.Many2one("account.move", readonly=True)
    message = fields.Text(
        string="Uruguay E-Invoice Error",
        copy=False,
        readonly=True,
        help="error details for CFEs in the 'error' state.",
    )
    # Attachment
    attachment_id = fields.Many2one(
        "ir.attachment",
        compute=lambda self: self._compute_linked_attachment_id("attachment_id", "attachment_file"),
        depends=["attachment_file"],
    )
    attachment_file = fields.Binary(copy=False, attachment=True)

    # Related fields from origin record
    l10n_latam_document_type_id = fields.Many2one(
        "l10n_latam.document.type", "Document Type", related=False, compute="_compute_from_origin"
    )
    l10n_latam_document_number = fields.Char(related=False, compute="_compute_from_origin")
    company_id = fields.Many2one("res.company", related=False, compute="_compute_from_origin")
    partner_id = fields.Many2one("res.partner", related=False, compute="_compute_from_origin")

    # Compute methods

    @api.depends('move_id.l10n_latam_document_number', 'move_id.l10n_latam_document_type_id', 'move_id.company_id', 'move_id.partner_id')
    def _compute_from_origin(self):
        for doc in self:
            if doc.move_id:
                doc.l10n_latam_document_number = doc.move_id.l10n_latam_document_number
                doc.l10n_latam_document_type_id = doc.move_id.l10n_latam_document_type_id
                doc.company_id = doc.move_id.company_id
                doc.partner_id = doc.move_id.partner_id

    def _compute_linked_attachment_id(self, attachment_field, binary_field):
        """Helper to retrieve Attachment from Binary fields
        This is needed because fields.Many2one("ir.attachment") makes all
        attachments available to the user.
        """
        attachments = self.env["ir.attachment"].search([
            ("res_model", "=", self._name),
            ("res_id", "in", self.ids),
            ("res_field", "=", binary_field)
        ])
        edi_vals = {att.res_id: att for att in attachments}
        for edi_doc in self:
            edi_doc[attachment_field] = edi_vals.get(edi_doc._origin.id, False)

    # Action Methods

    def action_download_file(self):
        """ Be able to download the XML file related to this EDI document

        * If document received/accepted it will be the valid CFE
        * If document is in error state will download the preview of the XML that we are trying to send to
        Uruware-DGI """
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.attachment_id.id}?download=true",
        }

    def action_update_dgi_state(self):
        """ Call endpoint that return the updated state of the EDI document on DGI.
        Make a query to UCFE in order to know if DGI give us a definitive state for the invoice (Used only for all the
        electronic invoices that are state waiting DGI response). Only applies to customer invoices

        Will return None and the result will be update the cfe_state field (error field
        if applies)"""
        for edi_doc in self:
            if edi_doc.move_id.journal_id.type == 'sale':
                result = edi_doc._ucfe_inbox("360", {"Uuid": edi_doc.uuid})
            else:
                document_number = re.search(r"([A-Z]*)([0-9]*)", edi_doc.move_id.l10n_latam_document_number).groups()
                result = edi_doc._ucfe_inbox("650", {
                    "TipoCfe": edi_doc.move_id.l10n_latam_document_type_id_code,
                    "Serie": document_number[0],
                    "NumeroCfe": document_number[1],
                    "RutEmisor": edi_doc.move_id.partner_id.vat})
            edi_doc._update_cfe_state(result)

    # Extended methods

    def unlink(self):
        self.attachment_id.unlink()
        return super().unlink()

    def _get_fields_to_detach(self):
        # EXTENDS account
        fields_list = super()._get_fields_to_detach()
        fields_list.append('attachment_file')
        return fields_list

    # Helpers

    def _can_edit(self):
        """ The CFE cannot be modified once processed by DGI """
        self.ensure_one()
        return self.state not in ["accepted", "rejected", "received"]

    @api.model
    def _cfe_needs_partner_info(self, move):
        """ Whether the partner address is required.
        For e-ticket, if the amount is less than 5000 UYI, it's optional. """
        move.ensure_one()
        document_type = int(move.l10n_latam_document_type_id.code)
        min_amount = self._get_minimum_legal_amount(move.company_id, move.date)
        return (
            document_type in [101, 102, 103, 131, 132, 133]
            and float_compare(abs(move.amount_total_signed), min_amount, precision_digits=2) == 1
        )

    @api.model
    def _validate_credentials(self, company):
        """ Make a ECHO test to UCFE to see if the server is running and that the environment
        params have been properly configured """
        error = self.env["l10n_uy_edi.document"]._is_connection_info_incomplete(company)
        if error:
            return error

        company_missing_data = company._l10n_uy_edi_validate_company_data()
        if company_missing_data:
            return _(
                "Not able to check credentials, first complete your company data:\n\t- %(errors)s",
                errors="\n\t- ".join(company_missing_data),
            )

        now = fields.Datetime.now()
        result = self._ucfe_inbox("820", {"FechaReq": now.date().strftime("%Y%m%d"), "HoraReq": now.strftime("%H%M%S")})
        if errors := result.get("errors"):
            return "\n".join(errors)
        return ""

    @api.model
    def _check_field_size(self, field_name, res, limit):
        errors = []
        if res and len(res) > limit:
            errors.append(_(
                "We cannot generate the CFE because the field length is not valid.\nCheck if disclosure/addenda are"
                " being applied.\n\n * Name of the field: %(xml_tag)s (%(xml_tag_len)s)\n * Content:"
                " (%(value_len)s)\n %(value_content)s",
                xml_tag=field_name, xml_tag_len=limit, value_len=len(res), value_content=res))
        return errors

    @api.model
    def _get_cfe_tag(self, move):
        move.ensure_one()
        cfe_code = int(move.l10n_latam_document_type_id.code)
        if cfe_code in [101, 102, 103, 201]:
            return "eTck"
        elif cfe_code in [111, 112, 113]:
            return "eFact"
        elif cfe_code in [121, 122, 123]:
            return "eFact_Exp"
        else:
            return False

    @api.model
    def _get_doc_parts(self, record):
        """ Return list [serie, number] of the give CFE. If not valid then return [False, False]"""
        res = re.findall(r"([A-Z]{1,2})[-]*([0-9]{1,8})", record.l10n_latam_document_number)
        return res[-1] if res else [False, False]

    @api.model
    def _get_legends(self, addenda_type, move_id):
        """ This method check return the legends and info to be used per xml tag. also will automatically add ̱̰{ } to
        the legends when needed, which indicates Uruware the presence
        of Mandatory Disclosure
        Return type: string  """
        res = []
        addendas = move_id.l10n_uy_edi_addenda_ids.filtered(lambda x: x.type == addenda_type)
        for addenda in addendas:
            res.append("{ %s }" % addenda.content if addenda.is_legend else addenda.content)
        return "\n".join(res)

    @api.model
    def _get_minimum_legal_amount(self, company, date):
        """ Converts 50000 UYI in the company currency """
        return self.env.ref("base.UYI")._convert(50000, company.currency_id, company=company, date=date)

    def _get_pdf(self):
        """ Connect to Uruware with the info of CFE and return the corresponding PDF file
        Legal representation.
        return: {"errors"; strg(), "file_content": bytes string file content}"""
        res = {}
        document_number = re.search(r"([A-Z]*)([0-9]*)", self.l10n_latam_document_number).groups()
        req_data = {
            "rut": self.company_id.partner_id.vat,
            "tipoCfe": int(self.l10n_latam_document_type_id.code),
            "serieCfe": document_number[0],
            "numeroCfe": document_number[1],
        }
        report_params, extra_params = self._get_report_params()
        req_data.update(extra_params)

        result = self._ucfe_query(report_params, req_data)
        response = result.get("response")

        if response is not None:
            res.update({"file_content": response.findtext(".//{*}" + report_params + "Result").encode()})

        if result.get("errors"):
            res.update({"errors": result.get("errors")})

        return res

    def _get_report_params(self):
        """ Print the default representation of the PDF report with extra params when applicable.
        Extra params available:
        1. ("adenda", "true") to print the adenda in a separate sheet if it is longer than 6 lines.
        2. ("reporte", "ingles") In case document is an e-ticket or e-factura expo or their respective CN and DN,
        if the partner's configured language is not Spanish it will print the report both in spanish and english.
        """

        available_doc_types = (
            self.env.ref('l10n_uy.dc_e_ticket') |
            self.env.ref('l10n_uy.dc_cn_e_ticket') |
            self.env.ref('l10n_uy.dc_dn_e_ticket') |
            self.env.ref('l10n_uy.dc_e_inv_exp') |
            self.env.ref('l10n_uy.dc_cn_e_inv_exp') |
            self.env.ref('l10n_uy.dc_dn_e_inv_exp')
        )
        addenda = self.move_id._l10n_uy_edi_get_addenda()
        parameters = {}

        if addenda:
            # The addenda (e.g. terms and conditions) is added in a small box at the bottom of the standard PDF report.
            # This can only accommodate roughly 6 lines of 140 characters.If the addenda exceeds that, the remainder is
            # cut off, which is problematic for mandatory disclosures etc.
            max_chars_per_line = 140
            max_lines_without_addenda = 6
            wrapped = textwrap.wrap(addenda, width=max_chars_per_line, replace_whitespace=False)

            # The resulting list will preserve newlines from the addenda because of replace_whitespace=False, join to
            # create the final string. Count the lines of the final string and request a dedicated addenda page if
            # needed, adding the parameter to the report.
            if len("\n".join(wrapped).splitlines()) > max_lines_without_addenda:
                parameters["adenda"] = "true"

        if (
            self.l10n_latam_document_type_id.code in available_doc_types.mapped('code')
            and self.partner_id.lang
            and not self.partner_id.lang.startswith("es_")
        ):
            parameters["reporte"] = "ingles"

        if parameters:
            return "ObtenerPdfConParametros", {
                "nombreParametros": {"string": list(parameters.keys())},
                "valoresParametros": {"string": list(parameters.values())}
            }

        return "ObtenerPdf", {}

    def _get_ucfe_username(self, company):
        return re.sub("[^0-9]", "", company.vat) if company.vat else False

    def _get_uuid(self, move):
        """ Uruware UUID to identify the edi document and also A4.1 (NroInterno) DGI field. Spec (V24) ALFA50.
        We did not make it as default value because we need the move to set """
        res = move._name + "-" + str(move.id)
        if move.company_id.l10n_uy_edi_ucfe_env == "testing":
            res = "am" + str(move.id) + "-" + self.env.cr.dbname
        return res[:50]

    def _get_ws_url(self, ws_endpoint, company):
        """
        Get the Uruware endpoint to be called, or False if we are in demo mode.
        The endpoints are read from the config parameters:
        * `l10n_uy_edi.l10n_uy_edi_ucfe_inbox_url`
        * `l10n_uy_edi.l10n_uy_edi_ucfe_query_url`

        :param ws_endpoint: "inbox" or "query"
        :param company: res.company
        """
        if company.l10n_uy_edi_ucfe_env == "demo":
            return False
        elif company.l10n_uy_edi_ucfe_env == 'production':
            base_url = "https://prod6109.ucfe.com.uy/"
        else:
            base_url = "https://odootest.ucfe.com.uy/"

        if ws_endpoint == "inbox":
            url = self.env["ir.config_parameter"].sudo().get_param(
                key="l10n_uy_edi.l10n_uy_edi_ucfe_inbox_url",
                default=base_url + "inbox115/cfeservice.svc",
            )
            pattern = r"https://.*\.ucfe\.com\.uy/inbox.*/cfeservice\.svc"
        elif ws_endpoint == "query":
            url = self.env["ir.config_parameter"].sudo().get_param(
                key="l10n_uy_edi.l10n_uy_edi_ucfe_query_url",
                default=base_url + "query116/webservicesfe.svc",
            )
            pattern = r"https://.*\.ucfe\.com\.uy/query.*/webservicesfe\.svc"
        else:
            url = pattern = None

        return url if re.match(pattern, url, re.IGNORECASE) is not None else False

    def _get_xml_attachment_name(self):
        if self and self.move_id.company_id.l10n_uy_edi_ucfe_env == "demo":
            return "demo-cfe-%s.xml" % self.l10n_latam_document_number
        if self.state in ["received", "accepted"]:
            return f"CFE_{self.l10n_latam_document_number}.xml"
        return "preview-cfe-move-%s.xml" % self.move_id.id

    @api.model
    def _is_connection_info_incomplete(self, company):
        """ False if everything is ok, Message if there is a problem or something missing """

        field_data = company.fields_get([])
        missing_info = []
        for field in (
            "l10n_uy_edi_ucfe_env",
            "l10n_uy_edi_ucfe_password",
            "l10n_uy_edi_ucfe_commerce_code",
            "l10n_uy_edi_ucfe_terminal_code",
        ):
            if not company[field]:
                missing_info.append(field_data[field]["string"])
        inbox_url = self._get_ws_url("inbox", company)
        if not inbox_url:
            missing_info.append(_("UCFE Provider Inbox URL"))
        query_url = self._get_ws_url("query", company)
        if not query_url:
            missing_info.append(_("UCFE Provider Query URL"))
        username = self._get_ucfe_username(company)
        if not username:
            missing_info.append(_("UCFE Provider Username"))

        if missing_info:
            return _(
                "Incomplete Data to connect to UCFE Provider on company %(company)s: Please complete the UCFE data to test "
                "the connection: %(missing)s",
                company=company.name,
                missing=", ".join(missing_info),
            )

        return False

    @api.model
    def _process_response(self, soap_response, errors):
        response_tree = False
        if errors and soap_response is None:
            return {"errors": errors}
        if soap_response is None:
            return {"errors": _("No response")}

        if soap_response.content is None:
            return {"errors": _("EMPTY response")}

        try:
            response_tree = etree.fromstring(soap_response.content)
        except etree.LxmlError as exp:
            return {"errors": _("Error processing the response %(exp_rep)s", exp_rep=str(exp))}

        # Capture any other errors in the connection
        if response_tree is not None:
            error_code = response_tree.findtext(".//{*}ErrorCode")
            if error_code and int(error_code):
                error_msg = response_tree.findtext(".//{*}ErrorMessage")
                errors.append(_("Response Error - Code: %(code)s %(msg)s", code=error_code, msg=error_msg or ""))
            if fault_string := response_tree.findtext(".//{*}faultstring"):
                errors.append(_("Fault Error - %(msg)s", msg=fault_string))

        return {"response": response_tree, "errors": errors}

    def _send_dgi(self, request_data):
        """ Call endpoint that lets us post a DGI Invoice (310 - Signature and sending of CFE (individual)) """
        self.ensure_one()
        return self._ucfe_inbox("310", request_data)

    def _ucfe_inbox(self, msg_type, extra_req):
        """ Call Operation on UCFE inbox webservice
        :param msg_type: integer that represents the query we are going to call. For instance:
            360 - Check CFE State
            310 - Create CFE on DGI (send)
            820 - Check Credentials
        :returns: dictionary ({"response" etree obj }, "errors": str()) """
        now = fields.Datetime.now()
        company = extra_req.get('company') or self.company_id or self.env.company
        data = {
            "CodComercio": company.sudo().l10n_uy_edi_ucfe_commerce_code,
            "CodTerminal": company.sudo().l10n_uy_edi_ucfe_terminal_code,
            "RequestDate": now.replace(microsecond=0).isoformat(),
            "Tout": "30000",
            "Req": {
                "TipoMensaje": msg_type,
                "CodComercio": company.sudo().l10n_uy_edi_ucfe_commerce_code,
                "CodTerminal": company.sudo().l10n_uy_edi_ucfe_terminal_code,
                "IdReq": 1,
                **extra_req,
            },
        }
        return self._ucfe_ws_call(company, "inbox", "Invoke", [data])

    def _ucfe_query(self, method, req_data):
        """ Call Query on UCFE Query Webservices """
        company = self.company_id or self.env.company
        return self._ucfe_ws_call(company, "query", method, **req_data)

    def _ucfe_ws_call(self, company, endpoint, method, *args, **kwargs):
        response = None
        errors = []

        if error := self._is_connection_info_incomplete(company):
            # An error is possible if the company does not have credentials or if they are incorrect
            return {'response': None, "errors": [error]}
        url = self._get_ws_url(endpoint, company)
        if url and not url.endswith("?wsdl"):
            url += "?wsdl"
        try:
            username_token = UsernameToken(self._get_ucfe_username(company), company.l10n_uy_edi_ucfe_password)
            client = Client(url, wsse=username_token, settings=Settings(raw_response=True))
            if args:
                response = client.service[method](*args)
            else:
                response = client.service[method](**kwargs)
        except (Timeout, ConnectionError, HTTPError) as exp:
            errors.append(_("There was a problem with the connection with Uruware: %s", repr(exp)))

        return self._process_response(response, errors)

    def _update_cfe_state(self, result):
        """ Update the CFE State and update the error message field if applies.
        It depends on the Uruware/DGI state, response(CodRta)

        If CFE have been accepted, received or rejected cannot be sent again to UCFE
        because they cannot be changed (they have been already sent to DGI) """
        errors = result.get("errors")
        if errors:
            self.write({
                'state': "error",
                'message': "\n - ".join(errors),
            })
        else:
            response = result.get("response")
            if response is not None:
                ucfe_result_code = response.findtext(".//{*}CodRta")
                self.state = RESPONSE_CODE_TO_STATE.get(ucfe_result_code, "error")
                if self.state in ["error", "rejected"]:
                    result_msg = response.findtext(".//{*}MensajeRta")
                    self.message = _("CODE %(code)s: %(msg)s", code=ucfe_result_code, msg=result_msg)
                elif self.state in ["received", "accepted"]:
                    self.message = False

    def _create_partner_from_notification(self, xml_tree, partner_vat_RUC):
        """DEPRECATED: Use _get_partner_from_xml instead."""
        return self._get_partner_from_xml(xml_tree, partner_vat_RUC)

    def _get_partner_from_xml(self, xml_tree, partner_vat_RUC):
        """Select partner if exists or create partner from vendor bill XML data. """
        partner = self.env["res.partner"]._retrieve_partner(vat=partner_vat_RUC, company=self.company_id)
        state_id = None
        if departamento := xml_tree.findtext(".//{*}Departamento"):
            state_id = self.env["res.country.state"].search([("name", "ilike", departamento), ("country_id.code", "=", "UY")], limit=1)
        return partner or self.env["res.partner"].create({
            "name": xml_tree.findtext(".//{*}RznSoc"),
            "vat": partner_vat_RUC,
            "city": xml_tree.findtext(".//{*}Ciudad"),
            "street": xml_tree.findtext(".//{*}DomFiscal"),
            "state_id": state_id.id if state_id else None,
            "country_id": self.env.ref("base.uy").id,
            "l10n_latam_identification_type_id": self.env.ref("l10n_uy.it_rut").id,
            "is_company": True
        })

    def _create_pdf_vendor_bill(self, move, req_data_pdf):
        """ DEPRECATED PARAMETER: 'move' is no longer used.
        Will connect to Uruware to get the a legal PDF representation of the EDI doc and attach it to the vendor
        bill. """
        self.ensure_one()
        result = self._ucfe_query('ObtenerPdfCfeRecibido', req_data_pdf)
        errors = result.get('errors')
        if errors := result.get('errors'):
            msg_error = _("It is not possible to create the pdf for this move. Error: %(errors)s.", errors="\n - ".join(errors))
            self.move_id.message_post(body=msg_error)
            return

        response = result.get("response")
        name = f"{self.move_id.l10n_latam_document_type_id.doc_code_prefix} {req_data_pdf['serieCfe']}{req_data_pdf['numeroCfe'].zfill(7).replace('/', '_')}.pdf"
        return self.env["ir.attachment"].create({
            "name": name,
            "res_model": self.move_id._name,
            "res_field": "invoice_pdf_report_file",
            "res_id": self.move_id.id,
            "type": "binary",
            "datas": response.findtext('.//{*}ObtenerPdfCfeRecibidoResult').encode()
        })

    def cron_l10n_uy_edi_get_vendor_bills(self, batch_size=10):
        """ UY: Create vendor bills from Uruware. If there are notifications available on Uruware side then here
        is pulled that information, then we create the vendor bill and after that we dismiss the notification to
        continue reading the next one until there are no more notifications available. """
        company_errors = {}
        cron_limit_time = tools.config['limit_time_real_cron'] or -1
        limit_time = cron_limit_time if 0 < cron_limit_time < 300 else 300
        start_time = fields.Datetime.now()
        processed_notifications = 0
        for company in self.env['res.company'].search([]).filtered(lambda x: x.country_code == 'UY'):
            if not self.env['account.journal'].search([
                *self.env['account.tax']._check_company_domain(company),
                ('type', '=', 'purchase')
            ], limit=1):
                continue
            notifications = True
            while notifications and processed_notifications < batch_size:
                # 600 - Check for available notifications.
                response_600 = self._notification_consult(company)
                if errors := response_600['errors']:
                    joined_errors_msg = ". ".join(errors)
                    error_msg = _("We found an error while consulting a notification %(joined_errors_msg)s.", joined_errors_msg=joined_errors_msg)
                    company_errors[f'{company.id}'] = error_msg
                    notifications = False
                    continue

                # Verify response_600 code
                cod_rta_status = self._notification_verify_codrta(company, response_600['response'])
                if not cod_rta_status['response']:
                    if error := cod_rta_status['error']:
                        company_errors[f'{company.id}'] = error
                    notifications = False
                    continue

                # 610 - Request notification details.
                l10n_uy_idreq = response_600['response'].findtext('.//{*}IdReq')
                response_610 = self._ucfe_inbox("610", {"IdReq": l10n_uy_idreq, 'company': company})
                if errors := response_610['errors']:
                    company_errors[f'{company.id}'] = "\n".join(errors)
                    notifications = False
                    continue

                doc_type = self.env['account.move']._l10n_uy_edi_get_cfe_document_type(response_610['response'])
                # Only implemented for vendor bills and vendor refunds
                if doc_type and doc_type.code not in ['124', '181', '182', '224', '281', '282']:
                    move = self._create_edi_move(
                        response_610['response'],
                        company=company,
                        doc_type=doc_type,
                        l10n_uy_idreq=l10n_uy_idreq + '-notification'
                    )
                    xml_cfe_firmado = response_610['response'].findtext(".//{*}XmlCfeFirmado")

                    document_number = response_610['response'].findtext(".//{*}Serie") +\
                        (response_610['response'].findtext(".//{*}NumeroCfe") or response_610['response'].findtext(".//{*}Nro")).zfill(7)

                    self.env["ir.attachment"].create({
                        "name": f"CFE_{document_number}.xml",
                        "res_model": "l10n_uy_edi.document",
                        "res_id": move.l10n_uy_edi_document_id.id,
                        "res_field": "attachment_file",
                        "type": "binary",
                        "datas": base64.b64encode(xml_cfe_firmado.encode()
                                                  if xml_cfe_firmado
                                                  else etree.tostring(response_610['response']))})
                    move._l10n_uy_edi_complete_cfe_from_xml(etree.fromstring(xml_cfe_firmado))
                else:
                    # Until now we are not supporting the creation of e-Resguardos and e-Remitos
                    doc_type_name = doc_type.name if doc_type else 'undefined'
                    company_errors[f'{company.id}'] = _("Up to now it is not possible to create %(doc_type_name)s documents. IdReq: %(l10n_uy_idreq)s",
                                                        doc_type_name=doc_type_name,
                                                        l10n_uy_idreq=l10n_uy_idreq + '-notification')
                response_620 = self._notification_dismiss(company, response_600['response'])
                if response_620['response'].findtext('.//{*}CodRta') != "00":
                    company_errors[f'{company.id}'] = etree.tostring(response_620['response'])
                    notifications = False
                    continue
                if errors := response_620['errors']:
                    company_errors[f'{company.id}'] = str(errors)
                    notifications = False
                    continue
                processed_notifications += 1
            self._verify_company_errors_cron_l10n_uy_edi_get_vendor_bills(company_errors)
            if (fields.Datetime.now().timestamp() - start_time.timestamp() > limit_time) or notifications:
                self.env.ref('l10n_uy_edi.ir_cron_get_vendor_bills_received')._trigger()

    def _verify_company_errors_cron_l10n_uy_edi_get_vendor_bills(self, company_errors={}):
        if company_errors:
            _logger.warning(_('An error was found when synchronizing vendor bills\n'))
            for key, value in company_errors.items():
                _logger.warning(_('Company Name: "%(company_name)s", Company ID: (%(company_id)s), Errors: "%(error)s"',
                    company_name=self.env['res.company'].browse(int(key)).name, company_id=key, error=value)
                )

    @api.model
    def _create_edi_move(self, file_data, move=None, company=None, doc_type=None, l10n_uy_idreq=None):
        """Create move if does not exists and create edi document. 'uuid' edi document field containts the suffix
        '-manual' if the move was created by uploading the xml manually or the suffix '-notification' if the move was
        created by the cron 'UY: Create vendor bills (sync from Uruware)'."""
        company = company or self.env.company
        values = {
            'company_id': company.id,
            'move_type': doc_type._l10n_uy_edi_get_move_type(),
            'journal_id': self.env["account.journal"]
            .search(
                [
                    *self.env["account.journal"]._check_company_domain(company),
                    ("type", "=", "purchase"),
                    ("currency_id", "=", False),
                ],
                limit=1,
            )
            .id,
        }
        if move:
            move.write(values)
        else:
            move = self.env["account.move"].create(values)
        edi_doc = self.env["l10n_uy_edi.document"].create(
            {
                'move_id': move.id,
                'uuid': l10n_uy_idreq,
            }
        )
        move.l10n_uy_edi_document_id = edi_doc
        return move

    def _notification_consult(self, company=False):
        """ 600 - Consult notifications available on Uruware. """
        return self._ucfe_inbox("600", {"TipoNotificacion": "7", "company": company})

    def _notification_dismiss(self, company, response):
        """ This is implemented for vendor bills. It is needed to dismiss the last notification if the last vendor bill was
        created in Odoo from Uruware. To dismiss the last notification is needed to use the operation "620 - Descartar
        una notificación" with IdReq and TipoNotificacion. If is not possible to dismiss the last notification it will
        be returned the code "00" """
        id_req = response.findtext('.//{*}IdReq')
        response_620 = self._ucfe_inbox("620", {
            "IdReq": id_req,
            "TipoNotificacion": response.findtext('.//{*}TipoNotificacion'),
            "company": company})
        return response_620

    def _notification_verify_codrta(self, company, response_600):
        """ DEPRECATED PARAMETER: 'company' is no longer used.
        Verify response code from notifications (vendor bills). If response code is != 0 return False (can`t create
        new vendor bill), else return True (continue the process and create vendor bill).
        Available values for response code:
        00 Petición aceptada y procesada.
        01 Petición denegada.
        03 Comercio inválido.
        12 Requerimiento inválido.
        30 Error en formato.
        31 Error en formato de CFE.
        89 Terminal inválida.
        96 Error en sistema.
        99 Sesión no iniciada.
        ? Any other no specified code must be understanded as
        denied requirement."""
        cod_rta = response_600.findtext('.//{*}CodRta')
        response = {'response': False, 'error': ''}
        if cod_rta == "01":
            return response
        elif cod_rta != "00":
            response_msg = _("ERROR: This is what we receive when requesting notification data (610) %(tree)s", tree=etree.tostring(response_600))
            response['error'] = response_msg
            return response
        response['response'] = True
        return response
