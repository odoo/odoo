import base64
import datetime
import hashlib
import logging
import os
import tempfile
import uuid
import zoneinfo

from collections import defaultdict
from lxml import etree
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.xml_utils import cleanup_xml_node
from odoo.tools.business_data import split_vat

_logger = logging.getLogger(__name__)

NAMESPACES = {
    'tns': 'http://www.apis-it.hr/fin/2012/types/f73',
}


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_fiscalization_url(self):
        fisclization_mode = self.company_id.l10n_hr_fiscalization_mode
        urls = {
            'prod': "https://cis.porezna-uprava.hr:8449/FiskalizacijaService",
            'test': "https://cistest.apis-it.hr:8449/FiskalizacijaServiceTest",
            'demo': "demo??",
        }
        return urls[fisclization_mode]

    @api.model
    def _is_fiscalization_applicable(self, move):
        if not all([
            move.move_type in ('out_invoice', 'out_refund'),
            move.company_id.country_code == 'HR',
            move.company_id.l10n_hr_fiscalization_certificate,
        ]):
            return False

        return not move.partner_id.commercial_partner_id.is_company

    def _get_all_extra_edis(self):
        res = super()._get_all_extra_edis()
        res.update({'fiscalization': {'label': self.env._("Fiscalization"), 'is_applicable': self._is_fiscalization_applicable}})
        return res

    def _l10n_hr_to_hr_local_dt(self, dt):
        """Convert given datetime to Europe/Zagreb tz-aware datetime.

        Accepts Odoo datetime field values or naive/aware Python datetimes.
        Returns tz-aware datetime in Europe/Zagreb.
        """
        dt_utc = fields.Datetime.to_datetime(dt) or fields.Datetime.now()
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=datetime.UTC)
        else:
            dt_utc = dt_utc.astimezone(datetime.UTC)
        return dt_utc.astimezone(zoneinfo.ZoneInfo('Europe/Zagreb'))

    def _l10n_hr_format_hr_datetime(self, dt):
        """Format a datetime as Croatian local time (Europe/Zagreb) in TA format.

        Input `dt` is expected to be an Odoo datetime field value or Python datetime
        (naive, UTC). Returns string in dd.MM.yyyyThh:mm:ss localized to Europe/Zagreb.
        """
        return self._l10n_hr_to_hr_local_dt(dt).strftime('%d.%m.%YT%H:%M:%S')

    def _l10n_hr_datetime_to_odoo(self, hr_datetime_str):
        """Convert Croatian datetime string (dd.MM.yyyyThh:mm:ss) to Odoo datetime"""
        try:
            dt_str = hr_datetime_str or fields.Datetime.now()
            dt_local = datetime.datetime.strptime(dt_str, '%d.%m.%YT%H:%M:%S').replace(tzinfo=zoneinfo.ZoneInfo('Europe/Zagreb'))
            return dt_local.astimezone(datetime.UTC).replace(tzinfo=None)
        except Exception:  # noqa: BLE001
            return fields.Datetime.now()

    def _l10n_hr_get_oib(self, partner):
        if not partner or not partner.vat:
            return False

        vat_prefix, oib = split_vat(partner.vat)
        if len(oib) == 11 and oib.isdigit():
            return oib
        return False

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        # Batch/cron runs (no checkbox field) fiscalize everything applicable;
        # the single-invoice wizard respects the user's checkbox instead.
        has_checkbox_field = 'extra_edi_checkboxes' in self._fields
        do_fiscalization = (
            bool(self.extra_edi_checkboxes and self.extra_edi_checkboxes.get('fiscalization', {}).get('checked'))
            if has_checkbox_field else True
        )
        if not do_fiscalization:
            return

        for invoice, invoice_data in invoices_data.items():
            if not self._is_fiscalization_applicable(invoice):
                continue
            try:
                self.l10n_hr_fiscalize_invoice(invoice)
            except UserError as e:
                invoice_data['error'] = str(e)
                raise UserError(e)

    def _l10n_hr_generate_zki(self, move):
        """Generate ZKI (Zaštitni kod izdavatelja) per official spec.

        The payload is a concatenation of OIB, creation datetime, three-part
        invoice number, and total amount; signed with RSA-SHA256 then MD5-hashed.
        """
        _ = self.env._
        oib = self._l10n_hr_get_oib(move.company_id)
        date_str = self._l10n_hr_format_hr_datetime(move.l10n_hr_invoice_sending_time)
        invoice_number = str(move.l10n_hr_fiscalization_number).split('/')
        certificate = move.company_id.l10n_hr_fiscalization_certificate

        if not oib:
            raise UserError(_("Company's OIB is required for fiscalization"))

        if len(invoice_number) < 3:
            raise UserError(_("Invoice number format is not valid for fiscalization"))

        if not certificate:
            raise UserError(_("Fiscalization certificate is missing"))

        invoice_ref = invoice_number[0]
        sales_outlet_id = invoice_number[1]
        invoice_sequence_number = invoice_number[2]
        concatenated_string = oib + date_str + invoice_ref + sales_outlet_id + invoice_sequence_number + f"{move.amount_total:.2f}"

        certificate_record = certificate.sudo()
        private_key_data = bytes(certificate_record.with_context(bin_size=False).private_key_id.pem_key)

        password = None
        if b'ENCRYPTED' in private_key_data:
            if not certificate_record.pkcs12_password:
                raise UserError(_("Private key is encrypted but no password was provided"))
            password = certificate_record.pkcs12_password.encode()

        try:
            private_key = serialization.load_pem_private_key(private_key_data, password=password)
        except (TypeError, ValueError) as err:
            raise UserError(_("Error loading private key: %s", err))

        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise UserError(_("The certificate's private key must be an RSA key for signing"))

        signature = private_key.sign(concatenated_string.encode(), padding.PKCS1v15(), hashes.SHA256())
        return hashlib.md5(signature).hexdigest()

    def _l10n_hr_prepare_fiscalization_request(self, move):
        oib = self._l10n_hr_get_oib(move.company_id)
        date_str = self._l10n_hr_format_hr_datetime(move.l10n_hr_invoice_sending_time)
        invoice_number = str(move.l10n_hr_fiscalization_number).split('/')
        zki = move.l10n_hr_fiscalization_zki if not move.l10n_hr_fiscalization_zki else self._l10n_hr_generate_zki(move)
        payment_method = move.l10n_hr_payment_method_type
        sign, currency = move.direction_sign, move.currency_id
        vat_applicable = 'true' if move.company_id.vat else 'false'

        if not move.l10n_hr_operator_oib:
            raise UserError(self.env._("Operator OIB is required. Please set the Fiscal User on the invoice."))

        if len(invoice_number) < 3:
            raise UserError(self.env._("Invoice number format is not valid for fiscalization"))

        if not payment_method:
            raise UserError(self.env._("Select a valid payment method type to fiscalize this invoice."))

        if payment_method == 'Z':
            raise UserError(self.env._("You cannot use 'Ostalo' as payment method type for B2C fiscalization. Use 'Obračunsko plaćanje' as payment method type."))

        tax_lines, pdv_taxes, pnp_taxes, other_taxes = [], [], [], []

        base_amounts_by_tax = defaultdict(float)
        for line in move.line_ids:
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

        request_data = {
            'message_id': str(uuid.uuid4()),
            'timestamp': self._l10n_hr_format_hr_datetime(fields.Datetime.now()),
            'oib': oib,
            'vat_applicable': vat_applicable,
            'invoice_sending_time': date_str,
            'sequence_identifier': move.company_id.l10n_hr_fiscalization_sequence_identifier,
            'invoice_number': invoice_number[0],
            'sales_outlet_id': invoice_number[1],
            'invoice_sequence_number': invoice_number[2],
            'pdv': pdv_taxes,
            'pnp': pnp_taxes,
            'other_taxes': other_taxes,
            # Use explicit sign to ensure refunds (out_refund) are negative
            'amount_total': f'{move.amount_total:.2f}',
            'payment_method': payment_method,
            'operator_oib': move.l10n_hr_operator_oib,
            'zki': zki,
            'is_subsequent_delivery': 'false',
        }

        return request_data

    def _l10n_hr_generate_xml_file(self, request_data, is_payment_change=False, check_status=False):
        if is_payment_change:
            template_name = 'l10n_hr_fiscalization.template_invoice_payment_method_change_request'
        elif check_status:
            template_name = 'l10n_hr_fiscalization.template_invoice_check_fisicalization_status'
        else:
            template_name = 'l10n_hr_fiscalization.template_invoice_fisicalization'

        xml_str = self.env['ir.qweb']._render(template_name, request_data)
        xml_doc = cleanup_xml_node(xml_str)

        root = xml_doc if isinstance(xml_doc, etree._Element) else etree.fromstring(xml_doc)
        signed_xml = self._l10n_hr_sign_xml_file(root, is_payment_change, check_status)
        return etree.tostring(signed_xml, encoding='utf-8', xml_declaration=True)

    def _l10n_hr_sign_xml_file(self, xml_doc, is_payment_change=False, check_status=False):
        """Sign a SOAP body element using the company's certificate.

        Enveloped XML-DSig with Exclusive C14N, RSA-SHA256 signature method,
        SHA1 digest, and X509 data attached to KeyInfo.
        """
        certificate = self.company_id.l10n_hr_fiscalization_certificate

        if not certificate:
            raise UserError(self.env._("Fiscalization certificate is missing"))

        try:
            root = xml_doc

            if is_payment_change:
                xpath = '//tns:PromijeniNacPlacZahtjev'
                element_id = 'PromijeniNacPlacZahtjev'
            elif check_status:
                xpath = '//tns:ProvjeraZahtjev'
                element_id = 'ProvjeraZahtjev'
            else:
                xpath = '//tns:RacunZahtjev'
                element_id = 'RacunZahtjev'

            invoice_request = root.xpath(xpath, namespaces=NAMESPACES)[0]
            invoice_request.set('Id', element_id)

            canonicalized_xml = etree.tostring(
                invoice_request,
                method='c14n',
                exclusive=True,
                with_comments=False
            )

            digest = hashlib.sha256(canonicalized_xml).digest()
            digest_value = base64.b64encode(digest).decode('utf-8')
            signed_info_xml = self.env['ir.qweb']._render(
                'l10n_hr_fiscalization.template_invoice_fiscalization_signed_info',
                {'element_id': element_id, 'digest_value': digest_value},
            )
            signed_info_el = etree.fromstring(signed_info_xml)

            signed_info_c14n = etree.tostring(
                signed_info_el,
                method='c14n',
                exclusive=True,
                with_comments=False,
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
                }
            )
            signature_root = etree.fromstring(signature_xml)

            rendered_signed_info = signature_root.find("{http://www.w3.org/2000/09/xmldsig#}SignedInfo")
            signature_root.replace(rendered_signed_info, signed_info_el)

            invoice_request.append(signature_root)
            return root
        except Exception as e:  # noqa: BLE001
            raise UserError(self.env._("Error signing XML: %s", e))

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
            raise UserError(self.env._("Cann't fiscalize invoice in demo mode."))

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
                with tempfile.NamedTemporaryFile(prefix="fina_ca_bundle_", suffix=".pem", delete=False) as f:
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
                verify=verify_param)

            if response.status_code != 200:
                response_xml = etree.fromstring(response.content)
                code = _find_text(response_xml, './/tns:SifraGreske')
                message = _find_text(response_xml, './/tns:PorukaGreske')
                detail = f"{code or ''} - {message or ''}" if code is not None or message is not None else None
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
                        if invoice_number is not None and sales_outlet_id is not None and invoice_sequence_number is not None:
                            invoice_details['invoice_number'] = f"{invoice_number}/{sales_outlet_id}/{invoice_sequence_number}"

                timestamp = _find_text(response_xml, './/tns:DatumVrijeme')
                success_element = response_xml.find('.//tns:ProvjeraOdgovor', namespaces=NAMESPACES)

                errors = []
                for error_element in response_xml.findall('.//tns:Greska', namespaces=NAMESPACES):
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
                error_message = "; ".join(f"{error['code']}: {error['message']}" for error in errors)
                return {
                    'success': False,
                    'timestamp': timestamp,
                    'errors': errors,
                    'invoice_details': invoice_details,
                    'error': error_message or "Unknown error",
                }
            elif is_payment_change:
                # The payment-change response confirms success/failure only - it
                # never contains a JIR.
                success_element = response_xml.find('.//tns:PromijeniNacPlacOdgovor', namespaces=NAMESPACES)
                timestamp = _find_text(response_xml, './/tns:DatumVrijeme')

                if success_element is not None:
                    return {
                        'success': True,
                        'datetime_of_payment_method_change': timestamp,
                        'error': None,
                    }
                code = _find_text(response_xml, './/tns:SifraGreske')
                message = _find_text(response_xml, './/tns:PorukaGreske')
                error_message = f"{message or ''} - {code or ''}" if code is not None or message is not None else "Unknown error"
                return {'success': False, 'error': error_message}
            else:
                return {
                    'success': True,
                    'jir': _find_text(response_xml, './/tns:Jir'),
                    'timestamp': _find_text(response_xml, './/tns:DatumVrijeme'),
                    'error': None,
                }
        except Exception as e:  # noqa: BLE001
            _logger.exception("Fiscalization web service call failed for company %s", company.display_name)
            return {'success': False, 'jir': None, 'timestamp': None, 'error': str(e)}
        finally:
            try:
                if tmp_bundle_path and os.path.exists(tmp_bundle_path):
                    os.unlink(tmp_bundle_path)
            except Exception:  # noqa: BLE001
                _logger.warning("Failed to remove temporary CA bundle file %s", tmp_bundle_path)

    def l10n_hr_fiscalize_invoice(self, invoice):
        """Fiscalize the invoice with Croatian Tax Authority"""
        if invoice.l10n_hr_fiscalization_status == '0' and invoice.l10n_hr_fiscalization_jir:
            current_oib = invoice.partner_id.commercial_partner_id.l10n_hr_personal_oib
            old_oib = invoice.l10n_hr_fiscalization_old_recipient_oib
            current_payment_method_type = invoice.l10n_hr_payment_method_type
            old_payment_method_type = invoice.l10n_hr_old_payment_method_type
            if current_oib != old_oib:
                invoice._l10n_hr_change_payment_method(current_payment_method_type, current_oib, True)
                return True
            elif current_payment_method_type != old_payment_method_type:
                invoice._l10n_hr_change_payment_method(current_payment_method_type)
                return True
            else:
                raise UserError(self.env._(
                    "Invoice %(invoice)s has already been fiscalized with JIR: %(jir)s",
                    invoice=invoice.name,
                    jir=invoice.l10n_hr_fiscalization_jir,
                ))

        if not invoice.l10n_hr_fiscalization_zki:
            invoice.l10n_hr_fiscalization_zki = self._l10n_hr_generate_zki(invoice)

        request_data = self._l10n_hr_prepare_fiscalization_request(invoice)

        try:
            xml_doc = self._l10n_hr_generate_xml_file(request_data)
            response = self._l10n_hr_send_xml_file(xml_doc)
            if response['success']:
                fiscalization_datetime = self._l10n_hr_datetime_to_odoo(response['timestamp'])
                invoice.write({
                    'l10n_hr_fiscalization_status': '0',
                    'l10n_hr_fiscalization_jir': response['jir'],
                    'l10n_hr_invoice_sending_time': fiscalization_datetime,
                    'l10n_hr_fiscalization_error': False,
                    'l10n_hr_fiscalization_old_recipient_oib': invoice.partner_id.commercial_partner_id.l10n_hr_personal_oib,
                    'l10n_hr_old_payment_method_type': invoice.l10n_hr_payment_method_type,
                })
                return True
            else:
                invoice.write({
                    'l10n_hr_fiscalization_status': '1',
                    'l10n_hr_fiscalization_error': response['error'],
                })
                raise UserError(response['error'])
        except Exception as e:  # noqa: BLE001
            invoice.write({
                'l10n_hr_fiscalization_status': '1',
                'l10n_hr_fiscalization_error': str(e),
            })
            raise UserError(e)
