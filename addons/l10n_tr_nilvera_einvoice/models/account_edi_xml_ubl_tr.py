import math
from num2words import num2words
from odoo import api, models


class AccountEdiXmlUblTr(models.AbstractModel):
    _name = "account.edi.xml.ubl.tr"
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL-TR 1.2"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        # EXTENDS account_edi_ubl_cii
        return '%s_einvoice.xml' % invoice.name.replace("/", "_")

    def _get_tax_category_code(self, customer, supplier, tax):
        # OVERRIDES account.edi.ubl_21
        if tax.amount < 0:  # This is a withholding
            return '9015'
        return '0015'

    def _add_invoice_currency_vals(self, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_currency_vals(vals)
        vals['currency_dp'] = 2  # Force 2 decimal places everywhere

    # -------------------------------------------------------------------------
    # EXPORT: TEMPLATES
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']

        # Check the customer status if it hasn't been done before as it's needed for profile_id
        if invoice.partner_id.l10n_tr_nilvera_customer_status == 'not_checked':
            invoice.partner_id._check_nilvera_customer()

        # For now, we assume that the sequence is going to be in the format {prefix}/{year}/{invoice_number}.
        # To send an invoice to Nlvera, the format needs to follow ABC2009123456789.
        parts = invoice.name.split('/')
        prefix, year, number = parts[0], parts[1], parts[2].zfill(9)
        invoice_id = f"{prefix.upper()}{year}{number}"

        document_node.update({
            'cbc:CustomizationID': {'_text': 'TR1.2'},
            'cbc:ProfileID': {
                '_text': 'TEMELFATURA' if invoice.partner_id.l10n_tr_nilvera_customer_status == 'einvoice' else 'EARSIVFATURA'
            },
            'cbc:ID': {'_text': invoice_id},
            'cbc:CopyIndicator': {'_text': 'false'},
            'cbc:UUID': {'_text': invoice.l10n_tr_nilvera_uuid},
            'cbc:DueDate': None,
            'cbc:InvoiceTypeCode': {'_text': 'SATIS'} if vals['document_type'] == 'invoice' else None,
            'cbc:CreditNoteTypeCode': {'_text': 'IADE'} if vals['document_type'] == 'credit_note' else None,
            'cbc:PricingCurrencyCode': {'_text': invoice.currency_id.name.upper()}
                if vals['currency_id'] != vals['company_currency_id'] else None,
            'cbc:LineCountNumeric': {'_text': len(invoice.line_ids)},
            'cbc:BuyerReference': None,  # Nilvera will reject any <BuyerReference> tag, so remove it
        })

        if invoice.invoice_line_ids._fields.get('deferred_start_date'):
            line_ids = invoice.invoice_line_ids.filtered(lambda line: line.display_type == 'product' and line.deferred_start_date)
            if line_ids:
                document_node['cac:InvoicePeriod'] = {
                    'cbc:StartDate': {'_text': line_ids[0].deferred_start_date},
                    'cbc:EndDate': {'_text': line_ids[0].deferred_end_date},
                }

        document_node['cac:OrderReference']['cbc:IssueDate'] = {'_text': invoice.invoice_date}

        if invoice.partner_id.l10n_tr_nilvera_customer_status == 'earchive':
            document_node['cac:AdditionalDocumentReference'] = {
                'cbc:ID': {'_text': 'ELEKTRONIK'},
                'cbc:IssueDate': {'_text': invoice.invoice_date},
                'cbc:DocumentTypeCode': {'_text': 'SEND_TYPE'},
            }
        document_node['cbc:Note'] = [
            document_node['cbc:Note'],
            {'_text': self._l10n_tr_get_amount_integer_partn_text_note(invoice.amount_residual_signed, self.env.ref('base.TRY')), 'note_attrs': {}}
        ]
        if vals['invoice'].currency_id.name != 'TRY':
            document_node['cbc:Note'].append({'_text': self._l10n_tr_get_amount_integer_partn_text_note(invoice.amount_residual, vals['invoice'].currency_id), 'note_attrs': {}})
            document_node['cbc:Note'].append({'_text': self._l10n_tr_get_invoice_currency_exchange_rate(invoice)})

    @api.model
    def _l10n_tr_get_amount_integer_partn_text_note(self, amount, currency):
        sign = math.copysign(1.0, amount)
        amount_integer_part, amount_decimal_part = divmod(abs(amount), 1)
        amount_decimal_part = int(amount_decimal_part * 100)

        text_i = num2words(amount_integer_part * sign, lang="tr") or 'Sifir'
        text_d = num2words(amount_decimal_part * sign, lang="tr") or 'Sifir'
        return f'YALNIZ : {text_i} {currency.name} {text_d} {currency.currency_subunit_label}'.upper()

    def _add_invoice_delivery_nodes(self, document_node, vals):
        super()._add_invoice_delivery_nodes(document_node, vals)
        invoice = vals['invoice']
        if 'picking_ids' in invoice._fields and invoice.picking_ids:
            document_node['cac:Delivery']['cbc:ID'] = {'_text': invoice.picking_ids[0].name}
            document_node['cac:Delivery']['cbc:ActualDeliveryDate'] = {'_text': invoice.delivery_date}
        else:
            document_node['cac:Delivery'] = None

    def _l10n_tr_get_invoice_currency_exchange_rate(self, invoice):
        conversion_rate = self.env['res.currency']._get_conversion_rate(
            from_currency=invoice.currency_id,
            to_currency=invoice.company_currency_id,
            company=invoice.company_id,
            date=invoice.invoice_date,
        )
        # Nilvera Portal accepts the exchange rate for 6 decimals places only.
        return f'KUR : {conversion_rate:.6f} TL'

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_payment_means_nodes(document_node, vals)
        payment_means_node = document_node['cac:PaymentMeans']
        payment_means_node['cbc:InstructionID'] = None
        payment_means_node['cbc:PaymentID'] = None

    def _add_invoice_exchange_rate_nodes(self, document_node, vals):
        invoice = vals['invoice']
        if vals['currency_id'] != vals['company_currency_id']:
            document_node['cac:PricingExchangeRate'] = {
                'cbc:SourceCurrencyCode': {'_text': vals['currency_name']},
                'cbc:TargetCurrencyCode': {'_text': vals['company_currency_id'].name},
                'cbc:CalculationRate': {'_text': round(invoice.currency_id._get_conversion_rate(invoice.currency_id, invoice.company_id.currency_id, invoice.company_id, invoice.invoice_date), 6)},
                'cbc:Date': {'_text': invoice.invoice_date},
            }

    def _l10n_tr_get_total_invoice_discount_amount(self, vals):
        invoice = vals['invoice']
        invoice_lines = invoice.invoice_line_ids.filtered(lambda line: line.display_type not in {'line_note', 'line_section'})
        return sum(
            line.currency_id.round(line.price_unit * line.quantity * (line.discount / 100))
            for line in invoice_lines
        )

    def _add_document_allowance_charge_nodes(self, document_node, vals):
        super()._add_document_allowance_charge_nodes(document_node, vals)
        for node in document_node['cac:AllowanceCharge']:
            node['cbc:AllowanceChargeReasonCode'] = None

        total_discount_amount = self._l10n_tr_get_total_invoice_discount_amount(vals)
        if total_discount_amount:
            document_node['cac:AllowanceCharge'].append({
                'cbc:ChargeIndicator': {'_text': 'false'},
                'cbc:AllowanceChargeReason': {'_text': "Discount"},
                'cbc:Amount': {
                    '_text': self.format_float(total_discount_amount, vals['currency_dp']),
                    'currencyID': vals['currency_name'],
                },
            })

    def _get_address_node(self, vals):
        partner = vals['partner']
        model = vals.get('model', 'res.partner')
        country = partner['country' if model == 'res.bank' else 'country_id']
        state = partner['state' if model == 'res.bank' else 'state_id']

        return {
            'cbc:StreetName': {'_text': partner.street},
            'cbc:CitySubdivisionName': {'_text': partner.city},
            'cbc:AdditionalStreetName': {'_text': partner.street2},
            'cbc:CityName': {'_text': state.name},
            'cbc:PostalZone': {'_text': partner.zip},
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': country.code},
                'cbc:Name': {'_text': country.with_context(lang='tr_TR').name},
            }
        }

    def _get_party_node(self, vals):
        partner = vals['partner']
        commercial_partner = partner.commercial_partner_id

        party_node = {
            'cac:PartyIdentification': {
                'cbc:ID': {
                    '_text': partner.vat,
                    'schemeID': 'VKN' if partner.is_company else 'TCKN',
                }
            },
            'cac:PartyName': {
                'cbc:Name': {'_text': partner.display_name}
            },
            'cac:PostalAddress': self._get_address_node(vals),
            'cac:PartyTaxScheme': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
                'cac:TaxScheme': {
                    'cbc:Name': {
                        '_text': (
                            commercial_partner.ref
                        )
                    }
                }
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
            },
            'cac:Contact': {
                'cbc:ID': {'_text': partner.id},
                'cbc:Name': {'_text': partner.name},
                'cbc:Telephone': {'_text': partner.phone},
                'cbc:ElectronicMail': {'_text': partner.email},
            }
        }
        if not partner.is_company:
            name_parts = partner.name.split(' ', 1)
            party_node['cac:Person'] = {
                'cbc:FirstName': {'_text': name_parts[0]},
                # If no family name is present, use a zero-width space (U+200B) to ensure the XML tag is rendered. This is required by Nilvera.
                'cbc:FamilyName': {'_text': name_parts[1] if len(name_parts) > 1 else '\u200B'},
            }
        return party_node

    def _get_tax_category_node(self, vals):
        # OVERRIDES account.edi.ubl_21
        grouping_key = vals['grouping_key']
        is_withholding = grouping_key['tax_category_code'] == '9015'
        tax_category_node = {
            'cac:TaxScheme': {
                'cbc:Name': {'_text': 'KDV Tevkifatı' if is_withholding else 'Gerçek Usulde KDV'},
                'cbc:TaxTypeCode': {'_text': grouping_key['tax_category_code']}
            }
        }
        return tax_category_node

    def _get_tax_subtotal_node(self, vals):
        # EXTENDS account.edi.xml.ubl_21
        tax_subtotal_node = super()._get_tax_subtotal_node(vals)
        tax_subtotal_node['cac:TaxCategory']['cbc:Percent'] = None
        return tax_subtotal_node

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_invoice_monetary_total_nodes(document_node, vals)
        invoice = vals['invoice']

        monetary_total_tag = 'cac:LegalMonetaryTotal' if vals['document_type'] in {'invoice', 'credit_note'} else 'cac:RequestedMonetaryTotal'
        monetary_total_node = document_node[monetary_total_tag]

        # allowance_total_amount needs to have a value even if 0.0 otherwise it's blank in the Nilvera PDF.
        total_allowance_amount = self._l10n_tr_get_total_invoice_discount_amount(vals)
        monetary_total_node['cbc:AllowanceTotalAmount'] = {
            '_text': self.format_float(total_allowance_amount, vals['currency_dp']),
            'currencyID': vals['currency_name'],
        }

        # <cbc:PrepaidAmount> tag is not supported by Nilvera. so it is removed and <cbc:PayableAmount> holds the
        # amount_total so that the total invoice amount (in invoice currency) is preserved.
        monetary_total_node['cbc:PrepaidAmount'] = None
        monetary_total_node['cbc:PayableAmount'] = {
            '_text': self.format_float(invoice.amount_total, vals['currency_dp']),
            'currencyID': vals['currency_name'],
        }

    def _add_document_line_allowance_charge_nodes(self, line_node, vals):
        # EXTENDS account.edi.xml.ubl_21
        super()._add_document_line_allowance_charge_nodes(line_node, vals)
        for allowance_charge_node in line_node['cac:AllowanceCharge']:
            allowance_charge_node['cbc:AllowanceChargeReasonCode'] = None

    def _add_document_line_tax_category_nodes(self, line_node, vals):
        # No InvoiceLine/Item/ClassifiedTaxCategory in Turkey
        pass

    def _add_invoice_line_period_nodes(self, line_node, vals):
        # Start and End Dates on Invoice Lines is not allowed in Turkey
        pass

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_retrieve_partner_vals(self, tree, role):
        # EXTENDS account.edi.xml.ubl_20
        partner_vals = super()._import_retrieve_partner_vals(tree, role)
        partner_vals.update({
            'vat': self._find_value(f'.//cac:Accounting{role}Party/cac:Party//cac:PartyIdentification//cbc:ID[string-length(text()) > 5]', tree),
        })
        return partner_vals

    def _import_fill_invoice_form(self, invoice, tree, qty_factor):
        # EXTENDS account.edi.xml.ubl_20
        logs = super()._import_fill_invoice_form(invoice, tree, qty_factor)

        # ==== Nilvera UUID ====
        if uuid_node := tree.findtext('./{*}UUID'):
            invoice.l10n_tr_nilvera_uuid = uuid_node

        return logs
