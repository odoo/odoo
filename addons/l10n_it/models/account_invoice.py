# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import zipfile
import io
import logging
import re

from datetime import date, datetime

from odoo import api, fields, models, _
from odoo.tools import float_repr
from odoo.exceptions import UserError, ValidationError
from odoo.addons.base.models.ir_mail_server import MailDeliveryException

_logger = logging.getLogger(__name__)

DEFAULT_FACTUR_ITALIAN_DATE_FORMAT = '%Y-%m-%d'

PAYMENT_METHODS = [
    ("MP01", "[MP01] contanti"),
    ("MP02", "[MP02] assegno"),
    ("MP03", "[MP03] assegno circolare"),
    ("MP04", "[MP04] contanti presso Tesoreria"),
    ("MP05", "[MP05] bonifico"),
    ("MP06", "[MP06] vaglia cambiario"),
    ("MP07", "[MP07] bollettino bancario"),
    ("MP08", "[MP08] carta di pagamento"),
    ("MP09", "[MP09] RID"),
    ("MP10", "[MP10] RID utenze"),
    ("MP11", "[MP11] RID veloce"),
    ("MP12", "[MP12] RIBA"),
    ("MP13", "[MP13] MAV"),
    ("MP14", "[MP14] quietanza erario"),
    ("MP15", "[MP15] giroconto su conti di contabilità speciale"),
    ("MP16", "[MP16] domiciliazione bancaria"),
    ("MP17", "[MP17] domiciliazione postale"),
    ("MP18", "[MP18] bollettino di c/c postale"),
    ("MP19", "[MP19] SEPA Direct Debit"),
    ("MP20", "[MP20] SEPA Direct Debit CORE"),
    ("MP21", "[MP21] SEPA Direct Debit B2B"),
    ("MP22", "[MP22] Trattenuta su somme già riscosse")
]

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    _name = 'account.invoice'

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
    ], default='to_send')

    l10n_it_stamp_duty = fields.Float(default=0, string="Dati Bollo", size=15, readonly=True, states={'draft': [('readonly', False)]})

    l10n_it_document_order_ids = fields.One2many('document.order.data', 'l10n_it_invoice_id', string='Document order',
                                                   readonly=True, states={'draft': [('readonly', False)]}, copy=True)

    l10n_it_ddt_id = fields.Many2one('l10n.it.ddt', string='DDT', readonly=True, states={'draft': [('readonly', False)]})

    l10n_it_progressive_number = fields.Char(help="Unique sequence use to send this document to government", readonly=True)
    l10n_it_einvoice_name = fields.Char(readonly=True)

    l10n_it_einvoice_id = fields.Many2one('ir.attachment', string="Electronic invoice")

    @api.multi
    def invoice_validate(self):
        super(AccountInvoice, self).invoice_validate()
        for invoice in self:
            if invoice.type == 'in_invoice' or invoice.type == 'in_refund':
                invoice.l10n_it_send_state = "other"
                continue

            invoice._check_before_xml_exporting()

            if not invoice.l10n_it_progressive_number:
                invoice.l10n_it_progressive_number = invoice.env['ir.sequence'].next_by_code('account.it.invoice')

            invoice.invoice_generate_xml()
            invoice.l10n_it_send_state = "to_send"
            invoice.send_pec_mail()

    @api.multi
    def invoice_generate_xml(self):
        for invoice in self:
            if invoice.l10n_it_einvoice_id and invoice.l10n_it_send_state not in ['invalid', 'to_send']:
                raise UserError(_("You can't regenerate an E-Invoice when the first one is sent and there are no errors"))
            if invoice.l10n_it_einvoice_id:
                invoice.l10n_it_einvoice_id.unlink()
            report_name = '%(country_code)s%(codice)s_%(progressive_number)s.xml' % {
                'country_code': invoice.company_id.country_id.code,
                'codice': invoice.company_id.l10n_it_codice_fiscale,
                'progressive_number': invoice.l10n_it_progressive_number,
                }
            invoice.l10n_it_einvoice_name = report_name

            data = b"<?xml version='1.0' encoding='UTF-8'?>" + invoice._export_as_xml()
            description = _('Italian invoice: %s') % invoice.type
            invoice.l10n_it_einvoice_id = self.env['ir.attachment'].create({
                'name': report_name,
                'res_id': invoice.id,
                'res_model': invoice._name,
                'datas': base64.encodestring(data),
                'datas_fname': report_name,
                'description': description,
                'type': 'binary',
                })

            invoice.message_post(
                body=(_("E-Invoice is generated on %s by %s") % (fields.Datetime.now(), self.env.user.display_name))
            )

    def _check_before_xml_exporting(self):
        seller = self.company_id
        buyer = self.commercial_partner_id

        # <1.1.1.1>
        if not seller.country_id:
            raise UserError(_("%s must have a country") % (seller.display_name))

        # <1.1.1.2>
        if not seller.vat:
            raise UserError(_("%s must have a VAT number") % (seller.display_name))
        elif len(seller.vat) > 30:
            raise UserError(_("The maximum length for VAT number is 30. %s have a VAT number too long: %s.") % (seller.display_name, seller.vat))

        # <1.2.1.2>
        if not seller.l10n_it_codice_fiscale:
            raise UserError(_("%s must have a codice fiscale number") % (seller.display_name))

        # <1.2.1.8>
        if not seller.l10n_it_tax_system:
            raise UserError("The seller's company must have a tax system.")

        # <1.2.2>
        if not seller.street and not seller.street2:
            raise UserError(_("%s must have a street.") % (seller.display_name))
        if not seller.zip:
            raise UserError(_("%s must have a post code.") % (seller.display_name))
        if len(seller.zip) != 5:
            raise UserError(_("%s must have a post code of length 5.") % (seller.display_name))
        if not seller.city:
            raise UserError(_("%s must have a city.") % (seller.display_name))
        if not seller.country_id:
            raise UserError(_("%s must have a country.") % (seller.display_name))

        # <1.4.1>
        if not buyer.vat and not buyer.l10n_it_codice_fiscale:
            raise UserError(_("The buyer, %s, or his company must have either a VAT number either a tax code (Codice Fiscale).") % (buyer.display_name))

        # <1.4.2>
        if not buyer.street and not buyer.street2:
            raise UserError(_("%s must have a street.") % (buyer.display_name))
        if not buyer.zip:
            raise UserError(_("%s must have a post code.") % (buyer.display_name))
        if len(buyer.zip) != 5:
            raise UserError(_("%s must have a post code of length 5.") % (buyer.display_name))
        if not buyer.city:
            raise UserError(_("%s must have a city.") % (buyer.display_name))
        if not buyer.country_id:
            raise UserError(_("%s must have a country.") % (buyer.display_name))

        # <2.2.1>
        for invoice_line in self.invoice_line_ids:
            if len(invoice_line.invoice_line_tax_ids) != 1:
                raise UserError(_("You must select one and only one tax by line."))

        # <2.4.2.2>
        if self.partner_bank_id and self.partner_bank_id.acc_number:
            if len(self.partner_bank_id.acc_number) < 15 or len(self.partner_bank_id.acc_number) > 34:
                raise UserError(_("IBAN is incorrect."))
        elif self.payment_term_id and self.payment_term_id.l10n_it_payment_method == 'MP05':
            raise UserError(_("Your company need an IBAN."))
        if self.partner_bank_id and self.partner_bank_id.bank_id.bic:
            if len(self.partner_bank_id.bank_id.bic) < 8 or len(self.partner_bank_id.bank_id.bic) > 11:
                raise UserError(_("BIC is incorrect."))
        elif self.payment_term_id and self.payment_term_id.l10n_it_payment_method == 'MP05':
            raise UserError(_("Your company need a BIC."))

        for tax_line in self.tax_line_ids:
            if not tax_line.tax_id.l10n_it_has_exoneration and tax_line.tax_id.amount == 0:
                raise ValidationError(_("%s has an amount of 0.0, you must indicate the kind of exoneration." % tax_line.name))

    def _export_as_xml(self):
        ''' Create the xml file content.
        :return: The XML content as str.
        '''
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
                return float_repr(number, 2)

            cents = number_splited[1]
            if len(cents) > 8:
                return float_repr(number, 8)
            return float_repr(number, max(2, len(cents)))

        def format_numbers_two(number):
            #format number to str with 2 (event if it's .00)
            return float_repr(number, 2)

        def discount_type(discount):
            if discount > 0:
                return 'SC'
            return 'MG'

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

        formato_trasmissione = "FPR12"
        if len(self.commercial_partner_id.l10n_it_pa_index or '1') == 6 or self.commercial_partner_id.country_id.code != 'IT':
            formato_trasmissione = "FPA12"

        if self.type == 'out_invoice':
            document_type = 'TD01'
        elif self.type == 'out_refund':
            document_type = 'TD04'
        else:
            document_type = 'TD0X'

        if self.payment_term_id and self.payment_term_id.l10n_it_payment_method:
            payment_method = self.payment_term_id.l10n_it_payment_method
        else:
            payment_method = False

        pdf = self.env.ref('account.account_invoices').render_qweb_pdf(self.id)[0]
        pdf = base64.b64encode(pdf)
        pdf_name = re.sub(r'\W+', '', self.number) + '.pdf'

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
            'abs': abs,
            'formato_trasmissione': formato_trasmissione,
            'document_type': document_type,
            'payment_method': payment_method,
            'pdf': pdf,
            'pdf_name': pdf_name,
        }
        content = self.env.ref('l10n_it.account_invoice_it_FatturaPA_export').render(template_values)
        return content

    def _create_zip(self, attachments):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zipf:
            for attachment in attachments:
                filename = attachment.datas_fname
                zipf.writestr(filename, base64.b64decode(attachment['datas']))
        return stream.getvalue()

    @api.multi
    def send_pec_mail(self):
        self.ensure_one()
        allowed_state = ['to_send', 'invalid']

        if not self.company_id.l10n_it_mail_pec_server_id or not self.company_id.l10n_it_address_send_fatturapa:
            self.message_post(
                body=(_("Error when sending mail with E-Invoice: Your company must have a mail PEC server and must indicate the mail PEC that will send electronic invoice."))
                )
            self.l10n_it_send_state = 'invalid'
            return

        if self.l10n_it_send_state not in allowed_state:
            raise UserError(_("%s isn't in a right state. It must be in a 'Not yet send' or 'Invalid' state.") % (self.display_name))

        message = self.env['mail.message'].create({
            'subject': _('Sending file: %s') % (self.l10n_it_einvoice_id.name),
            'body': _('Sending file: %s to ES: %s') % (self.l10n_it_einvoice_id.name, self.env.user.company_id.l10n_it_address_recipient_fatturapa),
            'email_from': self.env.user.company_id.l10n_it_address_send_fatturapa,
            'mail_server_id': self.env.user.company_id.l10n_it_mail_pec_server_id.id,
            'attachment_ids': [(6, 0, self.l10n_it_einvoice_id.ids)],
        })

        mail_fattura = self.env['mail.mail'].create({
            'mail_message_id': message.id,
            'email_to': self.env.user.company_id.l10n_it_address_recipient_fatturapa,
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

class AccountTax(models.Model):
    _name = "account.tax"
    _inherit = "account.tax"

    l10n_it_vat_due_date = fields.Selection([
        ("I", "[I] IVA ad esigibilità immediata"),
        ("D", "[D] IVA ad esigibilità differita"),
        ("S", "[S] Scissione dei pagamenti")], default="I", string="VAT due date")

    l10n_it_has_exoneration = fields.Boolean(string="Has exoneration of tax", help="Tax has a tax exoneration.")
    l10n_it_kind_exoneration = fields.Selection(selection=[
            ("N1", "[N1] Escluse ex art. 15"),
            ("N2", "[N2] Non soggette"),
            ("N3", "[N3] Non imponibili"),
            ("N4", "[N4] Esenti"),
            ("N5", "[N5] Regime del margine / IVA non esposta in fattura"),
            ("N6", "[N6] Inversione contabile (per le operazioni in reverse charge ovvero nei casi di autofatturazione per acquisti extra UE di servizi ovvero per importazioni di beni nei soli casi previsti)"),
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
                    raise ValidationError("If the tax has exoneration, you must enter a kind of exoneration, a law reference and the amount of the tax must be 0.0.")
                if tax.l10n_it_kind_exoneration == 'N6' and tax.l10n_it_vat_due_date == 'S':
                    raise UserError(_("'Scissione dei pagamenti' is not compatible with exoneration of kind 'N6'"))

class AccountPaymentTerm(models.Model):
    _name = "account.payment.term"
    _inherit = "account.payment.term"

    l10n_it_payment_method = fields.Selection(selection=PAYMENT_METHODS,
                                              string="Payment Method")

    l10n_it_condition = fields.Selection(selection=[
            ("TP01", "[TP01] Pagamento a rate"),
            ("TP02", "[TP02] Pagamento completo"),
            ("TP03", "[TP03] Anticipo")],
        string="payment condition", required="True", default="TP01")
