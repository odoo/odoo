# -*- coding: utf-8 -*-

from odoo import _, models, Command
from odoo.tools import float_repr
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang

from zeep import Client

# -------------------------------------------------------------------------
# UNIT OF MEASURE
# -------------------------------------------------------------------------
UOM_TO_UNECE_CODE = {
    'uom.product_uom_unit': 'C62',
    'uom.product_uom_dozen': 'DZN',
    'uom.product_uom_kgm': 'KGM',
    'uom.product_uom_gram': 'GRM',
    'uom.product_uom_day': 'DAY',
    'uom.product_uom_hour': 'HUR',
    'uom.product_uom_ton': 'TNE',
    'uom.product_uom_meter': 'MTR',
    'uom.product_uom_km': 'KMT',
    'uom.product_uom_cm': 'CMT',
    'uom.product_uom_litre': 'LTR',
    'uom.product_uom_cubic_meter': 'MTQ',
    'uom.product_uom_lb': 'LBR',
    'uom.product_uom_oz': 'ONZ',
    'uom.product_uom_inch': 'INH',
    'uom.product_uom_foot': 'FOT',
    'uom.product_uom_mile': 'SMI',
    'uom.product_uom_floz': 'OZA',
    'uom.product_uom_qt': 'QT',
    'uom.product_uom_gal': 'GLL',
    'uom.product_uom_cubic_inch': 'INQ',
    'uom.product_uom_cubic_foot': 'FTQ',
}

# -------------------------------------------------------------------------
# ELECTRONIC ADDRESS SCHEME (EAS), see https://docs.peppol.eu/poacc/billing/3.0/codelist/eas/
# -------------------------------------------------------------------------
COUNTRY_EAS = {
    'HU': 9910,
    'AT': 9915,
    'ES': 9920,
    'AD': 9922,
    'AL': 9923,
    'BA': 9924,
    'BE': 9925,
    'BG': 9926,
    'CH': 9927,
    'CY': 9928,
    'CZ': 9929,
    'DE': 9930,
    'DK': '0184',
    'EE': 9931,
    'GB': 9932,
    'GR': 9933,
    'HR': 9934,
    'IE': 9935,
    'IT': '0211',
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
    'NO': '0192',
    'SG': '0195',
    'AU': '0151',
    'NZ': '0088',
    'FI': '0213',
}


class AccountEdiCommon(models.AbstractModel):
    _name = "account.edi.common"
    _description = "Common functions for EDI documents: generate the data, the constraints, etc"

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def format_float(self, amount, precision_digits):
        if amount is None:
            return None
        return float_repr(float_round(amount, precision_digits), precision_digits)

    def _get_uom_unece_code(self, line):
        """
        list of codes: https://docs.peppol.eu/poacc/billing/3.0/codelist/UNECERec20/
        or https://unece.org/fileadmin/DAM/cefact/recommendations/bkup_htm/add2c.htm (sorted by letter)
        """
        xmlid = line.product_uom_id.get_external_id()
        if xmlid and line.product_uom_id.id in xmlid:
            return UOM_TO_UNECE_CODE.get(xmlid[line.product_uom_id.id], 'C62')
        return 'C62'

    # -------------------------------------------------------------------------
    # TAXES
    # -------------------------------------------------------------------------

    def _validate_taxes(self, invoice):
        """ Validate the structure of the tax repartition lines (invalid structure could lead to unexpected results)
        """
        for tax in invoice.invoice_line_ids.tax_ids:
            try:
                tax._validate_repartition_lines()
            except ValidationError as e:
                error_msg = _("Tax '%s' is invalid: %s", tax.name, e.args[0])  # args[0] gives the error message
                raise ValidationError(error_msg)

    def _get_tax_unece_codes(self, invoice, tax):
        """
        Source: doc of Peppol (but the CEF norm is also used by factur-x, yet not detailed)
        https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice/cac-TaxTotal/cac-TaxSubtotal/cac-TaxCategory/cbc-TaxExemptionReasonCode/
        https://docs.peppol.eu/poacc/billing/3.0/codelist/vatex/
        https://docs.peppol.eu/poacc/billing/3.0/codelist/UNCL5305/
        :returns: {
            tax_category_code: str,
            tax_exemption_reason_code: str,
            tax_exemption_reason: str,
        }
        """
        def create_dict(tax_category_code=None, tax_exemption_reason_code=None, tax_exemption_reason=None):
            return {
                'tax_category_code': tax_category_code,
                'tax_exemption_reason_code': tax_exemption_reason_code,
                'tax_exemption_reason': tax_exemption_reason,
            }

        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.commercial_partner_id

        # add Norway, Iceland, Liechtenstein
        european_economic_area = self.env.ref('base.europe').country_ids.mapped('code') + ['NO', 'IS', 'LI']

        if customer.country_id.code == 'ES' and customer.zip:
            if customer.zip[:2] in ('35', '38'):  # Canary
                # [BR-IG-10]-A VAT breakdown (BG-23) with VAT Category code (BT-118) "IGIC" shall not have a VAT
                # exemption reason code (BT-121) or VAT exemption reason text (BT-120).
                return create_dict(tax_category_code='L')
            if customer.zip[:2] in ('51', '52'):
                return create_dict(tax_category_code='M')  # Ceuta & Mellila

        # see: https://anskaffelser.dev/postaward/g3/spec/current/billing-3.0/norway/#_value_added_tax_norwegian_mva
        if customer.country_id.code == 'NO':
            if tax.amount == 25:
                return create_dict(tax_category_code='S', tax_exemption_reason=_('Output VAT, regular rate'))
            if tax.amount == 15:
                return create_dict(tax_category_code='S', tax_exemption_reason=_('Output VAT, reduced rate, middle'))
            if tax.amount == 11.11:
                return create_dict(tax_category_code='S', tax_exemption_reason=_('Output VAT, reduced rate, raw fish'))
            if tax.amount == 12:
                return create_dict(tax_category_code='S', tax_exemption_reason=_('Output VAT, reduced rate, low'))

        if supplier.country_id == customer.country_id:
            if not tax or tax.amount == 0:
                # in theory, you should indicate the precise law article
                return create_dict(tax_category_code='E', tax_exemption_reason=_('Articles 226 items 11 to 15 Directive 2006/112/EN'))
            else:
                return create_dict(tax_category_code='S')  # standard VAT

        if supplier.country_id.code in european_economic_area:
            if tax.amount != 0:
                # otherwise, the validator will complain because G and K code should be used with 0% tax
                return create_dict(tax_category_code='S')
            if customer.country_id.code not in european_economic_area:
                return create_dict(
                    tax_category_code='G',
                    tax_exemption_reason_code='VATEX-EU-G',
                    tax_exemption_reason=_('Export outside the EU'),
                )
            if customer.country_id.code in european_economic_area:
                return create_dict(
                    tax_category_code='K',
                    tax_exemption_reason_code='VATEX-EU-IC',
                    tax_exemption_reason=_('Intra-Community supply'),
                )

        if tax.amount != 0:
            return create_dict(tax_category_code='S')
        else:
            return create_dict(tax_category_code='E', tax_exemption_reason=_('Articles 226 items 11 to 15 Directive 2006/112/EN'))

    def _get_tax_category_list(self, invoice, taxes):
        """ Full list: https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred5305.htm
        Subset: https://docs.peppol.eu/poacc/billing/3.0/codelist/UNCL5305/

        :param taxes:   account.tax records.
        :return:        A list of values to fill the TaxCategory foreach template.
        """
        res = []
        for tax in taxes:
            tax_unece_codes = self._get_tax_unece_codes(invoice, tax)
            res.append({
                'id': tax_unece_codes.get('tax_category_code'),
                'percent': tax.amount if tax.amount_type == 'percent' else False,
                'name': tax_unece_codes.get('tax_exemption_reason'),
                'tax_scheme_id': 'VAT',
                **tax_unece_codes,
            })
        return res

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def _check_required_fields(self, record, field_names, custom_warning_message=""):
        """
        This function check that a field exists on a record or dictionaries
        returns a generic error message if it's not the case or a custom one if specified
        """
        if not record:
            return custom_warning_message or _("The element %s is required on %s.", record, ', '.join(field_names))

        if not isinstance(field_names, list):
            field_names = [field_names]

        has_values = any(record[field_name] for field_name in field_names)
        # field is present
        if has_values:
            return

        # field is not present
        if custom_warning_message or isinstance(record, dict):
            return custom_warning_message or _("The element %s is required on %s.", record, ', '.join(field_names))

        display_field_names = record.fields_get(field_names)
        if len(field_names) == 1:
            display_field = f"'{display_field_names[field_names[0]]['string']}'"
            return _("The field %s is required on %s.", display_field, record.display_name)
        else:
            display_fields = ', '.join(f"'{display_field_names[x]['string']}'" for x in display_field_names)
            return _("At least one of the following fields %s is required on %s.", display_fields, record.display_name)

    # -------------------------------------------------------------------------
    # COMMON CONSTRAINTS
    # -------------------------------------------------------------------------

    def _invoice_constraints_common(self, invoice):
        # check that there is a tax on each line
        for line in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section')):
            if not line.tax_ids:
                return {'tax_on_line': _("Each invoice line should have at least one tax.")}
        return {}

    # -------------------------------------------------------------------------
    # Import invoice
    # -------------------------------------------------------------------------

    def _import_invoice(self, journal, filename, tree, existing_invoice=None):
        move_types, qty_factor = self._get_import_document_amount_sign(filename, tree)
        if not move_types:
            return
        if journal.type == 'purchase':
            move_type = move_types[0]
        elif journal.type == 'sale':
            move_type = move_types[1]
        else:
            return
        if existing_invoice and existing_invoice.move_type != move_type:
            # with an email alias to create account_move, first the move is created (using alias_defaults, which
            # contains move_type = 'out_invoice') then the attachment is decoded, if it represents a credit note,
            # the move type needs to be changed to 'out_refund'
            types = {move_type, existing_invoice.move_type}
            if types == {'out_invoice', 'out_refund'} or types == {'in_invoice', 'in_refund'}:
                existing_invoice.move_type = move_type
            else:
                return

        with (existing_invoice or self.env['account.move']).with_context(
            account_predictive_bills_disable_prediction=True,
            default_move_type=move_type,
            default_journal_id=journal.id,
        )._get_edi_creation() as invoice:
            logs = self._import_fill_invoice_form(journal, tree, invoice, qty_factor)

        # For UBL, we should override the computed tax amount if it is less than 0.05 different of the one in the xml.
        # In order to support use case where the tax total is adapted for rounding purpose.
        # This has to be done after the first import in order to let Odoo compute the taxes before overriding if needed.
        with invoice.with_context(account_predictive_bills_disable_prediction=True)._get_edi_creation() as invoice:
            self._correct_invoice_tax_amount(tree, invoice)
        if invoice:
            if logs:
                body = _(
                    "<strong>Format used to import the invoice: %s</strong> <p><li> %s </li></p>",
                    str(self._description), "</li><li>".join(logs)
                )
            else:
                body = _("<strong>Format used to import the invoice: %s</strong>", str(self._description))
            invoice.with_context(no_new_invoice=True).message_post(body=body)

        # === Import the embedded PDF in the xml if some are found ===

        attachments = self.env['ir.attachment']
        additional_docs = tree.findall('./{*}AdditionalDocumentReference')
        for document in additional_docs:
            attachment_name = document.find('{*}ID')
            attachment_data = document.find('{*}Attachment/{*}EmbeddedDocumentBinaryObject')
            if attachment_name is not None \
                    and attachment_data is not None \
                    and attachment_data.attrib.get('mimeCode') == 'application/pdf':
                text = attachment_data.text
                # Normalize the name of the file : some e-fff emitters put the full path of the file
                # (Windows or Linux style) and/or the name of the xml instead of the pdf.
                # Get only the filename with a pdf extension.
                name = (attachment_name.text or 'invoice').split('\\')[-1].split('/')[-1].split('.')[0] + '.pdf'
                attachment = self.env['ir.attachment'].create({
                    'name': name,
                    'res_id': invoice.id,
                    'res_model': 'account.move',
                    'datas': text + '=' * (len(text) % 3),  # Fix incorrect padding
                    'type': 'binary',
                    'mimetype': 'application/pdf',
                })
                # Upon receiving an email (containing an xml) with a configured alias to create invoice, the xml is
                # set as the main_attachment. To be rendered in the form view, the pdf should be the main_attachment.
                if invoice.message_main_attachment_id and \
                        invoice.message_main_attachment_id.name.endswith('.xml') and \
                        'pdf' not in invoice.message_main_attachment_id.mimetype:
                    invoice.message_main_attachment_id = attachment
                attachments |= attachment
        if attachments:
            invoice.with_context(no_new_invoice=True).message_post(attachment_ids=attachments.ids)

        return invoice

    def _import_retrieve_and_fill_partner(self, invoice, name, phone, mail, vat, country_code=False):
        """ Retrieve the partner, if no matching partner is found, create it (only if he has a vat and a name)
        """
        invoice.partner_id = self.env['account.edi.format']._retrieve_partner(name=name, phone=phone, mail=mail, vat=vat)
        if not invoice.partner_id and name and vat:
            partner_vals = {'name': name, 'email': mail, 'phone': phone}
            country = self.env.ref(f'base.{country_code.lower()}', raise_if_not_found=False) if country_code else False
            if country:
                partner_vals['country_id'] = country.id
            invoice.partner_id = self.env['res.partner'].create(partner_vals)
            if vat and self.env['res.partner']._run_vat_test(vat, country, invoice.partner_id.is_company):
                invoice.partner_id.vat = vat

    def _import_fill_invoice_allowance_charge(self, tree, invoice, journal, qty_factor):
        logs = []
        if '{urn:oasis:names:specification:ubl:schema:xsd' in tree.tag:
            is_ubl = True
        elif '{urn:un:unece:uncefact:data:standard:' in tree.tag:
            is_ubl = False
        else:
            return

        xpath = './{*}AllowanceCharge' if is_ubl else './{*}SupplyChainTradeTransaction/{*}ApplicableHeaderTradeSettlement/{*}SpecifiedTradeAllowanceCharge'
        allowance_charge_nodes = tree.findall(xpath)
        line_vals = []
        for allow_el in allowance_charge_nodes:
            # get the charge factor
            charge_factor = -1  # factor is -1 for discount, 1 for charge
            if is_ubl:
                charge_indicator_node = allow_el.find('./{*}ChargeIndicator')
            else:
                charge_indicator_node = allow_el.find('./{*}ChargeIndicator/{*}Indicator')
            if charge_indicator_node is not None:
                charge_factor = -1 if charge_indicator_node.text == 'false' else 1

            # get the name
            name = ""
            reason_node = allow_el.find('./{*}AllowanceChargeReason' if is_ubl else './{*}Reason')
            if reason_node is not None:
                name = reason_node.text

            # get quantity and price unit
            quantity = 1
            price_unit = 0
            amount_node = allow_el.find('./{*}Amount' if is_ubl else './{*}ActualAmount')
            base_amount_node = allow_el.find('./{*}BaseAmount' if is_ubl else './{*}BasisAmount')
            # Since there is no quantity associated for the allowance/charge on document level,
            # if we have an invoice with negative amounts, the price was multiplied by -1 and not the quantity
            # See the file in test_files: 'base-negative-inv-correction.xml' VS 'base-example.xml' for 'Insurance'
            if base_amount_node is not None:
                price_unit = float(base_amount_node.text) * charge_factor * qty_factor
                percent_node = allow_el.find('./{*}MultiplierFactorNumeric' if is_ubl else './{*}CalculationPercent')
                if percent_node is not None:
                    quantity = float(percent_node.text) / 100
            elif amount_node is not None:
                price_unit = float(amount_node.text) * charge_factor * qty_factor

            # get taxes
            tax_xpath = './{*}TaxCategory/{*}Percent' if is_ubl else './{*}CategoryTradeTax/{*}RateApplicablePercent'
            tax_ids = []
            for tax_categ_percent_el in allow_el.findall(tax_xpath):
                tax = self.env['account.tax'].search([
                    ('company_id', '=', journal.company_id.id),
                    ('amount', '=', float(tax_categ_percent_el.text)),
                    ('amount_type', '=', 'percent'),
                    ('type_tax_use', '=', journal.type),
                ], limit=1)
                if tax:
                    tax_ids += tax.ids
                else:
                    logs.append(
                        _("Could not retrieve the tax: %s %% for line '%s'.",
                            float(tax_categ_percent_el.text),
                            name)
                    )

            line_vals += [Command.create({
                'sequence': 0,  # be sure to put these lines above the 'real' invoice lines
                'name': name,
                'quantity': quantity,
                'price_unit': price_unit,
                'tax_ids': [Command.set(tax_ids)],
            })]

        invoice.write({'invoice_line_ids': line_vals})
        return logs

    def _import_fill_invoice_down_payment(self, invoice, prepaid_node, qty_factor):
        """
        DEPRECATED: removed in master
        Creates a down payment line on the invoice at import if prepaid_node (TotalPrepaidAmount in CII,
        PrepaidAmount in UBL) exists.
        qty_factor -1 if the xml is labelled as an invoice but has negative amounts -> conversion into a credit note
        needed, so we need this multiplier. Otherwise, qty_factor is 1.
        """
        if prepaid_node is not None and float(prepaid_node.text) != 0:
            invoice.write({
                'invoice_line_ids': [
                    Command.create({
                        'display_type': 'line_section',
                        'sequence': 9998,
                        'name': _("Down Payments"),
                    }),
                    Command.create({
                        'sequence': 9999,
                        'name': _("Down Payment"),
                        'price_unit': float(prepaid_node.text),
                        'quantity': qty_factor * -1,
                        'tax_ids': False,
                    }),
                ]
            })

    def _import_log_prepaid_amount(self, invoice_form, prepaid_node, qty_factor):
        """
        Log a message in the chatter at import if prepaid_node (TotalPrepaidAmount in CII, PrepaidAmount in UBL) exists.
        """
        prepaid_amount = float(prepaid_node.text) if prepaid_node is not None else 0.0
        if not invoice_form.currency_id.is_zero(prepaid_amount):
            amount = prepaid_amount * qty_factor
            formatted_amount = formatLang(self.env, amount, currency_obj=invoice_form.currency_id)
            return [
                _("A payment of %s was detected.", formatted_amount)
            ]
        return []

    def _import_fill_invoice_line_values(self, tree, xpath_dict, invoice_line, qty_factor):
        """
        Read the xml invoice, extract the invoice line values, compute the odoo values
        to fill an invoice line form: quantity, price_unit, discount, product_uom_id.

        The way of computing invoice line is quite complicated:
        https://docs.peppol.eu/poacc/billing/3.0/bis/#_calculation_on_line_level (same as in factur-x documentation)

        line_net_subtotal = ( gross_unit_price - rebate ) * (billed_qty / basis_qty) - allow_charge_amount

        with (UBL | CII):
            * net_unit_price = 'Price/PriceAmount' | 'NetPriceProductTradePrice' (mandatory) (BT-146)
            * gross_unit_price = 'Price/AllowanceCharge/BaseAmount' | 'GrossPriceProductTradePrice' (optional) (BT-148)
            * basis_qty = 'Price/BaseQuantity' | 'BasisQuantity' (optional, either below net_price node or
                gross_price node) (BT-149)
            * billed_qty = 'InvoicedQuantity' | 'BilledQuantity' (mandatory) (BT-129)
            * allow_charge_amount = sum of 'AllowanceCharge' | 'SpecifiedTradeAllowanceCharge' (same level as Price)
                ON THE LINE level (optional) (BT-136 / BT-141)
            * line_net_subtotal = 'LineExtensionAmount' | 'LineTotalAmount' (mandatory) (BT-131)
            * rebate = 'Price/AllowanceCharge' | 'AppliedTradeAllowanceCharge' below gross_price node ! (BT-147)
                "item price discount" which is different from the usual allow_charge_amount
                gross_unit_price (BT-148) - rebate (BT-147) = net_unit_price (BT-146)

        In Odoo, we obtain:
        (1) = price_unit  =  gross_price_unit / basis_qty  =  (net_price_unit + rebate) / basis_qty
        (2) = quantity  =  billed_qty
        (3) = discount (converted into a percentage)  =  100 * (1 - price_subtotal / (billed_qty * price_unit))
        (4) = price_subtotal

        Alternatively, we could also set: quantity = billed_qty/basis_qty

        WARNING, the basis quantity parameter is annoying, for instance, an invoice with a line:
            item A  | price per unit of measure/unit price: 30  | uom = 3 pieces | billed qty = 3 | rebate = 2  | untaxed total = 28
        Indeed, 30 $ / 3 pieces = 10 $ / piece => 10 * 3 (billed quantity) - 2 (rebate) = 28

        UBL ROUNDING: "the result of Item line net
            amount = ((Item net price (BT-146)÷Item price base quantity (BT-149))×(Invoiced Quantity (BT-129))
        must be rounded to two decimals, and the allowance/charge amounts are also rounded separately."
        It is not possible to do it in Odoo.

        :params tree
        :params xpath_dict dict: {
            'basis_qty': list of str,
            'gross_price_unit': str,
            'rebate': str,
            'net_price_unit': str,
            'billed_qty': str,
            'allowance_charge': str, to be used in a findall !,
            'allowance_charge_indicator': str, relative xpath from allowance_charge,
            'allowance_charge_amount': str, relative xpath from allowance_charge,
            'line_total_amount': str,
        }
        :params: invoice_line
        :params: qty_factor
        :returns: {
            'quantity': float,
            'product_uom_id': (optional) uom.uom,
            'price_unit': float,
            'discount': float,
        }
        """
        # basis_qty (optional)
        basis_qty = 1
        for xpath in xpath_dict['basis_qty']:
            basis_quantity_node = tree.find(xpath)
            if basis_quantity_node is not None:
                basis_qty = float(basis_quantity_node.text) or 1

        # gross_price_unit (optional)
        gross_price_unit = None
        gross_price_unit_node = tree.find(xpath_dict['gross_price_unit'])
        if gross_price_unit_node is not None:
            gross_price_unit = float(gross_price_unit_node.text)

        # rebate (optional)
        # Discount. /!\ as no percent discount can be set on a line, need to infer the percentage
        # from the amount of the actual amount of the discount (the allowance charge)
        rebate = 0
        rebate_node = tree.find(xpath_dict['rebate'])
        net_price_unit_node = tree.find(xpath_dict['net_price_unit'])
        if rebate_node is not None:
            rebate = float(rebate_node.text)
        elif net_price_unit_node is not None and gross_price_unit_node is not None:
            rebate = float(gross_price_unit_node.text) - float(net_price_unit_node.text)

        # net_price_unit (mandatory)
        net_price_unit = None
        if net_price_unit_node is not None:
            net_price_unit = float(net_price_unit_node.text)

        # billed_qty (mandatory)
        billed_qty = 1
        product_uom_id = None
        quantity_node = tree.find(xpath_dict['billed_qty'])
        if quantity_node is not None:
            billed_qty = float(quantity_node.text)
            uom_xml = quantity_node.attrib.get('unitCode')
            if uom_xml:
                uom_infered_xmlid = [
                    odoo_xmlid for odoo_xmlid, uom_unece in UOM_TO_UNECE_CODE.items() if uom_unece == uom_xml
                ]
                if uom_infered_xmlid:
                    product_uom_id = self.env.ref(uom_infered_xmlid[0], raise_if_not_found=False)

        # allow_charge_amount
        fixed_taxes_list = []
        allow_charge_amount = 0  # if positive: it's a discount, if negative: it's a charge
        allow_charge_nodes = tree.findall(xpath_dict['allowance_charge'])
        for allow_charge_el in allow_charge_nodes:
            charge_indicator = allow_charge_el.find(xpath_dict['allowance_charge_indicator'])
            if charge_indicator.text and charge_indicator.text.lower() == 'false':
                discount_factor = 1  # it's a discount
            else:
                discount_factor = -1  # it's a charge
            amount = allow_charge_el.find(xpath_dict['allowance_charge_amount'])
            reason_code = allow_charge_el.find(xpath_dict['allowance_charge_reason_code'])
            reason = allow_charge_el.find(xpath_dict['allowance_charge_reason'])
            if amount is not None:
                if reason_code is not None and reason_code.text == 'AEO' and reason is not None:
                    # Handle Fixed Taxes: when exporting from Odoo, we use the allowance_charge node
                    fixed_taxes_list.append({
                        'tax_name': reason.text,
                        'tax_amount': float(amount.text),
                    })
                else:
                    allow_charge_amount += float(amount.text) * discount_factor

        # line_net_subtotal (mandatory)
        price_subtotal = None
        line_total_amount_node = tree.find(xpath_dict['line_total_amount'])
        if line_total_amount_node is not None:
            price_subtotal = float(line_total_amount_node.text)

        ####################################################
        # Setting the values on the invoice_line
        ####################################################

        # quantity
        quantity = billed_qty * qty_factor

        # price_unit
        if gross_price_unit is not None:
            price_unit = gross_price_unit / basis_qty
        elif net_price_unit is not None:
            price_unit = (net_price_unit + rebate) / basis_qty
        elif price_subtotal is not None:
            price_unit = (price_subtotal + allow_charge_amount) / (billed_qty or 1)
        else:
            raise UserError(_("No gross price, net price nor line subtotal amount found for line in xml"))

        # discount
        discount = 0
        amount_fixed_taxes = sum(d['tax_amount'] for d in fixed_taxes_list)
        if billed_qty * price_unit != 0 and price_subtotal is not None:
            discount = 100 * (1 - (price_subtotal - amount_fixed_taxes) / (billed_qty * price_unit))

        # Sometimes, the xml received is very bad: unit price = 0, qty = 1, but price_subtotal = -200
        # for instance, when filling a down payment as an invoice line. The equation in the docstring is not
        # respected, and the result will not be correct, so we just follow the simple rule below:
        if net_price_unit == 0 and price_subtotal != net_price_unit * (billed_qty / basis_qty) - allow_charge_amount:
            price_unit = price_subtotal / (billed_qty or 1)

        return {
            'quantity': quantity,
            'price_unit': price_unit,
            'discount': discount,
            'product_uom_id': product_uom_id,
            'fixed_taxes_list': fixed_taxes_list,
        }

    def _import_retrieve_fixed_tax(self, invoice_line_form, fixed_tax_vals):
        """ Retrieve the fixed tax at import, iteratively search for a tax:
        1. not price_include matching the name and the amount
        2. not price_include matching the amount
        3. price_include matching the name and the amount
        4. price_include matching the amount
        """
        base_domain = [
            ('company_id', '=', invoice_line_form.company_id.id),
            ('amount_type', '=', 'fixed'),
            ('amount', '=', fixed_tax_vals['tax_amount']),
        ]
        for price_include in (False, True):
            for name in (fixed_tax_vals['tax_name'], False):
                domain = base_domain + [('price_include', '=', price_include)]
                if name:
                    domain.append(('name', '=', name))
                tax = self.env['account.tax'].search(domain, limit=1)
                if tax:
                    return tax
        return self.env['account.tax']

    def _import_fill_invoice_line_taxes(self, journal, tax_nodes, invoice_line_form, inv_line_vals, logs):
        # Taxes: all amounts are tax excluded, so first try to fetch price_include=False taxes,
        # if no results, try to fetch the price_include=True taxes. If results, need to adapt the price_unit.
        inv_line_vals['taxes'] = []
        for tax_node in tax_nodes:
            amount = float(tax_node.text)
            domain = [
                ('company_id', '=', journal.company_id.id),
                ('amount_type', '=', 'percent'),
                ('type_tax_use', '=', journal.type),
                ('amount', '=', amount),
            ]
            tax_excl = self.env['account.tax'].search(domain + [('price_include', '=', False)], limit=1)
            tax_incl = self.env['account.tax'].search(domain + [('price_include', '=', True)], limit=1)
            if tax_excl:
                inv_line_vals['taxes'].append(tax_excl.id)
            elif tax_incl:
                inv_line_vals['taxes'].append(tax_incl.id)
                inv_line_vals['price_unit'] *= (1 + tax_incl.amount / 100)
            else:
                logs.append(_("Could not retrieve the tax: %s %% for line '%s'.", amount, invoice_line_form.name))

        # Handle Fixed Taxes
        for fixed_tax_vals in inv_line_vals['fixed_taxes_list']:
            tax = self._import_retrieve_fixed_tax(invoice_line_form, fixed_tax_vals)
            if not tax:
                # Nothing found: fix the price_unit s.t. line subtotal is matching the original invoice
                inv_line_vals['price_unit'] += fixed_tax_vals['tax_amount']
            elif tax.price_include:
                inv_line_vals['taxes'].append(tax.id)
                inv_line_vals['price_unit'] += tax.amount
            else:
                inv_line_vals['taxes'].append(tax.id)

        # Set the values on the line_form
        invoice_line_form.quantity = inv_line_vals['quantity']
        if inv_line_vals.get('product_uom_id'):
            invoice_line_form.product_uom_id = inv_line_vals['product_uom_id']
        else:
            logs.append(
                _("Could not retrieve the unit of measure for line with label '%s'.", invoice_line_form.name))
        invoice_line_form.price_unit = inv_line_vals['price_unit']
        invoice_line_form.discount = inv_line_vals['discount']
        invoice_line_form.tax_ids = inv_line_vals['taxes']
        return logs

    def _correct_invoice_tax_amount(self, tree, invoice):
        pass  # To be implemented by the format if needed

    # -------------------------------------------------------------------------
    # Check xml using the free API from Ph. Helger, don't abuse it !
    # -------------------------------------------------------------------------

    def _check_xml_ecosio(self, invoice, xml_content, ecosio_formats):
        # see https://peppol.helger.com/public/locale-en_US/menuitem-validation-ws2
        if not ecosio_formats:
            return
        soap_client = Client('https://peppol.helger.com/wsdvs?wsdl')
        if invoice.move_type == 'out_invoice':
            ecosio_format = ecosio_formats['invoice']
        elif invoice.move_type == 'out_refund':
            ecosio_format = ecosio_formats['credit_note']
        else:
            invoice.with_context(no_new_invoice=True).message_post(
                body="ECOSIO: could not validate xml, formats only exist for invoice or credit notes"
            )
            return
        if not ecosio_format:
            return
        response = soap_client.service.validate(xml_content, ecosio_format)

        report = []
        errors_cnt = 0
        for item in response['Result']:
            if item['artifactPath']:
                report.append(
                    "<li><font style='color:Blue;'><strong>" + item['artifactPath'] + "</strong></font></li>")
            for detail in item['Item']:
                if detail['errorLevel'] == 'WARN':
                    errors_cnt += 1
                    report.append(
                        "<li><font style='color:Orange;'><strong>" + detail['errorText'] + "</strong></font></li>")
                elif detail['errorLevel'] == 'ERROR':
                    errors_cnt += 1
                    report.append(
                        "<li><font style='color:Tomato;'><strong>" + detail['errorText'] + "</strong></font></li>")

        if errors_cnt == 0:
            invoice.with_context(no_new_invoice=True).message_post(
                body=f"<font style='color:Green;'><strong>ECOSIO: All clear for format {ecosio_format}!</strong></font>"
            )
        else:
            invoice.with_context(no_new_invoice=True).message_post(
                body=f"<font style='color:Tomato;'><strong>ECOSIO ERRORS/WARNINGS for format {ecosio_format}</strong></font>: <ul> "
                     + "\n".join(report) + " </ul>"
            )
        return response
