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
    ], default='to_send', copy=False)

    l10n_it_stamp_duty = fields.Float(default=0, string="Dati Bollo", size=15, readonly=True, states={'draft': [('readonly', False)]})

    l10n_it_ddt_id = fields.Many2one('l10n_it.ddt', string='DDT', readonly=True, states={'draft': [('readonly', False)]}, copy=False)

    l10n_it_einvoice_name = fields.Char(readonly=True, copy=False)

    l10n_it_einvoice_id = fields.Many2one('ir.attachment', string="Electronic invoice", copy=False)

    @api.multi
    def invoice_validate(self):
        # Clean context from default_type to avoid making attachment
        # with wrong values in subsequent operations
        cleaned_ctx = dict(self.env.context)
        cleaned_ctx.pop('default_type', None)
        self = self.with_context(cleaned_ctx)

        super(AccountInvoice, self).invoice_validate()
        for invoice in self:
            if invoice.company_id.country_id != self.env.ref('base.it'):
                continue
            if invoice.type == 'in_invoice' or invoice.type == 'in_refund':
                invoice.l10n_it_send_state = "other"
                continue
            if invoice.l10n_it_send_state in ['sent', 'delivered', 'delivered_accepted']:
                continue

            invoice._check_before_xml_exporting()

            invoice.invoice_generate_xml()
            if len(invoice.commercial_partner_id.l10n_it_pa_index or '') == 6:
                invoice.message_post(
                    body=(_("Invoices for PA are not managed by Odoo, you can download the document and send it on your own."))
                )
                invoice.l10n_it_send_state = "other"
                continue
            invoice.l10n_it_send_state = "to_send"
            invoice.send_pec_mail()

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
            raise UserError(_("The seller's company must have a tax system."))

        # <1.2.2>
        if not seller.street and not seller.street2:
            raise UserError(_("%s must have a street.") % (seller.display_name))
        if not seller.zip:
            raise UserError(_("%s must have a post code.") % (seller.display_name))
        if len(seller.zip) != 5 and seller.country_id.code == 'IT':
            raise UserError(_("%s must have a post code of length 5.") % (seller.display_name))
        if not seller.city:
            raise UserError(_("%s must have a city.") % (seller.display_name))
        if not seller.country_id:
            raise UserError(_("%s must have a country.") % (seller.display_name))

        # <1.4.1>
        if not buyer.vat and not buyer.l10n_it_codice_fiscale and buyer.country_id.code == 'IT':
            raise UserError(_("The buyer, %s, or his company must have either a VAT number either a tax code (Codice Fiscale).") % (buyer.display_name))

        # <1.4.2>
        if not buyer.street and not buyer.street2:
            raise UserError(_("%s must have a street.") % (buyer.display_name))
        if not buyer.zip:
            raise UserError(_("%s must have a post code.") % (buyer.display_name))
        if len(buyer.zip) != 5 and buyer.country_id.code == 'IT':
            raise UserError(_("%s must have a post code of length 5.") % (buyer.display_name))
        if not buyer.city:
            raise UserError(_("%s must have a city.") % (buyer.display_name))
        if not buyer.country_id:
            raise UserError(_("%s must have a country.") % (buyer.display_name))

        # <2.2.1>
        for invoice_line in self.invoice_line_ids:
            if len(invoice_line.invoice_line_tax_ids) != 1:
                raise UserError(_("You must select one and only one tax by line."))

        for tax_line in self.tax_line_ids:
            if not tax_line.tax_id.l10n_it_has_exoneration and tax_line.tax_id.amount == 0:
                raise ValidationError(_("%s has an amount of 0.0, you must indicate the kind of exoneration." % tax_line.name))

    @api.multi
    def invoice_generate_xml(self):
        for invoice in self:
            if invoice.l10n_it_einvoice_id and invoice.l10n_it_send_state not in ['invalid', 'to_send']:
                raise UserError(_("You can't regenerate an E-Invoice when the first one is sent and there are no errors"))
            if invoice.l10n_it_einvoice_id:
                invoice.l10n_it_einvoice_id.unlink()

            a = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            n = invoice.id
            progressive_number = ""
            while n:
                (n,m) = divmod(n,len(a))
                progressive_number = a[m] + progressive_number

            report_name = '%(country_code)s%(codice)s_%(progressive_number)s.xml' % {
                'country_code': invoice.company_id.country_id.code,
                'codice': invoice.company_id.l10n_it_codice_fiscale,
                'progressive_number': progressive_number.zfill(5),
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

        formato_trasmissione = "FPR12"
        if len(self.commercial_partner_id.l10n_it_pa_index or '1') == 6:
            formato_trasmissione = "FPA12"

        if self.type == 'out_invoice':
            document_type = 'TD01'
        elif self.type == 'out_refund':
            document_type = 'TD04'
        else:
            document_type = 'TD0X'

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
            'in_eu': in_eu,
            'abs': abs,
            'formato_trasmissione': formato_trasmissione,
            'document_type': document_type,
            'pdf': pdf,
            'pdf_name': pdf_name,
        }
        content = self.env.ref('l10n_it_edi.account_invoice_it_FatturaPA_export').render(template_values)
        return content

    @api.multi
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
            'subject': _('Sending file: %s') % (self.l10n_it_einvoice_id.name),
            'body': _('Sending file: %s to ES: %s') % (self.l10n_it_einvoice_id.name, self.env.user.company_id.l10n_it_address_recipient_fatturapa),
            'email_from': self.env.user.company_id.l10n_it_address_send_fatturapa,
            'reply_to': self.env.user.company_id.l10n_it_address_send_fatturapa,
            'mail_server_id': self.env.user.company_id.l10n_it_mail_pec_server_id.id,
            'attachment_ids': [(6, 0, self.l10n_it_einvoice_id.ids)],
        })

        mail_fattura = self.env['mail.mail'].with_context(wo_bounce_return_path=True).create({
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

    def _import_xml_invoice(self, content, attachment):
        ''' Extract invoice values from the E-Invoice xml tree passed as parameter.

        :param content: The tree of the xml file.
        :return: A dictionary containing account.invoice values to create/update it.
        '''

        try:
            tree = etree.fromstring(content)
        except:
            _logger.info('Error during decoding XML file')
            return self.env['account.invoice']

        invoices = self.env['account.invoice']

        # possible to have multiple invoices in the case of an invoice batch, the batch itself is repeated for every invoice of the batch
        for body_tree in tree.xpath('//FatturaElettronicaBody'):

            elements = tree.xpath('//DatiGeneraliDocumento/TipoDocumento')
            if elements and elements[0].text and elements[0].text == 'TD01':
                self_ctx = self.with_context(type='in_invoice')
            elif elements and elements[0].text and elements[0].text == 'TD04':
                self_ctx = self.with_context(type='in_refund')
            else:
                _logger.info(_('Document type not managed: %s.') % (elements[0].text))

            # type must be present in the context to get the right behavior of the _default_journal method (account.invoice).
            # journal_id must be present in the context to get the right behavior of the _default_account method (account.invoice.line).

            elements = tree.xpath('//CessionarioCommittente//IdCodice')
            company = elements and self.env['res.company'].search([('vat', 'ilike', elements[0].text)], limit=1)
            if not company:
                elements = tree.xpath('//CessionarioCommittente//CodiceFiscale')
                company = elements and self.env['res.company'].search([('l10n_it_codice_fiscale', 'ilike', elements[0].text)], limit=1)

            if company:
                self_ctx = self_ctx.with_context(company_id=company.id)
            else:
                company = self.env.user.company_id
                if elements:
                    _logger.info(_('Company not found with codice fiscale: %s. The company\'s user is set by default.') % elements[0].text)
                else:
                    _logger.info(_('Company not found. The company\'s user is set by default.'))

            if not self.env.user._is_superuser():
                if self.env.user.company_id != company:
                    raise UserError(_("You can only import invoice concern your current company: %s") % self.env.user.company_id.display_name)

            journal_id = self_ctx._default_journal().id
            self_ctx = self_ctx.with_context(journal_id=journal_id)

            # self could be a single record (editing) or be empty (new).
            with Form(self_ctx, view='account.invoice_supplier_form') as invoice_form:
                message_to_log = []

                invoice_form.company_id = company

                # Refund type.
                # TD01 == invoice
                # TD02 == advance/down payment on invoice
                # TD03 == advance/down payment on fee
                # TD04 == credit note
                # TD05 == debit note
                # TD06 == fee
                elements = tree.xpath('//DatiGeneraliDocumento/TipoDocumento')
                if elements and elements[0].text and elements[0].text == 'TD01':
                    invoice_form.type = 'in_invoice'
                elif elements and elements[0].text and elements[0].text == 'TD04':
                    invoice_form.type = 'in_refund'

                # Partner (first step to avoid warning 'Warning! You must first select a partner.'). <1.2>
                elements = tree.xpath('//CedentePrestatore//IdCodice')
                partner = elements and self.env['res.partner'].search(['&', ('vat', 'ilike', elements[0].text), '|', ('company_id', '=', company.id), ('company_id', '=', False)], limit=1)
                if not partner:
                    elements = tree.xpath('//CedentePrestatore//CodiceFiscale')
                    partner = elements and self.env['res.partner'].search(['&', ('l10n_it_codice_fiscale', '=', elements[0].text), '|', ('company_id', '=', company.id), ('company_id', '=', False)], limit=1)
                if not partner:
                    elements = tree.xpath('//DatiTrasmissione//Email')
                    partner = elements and self.env['res.partner'].search(['&', '|', ('email', '=', elements[0].text), ('l10n_it_pec_email', '=', elements[0].text), '|', ('company_id', '=', company.id), ('company_id', '=', False)], limit=1)
                if partner:
                    invoice_form.partner_id = partner
                else:
                    message_to_log.append("%s<br/>%s" % (
                        _("Vendor not found, useful informations from XML file:"),
                        self._compose_info_message(
                            tree, './/CedentePrestatore')))

                # Numbering attributed by the transmitter. <1.1.2>
                elements = tree.xpath('//ProgressivoInvio')
                if elements:
                    invoice_form.name = elements[0].text

                elements = body_tree.xpath('.//DatiGeneraliDocumento//Numero')
                if elements:
                    invoice_form.reference = elements[0].text

                # Currency. <2.1.1.2>
                elements = body_tree.xpath('.//DatiGeneraliDocumento/Divisa')
                if elements:
                    currency_str = elements[0].text
                    currency = self.env.ref('base.%s' % currency_str.upper(), raise_if_not_found=False)
                    if currency != self.env.user.company_id.currency_id and currency.active:
                        invoice_form.currency_id = currency

                # Date. <2.1.1.3>
                elements = body_tree.xpath('.//DatiGeneraliDocumento/Data')
                if elements:
                    date_str = elements[0].text
                    date_obj = datetime.strptime(date_str, DEFAULT_FACTUR_ITALIAN_DATE_FORMAT)
                    invoice_form.date_invoice = date_obj.strftime(DEFAULT_FACTUR_ITALIAN_DATE_FORMAT)

                #  Dati Bollo. <2.1.1.6>
                elements = body_tree.xpath('.//DatiGeneraliDocumento/DatiBollo/ImportoBollo')
                if elements:
                    invoice_form.l10n_it_stamp_duty = float(elements[0].text)

                # List of all amount discount (will be add after all article to avoid to have a negative sum)
                discount_list = []
                percentage_global_discount = 1.0

                # Global discount. <2.1.1.8>
                discount_elements = body_tree.xpath('.//DatiGeneraliDocumento/ScontoMaggiorazione')
                total_discount_amount = 0.0
                if discount_elements:
                    for discount_element in discount_elements:
                        discount_line = discount_element.xpath('.//Tipo')
                        discount_sign = -1
                        if discount_line and discount_line[0].text == 'SC':
                            discount_sign = 1
                        discount_percentage = discount_element.xpath('.//Percentuale')
                        if discount_percentage and discount_percentage[0].text:
                            percentage_global_discount *= 1 - float(discount_percentage[0].text)/100 * discount_sign

                        discount_amount_text = discount_element.xpath('.//Importo')
                        if discount_amount_text and discount_amount_text[0].text:
                            discount_amount = float(discount_amount_text[0].text) * discount_sign * -1
                            discount = {}
                            discount["seq"] = 0

                            if discount_amount < 0:
                                discount["name"] = _('GLOBAL DISCOUNT')
                            else:
                                discount["name"] = _('GLOBAL EXTRA CHARGE')
                            discount["amount"] = discount_amount
                            discount["tax"] = []
                            discount_list.append(discount)

                # Comment. <2.1.1.11>
                elements = body_tree.xpath('.//DatiGeneraliDocumento//Causale')
                for element in elements:
                    invoice_form.comment = '%s%s\n' % (invoice_form.comment or '', element.text)

                # Informations relative to the purchase order, the contract, the agreement,
                # the reception phase or invoices previously transmitted
                # <2.1.2> - <2.1.6>
                for document_type in ['DatiOrdineAcquisto', 'DatiContratto', 'DatiConvenzione', 'DatiRicezione', 'DatiFattureCollegate']:
                    elements = body_tree.xpath('.//DatiGenerali/' + document_type)
                    if elements:
                        for element in elements:
                            message_to_log.append("%s %s<br/>%s" % (document_type, _("from XML file:"),
                            self._compose_info_message(element, '.')))

                #  Dati DDT. <2.1.8>
                elements = body_tree.xpath('.//DatiGenerali/DatiDDT')
                if elements:
                    message_to_log.append("%s<br/>%s" % (
                        _("Transport informations from XML file:"),
                        self._compose_info_message(body_tree, './/DatiGenerali/DatiDDT')))

                # Due date. <2.4.2.5>
                elements = body_tree.xpath('.//DatiPagamento/DettaglioPagamento/DataScadenzaPagamento')
                if elements:
                    date_str = elements[0].text
                    date_obj = datetime.strptime(date_str, DEFAULT_FACTUR_ITALIAN_DATE_FORMAT)
                    invoice_form.date_due = fields.Date.to_string(date_obj)

                # Total amount. <2.4.2.6>
                elements = body_tree.xpath('.//ImportoPagamento')
                amount_total_import = 0
                for element in elements:
                    amount_total_import += float(element.text)
                if amount_total_import:
                    message_to_log.append(_("Total amount from the XML File: %s") % (
                        amount_total_import))

                # Bank account. <2.4.2.13>
                if invoice_form.type not in ('out_invoice', 'in_refund'):
                    elements = body_tree.xpath('.//DatiPagamento/DettaglioPagamento/IBAN')
                    if elements:
                        if invoice_form.partner_id and invoice_form.partner_id.commercial_partner_id:
                            bank = self.env['res.partner.bank'].search([
                                ('acc_number', '=', elements[0].text),
                                ('partner_id.id', '=', invoice_form.partner_id.commercial_partner_id.id)
                                ])
                        else:
                            bank = self.env['res.partner.bank'].search([('acc_number', '=', elements[0].text)])
                        if bank:
                            invoice_form.partner_bank_id = bank
                        else:
                            message_to_log.append("%s<br/>%s" % (
                                _("Bank account not found, useful informations from XML file:"),
                                self._compose_multi_info_message(
                                    body_tree, ['.//DatiPagamento//Beneficiario',
                                        './/DatiPagamento//IstitutoFinanziario',
                                        './/DatiPagamento//IBAN',
                                        './/DatiPagamento//ABI',
                                        './/DatiPagamento//CAB',
                                        './/DatiPagamento//BIC',
                                        './/DatiPagamento//ModalitaPagamento'])))
                    else:
                        elements = body_tree.xpath('.//DatiPagamento/DettaglioPagamento')
                        if elements:
                            message_to_log.append("%s<br/>%s" % (
                                _("Bank account not found, useful informations from XML file:"),
                                self._compose_info_message(body_tree, './/DatiPagamento')))

                # Invoice lines. <2.2.1>
                elements = body_tree.xpath('.//DettaglioLinee')
                if elements:
                    for element in elements:
                        with invoice_form.invoice_line_ids.new() as invoice_line_form:

                            # Sequence.
                            line_elements = element.xpath('.//NumeroLinea')
                            if line_elements:
                                invoice_line_form.sequence = int(line_elements[0].text) * 2

                            # Product.
                            line_elements = element.xpath('.//Descrizione')
                            if line_elements:
                                invoice_line_form.name = " ".join(line_elements[0].text.split())

                            elements_code = element.xpath('.//CodiceArticolo')
                            if elements_code:
                                for element_code in elements_code:
                                    type_code = element_code.xpath('.//CodiceTipo')[0]
                                    code = element_code.xpath('.//CodiceValore')[0]
                                    if type_code.text == 'EAN':
                                        product = self.env['product.product'].search([('barcode', '=', code.text)])
                                        if product:
                                            invoice_line_form.product_id = product
                                            break
                                    if partner:
                                        product_supplier = self.env['product.supplierinfo'].search([('name', '=', partner.id), ('product_code', '=', code.text)])
                                        if product_supplier and product_supplier.product_id:
                                            invoice_line_form.product_id = product_supplier.product_id
                                            break
                                if not invoice_line_form.product_id:
                                    for element_code in elements_code:
                                        code = element_code.xpath('.//CodiceValore')[0]
                                        product = self.env['product.product'].search([('default_code', '=', code.text)])
                                        if product:
                                            invoice_line_form.product_id = product
                                            break

                            # Price Unit.
                            line_elements = element.xpath('.//PrezzoUnitario')
                            if line_elements:
                                invoice_line_form.price_unit = float(line_elements[0].text)

                            # Quantity.
                            line_elements = element.xpath('.//Quantita')
                            if line_elements:
                                invoice_line_form.quantity = float(line_elements[0].text)
                            else:
                                invoice_line_form.quantity = 1

                            # Taxes
                            tax_element = element.xpath('.//AliquotaIVA')
                            natura_element = element.xpath('.//Natura')
                            invoice_line_form.invoice_line_tax_ids.clear()
                            if tax_element and tax_element[0].text:
                                percentage = float(tax_element[0].text)
                                if natura_element and natura_element[0].text:
                                    l10n_it_kind_exoneration = natura_element[0].text
                                    tax = self.env['account.tax'].search([
                                        ('company_id', '=', invoice_form.company_id.id),
                                        ('amount_type', '=', 'percent'),
                                        ('type_tax_use', '=', 'purchase'),
                                        ('amount', '=', percentage),
                                        ('l10n_it_kind_exoneration', '=', l10n_it_kind_exoneration),
                                    ], limit=1)
                                else:
                                    tax = self.env['account.tax'].search([
                                        ('company_id', '=', invoice_form.company_id.id),
                                        ('amount_type', '=', 'percent'),
                                        ('type_tax_use', '=', 'purchase'),
                                        ('amount', '=', percentage),
                                    ], limit=1)
                                    l10n_it_kind_exoneration = ''

                                if tax:
                                    invoice_line_form.invoice_line_tax_ids.add(tax)
                                else:
                                    if l10n_it_kind_exoneration:
                                        message_to_log.append(_("Tax not found with percentage: %s and exoneration %s for the article: %s") % (
                                            percentage,
                                            l10n_it_kind_exoneration,
                                            invoice_line_form.name))
                                    else:
                                        message_to_log.append(_("Tax not found with percentage: %s for the article: %s") % (
                                            percentage,
                                            invoice_line_form.name))

                            # Discount in cascade mode.
                            # if 3 discounts : -10% -50€ -20%
                            # the result must be : (((price -10%)-50€) -20%)
                            # Generic form : (((price -P1%)-A1€) -P2%)
                            # It will be split in two parts: fix amount and pourcent amount
                            # example: (((((price - A1€) -P2%) -A3€) -A4€) -P5€)
                            # pourcent: 1-(1-P2)*(1-P5)
                            # fix amount: A1*(1-P2)*(1-P5)+A3*(1-P5)+A4*(1-P5) (we must take account of all
                            # percentage present after the fix amount)
                            line_elements = element.xpath('.//ScontoMaggiorazione')
                            total_discount_amount = 0.0
                            total_discount_percentage = percentage_global_discount
                            if line_elements:
                                for line_element in line_elements:
                                    discount_line = line_element.xpath('.//Tipo')
                                    discount_sign = -1
                                    if discount_line and discount_line[0].text == 'SC':
                                        discount_sign = 1
                                    discount_percentage = line_element.xpath('.//Percentuale')
                                    if discount_percentage and discount_percentage[0].text:
                                        pourcentage_actual = 1 - float(discount_percentage[0].text)/100 * discount_sign
                                        total_discount_percentage *= pourcentage_actual
                                        total_discount_amount *= pourcentage_actual

                                    discount_amount = line_element.xpath('.//Importo')
                                    if discount_amount and discount_amount[0].text:
                                        total_discount_amount += float(discount_amount[0].text) * discount_sign * -1

                                # Save amount discount.
                                if total_discount_amount != 0:
                                    discount = {}
                                    discount["seq"] = invoice_line_form.sequence + 1

                                    if total_discount_amount < 0:
                                        discount["name"] = _('DISCOUNT: ') + invoice_line_form.name
                                    else:
                                        discount["name"] = _('EXTRA CHARGE: ') + invoice_line_form.name
                                    discount["amount"] = total_discount_amount
                                    discount["tax"] = []
                                    for tax in invoice_line_form.invoice_line_tax_ids:
                                        discount["tax"].append(tax)
                                    discount_list.append(discount)
                            invoice_line_form.discount = (1 - total_discount_percentage) * 100

                # Apply amount discount.
                for discount in discount_list:
                    with invoice_form.invoice_line_ids.new() as invoice_line_form_discount:
                        invoice_line_form_discount.invoice_line_tax_ids.clear()
                        invoice_line_form_discount.sequence = discount["seq"]
                        invoice_line_form_discount.name = discount["name"]
                        invoice_line_form_discount.price_unit = discount["amount"]

            new_invoice = invoice_form.save()
            new_invoice.l10n_it_send_state = "other"

            elements = body_tree.xpath('.//Allegati')
            if elements:
                for element in elements:
                    name_attachment = element.xpath('.//NomeAttachment')[0].text
                    attachment_64 = str.encode(element.xpath('.//Attachment')[0].text)
                    attachment_64 = self.env['ir.attachment'].create({
                        'name': name_attachment,
                        'datas': attachment_64,
                        'datas_fname': name_attachment,
                        'type': 'binary',
                    })

                    # default_res_id is had to context to avoid facturx to import his content
                    new_invoice.with_context(default_res_id=new_invoice.id).message_post(
                        body=(_("Attachment from XML")),
                        attachment_ids=[attachment_64.id]
                    )

            for message in message_to_log:
                new_invoice.message_post(body=message)

            if attachment:
                new_invoice.l10n_it_einvoice_name = attachment.name
                attachment.write({'res_model': 'account.invoice', 'res_id': new_invoice.id})
                new_invoice.message_post(attachment_ids=[attachment.id])
            invoices += new_invoice
        return invoices

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

class ImportInvoiceImportWizard(models.TransientModel):
    _name = 'account.invoice.import.wizard'
    _inherit = 'account.invoice.import.wizard'

    @api.multi
    def _create_invoice_from_file(self, attachment):
        if attachment.mimetype == 'application/xml' and re.search("([A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.(xml.p7m|xml))", attachment.name):
            if self.env['account.invoice'].search([('l10n_it_einvoice_name', '=', attachment.name)], limit=1):
                # invoice already exist
                raise UserError(_('E-invoice already exist: %s') % attachment.name)
            self = self.with_context(default_journal_id= self.journal_id.id)
            invoice = self.env['account.invoice']._import_xml_invoice(base64.decodestring(attachment.datas), attachment)
        else:
            invoice = super(ImportInvoiceImportWizard, self)._create_invoice_from_file(attachment)
        return invoice
