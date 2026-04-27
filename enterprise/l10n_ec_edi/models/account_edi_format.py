# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from functools import partial
from uuid import uuid4

from lxml import etree
from markupsafe import Markup, escape

from odoo import _, api, models
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_VAT_SUBTAXES
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.tools import float_compare, float_is_zero, float_repr, float_round, html_escape
from odoo.tools.xml_utils import cleanup_xml_node
from pytz import timezone
from requests.exceptions import RequestException
from odoo.tools.zeep import Client
from odoo.tools.zeep.exceptions import Error as ZeepError
from odoo.addons.l10n_ec_edi.models.xml_utils import (
    NS_MAP,
    calculate_references_digests,
    cleanup_xml_signature,
    fill_signature,
)


TEST_URL = {
    'reception': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
    'authorization': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
}

PRODUCTION_URL = {
    'reception': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl',
    'authorization': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline?wsdl',
}

DEFAULT_TIMEOUT_WS = 20

class AccountEdiFormat(models.Model):

    _inherit = 'account.edi.format'

    def _is_compatible_with_journal(self, journal):
        # EXTENDS account.edi.format
        # For Ecuador include the journals for sales invoices, purchase liquidations and purchase withholds
        if self.code != 'ecuadorian_edi':
            return super()._is_compatible_with_journal(journal)
        return journal.country_code == 'EC' and ((journal.type == 'sale' and journal.l10n_latam_use_documents)
                or (journal.type == 'general' and journal.l10n_ec_withhold_type == 'in_withhold')
                or (journal.type == 'purchase' and journal.l10n_ec_is_purchase_liquidation))

    def _needs_web_services(self):
        # EXTENDS account.edi.format
        return self.code == 'ecuadorian_edi' or super(AccountEdiFormat, self)._needs_web_services()

    def _get_move_applicability(self, move):
        # EXTENDS account.edi.format
        self.ensure_one()
        if self.code != 'ecuadorian_edi' or move.country_code != 'EC':
            return super()._get_move_applicability(move)

        internal_type = move.l10n_latam_document_type_id.internal_type
        if move.move_type in ('out_invoice', 'out_refund') or internal_type == 'purchase_liquidation':
            return {
                'post': self._post_invoice_edi,
                'cancel': self._cancel_invoice_edi,
                'edi_content': self._get_invoice_edi_content,
            }
        elif move.journal_id.l10n_ec_withhold_type == 'in_withhold':
            return {
                'post': self._post_withhold_edi,
                'cancel': self._cancel_withhold_edi,
                'edi_content': self._get_withhold_edi_content,
            }

    def _check_move_configuration(self, move):
        # EXTENDS account.edi.format
        errors = super()._check_move_configuration(move)

        if self.code != 'ecuadorian_edi' or move.country_code != 'EC':
            return errors

        if (move.move_type in ('out_invoice', 'out_refund')
                or move.l10n_latam_document_type_id.internal_type == 'purchase_liquidation'
                or move.journal_id.l10n_ec_withhold_type == 'in_withhold'):
            journal = move.journal_id
            address = journal.l10n_ec_emission_address_id
            if not move.company_id.vat:
                errors.append(_("You must set a VAT number for company %s", move.company_id.display_name))

            if not address:
                errors.append(_("You must set an emission address on journal %s", journal.display_name))

            if address and not address.street:
                errors.append(_("You must set an address on contact %s, field Street must be filled", address.display_name))

            if address and not address.commercial_partner_id.street:
                errors.append(_(
                    "You must set a headquarter address on contact %s, field Street must be filled",
                    address.commercial_partner_id.display_name
                ))

            if not move.commercial_partner_id.vat:
                errors.append(_("You must set a VAT number for partner %s", move.commercial_partner_id.display_name))

            if not move.l10n_ec_sri_payment_id and move.move_type in ['out_invoice', 'in_invoice']: # needed for documents excluding credit notes
                errors.append(_("You must set the Payment Method SRI on document %s", move.display_name))

            if not move.l10n_latam_document_number:
                errors.append(_("You must set the Document Number on document %s", move.display_name))

            if move._l10n_ec_is_withholding():
                for line in move.l10n_ec_withhold_line_ids:
                    if not line.l10n_ec_withhold_invoice_id.l10n_ec_sri_payment_id:
                        errors.append(_(
                            "You must set the Payment Method SRI on document %s",
                            line.l10n_ec_withhold_invoice_id.name
                        ))
                    if not line.l10n_ec_withhold_invoice_id:
                        errors.append(_("Please use the wizard on the invoice to generate the withholding."))
                    code = move._l10n_ec_wth_map_tax_code(line)
                    if not code:
                        errors.append(_("Wrong tax (%(tax)s) for document %(document)s", tax=line.tax_ids[0].name, document=move.display_name))
            else:
                unsupported_tax_types = set()
                vat_subtaxes = (lambda l: L10N_EC_VAT_SUBTAXES[l.tax_group_id.l10n_ec_type])
                tax_groups = self.env['account.move']._l10n_ec_map_tax_groups
                for line in move.line_ids.filtered(lambda l: l.tax_group_id.l10n_ec_type):
                    if not (vat_subtaxes(line) and tax_groups(line)):
                        unsupported_tax_types.add(line.tax_group_id.l10n_ec_type)
                for tax_type in unsupported_tax_types:
                    errors.append(_("Tax type not supported: %s", tax_type))

        if not move.company_id.sudo().l10n_ec_edi_certificate_id and not move.company_id._l10n_ec_is_demo_environment():
            errors.append(_("You must select a valid certificate in the settings for company %s", move.company_id.name))

        if not move.company_id.l10n_ec_legal_name:
            errors.append(_("You must define a legal name in the settings for company %s", move.company_id.name))

        if not move.commercial_partner_id.country_id:
            errors.append(_("You must set a Country for Partner: %s", move.commercial_partner_id.name))

        if move.move_type == "out_refund" and not move.reversed_entry_id:
            errors.append(_(
                "Credit Note %s must have an original invoice related, try to 'Add Credit Note' from invoice",
                move.display_name
            ))

        if move.l10n_latam_document_type_id.internal_type == 'debit_note' and not move.debit_origin_id:
            errors.append(_(
                "Debit Note %s must have an original invoice related, try to 'Add Debit Note' from invoice",
                move.display_name
            ))
        return errors

    # ===== Post & Cancel methods =====

    def _l10n_ec_post_move_edi(self, moves):
        res = {}
        for move in moves:
            xml_string, errors = self._l10n_ec_generate_xml(move)

            # Error management
            if errors:
                blocking_level = 'error'
                attachment = None
            else:
                errors, blocking_level, attachment = self._l10n_ec_send_xml_to_authorize(move, xml_string)

            res.update({
                move: {
                    'success': not errors,
                    'error': '<br/>'.join([html_escape(e) for e in errors]),
                    'attachment': attachment,
                    'blocking_level': blocking_level,
                }}
            )
        return res

    def _post_withhold_edi(self, withholds):
        return self._l10n_ec_post_move_edi(withholds)

    def _post_invoice_edi(self, invoices):
        if self.code != 'ecuadorian_edi':
            return super(AccountEdiFormat, self)._post_invoice_edi(invoices)
        return self._l10n_ec_post_move_edi(invoices)

    def _l10n_ec_cancel_move_edi(self, moves):
        res = {}
        for move in moves:
            if not move.company_id.l10n_ec_production_env:
                # In test environment, act as if invoice had already been cancelled for the govt
                auth_num, auth_date, errors, warnings = False, False, [], []
                move.with_context(no_new_invoice=True).message_post(
                    body=escape(
                        _(
                            "{}This is a DEMO environment, for which SRI has no portal.{}"
                            "For the purpose of testing all flows, we act as if the document had been cancelled for the government.{}"
                            "In a production environment, you will first have to use the SRI portal to cancel the invoice.",
                        )
                    ).format(Markup('<strong>'), Markup('</strong><br/>'), Markup('<br/>')),
                )
            else:
                _auth_state, auth_num, auth_date, errors, warnings = self._l10n_ec_get_authorization_status_new(move.company_id, move.l10n_ec_authorization_number)
                if auth_num:
                    errors.append(
                        _("You cannot cancel a document that is still authorized (%(authorization_num)s, %(authorization_date)s), check the SRI portal",
                          authorization_num=auth_num, authorization_date=auth_date),
                    )
            if not errors:
                move.l10n_ec_authorization_date = False  # unset upon cancelling
            res[move] = {
                'success': not errors,
                'error': '<br/>'.join([html_escape(e) for e in (errors or warnings)]),
                'blocking_level': 'error' if errors else 'warning',
            }
        return res

    def _cancel_withhold_edi(self, withholds):
        return self._l10n_ec_cancel_move_edi(withholds)

    def _cancel_invoice_edi(self, invoices):
        if self.code != 'ecuadorian_edi':
            return super(AccountEdiFormat, self)._cancel_invoice_edi(invoices)
        return self._l10n_ec_cancel_move_edi(invoices)

    # ===== XML generation methods =====

    def _get_invoice_edi_content(self, invoice):
        # EXTENDS account_edi
        if self.code != 'ecuadorian_edi':
            return super()._get_invoice_edi_content(invoice)
        return self._l10n_ec_generate_xml(invoice)[0].encode()

    def _get_withhold_edi_content(self, withhold):
        # EXTENDS account_edi
        return self._l10n_ec_generate_xml(withhold)[0].encode()

    def _l10n_ec_get_xml_common_values(self, move):
        internal_type = move.l10n_latam_document_type_id.internal_type
        # Reimbursements
        # If it's withholding, we must return the origin invoice that has the reimbursements
        reimbursement_move_ids = (move._l10n_ec_is_withholding() and move.line_ids.l10n_ec_withhold_invoice_id) or move
        reimbursement_vals = move._l10n_ec_get_reimbursement_common_values(reimbursement_move_ids)

        return {
            'move': move,
            'sequential': move.name.split('-')[2].rjust(9, '0'),
            'company': move.company_id,
            'journal': move.journal_id,
            'partner': move.commercial_partner_id,
            'partner_sri_code': move.partner_id._get_sri_code_for_partner().value,
            'is_cnote': internal_type == 'credit_note',
            'is_dnote': internal_type == 'debit_note',
            'is_liquidation': internal_type == 'purchase_liquidation',
            'is_invoice': internal_type == 'invoice',
            'is_withhold': move.journal_id.l10n_ec_withhold_type == 'in_withhold',
            'reimbursement_vals': reimbursement_vals,
            'format_num_2': self._l10n_ec_format_number,
            'format_num_6': partial(self._l10n_ec_format_number, decimals=6),
            'currency_round': move.company_currency_id.round,
            'clean_str': self._l10n_ec_remove_newlines,
            'strftime': partial(datetime.strftime, format='%d/%m/%Y'),
        }

    def l10n_ec_merge_negative_and_positive_line(self, negative_line_tax_data, tax_data, precision_digits):
        def merge_tax_datas(tax_data_to_add, tax_data_to_nullify):
            keys_to_merge = ['base_amount_currency', 'base_amount', 'tax_amount_currency', 'tax_amount']
            for key in keys_to_merge:
                tax_data_to_add[key] += tax_data_to_nullify[key]
                tax_data_to_nullify[key] = 0.0

        if tax_data['base_amount'] > abs(negative_line_tax_data['base_amount']):
            merge_tax_datas(tax_data, negative_line_tax_data)
            for tax in tax_data['tax_details']:
                merge_tax_datas(tax_data['tax_details'][tax], negative_line_tax_data['tax_details'][tax])
        else:
            merge_tax_datas(negative_line_tax_data, tax_data)
            for tax in tax_data['tax_details']:
                merge_tax_datas(negative_line_tax_data['tax_details'][tax], tax_data['tax_details'][tax])

    def _l10n_ec_dispatch_negative_line_into_discounts(self, negative_line_tax_data, positive_tax_details_sorted, precision_digits):
        def is_same_taxes(taxes_1, taxes_2):
            def tax_dict_to_tuple(tax_dict):
                return (tax_dict['code'], tax_dict['code_percentage'], tax_dict['rate'], tax_dict['tax_group_id'])
            return sorted(taxes_1, key=tax_dict_to_tuple) == sorted(taxes_2, key=tax_dict_to_tuple)

        for tax_data in positive_tax_details_sorted:
            if (
                not float_is_zero(tax_data['base_amount'], precision_digits=precision_digits)
                and is_same_taxes(negative_line_tax_data['tax_details'].keys(), tax_data['tax_details'].keys())
            ):
                self.l10n_ec_merge_negative_and_positive_line(negative_line_tax_data, tax_data, precision_digits)
                if float_is_zero(negative_line_tax_data['base_amount'], precision_digits=precision_digits):
                    continue
        if not float_is_zero(negative_line_tax_data['base_amount'], precision_digits=precision_digits):
            return [_("Failed to dispatch negative lines into discounts.")]

    def _l10n_ec_remove_negative_lines_from_move_info(self, move_info):
        precision_digits = move_info['move'].company_id.currency_id.decimal_places

        tax_details_per_line = move_info['taxes_data']['tax_details_per_record']
        negative_lines = [line for line, tax_data in tax_details_per_line.items() if float_compare(tax_data['base_amount'], 0.0, precision_digits=precision_digits) == -1]

        if not negative_lines:
            return []

        negative_amount_total = sum(tax_details_per_line[line]['base_amount'] for line in negative_lines)
        move_info['discount_total'] += abs(negative_amount_total)

        positive_tax_details_sorted = sorted(
            [value for key, value in tax_details_per_line.items() if key not in negative_lines],
            key=lambda tax_data: tax_data['base_amount'],
            reverse=True
        )
        for negative_line in negative_lines:
            error = self._l10n_ec_dispatch_negative_line_into_discounts(tax_details_per_line[negative_line], positive_tax_details_sorted, precision_digits)
            if error:
                return error
            tax_details_per_line.pop(negative_line)

        return []

    def _l10n_ec_generate_xml(self, move):
        # Gather XML values
        move_info = self._l10n_ec_get_xml_common_values(move)
        if move.journal_id.l10n_ec_withhold_type:  # withholds
            doc_type = 'withhold'
            template = 'l10n_ec_edi.withhold_template'
            move_info.update(move._l10n_ec_get_withhold_edi_data())
        else:  # invoices
            doc_type = move.l10n_latam_document_type_id.internal_type
            template = {
                'credit_note': 'l10n_ec_edi.credit_note_template',
                'debit_note': 'l10n_ec_edi.debit_note_template',
                'invoice': 'l10n_ec_edi.invoice_template',
                'purchase_liquidation': 'l10n_ec_edi.purchase_liquidation_template',
            }[doc_type]
            move_info.update(move._l10n_ec_get_invoice_edi_data())

        # Generate XML document
        errors = []
        if move_info.get('taxes_data'):
            errors += self._l10n_ec_remove_negative_lines_from_move_info(move_info)
        xml_content = self.env['ir.qweb']._render(template, move_info)
        xml_content = cleanup_xml_node(xml_content)

        # Sign the document
        xml_signed = self.sudo()._l10n_ec_generate_signed_xml(move.company_id, xml_content)

        return xml_signed, errors

    @api.model
    def _l10n_ec_generate_signed_xml(self, company_id, xml_node_or_string):
        if company_id._l10n_ec_is_demo_environment():  # unless we're in a test environment without certificate
            xml_node_or_string = etree.tostring(xml_node_or_string, encoding='UTF-8', xml_declaration=True, pretty_print=True)
        else:
            certificate_sudo = company_id.sudo().l10n_ec_edi_certificate_id

            # Signature rendering: prepare reference identifiers
            signature_id = f"Signature{uuid4()}"
            qweb_values = {
                'signature_id': signature_id,
                'signature_property_id': f'{signature_id}-SignedPropertiesID{uuid4()}',
                'certificate_id': f'Certificate{uuid4()}',
                'reference_uri': f'Reference-ID-{uuid4()}',
                'signed_properties_id': f'SignedPropertiesID{uuid4()}',
            }

            # Signature rendering: prepare certificate values
            e, n = certificate_sudo._get_public_key_numbers_bytes()
            qweb_values.update({
                'sig_certif_digest': certificate_sudo._get_fingerprint_bytes(hashing_algorithm='sha1', formatting='base64').decode(),
                'x509_certificate': certificate_sudo._get_der_certificate_bytes().decode(),
                'rsa_modulus': n.decode(),
                'rsa_exponent': e.decode(),
                'x509_issuer_description': certificate_sudo._l10n_ec_edi_get_issuer_rfc_string(),
                'x509_serial_number': int(certificate_sudo.serial_number),
            })

            # Parse document, append rendered signature and process references
            doc = cleanup_xml_node(xml_node_or_string)
            signature_str = self.env['ir.qweb']._render('l10n_ec_edi.ec_edi_signature', qweb_values)
            signature = cleanup_xml_signature(signature_str)
            doc.append(signature)
            calculate_references_digests(signature.find('SignedInfo', namespaces=NS_MAP), base_uri='#comprobante')

            # Sign (writes into SignatureValue)
            fill_signature(signature, certificate_sudo)

            xml_node_or_string = etree.tostring(doc, encoding='UTF-8', xml_declaration=True, pretty_print=True)

        # Decode the byte string to a Unicode string
        xml_string = xml_node_or_string.decode('UTF-8')
        return xml_string

    def _l10n_ec_generate_demo_xml_attachment(self, move, xml_string):
        """
        Generates an xml attachment to simulate a response from the SRI without the need for a digital signature.
        """
        move.l10n_ec_authorization_date = datetime.now(tz=timezone('America/Guayaquil')).date()
        attachment = self.env['ir.attachment'].create({
            'name': move.display_name + '_demo.xml',
            'res_id': move.id,
            'res_model': move._name,
            'type': 'binary',
            'raw': self._l10n_ec_create_authorization_file(
                move, xml_string,
                move.l10n_ec_authorization_number, move.l10n_ec_authorization_date),
            'mimetype': 'application/xml',
            'description': f"Ecuadorian electronic document generated for document {move.display_name}."
        })
        move.with_context(no_new_invoice=True).message_post(
            body=escape(
                _(
                    "{}This is a DEMO response, which means this document was not sent to the SRI.{}If you want your document to be processed by the SRI, please set an {}Electronic Certificate File{} in the settings.{}Demo electronic document.{}Authorization num:{}%(authorization_num)s{}Authorization date:{}%(authorization_date)s",
                    authorization_num=move.l10n_ec_authorization_number, authorization_date=move.l10n_ec_authorization_date
                )
            ).format(Markup('<strong>'), Markup('</strong><br/>'), Markup('<strong>'), Markup('</strong>'), Markup('<br/><br/>'), Markup('<br/><strong>'), Markup('</strong><br/>'), Markup('<br/><strong>'), Markup('</strong><br/>')),
            attachment_ids=attachment.ids,
        )
        return [], "", attachment

    def _l10n_ec_send_xml_to_authorize(self, move, xml_string):
        # === DEMO ENVIRONMENT REPONSE ===
        if move.company_id._l10n_ec_is_demo_environment():
            return self._l10n_ec_generate_demo_xml_attachment(move, xml_string)

        # === Try sending and getting authorization status === #
        errors, error_type, auth_date, auth_num = self._l10n_ec_send_document(
            move.company_id,
            move.l10n_ec_authorization_number,
            xml_string,
            already_sent=move.l10n_ec_authorization_date,
        )
        attachment = False
        if auth_num and auth_date:
            move.l10n_ec_authorization_date = auth_date.replace(tzinfo=None)
            attachment = self.env['ir.attachment'].create({
                'name': move.display_name + '.xml',
                'res_id': move.id,
                'res_model': move._name,
                'type': 'binary',
                'raw': self._l10n_ec_create_authorization_file(move, xml_string, auth_num, auth_date),
                'mimetype': 'application/xml',
                'description': f"Ecuadorian electronic document generated for document {move.display_name}."
            })
            move.with_context(no_new_invoice=True).message_post(
                body=escape(
                    _(
                        "Electronic document authorized.{}Authorization num:{}%(authorization_num)s{}Authorization date:{}%(authorization_date)s",
                        authorization_num=move.l10n_ec_authorization_number, authorization_date=move.l10n_ec_authorization_date,
                    )
                ).format(Markup('<br/><strong>'), Markup('</strong><br/>'), Markup('<br/><strong>'), Markup('</strong><br/>')),
                attachment_ids=attachment.ids,
            )

        return errors, error_type, attachment

    def _l10n_ec_send_document(self, company_id, authorization_num, xml_string, already_sent=False):
        # === STEP 1 ===
        errors, warnings = [], []
        if not already_sent:
            # Submit the generated XML
            response, zeep_errors, warnings = self._l10n_ec_get_client_service_response_new(company_id, 'reception', xml=xml_string.encode())
            if zeep_errors:
                return zeep_errors, 'error', None, None
            try:
                response_state = response['estado']
                response_checks = response['comprobantes'] and response['comprobantes']['comprobante'] or []
            except (AttributeError, TypeError) as err:
                return warnings or [_("SRI response unexpected: %s", err)], 'warning' if warnings else 'error', None, None

            # Parse govt's response for errors or response state
            if response_state == 'DEVUELTA':
                for check in response_checks:
                    for msg in check['mensajes']['mensaje']:
                        if msg['identificador'] != '43':  # 43 means Authorization number already registered
                            errors.append(' - '.join(
                                filter(None, [msg['identificador'], msg['informacionAdicional'], msg['mensaje'], msg['tipo']])
                            ))
            elif response_state != 'RECIBIDA':
                errors.append(_("SRI response state: %s", response_state))

            # If any errors have been found (other than those indicating already-authorized document)
            if errors:
                return errors, 'error', None, None

        # === STEP 2 ===
        # Get authorization status, store response & raise any errors
        auth_state, auth_num, auth_date, auth_errors, auth_warnings = self._l10n_ec_get_authorization_status_new(company_id, authorization_num)
        errors.extend(auth_errors)
        warnings.extend(auth_warnings)
        if auth_num and auth_date:
            if authorization_num != auth_num:
                warnings.append(_("Authorization number %(authorization_number)s does not match document's %(document_number)s", authorization_number=auth_num, document_number=authorization_num))
        elif not auth_num and auth_state == 'EN PROCESO':
            # No authorization number means the invoice was no authorized yet
            warnings.append(_("Document with access key %s received by government and pending authorization",
                              authorization_num))
        else:
            # SRI unexpected error
            errors.append(_("Document not authorized by SRI, please try again later"))

        return errors or warnings, 'error' if errors else 'warning', auth_date, auth_num

    def _l10n_ec_get_authorization_status(self, move):
        """
        Government interaction: retrieves status of previously sent document.
        """
        return self._l10n_ec_get_authorization_status_new(move.company_id, move.l10n_ec_authorization_number)

    def _l10n_ec_get_authorization_status_new(self, company_id, l10n_ec_authorization_number):
        # TODO master: merge this with `_l10n_ec_get_authorization_status`
        auth_state, auth_num, auth_date = None, None, None

        response, zeep_errors, zeep_warnings = self._l10n_ec_get_client_service_response_new(
            company_id, "authorization",
            claveAccesoComprobante=l10n_ec_authorization_number
        )
        if zeep_errors:
            return auth_state, auth_num, auth_date, zeep_errors, zeep_warnings
        try:
            response_auth_list = response['autorizaciones'] and response['autorizaciones']['autorizacion'] or []
        except (AttributeError, TypeError) as err:
            return auth_state, auth_num, auth_date, [_("SRI response unexpected: %s", err)], zeep_warnings

        errors = []
        if not isinstance(response_auth_list, list):
            response_auth_list = [response_auth_list]

        for doc in response_auth_list:
            auth_state = doc['estado']
            if doc['estado'] == "AUTORIZADO":
                auth_num = doc['numeroAutorizacion']
                auth_date = doc['fechaAutorizacion']
            else:
                messages = doc['mensajes']
                if messages:
                    messages_list = messages['mensaje']
                    if not isinstance(messages_list, list):
                        messages_list = messages
                    for msg in messages_list:
                        errors.append(' - '.join(
                            filter(None, [msg['identificador'], msg['informacionAdicional'], msg['mensaje'], msg['tipo']])
                        ))
        return auth_state, auth_num, auth_date, errors, zeep_warnings

    def _l10n_ec_get_client_service_response(self, move, mode, **kwargs):
        """
        Government interaction: SOAP Transport and Client management.
        """
        return self._l10n_ec_get_client_service_response_new(move.company_id, mode, **kwargs)

    def _l10n_ec_get_client_service_response_new(self, company_id, mode, **kwargs):
        # TODO: in master, merge this with `_l10n_ec_get_client_service_response`
        if company_id.l10n_ec_production_env:
            wsdl_url = PRODUCTION_URL.get(mode)
        else:
            wsdl_url = TEST_URL.get(mode)

        errors, warnings = [], []
        response = None
        try:
            client = Client(wsdl=wsdl_url, timeout=DEFAULT_TIMEOUT_WS)
            if mode == "reception":
                response = client.service.validarComprobante(**kwargs)
            elif mode == "authorization":
                response = client.service.autorizacionComprobante(**kwargs)
            if not response:
                errors.append(_("No response received."))
        except ZeepError as e:
            errors.append(_("The SRI service failed with the following error: %s", e))
        except RequestException as e:
            warnings.append(_("The SRI service failed with the following message: %s", e))
        return response, errors, warnings

    # ===== Helper methods =====

    def _l10n_ec_create_authorization_file(self, move, xml_string, authorization_number, authorization_date):
        return self._l10n_ec_create_authorization_file_new(move.company_id, xml_string, authorization_number, authorization_date)

    def _l10n_ec_create_authorization_file_new(self, company_id, xml_string, authorization_number, authorization_date):
        # TODO master: merge with `_l10n_ec_create_authorization_file`
        xml_values = {
            'xml_file_content': Markup(xml_string[xml_string.find('?>') + 2:]),  # remove header to embed sent xml
            'mode': 'PRODUCCION' if company_id.l10n_ec_production_env else 'PRUEBAS',
            'authorization_number': authorization_number,
            'authorization_date': authorization_date.strftime(DTF),
        }
        xml_response = self.env['ir.qweb']._render('l10n_ec_edi.authorization_template', xml_values)
        xml_response = cleanup_xml_node(xml_response)
        return etree.tostring(xml_response, encoding='unicode')

    def _l10n_ec_format_number(self, value, decimals=2):
        return float_repr(float_round(value, decimals), decimals)

    def _l10n_ec_remove_newlines(self, s, max_len=300):
        return s.replace('\n', '')[:max_len]
