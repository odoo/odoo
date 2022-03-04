# -*- coding: utf-8 -*-

from odoo import api, models, fields, tools, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr, is_html_empty, str2bool
from odoo.tests.common import Form
from odoo.exceptions import RedirectWarning, UserError, ValidationError

from datetime import datetime
from lxml import etree
from PyPDF2 import PdfFileReader
import base64
import markupsafe

import io

import logging

_logger = logging.getLogger(__name__)

DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'

# mapping used at export and import
UOM_TO_UNECE_CODE = {
    'Units': 'C62',
    'Dozens': 'DZN',
    'g': 'GRM',
    'oz': 'ONZ',
    'lb': 'LBR',
    'kg': 'KGM',
    't': 'TNE',
    'Hours': 'HUR',
    'Days': 'DAY',
    'mi': 'SMI',
    'cm': 'CMT',
    'in': 'INH',
    'ft': 'FOT',
    'm': 'MTR',
    'km': 'KTM',
    'in³': 'INQ',
    'fl oz (US)': 'OZA',
    'qt (US)': 'QT',
    'L': 'LTR',
    'gal (US)': 'GLL',
    'ft³': 'FTQ',
    'm³': 'MTQ',
}

class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _post_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != 'facturx_2_2':
            return super()._post_invoice_edi(invoices, test_mode)
        res = {}
        for invoice in invoices:
            attachment = self._export_facturx(invoice)
            res[invoice] = {'success': True, 'attachment': attachment}
        return res

    def _is_embedding_to_invoice_pdf_needed(self):
        # OVERRIDE
        self.ensure_one()
        return True if self.code == 'facturx_2_2' else super()._is_embedding_to_invoice_pdf_needed()

    def _get_embedding_to_invoice_pdf_values(self, invoice):
        values = super()._get_embedding_to_invoice_pdf_values(invoice)
        if values and self.code == 'facturx_2_2':
            values['name'] = 'factur-x.xml'
        return values

    def _prepare_invoice_report(self, pdf_writer, edi_document):
        self.ensure_one()
        if self.code != 'facturx_2_2':
            return super()._prepare_invoice_report(pdf_writer, edi_document)
        if not edi_document.attachment_id:
            return

        pdf_writer.embed_odoo_attachment(edi_document.attachment_id, subtype='application/xml')
        if not pdf_writer.is_pdfa and str2bool(
                self.env['ir.config_parameter'].sudo().get_param('edi.use_pdfa', 'False')):
            try:
                pdf_writer.convert_to_pdfa()
            except Exception as e:
                _logger.exception("Error while converting to PDF/A: %s", e)
            metadata_template = self.env.ref('account_edi_facturx_en16931.account_invoice_pdfa_3_facturx_metadata_22',
                                             raise_if_not_found=False)
            if metadata_template:
                pdf_writer.add_file_metadata(metadata_template._render({
                    'title': edi_document.move_id.name,
                    'date': fields.Date.context_today(self),
                }).encode())

    def cleanup_xml_content(self, xml_content):
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.fromstring(xml_content, parser=parser)

        def cleanup_node(parent_node, node):
            # Clean children nodes recursively.
            for child_node in node:
                cleanup_node(node, child_node)

            # Remove empty node.
            if parent_node is not None and not len(node) and not (node.text or '').strip():
                parent_node.remove(node)

        cleanup_node(None, tree)

        return etree.tostring(tree, pretty_print=True, encoding='unicode')

    def _export_invoice_constraints(self, vals):
        return {
            # [BR-08]-An Invoice shall contain the Seller postal address (BG-5).
            # [BR-09]-The Seller postal address (BG-5) shall contain a Seller country code (BT-40).
            'seller_postal_address': self._check_required_fields(
                vals['record']['company_id']['partner_id'], ['zip', 'street', 'city', 'country_id']
            ),
            # [BR-DE-9] The element "Buyer post code" (BT-53) must be transmitted. (only mandatory in Germany ?)
            'buyer_postal_address': self._check_required_fields(
                vals['record']['commercial_partner_id'], ['zip', 'street', 'city', 'country_id']
            ),
            # [BR-CO-26]-In order for the buyer to automatically identify a supplier, the Seller identifier (BT-29),
            # the Seller legal registration identifier (BT-30) and/or the Seller VAT identifier (BT-31) shall be present.
            'seller_identifier': self._check_required_fields(
                vals['record']['company_id'], ['vat', 'siret']
            ),
            # [BR-DE-1] An Invoice must contain information on "PAYMENT INSTRUCTIONS" (BG-16)
            # first check that a partner_bank_id exists, then check that there is an account number
            'seller_payment_instructions_1': self._check_required_fields(
                vals['record'], 'partner_bank_id'
            ),
            'seller_payment_instructions_2': self._check_required_fields(
                vals['record']['partner_bank_id'], 'sanitized_acc_number'
            ),
            # [BR-DE-15] The element "Buyer reference" (BT-10) must be transmitted
            # (required only for certain buyers in France when using Chorus pro, it's the "service executant")
            'buyer_reference': self._check_required_fields(
                vals['record']['commercial_partner_id'], 'ref'
            ),
            # [BR-DE-6] The element "Seller contact telephone number" (BT-42) must be transmitted.
            'seller_phone': self._check_required_fields(
                vals['record']['company_id']['partner_id'], ['phone', 'mobile'],
            ),
            # [BR-DE-7] The element "Seller contact email address" (BT-43) must be transmitted.
            'seller_email': self._check_required_fields(
                vals['record']['company_id'], 'email'
            ),
            # [BR-CO-04]-Each Invoice line (BG-25) shall be categorized with an Invoiced item VAT category code (BT-151).
            'tax_invoice_line': self._check_required_tax(vals),
            # [BR-IC-02]-An Invoice that contains an Invoice line (BG-25) where the Invoiced item VAT category code (BT-151)
            # is "Intra-community supply" shall contain the Seller VAT Identifier (BT-31) or the Seller tax representative
            # VAT identifier (BT-63) and the Buyer VAT identifier (BT-48).
            'intracom_seller_vat': self._check_required_fields(vals['record']['company_id'], 'vat') if vals['intracom_delivery'] else None,
            'intracom_buyer_vat': self._check_required_fields(vals['record']['partner_id'], 'vat') if vals['intracom_delivery'] else None,
        }

    def _check_constraints(self, constraints):
        return [x for x in constraints.values() if x]

    def _check_required_fields(self, record, field_names):
        if not isinstance(field_names, list):
            field_names = [field_names]

        field_names_copy = field_names.copy()
        for field_name in field_names:
            if field_name not in record._fields:
                field_names.remove(field_name)
        if not field_names:
            raise ValueError(f"The record: {record} do not have any of the fields: {field_names_copy}")

        has_values = any(record[field_name] for field_name in field_names)
        if has_values:
            return

        display_field_names = record.fields_get(field_names)
        if len(field_names) == 1:
            display_field = f"'{display_field_names[field_names[0]]['string']}'"
            return _("The field %s is required on %s.", display_field, record.display_name)
        else:
            display_fields = ', '.join(f"'{display_field_names[x]['string']}'" for x in display_field_names)
            return _("At least one of the following fields %s is required on %s.", display_fields, record.display_name)

    def _check_required_tax(self, vals):
        for line_vals in vals['invoice_line_vals_list']:
            line = line_vals['line']
            if not vals['tax_details']['invoice_line_tax_details'][line]['tax_details']:
                return _("You should include at least one tax per invoice line. [BR-CO-04]-Each Invoice line (BG-25) "
                         "shall be categorized with an Invoiced item VAT category code (BT-151).")

    def get_uom_info(self, line):
        # list of codes: https://docs.peppol.eu/poacc/billing/3.0/codelist/UNECERec20/
        # or https://unece.org/fileadmin/DAM/cefact/recommendations/bkup_htm/add2c.htm (sorted by letter)
        # First attempt to cover most cases: convert units to their reference but then
        # Problem: if we buy 1 dozen desks at 1000$/dozen, then in facturx, net price per product
        # is marked as 1000$ but quantity is 12 units and lineTotalAmount is 1000$ != 12*1000$ ...
        # Only solution is to have a big dictionnary mapping the units and the unit codes
        return UOM_TO_UNECE_CODE.get(line.product_uom_id.name, None)

    def get_tax_info(self, invoice, tax):
        """
        Source: doc of Peppol (but the CEF norm is also used by factur-x, yet not detailed)
        https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/cac-TaxTotal/cac-TaxSubtotal/cac-TaxCategory/cbc-TaxExemptionReasonCode/
        https://docs.peppol.eu/poacc/billing/3.0/codelist/vatex/

        :returns: (tax_category_code, tax_exemption_reason_code, tax_exemption_reason)
        """
        # TODO: this needs to be improved but no means to say what the tax_reason is
        # if invoice.narration:
        #    if 'VATEX-EU-O' in invoice.narration:
        #        return 'O', 'VATEX-EU-O', 'Not subject to VAT'
        #    if 'VATEX-EU-AE' in invoice.narration:
        #        return 'AE', 'VATEX-EU-AE', 'Reverse charge'
        #    if 'VATEX-EU-D' in invoice.narration:
        #        return 'E', 'VATEX-EU-D', 'Intra-Community acquisition from second hand means of transport'
        #    if 'VATEX-EU-I' in invoice.narration:
        #        return 'E', 'VATEX-EU-I', 'Intra-Community acquisition of works of art'
        #    if 'VATEX-EU-J' in invoice.narration:
        #        return 'E', 'VATEX-EU-J', 'Intra-Community acquisition of collectors items and antiques'
        #    if 'VATEX-EU-F' in invoice.narration:
        #        return 'E', 'VATEX-EU-F', 'Intra-Community acquisition of second hand goods'

        customer_country = invoice.partner_id.country_id
        if customer_country.code == 'FR':
            if not tax or tax.amount == 0:
                if invoice.narration and 'DEBOURS' in invoice.narration:  # https://www.legifiscal.fr/tva/tva-francaise/regimes-specifiques/debours-tva.html
                    return 'E', None, 'DEBOURS'
                else:
                    return 'E', None, 'Articles 226 items 11 to 15 Directive 2006/112/EN'  # in theory, you should indicate the precise the article
            else:
                return 'S', None, None  # TVA standard

        if customer_country.code == 'ES':
            if customer_country.zip[:2] in ['35', '38']:
                return 'L', None, 'Canary Islands'
            if customer_country.zip[:2] in ['51', '52']:
                return 'M', None, 'Ceuta or Melila'

        if customer_country not in self.env.ref('base.europe').country_ids:
            return 'G', 'VATEX-EU-G', 'Export outside the EU'
        if customer_country in self.env.ref('base.europe').country_ids:
            return 'K', 'VATEX-EU-IC', 'Intra-Community supply'

    def get_scheduled_delivery_time(self, invoice):
        # don't create a bridge only to get line.sale_line_ids.order_id.picking_ids.date_done
        # line.sale_line_ids.order_id.picking_ids.scheduled_date or line.sale_line_ids.order_id.commitment_date
        return invoice.invoice_date

    def get_invoicing_period(self, invoice):
        # get the Invoicing period (BG-14): a list of dates covered by the invoice
        # don't create a bridge to get the date range from the timesheet_ids
        return [invoice.invoice_date]

    def _export_facturx(self, invoice):

        def format_date(dt):
            # Format the date in the Factur-x standard.
            dt = dt or datetime.now()
            return dt.strftime(DEFAULT_FACTURX_DATE_FORMAT)

        def format_monetary(number, decimal_places=2):
            # Facturx requires the monetary values to be rounded to 2 decimal values
            return float_repr(number, decimal_places)

        self.ensure_one()

        # check that there is at least one tax repartition line !
        for tax in invoice.invoice_line_ids.mapped('tax_ids'):
            for line_repartition_ids in ['invoice_repartition_line_ids', 'refund_repartition_line_ids']:
                lines = tax[line_repartition_ids]
                base_line = lines.filtered(lambda x: x.repartition_type == 'base')
                if not lines - base_line:
                    raise ValidationError(
                        _("Invoice and credit note repartition should have at least one tax repartition line."))

        # Create file content.
        template_values = {
            **invoice._prepare_edi_vals_to_export(),
            'tax_details': invoice._prepare_edi_tax_details(),
            'format_date': format_date,
            'format_monetary': format_monetary,
            'is_html_empty': is_html_empty,
            'scheduled_delivery_time': self.get_scheduled_delivery_time(invoice),
            'intracom_delivery': False,
        }

        errors = []
        # data used for IncludedSupplyChainTradeLineItem / SpecifiedLineTradeSettlement
        for line_vals in template_values['invoice_line_vals_list']:
            line = line_vals['line']
            uom_info = self.get_uom_info(line)
            if not uom_info:
                errors.append(_("The unit of measure '%s' could not be matched with a standard Factur-x code." % line.product_uom_id.name))
            line_vals['uom_code'] = uom_info or line.product_uom_id.name
            # data used for IncludedSupplyChainTradeLineItem / SpecifiedLineTradeSettlement / ApplicableTradeTax
            for tax_detail_vals in template_values['tax_details']['invoice_line_tax_details'][line]['tax_details'].values():
                tax = tax_detail_vals['tax']
                tax_detail_vals['tax_category_code'] = self.get_tax_info(invoice, tax)[0]

        # data used for ApplicableHeaderTradeSettlement / ApplicableTradeTax (at the end of the xml)
        for tax_detail_vals in template_values['tax_details']['tax_details'].values():
            tax = tax_detail_vals['tax']
            tax_amount = tax_detail_vals['tax_amount']
            tax_detail_vals['tax_amount'] = -tax_amount if tax_amount != 0 else tax_amount
            tax_category_code, tax_exemption_reason_code, tax_exemption_reason = self.get_tax_info(invoice, tax)
            tax_detail_vals['tax_category_code'] = tax_category_code
            tax_detail_vals['tax_exemption_reason_code'] = tax_exemption_reason_code
            tax_detail_vals['tax_exemption_reason'] = tax_exemption_reason

            if tax_category_code == 'K':
                template_values['intracom_delivery'] = True
            # [BR - IC - 11] - In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14) shall not be blank.
            if tax_category_code == 'K' and not template_values['scheduled_delivery_time']:
                date_range = self.get_invoicing_period(invoice)
                template_values['billing_start'] = min(date_range)
                template_values['billing_end'] = max(date_range)

        # check the constraints
        errors += self._check_constraints(self._export_invoice_constraints(template_values))
        if len(template_values['tax_details']['tax_details']) == 0:
            errors.append("You should include at least one tax on each line.")
        for line in invoice.line_ids:
            for tax in line.tax_ids:
                invoice_repartition_line_ids = tax.invoice_repartition_line_ids
                refund_repartition_line_ids = tax.refund_repartition_line_ids
                if not invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax') or \
                        not refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax'):
                    errors.append("You should use taxes with at least one tax repartition line.")
        # Chatter
        if errors:
            invoice.with_context(no_new_invoice=True).message_post(
                body=_("Warning, errors occured while creating the factur-x document. The receiver might refuse it.")
                     + '<p>' + "\n".join(errors) + '<p>',
            )

        xml_content = b"<?xml version='1.0' encoding='UTF-8'?>\n"
        template = self.env.ref('account_edi_facturx_en16931.account_invoice_facturx_export_22')
        body = template._render(template_values)
        xml_content += self.cleanup_xml_content(body).encode('utf-8')
        return self.env['ir.attachment'].create({
            'name': 'factur-x.xml',
            'res_model': 'account.move',  # TODO: remove line
            'res_id': invoice.id,  # TODO: remove line
            'datas': base64.encodebytes(xml_content),
            'mimetype': 'application/xml'
        })

    def _is_facturx(self, filename, tree):
        return self.code == 'facturx_2_2' and tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice'

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self._is_facturx(filename, tree):
            return self._import_facturx(tree, self.env['account.move'])
        return super()._create_invoice_from_xml_tree(filename, tree)

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self._is_facturx(filename, tree):
            return self._import_facturx(tree, invoice)
        return super()._update_invoice_from_xml_tree(filename, tree, invoice)

    def _import_facturx(self, tree, invoice):
        """ Decodes a factur-x invoice into an invoice.

        :param tree:    the factur-x tree to decode.
        :param invoice: the invoice to update or an empty recordset.
        :returns:       the invoice where the factur-x data was imported.
        """

        def _find_value(xpath, element=tree):
            return self._find_value(xpath, element, tree.nsmap)

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
        with Form(invoice.with_context(default_move_type=default_move_type)) as invoice_form:
            partner_type = invoice_form.journal_id.type == 'purchase' and 'SellerTradeParty' or 'BuyerTradeParty'
            invoice_form.partner_id = self._retrieve_partner(
                name=_find_value(f"//ram:{partner_type}/ram:Name"),
                mail=_find_value(f"//ram:{partner_type}//ram:URIID[@schemeID='SMTP']"),
                vat=_find_value(f"//ram:{partner_type}/ram:SpecifiedTaxRegistration/ram:ID"),
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
                    currency = self._retrieve_currency(currency_str)
                    if currency and not currency.active:
                        error_msg = _(
                            'The currency (%s) of the document you are uploading is not active in this database.\n'
                            'Please activate it before trying again to import.', currency.name)
                        error_action = {
                            'view_mode': 'form',
                            'res_model': 'res.currency',
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'res_id': currency.id,
                            'views': [[False, 'form']]
                        }
                        raise RedirectWarning(error_msg, error_action, _('Display the currency'))
                    invoice_form.currency_id = currency

                    # Store xml total amount.
                    amount_total_import = total_amount * refund_sign

            # Date.
            elements = tree.xpath('//rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString', namespaces=tree.nsmap)
            if elements:
                date_str = elements[0].text
                date_obj = datetime.strptime(date_str, DEFAULT_FACTURX_DATE_FORMAT)
                invoice_form.invoice_date = date_obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

            # Due date.
            elements = tree.xpath('//ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString',
                                  namespaces=tree.nsmap)
            if elements:
                date_str = elements[0].text
                date_obj = datetime.strptime(date_str, DEFAULT_FACTURX_DATE_FORMAT)
                invoice_form.invoice_date_due = date_obj.strftime(DEFAULT_SERVER_DATE_FORMAT)

            # Invoice lines.
            elements = tree.xpath('//ram:IncludedSupplyChainTradeLineItem', namespaces=tree.nsmap)
            if elements:
                for element in elements:
                    with invoice_form.invoice_line_ids.new() as invoice_line_form:

                        # Sequence.
                        line_elements = element.xpath('.//ram:AssociatedDocumentLineDocument/ram:LineID',
                                                      namespaces=tree.nsmap)
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
                        line_elements = element.xpath('.//ram:SpecifiedLineTradeDelivery/ram:BilledQuantity',
                                                      namespaces=tree.nsmap)
                        if line_elements:
                            uom_read = line_elements[0].attrib['unitCode']
                            uom_infered = [odoo_uom for odoo_uom, uom_unece in UOM_TO_UNECE_CODE.items() if uom_unece == uom_read]
                            if uom_infered:
                                uom = self.env['uom.uom'].search([('name', '=', uom_infered[0])], limit=1)
                                if uom:
                                    invoice_line_form.product_uom_id = uom
                            invoice_line_form.quantity = float(line_elements[0].text)

                        # Price Unit.
                        line_elements = element.xpath('.//ram:GrossPriceProductTradePrice/ram:ChargeAmount',
                                                      namespaces=tree.nsmap)
                        if line_elements:
                            quantity_elements = element.xpath('.//ram:GrossPriceProductTradePrice/ram:BasisQuantity',
                                                              namespaces=tree.nsmap)
                            if quantity_elements:
                                invoice_line_form.price_unit = float(line_elements[0].text) / float(quantity_elements[0].text)
                            else:
                                invoice_line_form.price_unit = float(line_elements[0].text)
                        else:
                            line_elements = element.xpath('.//ram:NetPriceProductTradePrice/ram:ChargeAmount',
                                                          namespaces=tree.nsmap)
                            if line_elements:
                                quantity_elements = element.xpath('.//ram:NetPriceProductTradePrice/ram:BasisQuantity',
                                                                  namespaces=tree.nsmap)
                                if quantity_elements:
                                    invoice_line_form.price_unit = float(line_elements[0].text) / float(quantity_elements[0].text)
                                else:
                                    invoice_line_form.price_unit = float(line_elements[0].text)
                        # Discount. /!\ as no percent discount can be set on a line, need to infer the percentage
                        # from the amount of the actual amount of the discount (the allowance charge)
                        line_elements = element.xpath('.//ram:SpecifiedTradeAllowanceCharge/ram:ActualAmount',
                                                      namespaces=tree.nsmap)
                        if line_elements:
                            discount_amount = float(line_elements[0].text)
                            invoice_line_form.discount = (discount_amount/invoice_line_form.price_unit)*100

                        # Taxes
                        tax_element = element.xpath(
                            './/ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax/ram:RateApplicablePercent',
                            namespaces=tree.nsmap)
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
