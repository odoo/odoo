# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _
from odoo.tests.common import Form
from odoo.osv import expression

import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_ubl_namespaces(self, tree):
        ''' If the namespace is declared with xmlns='...', the namespaces map contains the 'None' key that causes an
        TypeError: empty namespace prefix is not supported in XPath
        Then, we need to remap arbitrarily this key.

        :param tree: An instance of etree.
        :return: The namespaces map without 'None' key.
        '''
        namespaces = tree.nsmap
        namespaces['inv'] = namespaces.pop(None)
        return namespaces

    @api.model
    def _detect_ubl_2_1(self, tree, file_name):
        # Quick check the tree looks like an UBL 2.1 file.
        flag = tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice'
        error = None

        return {'flag': flag, 'error': error}

    @api.model
    def _decode_ubl_2_1(self, tree):
        self.ensure_one()
        namespaces = self._get_ubl_namespaces(tree)

        elements = tree.xpath('//cbc:InvoiceTypeCode', namespaces=namespaces)
        if elements:
            type_code = elements[0].text
            type = 'in_refund' if type_code == '381' else 'in_invoice'
        else:
            type = 'in_invoice'

        default_journal = self.with_context(default_type=type)._get_default_journal()

        with Form(self.with_context(default_type=type, default_journal_id=default_journal.id)) as invoice_form:
            # Reference
            elements = tree.xpath('//cbc:ID', namespaces=namespaces)
            if elements:
                invoice_form.ref = elements[0].text
            elements = tree.xpath('//cbc:InstructionID', namespaces=namespaces)
            if elements:
                invoice_form.invoice_payment_ref = elements[0].text

            # Dates
            elements = tree.xpath('//cbc:IssueDate', namespaces=namespaces)
            if elements:
                invoice_form.invoice_date = elements[0].text
            elements = tree.xpath('//cbc:PaymentDueDate', namespaces=namespaces)
            if elements:
                invoice_form.invoice_date_due = elements[0].text
            # allow both cbc:PaymentDueDate and cbc:DueDate
            elements = tree.xpath('//cbc:DueDate', namespaces=namespaces)
            invoice_form.invoice_date_due = invoice_form.invoice_date_due or elements and elements[0].text

            # Currency
            elements = tree.xpath('//cbc:DocumentCurrencyCode', namespaces=namespaces)
            currency_code = elements and elements[0].text or ''
            currency = self.env['res.currency'].search([('name', '=', currency_code.upper())], limit=1)
            if elements:
                invoice_form.currency_id = currency

            # Incoterm
            elements = tree.xpath('//cbc:TransportExecutionTerms/cac:DeliveryTerms/cbc:ID', namespaces=namespaces)
            if elements:
                invoice_form.invoice_incoterm_id = self.env['account.incoterms'].search([('code', '=', elements[0].text)], limit=1)

            # Partner
            partner_element = tree.xpath('//cac:AccountingSupplierParty/cac:Party', namespaces=namespaces)
            if partner_element:
                domains = []
                partner_element = partner_element[0]
                elements = partner_element.xpath('//cac:AccountingSupplierParty/cac:Party//cbc:Name', namespaces=namespaces)
                if elements:
                    partner_name = elements[0].text
                    domains.append([('name', 'ilike', partner_name)])
                elements = partner_element.xpath('//cac:AccountingSupplierParty/cac:Party//cbc:Telephone', namespaces=namespaces)
                if elements:
                    partner_telephone = elements[0].text
                    domains.append([('phone', '=', partner_telephone), ('mobile', '=', partner_telephone)])
                elements = partner_element.xpath('//cac:AccountingSupplierParty/cac:Party//cbc:ElectronicMail', namespaces=namespaces)
                if elements:
                    partner_mail = elements[0].text
                    domains.append([('email', '=', partner_mail)])
                elements = partner_element.xpath('//cac:AccountingSupplierParty/cac:Party//cbc:ID', namespaces=namespaces)
                if elements:
                    partner_id = elements[0].text
                    domains.append([('vat', 'like', partner_id)])

                if domains:
                    partner = self.env['res.partner'].search(expression.OR(domains), limit=1)
                    if partner:
                        invoice_form.partner_id = partner
                    else:
                        invoice_form.partner_id = self.env['res.partner']

            # Regenerate PDF
            attachments = self.env['ir.attachment']
            elements = tree.xpath('//cac:AdditionalDocumentReference', namespaces=namespaces)
            for element in elements:
                attachment_name = element.xpath('cbc:ID', namespaces=namespaces)
                attachment_data = element.xpath('cac:Attachment//cbc:EmbeddedDocumentBinaryObject', namespaces=namespaces)
                if attachment_name and attachment_data:
                    attachments |= self.env['ir.attachment'].create({
                        'name': attachment_name[0].text,
                        'res_id': self.id,
                        'res_model': 'account.move',
                        'datas': attachment_data[0].text,
                        'type': 'binary',
                    })
            if attachments:
                self.with_context(no_new_invoice=True).message_post(attachment_ids=attachments.ids)

            # Lines
            lines_elements = tree.xpath('//cac:InvoiceLine', namespaces=namespaces)
            for eline in lines_elements:
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    # Quantity
                    elements = eline.xpath('cbc:InvoicedQuantity', namespaces=namespaces)
                    quantity = elements and float(elements[0].text) or 1.0
                    invoice_line_form.quantity = quantity

                    # Price Unit
                    elements = eline.xpath('cac:Price/cbc:PriceAmount', namespaces=namespaces)
                    invoice_line_form.price_unit = elements and float(elements[0].text) or 0.0

                    # Name
                    elements = eline.xpath('cac:Item/cbc:Description', namespaces=namespaces)
                    invoice_line_form.name = elements and elements[0].text or ''
                    invoice_line_form.name = invoice_line_form.name.replace('%month%', str(fields.Date.to_date(invoice_form.invoice_date).month))  # TODO: full name in locale
                    invoice_line_form.name = invoice_line_form.name.replace('%year%', str(fields.Date.to_date(invoice_form.invoice_date).year))

                    # Product
                    elements = eline.xpath('cac:Item/cac:SellersItemIdentification/cbc:ID', namespaces=namespaces)
                    domains = []
                    if elements:
                        product_code = elements[0].text
                        domains.append([('default_code', '=', product_code)])
                    elements = eline.xpath('cac:Item/cac:StandardItemIdentification/cbc:ID[@schemeID=\'GTIN\']', namespaces=namespaces)
                    if elements:
                        product_ean13 = elements[0].text
                        domains.append([('ean13', '=', product_ean13)])
                    if domains:
                        product = self.env['product.product'].search(expression.OR(domains), limit=1)
                        if product:
                            invoice_line_form.product_id = product

                    # Taxes
                    taxes_elements = eline.xpath('cac:TaxTotal/cac:TaxSubtotal', namespaces=namespaces)
                    invoice_line_form.tax_ids.clear()
                    for etax in taxes_elements:
                        elements = etax.xpath('cbc:Percent', namespaces=namespaces)
                        if elements:
                            tax = self.env['account.tax'].search([
                                ('company_id', '=', self.env.company.id),
                                ('amount', '=', float(elements[0].text)),
                                ('type_tax_use', '=', invoice_form.journal_id.type),
                            ], order='sequence ASC', limit=1)
                            if tax:
                                invoice_line_form.tax_ids.add(tax)

        return invoice_form.save()

    @api.model
    def _get_xml_decoders(self):
        # Override
        ubl_decoders = [('UBL 2.1', self._detect_ubl_2_1, self._decode_ubl_2_1)]
        return super(AccountMove, self)._get_xml_decoders() + ubl_decoders
