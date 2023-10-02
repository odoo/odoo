# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _, tools, release
from odoo.exceptions import UserError

from cryptography.hazmat.primitives import hashes, ciphers
from base64 import b64decode, b64encode
from datetime import date, datetime
import uuid
import requests
from lxml import etree

import logging

_logger = logging.getLogger(__name__)


class AES_ECB_Cipher(object):
    """
    Usage:
        c = AES_ECB_Cipher('password').encrypt('message')
        m = AES_ECB_Cipher('password').decrypt(c)
    Tested under Python 3.10.10 and cryptography==3.4.8.
    """

    def __init__(self, key):
        self.bs = int(ciphers.algorithms.AES.block_size / 8)
        self.key = key.encode()

    def encrypt(self, message):
        encryptor = self._get_cipher().encryptor()
        ct = encryptor.update(self._pad(message).encode()) + encryptor.finalize()
        return b64encode(ct).decode("utf-8")

    def decrypt(self, enc):
        decryptor = self._get_cipher().decryptor()
        try:
            enc = b64decode(enc)
        except Exception:  # noqa: BLE001
            pass
        ct = decryptor.update(enc) + decryptor.finalize()
        return self._unpad(ct).decode("utf-8")

    def _get_cipher(self):
        return ciphers.Cipher(ciphers.algorithms.AES(self.key), ciphers.modes.ECB())

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[: -ord(s[len(s) - 1 :])]


def egyadat(path, fn, root, dest, f=None):
    if root.xpath(path):
        val = root.xpath(path)[0].text
        if callable(f):
            val = f(val)
        if val not in ("", None, []):
            dest[fn] = val


def egyadat_bool(*k, **kw):
    def boolconv(t):
        if t in ("false", "False", "0"):
            return False
        elif t in ("true", "True", "1"):
            return True
        return bool(t)

    kw["f"] = boolconv
    return egyadat(*k, **kw)


def egyadat_int(*k, **kw):
    kw["f"] = int
    return egyadat(*k, **kw)


def egyadat_dec(*k, **kw):
    kw["f"] = float
    return egyadat(*k, **kw)


def egyadat_date(*k, **kw):
    kw["f"] = fields.Date.to_date
    return egyadat(*k, **kw)


def egyadat_datetime(*k, **kw):
    def dtconv(adat):
        timestamp = None
        # 2023-01-31T05:57:34+01:00
        if len(adat) == 25 and "Z" not in adat:
            timestamp = datetime.strptime(adat, "%Y-%m-%dT%H:%M:%S%z")
        # 2023-01-31T05:57:34Z
        elif len(adat) == 20:
            timestamp = datetime.strptime(adat.replace("Z", ".000+0000"), "%Y-%m-%dT%H:%M:%S.%f%z")
        # 2023-01-31T05:57:34.111Z
        else:
            timestamp = datetime.strptime(adat.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S.%f%z")
        if timestamp:
            if timestamp.tzinfo:
                timestamp = datetime.utcfromtimestamp(timestamp.timestamp())

        return timestamp

    kw["f"] = dtconv
    return egyadat(*k, **kw)


class L10nHuNavCommunication(models.Model):
    _name = "l10n_hu.nav_communication"
    _description = "Hungarian TAX Authority Login Credentials"
    _rec_name = "username"
    _order = "company_id, sequence"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    vat_hu = fields.Char("VAT Number", related="company_id.partner_id.vat", store=True, readonly=True)

    sequence = fields.Integer("Sequence", default=10, required=True, index=True)
    username = fields.Char(
        "Username", required=True, readonly=True, states={"draft": [("readonly", False)]}, index=True
    )
    password = fields.Char("Password", required=True, readonly=True, states={"draft": [("readonly", False)]})
    sign_key = fields.Char("Sign Key", required=True, readonly=True, states={"draft": [("readonly", False)]})
    back_key = fields.Char("Back Key", required=True, readonly=True, states={"draft": [("readonly", False)]})

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("prod", "Production"),
            ("test", "Test"),
        ],
        string="Status",
        readonly=True,
        index=True,
        default="draft",
    )

    @api.model
    def _check_login(self, vat_hu, username, password, sign_key, back_key):
        # try PRODUCTION first
        response = self.do_token_request(vat_hu, username, password, sign_key, back_key, demo=False)
        if "ExchangeToken" in response:
            return "prod"

        # try TEST system
        response = self.do_token_request(vat_hu, username, password, sign_key, back_key, demo=True)
        if "ExchangeToken" in response:
            return "test"

        return "draft"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("company_id"):
                company = self.env["res.company"].search([("id", "=", vals.get("company_id"))])
            else:
                company = self.env.company
            if not company.ids:
                raise UserError(_("Missing company_id parameter"))

            if not company.vat:
                raise UserError(_("NAV Credentials: Please set the hungarian vat number first!"))

            if (
                not vals.get("username")
                or not vals.get("password")
                or not vals.get("sign_key")
                or not vals.get("back_key")
            ):
                raise UserError(_("NAV Credentials: Insufficient login informations!"))

            mode = self._check_login(
                company.vat,
                vals.get("username"),
                vals.get("password"),
                vals.get("sign_key"),
                vals.get("back_key"),
            )

            if mode not in ("prod", "test"):
                raise UserError(_("NAV Credentials: Wrong login informations!"))

            vals.update(
                {
                    "state": mode,
                }
            )

        return super().create(vals_list)

    def write(self, vals):
        if vals == {"company_id": False}:
            return super().unlink()
        if self.filtered(lambda c: c.state != "draft") and (
            "username" in vals or "password" in vals or "sign_key" in vals or "back_key" in vals
        ):
            raise UserError(_("Modification is prohibited! Create a new record instead!"))
        return super().write(vals)

    def force_retest(self):
        for conn in self:
            mode = self._check_login(
                conn.company_id.vat,
                conn.username,
                conn.password,
                conn.sign_key,
                conn.back_key,
            )
            conn.write({"state": mode})

    def _check_status(self):
        """Make sure this is a tested credential object"""
        self.ensure_one()

        if self.state == "draft":
            raise UserError(_("Credentials are not validated!"))

    @api.model
    def _get_best_communication(self, company=None):
        """Returns with the best usage communication object for a company
        If the test mode is forced, than look for a test object first
        Else go with the first production one, if there is any
        Else go with the first test one, if there is any
        Throw error if none found
        """
        self = self.sudo()
        if not company:
            company = self.env.company

        mode = "prod"
        if company.l10n_hu_use_demo_mode:
            mode = "test"

        conn_obj = self.search(
            [
                ("company_id", "=", company.id),
                ("state", "=", mode),
            ],
            limit=1,
        )
        if conn_obj:
            return conn_obj

        if mode == "prod":
            conn_obj = self.search(
                [
                    ("company_id", "=", company.id),
                    ("state", "=", "test"),
                ],
                limit=1,
            )
            if conn_obj:
                return conn_obj

        raise UserError(_("Please set NAV credentials first!"))

    @api.model
    def _get_nav_connection_credentials(self, company=None, prod=True):
        """This is like the previous one but for the login credentials.
        Difference is here we don't look for demo keys when we are in forced demo mode.
        """
        if not company:
            if self.ids:
                self.ensure_one()
                company = self.company_id
            else:
                company = self.env.company

        sd = [("company_id", "=", company.id)]
        if prod:
            sd += [("state", "=", "prod")]
        else:
            sd += [("state", "=", "test")]
        login_obj = self.search(sd, limit=1)

        if login_obj:
            return (
                login_obj.vat_hu[:8],
                login_obj.username,
                login_obj.password,
                login_obj.sign_key,
                login_obj.back_key,
            )

        raise UserError(_("No such validated credentials!"))

    @api.model
    def _AESCipher(self, key):
        return AES_ECB_Cipher(key)

    @api.model
    def _gen_request_id(self):
        """pattern: [+a-zA-Z0-9_]{1,30}"""
        return ("ODOO" + str(uuid.uuid4()).replace("-", ""))[:30]

    @api.model
    def _calc_PasswordHash(self, value):
        digest = hashes.Hash(hashes.SHA512())
        digest.update(value.encode())
        return digest.finalize().hex().upper()

    @api.model
    def _calc_InvoiceHash(self, value):
        digest = hashes.Hash(hashes.SHA3_512())
        digest.update(value.encode())
        return digest.finalize().hex().upper()

    @api.model
    def _calc_requestSignature(self, key_sign, reqid, reqdate, invoice_hashs=None):
        s = [reqid, reqdate.strftime("%Y%m%d%H%M%S"), key_sign]

        # merge the invoice CRCs if we got
        if invoice_hashs:
            s += invoice_hashs

        # join the strings
        s = "".join(s)
        # return back the uppered hexdigest
        return self._calc_InvoiceHash(s)

    @api.model
    def _gen_nav_format_timestamp(self, timestamp=None):
        if not timestamp:
            timestamp = datetime.utcnow()
        elif isinstance(timestamp, (date, str)):
            timestamp = fields.Datetime.to_datetime(timestamp)
        # convert TZ localtime to UTC time
        if timestamp.tzinfo:
            timestamp = datetime.utcfromtimestamp(timestamp.timestamp())
        return timestamp.strftime(f"%Y-%m-%dT%H:%M:%S.{int(int(timestamp.strftime('%f'))/1000)}Z")

    @api.model
    def _gen_nav_format_date(self, day=None):
        if not day:
            day = datetime.utcnow()
        elif isinstance(day, str):
            day = fields.Date.to_date(day)
        return day.strftime("%Y-%m-%d")

    @api.model
    def _gen_nav_format_bool(self, value):
        if bool(value):
            return "true"
        else:
            return "false"

    @api.model
    def _do_nav_comm(self, url, data):
        headers = {"content-type": "application/xml", "accept": "application/xml"}
        if self.env.context.get("nav_comm_debug"):
            _logger.warning("REQUEST: POST: %s==>headers:%s\ndata:%s", str(url), str(headers), str(data))
        response_object = requests.post(url, data=data.encode("utf-8"), headers=headers)
        if self.env.context.get("nav_comm_debug"):
            _logger.warning(
                "RESPONSE: status_code:%s\nheaders:%s\ndata:%s",
                response_object.status_code,
                response_object.headers,
                response_object.text,
            )
        return response_object

    @api.model
    def _get_nav_url(self, service, demo=False):
        base_url = "https://api.onlineszamla.nav.gov.hu/invoiceService/v3"
        if demo:
            base_url = "https://api-test.onlineszamla.nav.gov.hu/invoiceService/v3"

        if service in ("invoice_upload", "manageInvoice"):
            return f"{base_url}/manageInvoice"

        if service in ("taxpayer_query", "queryTaxpayer"):
            return f"{base_url}/queryTaxpayer"

        if service in ("token_request", "tokenExchange"):
            return f"{base_url}/tokenExchange"

        if service in ("query_transaction", "queryTransactionStatus"):
            return f"{base_url}/queryTransactionStatus"

        raise UserError("Wrong NAV service!")

    @api.model
    def _do_nav_service_comm(self, service, data, demo=False):
        return self._do_nav_comm(self._get_nav_url(service, demo=demo), data=data)

    @api.model
    def _gen_developer_values(self, odoo_ver=None):
        if not odoo_ver:
            odoo_ver = release.version
        # TODO: Odoo will be the developer?
        # "softwareName": release.product_name,
        # "softwareDevName": release.author,
        # "softwareDevContact": release.author_email,
        # "softwareDevCountryCode": "BG",
        data = {
            "softwareId": f"ODOOENTERPRISE-{odoo_ver[:2]}0",
            "softwareName": "Odoo Enterprise",
            "softwareOperation": "LOCAL_SOFTWARE",
            "softwareMainVersion": odoo_ver,
            "softwareDevName": "OdooTech Zrt.",
            "softwareDevContact": "info@odootech.hu",
            "softwareDevCountryCode": "HU",
            "softwareDevTaxNumber": "32226375",
        }
        return data

    @api.model
    def _gen_general_functions(self):
        return {
            "format_bool": self._gen_nav_format_bool,
            "format_datetime": self._gen_nav_format_timestamp,
            "format_timestamp": self._gen_nav_format_timestamp,
            "format_date": self._gen_nav_format_date,
            "password_hash": self._calc_PasswordHash,
        }

    @api.model
    def _gen_communication_values(
        self,
        nav_vat,
        nav_username,
        nav_password,
        nav_key_crypt,
        nav_key_decode=None,
        invoice_hashs=None,
        query_date=None,
        request_id=None,
        odoo_ver=None,
    ):
        if not query_date:
            query_date = datetime.utcnow()
        if not request_id:
            request_id = self._gen_request_id()

        request_signature = self._calc_requestSignature(
            nav_key_crypt, request_id, query_date, invoice_hashs=invoice_hashs
        )

        data = {
            **self._gen_developer_values(odoo_ver=odoo_ver),
            **self._gen_general_functions(),
            "nav_vat": nav_vat,
            "nav_username": nav_username,
            "nav_password": nav_password,
            "nav_key_crypt": nav_key_crypt,
            "nav_key_decode": nav_key_decode,
            "request_id": request_id,
            "query_date": query_date,
            "request_signature": request_signature,
        }

        return data

    @api.model
    def _get_xsd_file_name(self):
        return {
            "QueryTaxpayerRequest": "invoiceApi.xsd",
            "TokenExchangeRequest": "invoiceApi.xsd",
            "ManageInvoiceRequest": "invoiceApi.xsd",
            "QueryTransactionStatusRequest": "invoiceApi.xsd",
            "InvoiceData": "invoiceData.xsd",
        }

    @api.model
    def _xml_validator(self, xml_to_validate, operation_type):
        """
        This method validates the format description of the xml files

        :param xml_to_validate: xml to validate
        :param validation_type: the type of the document
        :return: whether the xml is valid. If the XSD files are not found returns True
        """

        if isinstance(xml_to_validate, bytes):
            xml_to_validate = xml_to_validate.replace(b"base:", b"")

        elif isinstance(xml_to_validate, str):
            xml_to_validate = xml_to_validate.replace("common:", "").encode("UTF-8")

        xsd_fname = self._get_xsd_file_name().get(operation_type)

        if not xsd_fname:
            _logger.warning(_("The XSD validation files for operation type '%s' have not been found"), operation_type)
            return True

        try:
            return tools.validate_xml_from_attachment(
                self.env,
                xml_to_validate,
                f"l10n_hu_navservice.{xsd_fname}",
                self.env["ir.attachment"]._l10n_hu_navservice_load_xsd_files,
            )
        except FileNotFoundError:
            _logger.warning(_("The XSD validation files from NAV have not been found"))
            return True
        except UserError as exc:
            return str(exc)
        _logger.info(_("The XSD validation for operation '%s' is success"), operation_type)

    @api.model
    def _parse_response(self, request_object, decode_password=None):
        if isinstance(request_object, requests.models.Response):
            data = request_object.text
        else:
            data = bytes(request_object.read())

        response_data = {
            "response_tag": None,
            "http_code": request_object.status_code,
            "response_raw": data,
        }
        response_data.update(self._parse_response_xml(data, decode_password=decode_password))

        if self.env.context.get("nav_comm_debug"):
            _logger.warning("PARSED RESPONSE:\nresponse_data:%s", response_data)
        return response_data

    @api.model
    def _evaluate_xml_text(self, xml_text, clean_ns=True):
        if isinstance(xml_text, str):
            xml_text = xml_text.encode("utf-8")

        if isinstance(xml_text, bytearray):
            xml_text = bytes(xml_text)

        if not isinstance(xml_text, bytes):
            raise UserError("_evaluate_xml_text(xml_text): Wrong attribute xml_text: is not bytes type!")

        xml_object = etree.fromstring(xml_text)

        if clean_ns:
            # Iterate through all XML elements
            for elem in xml_object.getiterator():
                # Skip comments and processing instructions,
                # because they do not have names
                if not isinstance(elem, (etree._Comment, etree._ProcessingInstruction)):
                    # Remove a namespace URI in the element's name
                    elem.tag = etree.QName(elem).localname

            # Remove unused namespace declarations
            etree.cleanup_namespaces(xml_object)

        return xml_object

    @api.model
    def _parse_response_xml(self, response_xml, decode_password=None):
        if isinstance(response_xml, (str, bytes, bytearray)):
            response_xml = self._evaluate_xml_text(response_xml)

        # if self.env.context.get("nav_comm_debug"):
        #     print(etree.tostring(response_xml, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode())

        response = {
            "response_tag": response_xml.tag,
            "requestId": None,
            "funcCode": None,
        }

        egyadat("//header/requestId", "requestId", response_xml, response)
        egyadat("//result/funcCode", "funcCode", response_xml, response)

        if response_xml.tag == "GeneralExceptionResponse":
            response.update(self._parse_response_xml_GeneralExceptionResponse(response_xml))

        if response_xml.tag == "GeneralErrorResponse":
            response.update(self._parse_response_xml_GeneralErrorResponse(response_xml))

        if response_xml.tag == "TokenExchangeResponse":
            response.update(self._parse_response_xml_TokenExchangeResponse(response_xml, decode_password))

        if response_xml.tag == "QueryTaxpayerResponse":
            response.update(self._parse_response_xml_QueryTaxpayerResponse(response_xml))

        if response_xml.tag == "ManageInvoiceResponse":
            response.update(self._parse_response_xml_ManageInvoiceResponse(response_xml))

        if response_xml.tag == "QueryTransactionStatusResponse":
            response.update(self._parse_response_xml_QueryTransactionStatusResponse(response_xml))

        return response

    @api.model
    def _parse_response_xml_GeneralErrorResponse(self, response_xml):
        response = {}

        egyadat("//result/errorCode", "errorCode", response_xml, response)
        egyadat("//result/message", "message", response_xml, response)

        return response

    @api.model
    def _parse_response_xml_GeneralExceptionResponse(self, response_xml, xpath_text=None):
        if not xpath_text:
            xpath_text = "//technicalValidationMessages"

        dn = xpath_text.split("/")[-1]
        response = {dn: []}

        for msg in response_xml.xpath(xpath_text):
            msg_data = {}
            egyadat("./validationResultCode", "validationResultCode", msg, msg_data)
            egyadat("./validationErrorCode", "validationErrorCode", msg, msg_data)
            egyadat("./message", "message", msg, msg_data)

            pointers = []
            for pointer_xml in msg.xpath("./pointer"):
                pointer = {}
                for element in pointer_xml.iter():
                    if element.tag == "pointer":
                        continue
                    pointer[element.tag] = element.text.strip()
                if pointer:
                    pointers.append(pointer)

            if pointers:
                msg_data["pointer"] = pointers

            if msg_data:
                response[dn].append(msg_data)

        return response

    @api.model
    def do_token_request(
        self, nav_vat=None, nav_username=None, nav_password=None, nav_key_crypt=None, nav_key_decrypt=None, demo=None
    ):
        if self.ids:
            self._check_status()

            if not nav_vat or not nav_username or not nav_password or not nav_key_crypt:
                nav_vat, nav_username, nav_password, nav_key_crypt, nav_key_decrypt = (
                    self.vat_hu[:8],
                    self.username,
                    self.password,
                    self.sign_key,
                    self.back_key,
                )

        if not nav_vat or not nav_username or not nav_password or not nav_key_crypt:
            raise UserError(_("Missing NAV connection parameter."))

        if demo is None:
            demo = self.state == "test"

        xml_content = self._generate_xml_TokenExchangeRequest(
            nav_vat,
            nav_username,
            nav_password,
            nav_key_crypt,
        )
        request_object = self._do_nav_service_comm("token_request", xml_content, demo=demo)

        response = self._parse_response(request_object, decode_password=nav_key_decrypt)
        return response

    @api.model
    def _generate_xml_TokenExchangeRequest(
        self, nav_vat, nav_username, nav_password, nav_key_crypt, query_date=None, request_id=None, odoo_ver=None
    ):
        template_values = self._gen_communication_values(
            nav_vat,
            nav_username,
            nav_password,
            nav_key_crypt,
            odoo_ver=odoo_ver,
            query_date=query_date,
            request_id=request_id,
        )
        content = self.env["ir.qweb"]._render("l10n_hu_edi.nav_TokenExchangeRequest", template_values)

        self._xml_validator(content, "TokenExchangeRequest")

        return f'<?xml version="1.0" encoding="UTF-8"?>{content}'

    @api.model
    def _parse_response_xml_TokenExchangeResponse(self, response_xml, decode_password):
        response = {}

        egyadat("//encodedExchangeToken", "encodedExchangeToken", response_xml, response)
        egyadat_datetime("//tokenValidityFrom", "tokenValidityFrom", response_xml, response)
        egyadat_datetime("//tokenValidityTo", "tokenValidityTo", response_xml, response)

        try:
            response["ExchangeToken"] = self._AESCipher(decode_password).decrypt(response["encodedExchangeToken"])
        except ValueError:
            _logger.error("NAV Communication: XML Parse Error during decryption of ExchangeToken")

        return response

    @api.model
    def do_taxpayer_query(
        self,
        vatnumber,
        nav_vat=None,
        nav_username=None,
        nav_password=None,
        nav_key_crypt=None,
        demo=None,
    ):
        if not nav_vat or not nav_username or not nav_password or not nav_key_crypt:
            (
                nav_vat,
                nav_username,
                nav_password,
                nav_key_crypt,
                dummy_nav_key_decrypt,
            ) = self._get_nav_connection_credentials(prod=True)

        if not nav_vat or not nav_username or not nav_password or not nav_key_crypt:
            raise UserError(_("Taxpayer validation needs a NAV Credential for the production system!"))

        xml_content = self._generate_xml_QueryTaxpayerRequest(
            vatnumber, nav_vat, nav_username, nav_password, nav_key_crypt
        )
        # taxpayer query is not available in demo service!
        request_object = self._do_nav_service_comm("taxpayer_query", xml_content, demo=False)

        response = self._parse_response(request_object)
        return response

    @api.model
    def _generate_xml_QueryTaxpayerRequest(
        self,
        vatnumber,
        nav_vat,
        nav_username,
        nav_password,
        nav_key_crypt,
        query_date=None,
        request_id=None,
        odoo_ver=None,
    ):
        template_values = {
            **self._gen_communication_values(
                nav_vat,
                nav_username,
                nav_password,
                nav_key_crypt,
                query_date=query_date,
                request_id=request_id,
                odoo_ver=odoo_ver,
            ),
            "vatnumber": vatnumber,
        }
        content = self.env["ir.qweb"]._render("l10n_hu_edi.nav_QueryTaxpayerRequest", template_values)

        self._xml_validator(content, "QueryTaxpayerRequest")

        return f'<?xml version="1.0" encoding="UTF-8"?>{content}'

    @api.model
    def _parse_response_xml_QueryTaxpayerResponse(self, response_xml):
        response = {}

        egyadat_datetime("//infoDate", "infoDate", response_xml, response)
        egyadat_bool("//taxpayerValidity", "Validity", response_xml, response)

        if response_xml.xpath("//taxpayerData"):
            egyadat("//taxpayerData/taxpayerName", "Name", response_xml, response)
            egyadat("//taxpayerData/taxpayerShortName", "ShortName", response_xml, response)
            egyadat("//taxpayerData/incorporation", "incorporation", response_xml, response)

            egyadat("//taxpayerData/taxNumberDetail/taxpayerId", "taxNumber", response_xml, response)
            egyadat("//taxpayerData/taxNumberDetail/vatCode", "vatCode", response_xml, response)
            egyadat("//taxpayerData/taxNumberDetail/countyCode", "countyCode", response_xml, response)
            egyadat("//taxpayerData/vatGroupMembership", "vatGroupMembership", response_xml, response)

            response["AddressList"] = []

            for addrItem in response_xml.xpath("//taxpayerData/taxpayerAddressList/taxpayerAddressItem"):
                addr_data = {}

                egyadat("./taxpayerAddressType", "Type", addrItem, addr_data)
                egyadat("./taxpayerAddress/countryCode", "countryCode", addrItem, addr_data)
                egyadat("./taxpayerAddress/region", "region", addrItem, addr_data)
                egyadat("./taxpayerAddress/postalCode", "postalCode", addrItem, addr_data)
                egyadat("./taxpayerAddress/city", "city", addrItem, addr_data)
                egyadat("./taxpayerAddress/streetName", "streetName", addrItem, addr_data)
                egyadat("./taxpayerAddress/publicPlaceCategory", "publicPlaceCategory", addrItem, addr_data)
                egyadat("./taxpayerAddress/number", "number", addrItem, addr_data)
                egyadat("./taxpayerAddress/building", "building", addrItem, addr_data)
                egyadat("./taxpayerAddress/staircase", "staircase", addrItem, addr_data)
                egyadat("./taxpayerAddress/floor", "floor", addrItem, addr_data)
                egyadat("./taxpayerAddress/door", "door", addrItem, addr_data)
                egyadat("./taxpayerAddress/lotNumber", "lotNumber", addrItem, addr_data)

                response["AddressList"].append(addr_data)

        return response

    @api.model
    def do_invoice_upload(
        self,
        invoices,
        token=None,
        nav_vat=None,
        nav_username=None,
        nav_password=None,
        nav_key_crypt=None,
        nav_key_decrypt=None,
        demo=None,
    ):
        if self.ids:
            self._check_status()

            if not nav_vat or not nav_username or not nav_password or not nav_key_crypt:
                nav_vat, nav_username, nav_password, nav_key_crypt, nav_key_decrypt = (
                    self.vat_hu[:8],
                    self.username,
                    self.password,
                    self.sign_key,
                    self.back_key,
                )

        if not nav_vat or not nav_username or not nav_password or not nav_key_crypt:
            raise UserError(_("Missing NAV connection parameter."))

        if demo is None:
            demo = self.state == "test"

        if not token:
            token_resp = self.do_token_request(
                nav_vat=nav_vat,
                nav_username=nav_username,
                nav_password=nav_password,
                nav_key_crypt=nav_key_crypt,
                nav_key_decrypt=nav_key_decrypt,
                demo=demo,
            )
            token = token_resp.get("ExchangeToken")

        invoice_xmls = {}
        for invoice in invoices:
            attachment_obj = self.env["ir.attachment"].search(
                [
                    ("name", "=", "invoice_data_navxml.xml"),
                    ("res_id", "=", invoice.id),
                    ("res_model", "=", invoice._name),
                    ("mimetype", "=", "application/xml"),
                ],
                limit=1,
            )
            if not attachment_obj:
                raise UserError(_("No NAV XML is generated for invoice %s (*%s)!", invoice.name, invoice.id))

            invoice_xmls[len(invoice_xmls) + 1] = (invoice._l10n_hu_get_nav_operation(), attachment_obj.raw)

        xml_content = self._generate_xml_ManageInvoiceRequest(
            token, invoice_xmls, nav_vat, nav_username, nav_password, nav_key_crypt
        )
        request_object = self._do_nav_service_comm("invoice_upload", xml_content, demo=demo)

        response = self._parse_response(request_object, decode_password=nav_key_decrypt)
        return response

    @api.model
    def _generate_xml_ManageInvoiceRequest(
        self,
        token,
        invoice_xmls,
        nav_vat=None,
        nav_username=None,
        nav_password=None,
        nav_key_crypt=None,
        query_date=None,
        request_id=None,
        odoo_ver=None,
    ):
        template_values = {
            "exchangeToken": token,
            "compressed": False,
            "invoices": [],
        }
        hashs = []
        # index should be 1, 2, ...
        for index in range(1, len(invoice_xmls) + 1):
            operation, invoice_xml = invoice_xmls[index]
            inv_data_b64 = b64encode(invoice_xml).decode("utf-8")
            inv_data = {
                "index": index,
                "operation": operation,
                "invoice_base64": inv_data_b64,
            }
            template_values["invoices"].append(inv_data)
            hashs.append(self._calc_InvoiceHash(f"{operation}{inv_data_b64}"))

        template_values.update(
            self._gen_communication_values(
                nav_vat,
                nav_username,
                nav_password,
                nav_key_crypt,
                invoice_hashs=hashs,
                query_date=query_date,
                request_id=request_id,
                odoo_ver=odoo_ver,
            )
        )

        content = self.env["ir.qweb"]._render("l10n_hu_edi.nav_ManageInvoiceRequest", template_values)

        self._xml_validator(content, "ManageInvoiceRequest")

        return f'<?xml version="1.0" encoding="UTF-8"?>{content}'

    @api.model
    def _parse_response_xml_ManageInvoiceResponse(self, response_xml):
        response = {}
        egyadat("//transactionId", "transactionId", response_xml, response)
        return response

    @api.model
    def do_query_transaction(
        self,
        transaction,
        nav_vat=None,
        nav_username=None,
        nav_password=None,
        nav_key_crypt=None,
        query_original=False,
        demo=None,
    ):
        if self.ids:
            self._check_status()

            if not nav_vat or not nav_username or not nav_password or not nav_key_crypt:
                nav_vat, nav_username, nav_password, nav_key_crypt, dummy_nav_key_decrypt = (
                    self.vat_hu[:8],
                    self.username,
                    self.password,
                    self.sign_key,
                    self.back_key,
                )

        if not nav_vat or not nav_username or not nav_password or not nav_key_crypt:
            raise UserError(_("Missing NAV connection parameter."))

        if demo is None:
            demo = self.state == "test"

        xml_content = self._generate_xml_QueryTransactionStatusRequest(
            nav_vat, nav_username, nav_password, nav_key_crypt, transaction, query_original=query_original
        )
        request_object = self._do_nav_service_comm("query_transaction", xml_content, demo=demo)

        response = self._parse_response(request_object)
        return response

    @api.model
    def _generate_xml_QueryTransactionStatusRequest(
        self,
        nav_vat,
        nav_username,
        nav_password,
        nav_key_crypt,
        transaction,
        query_original=False,
        query_date=None,
        request_id=None,
        odoo_ver=None,
    ):
        template_values = {
            **self._gen_communication_values(
                nav_vat,
                nav_username,
                nav_password,
                nav_key_crypt,
                query_date=query_date,
                request_id=request_id,
                odoo_ver=odoo_ver,
            ),
            "transactionId": transaction,
            "returnOriginalRequest": query_original,
        }
        content = self.env["ir.qweb"]._render("l10n_hu_edi.nav_QueryTransactionStatusRequest", template_values)

        self._xml_validator(content, "QueryTransactionStatusRequest")

        return f'<?xml version="1.0" encoding="UTF-8"?>{content}'

    @api.model
    def _parse_response_xml_QueryTransactionStatusResponse(self, response_xml):
        response = {"invoices": {}}

        egyadat("//processingResults/originalRequestVersion", "originalRequestVersion", response_xml, response)

        for inv_data in response_xml.xpath("//processingResults/processingResult"):
            data = {}

            egyadat_int("./index", "index", inv_data, data)
            egyadat_int("./batchIndex", "batchIndex", inv_data, data)
            egyadat("./invoiceStatus", "invoiceStatus", inv_data, data)
            egyadat_bool("./compressedContentIndicator", "compressedContentIndicator", inv_data, data)
            egyadat("./originalRequest", "originalRequest", inv_data, data)

            if data.get("originalRequest"):
                data["original_xml"] = b64decode(data["originalRequest"].decode("UTF-8"))

            data.update(
                self._parse_response_xml_GeneralExceptionResponse(inv_data, xpath_text="./technicalValidationMessages")
            )
            data.update(
                self._parse_response_xml_GeneralExceptionResponse(inv_data, xpath_text="./businessValidationMessages")
            )

            egyadat("./annulmentData/annulmentVerificationStatus", "annulmentVerificationStatus", inv_data, data)
            egyadat_datetime("./annulmentData/annulmentDecisionDate", "annulmentDecisionDate", inv_data, data)
            egyadat("./annulmentData/annulmentDecisionUser", "annulmentDecisionUser", inv_data, data)

            response["invoices"][data["index"]] = data

        return response
