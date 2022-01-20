# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import zipfile
import io
import logging
import re

from datetime import date, datetime
from lxml import etree

from odoo import api, fields, models, _
from odoo.tools import float_repr
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.tests.common import Form


_logger = logging.getLogger(__name__)

DEFAULT_FACTUR_ITALIAN_DATE_FORMAT = '%Y-%m-%d'


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_it_send_state = fields.Selection([
        ('new', 'New'),
        ('other', 'Other'),
        ('to_send', 'Not yet send'),
        ('sent', 'Sent, waiting for response'),
        ('invalid', 'Sent, but invalid'),
        ('delivered', 'This invoice is delivered'),
        ('delivered_accepted', 'This invoice is delivered and accepted by destinatory'),
        ('delivered_refused', 'This invoice is delivered and refused by destinatory'),
        ('delivered_expired', 'This invoice is delivered and expired (expiry of the maximum term for communication of acceptance/refusal)'),
        ('failed_delivery', 'Delivery impossible, ES certify that it has received the invoice and that the file \
                        could not be delivered to the addressee') # ok we must do nothing
    ], default='to_send', copy=False)

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

    def _check_before_xml_exporting(self):
        # DEPRECATED use AccountEdiFormat._l10n_it_edi_check_invoice_configuration instead
        errors = self.env['account.edi.format']._l10n_it_edi_check_invoice_configuration(self)
        if errors:
            raise UserError(self.env['account.edi.format']._format_error_message(_("Invalid configuration:"), errors))

    def invoice_generate_xml(self):
        self.ensure_one()
        report_name = self.env['account.edi.format']._l10n_it_edi_generate_electronic_invoice_filename(self)

        data = b"<?xml version='1.0' encoding='UTF-8'?>" + self._export_as_xml()
        description = _('Italian invoice: %s', self.move_type)
        attachment = self.env['ir.attachment'].create({
            'name': report_name,
            'res_id': self.id,
            'res_model': self._name,
            'datas': base64.encodebytes(data),
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
        return len(self.commercial_partner_id.l10n_it_pa_index or '')  == 6

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
            return vat[2:].replace(' ', '')

        def get_vat_country(vat):
            return vat[:2].upper()

        def in_eu(partner):
            europe = self.env.ref('base.europe', raise_if_not_found=False)
            country = partner.country_id
            if not europe or not country or country in europe.country_ids:
                return True
            return False

        formato_trasmissione = "FPA12" if self._is_commercial_partner_pa() else "FPR12"

        if self.move_type == 'out_invoice':
            document_type = 'TD01'
        elif self.move_type == 'out_refund':
            document_type = 'TD04'
        else:
            document_type = 'TD0X'

        pdf = self.env.ref('account.account_invoices')._render_qweb_pdf(self.id)[0]
        pdf = base64.b64encode(pdf)
        pdf_name = re.sub(r'\W+', '', self.name) + '.pdf'

        # tax map for 0% taxes which have no tax_line_id
        tax_map = dict()
        for line in self.line_ids:
            for tax in line.tax_ids:
                if tax.amount == 0.0:
                    tax_map[tax] = tax_map.get(tax, 0.0) + line.price_subtotal

        # Create file content.
        template_values = {
            'record': self,
            'format_date': format_date,
            'format_monetary': format_monetary,
            'format_numbers': format_numbers,
            'format_numbers_two': format_numbers_two,
            'format_phone': format_phone,
            'discount_type': discount_type,
            'get_vat_number': get_vat_number,
            'get_vat_country': get_vat_country,
            'in_eu': in_eu,
            'abs': abs,
            'formato_trasmissione': formato_trasmissione,
            'document_type': document_type,
            'pdf': pdf,
            'pdf_name': pdf_name,
            'tax_map': tax_map,
        }
        return template_values

    def _export_as_xml(self):
        '''DEPRECATED : this will be moved to AccountEdiFormat in a future version.
        Create the xml file content.
        :return: The XML content as str.
        '''
        template_values = self._prepare_fatturapa_export_values()
        content = self.env.ref('l10n_it_edi.account_invoice_it_FatturaPA_export')._render(template_values)
        return content

    def _post(self, soft=True):
        # OVERRIDE
        posted = super()._post(soft=soft)

        for move in posted.filtered(lambda m: m.l10n_it_send_state == 'to_send' and m.move_type in ['out_invoice', 'out_refund'] and m.company_id.country_id.code == 'IT'):
            move.send_pec_mail()

        return posted

    def send_pec_mail(self):
        self.ensure_one()
        allowed_state = ['to_send', 'invalid']

        if (
            not self.company_id.l10n_it_mail_pec_server_id
            or not self.company_id.l10n_it_mail_pec_server_id.active
            or not self.company_id.l10n_it_address_send_fatturapa
        ):
            self.message_post(
                body=(_("Error when sending mail with E-Invoice: Your company must have a mail PEC server and must indicate the mail PEC that will send electronic invoice."))
                )
            self.l10n_it_send_state = 'invalid'
            return

        if self.l10n_it_send_state not in allowed_state:
            raise UserError(_("%s isn't in a right state. It must be in a 'Not yet send' or 'Invalid' state.") % (self.display_name))

        message = self.env['mail.message'].create({
            'subject': _('Sending file: %s') % (self.l10n_it_einvoice_name),
            'body': _('Sending file: %s to ES: %s') % (self.l10n_it_einvoice_name, self.env.company.l10n_it_address_recipient_fatturapa),
            'author_id': self.env.user.partner_id.id,
            'email_from': self.env.company.l10n_it_address_send_fatturapa,
            'reply_to': self.env.company.l10n_it_address_send_fatturapa,
            'mail_server_id': self.env.company.l10n_it_mail_pec_server_id.id,
            'attachment_ids': [(6, 0, self.l10n_it_einvoice_id.ids)],
        })

        mail_fattura = self.env['mail.mail'].sudo().with_context(wo_bounce_return_path=True).create({
            'mail_message_id': message.id,
            'email_to': self.env.company.l10n_it_address_recipient_fatturapa,
        })
        try:
            mail_fattura.send(raise_exception=True)
            self.message_post(
                body=(_("Mail sent on %s by %s") % (fields.Datetime.now(), self.env.user.display_name))
                )
            self.l10n_it_send_state = 'sent'
        except MailDeliveryException as error:
            self.message_post(
                body=(_("Error when sending mail with E-Invoice: %s") % (error.args[0]))
                )
            self.l10n_it_send_state = 'invalid'

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
            ("N7", "[N7] IVA assolta in altro stato UE (vendite a distanza ex art. 40 c. 3 e 4 e art. 41 c. 1 lett. b,  DL 331/93; prestazione di servizi di telecomunicazioni, tele-radiodiffusione ed elettronici ex art. 7-sexies lett. f, g, art. 74-sexies DPR 633/72)")],
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
