# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import re

from datetime import datetime

from odoo import api, fields, models, _
from odoo.tools import float_repr, float_compare
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)

DEFAULT_FACTUR_ITALIAN_DATE_FORMAT = '%Y-%m-%d'


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_edi_transaction = fields.Char(copy=False, string="FatturaPA Transaction")
    l10n_it_edi_attachment_id = fields.Many2one('ir.attachment', copy=False, string="FatturaPA Attachment")

    l10n_it_stamp_duty = fields.Float(default=0, string="Dati Bollo", readonly=True, states={'draft': [('readonly', False)]})

    l10n_it_ddt_id = fields.Many2one('l10n_it.ddt', string='DDT', readonly=True, states={'draft': [('readonly', False)]}, copy=False)

    l10n_it_einvoice_name = fields.Char(compute='_compute_l10n_it_einvoice')

    l10n_it_einvoice_id = fields.Many2one('ir.attachment', string="Electronic invoice", compute='_compute_l10n_it_einvoice')

    @api.depends('edi_document_ids', 'edi_document_ids.attachment_id')
    def _compute_l10n_it_einvoice(self):
        fattura_pa = self.env.ref('l10n_it_edi.edi_fatturaPA')
        for invoice in self:
            einvoice = invoice.edi_document_ids.filtered(lambda d: d.edi_format_id == fattura_pa)
            invoice.l10n_it_einvoice_id = einvoice.attachment_id
            invoice.l10n_it_einvoice_name = einvoice.attachment_id.name

    def invoice_generate_xml(self):
        self.ensure_one()
        report_name = self.env['account.edi.format']._l10n_it_edi_generate_electronic_invoice_filename(self)

        data = "<?xml version='1.0' encoding='UTF-8'?>" + str(self._l10n_it_edi_export_invoice_as_xml())
        description = _('Italian invoice: %s', self.move_type)
        attachment = self.env['ir.attachment'].create({
            'name': report_name,
            'res_id': self.id,
            'res_model': self._name,
            'raw': data.encode(),
            'description': description,
            'type': 'binary',
            })

        self.message_post(
            body=(_("E-Invoice is generated on %s by %s") % (fields.Datetime.now(), self.env.user.display_name))
        )
        return {'attachment': attachment}

    def _is_commercial_partner_pa(self):
        """
            Returns True if the destination of the FatturaPA belongs to the Public Administration.
        """
        return len(self.commercial_partner_id.l10n_it_pa_index or '') == 6

    def _l10n_it_edi_prepare_fatturapa_line_details(self, reverse_charge_refund=False, is_downpayment=False, convert_to_euros=True):
        """ Returns a list of dictionaries passed to the template for the invoice lines (DettaglioLinee)
        """
        invoice_lines = []
        lines = self.invoice_line_ids.filtered(lambda l: not l.display_type in ('line_note', 'line_section'))
        for num, line in enumerate(lines):
            sign = -1 if line.move_id.is_inbound() else 1
            price_subtotal = (line.balance * sign) if convert_to_euros else line.price_subtotal
            # The price_subtotal should be inverted when the line is a reverse charge refund.
            if reverse_charge_refund:
                price_subtotal = -price_subtotal

            # Unit price
            price_unit = 0
            if line.quantity and line.discount != 100.0:
                price_unit = price_subtotal / ((1 - (line.discount or 0.0) / 100.0) * abs(line.quantity))
            else:
                price_unit = line.price_unit

            description = line.name
            if not is_downpayment:
                if line.price_subtotal < 0:
                    moves = line._get_downpayment_lines().move_id
                    if moves:
                        description += ', '.join([move.name for move in moves])

            line_dict = {
                'line': line,
                'line_number': num + 1,
                'description': description or 'NO NAME',
                'unit_price': price_unit,
                'subtotal_price': price_subtotal,
            }
            invoice_lines.append(line_dict)
        return invoice_lines

    def _l10n_it_edi_prepare_fatturapa_tax_details(self, tax_details, reverse_charge_refund=False):
        """ Returns a list of dictionaries passed to the template for the invoice lines (DatiRiepilogo)
        """
        tax_lines = []
        for _tax_name, tax_dict in tax_details['tax_details'].items():
            # The assumption is that the company currency is EUR.
            base_amount = tax_dict['base_amount']
            tax_amount = tax_dict['tax_amount']
            tax_rate = tax_dict['tax'].amount
            expected_base_amount = tax_amount * 100 / tax_rate if tax_rate else False
            tax = tax_dict['tax']
            # Constraints within the edi make local rounding on price included taxes a problem.
            # To solve this there is a <Arrotondamento> or 'rounding' field, such that:
            #   taxable base = sum(taxable base for each unit) + Arrotondamento
            if tax.price_include and tax.amount_type == 'percent':
                if expected_base_amount and float_compare(base_amount, expected_base_amount, 2):
                    tax_dict['rounding'] = base_amount - (tax_amount * 100 / tax_rate)
                    tax_dict['base_amount'] = base_amount - tax_dict['rounding']

            if not reverse_charge_refund:
                tax_dict['base_amount'] = abs(tax_dict['base_amount'])
                tax_dict['tax_amount'] = abs(tax_dict['tax_amount'])

            tax_line_dict = {
                'tax': tax,
                'rounding': tax_dict.get('rounding', False),
                'base_amount': tax_dict['base_amount'],
                'tax_amount': tax_dict['tax_amount'],
            }
            tax_lines.append(tax_line_dict)
        return tax_lines

    def _prepare_fatturapa_export_values(self):
        self.ensure_one()

        def format_date(dt):
            # Format the date in the italian standard.
            dt = dt or datetime.now()
            return dt.strftime(DEFAULT_FACTUR_ITALIAN_DATE_FORMAT)

        def format_monetary(number, currency):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            return float_repr(number, min(2, currency.decimal_places))

        def format_numbers(number):
            #format number to str with between 2 and 8 decimals (event if it's .00)
            number_splited = str(number).split('.')
            if len(number_splited) == 1:
                return "%.02f" % number

            cents = number_splited[1]
            if len(cents) > 8:
                return "%.08f" % number
            return float_repr(number, max(2, len(cents)))

        def format_numbers_two(number):
            #format number to str with 2 (event if it's .00)
            return "%.02f" % number

        def discount_type(discount):
            return 'SC' if discount > 0 else 'MG'

        def format_phone(number):
            if not number:
                return False
            number = number.replace(' ', '').replace('/', '').replace('.', '')
            if len(number) > 4 and len(number) < 13:
                return number
            return False

        def get_vat_number(vat):
            if vat[:2].isdecimal():
                return vat.replace(' ', '')
            return vat[2:].replace(' ', '')

        def get_vat_country(vat):
            if vat[:2].isdecimal():
                return 'IT'
            return vat[:2].upper()

        def format_alphanumeric(text_to_convert):
            return text_to_convert.encode('latin-1', 'replace').decode('latin-1') if text_to_convert else False

        formato_trasmissione = "FPA12" if self._is_commercial_partner_pa() else "FPR12"

        # Flags
        in_eu = self.env['account.edi.format']._l10n_it_edi_partner_in_eu
        is_self_invoice = self.env['account.edi.format']._l10n_it_edi_is_self_invoice(self)
        document_type = self.env['account.edi.format']._l10n_it_get_document_type(self)
        if self.env['account.edi.format']._l10n_it_is_simplified_document_type(document_type):
            formato_trasmissione = "FSM10"

        # Represent if the document is a reverse charge refund in a single variable
        reverse_charge = document_type in ['TD17', 'TD18', 'TD19']
        is_downpayment = document_type in ['TD02']
        reverse_charge_refund = self.move_type == 'in_refund' and reverse_charge
        convert_to_euros = self.currency_id.name != 'EUR'

        # b64encode returns a bytestring, the template tries to turn it to string,
        # but only gets the repr(pdf) --> "b'<base64_data>'"
        pdf = self.env['ir.actions.report']._render_qweb_pdf("account.account_invoices", self.id)[0]
        pdf = base64.b64encode(pdf).decode()
        pdf_name = re.sub(r'\W+', '', self.name) + '.pdf'

        tax_details = self._prepare_edi_tax_details(
            filter_to_apply=lambda base_line, tax_values: tax_values['tax_repartition_line'].factor_percent >= 0
        )

        company = self.company_id
        partner = self.commercial_partner_id
        buyer = partner if not is_self_invoice else company
        seller = company if not is_self_invoice else partner
        codice_destinatario = (
            (is_self_invoice and company.partner_id.l10n_it_pa_index)
            or partner.l10n_it_pa_index
            or (partner.country_id.code == 'IT' and '0000000')
            or 'XXXXXXX')

        # Self-invoices are technically -100%/+100% repartitioned
        # but functionally need to be exported as 100%
        document_total = self.amount_total
        if is_self_invoice:
            document_total += sum([abs(v['tax_amount_currency']) for k, v in tax_details['tax_details'].items()])
            if reverse_charge_refund:
                document_total = -abs(document_total)

        # Reference line for finding the conversion rate used in the document
        conversion_line = self.invoice_line_ids.sorted(lambda l: abs(l.balance), reverse=True)[0] if self.invoice_line_ids else None
        conversion_rate = float_repr(
            abs(conversion_line.balance / conversion_line.amount_currency), precision_digits=5,
        ) if convert_to_euros and conversion_line else None

        invoice_lines = self._l10n_it_edi_prepare_fatturapa_line_details(reverse_charge_refund, is_downpayment, convert_to_euros)
        tax_lines = self._l10n_it_edi_prepare_fatturapa_tax_details(tax_details, reverse_charge_refund)

        # Create file content.
        template_values = {
            'record': self,
            'balance_multiplicator': -1 if self.is_inbound() else 1,
            'company': company,
            'sender': company,
            'sender_partner': company.partner_id,
            'partner': partner,
            'buyer': buyer,
            'buyer_partner': partner if not is_self_invoice else company.partner_id,
            'buyer_is_company': is_self_invoice or partner.is_company,
            'seller': seller,
            'seller_partner': company.partner_id if not is_self_invoice else partner,
            'currency': self.currency_id or self.company_currency_id if not convert_to_euros else self.env.ref('base.EUR'),
            'document_total': document_total,
            'representative': company.l10n_it_tax_representative_partner_id,
            'codice_destinatario': codice_destinatario,
            'regime_fiscale': company.l10n_it_tax_system if not is_self_invoice else 'RF18',
            'is_self_invoice': is_self_invoice,
            'partner_bank': self.partner_bank_id,
            'format_date': format_date,
            'format_monetary': format_monetary,
            'format_numbers': format_numbers,
            'format_numbers_two': format_numbers_two,
            'format_phone': format_phone,
            'format_alphanumeric': format_alphanumeric,
            'discount_type': discount_type,
            'formato_trasmissione': formato_trasmissione,
            'document_type': document_type,
            'pdf': pdf,
            'pdf_name': pdf_name,
            'tax_details': tax_details,
            'abs': abs,
            'normalize_codice_fiscale': partner._l10n_it_normalize_codice_fiscale,
            'get_vat_number': get_vat_number,
            'get_vat_country': get_vat_country,
            'in_eu': in_eu,
            'rc_refund': reverse_charge_refund,
            'invoice_lines': invoice_lines,
            'tax_lines': tax_lines,
            'conversion_rate': conversion_rate,
        }
        return template_values

    def _post(self, soft=True):
        # OVERRIDE
        posted = super()._post(soft=soft)
        return posted

    def _compose_info_message(self, tree, element_tags):
        output_str = ""
        elements = tree.xpath(element_tags)
        for element in elements:
            output_str += "<ul>"
            for line in element.iter():
                if line.text:
                    text = " ".join(line.text.split())
                    if text:
                        output_str += "<li>%s: %s</li>" % (line.tag, text)
            output_str += "</ul>"
        return output_str

    def _compose_multi_info_message(self, tree, element_tags):
        output_str = "<ul>"

        for element_tag in element_tags:
            elements = tree.xpath(element_tag)
            if not elements:
                continue
            for element in elements:
                text = " ".join(element.text.split())
                if text:
                    output_str += "<li>%s: %s</li>" % (element.tag, text)
        return output_str + "</ul>"

class AccountTax(models.Model):
    _name = "account.tax"
    _inherit = "account.tax"

    l10n_it_vat_due_date = fields.Selection([
        ("I", "[I] IVA ad esigibilità immediata"),
        ("D", "[D] IVA ad esigibilità differita"),
        ("S", "[S] Scissione dei pagamenti")], default="I", string="VAT due date")

    l10n_it_has_exoneration = fields.Boolean(string="Has exoneration of tax (Italy)", help="Tax has a tax exoneration.")
    l10n_it_kind_exoneration = fields.Selection(selection=[
            ("N1", "[N1] Escluse ex art. 15"),
            ("N2", "[N2] Non soggette"),
            ("N2.1", "[N2.1] Non soggette ad IVA ai sensi degli artt. Da 7 a 7-septies del DPR 633/72"),
            ("N2.2", "[N2.2] Non soggette – altri casi"),
            ("N3", "[N3] Non imponibili"),
            ("N3.1", "[N3.1] Non imponibili – esportazioni"),
            ("N3.2", "[N3.2] Non imponibili – cessioni intracomunitarie"),
            ("N3.3", "[N3.3] Non imponibili – cessioni verso San Marino"),
            ("N3.4", "[N3.4] Non imponibili – operazioni assimilate alle cessioni all’esportazione"),
            ("N3.5", "[N3.5] Non imponibili – a seguito di dichiarazioni d’intento"),
            ("N3.6", "[N3.6] Non imponibili – altre operazioni che non concorrono alla formazione del plafond"),
            ("N4", "[N4] Esenti"),
            ("N5", "[N5] Regime del margine / IVA non esposta in fattura"),
            ("N6", "[N6] Inversione contabile (per le operazioni in reverse charge ovvero nei casi di autofatturazione per acquisti extra UE di servizi ovvero per importazioni di beni nei soli casi previsti)"),
            ("N6.1", "[N6.1] Inversione contabile – cessione di rottami e altri materiali di recupero"),
            ("N6.2", "[N6.2] Inversione contabile – cessione di oro e argento puro"),
            ("N6.3", "[N6.3] Inversione contabile – subappalto nel settore edile"),
            ("N6.4", "[N6.4] Inversione contabile – cessione di fabbricati"),
            ("N6.5", "[N6.5] Inversione contabile – cessione di telefoni cellulari"),
            ("N6.6", "[N6.6] Inversione contabile – cessione di prodotti elettronici"),
            ("N6.7", "[N6.7] Inversione contabile – prestazioni comparto edile esettori connessi"),
            ("N6.8", "[N6.8] Inversione contabile – operazioni settore energetico"),
            ("N6.9", "[N6.9] Inversione contabile – altri casi"),
            ("N7", "[N7] IVA assolta in altro stato UE (prestazione di servizi di telecomunicazioni, tele-radiodiffusione ed elettronici ex art. 7-octies, comma 1 lett. a, b, art. 74-sexies DPR 633/72)")],
        string="Exoneration",
        help="Exoneration type",
        default="N1")
    l10n_it_law_reference = fields.Char(string="Law Reference", size=100)

    @api.constrains('l10n_it_has_exoneration',
                    'l10n_it_kind_exoneration',
                    'l10n_it_law_reference',
                    'amount',
                    'l10n_it_vat_due_date')
    def _check_exoneration_with_no_tax(self):
        for tax in self:
            if tax.l10n_it_has_exoneration:
                if not tax.l10n_it_kind_exoneration or not tax.l10n_it_law_reference or tax.amount != 0:
                    raise ValidationError(_("If the tax has exoneration, you must enter a kind of exoneration, a law reference and the amount of the tax must be 0.0."))
                if tax.l10n_it_kind_exoneration == 'N6' and tax.l10n_it_vat_due_date == 'S':
                    raise UserError(_("'Scissione dei pagamenti' is not compatible with exoneration of kind 'N6'"))
