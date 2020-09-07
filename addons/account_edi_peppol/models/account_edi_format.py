# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from lxml import etree
import base64
from odoo.tools import float_repr
from odoo.tests.common import Form
from odoo.exceptions import UserError
from odoo.osv import expression


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------------

    def _check_for_incompatibilities(self, invoice):
        '''Throws an error if some information is missing to generate valid UBL'''
        errors = []
        if not invoice.company_id.partner_id.commercial_partner_id.peppol_endpoint_scheme:
            errors.append(_('Only companies with a European VAT are supported'))
            # See PEPPOL_COUNTRY_EAS : only those VAT number are supported.
            # Other identification are possible but not yet implemented in Odoo, see : https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/
        if not invoice.company_id.partner_id.commercial_partner_id.peppol_endpoint:
            errors.append(_('Please set a vat number on the seller\'s company'))

        if not invoice.commercial_partner_id.peppol_endpoint_scheme:
            errors.append(_('Only companies with a European VAT are supported (customer)'))
        if not invoice.commercial_partner_id.peppol_endpoint:
            errors.append(_('Please set a vat number on the customer\'s company'))
        return errors

    def _export_peppol(self, invoice):
        self.ensure_one()

        def format_monetary(amount, currency=invoice.currency_id):
            # Format the monetary values to avoid trailing decimals (e.g. 90.85000000000001).
            return float_repr(amount, currency.decimal_places)

        def convert_monetary(amount, from_currency):
            # All monetary should be in the invoice currency, except for vat total
            return from_currency._convert(amount, invoice.currency_id, invoice.company_id, invoice.invoice_date)

        def get_tax_total():
            breakdown = {}
            for line in invoice.invoice_line_ids.filtered(lambda line: not line.display_type):
                if line.tax_ids:
                    price_unit_wo_discount = line.price_unit * (1 - (line.discount / 100.0))
                    line_taxes = line.tax_ids.compute_all(
                        price_unit_wo_discount,
                        quantity=line.quantity,
                        product=line.product_id,
                        partner=invoice.partner_id,
                        currency=line.currency_id,
                        is_refund=invoice.move_type in ('out_refund', 'in_refund'))['taxes']
                    for tax in line_taxes:
                        tax_category = 'S' if tax['amount'] else 'Z'
                        tax_percent = self.env['account.tax'].browse(tax['id']).amount
                        breakdown.setdefault((tax_category, tax_percent), {'base': 0, 'amount': 0})
                        breakdown[(tax_category, tax_percent)]['base'] += tax['base']
                        breakdown[(tax_category, tax_percent)]['amount'] += tax['amount']
                else:
                    breakdown.setdefault(('Z', 0), {'base': 0, 'amount': 0})
                    breakdown[('Z', 0)]['base'] += line.price_subtotal

            sign = -1 if invoice.move_type in ('out_refund', 'in_refund') else 1
            return {'amount': invoice.amount_tax,
                    'seller_currency': invoice.company_id.currency_id,
                    'amount_seller_currency': invoice.currency_id._convert(invoice.amount_tax_signed * sign, invoice.company_id.currency_id, invoice.company_id, invoice.date),
                    'breakdown': breakdown}

        errors = self._check_for_incompatibilities(invoice)
        if errors:
            return {'error': errors}

        # Create file content.
        data = {
            'invoice': invoice,

            'type_code': 380 if invoice.move_type == 'out_invoice' else 381,
            'payment_means_code': 42 if invoice.journal_id.bank_account_id else 31,
            'due_date': fields.Date.to_string(invoice.invoice_date_due),
            'invoice_date': fields.Date.to_string(invoice.invoice_date),

            'format_monetary': format_monetary,
            'convert_monetary': convert_monetary,
            'tax_total': get_tax_total()
        }

        xml_content = self.env.ref('account_edi_peppol.export_peppol_invoice')._render(data)
        xml_name = '%s_peppol_bis3.xml' % (invoice.name.replace('/', '_'))
        return {'attachment': self.env['ir.attachment'].create({
            'name': xml_name,
            'datas': base64.encodebytes(xml_content),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'mimetype': 'application/xml'
        })}

    # -------------------------------------------------------------------------
    # Import
    # -------------------------------------------------------------------------

    def _is_peppol(self, filename, tree):
        tag = tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice'
        profile = tree.xpath("//*[local-name()='ProfileID']")
        profile = profile[0].text == 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0' if profile else False

        return self.code == 'peppol_3_10' and tag and profile

    def _decode_peppol(self, tree, invoice):

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

        with Form(invoice.with_context(default_move_type='in_invoice')) as invoice_form:
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
                vat=_find_value('//cac:AccountingSupplierParty/cac:Party//cbc:ID'),
            )

            # Lines
            lines_elements = tree.xpath('//cac:InvoiceLine', namespaces=namespaces)
            for eline in lines_elements:
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    # Product
                    invoice_line_form.product_id = self._retrieve_product(
                        default_code=_find_value('cac:Item/cac:SellersItemIdentification/cbc:ID', eline),
                        name=_find_value('cac:Item/cbc:Name', eline),
                        ean13=_find_value('cac:Item/cac:StandardItemIdentification/cbc:ID[@schemeID=\'0160\']', eline)
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

    # -------------------------------------------------------------------------
    # BUSINESS FLOW: EDI (Export)
    # -------------------------------------------------------------------------

    def _post_invoice_edi(self, invoice, test_mode=False):
        self.ensure_one()
        if self.code != 'peppol_3_10':
            return super()._post_invoice_edi(invoice, test_mode=test_mode)
        return {invoice: self._export_peppol(invoice)}

    # -------------------------------------------------------------------------
    # BUSINESS FLOW: EDI (Import)
    # -------------------------------------------------------------------------

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self._is_peppol(filename, tree):
            return self._decode_peppol()(tree, self.env['account_move'])
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self._is_peppol(filename, tree):
            return self._decode_peppol(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)
