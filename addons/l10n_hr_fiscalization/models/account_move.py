import base64
import datetime
import hashlib
import logging
import os
import tempfile
import uuid
import zoneinfo

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
    l10n_hr_old_payment_method_type = fields.Char(string="Old Payment Method")
    l10n_hr_fiscalization_payment_method_change_date = fields.Datetime(
        string="Payment Method Change Date",
        readonly=True,
    )

    @api.ondelete(at_uninstall=False)
    def _l10n_hr_fiscalization_unlink_except_fiscalized(self):
        if self.filtered(lambda m: m.l10n_hr_fiscalization_status == 0):
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
        - Datetime format: YYYYMMDD_HHMM (issued datetime)
        - Amount: absolute total with two decimals, period removed

        Uses 'l10n_hr_invoice_sending_time' (issued datetime) for QR;
        The datetime is converted to the Croatian timezone (Europe/Zagreb) for
        consistent representation with TA.
        """
        self.ensure_one()

        id_key = 'jir' if self.l10n_hr_fiscalization_jir else 'zki'
        identifier = self.l10n_hr_fiscalization_jir or self.l10n_hr_fiscalization_zki
        formatted_date = self._l10n_hr_format_datetime(
            self.l10n_hr_invoice_sending_time, date_format='%Y%m%d_%H%M'
        )
        amount_str = f'{self.amount_total_signed:.2f}'.replace('.', '')
        return f"https://porezna.gov.hr/rn?{id_key}={identifier}&datv={formatted_date}&izn={amount_str}"

    def _l10n_hr_format_datetime(self, dt, date_format='%d.%m.%YT%H:%M:%S'):
        """Convert a datetime to Croatian local time (Europe/Zagreb) and format it."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.UTC)
        return dt.astimezone(zoneinfo.ZoneInfo('Europe/Zagreb')).strftime(date_format)

    def _l10n_hr_datetime_to_odoo(self, hr_datetime_str):
        """Convert Croatian datetime string (dd.MM.yyyyThh:mm:ss) to Odoo datetime."""
        dt_local = datetime.datetime.strptime(
            hr_datetime_str, '%d.%m.%YT%H:%M:%S',
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
        date_str = self._l10n_hr_format_datetime(self.l10n_hr_invoice_sending_time)
        invoice_number = str(self.l10n_hr_fiscalization_number).split('/')
        certificate = self.company_id.l10n_hr_fiscalization_certificate

        if not oib:
            raise UserError(_("Company's OIB is required for fiscalization"))

        if len(invoice_number) < 3:
            raise UserError(_(
                "Invoice number format is not valid for fiscalization."
                "It should be like INV-2026-0001/1/1."
            ))

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
                raise UserError(_("Private key is encrypted but no password was provided."))
            password = certificate_record.pkcs12_password.encode()

        try:
            private_key = serialization.load_pem_private_key(
                private_key_data, password=password
            )
        except (TypeError, ValueError) as e:
            raise UserError(_("Error loading private key: %s", e))

        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise UserError(_("The certificate's private key must be an RSA key for signing."))

        signature = private_key.sign(
            concatenated_string.encode(), padding.PKCS1v15(), hashes.SHA256()
        )
        return hashlib.md5(signature).hexdigest()

    def _l10n_hr_prepare_fiscalization_request(self):
        """Return the dict of text values used to render the fiscalization request XML."""
        _ = self.env._

        invoice_number = str(self.l10n_hr_fiscalization_number).split('/')
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

        if not self.l10n_hr_payment_method_type:
            raise UserError(_(
                "Select a valid payment method type to fiscalize this invoice."
            ))

        tax_lines, pdv_taxes, pnp_taxes, other_taxes = [], [], [], []
        base_lines = self.line_ids.filtered('tax_ids')
        tax_lines = self.line_ids.filtered('tax_line_id')

        for tax_line in tax_lines:
            tax = tax_line.tax_line_id
            base_amount = sum(
                base_lines.filtered(lambda line: tax in line.tax_ids).mapped('balance')
            )
            entry = {
                'rate': f'{tax.amount:.2f}',
                'base_amount': f'{currency.round(sign * base_amount):.2f}',
                'tax_amount': f'{currency.round(sign * tax_line.balance):.2f}',
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
            'oib': self._l10n_hr_get_oib(self.company_id),
            'vat_applicable': vat_applicable,
            'invoice_sending_time':  self._l10n_hr_format_datetime(self.l10n_hr_invoice_sending_time),
            'sequence_identifier': self.company_id.l10n_hr_fiscalization_sequence_identifier,
            'invoice_number': invoice_number[0],
            'sales_outlet_id': invoice_number[1],
            'invoice_sequence_number': invoice_number[2],
            'pdv': pdv_taxes,
            'pnp': pnp_taxes,
            'other_taxes': other_taxes,
            'amount_total': f'{self.amount_total:.2f}',
            'payment_method': self.l10n_hr_payment_method_type,
            'operator_oib': self.l10n_hr_operator_oib,
            'zki': self.l10n_hr_fiscalization_zki or self._l10n_hr_generate_zki(),
            'is_subsequent_delivery': 'false',
        }

    def _l10n_hr_generate_xml_file(self, request_data, is_payment_change=False, check_status=False):
        """Render the fiscalization request XML and attach its XML-digital signature.

        Picks the matching QWeb template, renders the unsigned SOAP request, then
        signs the request element in place: enveloped signature over its
        Exclusive C14N form, SHA-256 digest, RSA-SHA256 signature method, with
        the certificate embedded in KeyInfo. Returns the final signed XML bytes.
        """
        self.ensure_one()
        _ = self.env._

        # Each type of request has its own template and its own main element.
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
            # The rendered template is wrong.
            raise UserError(_("Error signing XML: expected element '%s' not found", xpath))
        invoice_request = matches[0]
        invoice_request.set('Id', element_id)

        try:
            # Make a digest of the request. "c14n" writes the XML in one fixed way,
            # so we and the Central Information System(CIS) get exactly the same bytes.
            canonicalized_xml = etree.tostring(
                invoice_request, method='c14n', exclusive=True, with_comments=False,
            )
            digest_value = base64.b64encode(
                hashlib.sha256(canonicalized_xml).digest()
            ).decode('utf-8')

            signed_info_xml = self.env['ir.qweb']._render(
                'l10n_hr_fiscalization.template_invoice_fiscalization_signed_info',
                {'element_id': element_id, 'digest_value': digest_value},
            )
            signed_info_el = etree.fromstring(signed_info_xml)
            signed_info_c14n = etree.tostring(
                signed_info_el, method='c14n', exclusive=True, with_comments=False,
            )

            # signs the digest with fiscalization private key
            signature_value = certificate._l10n_hr_sign_data(signed_info_c14n)
            cert_info = certificate._l10n_hr_get_certificate_info()

            # Builds the full Signature block
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
            # This template has its own SignedInfo, but it is not the one we signed.
            # Replace it with the signed one. If the bytes differ, the Tax Authority
            # rejects the signature (error s004).
            signature_root = etree.fromstring(signature_xml)
            rendered_signed_info = signature_root.find(
                "{http://www.w3.org/2000/09/xmldsig#}SignedInfo"
            )
            signature_root.replace(rendered_signed_info, signed_info_el)

            # append the signature at the request.
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

            # Require FINA RDC CA PEMs for production for certificate verification
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
            response_xml = etree.fromstring(response.content)
            timestamp = _find_text(response_xml, './/tns:DatumVrijeme')

            if response.status_code != 200:
                error = f"HTTP Error: {response.status_code} - {response.reason}"
                code = _find_text(response_xml, './/tns:SifraGreske')
                message = _find_text(response_xml, './/tns:PorukaGreske')
                if detail := ' - '.join(filter(None, (code, message))):
                    error += f" - {detail}"
                _logger.warning(
                    "CIS rejected the request for %s (company %s): %s",
                    self.display_name, company.display_name, error,
                )
                return {'success': False, 'jir': None, 'timestamp': None, 'error': error}

            if check_status:
                invoice_details = {}
                invoice_el = response_xml.find('.//tns:Racun', namespaces=NAMESPACES)
                if invoice_el is not None:
                    invoice_fields = {
                        'OIB': './/tns:Oib',
                        'vat_system': './/tns:USustPdv',
                        'date_time': './/tns:DatVrijeme',
                        'sequence_number': './/tns:OznSlijed',
                        'amount_total': './/tns:IznosUkupno',
                        'payment_method': './/tns:NacinPlac',
                        'ZKI': './/tns:ZastKod',
                    }
                    for label, xpath in invoice_fields.items():
                        if value := _find_text(invoice_el, xpath):
                            invoice_details[label] = value

                # Collect the errors as "code: message"
                blocking_errors = []
                for error_el in response_xml.findall('.//tns:Greska', namespaces=NAMESPACES):
                    code = _find_text(error_el, './/tns:SifraGreske')
                    message = _find_text(error_el, './/tns:PorukaGreske')
                    if code and code != 'v100':
                        blocking_errors.append(f"{code}: {message or ''}".strip())

                is_ok = (
                    response_xml.find('.//tns:ProvjeraOdgovor', namespaces=NAMESPACES) is not None
                    and not blocking_errors
                )
                return {
                    'success': is_ok,
                    'timestamp': timestamp,
                    'invoice_details': invoice_details,
                    'error': None if is_ok else ('; '.join(blocking_errors) or "Unknown error"),
                }
            if is_payment_change:
                # The payment-change response confirms success/failure only - it
                # never contains a JIR.
                success_element = response_xml.find('.//tns:PromijeniNacPlacOdgovor', namespaces=NAMESPACES)

                if success_element:
                    return {
                        'success': True,
                        'datetime_of_payment_method_change': timestamp,
                        'error': None,
                    }
                code = _find_text(response_xml, './/tns:SifraGreske')
                message = _find_text(response_xml, './/tns:PorukaGreske')
                error_message = ' - '.join(filter(None, (code, message))) or "Unknown error"
                return {'success': False, 'error': error_message}

            _logger.info(
                "Invoice %s fiscalized (company %s), JIR %s",
                self.display_name,
                company.display_name,
                _find_text(response_xml, './/tns:Jir')
            )
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

    def _l10n_hr_change_payment_method_type(self, new_payment_method):
        """Send requset to the CIS to change the payment method of a fiscalized invoice.

        Only allowed on the day the invoice was fiscalized. Returns a dict with
        'success' and either 'message' or 'error'."""
        self.ensure_one()
        _ = self.env._

        if (fields.Date.context_today(self, self.l10n_hr_invoice_sending_time) != fields.Date.context_today(self)):
            return {
                'success': False,
                'error': _(
                    "Invoice data can only be changed on the same day the invoice was fiscalized."
                )
            }

        request_data = self._l10n_hr_prepare_fiscalization_request()
        request_data['payment_method'] = self.l10n_hr_old_payment_method_type
        request_data['changed_payment_method'] = new_payment_method
        request_data['change_payment_method_type'] = True
        message = f"Payment method type have been changed to {new_payment_method}."

        xml_doc = self._l10n_hr_generate_xml_file(request_data, is_payment_change=True)
        response = self._l10n_hr_send_xml_file(xml_doc, is_payment_change=True)

        if response.get('success'):
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
            'error': response.get('error'),
        }

    def _l10n_hr_check_fiscalization_status(self):
        _ = self.env._

        if (
            self.l10n_hr_fiscalization_status != '0'
            and not self.l10n_hr_fiscalization_jir
        ):
            return {
                'success': False,
                'error': _(
                    "Only fiscalized invoices can be checked. "
                    "Send invoice to Fiscalization first."
                )
            }

        request_data = self._l10n_hr_prepare_fiscalization_request()
        xml_doc = self._l10n_hr_generate_xml_file(request_data, check_status=True)
        response = self._l10n_hr_send_xml_file(xml_doc, check_status=True)

        if response['success']:
            return {
                'success': True,
                'message': _("Invoice is properly fiscalized."),
                'invoice_details': response.get('invoice_details')
            }
        return {
            'success': False,
            'error': _("Failed: %s", response.get('error')),
            'invoice_details': response.get('invoice_details')
        }

    def l10n_hr_fiscalize_invoice(self):
        """Fiscalize the invoice with the Croatian Tax Authority ."""
        self.ensure_one()

        # Already fiscalized: only a changed payment method type can be re-sent
        if self.l10n_hr_fiscalization_status == '0' and self.l10n_hr_fiscalization_jir:
            if self.l10n_hr_payment_method_type != self.l10n_hr_old_payment_method_type:
                response = self._l10n_hr_change_payment_method_type(
                    new_payment_method=self.l10n_hr_payment_method_type
                )
                if not response.get('success'):
                    raise UserError(response.get('error'))
                self.l10n_hr_old_payment_method_type = self.l10n_hr_payment_method_type
                return True
            raise UserError(self.env._(
                "Invoice %(invoice)s has already been fiscalized with JIR: %(jir)s",
                invoice=self.name,
                jir=self.l10n_hr_fiscalization_jir,
            ))
        else:
            request_data = self._l10n_hr_prepare_fiscalization_request()
            xml_doc = self._l10n_hr_generate_xml_file(request_data)
            response = self._l10n_hr_send_xml_file(xml_doc)

        if response.get('success'):
            self.write({
                'l10n_hr_fiscalization_status': '0',
                'l10n_hr_fiscalization_jir': response['jir'],
                'l10n_hr_fiscalization_zki': request_data['zki'],
                'l10n_hr_invoice_sending_time': self._l10n_hr_datetime_to_odoo(response['timestamp']),
                'l10n_hr_fiscalization_error': False,
                'l10n_hr_old_payment_method_type': self.l10n_hr_payment_method_type,
            })
        else:
            self.write({
                'l10n_hr_fiscalization_status': '1',
                'l10n_hr_fiscalization_error': response.get('error'),
            })
            if error := response.get('error'):
                raise UserError(self.env._("Fiscalization Error: %s", error))
        return response

    def action_check_fiscalization_status(self):
        self.ensure_one()
        result = self._l10n_hr_check_fiscalization_status()
        message = result.get('message') or result.get('error')
        invoice_details = result.get('invoice_details')
        if not result['success'] and invoice_details:
            details_text = "\n".join(f"{key}: {value}" for key, value in invoice_details.items())
            message += self.env._("\n\nInvoice details from the Tax Authority:\n%s", details_text)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': message,
                'type': 'success' if result['success'] else 'danger',
            }
        }
