# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Colombian UBL 2.1 XML builder for DIAN electronic invoicing.

Extends the standard UBL 2.1 builder with DIAN-specific elements:
- ext:UBLExtensions with DianExtensions (authorization, software provider, QR)
- Colombian party identification (NIT with check digit, fiscal responsibilities)
- DIAN tax type codes (01=IVA, 03=ICA, 04=INC, 05=RteIVA, 06=RteFte)
- DIAN document type codes (01=Invoice, 91=CreditNote, 92=DebitNote)
- ProfileID / CustomizationID / ProfileExecutionID per Technical Annex v1.9
"""

import hashlib
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)

# DIAN identification type codes per Resolution 000012 de 2021
DIAN_ID_TYPE_CODES = {
    'rut': '31',
    'nit': '31',
    'cedula_ciudadania': '13',
    'cc': '13',
    'cedula_extranjeria': '22',
    'ce': '22',
    'tarjeta_identidad': '12',
    'ti': '12',
    'pasaporte': '41',
    'pp': '41',
    'registro_civil': '11',
    'rc': '11',
    'doc_id_extranjero': '42',
    'de': '42',
    'nit_otro_pais': '50',
    'nuip': '91',
}

# DIAN tax type codes and names
DIAN_TAX_CODES = {
    '01': 'IVA',
    '02': 'IC',
    '03': 'ICA',
    '04': 'INC',
    '05': 'ReteIVA',
    '06': 'RteFte',
    '07': 'RteICA',
    '08': 'FtoHorticultura',
    '20': 'RteCREE',
    '21': 'RteRenta',
    '22': 'FtoTabaco',
    'ZZ': 'No causa',
}

# Withholding tax codes (reported in WithholdingTaxTotal)
DIAN_WITHHOLDING_CODES = {'05', '06', '07'}


def compute_nit_check_digit(nit):
    """Compute the Colombian NIT check digit (digito de verificacion).

    Algorithm per DIAN specifications:
    - Multiply each digit (right to left) by prime weights
    - Sum the products, take modulo 11
    - If remainder >= 2: check_digit = 11 - remainder
    - If remainder is 0 or 1: check_digit = remainder

    :param nit: str — NIT number without check digit or hyphens
    :return: str — single digit check digit
    """
    weights = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
    nit_str = str(nit).strip().replace('-', '')

    total = 0
    for i, digit in enumerate(reversed(nit_str)):
        if i < len(weights):
            total += int(digit) * weights[i]

    remainder = total % 11
    if remainder >= 2:
        return str(11 - remainder)
    return str(remainder)


class AccountEdiXmlUblCO(models.AbstractModel):
    _name = 'account.edi.xml.ubl_co'
    _inherit = 'account.edi.xml.ubl_21'
    _description = "DIAN UBL 2.1 Colombia"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_co_dian.xml"

    # _export_invoice is inherited from account.edi.xml.ubl_20 — our overrides
    # of _get_invoice_node, _get_document_template, and _get_document_nsmap
    # are called automatically via MRO.

    # -------------------------------------------------------------------------
    # EXPORT: Templates and Namespaces
    # -------------------------------------------------------------------------

    def _get_document_template(self, vals):
        from odoo.addons.l10n_co_edi.tools.ubl_21_dian import DianInvoice, DianCreditNote
        return {
            'invoice': DianInvoice,
            'credit_note': DianCreditNote,
            'debit_note': DianCreditNote,  # Debit notes use credit note structure in CO
        }[vals['document_type']]

    def _get_document_nsmap(self, vals):
        nsmap = super()._get_document_nsmap(vals)
        nsmap.update({
            'sts': 'dian:gov:co:facturaelectronica:Structures-2-1',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'xades': 'http://uri.etsi.org/01903/v1.3.2#',
            'xades141': 'http://uri.etsi.org/01903/v1.4.1#',
        })
        return nsmap

    # -------------------------------------------------------------------------
    # EXPORT: Invoice Node (main builder)
    # -------------------------------------------------------------------------

    def _get_invoice_node(self, vals):
        document_node = super()._get_invoice_node(vals)
        self._add_dian_extensions(document_node, vals)
        return document_node

    def _add_dian_extensions(self, document_node, vals):
        """Populate ext:UBLExtensions with DIAN-specific extension data."""
        invoice = vals['invoice']
        company = vals['company']
        journal = invoice.journal_id

        # Software security code: SHA384(SoftwareID + PIN + InvoiceNumber)
        sw_id = company.l10n_co_edi_software_id or ''
        sw_pin = company.l10n_co_edi_software_pin or ''
        security_input = sw_id + sw_pin + (invoice.name or '')
        security_code = hashlib.sha384(security_input.encode('utf-8')).hexdigest()

        # InvoiceControl only for sales invoices (not credit/debit notes)
        invoice_control = None
        if vals['document_type'] == 'invoice':
            invoice_control = {
                'sts:InvoiceAuthorization': {'_text': journal.l10n_co_edi_dian_authorization or ''},
                'sts:AuthorizationPeriod': {
                    'cbc:StartDate': {'_text': journal.l10n_co_edi_dian_range_valid_from},
                    'cbc:EndDate': {'_text': journal.l10n_co_edi_dian_range_valid_to},
                },
                'sts:AuthorizedInvoices': {
                    'sts:Prefix': {'_text': journal.l10n_co_edi_dian_prefix or ''},
                    'sts:From': {'_text': journal.l10n_co_edi_dian_range_from},
                    'sts:To': {'_text': journal.l10n_co_edi_dian_range_to},
                },
            }

        nit = (company.vat or '').replace('-', '').strip()

        document_node['ext:UBLExtensions'] = {
            'ext:UBLExtension': [
                {
                    'ext:ExtensionContent': {
                        'sts:DianExtensions': {
                            'sts:InvoiceControl': invoice_control,
                            'sts:InvoiceSource': {
                                'cbc:IdentificationCode': {
                                    '_text': 'CO',
                                    'listAgencyID': '6',
                                    'listAgencyName': 'United Nations Economic Commission for Europe',
                                    'listSchemeURI': 'urn:oasis:names:specification:ubl:codelist:gc:CountryIdentificationCode-2.1',
                                },
                            },
                            'sts:SoftwareProvider': {
                                'sts:ProviderID': {
                                    '_text': nit,
                                    'schemeAgencyID': '195',
                                    'schemeAgencyName': 'CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)',
                                },
                                'sts:SoftwareID': {
                                    '_text': sw_id,
                                    'schemeAgencyID': '195',
                                    'schemeAgencyName': 'CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)',
                                },
                            },
                            'sts:SoftwareSecurityCode': {
                                '_text': security_code,
                                'schemeAgencyID': '195',
                                'schemeAgencyName': 'CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)',
                            },
                            'sts:AuthorizationProvider': {
                                'sts:AuthorizationProviderID': {
                                    '_text': '800197268',
                                    'schemeAgencyID': '195',
                                    'schemeAgencyName': 'CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)',
                                    'schemeID': '4',
                                    'schemeName': '31',
                                },
                            },
                            'sts:QRCode': {'_text': invoice.l10n_co_edi_qr_data or ''},
                        },
                    },
                },
            ],
        }

    # -------------------------------------------------------------------------
    # EXPORT: Header Nodes
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)

        invoice = vals['invoice']
        company = vals['company']

        tipo_ambiente = '2' if company.l10n_co_edi_test_mode else '1'

        # Line count
        line_count = len([
            bl for bl in vals.get('base_lines', [])
            if not self._is_document_allowance_charge(bl)
        ])

        document_node.update({
            'cbc:UBLVersionID': {'_text': 'UBL 2.1'},
            'cbc:CustomizationID': {'_text': self._get_co_customization_id(vals)},
            'cbc:ProfileID': {'_text': 'DIAN 2.1'},
            'cbc:ProfileExecutionID': {'_text': tipo_ambiente},
            'cbc:UUID': {
                '_text': invoice.l10n_co_edi_cufe_cude or '',
                'schemeID': tipo_ambiente,
                'schemeName': (
                    'CUFE-SHA384'
                    if vals['document_type'] == 'invoice' and not invoice.l10n_co_edi_is_dee
                    else 'CUDE-SHA384'
                ),
            },
            'cbc:IssueTime': {'_text': self._format_co_time(invoice.l10n_co_edi_datetime)},
            'cbc:LineCountNumeric': {'_text': line_count},
        })

        # DIAN document type codes
        if vals['document_type'] == 'invoice':
            # DEE uses its own type code; regular invoices use '01'
            type_code = '01'
            if invoice.l10n_co_edi_is_dee and invoice.l10n_co_edi_dee_type_id:
                type_code = invoice.l10n_co_edi_dee_type_id.code
            document_node['cbc:InvoiceTypeCode'] = {'_text': type_code}
        elif vals['document_type'] == 'credit_note':
            document_node['cbc:CreditNoteTypeCode'] = {'_text': '91'}

    def _get_co_customization_id(self, vals):
        """Return the DIAN operation type code (CustomizationID).

        10 = Standard sales invoice
        20 = Export invoice
        30 = Contingency invoice
        05 = Documento Equivalente POS (tiquete)
        07-18 = Other DEE types per Res. 000165/2023
        91 = Credit note
        92 = Debit note
        """
        invoice = vals['invoice']
        doc_type = vals['document_type']

        if doc_type == 'credit_note':
            return '91'
        if doc_type == 'debit_note':
            return '92'

        # DEE: use the specific document type code
        if invoice.l10n_co_edi_is_dee and invoice.l10n_co_edi_dee_type_id:
            return invoice.l10n_co_edi_dee_type_id.code

        if invoice.journal_id.l10n_co_edi_is_contingency:
            return '30'

        return '10'

    def _format_co_time(self, dt):
        """Format datetime as HH:MM:SS-05:00 (Colombia timezone UTC-5)."""
        if dt:
            return dt.strftime('%H:%M:%S') + '-05:00'
        return '00:00:00-05:00'

    # -------------------------------------------------------------------------
    # EXPORT: Party Nodes (Colombian identification)
    # -------------------------------------------------------------------------

    def _add_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        partner = vals['supplier']
        document_node['cac:AccountingSupplierParty'] = {
            'cbc:AdditionalAccountID': {
                '_text': '1' if partner.is_company else '2',
            },
            'cac:Party': self._get_co_party_node({
                **vals,
                'partner': partner,
                'role': 'supplier',
            }),
        }

    def _add_invoice_accounting_customer_party_nodes(self, document_node, vals):
        partner = vals['customer']
        invoice = vals['invoice']

        # DEE with simplified buyer: use minimal party data per Res. 000202/2025
        if invoice.l10n_co_edi_is_dee and invoice.l10n_co_edi_dee_simplified_buyer:
            document_node['cac:AccountingCustomerParty'] = {
                'cbc:AdditionalAccountID': {
                    '_text': '2',  # Persona Natural
                },
                'cac:Party': self._get_co_simplified_buyer_node(vals),
            }
            return

        document_node['cac:AccountingCustomerParty'] = {
            'cbc:AdditionalAccountID': {
                '_text': '1' if partner.is_company else '2',
            },
            'cac:Party': self._get_co_party_node({
                **vals,
                'partner': partner,
                'role': 'customer',
            }),
        }

    def _get_co_simplified_buyer_node(self, vals):
        """Build a minimal buyer party node for DEE POS tickets.

        Per Res. 000202/2025, POS equivalent documents require only:
        - Buyer name (or 'CONSUMIDOR FINAL')
        - Identification type (or '13' for CC)
        - Identification number (or '222222222222' for anonymous)
        """
        partner = vals.get('customer')
        buyer_name = 'CONSUMIDOR FINAL'
        buyer_id = '222222222222'
        buyer_id_type = '13'  # CC

        if partner and partner.vat:
            buyer_name = partner.name or 'CONSUMIDOR FINAL'
            buyer_id = (partner.vat or '').replace('-', '').strip()
            buyer_id_type = self._get_co_id_type_code(partner.commercial_partner_id)

        return {
            'cac:PartyName': {
                'cbc:Name': {'_text': buyer_name},
            },
            'cac:PhysicalLocation': {
                'cac:Address': {
                    'cac:Country': {
                        'cbc:IdentificationCode': {'_text': 'CO'},
                        'cbc:Name': {'_text': 'Colombia', 'languageID': 'es'},
                    },
                },
            },
            'cac:PartyTaxScheme': {
                'cbc:RegistrationName': {'_text': buyer_name},
                'cbc:CompanyID': {
                    '_text': buyer_id,
                    'schemeAgencyID': '195',
                    'schemeAgencyName': 'CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)',
                    'schemeID': '',
                    'schemeName': buyer_id_type,
                },
                'cbc:TaxLevelCode': {
                    '_text': 'R-99-PN',
                    'listName': '48',
                },
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'ZZ'},
                    'cbc:Name': {'_text': 'No causa'},
                },
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': buyer_name},
                'cbc:CompanyID': {
                    '_text': buyer_id,
                    'schemeAgencyID': '195',
                    'schemeAgencyName': 'CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)',
                    'schemeID': '',
                    'schemeName': buyer_id_type,
                },
            },
        }

    def _get_co_party_node(self, vals):
        """Build a DIAN-compliant party node with Colombian identification."""
        partner = vals['partner']
        commercial = partner.commercial_partner_id
        company = vals['company']
        role = vals.get('role', 'customer')

        vat = (commercial.vat or '').replace('-', '').strip()
        id_type_code = self._get_co_id_type_code(commercial)
        check_digit = compute_nit_check_digit(vat) if id_type_code == '31' and vat else ''

        # Fiscal responsibilities — supplier uses company data, customer uses partner data
        fiscal_resp = ''
        if role == 'supplier' and company.l10n_co_edi_fiscal_responsibilities:
            fiscal_resp = company.l10n_co_edi_fiscal_responsibilities
        elif role == 'customer':
            fiscal_resp = commercial.l10n_co_edi_fiscal_responsibilities or ''

        # Tax regime determines which TaxScheme to report
        tax_scheme_id = '01'  # IVA by default
        tax_scheme_name = 'IVA'
        if role == 'supplier':
            regime = company.l10n_co_edi_tax_regime
        else:
            regime = commercial.l10n_co_edi_tax_regime
        if regime == 'not_responsible':
            tax_scheme_id = 'ZZ'
            tax_scheme_name = 'No causa'

        # Build PartyLegalEntity
        party_legal = {
            'cbc:RegistrationName': {'_text': commercial.name},
            'cbc:CompanyID': {
                '_text': vat,
                'schemeAgencyID': '195',
                'schemeAgencyName': 'CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)',
                'schemeID': check_digit,
                'schemeName': id_type_code,
            },
        }

        # Add CorporateRegistrationScheme for supplier
        if role == 'supplier':
            journal = vals['invoice'].journal_id
            party_legal['cac:CorporateRegistrationScheme'] = {
                'cbc:ID': {'_text': journal.l10n_co_edi_dian_prefix or ''},
            }

        party_node = {
            'cac:PartyName': {
                'cbc:Name': {
                    '_text': commercial.name,
                },
            },
            'cac:PhysicalLocation': {
                'cac:Address': self._get_co_address_node(commercial),
            },
            'cac:PartyTaxScheme': {
                'cbc:RegistrationName': {'_text': commercial.name},
                'cbc:CompanyID': {
                    '_text': vat,
                    'schemeAgencyID': '195',
                    'schemeAgencyName': 'CO, DIAN (Direccion de Impuestos y Aduanas Nacionales)',
                    'schemeID': check_digit,
                    'schemeName': id_type_code,
                },
                'cbc:TaxLevelCode': {
                    '_text': fiscal_resp or 'R-99-PN',
                    'listName': '48',
                } if fiscal_resp or role == 'customer' else None,
                'cac:RegistrationAddress': self._get_co_address_node(commercial),
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': tax_scheme_id},
                    'cbc:Name': {'_text': tax_scheme_name},
                },
            },
            'cac:PartyLegalEntity': party_legal,
            'cac:Contact': {
                'cbc:Telephone': {'_text': commercial.phone},
                'cbc:ElectronicMail': {'_text': commercial.email},
            },
        }
        return party_node

    def _get_co_address_node(self, partner):
        """Build a Colombian address node with DANE department/municipality codes."""
        state = partner.state_id
        country = partner.country_id
        return {
            'cbc:ID': {'_text': state.code if state else None},
            'cbc:CityName': {'_text': partner.city},
            'cbc:PostalZone': {'_text': partner.zip},
            'cbc:CountrySubentity': {'_text': state.name if state else None},
            'cbc:CountrySubentityCode': {'_text': state.code if state else None},
            'cac:AddressLine': {
                'cbc:Line': {'_text': partner.street or ''},
            },
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': country.code if country else 'CO'},
                'cbc:Name': {
                    '_text': country.name if country else 'Colombia',
                    'languageID': 'es',
                },
            },
        }

    def _get_co_id_type_code(self, partner):
        """Map a partner's l10n_latam_identification_type_id to a DIAN code."""
        if not partner.l10n_latam_identification_type_id:
            return '31'  # Default: NIT

        id_type = partner.l10n_latam_identification_type_id
        # Try matching by l10n_co_document_code first
        if hasattr(id_type, 'l10n_co_document_code') and id_type.l10n_co_document_code:
            return id_type.l10n_co_document_code

        # Fallback: match by name fragments
        name = (id_type.name or '').lower()
        for key, code in DIAN_ID_TYPE_CODES.items():
            if key in name:
                return code

        return '31'  # Default to NIT

    # -------------------------------------------------------------------------
    # EXPORT: Tax Total Nodes (DIAN tax codes)
    # -------------------------------------------------------------------------

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        """Build TaxTotal and WithholdingTaxTotal per DIAN requirements.

        DIAN separates regular taxes (IVA, INC, ICA) from withholding taxes
        (RteFte, RteIVA, RteICA) into different XML sections.
        """
        invoice = vals['invoice']

        # Get tax data grouped by DIAN code
        tax_totals = self._get_co_tax_data(vals)

        # Regular taxes -> cac:TaxTotal
        regular_taxes = {
            code: data for code, data in tax_totals.items()
            if code not in DIAN_WITHHOLDING_CODES
        }
        document_node['cac:TaxTotal'] = self._build_co_tax_total_node(regular_taxes, vals)

        # Withholding taxes -> cac:WithholdingTaxTotal
        withholding_taxes = {
            code: data for code, data in tax_totals.items()
            if code in DIAN_WITHHOLDING_CODES
        }
        if withholding_taxes:
            document_node['cac:WithholdingTaxTotal'] = self._build_co_tax_total_node(
                withholding_taxes, vals
            )
        else:
            document_node['cac:WithholdingTaxTotal'] = None

    def _get_co_tax_data(self, vals):
        """Aggregate tax amounts grouped by DIAN tax code.

        Returns a dict like:
        {
            '01': {'amount': 190000.00, 'base': 1000000.00, 'percent': 19.0, 'name': 'IVA'},
            '04': {'amount': 0.00, 'base': 0.00, 'percent': 0.0, 'name': 'INC'},
        }
        """
        invoice = vals['invoice']
        result = {}

        for line in invoice.line_ids.filtered(lambda l: l.tax_line_id):
            tax = line.tax_line_id
            dian_code = invoice._l10n_co_edi_get_dian_tax_code(tax)
            if not dian_code:
                continue

            if dian_code not in result:
                result[dian_code] = {
                    'amount': 0.0,
                    'base': 0.0,
                    'percent': abs(tax.amount) if tax.amount_type == 'percent' else 0.0,
                    'name': DIAN_TAX_CODES.get(dian_code, ''),
                }

            result[dian_code]['amount'] += abs(line.balance)
            result[dian_code]['base'] += abs(line.tax_base_amount)

        # Ensure IVA is always present (even if zero)
        if '01' not in result:
            result['01'] = {
                'amount': 0.0,
                'base': abs(invoice.amount_untaxed_signed),
                'percent': 0.0,
                'name': 'IVA',
            }

        return result

    def _build_co_tax_total_node(self, tax_data, vals):
        """Build a cac:TaxTotal node from aggregated DIAN tax data."""
        total_amount = sum(d['amount'] for d in tax_data.values())
        currency_dp = vals.get('currency_dp', 2)
        currency_name = vals.get('currency_name', 'COP')

        subtotals = []
        for code in sorted(tax_data.keys()):
            data = tax_data[code]
            subtotals.append({
                'cbc:TaxableAmount': {
                    '_text': self.format_float(data['base'], currency_dp),
                    'currencyID': currency_name,
                },
                'cbc:TaxAmount': {
                    '_text': self.format_float(data['amount'], currency_dp),
                    'currencyID': currency_name,
                },
                'cac:TaxCategory': {
                    'cbc:Percent': {'_text': self.format_float(data['percent'], 2)},
                    'cac:TaxScheme': {
                        'cbc:ID': {'_text': code},
                        'cbc:Name': {'_text': data['name']},
                    },
                },
            })

        return {
            'cbc:TaxAmount': {
                '_text': self.format_float(total_amount, currency_dp),
                'currencyID': currency_name,
            },
            'cac:TaxSubtotal': subtotals,
        }

    def _get_tax_category_node(self, vals):
        """Override to use DIAN tax type codes instead of generic VAT."""
        grouping_key = vals['grouping_key']

        # Map tax category code to DIAN tax code
        dian_code = '01'  # Default: IVA
        dian_name = 'IVA'

        tax_category = grouping_key.get('tax_category_code', '')
        if tax_category in DIAN_TAX_CODES:
            dian_code = tax_category
            dian_name = DIAN_TAX_CODES[tax_category]

        return {
            'cbc:Percent': {'_text': grouping_key['amount']} if grouping_key.get('amount_type') == 'percent' else None,
            'cac:TaxScheme': {
                'cbc:ID': {'_text': dian_code},
                'cbc:Name': {'_text': dian_name},
            },
        }

    # -------------------------------------------------------------------------
    # EXPORT: Payment Means (DIAN codes)
    # -------------------------------------------------------------------------

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        """Override to use DIAN payment means codes."""
        invoice = vals['invoice']

        # DIAN payment means: 1=Contado, 2=Credito
        payment_means_code = '2' if invoice.invoice_date_due != invoice.invoice_date else '1'

        # DIAN payment method code
        # 10=Cash, 42=Bank transfer, 47=Transfer between accounts
        payment_method_code = '42'  # Default: bank transfer
        if invoice.partner_bank_id:
            payment_method_code = '42'

        document_node['cac:PaymentMeans'] = {
            'cbc:ID': {'_text': payment_means_code},
            'cbc:PaymentMeansCode': {'_text': payment_method_code},
            'cbc:PaymentDueDate': {'_text': invoice.invoice_date_due or invoice.invoice_date},
            'cbc:PaymentID': {'_text': invoice.payment_reference or invoice.name},
        }

    # -------------------------------------------------------------------------
    # EXPORT: Billing Reference (for credit/debit notes)
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes_billing_reference(self, document_node, vals):
        """Add BillingReference for credit/debit notes referencing original invoice."""
        invoice = vals['invoice']
        if vals['document_type'] in ('credit_note', 'debit_note'):
            # Find the referenced invoice
            ref_move = invoice.reversed_entry_id or invoice.debit_origin_id if hasattr(invoice, 'debit_origin_id') else None
            if ref_move:
                document_node['cac:BillingReference'] = {
                    'cac:InvoiceDocumentReference': {
                        'cbc:ID': {'_text': ref_move.name},
                        'cbc:UUID': {
                            '_text': ref_move.l10n_co_edi_cufe_cude or '',
                            'schemeName': 'CUFE-SHA384',
                        },
                        'cbc:IssueDate': {'_text': ref_move.invoice_date},
                    },
                }

                # DiscrepancyResponse for credit notes
                if vals['document_type'] == 'credit_note':
                    document_node['cac:DiscrepancyResponse'] = {
                        'cbc:ReferenceID': {'_text': ref_move.name},
                        'cbc:ResponseCode': {'_text': '2'},  # 2=Correccion
                        'cbc:Description': {'_text': invoice.ref or 'Correccion de factura'},
                    }

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals)

        company = invoice.company_id
        partner = invoice.commercial_partner_id

        if not company.vat:
            constraints['co_company_nit'] = _('Company NIT is required for DIAN electronic invoicing.')

        if not partner.vat and not partner.l10n_latam_identification_type_id:
            constraints['co_partner_id'] = _('Customer identification (NIT/CC/CE) is required.')

        if not company.l10n_co_edi_software_id:
            constraints['co_software_id'] = _('DIAN Software ID is not configured.')

        return constraints
