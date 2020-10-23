# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tests.common import Form


COUNTRY_EAS = {
    'HU': 9910,

    'AD': 9922,
    'AL': 9923,
    'BA': 9924,
    'BE': 9925,
    'BG': 9926,
    'CH': 9927,
    'CY': 9928,
    'CZ': 9929,
    'DE': 9930,
    'EE': 9931,
    'UK': 9932,
    'GR': 9933,
    'HR': 9934,
    'IE': 9935,
    'LI': 9936,
    'LT': 9937,
    'LU': 9938,
    'LV': 9939,
    'MC': 9940,
    'ME': 9941,
    'MK': 9942,
    'MT': 9943,
    'NL': 9944,
    'PL': 9945,
    'PT': 9946,
    'RO': 9947,
    'RS': 9948,
    'SI': 9949,
    'SK': 9950,
    'SM': 9951,
    'TR': 9952,
    'VA': 9953,

    'SE': 9955,

    'FR': 9957
}


class AccountEdiFormat(models.Model):
    ''' This edi_format is "abstract" meaning that it provides an additional layer for similar edi_format (formats deriving from
    EN16931) that share some functionnalities, but needs to be extended to be used.
    '''
    _inherit = 'account.edi.format'

    ####################################################
    # Helpers
    ####################################################

    def _check_en_16931_invoice_configuration(self, invoice):
        errors = []

        # partners
        customer = invoice.commercial_partner_id
        if not self._get_ubl_partner_values(customer).get('en_16931_endpoint', False):
            errors.append(_('The customer needs to have an endpoint id, typically this is the vat number. Please note that countries outside of EU are not supported.'))

        supplier = invoice.company_id.partner_id.commercial_partner_id
        if not self._get_ubl_partner_values(supplier).get('en_16931_endpoint', False):
            errors.append(_('The supplier needs to have an endpoint id, typically this is the vat number. Please note that countries outside of EU are not supported.'))

        # invoice line
        if invoice.invoice_line_ids.filtered(lambda l: not (l.product_id.name or l.name)):
            errors.append(_('Each invoice line must have a product or a label.'))

        if invoice.invoice_line_ids.tax_ids.invoice_repartition_line_ids.filtered(lambda r: r.use_in_tax_closing) and \
           not supplier.vat:
            errors.append(_("When vat is present, the supplier must have a vat number."))

        return errors

    def _get_ubl_partner_values(self, partner):
        # OVERRIDE
        values = super()._get_ubl_partner_values(partner)
        if partner.country_id.code in COUNTRY_EAS:
            values['en_16931_endpoint'] = partner.vat
            values['en_16931_endpoint_scheme'] = COUNTRY_EAS[partner.country_id.code]
        return values

    def _get_ubl_values(self, invoice):
        ''' Get the necessary values to generate the XML. These values will be used in the qweb template when rendering.
        Needed values differ depending on the implementation of the EN16931, as (sub)template can be overriden or called dynamically.
        TO OVERRIDE

        :returns:   a dictionary with the value used in the template has key and the value as value.
        '''
        self.ensure_one()

        def convert_monetary(amount, from_currency):
            # All monetary should be in the invoice currency, except for vat total
            return from_currency._convert(amount, invoice.currency_id, invoice.company_id, invoice.invoice_date)

        values = super()._get_ubl_values(invoice)
        values.update({
            'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0',
            'profile_id': 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0',
            'due_date': fields.Date.to_string(invoice.invoice_date_due),
            'invoice_date': fields.Date.to_string(invoice.invoice_date),

            'convert_monetary': convert_monetary,
        })

        # Compute tax and price values based on compute_all
        # In BIS3 only vat are considered as taxes, other taxes must be applied already.
        values['lines'] = {}
        values['price_subtotal'] = 0
        values['tax_total'] = 0
        values.setdefault('breakdown', {})
        for line in invoice.invoice_line_ids.filtered(lambda line: not line.display_type):
            price_unit_wo_discount = line.price_unit * (1 - (line.discount / 100.0))
            line_taxes = line.tax_ids.compute_all(
                price_unit_wo_discount,
                quantity=line.quantity,
                product=line.product_id,
                partner=invoice.partner_id,
                currency=line.currency_id,
                is_refund=invoice.move_type in ('out_refund', 'in_refund'))
            line_vals = {'base': line_taxes['total_excluded'], 'category': 'Z', 'percent': 0}
            values['price_subtotal'] += line_taxes['total_excluded']
            for tax in line_taxes['taxes']:
                repartition_line = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
                if repartition_line.use_in_tax_closing:
                    tax_percent = self.env['account.tax'].browse(tax['id']).amount
                    tax_category = 'S' if tax_percent else 'Z'
                    if line_vals['category'] != 'Z' and line_vals['percent'] != tax_percent:
                        raise UserError('Multiple vat percentage not supported on the same invoice line')
                    else:
                        line_vals['percent'] = tax_percent
                        line_vals['category'] = tax_category
                        values['breakdown'].setdefault((tax_category, tax_percent), {'base': 0, 'amount': 0})
                        values['breakdown'][(tax_category, tax_percent)]['base'] += tax['base']
                        values['breakdown'][(tax_category, tax_percent)]['amount'] += tax['amount']
                        values['tax_total'] += tax['amount']
                else:
                    line_vals['base'] += tax['amount']
                    values['price_subtotal'] += tax['amount']
            values['lines'][line] = line_vals

        values['seller_currency'] = invoice.company_id.currency_id,
        values['tax_total_seller_currency'] = invoice.currency_id._convert(values['tax_total'], invoice.company_id.currency_id, invoice.company_id, invoice.date),

        return values

    ####################################################
    # Import
    ####################################################

    def _decode_en_16931(self, tree, invoice):
        """ Decodes an EN16931 invoice into an invoice.

        :param tree:    the UBL (EN16931) tree to decode.
        :param invoice: the invoice to update or an empty recordset.
        :returns:       the invoice where the UBL (EN16931) data was imported.
        """

        namespaces = self._get_ubl_namespaces(tree)

        def _find_value(xpath, element=tree):
            return self._find_value(xpath, element, namespaces)

        elements = tree.xpath('//cbc:InvoiceTypeCode', namespaces=namespaces)
        if elements:
            type_code = elements[0].text
            move_type = 'in_refund' if type_code == '381' else 'in_invoice'
        else:
            move_type = 'in_invoice'

        default_journal = invoice.with_context(default_move_type=move_type)._get_default_journal()

        with Form(invoice.with_context(default_move_type=move_type, default_journal_id=default_journal.id)) as invoice_form:
            # Reference
            elements = tree.xpath('//cbc:ID', namespaces=namespaces)
            if elements:
                invoice_form.ref = elements[0].text

            # Dates
            elements = tree.xpath('//cbc:IssueDate', namespaces=namespaces)
            if elements:
                invoice_form.invoice_date = elements[0].text
            elements = tree.xpath('//cbc:DueDate', namespaces=namespaces)
            if elements:
                invoice_form.invoice_date_due = elements[0].text

            # Currency
            currency = self._retrieve_currency(_find_value('//cbc:DocumentCurrencyCode'))
            if currency:
                invoice_form.currency_id = currency

            # Partner
            invoice_form.partner_id = self._retrieve_partner(
                name=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:Name'),
                phone=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:Telephone'),
                mail=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:ElectronicMail'),
                vat=_find_value('//cac:AccountingSupplierParty/cac:Party//cac:PartyTaxScheme/cbc:CompanyID'),
            )

            # Lines
            lines_elements = tree.xpath('//cac:InvoiceLine', namespaces=namespaces)
            for eline in lines_elements:
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    # Product
                    invoice_line_form.product_id = self._retrieve_product(
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
                    line_extension_amount = elements and float(elements[0].text) or 0.0
                    invoice_line_form.price_unit = price_unit or line_extension_amount / invoice_line_form.quantity or 0.0

                    # Name
                    elements = eline.xpath('cac:Item/cbc:Description', namespaces=namespaces)
                    invoice_line_form.name = elements and elements[0].text or ''

                    # Taxes
                    tax_element = eline.xpath('cac:Item/cac:ClassifiedTaxCategory', namespaces=namespaces)
                    invoice_line_form.tax_ids.clear()
                    for eline in tax_element:
                        invoice_line_form.tax_ids.add(self._retrieve_tax(
                            amount=_find_value('cbc:Percent', eline),
                            type_tax_use=invoice_form.journal_id.type
                        ))

        return invoice_form.save()
