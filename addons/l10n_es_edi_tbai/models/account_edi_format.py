# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import gzip
import json
from base64 import b64encode
from datetime import datetime
from re import sub as regex_sub
from uuid import uuid4
from markupsafe import Markup, escape

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import NameOID
from lxml import etree
from pytz import timezone
from requests.exceptions import RequestException

from odoo import _, models, release
from odoo.addons.l10n_es_edi_sii.models.account_edi_format import PatchedHTTPAdapter
from odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_agencies import get_key
from odoo.addons.l10n_es_edi_tbai.models.xml_utils import (
    NS_MAP, bytes_as_block, calculate_references_digests,
    cleanup_xml_signature, fill_signature, int_as_bytes)
from odoo.exceptions import UserError, ValidationError
from odoo.tools import get_lang
from odoo.tools.float_utils import float_repr
from odoo.tools.xml_utils import cleanup_xml_node, validate_xml_from_attachment


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # OVERRIDES & EXTENSIONS
    # -------------------------------------------------------------------------

    def _needs_web_services(self):
        # EXTENDS account_edi
        return self.code == 'es_tbai' or super()._needs_web_services()

    def _is_enabled_by_default_on_journal(self, journal):
        """ Disable SII by default on a new journal when tbai is installed"""
        if self.code != 'es_sii':
            return super()._is_enabled_by_default_on_journal(journal)
        return False

    def _is_compatible_with_journal(self, journal):
        # EXTENDS account_edi
        if self.code != 'es_tbai':
            return super()._is_compatible_with_journal(journal)

        return journal.country_code == 'ES' and journal.type in ('sale', 'purchase')

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code != 'es_tbai' or move.country_code != 'ES' or not move.l10n_es_tbai_is_required:
            return super()._get_move_applicability(move)

        return {
            'post': self._l10n_es_tbai_post_invoice_edi,
            'cancel': self._l10n_es_tbai_cancel_invoice_edi,
            'edi_content': self._l10n_es_tbai_get_invoice_content_edi,
        }

    def _check_move_configuration(self, invoice):
        # EXTENDS account_edi
        errors = super()._check_move_configuration(invoice)

        if self.code != 'es_tbai' or invoice.country_code != 'ES':
            return errors

        # Ensure a certificate is available.
        if not invoice.company_id.l10n_es_edi_certificate_id:
            errors.append(_("Please configure the certificate for TicketBAI/SII."))

        # Ensure a tax agency is available.
        if not invoice.company_id.mapped('l10n_es_tbai_tax_agency')[0]:
            errors.append(_("Please specify a tax agency on your company for TicketBAI."))

        # Ensure a vat is available.
        if not invoice.company_id.vat:
            errors.append(_("Please configure the Tax ID on your company for TicketBAI."))

        # Check the refund reason
        if invoice.move_type == 'out_refund':
            if not invoice.l10n_es_tbai_refund_reason:
                raise ValidationError(_('Refund reason must be specified (TicketBAI)'))
            if invoice._is_l10n_es_tbai_simplified():
                if invoice.l10n_es_tbai_refund_reason != 'R5':
                    raise ValidationError(_('Refund reason must be R5 for simplified invoices (TicketBAI)'))
            else:
                if invoice.l10n_es_tbai_refund_reason == 'R5':
                    raise ValidationError(_('Refund reason cannot be R5 for non-simplified invoices (TicketBAI)'))

        return errors

    def _l10n_es_tbai_post_invoice_edi(self, invoice):
        # EXTENDS account_edi
        if self.code != 'es_tbai':
            return super()._post_invoice_edi(invoice)

        if invoice.is_purchase_document():
            inv_xml = False # For Ticketbai Batuz vendor bills, we get the values later as it does not need chaining, ...

        else:
            # Chain integrity check: chain head must have been REALLY posted (not timeout'ed)
            # - If called from a cron, then the re-ordering of jobs should prevent this from triggering
            # - If called manually, then the user will see this error pop up when it triggers
            chain_head = invoice.company_id._get_l10n_es_tbai_last_posted_invoice()
            if chain_head and chain_head != invoice and not chain_head._l10n_es_tbai_is_in_chain():
                raise UserError(f"TicketBAI: Cannot post invoice while chain head ({chain_head.name}) has not been posted")

            # Generate the XML values.
            inv_dict = self._get_l10n_es_tbai_invoice_xml(invoice)
            if 'error' in inv_dict[invoice]:
                return inv_dict  # XSD validation failed, return result dict

            # Store the XML as attachment to ensure it is never lost (even in case of timeout error)
            inv_xml = inv_dict[invoice]['xml_file']
            invoice._update_l10n_es_tbai_submitted_xml(xml_doc=inv_xml, cancel=False)

            # Assign unique 'chain index' from dedicated sequence
            if not invoice.l10n_es_tbai_chain_index:
                invoice.l10n_es_tbai_chain_index = invoice.company_id._get_l10n_es_tbai_next_chain_index()

        # Call the web service and get response
        res = self._l10n_es_tbai_post_to_web_service(invoice, inv_xml)

        # SUCCESS
        if res[invoice].get('success'):
            # Create attachment
            attachment = self.env['ir.attachment'].create({
                'name': invoice.name + '_post.xml',
                'datas': invoice.l10n_es_tbai_post_xml,
                'mimetype': 'application/xml',
                'res_id': invoice.id,
                'res_model': 'account.move',
            })

            # Post attachment to chatter and save it as EDI document
            test_suffix = '(test mode)' if invoice.company_id.l10n_es_edi_test_env else ''
            invoice.with_context(no_new_invoice=True).message_post(
                body=Markup("<pre>TicketBAI: posted emission XML {test_suffix}\n{message}</pre>").format(
                    test_suffix=test_suffix, message=res[invoice]['message']
                ),
                attachment_ids=[attachment.id],
            )
            res[invoice]['attachment'] = attachment

        # FAILURE
        # NOTE: 'warning' means timeout so absolutely keep the XML and chain index
        elif res[invoice].get('blocking_level') == 'error':
            invoice._update_l10n_es_tbai_submitted_xml(xml_doc=None, cancel=False)  # deletes XML
            # delete index (avoids re-trying same XML and chaining off of it)
            invoice.l10n_es_tbai_chain_index = False

        return res

    def _l10n_es_tbai_cancel_invoice_edi(self, invoice):
        # EXTENDS account_edi
        if self.code != 'es_tbai':
            return super()._cancel_invoice_edi(invoice)

        if invoice.is_purchase_document():
            cancel_xml = False # Batuz specific
        else:
            # Generate the XML values.
            cancel_dict = self._get_l10n_es_tbai_invoice_xml(invoice, cancel=True)
            if 'error' in cancel_dict[invoice]:
                return cancel_dict  # XSD validation failed, return result dict

            # Store the XML as attachment to ensure it is never lost (even in case of timeout error)
            cancel_xml = cancel_dict[invoice]['xml_file']
            invoice._update_l10n_es_tbai_submitted_xml(xml_doc=cancel_xml, cancel=True)

        # Call the web service and get response
        res = self._l10n_es_tbai_post_to_web_service(invoice, cancel_xml, cancel=True)

        # SUCCESS
        if res[invoice].get('success'):
            # Create attachment
            attachment = self.env['ir.attachment'].create({
                'name': invoice.name + '_cancel.xml',
                'datas': invoice.l10n_es_tbai_cancel_xml,
                'mimetype': 'application/xml',
                'res_id': invoice.id,
                'res_model': 'account.move',
            })

            # Post attachment to chatter
            test_suffix = '(test mode)' if invoice.company_id.l10n_es_edi_test_env else ''
            invoice.with_context(no_new_invoice=True).message_post(
                body=Markup("<pre>TicketBAI: posted cancellation XML {test_suffix}\n{message}</pre>").format(
                    test_suffix=test_suffix, message=res[invoice]['message']
                ),
                attachment_ids=[attachment.id],
            )

        # FAILURE
        # NOTE: 'warning' means timeout so absolutely keep the XML and chain index
        elif res[invoice].get('blocking_level') == 'error':
            invoice._update_l10n_es_tbai_submitted_xml(xml_doc=None, cancel=True)  # will need to be re-created

        return res

    # -------------------------------------------------------------------------
    # XML DOCUMENT
    # -------------------------------------------------------------------------

    def _l10n_es_tbai_validate_xml_with_xsd(self, xml_doc, cancel, tax_agency):
        xsd_name = get_key(tax_agency, 'xsd_name')['cancel' if cancel else 'post']
        try:
            validate_xml_from_attachment(self.env, xml_doc, xsd_name, prefix='l10n_es_edi_tbai')
        except UserError as e:
            return {'error': escape(str(e)), 'blocking_level': 'error'}
        return {}

    def _l10n_es_tbai_get_invoice_content_edi(self, invoice):
        cancel = invoice.edi_state in ('to_cancel', 'cancelled')
        if invoice.is_purchase_document():
            lroe_values = self._l10n_es_tbai_prepare_values_bi(invoice, False, cancel=cancel)
            xml_str = self.env['ir.qweb']._render('l10n_es_edi_tbai.template_LROE_240_main_recibidas', lroe_values).encode()
        else:
            xml_tree = self._get_l10n_es_tbai_invoice_xml(invoice, cancel)[invoice]['xml_file']
            xml_str = etree.tostring(xml_tree)
        return xml_str

    def _get_l10n_es_tbai_invoice_xml(self, invoice, cancel=False):
        # If previously generated XML was posted and not rejected (success or timeout), reuse it
        doc = invoice._get_l10n_es_tbai_submitted_xml(cancel)
        if doc is not None:
            return {invoice: {'xml_file': doc}}

        # Otherwise, generate a new XML
        values = {
            **invoice.company_id._get_l10n_es_tbai_license_dict(),
            **self._l10n_es_tbai_get_header_values(invoice),
            **self._l10n_es_tbai_get_subject_values(invoice, cancel),
            **self._l10n_es_tbai_get_invoice_values(invoice, cancel),
            **self._l10n_es_tbai_get_trail_values(invoice, cancel),
            'is_emission': not cancel,
            'datetime_now': datetime.now(tz=timezone('Europe/Madrid')),
            'format_date': lambda d: datetime.strftime(d, '%d-%m-%Y'),
            'format_time': lambda d: datetime.strftime(d, '%H:%M:%S'),
            'format_float': lambda f: float_repr(f, precision_digits=2),
        }
        template_name = 'l10n_es_edi_tbai.template_invoice_main' + ('_cancel' if cancel else '_post')
        xml_str = self.env['ir.qweb']._render(template_name, values)
        xml_doc = cleanup_xml_node(xml_str, remove_blank_nodes=False)
        xml_doc = self._l10n_es_tbai_sign_invoice(invoice, xml_doc)
        res = {invoice: {'xml_file': xml_doc}}

        # Optional check using the XSD
        res[invoice].update(self._l10n_es_tbai_validate_xml_with_xsd(xml_doc, cancel, invoice.company_id.l10n_es_tbai_tax_agency))
        return res

    def _l10n_es_tbai_get_header_values(self, invoice):
        return {
            'tbai_version': self.L10N_ES_TBAI_VERSION,
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

        # NOTE: TicketBai supports simplified invoices WITH recipients but we don't for now (we should for POS)
        # NOTE: TicketBAI credit notes for simplified invoices are ALWAYS simplified BUT can have a recipient even if invoice doesn't
        if invoice._is_l10n_es_tbai_simplified():
            return values  # do not set 'recipient' unless there is an actual recipient (used as condition in template)

        # === RECIPIENTS (DESTINATARIOS) ===
        nif = False
        alt_id_country = False
        partner = invoice.commercial_partner_id
        alt_id_number = partner.vat or 'NO_DISPONIBLE'
        alt_id_type = ""
        if (not partner.country_id or partner.country_id.code == 'ES') and partner.vat:
            # ES partner with VAT.
            nif = partner.vat[2:] if partner.vat.startswith('ES') else partner.vat
        elif partner.country_id.code in self.env.ref('base.europe').country_ids.mapped('code'):
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
            'partner_address': ', '.join(filter(None, [partner.street, partner.street2, partner.city])),
        }

        values.update({
            'recipient': values_dest,
        })
        return values

    def _l10n_es_tbai_get_invoice_values(self, invoice, cancel):
        # Header
        values = {'invoice': invoice}
        if cancel:
            return values

        # Credit notes (factura rectificativa)
        # NOTE values below would have to be adapted for purchase invoices (Bizkaia LROE)
        values['is_refund'] = invoice.move_type == 'out_refund'
        if values['is_refund']:
            values['credit_note_code'] = invoice.l10n_es_tbai_refund_reason
            values['credit_note_invoice'] = invoice.reversed_entry_id

        # Lines (detalle)
        refund_sign = (1 if values['is_refund'] else -1)
        invoice_lines = []
        for line in invoice.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_section', 'line_note')):
            if line.discount == 100.0:
                inverse_currency_rate = abs(line.move_id.amount_total_signed / line.move_id.amount_total) if line.move_id.amount_total else 1
                balance_before_discount = - line.price_unit * line.quantity * inverse_currency_rate
            else:
                balance_before_discount = line.balance / (1 - line.discount / 100)
            discount = (balance_before_discount - line.balance)
            line_price_total = self._l10n_es_tbai_get_invoice_line_price_total(line)

            if not any([t.l10n_es_type == 'sujeto_isp' for t in line.tax_ids]):
                total = line_price_total * abs(line.balance / line.amount_currency if line.amount_currency != 0 else 1) * -refund_sign
            else:
                total = abs(line.balance) * -refund_sign * (-1 if line_price_total < 0 else 1)
            invoice_lines.append({
                'line': line,
                'discount': discount * refund_sign,
                'unit_price': (line.balance + discount) / line.quantity * refund_sign,
                'total': total,
                'description': regex_sub(r'[^0-9a-zA-Z ]', '', line.name)[:250]
            })
        values['invoice_lines'] = invoice_lines
        # Tax details (desglose)
        importe_total, desglose, amount_retention = self._l10n_es_tbai_get_importe_desglose(invoice)
        values['amount_total'] = importe_total
        values['invoice_info'] = desglose
        values['amount_retention'] = amount_retention * refund_sign if amount_retention != 0.0 else 0.0

        # Regime codes (ClaveRegimenEspecialOTrascendencia)
        # NOTE there's 11 more codes to implement, also there can be up to 3 in total
        # See https://www.gipuzkoa.eus/documents/2456431/13761128/Anexo+I.pdf/2ab0116c-25b4-f16a-440e-c299952d683d
        com_partner = invoice.commercial_partner_id
        if not com_partner.country_id or com_partner.country_id.code in self.env.ref('base.europe').country_ids.mapped('code'):
            values['regime_key'] = ['01']
        else:
            values['regime_key'] = ['02']

        if invoice._is_l10n_es_tbai_simplified():
            values['regime_key'].append(52)  # code for simplified invoices

        return values

    def _l10n_es_tbai_get_invoice_line_price_total(self, invoice_line):
        price_total = invoice_line.price_total
        retention_tax_lines = invoice_line.tax_ids.filtered(lambda t: t.l10n_es_type == "retencion")
        if retention_tax_lines:
            line_discount_price_unit = invoice_line.price_unit * (1 - (invoice_line.discount / 100.0))
            tax_lines_no_retention = invoice_line.tax_ids - retention_tax_lines
            if tax_lines_no_retention:
                taxes_res = tax_lines_no_retention.compute_all(line_discount_price_unit,
                                                               quantity=invoice_line.quantity,
                                                               currency=invoice_line.currency_id,
                                                               product=invoice_line.product_id,
                                                               partner=invoice_line.move_id.partner_id,
                                                               is_refund=invoice_line.is_refund)
                price_total = taxes_res['total_included']
        return price_total

    def _l10n_es_tbai_get_importe_desglose(self, invoice):
        com_partner = invoice.commercial_partner_id
        sign = -1 if invoice.move_type in ('out_refund', 'in_refund') else 1
        if com_partner.country_id.code in ('ES', False) and not (com_partner.vat or '').startswith("ESN"):
            tax_details_info_vals = self._l10n_es_edi_get_invoices_tax_details_info(invoice)
            tax_amount_retention = tax_details_info_vals['tax_amount_retention']
            desglose = {'DesgloseFactura': tax_details_info_vals['tax_details_info']}
            desglose['DesgloseFactura'].update({'S1': tax_details_info_vals['S1_list'],
                                                'S2': tax_details_info_vals['S2_list']})
            importe_total = round(sign * (
                tax_details_info_vals['tax_details']['base_amount']
                + tax_details_info_vals['tax_details']['tax_amount']
                - tax_amount_retention
            ), 2)
        else:
            tax_details_info_service_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                invoice,
                filter_invl_to_apply=lambda x: any(t.tax_scope == 'service' for t in x.tax_ids)
            )
            tax_details_info_consu_vals = self._l10n_es_edi_get_invoices_tax_details_info(
                invoice,
                filter_invl_to_apply=lambda x: any(t.tax_scope == 'consu' for t in x.tax_ids)
            )
            service_retention = tax_details_info_service_vals['tax_amount_retention']
            consu_retention = tax_details_info_consu_vals['tax_amount_retention']
            desglose = {}
            if tax_details_info_service_vals['tax_details_info']:
                desglose.setdefault('DesgloseTipoOperacion', {})
                desglose['DesgloseTipoOperacion']['PrestacionServicios'] = tax_details_info_service_vals['tax_details_info']
                desglose['DesgloseTipoOperacion']['PrestacionServicios'].update(
                    {'S1': tax_details_info_service_vals['S1_list'],
                     'S2': tax_details_info_service_vals['S2_list']})

            if tax_details_info_consu_vals['tax_details_info']:
                desglose.setdefault('DesgloseTipoOperacion', {})
                desglose['DesgloseTipoOperacion']['Entrega'] = tax_details_info_consu_vals['tax_details_info']
                desglose['DesgloseTipoOperacion']['Entrega'].update(
                    {'S1': tax_details_info_consu_vals['S1_list'],
                     'S2': tax_details_info_consu_vals['S2_list']})
            importe_total = round(sign * (
                tax_details_info_service_vals['tax_details']['base_amount']
                + tax_details_info_service_vals['tax_details']['tax_amount']
                - service_retention
                + tax_details_info_consu_vals['tax_details']['base_amount']
                + tax_details_info_consu_vals['tax_details']['tax_amount']
                - consu_retention
            ), 2)
            tax_amount_retention = service_retention + consu_retention
        return importe_total, desglose, tax_amount_retention

    def _l10n_es_tbai_get_trail_values(self, invoice, cancel):
        prev_invoice = invoice.company_id._get_l10n_es_tbai_last_posted_invoice(invoice)
        # NOTE: assumtion that last posted == previous works because XML is generated on post
        if prev_invoice and not cancel:
            return {
                'chain_prev_invoice': prev_invoice
            }
        else:
            return {}

    def _l10n_es_tbai_sign_invoice(self, invoice, xml_root):
        company = invoice.company_id
        cert_private, cert_public = company.l10n_es_edi_certificate_id._get_key_pair()
        public_key = cert_public.public_key()

        # Identifiers
        document_id = "Document-" + str(uuid4())
        signature_id = "Signature-" + document_id
        keyinfo_id = "KeyInfo-" + document_id
        sigproperties_id = "SignatureProperties-" + document_id

        # Render digital signature scaffold from QWeb
        common_name = cert_public.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        org_unit = cert_public.issuer.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)[0].value
        org_name = cert_public.issuer.get_attributes_for_oid(NameOID.ORGANIZATION_NAME)[0].value
        country_name = cert_public.issuer.get_attributes_for_oid(NameOID.COUNTRY_NAME)[0].value
        values = {
            'dsig': {
                'document_id': document_id,
                'x509_certificate': bytes_as_block(cert_public.public_bytes(encoding=serialization.Encoding.DER)),
                'public_modulus': bytes_as_block(int_as_bytes(public_key.public_numbers().n)),
                'public_exponent': bytes_as_block(int_as_bytes(public_key.public_numbers().e)),
                'iso_now': datetime.now().isoformat(),
                'keyinfo_id': keyinfo_id,
                'signature_id': signature_id,
                'sigproperties_id': sigproperties_id,
                'reference_uri': "Reference-" + document_id,
                'sigpolicy_url': get_key(company.l10n_es_tbai_tax_agency, 'sigpolicy_url'),
                'sigpolicy_digest': get_key(company.l10n_es_tbai_tax_agency, 'sigpolicy_digest'),
                'sigcertif_digest': b64encode(cert_public.fingerprint(hashes.SHA256())).decode(),
                'x509_issuer_description': 'CN={}, OU={}, O={}, C={}'.format(common_name, org_unit, org_name, country_name),
                'x509_serial_number': cert_public.serial_number,
            }
        }
        xml_sig_str = self.env['ir.qweb']._render('l10n_es_edi_tbai.template_digital_signature', values)
        xml_sig = cleanup_xml_signature(xml_sig_str)

        # Complete document with signature template
        xml_root.append(xml_sig)

        # Compute digest values for references
        calculate_references_digests(xml_sig.find("SignedInfo", namespaces=NS_MAP))

        # Sign (writes into SignatureValue)
        fill_signature(xml_sig, cert_private)

        return xml_root

    # -------------------------------------------------------------------------
    # WEB SERVICE CALLS
    # -------------------------------------------------------------------------

    def _l10n_es_tbai_post_to_web_service(self, invoice, invoice_xml, cancel=False):
        company = invoice.company_id

        try:
            # Call the web service, retrieve and parse response
            success, message, response_xml = self._l10n_es_tbai_post_to_agency(
                self.env, company.l10n_es_tbai_tax_agency, invoice, invoice_xml, cancel)
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

    # -------------------------------------------------------------------------
    # WEB SERVICE METHODS
    # -------------------------------------------------------------------------
    # Provides helper methods for interacting with the Basque country's TicketBai servers.

    L10N_ES_TBAI_VERSION = 1.2

    def _l10n_es_tbai_post_to_agency(self, env, agency, invoice, invoice_xml, cancel=False):
        if agency in ('araba', 'gipuzkoa'):
            post_method, process_method = self._l10n_es_tbai_prepare_post_params_ar_gi, self._l10n_es_tbai_process_post_response_ar_gi
        elif agency == 'bizkaia':
            post_method, process_method = self._l10n_es_tbai_prepare_post_params_bi, self._l10n_es_tbai_process_post_response_bi
        params = post_method(env, agency, invoice, invoice_xml, cancel)
        response = self._l10n_es_tbai_send_request_to_agency(timeout=10, **params)
        return process_method(env, response)

    def _l10n_es_tbai_send_request_to_agency(self, *args, **kwargs):
        session = requests.Session()
        session.cert = kwargs.pop('pkcs12_data')
        session.mount("https://", PatchedHTTPAdapter())
        return session.request('post', *args, **kwargs)

    def _l10n_es_tbai_prepare_post_params_ar_gi(self, env, agency, invoice, invoice_xml, cancel=False):
        """Web service parameters for Araba and Gipuzkoa."""
        company = invoice.company_id
        return {
            'url': get_key(agency, 'cancel_url_' if cancel else 'post_url_', company.l10n_es_edi_test_env),
            'headers': {"Content-Type": "application/xml; charset=utf-8"},
            'pkcs12_data': company.l10n_es_edi_certificate_id,
            'data': etree.tostring(invoice_xml, encoding='UTF-8'),
        }

    def _l10n_es_tbai_process_post_response_ar_gi(self, env, response):
        """Government response processing for Araba and Gipuzkoa."""
        try:
            response_xml = etree.fromstring(response.content)
        except etree.XMLSyntaxError as e:
            return False, e, None

        # Error management
        message = ''
        already_received = False
        # Get message in basque if env is in basque
        msg_node_name = 'Azalpena' if get_lang(env).code == 'eu_ES' else 'Descripcion'
        for xml_res_node in response_xml.findall(r'.//ResultadosValidacion'):
            message_code = xml_res_node.find('Codigo').text
            message += message_code + ": " + xml_res_node.find(msg_node_name).text + "\n"
            if message_code in ('005', '019'):
                already_received = True  # error codes 5/19 mean XML was already received with that sequence
        response_code = int(response_xml.find(r'.//Estado').text)
        response_success = (response_code == 0) or already_received

        return response_success, message, response_xml

    def _l10n_es_tbai_get_in_invoice_values_batuz(self, invoice):
        """ For the vendor bills for Bizkaia, the structure is different than the regular Ticketbai XML (LROE)"""
        values = {
            **self._l10n_es_tbai_get_subject_values(invoice, False),
            **self._l10n_es_tbai_get_header_values(invoice),
             **invoice._get_vendor_bill_tax_values(),
            'invoice': invoice,
            'datetime_now': datetime.now(tz=timezone('Europe/Madrid')),
            'format_date': lambda d: datetime.strftime(d, '%d-%m-%Y'),
            'format_time': lambda d: datetime.strftime(d, '%H:%M:%S'),
            'format_float': lambda f: float_repr(f, precision_digits=2),
        }
        # Check if intracom
        mod_303_10 = self.env.ref('l10n_es.mod_303_10')
        mod_303_11 = self.env.ref('l10n_es.mod_303_11')
        tax_tags = invoice.invoice_line_ids.tax_ids.invoice_repartition_line_ids.tag_ids
        intracom = bool(tax_tags & (mod_303_10 + mod_303_11))
        values['regime_key'] = ['09'] if intracom else ['01']
        # Credit notes (factura rectificativa)
        values['is_refund'] = invoice.move_type == 'in_refund'
        if values['is_refund']:
            values['credit_note_code'] = invoice.l10n_es_tbai_refund_reason
            values['credit_note_invoice'] = invoice.reversed_entry_id
        values['tipofactura'] = 'F1'
        return values

    def _l10n_es_tbai_prepare_values_bi(self, invoice, invoice_xml, cancel=False):
        sender = invoice.company_id
        lroe_values = {
            'is_emission': not cancel,
            'sender': sender,
            'sender_vat': sender.vat[2:] if sender.vat.startswith('ES') else sender.vat,
            'fiscal_year': str(invoice.date.year),
        }
        if invoice.is_sale_document():
            lroe_values.update({'tbai_b64_list': [b64encode(etree.tostring(invoice_xml, encoding="UTF-8")).decode()]})
        else:
            lroe_values.update(self._l10n_es_tbai_get_in_invoice_values_batuz(invoice))
        return lroe_values

    def _l10n_es_tbai_prepare_post_params_bi(self, env, agency, invoice, invoice_xml, cancel=False):
        """Web service parameters for Bizkaia."""
        lroe_values = self._l10n_es_tbai_prepare_values_bi(invoice, invoice_xml, cancel=cancel)
        if invoice.is_purchase_document():
            lroe_str = env['ir.qweb']._render('l10n_es_edi_tbai.template_LROE_240_main_recibidas', lroe_values)
            invoice.l10n_es_tbai_post_xml = b64encode(lroe_str.encode())
        else:
            lroe_str = env['ir.qweb']._render('l10n_es_edi_tbai.template_LROE_240_main', lroe_values)

        lroe_xml = cleanup_xml_node(lroe_str)
        lroe_str = etree.tostring(lroe_xml, encoding="UTF-8")
        lroe_bytes = gzip.compress(lroe_str)

        company = invoice.company_id
        return {
            'url': get_key(agency, 'cancel_url_' if cancel else 'post_url_', company.l10n_es_edi_test_env),
            'headers': {
                'Accept-Encoding': 'gzip',
                'Content-Encoding': 'gzip',
                'Content-Length': str(len(lroe_str)),
                'Content-Type': 'application/octet-stream',
                'eus-bizkaia-n3-version': '1.0',
                'eus-bizkaia-n3-content-type': 'application/xml',
                'eus-bizkaia-n3-data': json.dumps({
                    'con': 'LROE',
                    'apa': '1.1' if invoice.is_sale_document() else '2',
                    'inte': {
                        'nif': lroe_values['sender_vat'],
                        'nrs': invoice.company_id.name,
                    },
                    'drs': {
                        'mode': '240',
                        # NOTE: modelo 140 for freelancers (in/out invoices)
                        # modelo 240 for legal entities (lots of account moves ?)
                        'ejer': str(invoice.date.year),
                    }
                }),
            },
            'pkcs12_data': invoice.company_id.l10n_es_edi_certificate_id,
            'data': lroe_bytes,
        }

    def _l10n_es_tbai_process_post_response_bi(self, env, response):
        """Government response processing for Bizkaia."""
        # GLOBAL STATUS (LROE)
        response_messages = []
        response_success = True
        if response.headers['eus-bizkaia-n3-tipo-respuesta'] != "Correcto":
            code = response.headers['eus-bizkaia-n3-codigo-respuesta']
            response_messages.append(code + ': ' + response.headers['eus-bizkaia-n3-mensaje-respuesta'])
            response_success = False

        response_data = response.content
        response_xml = None
        if response_data:
            try:
                response_xml = etree.fromstring(response_data)
            except etree.XMLSyntaxError as e:
                response_success = False
                response_messages.append(str(e))
        else:
            response_success = False
            response_messages.append(_('No XML response received from LROE.'))

        # INVOICE STATUS (only one in batch)
        # Get message in basque if env is in basque
        if response_xml is not None:
            msg_node_name = 'DescripcionErrorRegistro' + ('EU' if get_lang(env).code == 'eu_ES' else 'ES')
            invoice_success = response_xml.find(r'.//EstadoRegistro').text == "Correcto"
            if not invoice_success:
                invoice_code = response_xml.find(r'.//CodigoErrorRegistro').text
                if invoice_code == "B4_2000003":  # already received
                    invoice_success = True
                response_messages.append(invoice_code + ": " + (response_xml.find(rf'.//{msg_node_name}').text or ''))

        return response_success and invoice_success, '<br/>'.join(response_messages), response_xml
