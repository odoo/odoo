# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields, tools, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr
from odoo.tests.common import Form
from odoo.exceptions import UserError
from odoo.osv import expression

from pathlib import PureWindowsPath

import logging

_logger = logging.getLogger(__name__)


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _create_invoice_from_ubl(self, tree):
        invoice = self.env['account.move']
        journal = invoice._get_default_journal()

        move_type = 'out_invoice' if journal.type == 'sale' else 'in_invoice'
        element = tree.find('.//{*}InvoiceTypeCode')
        if element is not None and element.text == '381':
            move_type = 'in_refund' if move_type == 'in_invoice' else 'out_refund'

        invoice = invoice.with_context(default_move_type=move_type, default_journal_id=journal.id)
        return self._import_ubl(tree, invoice)

    def _update_invoice_from_ubl(self, tree, invoice):
        invoice = invoice.with_context(default_move_type=invoice.move_type, default_journal_id=invoice.journal_id.id)
        return self._import_ubl(tree, invoice)

    def _import_ubl(self, tree, invoice):
        """ Decodes an UBL invoice into an invoice.

        :param tree:    the UBL tree to decode.
        :param invoice: the invoice to update or an empty recordset.
        :returns:       the invoice where the UBL data was imported.
        """

        def _get_ubl_namespaces():
            ''' If the namespace is declared with xmlns='...', the namespaces map contains the 'None' key that causes an
            TypeError: empty namespace prefix is not supported in XPath
            Then, we need to remap arbitrarily this key.

            :param tree: An instance of etree.
            :return: The namespaces map without 'None' key.
            '''
            namespaces = tree.nsmap
            namespaces['inv'] = namespaces.pop(None)
            return namespaces

        namespaces = _get_ubl_namespaces()

        def _find_value(xpath, element=tree):
            return self._find_value(xpath, element, namespaces)

        with Form(invoice.with_context(account_predictive_bills_disable_prediction=True)) as invoice_form:
            self_ctx = self.with_company(invoice.company_id.id)

            # Reference
            elements = tree.xpath('//cbc:ID', namespaces=namespaces)
            if elements:
                invoice_form.ref = elements[0].text
            elements = tree.xpath('//cbc:InstructionID', namespaces=namespaces)
            if elements:
                invoice_form.payment_reference = elements[0].text

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
            invoice_form.partner_id = self_ctx._retrieve_partner(
                name=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:Name'),
                phone=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:Telephone'),
                mail=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:ElectronicMail'),
                vat=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:CompanyID'),
            )

            # Lines
            lines_elements = tree.xpath('//cac:InvoiceLine', namespaces=namespaces)
            for eline in lines_elements:
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    # Product
                    invoice_line_form.product_id = self_ctx._retrieve_product(
                        default_code=_find_value('cac:Item/cac:SellersItemIdentification/cbc:ID', eline),
                        name=_find_value('cac:Item/cbc:Name', eline),
                        barcode=_find_value('cac:Item/cac:StandardItemIdentification/cbc:ID[@schemeID=\'0160\']', eline)
                    )

                    # Quantity
                    elements = eline.xpath('cbc:InvoicedQuantity', namespaces=namespaces)
                    quantity = elements and float(elements[0].text) or 1.0
                    invoice_line_form.quantity = quantity

                    # Price Unit
                    elements = eline.xpath('cac:Price/cbc:PriceAmount', namespaces=namespaces)
                    price_unit = elements and float(elements[0].text) or 0.0
                    elements = eline.xpath('cbc:LineExtensionAmount', namespaces=namespaces)
                    line_extension_amount = elements and float(elements[0].text) or 0.0
                    invoice_line_form.price_unit = price_unit or line_extension_amount / invoice_line_form.quantity or 0.0

                    # Name
                    elements = eline.xpath('cac:Item/cbc:Description', namespaces=namespaces)
                    if elements and elements[0].text:
                        invoice_line_form.name = elements[0].text
                        invoice_line_form.name = invoice_line_form.name.replace('%month%', str(fields.Date.to_date(invoice_form.invoice_date).month))  # TODO: full name in locale
                        invoice_line_form.name = invoice_line_form.name.replace('%year%', str(fields.Date.to_date(invoice_form.invoice_date).year))
                    else:
                        partner_name = _find_value('//cac:AccountingSupplierParty/cac:Party//cbc:Name')
                        invoice_line_form.name = "%s (%s)" % (partner_name or '', invoice_form.invoice_date)

                    # Taxes
                    tax_element = eline.xpath('cac:TaxTotal/cac:TaxSubtotal', namespaces=namespaces)
                    invoice_line_form.tax_ids.clear()
                    for eline in tax_element:
                        tax = self_ctx._retrieve_tax(
                            amount=_find_value('cbc:Percent', eline),
                            type_tax_use=invoice_form.journal_id.type
                        )
                        if tax:
                            invoice_line_form.tax_ids.add(tax)
        invoice = invoice_form.save()

        # Regenerate PDF
        attachments = self.env['ir.attachment']
        elements = tree.xpath('//cac:AdditionalDocumentReference', namespaces=namespaces)
        for element in elements:
            attachment_name = element.xpath('cbc:ID', namespaces=namespaces)
            attachment_data = element.xpath('cac:Attachment//cbc:EmbeddedDocumentBinaryObject', namespaces=namespaces)
            if attachment_name and attachment_data:
                text = attachment_data[0].text
                # Normalize the name of the file : some e-fff emitters put the full path of the file
                # (Windows or Linux style) and/or the name of the xml instead of the pdf.
                # Get only the filename with a pdf extension.
                name = PureWindowsPath(attachment_name[0].text).stem + '.pdf'
                attachments |= self.env['ir.attachment'].create({
                    'name': name,
                    'res_id': invoice.id,
                    'res_model': 'account.move',
                    'datas': text + '=' * (len(text) % 3),  # Fix incorrect padding
                    'type': 'binary',
                    'mimetype': 'application/pdf',
                })
        if attachments:
            invoice.with_context(no_new_invoice=True).message_post(attachment_ids=attachments.ids)

        return invoice
