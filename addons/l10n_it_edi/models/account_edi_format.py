# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.tests.common import Form
from odoo.exceptions import UserError
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature
from odoo.osv.expression import OR, AND

from lxml import etree
from datetime import datetime
import re
import logging
import json


_logger = logging.getLogger(__name__)

DEFAULT_FACTUR_ITALIAN_DATE_FORMAT = '%Y-%m-%d'


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_it_edi_generate_electronic_invoice_filename(self, invoice):
        '''Returns a name conform to the Fattura pa Specifications:
           See ES documentation 2.2
        '''
        a = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        # Each company should have its own filename sequence. If it does not exist, create it
        n = self.env['ir.sequence'].with_company(invoice.company_id).next_by_code('l10n_it_edi.fattura_filename')
        if not n:
            # The offset is used to avoid conflicts with existing filenames
            offset = 62 ** 4
            sequence = self.env['ir.sequence'].sudo().create({
                'name': 'FatturaPA Filename Sequence',
                'code': 'l10n_it_edi.fattura_filename',
                'company_id': invoice.company_id.id,
                'number_next': offset,
            })
            n = sequence._next()
        # The n is returned as a string, but we require an int
        n = int(''.join(filter(lambda c: c.isdecimal(), n)))

        progressive_number = ""
        while n:
            (n, m) = divmod(n, len(a))
            progressive_number = a[m] + progressive_number

        return '%(country_code)s%(codice)s_%(progressive_number)s.xml' % {
            'country_code': invoice.company_id.country_id.code,
            'codice': self.env['res.partner']._l10n_it_normalize_codice_fiscale(invoice.company_id.l10n_it_codice_fiscale),
            'progressive_number': progressive_number.zfill(5),
        }

    def _l10n_it_edi_check_invoice_configuration(self, invoice):
        errors = self._l10n_it_edi_check_ordinary_invoice_configuration(invoice)

        if not errors:
            errors = self._l10n_it_edi_check_simplified_invoice_configuration(invoice)

        return errors

    def _l10n_it_edi_is_self_invoice(self, invoice):
        """
            Italian EDI requires Vendor bills coming from EU countries to be sent as self-invoices.
            We recognize these cases based on the taxes that target the VJ tax grids, which imply
            the use of VAT External Reverse Charge.
        """
        report_lines_xmlids = invoice.line_ids.tax_tag_ids.tax_report_line_ids.mapped(lambda x: x.get_external_id().get(x.id, ''))
        return (invoice.is_purchase_document()
                and any([x.startswith("l10n_it.tax_report_line_vj") for x in report_lines_xmlids]))

    def _l10n_it_edi_check_ordinary_invoice_configuration(self, invoice):
        errors = []
        seller = invoice.company_id
        buyer = invoice.commercial_partner_id
        is_self_invoice = self._l10n_it_edi_is_self_invoice(invoice)
        if is_self_invoice:
            seller, buyer = buyer, seller

        # <1.1.1.1>
        if not seller.country_id:
            errors.append(_("%s must have a country", seller.display_name))

        # <1.1.1.2>
        if not seller.vat:
            errors.append(_("%s must have a VAT number", seller.display_name))
        elif len(seller.vat) > 30:
            errors.append(_("The maximum length for VAT number is 30. %s have a VAT number too long: %s.", seller.display_name, seller.vat))

        # <1.2.1.2>
        if not is_self_invoice and not seller.l10n_it_codice_fiscale:
            errors.append(_("%s must have a codice fiscale number", seller.display_name))

        # <1.2.1.8>
        if not is_self_invoice and not seller.l10n_it_tax_system:
            errors.append(_("The seller's company must have a tax system."))

        # <1.2.2>
        if not seller.street and not seller.street2:
            errors.append(_("%s must have a street.", seller.display_name))
        if not seller.zip:
            errors.append(_("%s must have a post code.", seller.display_name))
        elif len(seller.zip) != 5 and seller.country_id.code == 'IT':
            errors.append(_("%s must have a post code of length 5.", seller.display_name))
        if not seller.city:
            errors.append(_("%s must have a city.", seller.display_name))
        if not seller.country_id:
            errors.append(_("%s must have a country.", seller.display_name))

        if not is_self_invoice and seller.l10n_it_has_tax_representative and not seller.l10n_it_tax_representative_partner_id.vat:
            errors.append(_("Tax representative partner %s of %s must have a tax number.", seller.l10n_it_tax_representative_partner_id.display_name, seller.display_name))

        # <1.4.1>
        if not buyer.vat and not buyer.l10n_it_codice_fiscale and buyer.country_id.code == 'IT':
            errors.append(_("The buyer, %s, or his company must have a VAT number and/or a tax code (Codice Fiscale).", buyer.display_name))

        if is_self_invoice and self._l10n_it_edi_services_or_goods(invoice) == 'both':
            errors.append(_("Cannot apply Reverse Charge to a bill which contains both services and goods."))

        if is_self_invoice and not buyer.partner_id.l10n_it_pa_index:
            errors.append(_("Vendor bills sent as self-invoices to the SdI require a valid PA Index (Codice Destinatario) on the company's contact."))

        # <2.2.1>
        for invoice_line in invoice.invoice_line_ids:
            if not invoice_line.display_type and len(invoice_line.tax_ids) != 1:
                errors.append(_("In line %s, you must select one and only one tax by line.", invoice_line.name))

        for tax_line in invoice.line_ids.filtered(lambda line: line.tax_line_id):
            if not tax_line.tax_line_id.l10n_it_kind_exoneration and tax_line.tax_line_id.amount == 0:
                errors.append(_("%s has an amount of 0.0, you must indicate the kind of exoneration.", tax_line.name))

        return errors

    def _l10n_it_edi_is_simplified(self, invoice):
        """
            Simplified Invoices are a way for the invoice issuer to create an invoice with limited data.
            Example: a consultant goes to the restaurant and wants the invoice instead of the receipt,
            to be able to deduct the expense from his Taxes. The Italian State allows the restaurant
            to issue a Simplified Invoice with the VAT number only, to speed up times, instead of
            requiring the address and other informations about the buyer.
            Only invoices under the threshold of 400 Euroes are allowed, to avoid this tool
            be abused for bigger transactions, that would enable less transparency to tax institutions.
        """
        buyer = invoice.commercial_partner_id
        return all([
            self.env.ref('l10n_it_edi.account_invoice_it_simplified_FatturaPA_export', raise_if_not_found=False),
            not self._l10n_it_edi_is_self_invoice(invoice),
            self._l10n_it_edi_check_buyer_invoice_configuration(invoice),
            not buyer.country_id or buyer.country_id.code == 'IT',
            buyer.l10n_it_codice_fiscale or (buyer.vat and (buyer.vat[:2].upper() == 'IT' or buyer.vat[:2].isdecimal())),
            invoice.amount_total <= 400,
        ])

    def _l10n_it_edi_check_simplified_invoice_configuration(self, invoice):
        return [] if self._l10n_it_edi_is_simplified(invoice) else self._l10n_it_edi_check_buyer_invoice_configuration(invoice)

    def _l10n_it_edi_partner_in_eu(self, partner):
        europe = self.env.ref('base.europe', raise_if_not_found=False)
        country = partner.country_id
        return not europe or not country or country in europe.country_ids

    def _l10n_it_edi_services_or_goods(self, invoice):
        """
            Services and goods have different tax grids when VAT is Reverse Charged, and they can't
            be mixed in the same invoice, because the TipoDocumento depends on which which kind
            of product is bought and it's unambiguous.
        """
        scopes = []
        for line in invoice.invoice_line_ids.filtered(lambda l: not l.display_type):
            tax_ids_with_tax_scope = line.tax_ids.filtered(lambda x: x.tax_scope)
            if tax_ids_with_tax_scope:
                scopes += tax_ids_with_tax_scope.mapped('tax_scope')
            else:
                scopes.append(line.product_id and line.product_id.type or 'consu')

        if set(scopes) == set(['consu', 'service']):
            return "both"
        return scopes and scopes.pop()

    def _l10n_it_edi_check_buyer_invoice_configuration(self, invoice):
        errors = []
        buyer = invoice.commercial_partner_id

        # <1.4.2>
        if not buyer.street and not buyer.street2:
            errors.append(_("%s must have a street.", buyer.display_name))
        if not buyer.country_id:
            errors.append(_("%s must have a country.", buyer.display_name))
        if not buyer.zip:
            errors.append(_("%s must have a post code.", buyer.display_name))
        elif len(buyer.zip) != 5 and buyer.country_id.code == 'IT':
            errors.append(_("%s must have a post code of length 5.", buyer.display_name))
        if not buyer.city:
            errors.append(_("%s must have a city.", buyer.display_name))

        if any(line.quantity < 0 for line in invoice.invoice_line_ids):
            errors.append(_("All quantities should be positive."))

        for tax_line in invoice.line_ids.filtered(lambda line: line.tax_line_id):
            if not tax_line.tax_line_id.l10n_it_kind_exoneration and tax_line.tax_line_id.amount == 0:
                errors.append(_("%s has an amount of 0.0, you must indicate the kind of exoneration.", tax_line.name))

        return errors

    def _l10n_it_goods_in_italy(self, invoice):
        """
            There is a specific TipoDocumento (Document Type TD19) and tax grid (VJ3) for goods
            that are phisically in Italy but are in a VAT deposit, meaning that the goods
            have not passed customs.
        """
        report_lines_xmlids = invoice.line_ids.tax_tag_ids.tax_report_line_ids.mapped(lambda x: x.get_external_id().get(x.id, ''))
        return any([x == "l10n_it.tax_report_line_vj3" for x in report_lines_xmlids])

    def _l10n_it_document_type_mapping(self):
        return {
            'TD01': dict(move_types=['out_invoice'], import_type='in_invoice'),
            'TD02': dict(move_types=['out_invoice'], import_type='in_invoice', downpayment=True),
            'TD04': dict(move_types=['out_refund'], import_type='in_refund'),
            'TD07': dict(move_types=['out_invoice'], import_type='in_invoice', simplified=True),
            'TD08': dict(move_types=['out_refund'], import_type='in_refund', simplified=True),
            'TD09': dict(move_types=['out_invoice'], import_type='in_invoice', simplified=True),
            'TD17': dict(move_types=['in_invoice', 'in_refund'], import_type='out_invoice', self_invoice=True, services_or_goods="service"),
            'TD18': dict(move_types=['in_invoice', 'in_refund'], import_type='out_invoice', self_invoice=True, services_or_goods="consu", partner_in_eu=True),
            'TD19': dict(move_types=['in_invoice', 'in_refund'], import_type='out_invoice', self_invoice=True, services_or_goods="consu", goods_in_italy=True),
        }

    def _l10n_it_get_document_type(self, invoice):
        is_simplified = self._l10n_it_edi_is_simplified(invoice)
        is_self_invoice = self._l10n_it_edi_is_self_invoice(invoice)
        services_or_goods = self._l10n_it_edi_services_or_goods(invoice)
        goods_in_italy = services_or_goods == 'consu' and self._l10n_it_goods_in_italy(invoice)
        partner_in_eu = self._l10n_it_edi_partner_in_eu(invoice.commercial_partner_id)
        for code, infos in self._l10n_it_document_type_mapping().items():
            info_services_or_goods = infos.get('services_or_goods', "both")
            info_partner_in_eu = infos.get('partner_in_eu', False)
            if all([
                invoice.move_type in infos.get('move_types', False),
                invoice._is_downpayment() == infos.get('downpayment', False),
                is_self_invoice == infos.get('self_invoice', False),
                is_simplified == infos.get('simplified', False),
                info_services_or_goods in ("both", services_or_goods),
                info_partner_in_eu in (False, partner_in_eu),
                goods_in_italy == infos.get('goods_in_italy', False),
            ]):
                return code
        return None

    def _l10n_it_is_simplified_document_type(self, document_type):
        return self._l10n_it_document_type_mapping().get(document_type, {}).get('simplified', False)

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
        return journal.type in ('sale', 'purchase') and journal.country_code == 'IT'

    def _l10n_it_edi_is_required_for_invoice(self, invoice):
        """ Is the edi required for this invoice based on the method (here: PEC mail)
            Deprecated: in future release PEC mail will be removed.
            TO OVERRIDE
        """
        return ((invoice.is_sale_document() or self._l10n_it_get_document_type(invoice))
                and invoice.country_code == 'IT'
                and invoice.l10n_it_send_state not in ('sent', 'delivered', 'delivered_accepted'))

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'fattura_pa':
            return super()._is_required_for_invoice(invoice)

        return self._l10n_it_edi_is_required_for_invoice(invoice)

    def _post_fattura_pa(self, invoices):
        # TO OVERRIDE
        invoice = invoices  # no batching ensure that we only have one invoice
        invoice.l10n_it_send_state = 'other'
        invoice._check_before_xml_exporting()
        if invoice.l10n_it_einvoice_id and invoice.l10n_it_send_state not in ['invalid', 'to_send']:
            return {'error': _("You can't regenerate an E-Invoice when the first one is sent and there are no errors")}
        if invoice.l10n_it_einvoice_id:
            invoice.l10n_it_einvoice_id.unlink()
        res = invoice.invoice_generate_xml()
        if invoice._is_commercial_partner_pa():
            invoice.message_post(
                body=(_("Invoices for PA are not managed by Odoo, you can download the document and send it on your own."))
            )
        else:
            invoice.l10n_it_send_state = 'to_send'
        if 'attachment' in res:
            res['success'] = True
        return {invoice: res}

    def _post_invoice_edi(self, invoices, test_mode=False):
        # OVERRIDE
        self.ensure_one()
        edi_result = super()._post_invoice_edi(invoices)
        if self.code != 'fattura_pa':
            return edi_result

        return self._post_fattura_pa(invoices)

    # -------------------------------------------------------------------------
    # Import
    # -------------------------------------------------------------------------

    def _check_filename_is_fattura_pa(self, filename):
        return re.search("([A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.(xml.p7m|xml))", filename)

    def _is_fattura_pa(self, filename, tree):
        return self.code == 'fattura_pa' and self._check_filename_is_fattura_pa(filename)

    def _create_invoice_from_xml_tree(self, filename, tree, journal=None):
        self.ensure_one()
        if self._is_fattura_pa(filename, tree):
            return self._import_fattura_pa(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree, journal=journal)

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

    def _decode_p7m_to_xml(self, filename, content):
        decoded_content = remove_signature(content)
        if not decoded_content:
            return None

        try:
            # Some malformed XML are accepted by FatturaPA, this expends compatibility
            parser = etree.XMLParser(recover=True)
            xml_tree = etree.fromstring(decoded_content, parser)
        except Exception as e:
            _logger.exception("Error when converting the xml content to etree: %s", e)
            return None
        if xml_tree is None or len(xml_tree) == 0:
            return None

        return xml_tree

    def _create_invoice_from_binary(self, filename, content, extension):
        self.ensure_one()
        if extension.lower() == '.xml.p7m':
            decoded_content = self._decode_p7m_to_xml(filename, content)
            if decoded_content is not None and self._is_fattura_pa(filename, decoded_content):
                return self._import_fattura_pa(decoded_content, self.env['account.move'])
        return super()._create_invoice_from_binary(filename, content, extension)

    def _update_invoice_from_binary(self, filename, content, extension, invoice):
        self.ensure_one()
        if extension.lower() == '.xml.p7m':
            decoded_content = self._decode_p7m_to_xml(filename, content)
            if decoded_content is not None and self._is_fattura_pa(filename, decoded_content):
                return self._import_fattura_pa(decoded_content, invoice)
        return super()._update_invoice_from_binary(filename, content, extension, invoice)

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

            # Type must be present in the context to get the right behavior of the _default_journal method (account.move).
            # journal_id must be present in the context to get the right behavior of the _default_account method (account.move.line).
            elements = tree.xpath('//CessionarioCommittente//IdCodice')
            company = elements and self.env['res.company'].search([('vat', 'ilike', elements[0].text)], limit=1)
            if not company:
                elements = tree.xpath('//CessionarioCommittente//CodiceFiscale')
                company = elements and self.env['res.company'].search([('l10n_it_codice_fiscale', 'ilike', elements[0].text)], limit=1)
                if not company:
                    # Only invoices with a correct VAT or Codice Fiscale can be imported
                    _logger.warning('No company found with VAT or Codice Fiscale like %r.', elements[0].text)
                    continue

            # Refund type.
            # TD01 == invoice
            # TD02 == advance/down payment on invoice
            # TD03 == advance/down payment on fee
            # TD04 == credit note
            # TD05 == debit note
            # TD06 == fee
            # TD07 == simplified invoice
            # TD08 == simplified credit note
            # TD09 == simplified debit note
            # For unsupported document types, just assume in_invoice, and log that the type is unsupported
            elements = tree.xpath('//DatiGeneraliDocumento/TipoDocumento')
            document_type = elements[0].text if elements else ''
            move_type = self._l10n_it_document_type_mapping().get(document_type, {}).get('import_type', False)
            if not move_type:
                move_type = "in_invoice"
                _logger.info('Document type not managed: %s. Invoice type is set by default.', document_type)

            simplified = self._l10n_it_is_simplified_document_type(document_type)

            # Setup the context for the Invoice Form
            invoice_ctx = invoice.with_company(company) \
                                 .with_context(default_move_type=move_type)

            # move could be a single record (editing) or be empty (new).
            with Form(invoice_ctx) as invoice_form:
                message_to_log = []

                # Partner (first step to avoid warning 'Warning! You must first select a partner.'). <1.2>
                elements = tree.xpath('//CedentePrestatore//IdCodice')
                partner = elements and self.env['res.partner'].search(['&', ('vat', 'ilike', elements[0].text), '|', ('company_id', '=', company.id), ('company_id', '=', False)], limit=1)
                if not partner:
                    elements = tree.xpath('//CedentePrestatore//CodiceFiscale')
                    if elements:
                        codice = elements[0].text
                        domains = [[('l10n_it_codice_fiscale', '=', codice)]]
                        if re.match(r'^[0-9]{11}$', codice):
                            domains.append([('l10n_it_codice_fiscale', '=', 'IT' + codice)])
                        elif re.match(r'^IT[0-9]{11}$', codice):
                            domains.append([('l10n_it_codice_fiscale', '=', self.env['res.partner']._l10n_it_normalize_codice_fiscale(codice))])
                        partner = elements and self.env['res.partner'].search(
                            AND([OR(domains), OR([[('company_id', '=', company.id)], [('company_id', '=', False)]])]), limit=1)
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
                    invoice_form.invoice_date = date_obj

                #  Dati Bollo. <2.1.1.6>
                elements = body_tree.xpath('.//DatiGeneraliDocumento/DatiBollo/ImportoBollo')
                if elements:
                    invoice_form.l10n_it_stamp_duty = float(elements[0].text)


                # Comment. <2.1.1.11>
                elements = body_tree.xpath('.//DatiGeneraliDocumento//Causale')
                for element in elements:
                    invoice_form.narration = '%s%s<br/>' % (invoice_form.narration or '', element.text)

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
                                ('partner_id', '=', invoice_form.partner_id.commercial_partner_id.id),
                                ('company_id', 'in', [invoice_form.company_id.id, False])
                            ], order='company_id', limit=1)
                        else:
                            bank = self.env['res.partner.bank'].search([
                                ('acc_number', '=', elements[0].text), ('company_id', 'in', [invoice_form.company_id.id, False])
                            ], order='company_id', limit=1)
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
                            invoice._compose_info_message(body_tree, './/DatiPagamento')))

                # Invoice lines. <2.2.1>
                if not simplified:
                    elements = body_tree.xpath('.//DettaglioLinee')
                else:
                    elements = body_tree.xpath('.//DatiBeniServizi')

                if elements:
                    for element in elements:
                        with invoice_form.invoice_line_ids.new() as invoice_line_form:

                            # Sequence.
                            line_elements = element.xpath('.//NumeroLinea')
                            if line_elements:
                                invoice_line_form.sequence = int(line_elements[0].text)

                            # Product.
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
                                        product_supplier = self.env['product.supplierinfo'].search([('name', '=', partner.id), ('product_code', '=', code.text)], limit=2)
                                        if product_supplier and len(product_supplier) == 1 and product_supplier.product_id:
                                            invoice_line_form.product_id = product_supplier.product_id
                                            break
                                if not invoice_line_form.product_id:
                                    for element_code in elements_code:
                                        code = element_code.xpath('.//CodiceValore')[0]
                                        product = self.env['product.product'].search([('default_code', '=', code.text)], limit=2)
                                        if product and len(product) == 1:
                                            invoice_line_form.product_id = product
                                            break

                            # Label.
                            line_elements = element.xpath('.//Descrizione')
                            if line_elements:
                                invoice_line_form.name = " ".join(line_elements[0].text.split())

                            # Quantity.
                            line_elements = element.xpath('.//Quantita')
                            if line_elements:
                                invoice_line_form.quantity = float(line_elements[0].text)
                            else:
                                invoice_line_form.quantity = 1

                            # Taxes
                            percentage = None
                            price_subtotal = 0
                            if not simplified:
                                tax_element = element.xpath('.//AliquotaIVA')
                                if tax_element and tax_element[0].text:
                                    percentage = float(tax_element[0].text)
                            else:
                                amount_element = element.xpath('.//Importo')
                                if amount_element and amount_element[0].text:
                                    amount = float(amount_element[0].text)
                                    tax_element = element.xpath('.//Aliquota')
                                    if tax_element and tax_element[0].text:
                                        percentage = float(tax_element[0].text)
                                        price_subtotal = amount / (1 + percentage / 100)
                                    else:
                                        tax_element = element.xpath('.//Imposta')
                                        if tax_element and tax_element[0].text:
                                            tax_amount = float(tax_element[0].text)
                                            price_subtotal = amount - tax_amount
                                            percentage = round(tax_amount / price_subtotal * 100)

                            natura_element = element.xpath('.//Natura')
                            invoice_line_form.tax_ids.clear()
                            if percentage is not None:
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

                            # Price Unit.
                            if not simplified:
                                line_elements = element.xpath('.//PrezzoUnitario')
                                if line_elements:
                                    invoice_line_form.price_unit = float(line_elements[0].text)
                            else:
                                invoice_line_form.price_unit = price_subtotal

                            # Discounts
                            discount_elements = element.xpath('.//ScontoMaggiorazione')
                            if discount_elements:
                                discount_element = discount_elements[0]
                                discount_percentage = discount_element.xpath('.//Percentuale')
                                # Special case of only 1 percentage discount
                                if discount_percentage and len(discount_elements) == 1:
                                    discount_type = discount_element.xpath('.//Tipo')
                                    discount_sign = 1
                                    if discount_type and discount_type[0].text == 'MG':
                                        discount_sign = -1
                                    invoice_line_form.discount = discount_sign * float(discount_percentage[0].text)
                                # Discounts in cascade summarized in 1 percentage
                                else:
                                    total = float(element.xpath('.//PrezzoTotale')[0].text)
                                    discount = 100 - (100 * total) / (invoice_line_form.quantity * invoice_line_form.price_unit)
                                    invoice_line_form.discount = discount


                # Global discount summarized in 1 amount
                discount_elements = body_tree.xpath('.//DatiGeneraliDocumento/ScontoMaggiorazione')
                if discount_elements:
                    taxable_amount = float(json.loads(invoice_form.tax_totals_json)['amount_untaxed'])
                    discounted_amount = taxable_amount
                    for discount_element in discount_elements:
                        discount_type = discount_element.xpath('.//Tipo')
                        discount_sign = 1
                        if discount_type and discount_type[0].text == 'MG':
                            discount_sign = -1
                        discount_amount = discount_element.xpath('.//Importo')
                        if discount_amount:
                            discounted_amount -= discount_sign * float(discount_amount[0].text)
                            continue
                        discount_percentage = discount_element.xpath('.//Percentuale')
                        if discount_percentage:
                            discounted_amount *= 1 - discount_sign * float(discount_percentage[0].text) / 100

                    general_discount = discounted_amount - taxable_amount
                    sequence = len(elements) + 1

                    with invoice_form.invoice_line_ids.new() as invoice_line_global_discount:
                        invoice_line_global_discount.tax_ids.clear()
                        invoice_line_global_discount.sequence = sequence
                        invoice_line_global_discount.name = 'SCONTO' if general_discount < 0 else 'MAGGIORAZIONE'
                        invoice_line_global_discount.price_unit = general_discount

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
                        'res_model': 'account.move',
                        'res_id': new_invoice.id,
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
