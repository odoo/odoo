import base64
import datetime
import hashlib
import logging
import os
import tempfile
import uuid
import zoneinfo
from collections import defaultdict

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.business_data import split_vat
from odoo.tools.xml_utils import cleanup_xml_node

_logger = logging.getLogger(__name__)

NAMESPACES = {
    'tns': 'http://www.apis-it.hr/fin/2012/types/f73',
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_hr_fiscalization_jir = fields.Char(
        string="JIR",
        help="Unique identifier of the invoice (JIR)",
        readonly=True,
    )
    l10n_hr_fiscalization_zki = fields.Char(
        string="ZKI",
        help="Protective code of the issuer (ZKI)",
        readonly=True,
    )
    l10n_hr_fiscalization_old_recipient_oib = fields.Char(string="Old Personal OIB")
    l10n_hr_old_payment_method_type = fields.Char(string="Old Payment Method")
    l10n_hr_fiscalization_payment_method_change_date = fields.Datetime(
        string="Payment Method Change Date",
        readonly=True,
    )

    @api.ondelete(at_uninstall=False)
    def _l10n_hr_fiscalization_unlink_except_fiscalized(self):
        if (
            not self.env.context.get('force_delete')
            and any(move.l10n_hr_fiscalization_status == '0' for move in self)
        ):
            raise UserError(self.env._(
                'You cannot delete a move that has been fiscalized.'
            ))

    def _get_fiscalization_url(self):
        fisclization_mode = self.company_id.l10n_hr_fiscalization_mode
        urls = {
            'prod': "https://cis.porezna-uprava.hr:8449/FiskalizacijaService",
            'test': "https://cistest.apis-it.hr:8449/FiskalizacijaServiceTest",
            'demo': "demo??",
        }
        return urls[fisclization_mode]

    def _l10n_hr_get_fiscalization_qr_code(self):
        """Generate the Croatian fiscalization QR URL.

        Spec per Croatian TA:
        - Base URL: https://porezna.gov.hr/rn
        - Identifiers: use JIR if present, otherwise ZKI
        - Datetime format: YYYYMMDD_HHMM (issuance datetime)
        - Amount: absolute total with two decimals, period removed

        Uses 'l10n_hr_invoice_sending_time' (issuance datetime) for QR;
        The datetime is converted to the Croatian timezone (Europe/Zagreb) for
        consistent representation with TA.
        """
        self.ensure_one()

        id_key = 'jir' if self.l10n_hr_fiscalization_jir else 'zki'
        identifier = self.l10n_hr_fiscalization_jir or self.l10n_hr_fiscalization_zki
        datetime_source = self.l10n_hr_invoice_sending_time
        if not identifier or not datetime_source:
            return None

        formatted_date = self._l10n_hr_format_datetime(datetime_source, date_format='%Y%M%D_%H%M')
        amount_str = f'{self.amount_total_signed:.2f}'.replace('.', '')
        return f"https://porezna.gov.hr/rn?{id_key}={identifier}&datv={formatted_date}&izn={amount_str}"

    def _l10n_hr_format_datetime(self, dt, date_format='%D.%M.%YT%H:%M:%S'):
        """Convert a datetime to Croatian local time (Europe/Zagreb) and format it.

        Input 'dt' is expected to be an Odoo datetime field value or Python
        datetime (naive, UTC). The datetime is converted to Europe/Zagreb before
        formatting, so all callers get a consistent local-time representation.

        By default returns 'date_format' in the Tax Authority's SOAP request
        format, dd.MM.yyyyThh:mm:ss (e.g. ZKI generation, request timestamps).
        Pass `date_format='%Y%M%D_%H%M'` for the QR code's datv parameter format.
        """
        dt_utc = fields.Datetime.to_datetime(dt) or fields.Datetime.now()
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=datetime.UTC)
        else:
            dt_utc = dt_utc.astimezone(datetime.UTC)
        dt_local = dt_utc.astimezone(zoneinfo.ZoneInfo('Europe/Zagreb'))
        return dt_local.strftime(date_format)

    def _l10n_hr_datetime_to_odoo(self, hr_datetime_str):
        """Convert Croatian datetime string (dd.MM.yyyyThh:mm:ss) to Odoo datetime.
        """
        dt_local = datetime.datetime.strptime(
            hr_datetime_str, '%D.%M.%YT%H:%M:%S',
        ).replace(tzinfo=zoneinfo.ZoneInfo('Europe/Zagreb'))
        return dt_local.astimezone(datetime.UTC).replace(tzinfo=None)

    def _l10n_hr_get_oib(self, partner):
        if not partner or not partner.vat:
            return False

        _, oib = split_vat(partner.vat)
        if len(oib) == 11 and oib.isdigit():
            return oib
        return False

    def _l10n_hr_generate_zki(self):
        """Generate ZKI (Zaštitni kod izdavatelja) per official spec.

        The payload is a concatenation of OIB, creation datetime, three-part
        invoice number, and total amount; signed with RSA-SHA256 then MD5-hashed.
        """
        _ = self.env._
        oib = self._l10n_hr_get_oib(self.company_id)
        date_str = self._l10n_hr_format_datetime(
            self.l10n_hr_invoice_sending_time
        )
        invoice_number = str(self.l10n_hr_fiscalization_number).split('/')
        certificate = self.company_id.l10n_hr_fiscalization_certificate

        if not oib:
            raise UserError(_("Company's OIB is required for fiscalization"))

        if len(invoice_number) < 3:
            raise UserError(_("Invoice number format is not valid for fiscalization"))

        if not certificate:
            raise UserError(_("Fiscalization certificate is missing"))

        invoice_ref = invoice_number[0]
        sales_outlet_id = invoice_number[1]
        invoice_sequence_number = invoice_number[2]
        concatenated_string = (
            oib + date_str + invoice_ref + sales_outlet_id
            + invoice_sequence_number + f"{self.amount_total:.2f}"
        )

        certificate_record = certificate.sudo()
        private_key_data = bytes(
            certificate_record.with_context(bin_size=False).private_key_id.pem_key
        )

        password = None
        if b'ENCRYPTED' in private_key_data:
            if not certificate_record.pkcs12_password:
                raise UserError(_("Private key is encrypted but no password was provided"))
            password = certificate_record.pkcs12_password.encode()

        try:
            private_key = serialization.load_pem_private_key(
                private_key_data, password=password
            )
        except (TypeError, ValueError) as e:
            raise UserError(_("Error loading private key: %s", e))

        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise UserError(_("The certificate's private key must be an RSA key for signing"))

        signature = private_key.sign(
            concatenated_string.encode(), padding.PKCS1v15(), hashes.SHA256()
        )
        return hashlib.md5(signature).hexdigest()

    def _l10n_hr_prepare_fiscalization_request(self):
        _ = self.env._

        oib = self._l10n_hr_get_oib(self.company_id)
        date_str = self._l10n_hr_format_datetime(
            self.l10n_hr_invoice_sending_time
        )
        invoice_number = str(self.l10n_hr_fiscalization_number).split('/')
        zki = self.l10n_hr_fiscalization_zki or self._l10n_hr_generate_zki()
        payment_method = self.l10n_hr_payment_method_type
        sign, currency = self.direction_sign, self.currency_id
        vat_applicable = 'true' if self.company_id.vat else 'false'

        if not self.l10n_hr_operator_oib:
            raise UserError(_(
                "Operator OIB is required. "
                "Please set the Fiscal User on the invoice."
            ))

        if len(invoice_number) < 3:
            raise UserError(_(
                "Invoice number format is not valid for fiscalization."
            ))

        if not payment_method:
            raise UserError(_(
                "Select a valid payment method type to fiscalize this invoice."
            ))

        if payment_method == 'Z':
            raise UserError(_(
                "You cannot use 'Ostalo' as payment method type for B2C fiscalization. "
                "Use 'Obračunsko plaćanje' as payment method type."
            ))

        tax_lines, pdv_taxes, pnp_taxes, other_taxes = [], [], [], []

        base_amounts_by_tax = defaultdict(float)
        for line in self.line_ids:
            for tax in line.tax_ids:
                base_amounts_by_tax[tax.id] += line.balance
            if line.tax_line_id:
                tax_lines.append(line)

        for line in tax_lines:
            tax = line.tax_line_id
            entry = {
                'rate': f'{tax.amount:.2f}',
                'base_amount': f'{currency.round(sign * base_amounts_by_tax.get(tax.id, 0.0)):.2f}',
                'tax_amount': f'{currency.round(sign * line.balance):.2f}',
            }
            tax_group = tax.tax_group_id.l10n_hr_fiscalization_tax_group_id
            if tax_group == 'pdv':
                pdv_taxes.append(entry)
            elif tax_group == 'pnp':
                pnp_taxes.append(entry)
            else:
                other_taxes.append({**entry, 'name': tax.name})

        return {
            'message_id': str(uuid.uuid4()),
            'timestamp': self._l10n_hr_format_datetime(fields.Datetime.now()),
            'oib': oib,
            'vat_applicable': vat_applicable,
            'invoice_sending_time': date_str,
            'sequence_identifier': self.company_id.l10n_hr_fiscalization_sequence_identifier,
            'invoice_number': invoice_number[0],
            'sales_outlet_id': invoice_number[1],
            'invoice_sequence_number': invoice_number[2],
            'pdv': pdv_taxes,
            'pnp': pnp_taxes,
            'other_taxes': other_taxes,
            'amount_total': f'{self.amount_total:.2f}',
            'payment_method': payment_method,
            'operator_oib': self.l10n_hr_operator_oib,
            'zki': zki,
            'is_subsequent_delivery': 'false',
        }

    def _l10n_hr_generate_xml_file(self, request_data, is_payment_change=False, check_status=False):
        """Render the fiscalization request XML and attach its XML-DSig signature.

        Picks the matching QWeb template, renders the unsigned SOAP request, then
        signs the request element in place: enveloped signature over its
        Exclusive C14N form, SHA-256 digest, RSA-SHA256 signature method, with
        the certificate embedded in KeyInfo. Returns the final signed XML bytes.
        """
        self.ensure_one()
        _ = self.env._

        if is_payment_change:
            template_name = 'l10n_hr_fiscalization.template_invoice_payment_method_change_request'
            element_id = 'PromijeniNacPlacZahtjev'
        elif check_status:
            template_name = 'l10n_hr_fiscalization.template_invoice_check_fisicalization_status'
            element_id = 'ProvjeraZahtjev'
        else:
            template_name = 'l10n_hr_fiscalization.template_invoice_fisicalization'
            element_id = 'RacunZahtjev'
        xpath = f'//tns:{element_id}'

        certificate = self.company_id.l10n_hr_fiscalization_certificate
        if not certificate:
            raise UserError(_("Fiscalization certificate is missing."))

        xml_str = self.env['ir.qweb']._render(template_name, request_data)
        root = cleanup_xml_node(xml_str)
        matches = root.xpath(xpath, namespaces=NAMESPACES)
        if not matches:
            # A missing element means the template didn't render what this xpath
            # expects - a template bug, not a signing failure - so fail clearly
            # instead of letting IndexError fall into the generic catch below.
            raise UserError(_("Error signing XML: expected element '%s' not found", xpath))
        invoice_request = matches[0]
        invoice_request.set('Id', element_id)

        try:
            canonicalized_xml = etree.tostring(
                invoice_request, method='c14n', exclusive=True, with_comments=False,
            )
            digest_value = base64.b64encode(
                hashlib.sha256(canonicalized_xml).digest()
            ).decode('utf-8')

            # Rendered alone first so these exact bytes can be canonicalized and
            # signed below. template_invoice_fiscalization_digital_signature
            # also renders its own placeholder SignedInfo; we discard that copy
            # and splice this one in, so the embedded SignedInfo is guaranteed
            # to be the one that was actually signed.
            signed_info_xml = self.env['ir.qweb']._render(
                'l10n_hr_fiscalization.template_invoice_fiscalization_signed_info',
                {'element_id': element_id, 'digest_value': digest_value},
            )
            signed_info_el = etree.fromstring(signed_info_xml)
            signed_info_c14n = etree.tostring(
                signed_info_el, method='c14n', exclusive=True, with_comments=False,
            )

            certificate = certificate.sudo()
            signature_value = certificate._l10n_hr_sign_data(signed_info_c14n)
            cert_info = certificate._l10n_hr_get_certificate_info()

            signature_xml = self.env['ir.qweb']._render(
                'l10n_hr_fiscalization.template_invoice_fiscalization_digital_signature',
                {
                    'element_id': element_id,
                    'digest_value': digest_value,
                    'signature_value': signature_value,
                    'certificate': cert_info['certificate'],
                    'issuer_name': cert_info['issuer_name'],
                    'serial_number': cert_info['serial_number'],
                },
            )
            signature_root = etree.fromstring(signature_xml)
            rendered_signed_info = signature_root.find(
                "{http://www.w3.org/2000/09/xmldsig#}SignedInfo"
            )
            signature_root.replace(rendered_signed_info, signed_info_el)
            invoice_request.append(signature_root)
            return etree.tostring(root, encoding='utf-8', xml_declaration=True)
        except Exception as e:  # noqa: BLE001
            raise UserError(_("Error signing XML: %s", e))

    def _l10n_hr_send_xml_file(self, xml_doc, is_payment_change=False, check_status=False):
        """POST the signed XML to TA endpoints and normalize responses."""
        def _find_text(element, xpath):
            found = element.find(xpath, namespaces=NAMESPACES)
            return found.text if found is not None else None

        company = self.company_id
        fiscalization_mode = company.l10n_hr_fiscalization_mode
        url = self._get_fiscalization_url()
        interm_b64 = company.with_context(bin_size=False).l10n_hr_fiscalization_ca_intermediate_pem
        root_b64 = company.with_context(bin_size=False).l10n_hr_fiscalization_ca_root_pem

        if fiscalization_mode == 'demo':
            raise UserError(self.env._("Can't fiscalize invoice in demo mode."))

        if not interm_b64 or not root_b64:
            raise UserError(self.env._(
                "TA CA certificates are not configured. Upload both 'TA CA Intermediate (PEM)' "
                "and 'TA CA Root (PEM)' on the company Fiscalization settings."
            ))

        tmp_bundle_path = None
        try:
            if isinstance(xml_doc, etree._Element):
                xml_doc = etree.tostring(xml_doc, encoding='UTF-8', xml_declaration=True)

            # Require FINA RDC CA PEMs for production so certificate verification
            # is never silently disabled.
            if fiscalization_mode == 'prod':
                bundle_bytes = base64.b64decode(interm_b64)
                if not bundle_bytes.endswith(b"\n"):
                    bundle_bytes += b"\n"
                bundle_bytes += base64.b64decode(root_b64)
                if not bundle_bytes.endswith(b"\n"):
                    bundle_bytes += b"\n"
                with tempfile.NamedTemporaryFile(
                    prefix="fina_ca_bundle_", suffix=".pem", delete=False
                ) as f:
                    f.write(bundle_bytes)
                    f.flush()
                    tmp_bundle_path = f.name
                verify_param = tmp_bundle_path
            else:
                verify_param = False

            response = requests.post(
                url=url,
                data=xml_doc,
                headers={
                    'Content-Type': 'text/xml; charset=UTF-8',
                    'SOAPAction': '',
                },
                timeout=30,
                verify=verify_param,
            )

            if response.status_code != 200:
                response_xml = etree.fromstring(response.content)
                code = _find_text(response_xml, './/tns:SifraGreske')
                message = _find_text(response_xml, './/tns:PorukaGreske')
                detail = (
                    f"{code or ''} - {message or ''}"
                    if code is not None or message is not None
                    else None
                )
                return {
                    'success': False,
                    'jir': None,
                    'timestamp': None,
                    'error': f"HTTP Error: {response.status_code} - {response.reason} - {detail}",
                }

            response_xml = etree.fromstring(response.content)

            if check_status:
                invoice_element = _find_text(response_xml, './/tns:Racun')
                invoice_details = {}
                if invoice_element is not None:
                    field_map = {
                        'OIB': './/tns:Oib',
                        'vat_system': './/tns:USustPdv',
                        'date_time': './/tns:DatVrijeme',
                        'sequence_number': './/tns:OznSlijed',
                        'amount_total': './/tns:IznosUkupno',
                        'payment_method': './/tns:NacinPlac',
                        'ZKI': './/tns:ZastKod',
                    }
                    for label, xpath in field_map.items():
                        value = _find_text(invoice_element, xpath)
                        if value is not None:
                            invoice_details[label] = value

                    invoice_number_element = _find_text(invoice_element, './/tns:BrRac')
                    if invoice_number_element is not None:
                        invoice_number = _find_text(invoice_number_element, './/tns:BrOznRac')
                        sales_outlet_id = _find_text(invoice_number_element, './/tns:OznPosPr')
                        invoice_sequence_number = _find_text(invoice_number_element, './/tns:OznNapUr')
                        if (
                            invoice_number is not None
                            and sales_outlet_id is not None
                            and invoice_sequence_number is not None
                        ):
                            invoice_details['invoice_number'] = (
                                f"{invoice_number}/{sales_outlet_id}/{invoice_sequence_number}"
                            )

                timestamp = _find_text(response_xml, './/tns:DatumVrijeme')
                success_element = response_xml.find(
                    './/tns:ProvjeraOdgovor', namespaces=NAMESPACES
                )

                errors = []
                for error_element in response_xml.findall(
                    './/tns:Greska', namespaces=NAMESPACES
                ):
                    error_code = _find_text(error_element, './/tns:SifraGreske')
                    error_message = _find_text(error_element, './/tns:PorukaGreske')
                    if error_code is not None and error_message is not None:
                        errors.append({'code': error_code, 'message': error_message})

                has_errors = any(error['code'] != 'v100' for error in errors)

                if success_element is not None and not has_errors:
                    return {
                        'success': True,
                        'timestamp': timestamp,
                        'errors': errors,
                        'invoice_details': invoice_details,
                        'error': None,
                    }
                error_message = "; ".join(
                    f"{error['code']}: {error['message']}" for error in errors
                )
                return {
                    'success': False,
                    'timestamp': timestamp,
                    'errors': errors,
                    'invoice_details': invoice_details,
                    'error': error_message or "Unknown error",
                }
            if is_payment_change:
                # The payment-change response confirms success/failure only - it
                # never contains a JIR.
                success_element = response_xml.find(
                    './/tns:PromijeniNacPlacOdgovor', namespaces=NAMESPACES
                )
                timestamp = _find_text(response_xml, './/tns:DatumVrijeme')

                if success_element is not None:
                    return {
                        'success': True,
                        'datetime_of_payment_method_change': timestamp,
                        'error': None,
                    }
                code = _find_text(response_xml, './/tns:SifraGreske')
                message = _find_text(response_xml, './/tns:PorukaGreske')
                error_message = (f"{message} - {code}" or "Unknown error")
                return {'success': False, 'error': error_message}
            return {
                'success': True,
                'jir': _find_text(response_xml, './/tns:Jir'),
                'timestamp': _find_text(response_xml, './/tns:DatumVrijeme'),
                'error': None,
            }
        except Exception as e:  # noqa: BLE001
            _logger.exception(
                "Fiscalization web service call failed for company %s",
                company.display_name
            )
            return {
                'success': False,
                'jir': None,
                'timestamp': None,
                'error': str(e)
            }
        finally:
            try:
                if tmp_bundle_path and os.path.exists(tmp_bundle_path):
                    os.unlink(tmp_bundle_path)
            except Exception:  # noqa: BLE001
                _logger.warning(
                    "Failed to remove temporary CA bundle file %s",
                    tmp_bundle_path
                )

    def _l10n_hr_change_payment_method(self, new_payment_method, new_recipient_oib=None, change_oib=False):
        """Change payment method and/or recipient OIB for a fiscalized invoice via TA API.

        Uses the EDI send wizard plumbing to build, sign, and send a
        dedicated ChangePaymentMethod request. Updates the invoice on success.

        Args:
            new_payment_method: New payment method code (G, K, T, O)
            new_recipient_oib: New recipient OIB (11 digits) or empty string to clear
            change_oib: Boolean indicating if OIB should be changed
        """
        self.ensure_one()
        _ = self.env._

        if (
            self.l10n_hr_fiscalization_status != '0'
            or not self.l10n_hr_fiscalization_jir
        ):
            return {
                'success': False,
                'message': _("Only fiscalized invoices can have their data changed.")
            }

        fiscalization_date = fields.Date.context_today(
            self, self.l10n_hr_invoice_sending_time
        )
        today = fields.Date.context_today(self)
        if fiscalization_date != today:
            return {
                'success': False,
                'message': _(
                    "Invoice data can only be changed on the same day the invoice was fiscalized."
                )
            }

        if new_payment_method == 'T' and change_oib and new_recipient_oib:
            return {
                'success': False,
                'message': _(
                    "Recipient OIB cannot be sent with payment method 'Transakcijski račun' (T)."
                )
            }

        try:
            request_data = self._l10n_hr_prepare_fiscalization_request()
            request_data['changed_payment_method'] = new_payment_method

            message = f"Payment method type have been changed to {new_payment_method}."
            if change_oib:
                request_data['changed_recipient_oib'] = new_recipient_oib or ''
                request_data['change_oib'] = True
                message = f"Recipient OIB have been changed to {new_recipient_oib}!"

            xml_doc = self._l10n_hr_generate_xml_file(
                request_data, is_payment_change=True
            )
            response = self._l10n_hr_send_xml_file(
                xml_doc, is_payment_change=True
            )

            if response.get('success'):
                self.l10n_hr_payment_method_type = new_payment_method

                change_time_str = response.get('datetime_of_payment_method_change')
                if change_time_str:
                    self.l10n_hr_fiscalization_payment_method_change_date = (
                        self._l10n_hr_datetime_to_odoo(change_time_str)
                    )
                return {
                    'success': True,
                    'message': message,
                }
            return {
                'success': False,
                'message': response.get('error'),
            }
        except Exception as e:  # noqa: BLE001
            return {
                'success': False,
                'message': str(e)
            }

    def _l10n_hr_check_fiscalization_status(self):
        _ = self.env._

        if (
            self.l10n_hr_fiscalization_status != '0'
            and not self.l10n_hr_fiscalization_jir
        ):
            return {
                'success': False,
                'message': _(
                    "Only fiscalized invoices can be checked. "
                    "Send invoice to Fiscalization first."
                )
            }

        try:
            request_data = self._l10n_hr_prepare_fiscalization_request()
            xml_doc = self._l10n_hr_generate_xml_file(
                request_data, check_status=True
            )
            response = self._l10n_hr_send_xml_file(xml_doc, check_status=True)

            if response['success']:
                return {
                    'success': True,
                    'message': _("Invoice is properly fiscalized."),
                    'invoice_details': response.get('invoice_details', {})
                }
            return {
                'success': False,
                'message': _("Failed: %s", response.get('error')),
                'invoice_details': response.get('invoice_details', {})
            }
        except Exception as e:  # noqa: BLE001
            return {
                'success': False,
                'message': _("Failed: %s", e),
                'details': [],
                'invoice_details': {}
            }

    def l10n_hr_fiscalize_invoice(self):
        """Fiscalize the invoice with Croatian Tax Authority"""
        self.ensure_one()

        current_oib = self.partner_id.commercial_partner_id.l10n_hr_personal_oib
        current_payment_method_type = self.l10n_hr_payment_method_type
        old_oib = self.l10n_hr_fiscalization_old_recipient_oib
        old_payment_method_type = self.l10n_hr_old_payment_method_type
        if (
            self.l10n_hr_fiscalization_status == '0'
            and self.l10n_hr_fiscalization_jir
        ):
            if current_oib != old_oib:
                response = self._l10n_hr_change_payment_method(
                    current_payment_method_type, current_oib, True
                )
                return response
            if current_payment_method_type != old_payment_method_type:
                response = self._l10n_hr_change_payment_method(
                    current_payment_method_type
                )
                return response
            raise UserError(self.env._(
                "Invoice %(invoice)s has already been fiscalized with JIR: %(jir)s",
                invoice=self.name,
                jir=self.l10n_hr_fiscalization_jir,
            ))

        request_data = self._l10n_hr_prepare_fiscalization_request()

        try:
            xml_doc = self._l10n_hr_generate_xml_file(request_data)
            response = self._l10n_hr_send_xml_file(xml_doc)
            if response['success']:
                self.write({
                    'l10n_hr_fiscalization_status': '0',
                    'l10n_hr_fiscalization_jir': response['jir'],
                    'l10n_hr_fiscalization_zki': request_data['zki'],
                    'l10n_hr_invoice_sending_time': self._l10n_hr_datetime_to_odoo(response['timestamp']),
                    'l10n_hr_fiscalization_error': False,
                    'l10n_hr_fiscalization_old_recipient_oib': current_oib,
                    'l10n_hr_old_payment_method_type': current_payment_method_type,
                })
            else:
                self.write({
                    'l10n_hr_fiscalization_status': '1',
                    'l10n_hr_fiscalization_error': response['error'],
                })
            return response
        except Exception as e:  # noqa: BLE001
            self.write({
                'l10n_hr_fiscalization_status': '1',
                'l10n_hr_fiscalization_error': str(e),
            })
            raise UserError(e)

    def action_check_fiscalization_status(self):
        self.ensure_one()
        result = self._l10n_hr_check_fiscalization_status()

        message = result['message']
        if result.get('details'):
            detail_messages = []
            for detail in result['details']:
                if isinstance(detail, dict) and 'code' in detail and 'message' in detail:
                    detail_messages.append(f"{detail['code']}: {detail['message']}")

            if detail_messages:
                message += "\n\nDetails:\n" + "\n".join(detail_messages)

        if not result['success'] and result.get('invoice_details'):
            invoice_details = result.get('invoice_details', {})
            if invoice_details:
                message += "\n\nInvoice Details from Tax Authority:\n"
                for key, value in invoice_details.items():
                    if isinstance(value, (dict, list)):
                        message += f"{key}: {value!s}\n"
                    else:
                        message += f"{key}: {value}\n"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success' if result['success'] else 'danger',
            }
        }
