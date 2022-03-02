# -*- coding: utf-8 -*-

from odoo import api, models, fields, tools, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, float_repr, str2bool
from odoo.tests.common import Form
from odoo.exceptions import UserError

from datetime import datetime
from lxml import etree
from PyPDF2 import PdfFileReader
import base64

import io

import logging

_logger = logging.getLogger(__name__)


DEFAULT_FACTURX_DATE_FORMAT = '%Y%m%d'


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _is_compatible_with_journal(self, journal):
        self.ensure_one()
        res = super()._is_compatible_with_journal(journal)
        if self.code != 'facturx_1_0_05':
            return res
        return journal.type == 'sale'

    def _post_invoice_edi(self, invoices, test_mode=False):
        self.ensure_one()
        if self.code != 'facturx_1_0_05':
            return super()._post_invoice_edi(invoices, test_mode=test_mode)
        res = {}
        for invoice in invoices:
            attachment = self._export_facturx(invoice)
            # TODO: success: True, can be removed
            res[invoice] = {'success': True, 'attachment': attachment}
        return res

    def _is_embedding_to_invoice_pdf_needed(self):
        # OVERRIDE
        self.ensure_one()
        return True if self.code == 'facturx_1_0_05' else super()._is_embedding_to_invoice_pdf_needed()

    def _get_embedding_to_invoice_pdf_values(self, invoice):
        values = super()._get_embedding_to_invoice_pdf_values(invoice)
        if values and self.code == 'facturx_1_0_05':
            values['name'] = 'factur-x.xml'
        return values

    def _prepare_invoice_report(self, pdf_writer, edi_document):
        self.ensure_one()
        if self.code != 'facturx_1_0_05':
            return super()._prepare_invoice_report(pdf_writer, edi_document)
        if not edi_document.attachment_id:
            return

        pdf_writer.embed_odoo_attachment(edi_document.attachment_id, subtype='application/xml')
        if not pdf_writer.is_pdfa and str2bool(self.env['ir.config_parameter'].sudo().get_param('edi.use_pdfa', 'False')):
            try:
                pdf_writer.convert_to_pdfa()
            except Exception as e:
                _logger.exception("Error while converting to PDF/A: %s", e)
            metadata_template = self.env.ref('account_edi_facturx.account_invoice_pdfa_3_facturx_metadata', raise_if_not_found=False)
            if metadata_template:
                pdf_writer.add_file_metadata(metadata_template._render({
                    'title': edi_document.move_id.name,
                    'date': fields.Date.context_today(self),
                }))

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
                vals['record']['company_id'], ['phone', 'mobile'],
            ),
            # [BR-DE-7] The element "Seller contact email address" (BT-43) must be transmitted.
            'seller_email': self._check_required_fields(
                vals['record']['company_id'], 'email'
            ),
            # [BR-CO-04]-Each Invoice line (BG-25) shall be categorized with an Invoiced item VAT category code (BT-151).
            'tax_invoice_line': self._check_required_tax(vals),
        }

    def _check_constraints(self, constraints):
        return [x for x in constraints.values() if x]

    def _check_required_fields(self, record, field_names):
        if not isinstance(field_names, list):
            field_names = [field_names]

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
        for line_values in vals['invoice_line_values']:
            if not line_values['tax_details']:
                return _("You should include at least one tax per invoice line. [BR-CO-04]-Each Invoice line (BG-25) "
                         "shall be categorized with an Invoiced item VAT category code (BT-151).")

    def _export_facturx(self, invoice):

        def format_date(dt):
            # Format the date in the Factur-x standard.
            dt = dt or datetime.now()
            return dt.strftime(DEFAULT_FACTURX_DATE_FORMAT)

        def format_monetary(number, decimal_places=2):
            # Facturx requires the monetary values to be rounded to 2 decimal values
            return float_repr(number, decimal_places)

        def get_uom_info(line):
            # For instance: 1 Dozen = 12 Units
            qty = line.quantity
            uom = line.product_uom_id
            uom_category = uom.category_id.name
            if uom_category == 'Unit':
                uom_code = 'C62'  # Unit
            elif uom_category == 'Weight':
                uom_code = 'KGM'  # kg
            elif uom_category == 'Working Time':
                # /!\ One day in Odoo is 8 hours, while it's 24 hours
                # Alternatively, one could use 'E49' = 'working day'
                uom_code = 'DAY'  # Day
                qty = qty/3
            elif uom_category == 'Length / Distance':
                uom_code = 'MTR'  # m
            elif uom_category == 'Volume':
                uom_code = 'LTR'  # L
            else:
                raise UserError("uom_category could not be matched")

            ref_quantity = uom.factor * qty
            return {
                'ref_quantity': float_repr(ref_quantity, 3),
                'uom_code': uom_code,
            }

        def get_tax_category_code(invoice, tax):
            # TODO: still lacks the case 'AE'='autoliquidation de TVA' not caused by intracom delivery
            #  but not possible to distinguish here...
            customer_country = invoice.partner_id.country_id

            if customer_country.code == 'FR':
                if not tax or tax.amount == 0:
                    return 'E'  # Exempted of TVA
                else:
                    return 'S'  # TVA standard

            if customer_country.code == 'ES':
                if customer_country.zip[:2] in ['35', '38']:
                    return 'L'  # Canary Islands
                if customer_country.zip[:2] in ['51', '52']:
                    return 'M'  # Ceuta or Melila

            if customer_country not in self.env.ref('base.europe').country_ids:
                return 'G'  # export outside UE
            if customer_country in self.env.ref('base.europe').country_ids:
                return 'K'  # intracom deliveries

        def get_tax_exemption_reason(code, invoice, tax):
            # Source: doc of Peppol (but the CEF norm is also used by factur-x, yet not detailed)
            # https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/cac-TaxTotal/cac-TaxSubtotal/cac-TaxCategory/cbc-TaxExemptionReasonCode/
            if code == 'G':
                return 'VATEX-EU-G', "Export outside the EU"
            elif code == 'O':
                return 'VATEX-EU-O', "Not subject to VAT"
            elif code == 'K':
                return 'VATEX-EU-IC', "Intra-Community supply"
            elif code == 'AE':
                return 'VATEX-EU-AE', "Reverse charge"
            elif code == 'E':
                # pick one of those: ('VATEX-EU-D', "Intra-Community acquisition from second hand means of transport") \
                # ('VATEX-EU-F', "Intra-Community acquisition of second hand goods"), \
                # ('VATEX-EU-I', "Intra-Community acquisition of works of art"), \
                # ('VATEX-EU-J', "Intra-Community acquisition of collectors items and antiques")
                # No means to know which one to pick -> default: VATEX-EU-F
                return 'VATEX-EU-F', "Intra-Community acquisition of second hand goods"
            # No exemption reason associated to this code
            else:
                return None, None

        def get_scheduled_delivery_time(invoice):
            # in factur-x, we can only specify ONE scheduled delivery date, while multiple could exist (one/aml)...
            for line in invoice.line_ids:
                if line.sale_line_ids and line.sale_line_ids.order_id and line.sale_line_ids.order_id.picking_ids:
                    return line.sale_line_ids.order_id.picking_ids.scheduled_date
            return None

        self.ensure_one()
        # Create file content.
        template_values = {
            'record': invoice,
            'format_date': format_date,
            'format_monetary': format_monetary,
            'invoice_line_values': [],
            'scheduled_delivery_time': get_scheduled_delivery_time(invoice),
        }

        # Tax lines.
        aggregated_taxes_details = {}
        for line in invoice.line_ids.filtered('tax_line_id'):  # TODO, tax_line_id or tax_ids ? Annoying because if 0% tax, no tax_line_id...
            tax_category_code = get_tax_category_code(invoice, line.tax_line_id)
            aggregated_taxes_details[line.tax_line_id.id] = {
                'line': line,
                'tax_amount': -line.amount_currency if line.currency_id else -line.balance,
                'tax_base_amount': 0.0,
                'tax_category_code': tax_category_code,
                'tax_exemption_reason_code': get_tax_exemption_reason(tax_category_code, invoice, line.tax_line_id)[0],
        }

        if not aggregated_taxes_details:
            raise Exception("No aggregated tax details !")

        # Invoice lines.
        for i, line in enumerate(invoice.invoice_line_ids.filtered(lambda l: not l.display_type)):
            price_unit_with_discount = line.price_unit * (1 - (line.discount / 100.0))

            tmp = line.tax_ids.with_context(force_sign=line.move_id._get_tax_force_sign())
            taxes_res = tmp.compute_all(
                price_unit_with_discount,
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=invoice.partner_id,
                is_refund=line.move_id.move_type in ('in_refund', 'out_refund'),
            )
            #TODO When a 0% tax is applied on a line, it is not returned by the compute_all()

            line_template_values = {
                'line': line,
                'index': i + 1,
                'tax_details': [],
                'net_price_subtotal': taxes_res['total_excluded'],
                'uom_code': get_uom_info(line)['uom_code'],
                'ref_quantity': get_uom_info(line)['ref_quantity'],
            }

            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                tax_category_code = get_tax_category_code(invoice, tax)
                line_template_values['tax_details'].append({
                    'tax': tax,
                    'tax_amount': tax_res['amount'],
                    'tax_base_amount': tax_res['base'],
                    'tax_category_code': tax_category_code,
                    'tax_exemption_reason_code': get_tax_exemption_reason(tax_category_code, invoice, tax)[0],
                })

                if tax.id in aggregated_taxes_details:
                    aggregated_taxes_details[tax.id]['tax_base_amount'] += tax_res['base']

            template_values['invoice_line_values'].append(line_template_values)

        template_values['tax_details'] = list(aggregated_taxes_details.values())

        errors = self._check_constraints(self._export_invoice_constraints(template_values))
        for line in invoice.line_ids:
            for tax in line.tax_ids:
                invoice_repartition_line_ids = tax.invoice_repartition_line_ids
                refund_repartition_line_ids = tax.refund_repartition_line_ids
                if not invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax') or \
                        not refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax'):
                    errors.append("Use taxes with at least one tax repartition line.")
        # Chatter
        if errors:
            invoice.with_context(no_new_invoice=True).message_post(
                body=_("Warning, errors occured while creating the factur-x document. The receiver might refuse it.")
                     + '<p>' + "\n".join(errors) + '<p>',
            )
            #raise UserError("Factur-x: ", errors)

        template = self.env.ref('account_edi_facturx.account_invoice_facturx_export')
        xml_content = "<?xml version='1.0' encoding='UTF-8'?>\n\n" + self.cleanup_xml_content(template._render(template_values))
        return self.env['ir.attachment'].create({
            'name': 'factur-x.xml',
            'res_model': 'account.move',  #TODO: remove line (otherwise, xml appears in chatter when we confirm the invoice
            'res_id': invoice.id,  #TODO: remove line, same
            'datas': base64.encodebytes(bytes(xml_content, 'utf-8')),
            'mimetype': 'application/xml'
        })

    def _is_facturx(self, filename, tree):
        return self.code == 'facturx_1_0_05' and tree.tag == '{urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100}CrossIndustryInvoice'

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
            self_ctx = self.with_company(invoice.company_id)

            # Partner (first step to avoid warning 'Warning! You must first select a partner.').
            partner_type = invoice_form.journal_id.type == 'purchase' and 'SellerTradeParty' or 'BuyerTradeParty'
            invoice_form.partner_id = self_ctx._retrieve_partner(
                name=self._find_value('//ram:' + partner_type + '/ram:Name', tree, namespaces=tree.nsmap),
                mail=self._find_value('//ram:' + partner_type + '//ram:URIID[@schemeID=\'SMTP\']', tree, namespaces=tree.nsmap),
                vat=self._find_value('//ram:' + partner_type + '/ram:SpecifiedTaxRegistration/ram:ID', tree, namespaces=tree.nsmap),
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
                if elements[0].attrib.get('currencyID'):
                    currency_str = elements[0].attrib['currencyID']
                    currency = self.env.ref('base.%s' % currency_str.upper(), raise_if_not_found=False)
                    if currency != self.env.company.currency_id and currency.active:
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
            elements = tree.xpath('//ram:SpecifiedTradePaymentTerms/ram:DueDateDateTime/udt:DateTimeString', namespaces=tree.nsmap)
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
                        line_elements = element.xpath('.//ram:AssociatedDocumentLineDocument/ram:LineID', namespaces=tree.nsmap)
                        if line_elements:
                            invoice_line_form.sequence = int(line_elements[0].text)

                        # Product.
                        name = _find_value('.//ram:SpecifiedTradeProduct/ram:Name', element)
                        if name:
                            invoice_line_form.name = name
                        invoice_line_form.product_id = self_ctx._retrieve_product(
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
                            tax = self_ctx._retrieve_tax(
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
