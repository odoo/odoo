# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _, _lt
from odoo.exceptions import UserError
from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.l10n_it_edi.tools.remove_signature import remove_signature
from odoo.osv.expression import OR, AND

from lxml import etree
from datetime import datetime
import re
import logging
import base64


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
        if not invoice.is_purchase_document():
            return False

        invoice_lines_tags = invoice.line_ids.tax_tag_ids
        it_tax_report_vj_lines = self.env['account.report.line'].search([
            ('report_id.country_id.code', '=', 'IT'),
            ('code', 'like', 'VJ%'),
        ])
        vj_lines_tags = it_tax_report_vj_lines.expression_ids._get_matching_tags()
        return bool(invoice_lines_tags & vj_lines_tags)

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
            if invoice_line.display_type not in ('line_note', 'line_section') and len(invoice_line.tax_ids) != 1:
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
        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_note', 'line_section')):
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
        invoice_lines_tags = invoice.line_ids.tax_tag_ids
        it_tax_report_vj3_lines = self.env['account.report.line'].search([
            ('report_id.country_id.code', '=', 'IT'),
            ('code', '=', 'VJ3'),
        ])
        vj3_lines_tags = it_tax_report_vj3_lines.expression_ids._get_matching_tags()
        return bool(invoice_lines_tags & vj3_lines_tags)

    def _l10n_it_document_type_mapping(self):
        return {
            'TD01': dict(move_types=['out_invoice'], import_type='in_invoice'),
            'TD02': dict(move_types=['out_invoice'], import_type='in_invoice', downpayment=True),
            'TD04': dict(move_types=['out_refund'], import_type='in_refund'),
            'TD07': dict(move_types=['out_invoice'], import_type='in_invoice', simplified=True),
            'TD08': dict(move_types=['out_refund'], import_type='in_refund', simplified=True),
            'TD09': dict(move_types=['out_invoice'], import_type='in_invoice', simplified=True),
            'TD17': dict(move_types=['in_invoice', 'in_refund'], import_type='in_invoice', self_invoice=True, services_or_goods="service"),
            'TD18': dict(move_types=['in_invoice', 'in_refund'], import_type='in_invoice', self_invoice=True, services_or_goods="consu", partner_in_eu=True),
            'TD19': dict(move_types=['in_invoice', 'in_refund'], import_type='in_invoice', self_invoice=True, services_or_goods="consu", goods_in_italy=True),
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
    # Import
    # -------------------------------------------------------------------------

    def _cron_receive_fattura_pa(self):
        ''' Check the proxy for incoming invoices.
        '''
        proxy_users = self.env['account_edi_proxy_client.user'].search([('edi_format_id', '=', self.env.ref('l10n_it_edi.edi_fatturaPA').id)])

        if proxy_users._get_demo_state() == 'demo':
            return

        for proxy_user in proxy_users:
            company = proxy_user.company_id
            try:
                res = proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/in/RicezioneInvoice',
                                               params={'recipient_codice_fiscale': company.l10n_it_codice_fiscale})
            except AccountEdiProxyError as e:
                _logger.error('Error while receiving file from SdiCoop: %s', e)

            proxy_acks = []
            for id_transaction, fattura in res.items():
                if self.env['ir.attachment'].search([('name', '=', fattura['filename']), ('res_model', '=', 'account.move')], limit=1):
                    # name should be unique, the invoice already exists
                    _logger.info('E-invoice already exists: %s', fattura['filename'])
                    proxy_acks.append(id_transaction)
                    continue

                file = proxy_user._decrypt_data(fattura['file'], fattura['key'])

                try:
                    tree = etree.fromstring(file)
                except Exception:
                    # should not happen as the file has been checked by SdiCoop
                    _logger.info('Received file badly formatted, skipping: \n %s', file)
                    continue
                invoice = self.env['account.move'].with_company(company).create({'move_type': 'in_invoice'})
                attachment = self.env['ir.attachment'].create({
                    'name': fattura['filename'],
                    'raw': file,
                    'type': 'binary',
                    'res_model': 'account.move',
                    'res_id': invoice.id
                })
                if not self.env.context.get('test_skip_commit'):
                    self.env.cr.commit() # In case something fails after, we still have the attachment
                # So that we don't delete the attachment when deleting the invoice
                attachment.res_id = False
                attachment.res_model = False
                invoice.unlink()
                invoice = self.env.ref('l10n_it_edi.edi_fatturaPA')._create_invoice_from_xml_tree(fattura['filename'], tree)
                attachment.write({'res_model': 'account.move',
                                  'res_id': invoice.id})
                proxy_acks.append(id_transaction)
                if not self.env.context.get('test_skip_commit'):
                    self.env.cr.commit()


            if proxy_acks:
                try:
                    proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/ack',
                                            params={'transaction_ids': proxy_acks})
                except AccountEdiProxyError as e:
                    _logger.error('Error while receiving file from SdiCoop: %s', e)

    def _check_filename_is_fattura_pa(self, filename):
        return re.search("[A-Z]{2}[A-Za-z0-9]{2,28}_[A-Za-z0-9]{0,5}.((?i:xml.p7m|xml))", filename)

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

    def _l10n_it_get_partner_invoice(self, tree, company):
        # Partner (first step to avoid warning 'Warning! You must first select a partner.'). <1.2>
        elements = tree.xpath('//CedentePrestatore//IdCodice')
        partner = elements and self.env['res.partner'].search(
            ['&', ('vat', 'ilike', elements[0].text), '|', ('company_id', '=', company.id), ('company_id', '=', False)],
            limit=1)
        if not partner:
            elements = tree.xpath('//CedentePrestatore//CodiceFiscale')
            if elements:
                codice = elements[0].text
                domains = [[('l10n_it_codice_fiscale', '=', codice)]]
                if re.match(r'^[0-9]{11}$', codice):
                    domains.append([('l10n_it_codice_fiscale', '=', 'IT' + codice)])
                elif re.match(r'^IT[0-9]{11}$', codice):
                    domains.append([('l10n_it_codice_fiscale', '=',
                                     self.env['res.partner']._l10n_it_normalize_codice_fiscale(codice))])
                partner = elements and self.env['res.partner'].search(
                    AND([OR(domains), OR([[('company_id', '=', company.id)], [('company_id', '=', False)]])]), limit=1)
        if not partner:
            elements = tree.xpath('//DatiTrasmissione//Email')
            partner = elements and self.env['res.partner'].search(
                ['&', '|', ('email', '=', elements[0].text), ('l10n_it_pec_email', '=', elements[0].text), '|',
                 ('company_id', '=', company.id), ('company_id', '=', False)], limit=1)

        return partner

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
            with invoice_ctx._get_edi_creation() as invoice_form:
                message_to_log = []

                partner = self._l10n_it_get_partner_invoice(tree, company)

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
                        invoice_line_form = invoice_form.invoice_line_ids.create({'move_id': invoice_form.id})
                        if invoice_line_form:

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
                                        product_supplier = self.env['product.supplierinfo'].search([('partner_id', '=', partner.id), ('product_code', '=', code.text)], limit=2)
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
                            invoice_line_form.tax_ids = []
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
                                    invoice_line_form.tax_ids += tax
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
                    taxable_amount = float(invoice_form.tax_totals['amount_untaxed'])
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

            new_invoice = invoice_form

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

    # -------------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------------

    def _prepare_invoice_report(self, pdf_writer, edi_document):
        self.ensure_one()
        if self.code != 'fattura_pa':
            return super()._prepare_invoice_report(pdf_writer, edi_document)
        if edi_document.attachment_id:
            pdf_writer.embed_odoo_attachment(edi_document.attachment_id)

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'fattura_pa':
            return super()._is_compatible_with_journal(journal)
        return journal.type in ('sale', 'purchase') and journal.country_code == 'IT'

    def _get_move_applicability(self, move):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'fattura_pa':
            return super()._get_move_applicability(move)

        is_it_purchase_document = self._l10n_it_edi_is_self_invoice(move) and move.is_purchase_document()
        if move.country_code == 'IT' and (move.is_sale_document() or is_it_purchase_document):
            return {
                'post': self._post_fattura_pa,
                'post_batching': lambda move: (move.move_type, bool(move.l10n_it_edi_transaction)),
            }

    def _l10n_it_edi_export_invoice_as_xml(self, invoice):
        ''' Create the xml file content.
        :return: The XML content as str.
        '''
        template_values = invoice._prepare_fatturapa_export_values()
        if not self._l10n_it_is_simplified_document_type(template_values['document_type']):
            content = self.env['ir.qweb']._render('l10n_it_edi.account_invoice_it_FatturaPA_export', template_values)
        else:
            content = self.env['ir.qweb']._render('l10n_it_edi.account_invoice_it_simplified_FatturaPA_export', template_values)
            invoice.message_post(body=_(
                "A simplified invoice was created instead of an ordinary one. This is because the invoice \
                is a domestic invoice with a total amount of less than or equal to 400€ and the customer's address is incomplete."
            ))
        return content

    def _check_move_configuration(self, move):
        # OVERRIDE
        res = super()._check_move_configuration(move)
        if self.code != 'fattura_pa':
            return res

        res.extend(self._l10n_it_edi_check_invoice_configuration(move))

        if not self._get_proxy_user(move.company_id):
            res.append(_("You must accept the terms and conditions in the settings to use FatturaPA."))

        return res

    def _needs_web_services(self):
        self.ensure_one()
        return self.code == 'fattura_pa' or super()._needs_web_services()

    def _l10n_it_post_invoices_step_1(self, invoices):
        ''' Send the invoices to the proxy.
        '''
        to_return = {}

        to_send = {}
        for invoice in invoices:
            xml = "<?xml version='1.0' encoding='UTF-8'?>" + str(self._l10n_it_edi_export_invoice_as_xml(invoice))
            filename = self._l10n_it_edi_generate_electronic_invoice_filename(invoice)
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'res_id': invoice.id,
                'res_model': invoice._name,
                'raw': xml.encode(),
                'description': _('Italian invoice: %s', invoice.move_type),
                'type': 'binary',
            })
            invoice.l10n_it_edi_attachment_id = attachment

            if invoice._is_commercial_partner_pa():
                invoice.message_post(
                    body=(_("Invoices for PA are not managed by Odoo, you can download the document and send it on your own."))
                )
                to_return[invoice] = {'attachment': attachment, 'success': True}
            else:
                to_send[filename] = {
                    'invoice': invoice,
                    'data': {'filename': filename, 'xml': base64.b64encode(xml.encode()).decode()}}

        company = invoices.company_id
        proxy_user = self._get_proxy_user(company)
        if not proxy_user:  # proxy user should exist, because there is a check in _check_move_configuration
            return {invoice: {
                'error': _("You must accept the terms and conditions in the settings to use FatturaPA."),
                'blocking_level': 'error'} for invoice in invoices}

        responses = {}
        if proxy_user._get_demo_state() == 'demo':
            responses = {i['data']['filename']: {'id_transaction': 'demo'} for i in to_send.values()}
        else:
            try:
                responses = self._l10n_it_edi_upload([i['data'] for i in to_send.values()], proxy_user)
            except AccountEdiProxyError as e:
                return {invoice: {'error': e.message, 'blocking_level': 'error'} for invoice in invoices}

        for filename, response in responses.items():
            invoice = to_send[filename]['invoice']
            to_return[invoice] = response
            if 'id_transaction' in response:
                invoice.l10n_it_edi_transaction = response['id_transaction']
                to_return[invoice].update({
                    'error': _('The invoice was sent to FatturaPA, but we are still awaiting a response. Click the link above to check for an update.'),
                    'blocking_level': 'info',
                })
        return to_return

    def _l10n_it_post_invoices_step_2(self, invoices):
        ''' Check if the sent invoices have been processed by FatturaPA.
        '''
        to_check = {i.l10n_it_edi_transaction: i for i in invoices}
        to_return = {}
        company = invoices.company_id
        proxy_user = self._get_proxy_user(company)
        if not proxy_user:  # proxy user should exist, because there is a check in _check_move_configuration
            return {invoice: {
                'error': _("You must accept the terms and conditions in the settings to use FatturaPA."),
                'blocking_level': 'error'} for invoice in invoices}

        if proxy_user._get_demo_state() == 'demo':
            # simulate success and bypass ack
            return {invoice: {'attachment': invoice.l10n_it_edi_attachment_id} for invoice in invoices}
        else:
            try:
                responses = proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/in/TrasmissioneFatture',
                                                    params={'ids_transaction': list(to_check.keys())})
            except AccountEdiProxyError as e:
                return {invoice: {'error': e.message, 'blocking_level': 'error'} for invoice in invoices}

        proxy_acks = []
        for id_transaction, response in responses.items():
            invoice = to_check[id_transaction]
            if 'error' in response:
                to_return[invoice] = response
                continue

            state = response['state']
            if state == 'awaiting_outcome':
                to_return[invoice] = {
                    'error': _('The invoice was sent to FatturaPA, but we are still awaiting a response. Click the link above to check for an update.'),
                    'blocking_level': 'info',
                }
                continue
            elif state == 'not_found':
                # Invoice does not exist on proxy. Either it does not belong to this proxy_user or it was not created correctly when
                # it was sent to the proxy.
                to_return[invoice] = {'error': _('You are not allowed to check the status of this invoice.'), 'blocking_level': 'error'}
                continue

            if not response.get('file'): # It means there is no status update, so we can skip it
                document = invoice.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'fattura_pa')
                to_return[invoice] = {'error': document.error, 'blocking_level': document.blocking_level}
                continue
            xml = proxy_user._decrypt_data(response['file'], response['key'])
            response_tree = etree.fromstring(xml)
            if state == 'ricevutaConsegna':
                if invoice._is_commercial_partner_pa():
                    to_return[invoice] = {'error': _('The invoice has been succesfully transmitted. The addressee has 15 days to accept or reject it.')}
                else:
                    to_return[invoice] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
            elif state == 'notificaScarto':
                elements = response_tree.xpath('//Errore')
                error_codes = [element.find('Codice').text for element in elements]
                errors = [element.find('Descrizione').text for element in elements]
                # Duplicated invoice
                if '00404' in error_codes:
                    idx = error_codes.index('00404')
                    invoice.message_post(body=_(
                        'This invoice number had already been submitted to the SdI, so it is'
                        ' set as Sent. Please verify that the system is correctly configured,'
                        ' because the correct flow does not need to send the same invoice'
                        ' twice for any reason.\n'
                        ' Original message from the SDI: %s', errors[idx]))
                    to_return[invoice] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
                else:
                    # Add helpful text if duplicated filename error
                    if '00002' in error_codes:
                        idx = error_codes.index('00002')
                        errors[idx] = _(
                            'The filename is duplicated. Try again (or adjust the FatturaPA Filename sequence).'
                            ' Original message from the SDI: %s', [errors[idx]]
                        )
                    to_return[invoice] = {'error': self._format_error_message(_('The invoice has been refused by the Exchange System'), errors), 'blocking_level': 'error'}
                    invoice.l10n_it_edi_transaction = False
            elif state == 'notificaMancataConsegna':
                if invoice._is_commercial_partner_pa():
                    to_return[invoice] = {'error': _(
                        'The invoice has been issued, but the delivery to the Public Administration'
                        ' has failed. The Exchange System will contact them to report the problem'
                        ' and request that they provide a solution.'
                        ' During the following 10 days, the Exchange System will try to forward the'
                        ' FatturaPA file to the Public Administration in question again.'
                        ' Should this also fail, the System will notify Odoo of the failed delivery,'
                        ' and you will be required to send the invoice to the Administration'
                        ' through another channel, outside of the Exchange System.')}
                else:
                    to_return[invoice] = {'success': True, 'attachment': invoice.l10n_it_edi_attachment_id}
                    invoice._message_log(body=_(
                        'The invoice has been issued, but the delivery to the Addressee has'
                        ' failed. You will be required to send a courtesy copy of the invoice'
                        ' to your customer through another channel, outside of the Exchange'
                        ' System, and promptly notify him that the original is deposited'
                        ' in his personal area on the portal "Invoices and Fees" of the'
                        ' Revenue Agency.'))
            elif state == 'notificaEsito':
                outcome = response_tree.find('Esito').text
                if outcome == 'EC01':
                    to_return[invoice] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
                else:  # ECO2
                    to_return[invoice] = {'error': _('The invoice was refused by the addressee.'), 'blocking_level': 'error'}
            elif state == 'NotificaDecorrenzaTermini':
                to_return[invoice] = {'attachment': invoice.l10n_it_edi_attachment_id, 'success': True}
            proxy_acks.append(id_transaction)

        if proxy_acks:
            try:
                proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/ack',
                                        params={'transaction_ids': proxy_acks})
            except AccountEdiProxyError as e:
                # Will be ignored and acked again next time.
                _logger.error('Error while acking file to SdiCoop: %s', e)

        return to_return

    def _post_fattura_pa(self, invoice):
        # OVERRIDE
        if not invoice.l10n_it_edi_transaction:
            return self._l10n_it_post_invoices_step_1(invoice)
        else:
            return self._l10n_it_post_invoices_step_2(invoice)

    def _post_invoice_edi(self, invoices):
        # OVERRIDE
        self.ensure_one()
        edi_result = super()._post_invoice_edi(invoices)
        if self.code != 'fattura_pa':
            return edi_result

        return self._post_fattura_pa(invoices)

    # -------------------------------------------------------------------------
    # Proxy methods
    # -------------------------------------------------------------------------

    def _get_proxy_identification(self, company):
        if self.code != 'fattura_pa':
            return super()._get_proxy_identification()

        if not company.l10n_it_codice_fiscale:
            raise UserError(_('Please fill your codice fiscale to be able to receive invoices from FatturaPA'))

        return self.env['res.partner']._l10n_it_normalize_codice_fiscale(company.l10n_it_codice_fiscale)

    def _l10n_it_edi_upload(self, files, proxy_user):
        '''Upload files to fatturapa.

        :param files:    A list of dictionary {filename, base64_xml}.
        :returns:        A dictionary.
        * message:       Message from fatturapa.
        * transactionId: The fatturapa ID of this request.
        * error:         An eventual error.
        * error_level:   Info, warning, error.
        '''
        ERRORS = {
            'EI01': {'error': _lt('Attached file is empty'), 'blocking_level': 'error'},
            'EI02': {'error': _lt('Service momentarily unavailable'), 'blocking_level': 'warning'},
            'EI03': {'error': _lt('Unauthorized user'), 'blocking_level': 'error'},
        }

        if not files:
            return {}

        result = proxy_user._make_request(proxy_user._get_server_url() + '/api/l10n_it_edi/1/out/SdiRiceviFile', params={'files': files})

        # Translate the errors.
        for filename in result.keys():
            if 'error' in result[filename]:
                result[filename] = ERRORS.get(result[filename]['error'], {'error': result[filename]['error'], 'blocking_level': 'error'})

        return result
