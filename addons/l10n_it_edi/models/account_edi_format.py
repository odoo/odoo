# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.tests.common import Form
from odoo.exceptions import UserError
from odoo.tools import float_repr

import re
from datetime import date, datetime
import logging
import base64


_logger = logging.getLogger(__name__)

DEFAULT_FACTUR_ITALIAN_DATE_FORMAT = '%Y-%m-%d'


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------------

    def _is_embedding_to_invoice_pdf_needed(self):
        # OVERRIDE
        self.ensure_one()
        return True if self.code == 'fattura_pa' else super()._is_embedding_to_invoice_pdf_needed()

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'fattura_pa':
            return super()._is_compatible_with_journal(journal)
        return journal.type == 'sale' and journal.country_code == 'IT'

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'fattura_pa':
            return super()._is_required_for_invoice(invoice)

        # Determine on which invoices the Mexican CFDI must be generated.
        return invoice.is_sale_document() and invoice.l10n_it_send_state not in ['sent', 'delivered', 'delivered_accepted'] and invoice.country_code == 'IT'

    def _post_invoice_edi(self, invoices, test_mode=False):
        # OVERRIDE
        self.ensure_one()
        edi_result = super()._post_invoice_edi(invoices, test_mode=test_mode)
        if self.code != 'fattura_pa':
            return edi_result

        invoice = invoices  # no batching ensure that we only have one invoice
        invoice.l10n_it_send_state = 'other'
        invoice._check_before_xml_exporting()
        res = invoice.invoice_generate_xml()
        if len(invoice.commercial_partner_id.l10n_it_pa_index or '') == 6:
            invoice.message_post(
                body=(_("Invoices for PA are not managed by Odoo, you can download the document and send it on your own."))
            )
        else:
            invoice.l10n_it_send_state = 'to_send'
        return {invoice: res}

    # -------------------------------------------------------------------------
    # Import
    # -------------------------------------------------------------------------

    def _check_filename_is_fattura_pa(self, filename):
        return re.search("([A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.(xml.p7m|xml))", filename)

    def _is_fattura_pa(self, filename, tree):
        return self.code == 'fattura_pa' and self._check_filename_is_fattura_pa(filename)

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self._is_fattura_pa(filename, tree):
            return self._import_fattura_pa(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self._is_fattura_pa(filename, tree):
            if len(tree.xpath('//FatturaElettronicaBody')) > 1:
                invoice.message_post(body='The attachment contains multiple invoices, this invoice was not updated from it.',
                                     message_type='comment',
                                     subtype_xmlid='mail.mt_note',
                                     author_id=self.env.ref('base.partner_root').id)
            else:
                return self._import_fattura_pa(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    def _import_fattura_pa(self, tree, invoice):
        """ Decodes a fattura_pa invoice into an invoice.

        :param tree:    the fattura_pa tree to decode.
        :param invoice: the invoice to update or an empty recordset.
        :returns:       the invoice where the fattura_pa data was imported.
        """
        invoices = self.env['account.move']
        first_run = True

        # possible to have multiple invoices in the case of an invoice batch, the batch itself is repeated for every invoice of the batch
        for body_tree in tree.xpath('//FatturaElettronicaBody'):
            if not first_run or not invoice:
                # make sure all the iterations create a new invoice record (except the first which could have already created one)
                invoice = self.env['account.move']
            first_run = False

            elements = tree.xpath('//DatiGeneraliDocumento/TipoDocumento')
            if elements and elements[0].text and elements[0].text == 'TD01':
                self_ctx = invoice.with_context(default_move_type='in_invoice')
            elif elements and elements[0].text and elements[0].text == 'TD04':
                self_ctx = invoice.with_context(default_move_type='in_refund')
            else:
                _logger.info('Document type not managed: %s.', elements[0].text)

            # type must be present in the context to get the right behavior of the _default_journal method (account.move).
            # journal_id must be present in the context to get the right behavior of the _default_account method (account.move.line).

            elements = tree.xpath('//CessionarioCommittente//IdCodice')
            company = elements and self.env['res.company'].search([('vat', 'ilike', elements[0].text)], limit=1)
            if not company:
                elements = tree.xpath('//CessionarioCommittente//CodiceFiscale')
                company = elements and self.env['res.company'].search([('l10n_it_codice_fiscale', 'ilike', elements[0].text)], limit=1)

            if company:
                self_ctx = self_ctx.with_context(company_id=company.id)
            else:
                company = self.env.company
                if elements:
                    _logger.info('No company found with codice fiscale: %s. The user\'s company is set by default.', elements[0].text)
                else:
                    _logger.info('Company not found. The user\'s company is set by default.')

            if not self.env.is_superuser():
                if self.env.company != company:
                    raise UserError(_("You can only import invoice concern your current company: %s", self.env.company.display_name))

            # Refund type.
            # TD01 == invoice
            # TD02 == advance/down payment on invoice
            # TD03 == advance/down payment on fee
            # TD04 == credit note
            # TD05 == debit note
            # TD06 == fee
            elements = tree.xpath('//DatiGeneraliDocumento/TipoDocumento')
            if elements and elements[0].text and elements[0].text == 'TD01':
                move_type = 'in_invoice'
            elif elements and elements[0].text and elements[0].text == 'TD04':
                move_type = 'in_refund'
            # move could be a single record (editing) or be empty (new).
            with Form(invoice.with_context(default_move_type=move_type,
                                           account_predictive_bills_disable_prediction=True)) as invoice_form:
                message_to_log = []

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
                        invoice._compose_info_message(
                            tree, './/CedentePrestatore')))

                # Numbering attributed by the transmitter. <1.1.2>
                elements = tree.xpath('//ProgressivoInvio')
                if elements:
                    invoice_form.payment_reference = elements[0].text

                elements = body_tree.xpath('.//DatiGeneraliDocumento//Numero')
                if elements:
                    invoice_form.ref = elements[0].text

                # Currency. <2.1.1.2>
                elements = body_tree.xpath('.//DatiGeneraliDocumento/Divisa')
                if elements:
                    currency_str = elements[0].text
                    currency = self.env.ref('base.%s' % currency_str.upper(), raise_if_not_found=False)
                    if currency != self.env.company.currency_id and currency.active:
                        invoice_form.currency_id = currency

                # Date. <2.1.1.3>
                elements = body_tree.xpath('.//DatiGeneraliDocumento/Data')
                if elements:
                    date_str = elements[0].text
                    date_obj = datetime.strptime(date_str, DEFAULT_FACTUR_ITALIAN_DATE_FORMAT)
                    invoice_form.invoice_date = date_obj.strftime(DEFAULT_FACTUR_ITALIAN_DATE_FORMAT)

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
                    invoice_form.narration = '%s%s\n' % (invoice_form.narration or '', element.text)

                # Informations relative to the purchase order, the contract, the agreement,
                # the reception phase or invoices previously transmitted
                # <2.1.2> - <2.1.6>
                for document_type in ['DatiOrdineAcquisto', 'DatiContratto', 'DatiConvenzione', 'DatiRicezione', 'DatiFattureCollegate']:
                    elements = body_tree.xpath('.//DatiGenerali/' + document_type)
                    if elements:
                        for element in elements:
                            message_to_log.append("%s %s<br/>%s" % (document_type, _("from XML file:"),
                            invoice._compose_info_message(element, '.')))

                #  Dati DDT. <2.1.8>
                elements = body_tree.xpath('.//DatiGenerali/DatiDDT')
                if elements:
                    message_to_log.append("%s<br/>%s" % (
                        _("Transport informations from XML file:"),
                        invoice._compose_info_message(body_tree, './/DatiGenerali/DatiDDT')))

                # Due date. <2.4.2.5>
                elements = body_tree.xpath('.//DatiPagamento/DettaglioPagamento/DataScadenzaPagamento')
                if elements:
                    date_str = elements[0].text
                    date_obj = datetime.strptime(date_str, DEFAULT_FACTUR_ITALIAN_DATE_FORMAT)
                    invoice_form.invoice_date_due = fields.Date.to_string(date_obj)

                # Total amount. <2.4.2.6>
                elements = body_tree.xpath('.//ImportoPagamento')
                amount_total_import = 0
                for element in elements:
                    amount_total_import += float(element.text)
                if amount_total_import:
                    message_to_log.append(_("Total amount from the XML File: %s") % (
                        amount_total_import))

                # Bank account. <2.4.2.13>
                if invoice_form.move_type not in ('out_invoice', 'in_refund'):
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
                                invoice._compose_multi_info_message(
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
                            invoice_line_form.tax_ids.clear()
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
                                    invoice_line_form.tax_ids.add(tax)
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
                                        discount["name"] = _('DISCOUNT: %s', invoice_line_form.name)
                                    else:
                                        discount["name"] = _('EXTRA CHARGE: %s', invoice_line_form.name)
                                    discount["amount"] = total_discount_amount
                                    discount["tax"] = []
                                    for tax in invoice_line_form.tax_ids:
                                        discount["tax"].append(tax)
                                    discount_list.append(discount)
                            invoice_line_form.discount = (1 - total_discount_percentage) * 100

                # Apply amount discount.
                for discount in discount_list:
                    with invoice_form.invoice_line_ids.new() as invoice_line_form_discount:
                        invoice_line_form_discount.tax_ids.clear()
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
                        'type': 'binary',
                    })

                    # default_res_id is had to context to avoid facturx to import his content
                    # no_new_invoice to prevent from looping on the message_post that would create a new invoice without it
                    new_invoice.with_context(no_new_invoice=True, default_res_id=new_invoice.id).message_post(
                        body=(_("Attachment from XML")),
                        attachment_ids=[attachment_64.id]
                    )

            for message in message_to_log:
                new_invoice.message_post(body=message)

            invoices += new_invoice
        return invoices
