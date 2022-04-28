# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode
from datetime import datetime
from functools import partial
from re import sub as regex_sub
from uuid import uuid4

from cryptography.hazmat.primitives import hashes, serialization
from odoo import _, models, release
from odoo.addons.l10n_es_edi_tbai.models.web_services import TBAI_VERSION, get_web_services_for_agency
from odoo.addons.l10n_es_edi_tbai.models.xml_utils import L10nEsTbaiXmlUtils
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_repr
from pytz import timezone
from requests.exceptions import RequestException


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # EDI OVERRIDDEN METHODS
    # -------------------------------------------------------------------------

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        if self.code != 'es_tbai':
            return super()._is_required_for_invoice(invoice)

        # TODO for Bizkaia, move_type in ('in_invoice', 'in_refund') also yields True
        return invoice.l10n_es_tbai_is_required and invoice.move_type in ('out_invoice', 'out_refund')

    def _needs_web_services(self):
        # OVERRIDE
        return self.code == 'es_tbai' or super()._needs_web_services()

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        if self.code != 'es_tbai':
            return super()._is_compatible_with_journal(journal)

        return journal.country_code == 'ES'

    def _get_invoice_edi_content(self, invoice):
        # OVERRIDE
        if self.code != 'es_tbai':
            return super()._get_invoice_edi_content(invoice)
        return self._get_l10n_es_tbai_invoice_xml(invoice)

    def _check_move_configuration(self, invoice):
        # OVERRIDE
        if self.code != 'es_tbai':
            return super()._check_move_configuration(invoice)
        # Ensure a certificate is available.
        certificate = invoice.company_id.l10n_es_tbai_certificate_id
        if not certificate:
            return {
                'error': _("Please configure the certificate for TicketBAI."),
                'blocking_level': 'error',
            }

        # Ensure a tax agency is available.
        tax_agency = invoice.company_id.mapped('l10n_es_tbai_tax_agency')[0]
        if not tax_agency:
            return {
                'error': _("Please specify a tax agency on your company for TicketBAI."),
                'blocking_level': 'error',
            }

        return None

    def _post_invoice_edi(self, invoice):
        # OVERRIDE
        if self.code != 'es_tbai':
            return super()._post_invoice_edi(invoice)

        # Configuration check
        error_dict = self._check_move_configuration(invoice)
        if error_dict is not None:
            return {invoice: error_dict}

        # Chain integrity check: chain head must have been REALLY posted (not timeout'ed)
        chain_head = invoice.company_id.get_l10n_es_tbai_last_posted_invoice()
        if chain_head.edi_state == 'to_send' and chain_head != invoice:
            raise UserError(f"TicketBAI: Cannot post invoice while chain head ({chain_head.name}) has not been posted")

        # Generate the XML values.
        inv_xml = self._get_l10n_es_tbai_invoice_xml(invoice)

        # Optional check using the XSD
        xsd_id = f'l10n_es_edi_tbai.{invoice.company_id.l10n_es_tbai_tax_agency}_ticketBaiV1-2.xsd'
        res = {invoice: self._l10n_es_tbai_verify_xml(inv_xml, xsd_id)}
        if 'error' in res[invoice]:
            return res

        # Assign unique 'chain index' from dedicated sequence
        if not invoice.l10n_es_tbai_chain_index:
            invoice.l10n_es_tbai_chain_index = invoice.company_id._get_l10n_es_tbai_next_chain_index()

        # Call the web service and get response
        res.update(self._l10n_es_tbai_post_to_web_service(invoice, inv_xml))
        response_xml = res[invoice]['response']

        # TIMEOUT / NO RESPONSE: success is undetermined
        if response_xml is None:
            pass

        # SUCCESS
        elif res[invoice].get('success'):
            # Attachment: post to chatter and save as EDI document
            test_suffix = '(test mode)' if invoice.company_id.l10n_es_edi_test_env else ''
            invoice.with_context(no_new_invoice=True).message_post(
                body=f"<pre>TicketBAI: posted emission XML {test_suffix}\n{res[invoice]['message']}</pre>",
                attachment_ids=invoice.l10n_es_tbai_post_xml_id.ids,
            )
            res[invoice]['attachment'] = invoice.l10n_es_tbai_post_xml_id

        # FAILURE
        else:
            invoice._update_l10n_es_tbai_submitted_xml(xml_doc=None, cancel=False)  # deletes XML
            # delete index (avoids re-trying same XML and chaining off of it)
            invoice.l10n_es_tbai_chain_index = False

        return res

    def _cancel_invoice_edi(self, invoice):
        # OVERRIDE
        if self.code != 'es_tbai':
            return super()._post_invoice_edi(invoice)

        # Configuration check
        error_dict = self._check_move_configuration(invoice)
        if error_dict is not None:
            return {invoice: error_dict}

        # Generate the XML values.
        cancel_xml = self._get_l10n_es_tbai_invoice_xml(invoice, cancel=True)

        # Optional check using the XSD
        xsd_id = f'l10n_es_edi_tbai.{invoice.company_id.l10n_es_tbai_tax_agency}_Anula_ticketBaiV1-2.xsd'
        res = {invoice: self._l10n_es_tbai_verify_xml(cancel_xml, xsd_id)}
        if 'error' in res[invoice]:
            return res

        # Call the web service and get response
        res.update(self._l10n_es_tbai_post_to_web_service(invoice, cancel_xml, cancel=True))
        response_xml = res[invoice]['response']

        # TIMEOUT / NO RESPONSE: success is undetermined
        if response_xml is None:
            pass

        # SUCCESS
        elif res[invoice].get('success'):
            test_suffix = '(test mode)' if invoice.company_id.l10n_es_edi_test_env else ''
            # Attachment: save to chatter (TODO save as EDI document)
            invoice.with_context(no_new_invoice=True).message_post(
                body=f"<pre>TicketBAI: posted cancellation XML {test_suffix}\n{res[invoice]['message']}</pre>",
                attachment_ids=invoice.l10n_es_tbai_cancel_xml_id.ids,
            )

        # FAILURE
        else:
            invoice._update_l10n_es_tbai_submitted_xml(xml_doc=None, cancel=True)  # will need to be re-created

        return res

    # -------------------------------------------------------------------------
    # TBAI XML VERIFY
    # -------------------------------------------------------------------------

    def _l10n_es_tbai_verify_xml(self, xml, xsd_id):
        xsd_attachment = self.env.ref(xsd_id, raise_if_not_found=False)
        if xsd_attachment:
            try:
                L10nEsTbaiXmlUtils._validate_format_xsd(xml, xsd_id)
            except UserError as e:
                return {
                    'error': str(e).split('\\n'),
                    'blocking_level': 'error',
                }
        return {}

    # -------------------------------------------------------------------------
    # TBAI XML BUILD
    # -------------------------------------------------------------------------

    def _get_l10n_es_tbai_invoice_xml(self, invoice, cancel=False):
        # If peviously generated XML was posted and not rejected (success or timeout), reuse it
        doc = invoice._get_l10n_es_tbai_submitted_xml(cancel)
        if doc is not None:
            return doc

        # Otherwise, generate a new XML
        values = {
            'is_emission': not cancel,
            'datetime_now': datetime.now(tz=timezone('Europe/Madrid')),
            'datetime_strftime': datetime.strftime,
            'timezone_eus': timezone,
            'float_repr': partial(float_repr, precision_digits=2),
        }
        values.update(self._l10n_es_tbai_get_header_values(invoice))
        values.update(self._l10n_es_tbai_get_subject_values(invoice, cancel))
        values.update(self._l10n_es_tbai_get_invoice_values(invoice, cancel))
        values.update(self._l10n_es_tbai_get_trail_values(invoice, cancel))
        template_name = 'l10n_es_edi_tbai.template_invoice_main' + ('_cancel' if cancel else '_post')
        xml_str = self.env.ref(template_name)._render(values)
        xml_doc = L10nEsTbaiXmlUtils._cleanup_xml_content(xml_str)
        xml_doc = self._l10n_es_tbai_sign_invoice(invoice, xml_doc)

        # Store the XML as attachment to ensure it is never lost (even in case of timeout error)
        invoice._update_l10n_es_tbai_submitted_xml(xml_doc=xml_doc, cancel=cancel)

        return xml_doc

    def _l10n_es_tbai_get_header_values(self, invoice):
        return {
            'tbai_version': TBAI_VERSION,
            'odoo_version': release.version,
        }

    def _l10n_es_tbai_get_subject_values(self, invoice, cancel):
        # === SENDER (EMISOR) ===
        sender = invoice.company_id
        values = {
            'sender_vat': sender.vat[2:] if sender.vat.startswith('ES') else sender.vat,
            'sender': sender,
        }
        if cancel:
            return values  # cancellation invoices do not specify recipients (they stay the same)

        # TODO TicketBai supports simplified invoices WITH recipients: use checkbox in invoice (optional until POS implemented)
        # Note that credit notes for simplified invoices are ALWAYS simplified BUT can have a recipient even if invoice doesn't
        if invoice._is_l10n_es_tbai_simplified():
            return values  # do not set 'recipient' unless there is an actual recipient (used as condition in template)

        # === RECIPIENTS (DESTINATARIOS) ===
        eu_country_codes = set(self.env.ref('base.europe').country_ids.mapped('code'))

        nif = False
        alt_id_country = False
        partner = invoice.commercial_partner_id
        alt_id_number = partner.vat or 'NO_DISPONIBLE'
        alt_id_type = ""
        if (not partner.country_id or partner.country_id.code == 'ES') and partner.vat:
            # ES partner with VAT.
            nif = partner.vat[2:] if partner.vat.startswith('ES') else partner.vat
        elif partner.country_id.code in eu_country_codes:
            # European partner
            alt_id_type = '02'
        else:
            # Non-european partner
            if partner.vat:
                alt_id_type = '04'
            else:
                alt_id_type = '06'
            if partner.country_id:
                alt_id_country = partner.country_id.code

        values_dest = {
            'nif': nif,
            'alt_id_country': alt_id_country,
            'alt_id_number': alt_id_number,
            'alt_id_type': alt_id_type,
            'partner': partner,
            'partner_address': ', '.join(filter(lambda x: x, [partner.street, partner.street2, partner.city])),
        }

        values.update({
            'recipient': values_dest,
            # TODO for Bizkaia, option below can be "T" (if "in" invoice)
            'thirdparty_or_recipient': "D",  # thirdparty = Tercero, recipient = Destinatario
        })
        return values

    def _l10n_es_tbai_get_invoice_values(self, invoice, cancel):
        # Header
        values = {'invoice': invoice}
        if cancel:
            return values

        # Credit notes (factura rectificativa)
        # TODO values below would have to be adapted for in_invoices (Bizkaia LROE)
        values['is_refund'] = invoice.move_type == 'out_refund'
        values['is_simplified'] = invoice._is_l10n_es_tbai_simplified()
        if values['is_refund']:
            values['credit_note_code'] = invoice.l10n_es_tbai_refund_reason
            values['credit_note_invoice'] = invoice.reversed_entry_id

        # Lines (detalle)
        values['invoice_lines'] = [{
            'line': line,
            'description': regex_sub(r'[^0-9a-zA-Z ]', '', line.name)[:250],  # only keep characters allowed in description
        } for line in invoice.invoice_line_ids.filtered(lambda line: not line.display_type)]

        # Tax codes & tax details (claves régimen & desglose)
        # TODO ClaveRegimenEspecialOTrascendencia: there's 15 more codes to implement, also there can be up to 3 in total
        # See https://www.gipuzkoa.eus/documents/2456431/13761128/Anexo+I.pdf/2ab0116c-25b4-f16a-440e-c299952d683d
        edi_format_sii = self.env['account.edi.format']
        values['invoice_details'] = edi_format_sii._l10n_es_edi_get_invoices_info(invoice)[0]['FacturaExpedida']

        return values

    def _l10n_es_tbai_get_trail_values(self, invoice, cancel):
        prev_invoice = invoice.company_id.get_l10n_es_tbai_last_posted_invoice()
        if prev_invoice and not cancel:
            return {
                'chain_prev_invoice': prev_invoice
            }
        else:
            return {}

    def _l10n_es_tbai_sign_invoice(self, invoice, xml_root):
        company = invoice.company_id
        cert_private, cert_public = company.l10n_es_tbai_certificate_id._get_key_pair()
        public_key = cert_public.public_key()

        p12 = company.l10n_es_tbai_certificate_id._get_p12()
        cert_p12 = p12.get_certificate()
        issuer = cert_p12.get_issuer()

        # Identifiers
        document_id = "Document-" + str(uuid4())
        signature_id = "Signature-" + document_id
        keyinfo_id = "KeyInfo-" + document_id
        sigproperties_id = "SignatureProperties-" + document_id

        # Render digital signature scaffold from QWeb
        web_services = get_web_services_for_agency(agency=company.l10n_es_tbai_tax_agency, env=self.env)
        values = {
            'dsig': {
                'document_id': document_id,
                'x509_certificate': L10nEsTbaiXmlUtils._base64_print(b64encode(cert_public.public_bytes(encoding=serialization.Encoding.DER))),
                'public_modulus': L10nEsTbaiXmlUtils._base64_print(b64encode(L10nEsTbaiXmlUtils._int_to_bytes(public_key.public_numbers().n))),
                'public_exponent': L10nEsTbaiXmlUtils._base64_print(b64encode(L10nEsTbaiXmlUtils._int_to_bytes(public_key.public_numbers().e))),
                'iso_now': datetime.now().isoformat(),
                'keyinfo_id': keyinfo_id,
                'signature_id': signature_id,
                'sigproperties_id': sigproperties_id,
                'reference_uri': "Reference-" + document_id,
                'sigpolicy_description': "Política de Firma TicketBAI 1.0",  # í = &#237;
                'sigpolicy_url': web_services.get_sigpolicy_url(),
                'sigpolicy_digest': web_services.get_sigpolicy_digest(),
                'sigcertif_digest': b64encode(cert_public.fingerprint(hashes.SHA256())).decode(),
                'x509_issuer_description': f"CN={issuer.CN}, OU={issuer.OU}, O={issuer.O}, C={issuer.C}",
                'x509_serial_number': cert_p12.get_serial_number(),
            }
        }
        xml_sig_str = self.env.ref('l10n_es_edi_tbai.template_digital_signature')._render(values)
        xml_sig = L10nEsTbaiXmlUtils._cleanup_xml_signature(xml_sig_str)

        # Complete document with signature template
        xml_root.append(xml_sig)

        # Compute digest values for references
        L10nEsTbaiXmlUtils._reference_digests(xml_sig.find("ds:SignedInfo", namespaces=L10nEsTbaiXmlUtils.NS_MAP))

        # Sign (writes into SignatureValue)
        L10nEsTbaiXmlUtils._fill_signature(xml_sig, cert_private)

        return xml_root

    # -------------------------------------------------------------------------
    # TBAI SERVER CALLS
    # -------------------------------------------------------------------------

    def _l10n_es_tbai_post_to_web_service(self, invoice, invoice_xml, cancel=False):
        company = invoice.company_id
        tbai_services = get_web_services_for_agency(agency=company.l10n_es_tbai_tax_agency, env=self.env)

        try:
            # Call the web service, retrieve and parse response
            success, message, response_xml = tbai_services.post(invoice, invoice_xml, cancel)
        except (ValueError, RequestException) as e:
            # In case of timeout / request exception, return warning
            return {invoice: {
                'error': str(e),
                'blocking_level': 'warning',
                'response': None,
            }}

        if success:
            return {invoice: {
                'success': True,
                'message': message,
                'response': response_xml,
            }}
        else:
            return {invoice: {
                'error': message,
                'blocking_level': 'error',
                'response': response_xml,
            }}
