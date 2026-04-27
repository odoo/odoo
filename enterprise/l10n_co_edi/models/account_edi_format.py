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
from .account_invoice import L10N_CO_EDI_TYPE


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

    @api.model
    def _l10n_co_edi_prepare_tii_sections(self, base_line, aggregated_values):
        is_vendor_bill = base_line['record'].move_id.is_purchase_document()
        currency_name = 'COP' if not is_vendor_bill else base_line['currency_id'].name
        base_amount_field = 'base_amount' if not is_vendor_bill else 'base_amount_currency'
        tax_amount_field = 'tax_amount' if not is_vendor_bill else 'tax_amount_currency'

        tii_sections = []
        for grouping_key, values in aggregated_values.items():
            if not grouping_key or grouping_key['skip']:
                continue

            type_name = grouping_key['l10n_co_edi_type'].name
            type_code = grouping_key['l10n_co_edi_type'].code
            amount = grouping_key['amount']
            amount_type = grouping_key['amount_type']

            iim2 = values[tax_amount_field]
            if type_code == '05':
                if amount == -2.85:
                    iim4 = abs(values[base_amount_field] * 0.19)
                else:
                    iim4 = abs(values[base_amount_field] * 0.05)
            elif type_code == '34':
                iim4 = base_line['product_id'].l10n_co_edi_ref_nominal_tax * base_line['quantity']
            else:
                iim4 = abs(values[base_amount_field])

            if type_code != '34' or not iim2:
                iim9 = amount
            else:
                iim9 = (iim2 * 100 / iim4) if iim4 else 0.0

            iim6 = 15.0 if type_code == '05' else abs(amount)
            if is_vendor_bill and amount_type != 'fixed':
                tii4 = (iim6 * iim4 / 100) - iim2
            else:
                tii4 = None

            values = {
                'TII_1': abs(iim2),
                'TII_2': currency_name,
                'TII_3': 'true' if grouping_key['l10n_co_edi_type'].retention else 'false',
                'TII_4': tii4,
                'TII_5': currency_name if is_vendor_bill else None,

                'IIM_1': type_code,
                'IIM_2': abs(iim2),
                'IIM_3': currency_name,
                'IIM_4': iim4,
                'IIM_5': currency_name,
                'IIM_6': iim6,
                'IIM_7': '',
                'IIM_8': '',
                'IIM_9': '',
                'IIM_10': '',
                'IIM_11': type_name,
            }
            if amount_type == 'fixed':
                if type_code == '22':
                    iim8 = 'BO'
                elif type_code == '34':
                    iim8 = 'MLT'
                else:
                    iim8 = '94'

                values.update({
                    'IIM_6': None,
                    'IIM_7': iim4 if type_code == '34' else '1',
                    'IIM_8': iim8,
                    'IIM_9': iim9,
                    'IIM_10': currency_name,
                })
            tii_sections.append(values)
        return tii_sections

    @api.model
    def _l10n_co_edi_prepare_tim_sections(self, invoice, values_per_grouping_key, is_retention, in_cop):
        is_vendor_bill = invoice.is_purchase_document()
        currency_name = 'COP' if in_cop else invoice.currency_id.name
        base_amount_field = 'base_amount' if in_cop else 'base_amount_currency'
        tax_amount_field = 'tax_amount' if in_cop else 'tax_amount_currency'

        tim_per_code = defaultdict(lambda: {
            'TIM_1': 'true' if is_retention else 'false',
            'TIM_2': 0.0,
            'TIM_3': currency_name,
            'TIM_4': 0.0 if is_vendor_bill else None,
            'TIM_5': currency_name if is_vendor_bill else None,
            'IMPS': [],
        })

        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key or grouping_key['skip'] or grouping_key['is_retention'] != is_retention:
                continue

            type_name = grouping_key['l10n_co_edi_type'].name
            type_code = grouping_key['l10n_co_edi_type'].code
            amount = grouping_key['amount']
            tim = tim_per_code[type_code]
            tim['type_code'] = type_code

            if type_code == '05':
                imp2 = abs(values[tax_amount_field] * 100 / 15)
            elif type_code == '34':
                base_line_x_taxes_data = values['base_line_x_taxes_data']
                imp2 = sum(
                    base_line['product_id'].l10n_co_edi_ref_nominal_tax * base_line['quantity']
                    for base_line, _taxes_data in base_line_x_taxes_data
                )
            else:
                imp2 = abs(values[base_amount_field])

            imp = {
                'IMP_1': type_code,
                'IMP_2': imp2,
                'IMP_3': currency_name,
                'IMP_4': abs(values[tax_amount_field]),
                'IMP_5': currency_name,
                'IMP_11': type_name,
            }
            if grouping_key['amount_type'] == 'fixed':
                imp.update({
                    'IMP_6': 0,
                    'IMP_6_dp': 2,
                    'IMP_7': 1,
                    'IMP_8': '94',
                    'IMP_9': grouping_key['amount'],  # Tax rate
                    'IMP_10': currency_name,
                })
                if type_code == '22':
                    imp['IMP_8'] = 'BO'
                elif type_code == '34':
                    imp.update({
                        'IMP_7': imp['IMP_2'],
                        'IMP_8': 'MLT',
                        'IMP_9': float_round(abs(values[tax_amount_field]) * 100 / imp['IMP_2'], 2) if imp['IMP_2'] else None,
                    })
            else:
                imp6_dp = 2
                if type_code == '05':
                    imp6 = 15.0
                else:
                    imp6 = abs(amount)
                    if abs(imp6 - float("%.2f" % imp6)) > 0.00001:
                        imp6_dp = 3
                imp.update({
                    'IMP_6': imp6,
                    'IMP_6_dp': imp6_dp,
                    'IMP_7': '',
                    'IMP_8': '',
                    'IMP_9': '',
                    'IMP_10': '',
                })
                if tim['TIM_4'] is not None:
                    tim['TIM_4'] += float_round((imp['IMP_6'] / 100.0 * imp['IMP_2']) - imp['IMP_4'], 2)
            tim['TIM_2'] += imp['IMP_4']
            tim['IMPS'].append(imp)
        return list(tim_per_code.values())

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

        def format_float(number, dp):
            return float_repr(number, dp) if number not in (None, '') else number

        def format_monetary(number, currency):
            return format_float(number, currency.decimal_places)

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

        AccountTax = self.env['account.tax']
        base_amls = invoice.line_ids.filtered(lambda x: x.display_type == 'product')
        base_lines = [invoice._prepare_product_base_line_for_taxes_computation(x) for x in base_amls]
        tax_amls = invoice.line_ids.filtered('tax_repartition_line_id')
        tax_lines = [invoice._prepare_tax_line_for_taxes_computation(x) for x in tax_amls]
        AccountTax._add_tax_details_in_base_lines(base_lines, invoice.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, invoice.company_id, tax_lines=tax_lines)

        tax_group_covered_goods = self.env.ref('l10n_co.tax_group_covered_goods', raise_if_not_found=False)
        for index, base_line in enumerate(base_lines, start=1):
            price_unit = base_line['price_unit']
            quantity = base_line['quantity']
            discount = base_line['discount']
            rate = base_line['rate']
            tax_details = base_line['tax_details']
            base_line['co_edi_index'] = index
            base_line['co_price_subtotal'] = tax_details['total_excluded'] + tax_details['delta_total_excluded']

            if discount == 100:
                co_price_subtotal_before_discount = (price_unit * quantity) / rate if rate else 0.0
            else:
                co_price_subtotal_before_discount = base_line['co_price_subtotal'] / (1 - discount / 100)
            base_line['co_price_subtotal_before_discount'] = co_price_subtotal_before_discount
            base_line['co_discount_amount'] = co_price_subtotal_before_discount - base_line['co_price_subtotal']

            if quantity:
                co_price_unit = co_price_subtotal_before_discount / quantity
            else:
                co_price_unit = price_unit / rate if rate else 0.0
            base_line['co_price_unit'] = co_price_unit

            base_line['co_is_exempt_tax'] = tax_group_covered_goods and tax_group_covered_goods in base_line['tax_ids'].tax_group_id

        def grouping_function_tim_sections(base_line, tax_data):
            if not tax_data:
                return None
            tax = tax_data['tax']
            return {
                'amount': tax.amount,
                'amount_type': tax.amount_type,
                'l10n_co_edi_type': tax.l10n_co_edi_type,
                'skip': tax_data['tax'].l10n_co_edi_type.code in code_to_filter,
                'is_retention': tax.l10n_co_edi_type.retention,
            }

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function_tim_sections)
        for base_line, aggregated_values in base_lines_aggregated_values:
            base_line['co_tii_sections'] = self._l10n_co_edi_prepare_tii_sections(base_line, aggregated_values)

        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(base_lines_aggregated_values)
        is_vendor_bill = invoice.is_purchase_document()
        tim_sections_retention = self._l10n_co_edi_prepare_tim_sections(
            invoice, values_per_grouping_key, True, not is_vendor_bill)
        tim_sections_regular = self._l10n_co_edi_prepare_tim_sections(
            invoice, values_per_grouping_key, False, not is_vendor_bill)
        vmt_section = {
            'vmt7': 0.0,
            'vmt8': 0.0,
            'vmt16': 0.0,
            'vmt17': 0.0,
            'vmt18': 0.0,
        }
        if is_vendor_bill or invoice.currency_id == invoice.company_currency_id:
            vmt_tim_sections = tim_sections_retention + tim_sections_regular
        else:
            tim_sections_retention_foreign = self._l10n_co_edi_prepare_tim_sections(
                invoice, values_per_grouping_key, True, False)
            tim_sections_regular_foreign = self._l10n_co_edi_prepare_tim_sections(
                invoice, values_per_grouping_key, False, False)
            vmt_tim_sections = tim_sections_retention_foreign + tim_sections_regular_foreign
        for tim_section in vmt_tim_sections:
            type_code = tim_section['type_code']
            if type_code == '01':
                vmt_section['vmt7'] += tim_section['TIM_2']
            elif type_code == '04':
                vmt_section['vmt8'] += tim_section['TIM_2']
            elif type_code == '06':
                vmt_section['vmt16'] += tim_section['TIM_2']
            elif type_code == '07':
                vmt_section['vmt17'] += tim_section['TIM_2']
            elif type_code == '08':
                vmt_section['vmt18'] += tim_section['TIM_2']

        # The rate should indicate how many pesos is one foreign currency
        currency_rate = "%.2f" % (1 / invoice.invoice_currency_rate if invoice.invoice_currency_rate else 0.0)

        sign = 1 if invoice.is_outbound() else -1

        regular_tax_lines = invoice.line_ids.filtered(
            lambda line: line.tax_line_id and not line.tax_line_id.l10n_co_edi_type.retention and line.tax_line_id.l10n_co_edi_type.code not in code_to_filter
        )
        withholding_amount = '%.2f' % (invoice.amount_untaxed + abs(sum(regular_tax_lines.mapped('amount_currency'))))
        withholding_amount_company = '%.2f' % (-sign * invoice.amount_untaxed_signed + sum(sign * line.balance for line in regular_tax_lines))

        # ENC_8: validation_time
        validation_time = fields.Datetime.now()
        validation_time = pytz.utc.localize(validation_time)
        bogota_tz = pytz.timezone('America/Bogota')
        validation_time = validation_time.astimezone(bogota_tz)
        validation_time = validation_time.strftime(DEFAULT_SERVER_TIME_FORMAT) + "-05:00"

        # ENC_9: edi_type
        if invoice.move_type == 'out_refund':
            edi_type = "91"
        elif invoice.move_type == 'out_invoice' and invoice.l10n_co_edi_debit_note:
            edi_type = "92"
        else:
            edi_type = "{0:0=2d}".format(int(invoice.l10n_co_edi_type))

        # description
        description_field = None
        if invoice.move_type in ('out_refund', 'in_refund'):
            description_field = 'l10n_co_edi_description_code_credit'
        if invoice.move_type in ('out_invoice', 'in_invoice') and invoice.l10n_co_edi_debit_note:
            description_field = 'l10n_co_edi_description_code_debit'
        description_code = invoice[description_field] if description_field else None
        description = dict(invoice._fields[description_field].selection).get(description_code) if description_code else None
        xml_content = self.env['ir.qweb']._render(self._l10n_co_edi_get_electronic_invoice_template(invoice), {
            'invoice': invoice,
            'sign': sign,
            'edi_type': edi_type,
            'company_partner': invoice.company_id.partner_id,
            'sales_partner': invoice.user_id,
            'invoice_partner': invoice.partner_id.commercial_partner_id,
            'tax_types': invoice.mapped('line_ids.tax_ids.l10n_co_edi_type'),
            'currency_rate': currency_rate,
            'shipping_partner': invoice.partner_shipping_id,
            'invoice_type_to_ref_1': invoice_type_to_ref_1,
            'ovt_taxes': ovt_taxes,
            'float_compare': float_compare,
            'notas': get_notas(),
            'withholding_amount': withholding_amount,
            'withholding_amount_company': withholding_amount_company,
            'base_lines': base_lines,
            'tim_sections_retention': tim_sections_retention,
            'tim_sections_regular': tim_sections_regular,
            'vmt_section': vmt_section,
            'validation_time': validation_time,
            'delivery_date': invoice.invoice_date + timedelta(1),
            'description_code': description_code,
            'description': description,
            'format_float': format_float,
            'format_monetary': format_monetary,
            'format_domestic_phone_number': format_domestic_phone_number,
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
        is_dian_used = (
            'l10n_co_dian_provider' in move.company_id._fields
            and move.company_id.l10n_co_dian_provider == 'dian'
        )
        if self.code != 'ubl_carvajal' or is_dian_used:
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
        oldest_date = now - timedelta(days=6)
        newest_date = now + timedelta(days=6)
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
        if move.l10n_co_edi_type == L10N_CO_EDI_TYPE['Export Invoice'] and \
                any(l.product_id and not l.product_id.l10n_co_edi_customs_code for l in move.invoice_line_ids):
            edi_result.append(_("Every exportation product must have a customs code."))
        elif move.invoice_date and not (oldest_date <= fields.Datetime.to_datetime(move.invoice_date) <= newest_date):
            move.message_post(body=_('The issue date can not be older than 6 days or more than 6 days in the future.'))
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
        if not move.l10n_co_edi_type:
            edi_result.append(_("You need to set the Electronic Invoice Type on the invoice."))

        # Sugar taxes
        for line in move.invoice_line_ids:
            if "IBUA" in line.tax_ids.l10n_co_edi_type.mapped('name') and line.product_id.l10n_co_edi_ref_nominal_tax == 0:
                edi_result.append(_("You should set 'Volume in milliliters' on product: %s when using IBUA taxes.", line.product_id.name))

        return edi_result

    def _l10n_co_edi_post_invoice_step_1(self, invoice):
        return {invoice: self._l10n_co_post_invoice_step_1(invoice)}

    def _l10n_co_edi_post_invoice_step_2(self, invoice):
        return {invoice: self._l10n_co_post_invoice_step_2(invoice)}

    # to remove in master
    def _l10n_co_edi_cancel_invoice(self, invoice):
        return {invoice: {'success': True}}
