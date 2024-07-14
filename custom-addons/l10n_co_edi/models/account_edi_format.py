# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, api, models, _
from odoo.tools.float_utils import float_compare
from odoo.tools import DEFAULT_SERVER_TIME_FORMAT, float_repr, float_round
from odoo.tools import html2plaintext
from .carvajal_request import CarvajalRequest

import pytz
import base64
import re

from collections import defaultdict
from datetime import timedelta
from markupsafe import Markup


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_co_edi_generate_electronic_invoice_filename(self, invoice):
        '''Generates the filename for the XML sent to Carvajal. A separate
        sequence is used because Carvajal requires the invoice number
        to only contain digits.
        '''
        seq_code = 'l10n_co_edi.filename'
        IrSequence = self.env['ir.sequence'].with_company(invoice.company_id)
        invoice_number = IrSequence.next_by_code(seq_code)

        # if a sequence does not yet exist for this company create one
        if not invoice_number:
            IrSequence.sudo().create({
                'name': 'Colombian electronic invoicing sequence for company %s' % invoice.company_id.id,
                'code': seq_code,
                'implementation': 'no_gap',
                'padding': 10,
                'number_increment': 1,
                'company_id': invoice.company_id.id,
            })
            invoice_number = IrSequence.next_by_code(seq_code)

        return 'face_{}{:0>10}{:010x}.xml'.format(invoice._l10n_co_edi_get_electronic_invoice_type(),
                                                  invoice.company_id.vat,
                                                  int(invoice_number))

    def _l10n_co_edi_get_round_amount(self, amount):
        if amount == '':
            return ''
        if abs(amount - float("%.2f" % amount)) > 0.00001:
            return "%.3f" % amount
        return '%.2f' % amount

    def _l10n_co_edi_prepare_tim_sections(self, taxes_dict, invoice_currency, retention, tax_details=None, actual_tax_details=None, in_COP=False):
        # taxes_dict is no longer used and will be removed in master
        tax_details = tax_details or {}
        actual_tax_details = actual_tax_details or {}

        suffix = '' if in_COP else '_currency'
        currency_name = 'COP' if in_COP else invoice_currency.name
        base_amount_field = f'base_amount{suffix}'
        tax_amount_field = f'tax_amount{suffix}'

        # Mapping CO tax type -> TIM section
        new_taxes_dict = defaultdict(lambda: {
            'TIM_1': bool(retention),
            'TIM_2': 0.0,
            'TIM_3': currency_name,
            'TIM_4': 0.0,
            'TIM_5': currency_name,
            'IMPS': [],
        })

        for grouping_key, tax_detail in actual_tax_details['tax_details'].items():
            tax_type = grouping_key['l10n_co_edi_type']
            if tax_type.retention != retention:
                continue
            # Construct the IMP and add it to the TIM section (one IMP per tax *rate*)
            tim = new_taxes_dict[tax_type.code]
            if tax_type.code == '05':
                imp_2 = abs(tax_detail[tax_amount_field] * 100 / 15)
            elif tax_type.code == '34':
                imp_2 = sum(line.product_id.volume * line.quantity
                            for line in tax_detail['records'])  # Volume
            else:
                imp_2 = abs(tax_detail[base_amount_field])
            imp = {
                'IMP_1': tax_type.code,
                'IMP_2': imp_2,
                'IMP_3': currency_name,
                'IMP_4': abs(tax_detail[tax_amount_field]),
                'IMP_5': currency_name,
                'IMP_11': tax_type.name,
            }
            if grouping_key['amount_type'] == 'fixed':
                imp.update({
                    'IMP_6': 0,
                    'IMP_7': 1,
                    'IMP_8': '94',
                    'IMP_9': grouping_key['amount'],  # Tax rate
                    'IMP_10': currency_name,
                })
                if tax_type.code == '22':
                    imp['IMP_8'] = 'BO'
                elif tax_type.code == '34':
                    imp.update({
                        'IMP_7': imp['IMP_2'],
                        'IMP_8': 'MLT',
                        'IMP_9': imp['IMP_2'] and float_round(abs(tax_detail[tax_amount_field]) * 100 / imp['IMP_2'], 2),
                    })
            else:
                imp.update({
                    'IMP_6': 15.0 if tax_type.code == '05' else abs(grouping_key['amount']),
                    'IMP_7': '',
                    'IMP_8': '',
                    'IMP_9': '',
                    'IMP_10': '',
                })
                tim['TIM_4'] += float_round((imp['IMP_6'] / 100.0 * imp['IMP_2']) - imp['IMP_4'], 2)
            tim['TIM_2'] += imp['IMP_4']
            tim['IMPS'].append(imp)
        return new_taxes_dict

    # -------------------------------------------------------------------------
    # Generation
    # -------------------------------------------------------------------------

    def _l10n_co_edi_generate_xml(self, invoice):
        '''Renders the XML that will be sent to Carvajal.'''

        def format_domestic_phone_number(phone):
            '''The CDE_3 field only allows for 10 characters (since Anexo 1.9).
            Probably since Colombian telephone numbers are 10 digit numbers when excluding the country prefix (January 2024).
            '''
            phone = (phone or '').replace(' ', '')
            if len(phone) <= 10:
                return phone
            phone = re.sub(r'^(\+57|0057)', '', phone)
            return phone[:10]

        def format_monetary(number, currency):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            return float_repr(number, currency.decimal_places)

        def get_notas():
            '''This generates notes in a particular format. These notes are pieces
            of text that are added to the PDF in various places. |'s are
            interpreted as newlines by Carvajal. Each note is added to the
            XML as follows:

            <NOT><NOT_1>text</NOT_1></NOT>

            One might wonder why Carvajal uses this arbitrary format
            instead of some extra simple XML tags but such questions are best
            left to philosophers, not dumb developers like myself.
            '''
            # Volume has to be reported in l (not e.g. ml).
            if invoice.move_type in ('in_invoice', 'in_refund'):
                company_partner = invoice.company_id.partner_id
                invoice_partner = invoice.partner_id.commercial_partner_id
                return [
                    '23.-%s' % ("|".join([
                                        company_partner.street or '',
                                        company_partner.city or '',
                                        company_partner.country_id.name or '',
                                        company_partner.phone or '',
                                        company_partner.email or '',
                                    ])),
                    '24.-%s' % ("|".join([invoice_partner.phone or '',
                                        invoice_partner.ref or '',
                                        invoice_partner.email or '',
                                    ])),
                ]
            lines = invoice.invoice_line_ids.filtered(lambda line: line.product_uom_id.category_id == self.env.ref('uom.product_uom_categ_vol'))
            liters = sum(line.product_uom_id._compute_quantity(line.quantity, self.env.ref('uom.product_uom_litre')) for line in lines)
            total_volume = int(liters)

            # Weight has to be reported in kg (not e.g. g).
            lines = invoice.invoice_line_ids.filtered(lambda line: line.product_uom_id.category_id == self.env.ref('uom.product_uom_categ_kgm'))
            kg = sum(line.product_uom_id._compute_quantity(line.quantity, self.env.ref('uom.product_uom_kgm')) for line in lines)
            total_weight = int(kg)

            # Units have to be reported as units (not e.g. boxes of 12).
            lines = invoice.invoice_line_ids.filtered(lambda line: line.product_uom_id.category_id == self.env.ref('uom.product_uom_categ_unit'))
            units = sum(line.product_uom_id._compute_quantity(line.quantity, self.env.ref('uom.product_uom_unit')) for line in lines)
            total_units = int(units)

            withholding_amount = invoice.amount_untaxed + abs(sum(invoice.line_ids.filtered(lambda line: line.tax_line_id and not line.tax_line_id.l10n_co_edi_type.retention).mapped('amount_currency')))
            amount_in_words = invoice.currency_id.with_context(lang=invoice.partner_id.lang or 'es_ES').amount_to_text(withholding_amount)

            reg_a_tag = re.compile('<a.*?>')
            clean_narration = re.sub(reg_a_tag, '', invoice.narration) if invoice.narration else False
            narration = (html2plaintext(clean_narration or '') and html2plaintext(clean_narration) + ' ') + (invoice.invoice_origin or '')
            notas = [
                '1.-%s|%s|%s|%s|%s|%s' % (invoice.company_id.l10n_co_edi_header_gran_contribuyente or '',
                                          invoice.company_id.l10n_co_edi_header_tipo_de_regimen or '',
                                          invoice.company_id.l10n_co_edi_header_retenedores_de_iva or '',
                                          invoice.company_id.l10n_co_edi_header_autorretenedores or '',
                                          invoice.company_id.l10n_co_edi_header_resolucion_aplicable or '',
                                          invoice.company_id.l10n_co_edi_header_actividad_economica or ''),
                '2.-%s' % (invoice.company_id.l10n_co_edi_header_bank_information or '').replace('\n', '|'),
                ('3.- %s' % (narration or 'N/A'))[:5000],
                '6.- %s|%s' % (html2plaintext(invoice.invoice_payment_term_id.note), amount_in_words),
                '7.- %s' % (invoice.company_id.website),
                '8.-%s|%s|%s' % (invoice.partner_id.commercial_partner_id._get_vat_without_verification_code() or '', invoice.partner_shipping_id.phone or '', invoice.invoice_origin and invoice.invoice_origin.split(',')[0] or ''),
                '10.- | | | |%s' % (invoice.invoice_origin and invoice.invoice_origin.split(',')[0] or 'N/A'),
                '11.- |%s| |%s|%s' % (total_units, total_weight, total_volume)
            ]

            return notas

        invoice = invoice.with_context(lang=invoice.partner_id.lang)
        code_to_filter = ['07', 'ZZ'] if invoice.move_type in ('in_invoice', 'in_refund') else ['ZZ']
        move_lines_with_tax_type = invoice.line_ids.filtered(lambda l: l.tax_line_id.l10n_co_edi_type.code not in [False] + code_to_filter)

        ovt_tax_codes = ('01C', '02C', '03C')
        ovt_taxes = move_lines_with_tax_type.filtered(lambda move: move.tax_line_id.l10n_co_edi_type.code in ovt_tax_codes).tax_line_id

        invoice_type_to_ref_1 = {
            'out_invoice': 'IV',
            'out_refund': 'NC',
        }

        def group_tax_retention(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id
            return {'tax': tax, 'l10n_co_edi_type': tax.l10n_co_edi_type}

        def group_tax_tim(base_line, tax_values):
            """ Tax details to be used for the TIM section: taxes should be grouped per CO tax type, then per tax rate.
            """
            tax = tax_values['tax_repartition_line'].tax_id
            return {
                'amount': tax.amount,
                'amount_type': tax.amount_type,
                'l10n_co_edi_type': tax.l10n_co_edi_type,
            }

        def l10n_co_filter_to_apply(base_line, tax_values):
            return tax_values['tax_repartition_line'].tax_id.l10n_co_edi_type.code not in code_to_filter

        tax_details_tim = invoice._prepare_edi_tax_details(filter_to_apply=l10n_co_filter_to_apply, grouping_key_generator=group_tax_tim)
        tax_details = invoice._prepare_edi_tax_details(filter_to_apply=l10n_co_filter_to_apply, grouping_key_generator=group_tax_retention)
        retention_taxes = [(group, detail) for group, detail in tax_details['tax_details'].items() if detail['l10n_co_edi_type'].retention]
        regular_taxes = [(group, detail) for group, detail in tax_details['tax_details'].items() if not detail['l10n_co_edi_type'].retention]

        exempt_tax_dict = {}
        tax_group_covered_goods = self.env.ref('l10n_co.tax_group_covered_goods', raise_if_not_found=False)
        for line in invoice.invoice_line_ids:
            if tax_group_covered_goods and tax_group_covered_goods in line.mapped('tax_ids.tax_group_id'):
                exempt_tax_dict[line.id] = True

        # Remove in master: retention_lines_listdict, regular_lines_listdict no longer used
        retention_lines = move_lines_with_tax_type.filtered(
            lambda move: move.tax_line_id.l10n_co_edi_type.retention)
        retention_lines_listdict = defaultdict(list)
        for line in retention_lines:
            retention_lines_listdict[line.tax_line_id.l10n_co_edi_type.code].append(line)

        regular_lines = move_lines_with_tax_type - retention_lines
        regular_lines_listdict = defaultdict(list)
        for line in regular_lines:
            regular_lines_listdict[line.tax_line_id.l10n_co_edi_type.code].append(line)

        zero_tax_details = defaultdict(float)
        for line, tax_detail in tax_details['tax_details_per_record'].items():
            for tax, detail in tax_detail.get('tax_details').items():
                if not detail.get('tax_amount'):
                    tax = tax.get('tax')
                    for grouped_tax in detail.get('group_tax_details'):
                        zero_tax_details[tax.l10n_co_edi_type.code] += abs(grouped_tax.get('base_amount'))
        retention_taxes_new = self._l10n_co_edi_prepare_tim_sections(retention_lines_listdict, invoice.currency_id, True, None, tax_details_tim)
        regular_taxes_new = self._l10n_co_edi_prepare_tim_sections(regular_lines_listdict, invoice.currency_id, False, zero_tax_details, tax_details_tim)

        retention_taxes_new_COP = self._l10n_co_edi_prepare_tim_sections(retention_lines_listdict, invoice.currency_id, True, None, tax_details_tim, in_COP=True)
        regular_taxes_new_COP = self._l10n_co_edi_prepare_tim_sections(retention_lines_listdict, invoice.currency_id, False, zero_tax_details, tax_details_tim, in_COP=True)

        # The rate should indicate how many pesos is one foreign currency
        currency_rate_number = tax_details['base_amount'] / tax_details['base_amount_currency'] if tax_details['base_amount_currency'] else 1
        currency_rate = "%.2f" % currency_rate_number

        sign = 1 if invoice.is_outbound() else -1

        regular_tax_lines = invoice.line_ids.filtered(lambda line: line.tax_line_id and not line.tax_line_id.l10n_co_edi_type.retention)
        withholding_amount = '%.2f' % (invoice.amount_untaxed + abs(sum(regular_tax_lines.mapped('amount_currency'))))
        withholding_amount_company = '%.2f' % (-sign * invoice.amount_untaxed_signed + sum([sign * line.balance for line in regular_tax_lines]))

        # edi_type
        if invoice.move_type == 'out_refund':
            edi_type = "91"
        elif invoice.move_type == 'out_invoice' and invoice.l10n_co_edi_debit_note:
            edi_type = "92"
        else:
            edi_type = "{0:0=2d}".format(int(invoice.l10n_co_edi_type))

        # validation_time
        validation_time = fields.Datetime.now()
        validation_time = pytz.utc.localize(validation_time)
        bogota_tz = pytz.timezone('America/Bogota')
        validation_time = validation_time.astimezone(bogota_tz)
        validation_time = validation_time.strftime(DEFAULT_SERVER_TIME_FORMAT) + "-05:00"

        # description
        description_field = None
        if invoice.move_type in ('out_refund', 'in_refund'):
            description_field = 'l10n_co_edi_description_code_credit'
        if invoice.move_type in ('out_invoice', 'in_invoice') and invoice.l10n_co_edi_debit_note:
            description_field = 'l10n_co_edi_description_code_debit'
        description_code = invoice[description_field] if description_field else None
        description = dict(invoice._fields[description_field].selection).get(description_code) if description_code else None

        invoice_lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
        invoice_lines_values = {}
        for line in invoice_lines:
            price_subtotal = sign * line.balance
            if line.discount == 100:
                price_subtotal_before_discount = line.price_unit * line.quantity * currency_rate_number
            else:
                price_subtotal_before_discount = price_subtotal / (1 - line.discount / 100)
            if line.quantity:
                price_unit = price_subtotal_before_discount / line.quantity
            else:
                price_unit = line.price_unit * currency_rate_number
            invoice_lines_values[line.id] = {
                'price_unit': price_unit,
                'price_subtotal': price_subtotal,
                'discount_amount': price_subtotal_before_discount - price_subtotal,
                'price_subtotal_before_discount': price_subtotal_before_discount,
            }

        xml_content = self.env['ir.qweb']._render(self._l10n_co_edi_get_electronic_invoice_template(invoice), {
            'invoice': invoice,
            'sign': sign,
            'edi_type': edi_type,
            'company_partner': invoice.company_id.partner_id,
            'sales_partner': invoice.user_id,
            'invoice_partner': invoice.partner_id.commercial_partner_id,
            'retention_taxes': retention_taxes,
            'retention_taxes_new': retention_taxes_new,
            'retention_taxes_new_COP': retention_taxes_new_COP,
            'regular_taxes': regular_taxes,
            'regular_taxes_new': regular_taxes_new,
            'regular_taxes_new_COP': regular_taxes_new_COP,
            'tax_details': tax_details,
            'tax_types': invoice.mapped('line_ids.tax_ids.l10n_co_edi_type'),
            'exempt_tax_dict': exempt_tax_dict,
            'currency_rate': currency_rate,
            'shipping_partner': invoice.partner_shipping_id,
            'invoice_type_to_ref_1': invoice_type_to_ref_1,
            'ovt_taxes': ovt_taxes,
            'float_compare': float_compare,
            'notas': get_notas(),
            'withholding_amount': withholding_amount,
            'withholding_amount_company': withholding_amount_company,
            'invoice_lines': invoice_lines,
            'invoice_lines_values': invoice_lines_values,
            'validation_time': validation_time,
            'delivery_date': invoice.invoice_date + timedelta(1),
            'description_code': description_code,
            'description': description,
            'format_monetary': format_monetary,
            'format_domestic_phone_number': format_domestic_phone_number,
            '_l10n_co_edi_get_round_amount': self._l10n_co_edi_get_round_amount
        })
        return b'<?xml version="1.0" encoding="utf-8"?>' + xml_content.encode()

    def _l10n_co_edi_get_electronic_invoice_template(self, invoice):
        if invoice.move_type in ('in_invoice', 'in_refund'):
            return 'l10n_co_edi.electronic_invoice_vendor_document_xml'
        return 'l10n_co_edi.electronic_invoice_xml'

    def _l10n_co_post_invoice_step_1(self, invoice):
        '''Sends the xml to carvajal.
        '''
        # == Generate XML ==
        xml_filename = self._l10n_co_edi_generate_electronic_invoice_filename(invoice)
        xml = self._l10n_co_edi_generate_xml(invoice)
        attachment = self.env['ir.attachment'].create({
            'name': xml_filename,
            'res_id': invoice.id,
            'res_model': invoice._name,
            'type': 'binary',
            'raw': xml,
            'mimetype': 'application/xml',
            'description': _('Colombian invoice UBL generated for the %s document.', invoice.name),
        })

        # == Upload ==
        request = CarvajalRequest(invoice.move_type, invoice.company_id)
        response = request.upload(xml_filename, xml)

        if 'error' not in response:
            invoice.l10n_co_edi_transaction = response['transactionId']

            # == Chatter ==
            invoice.with_context(no_new_invoice=True).message_post(
                body=_('Electronic invoice submission succeeded. Message from Carvajal:') + Markup('<br/>)' + response['message']),
                attachment_ids=attachment.ids,
            )
            # Do not return the attachment because it is not signed yet.
        else:
            # Return the attachment with the error to allow debugging.
            response['attachment'] = attachment

        return response

    def _l10n_co_post_invoice_step_2(self, invoice):
        '''Checks the current status of an uploaded XML with Carvajal. It
        posts the results in the invoice chatter and also attempts to
        download a ZIP containing the official XML and PDF if the
        invoice is reported as fully validated.
        '''
        request = CarvajalRequest(invoice.move_type, invoice.company_id)
        response = request.check_status(invoice)
        if not response.get('error'):
            response['success'] = True
            invoice.l10n_co_edi_cufe_cude_ref = response['l10n_co_edi_cufe_cude_ref']

            # == Create the attachment ==
            if 'filename' in response and 'xml_file' in response:
                response['attachment'] = self.env['ir.attachment'].create({
                    'name': response['filename'],
                    'res_id': invoice.id,
                    'res_model': invoice._name,
                    'type': 'binary',
                    'datas': base64.b64encode(response['xml_file']),
                    'mimetype': 'application/xml',
                    'description': _('Colombian invoice UBL generated for the %s document.', invoice.name),
                })

            # == Chatter ==
            invoice.with_context(no_new_invoice=True).message_post(body=response['message'], attachments=response['attachments'])
        elif response.get('blocking_level') == 'error':
            invoice.l10n_co_edi_transaction = False

        return response

    # -------------------------------------------------------------------------
    # BUSINESS FLOW: EDI
    # -------------------------------------------------------------------------

    def _needs_web_services(self):
        # OVERRIDE
        return self.code == 'ubl_carvajal' or super()._needs_web_services()

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'ubl_carvajal':
            return super()._is_compatible_with_journal(journal)
        return journal.type in ['sale', 'purchase'] and journal.country_code == 'CO'

    def _get_move_applicability(self, move):
        # EXTENDS account_edi
        self.ensure_one()
        if self.code != 'ubl_carvajal':
            return super()._get_move_applicability(move)

        # Determine on which invoices the EDI must be generated.
        co_edi_needed = move.country_code == 'CO' and (
            move.move_type in ('in_invoice', 'in_refund')
            and bool(self.env.ref('l10n_co_edi.electronic_invoice_vendor_document_xml', raise_if_not_found=False))
        ) or (
            move.move_type in ('out_invoice', 'out_refund')
        )
        if co_edi_needed:
            if move.l10n_co_edi_transaction:
                return {
                    'post': self._l10n_co_edi_post_invoice_step_2,
                }
            else:
                return {
                    'post': self._l10n_co_edi_post_invoice_step_1,
                }

    def _check_move_configuration(self, move):
        # OVERRIDE
        self.ensure_one()
        edi_result = super()._check_move_configuration(move)
        if self.code != 'ubl_carvajal':
            return edi_result

        company = move.company_id
        journal = move.journal_id
        now = fields.Datetime.now()
        oldest_date = now - timedelta(days=5)
        newest_date = now + timedelta(days=10)
        if not company.sudo().l10n_co_edi_username or not company.sudo().l10n_co_edi_password or not company.l10n_co_edi_company or \
           not company.sudo().l10n_co_edi_account:
            edi_result.append(_("Carvajal credentials are not set on the company, please go to Accounting Settings and set the credentials."))
        if (move.move_type != 'out_refund' and not move.debit_origin_id) and \
           (not journal.l10n_co_edi_dian_authorization_number or not journal.l10n_co_edi_dian_authorization_date or not journal.l10n_co_edi_dian_authorization_end_date):
            edi_result.append(_("'Resolución DIAN' fields must be set on the journal %s", journal.display_name))
        if not move.partner_id.vat:
            edi_result.append(_("You can not validate an invoice that has a partner without VAT number."))
        if not move.company_id.partner_id.l10n_co_edi_obligation_type_ids:
            edi_result.append(_("'Obligaciones y Responsabilidades' on the Customer Fiscal Data section needs to be set for the partner %s.", move.company_id.partner_id.display_name))
        if not move.amount_total:
            edi_result.append(_("You cannot send Documents in Carvajal without an amount."))
        if not move.partner_id.commercial_partner_id.l10n_co_edi_obligation_type_ids:
            edi_result.append(_("'Obligaciones y Responsabilidades' on the Customer Fiscal Data section needs to be set for the partner %s.", move.partner_id.commercial_partner_id.display_name))
        if (move.l10n_co_edi_type == '2' and \
                any(l.product_id and not l.product_id.l10n_co_edi_customs_code for l in move.invoice_line_ids)):
            edi_result.append(_("Every exportation product must have a customs code."))
        elif move.invoice_date and not (oldest_date <= fields.Datetime.to_datetime(move.invoice_date) <= newest_date):
            move.message_post(body=_('The issue date can not be older than 5 days or more than 5 days in the future'))
        elif any(l.product_id and not l.product_id.default_code and \
                 not l.product_id.barcode and not l.product_id.unspsc_code_id for l in move.invoice_line_ids):
            edi_result.append(_("Every product on a line should at least have a product code (barcode, internal, UNSPSC) set."))

        if not move.company_id.partner_id.l10n_latam_identification_type_id.l10n_co_document_code:
            edi_result.append(_("The Identification Number Type on the company\'s partner should be 'NIT'."))
        if not move.partner_id.commercial_partner_id.l10n_latam_identification_type_id.l10n_co_document_code:
            edi_result.append(_("The Identification Number Type on the customer\'s partner should be 'NIT'."))
        if move.l10n_co_edi_operation_type == '20' and not move.l10n_co_edi_description_code_credit:
            edi_result.append(_("Credit Notes that reference an invoice require to have a Credit Note Concept, please fill in this value"))

        if not move.company_id.partner_id.email:
            edi_result.append(_("Your company's contact should have a reception email set."))

        # Sugar taxes
        for line in move.invoice_line_ids:
            if "IBUA" in line.tax_ids.l10n_co_edi_type.mapped('name') and line.product_id.volume == 0:
                edi_result.append(_("You should set a volume on product: %s when using IBUA taxes.", line.product_id.name))

        return edi_result

    def _l10n_co_edi_post_invoice_step_1(self, invoice):
        return {invoice: self._l10n_co_post_invoice_step_1(invoice)}

    def _l10n_co_edi_post_invoice_step_2(self, invoice):
        return {invoice: self._l10n_co_post_invoice_step_2(invoice)}

    # to remove in master
    def _l10n_co_edi_cancel_invoice(self, invoice):
        return {invoice: {'success': True}}
