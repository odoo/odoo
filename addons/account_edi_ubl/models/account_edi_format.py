# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo import _, models, fields
from odoo.exceptions import UserError
from odoo.tests.common import Form

# Electronic Address Scheme (EAS), see https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/
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

    'FR': 9957,
}


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_edi_ubl_info_hook(self, company_country_code):
        self.ensure_one()

        if self.code == 'ubl_2_1':
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_21'],
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl_2_1.xml",
            }

        # XRechnung (DE)
        if self.code == 'ubl_bis3' and company_country_code == 'DE':
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_de'],
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl_xrechnung.xml",
                'invoice_embed_to_pdf': True,
            }

        # Standard Peppol
        if self.code == 'ubl_bis3' and company_country_code in ('BE', 'FR'):
            return {
                'invoice_xml_builder': self.env['account.edi.xml.ubl_bis3'],
                'invoice_filename': lambda inv: f"{inv.name.replace('/', '_')}_ubl_bis3.xml",
            }

    def _get_edi_ubl_info(self, company, customer_country_code=None):
        self.ensure_one()

        if not company.country_id:
            return

        company_country_code = company.country_id.code.upper()
        is_customer_peppol_ok = not customer_country_code or customer_country_code.upper() in (
            'BE', 'NL', 'FR', 'DE', 'LU', 'NO',
        )

        if self.code != 'ubl_bis3' or not is_customer_peppol_ok:
            return {}

        return self._get_edi_ubl_info_hook(company_country_code)

    ####################################################
    # Import: Account.edi.format override
    ####################################################

    def _is_old_facturx(self, journal, filename, tree):
        return tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice'

    def _import_old_facturx(self, tree, invoice):
        """ Decodes a factur-x invoice into an invoice.
        :param tree:    the factur-x tree to decode.
        :param invoice: the invoice to update or an empty recordset.
        :returns:       the invoice where the factur-x data was imported.
        """

        def _find_value(xpath, element=tree):
            return self._find_value(xpath, element, tree.nsmap)

        default_facturx_date_format = '%Y%m%d'

        amount_total_import = None

        default_move_type = False
        if invoice._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(self.env.context['default_journal_id'])
            default_move_type = 'out_invoice' if journal.type == 'sale' else 'in_invoice'
        elif invoice._context.get('default_move_type'):
            default_move_type = self._context['default_move_type']
        elif invoice.move_type in self.env['account.move'].get_invoice_types(include_receipts=True):
            # in case an attachment is saved on a draft invoice previously created, we might
            # have lost the default value in context but the type was already set
            default_move_type = invoice.move_type

        if not default_move_type:
            raise UserError(_("No information about the journal or the type of invoice is passed"))
        if default_move_type == 'entry':
            return

        # Total amount.
        elements = tree.xpath('//ram:GrandTotalAmount', namespaces=tree.nsmap)
        total_amount = elements and float(elements[0].text) or 0.0

        # Refund type.
        # There is two modes to handle refund in Factur-X:
        # a) type_code == 380 for invoice, type_code == 381 for refund, all positive amounts.
        # b) type_code == 380, negative amounts in case of refund.
        # To handle both, we consider the 'a' mode and switch to 'b' if a negative amount is encountered.
        elements = tree.xpath('//rsm:ExchangedDocument/ram:TypeCode', namespaces=tree.nsmap)
        type_code = elements[0].text

        default_move_type.replace('_refund', '_invoice')
        if type_code == '381':
            default_move_type = 'out_refund' if default_move_type == 'out_invoice' else 'in_refund'
            refund_sign = -1
        else:
            # Handle 'b' refund mode.
            if total_amount < 0:
                default_move_type = 'out_refund' if default_move_type == 'out_invoice' else 'in_refund'
            refund_sign = -1 if 'refund' in default_move_type else 1

        # Write the type as the journal entry is already created.
        invoice.move_type = default_move_type

        # self could be a single record (editing) or be empty (new).
        with Form(invoice.with_context(default_move_type=default_move_type,
                                       account_predictive_bills_disable_prediction=True)) as invoice_form:
            partner_type = invoice_form.journal_id.type == 'purchase' and 'SellerTradeParty' or 'BuyerTradeParty'
            invoice_form.partner_id = self._retrieve_partner(
                name=_find_value(f"//ram:{partner_type}/ram:Name"),
                mail=_find_value(f"//ram:{partner_type}//ram:URIID[@schemeID='SMTP']"),
                vat=_find_value(f"//ram:{partner_type}/ram:SpecifiedTaxRegistration/ram:ID"),
            )

            # Delivery partner
            if 'partner_shipping_id' in invoice._fields:
                invoice_form.partner_shipping_id = self._retrieve_partner(
                    name=_find_value("//ram:ShipToTradeParty/ram:Name"),
                    mail=_find_value("//ram:ShipToTradeParty//ram:URIID[@schemeID='SMTP']"),
                    vat=_find_value("//ram:ShipToTradeParty/ram:SpecifiedTaxRegistration/ram:ID"),
                )

            # Reference.
            elements = tree.xpath('//rsm:ExchangedDocument/ram:ID', namespaces=tree.nsmap)
            if elements:
                invoice_form.ref = elements[0].text

            # Name.
            elements = tree.xpath('//ram:BuyerOrderReferencedDocument/ram:IssuerAssignedID', namespaces=tree.nsmap)
            if elements:
                invoice_form.payment_reference = elements[0].text

            # Comment.
            elements = tree.xpath('//ram:IncludedNote/ram:Content', namespaces=tree.nsmap)
            if elements:
                invoice_form.narration = elements[0].text

            # Total amount.
            elements = tree.xpath('//ram:GrandTotalAmount', namespaces=tree.nsmap)
            if elements:

                # Currency.
                currency_str = elements[0].attrib.get('currencyID', None)
                if currency_str:
                    invoice_form.currency_id = self._retrieve_currency(currency_str)

                    # Store xml total amount.
                    amount_total_import = total_amount * refund_sign

            # Date.
            elements = tree.xpath('//rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString', namespaces=tree.nsmap)
            if elements:
                date_str = elements[0].text
                invoice_form.invoice_date = datetime.strptime(date_str, default_facturx_date_format).date()

            # Due date.
            elements = tree.xpath('//ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString', namespaces=tree.nsmap)
            if elements:
                date_str = elements[0].text
                invoice_form.invoice_date_due = datetime.strptime(date_str, default_facturx_date_format).date()

            # Invoice lines.
            elements = tree.xpath('//ram:IncludedSupplyChainTradeLineItem', namespaces=tree.nsmap)
            if elements:
                for element in elements:
                    with invoice_form.invoice_line_ids.new() as invoice_line_form:

                        # Sequence.
                        line_elements = element.xpath('.//ram:AssociatedDocumentLineDocument/ram:LineID', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.sequence = int(line_elements[0].text)

                        # Product.
                        name = _find_value('.//ram:SpecifiedTradeProduct/ram:Name', element)
                        if name:
                            invoice_line_form.name = name
                        invoice_line_form.product_id = self._retrieve_product(
                            default_code=_find_value('.//ram:SpecifiedTradeProduct/ram:SellerAssignedID', element),
                            name=_find_value('.//ram:SpecifiedTradeProduct/ram:Name', element),
                            barcode=_find_value('.//ram:SpecifiedTradeProduct/ram:GlobalID', element)
                        )

                        # Quantity.
                        line_elements = element.xpath('.//ram:SpecifiedLineTradeDelivery/ram:BilledQuantity', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.quantity = float(line_elements[0].text)

                        # Price Unit.
                        line_elements = element.xpath('.//ram:GrossPriceProductTradePrice/ram:ChargeAmount', namespaces=tree.nsmap)
                        if line_elements:
                            quantity_elements = element.xpath('.//ram:GrossPriceProductTradePrice/ram:BasisQuantity', namespaces=tree.nsmap)
                            if quantity_elements:
                                invoice_line_form.price_unit = float(line_elements[0].text) / float(quantity_elements[0].text)
                            else:
                                invoice_line_form.price_unit = float(line_elements[0].text)
                        else:
                            line_elements = element.xpath('.//ram:NetPriceProductTradePrice/ram:ChargeAmount', namespaces=tree.nsmap)
                            if line_elements:
                                quantity_elements = element.xpath('.//ram:NetPriceProductTradePrice/ram:BasisQuantity', namespaces=tree.nsmap)
                                if quantity_elements:
                                    invoice_line_form.price_unit = float(line_elements[0].text) / float(quantity_elements[0].text)
                                else:
                                    invoice_line_form.price_unit = float(line_elements[0].text)
                        # Discount.
                        line_elements = element.xpath('.//ram:AppliedTradeAllowanceCharge/ram:CalculationPercent', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.discount = float(line_elements[0].text)

                        # Taxes
                        tax_element = element.xpath('.//ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent', namespaces=tree.nsmap)
                        invoice_line_form.tax_ids.clear()
                        for eline in tax_element:
                            tax = self._retrieve_tax(
                                amount=eline.text,
                                type_tax_use=invoice_form.journal_id.type
                            )
                            if tax:
                                invoice_line_form.tax_ids.add(tax)

            elif amount_total_import:
                # No lines in BASICWL.
                with invoice_form.invoice_line_ids.new() as invoice_line_form:
                    invoice_line_form.name = invoice_form.comment or '/'
                    invoice_line_form.quantity = 1
                    invoice_line_form.price_unit = amount_total_import

        return invoice_form.save()

    def _create_invoice_from_xml_tree(self, journal, filename, tree):
        # OVERRIDE
        self.ensure_one()

        if self.code in ('ubl_2_1', 'ubl_bis3'):
            ubl_info = self._get_edi_ubl_info(journal.company_id)
            if ubl_info:
                invoice = ubl_info['invoice_xml_builder']._import_invoice(journal, filename, tree)
                if invoice:
                    return invoice

            if self._is_old_facturx(journal, filename, tree):
                invoice = self._import_old_facturx(tree, self.env['account.move'])
                if invoice:
                    return invoice

        return super()._create_invoice_from_xml_tree(journal, filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        # OVERRIDE
        self.ensure_one()

        if self.code in ('ubl_2_1', 'ubl_bis3'):
            ubl_info = self._get_edi_ubl_info(invoice.journal_id.company_id)
            if ubl_info:
                invoice = ubl_info['invoice_xml_builder']._import_invoice(invoice.journal_id, filename, tree, existing_invoice=invoice)
                if invoice:
                    return invoice

            if self._is_old_facturx(invoice.journal_id, filename, tree):
                invoice = self._import_old_facturx(tree, invoice)
                if invoice:
                    return invoice

        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    ####################################################
    # Export: Account.edi.format override
    ####################################################

    def _is_required_for_invoice(self, invoice):
        # OVERRIDE
        self.ensure_one()

        if self.code in ('ubl_2_1', 'ubl_bis3'):
            if invoice.move_type not in ('out_invoice', 'out_refund'):
                return False

            ubl_info = self._get_edi_ubl_info(invoice.company_id, customer_country_code=invoice.partner_id.country_id.code)
            return bool(ubl_info)

        return super()._is_required_for_invoice(invoice)

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()

        if self.code in ('ubl_2_1', 'ubl_bis3'):
            return bool(self._get_edi_ubl_info(journal.company_id))

        return super()._is_compatible_with_journal(journal)

    def _is_enabled_by_default_on_journal(self, journal):
        # OVERRIDE
        self.ensure_one()

        if self.code == 'ubl_bis3':
            return bool(self._get_edi_ubl_info(journal.company_id))

        return super()._is_enabled_by_default_on_journal(journal)

    def _post_invoice_edi(self, invoices):
        # OVERRIDE
        self.ensure_one()

        if self.code not in ('ubl_2_1', 'ubl_bis3'):
            return super()._post_invoice_edi(invoices)

        ubl_info = self._get_edi_ubl_info(invoices.company_id, customer_country_code=invoices.partner_id.country_id.code)

        res = {}
        for invoice in invoices:
            xml_content, errors = ubl_info['invoice_xml_builder']._export_invoice(invoice)
            if errors:
                res[invoice] = {'error': '\n'.join(set(errors))}
            else:
                attachment = self.env['ir.attachment'].create({
                    'name': ubl_info['invoice_filename'](invoice),
                    'raw': xml_content.encode(),
                    'res_model': 'account.move',
                    'res_id': invoice.id,
                    'mimetype': 'application/xml'
                })
                res[invoice] = {'success': True, 'attachment': attachment}

        return res

    def _is_embedding_to_invoice_pdf_needed(self, invoice):
        # OVERRIDE
        self.ensure_one()

        if self.code in ('ubl_2_1', 'ubl_bis3'):
            ubl_info = self._get_edi_ubl_info(invoice.company_id, customer_country_code=invoice.partner_id.country_id.code)
            return (ubl_info or {}).get('invoice_embed_to_pdf', False)

        return super()._is_embedding_to_invoice_pdf_needed(invoice)
