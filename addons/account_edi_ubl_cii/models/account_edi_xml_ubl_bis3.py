from odoo import _, api, models
from odoo.tools.misc import str2bool
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES

from stdnum.no import mva
from stdnum.be import vat as be_vat
CHORUS_PRO_PEPPOL_ID = "0009:11000201100044"


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _name = "account.edi.xml.ubl_bis3"
    _inherit = ['account.edi.xml.ubl_21', 'account.edi.ubl_pint_eu']
    _description = "UBL BIS Billing 3.0.12"

    """
    * Documentation of EHF Billing 3.0: https://anskaffelser.dev/postaward/g3/
    * EHF 2.0 is no longer used:
      https://anskaffelser.dev/postaward/g2/announcement/2019-11-14-removal-old-invoicing-specifications/
    * Official doc for EHF Billing 3.0 is the OpenPeppol BIS 3 doc +
      https://anskaffelser.dev/postaward/g3/spec/current/billing-3.0/norway/

        "Based on work done in PEPPOL BIS Billing 3.0, Difi has included Norwegian rules in PEPPOL BIS Billing 3.0 and
        does not see a need to implement a different CIUS targeting the Norwegian market. Implementation of EHF Billing
        3.0 is therefore done by implementing PEPPOL BIS Billing 3.0 without extensions or extra rules."

    Thus, EHF 3 and Bis 3 are actually the same format. The specific rules for NO defined in Bis 3 are added in Bis 3.
    """

    @api.model
    def _is_customer_behind_chorus_pro(self, customer):
        return customer.peppol_eas and customer.peppol_endpoint and f"{customer.peppol_eas}:{customer.peppol_endpoint}" == CHORUS_PRO_PEPPOL_ID

    def _import_invoice_ubl_cii(self, invoice, file_data, new=False):
        return self._ubl_import_invoice(invoice, file_data, new=new)

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_bis3.xml"

    def _export_invoice_ecosio_schematrons(self):
        return {
            'invoice': 'eu.peppol.bis3:invoice:3.13.0',
            'credit_note': 'eu.peppol.bis3:creditnote:3.13.0',
        }

    def _get_country_vals(self, country):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_country_vals(country)

        vals.pop('name', None)

        return vals

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        if not partner.vat or partner.vat == '/':
            return [{
                'company_id': partner.peppol_endpoint,
                'tax_scheme_vals': {'id': partner.peppol_eas},
            }]

        for vals in vals_list:
            vals.pop('registration_name', None)
            vals.pop('registration_address_vals', None)

        # sources:
        #  https://anskaffelser.dev/postaward/g3/spec/current/billing-3.0/norway/#_applying_foretaksregisteret
        #  https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules (NO-R-002 (warning))
        if partner.country_id.code == "NO" and role == 'supplier':
            vals_list.append({
                'company_id': "Foretaksregisteret",
                'tax_scheme_vals': {'id': 'TAX'},
            })

        # source:
        # https://docs.peppol.eu/poacc/billing/3.0/2025-Q4/rules/ubl-peppol/SE-R-005/
        # https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules (SE-R-005 (fatal))
        if partner.country_id.code == "SE" and role == 'supplier':
            vals_list.append({
                'company_id': "GODKÄND FÖR F-SKATT",
                'tax_scheme_vals': {'id': 'TAX'},
            })

        return vals_list

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)

        for vals in vals_list:
            vals.pop('registration_address_vals', None)
            if partner.country_code == 'NL':
                # For NL, VAT can be used as a Peppol endpoint, but KVK/OIN has to be used as PartyLegalEntity/CompanyID
                # To implement a workaround on stable, company_registry field is used without recording whether
                # the number is a KVK or OIN, and the length of the number (8 = KVK, 9 = OIN) is used to determine the type
                nl_id = partner.company_registry if partner.peppol_eas not in ('0106', '0190') else partner.peppol_endpoint
                vals.update({
                    'company_id': nl_id,
                    'company_id_attrs': {'schemeID': '0190' if nl_id and len(nl_id) == 20 else '0106'},
                })
            if partner.country_id.code == "LU":
                if 'l10n_lu_peppol_identifier' in partner._fields and partner.l10n_lu_peppol_identifier:
                    vals['company_id'] = partner.l10n_lu_peppol_identifier
                elif partner.company_registry:
                    vals['company_id'] = partner.company_registry
            if partner.country_id.code == 'DK':
                # DK-R-014: For Danish Suppliers it is mandatory to specify schemeID as "0184" (DK CVR-number) when
                # PartyLegalEntity/CompanyID is used for AccountingSupplierParty
                vals['company_id_attrs'] = {'schemeID': '0184'}
            if partner.country_code == 'SE' and partner.company_registry:
                vals['company_id'] = ''.join(char for char in partner.company_registry if char.isdigit())
            if not vals['company_id']:
                vals['company_id'] = partner.peppol_endpoint

        return vals_list

    def _get_partner_contact_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_partner_contact_vals(partner)

        vals.pop('id', None)

        return vals

    def _get_partner_party_vals(self, partner, role):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        if (
            role == 'delivery'
            # If the user hasn't updated the module, we just don't render `DeliveryParty` because the UBL
            # to avoid generating an invalid UBL.
            and '<cac:Party>' not in self.env.ref('account_edi_ubl_cii.ubl_20_DeliveryType').arch
        ):
            return {
                'party_vals': {
                    'party_name_vals': [
                        {
                            'name': partner.display_name,
                        }
                    ],
                }
            }
        else:
            vals = super()._get_partner_party_vals(partner, role)

            partner = partner.commercial_partner_id
            vals.update({
                'endpoint_id': partner.peppol_endpoint,
                'endpoint_id_attrs': {'schemeID': partner.peppol_eas},
            })
            return vals

    def _get_partner_party_identification_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_partner_party_identification_vals_list(partner)

        if partner.country_code == 'NL' and partner.peppol_endpoint:
            # [UBL-SR-16] Buyer identifier shall occur maximum once
            if self._context.get('ubl_partner_role') == 'customer':
                vals = [{'id': partner.peppol_endpoint}]
            else:
                vals.append({
                    'id': partner.peppol_endpoint,
                })
        return vals

    def _get_delivery_vals_list(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.partner_id

        intracom_delivery = (customer.country_id.code in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES
                             and supplier.country_id.code in EUROPEAN_ECONOMIC_AREA_COUNTRY_CODES
                             and supplier.country_id != customer.country_id)

        # [BR-IC-12]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
        # "Intra-community supply" the Deliver to country code (BT-80) shall not be blank.

        # [BR-IC-11]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
        # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14)
        # shall not be blank.

        if intracom_delivery:
            partner_shipping = invoice.partner_shipping_id or customer

            return [{
                'actual_delivery_date': invoice.invoice_date,
                'delivery_location_vals': {
                    'delivery_address_vals': self._get_partner_address_vals(partner_shipping),
                },
                'delivery_party_vals': self._get_partner_party_vals(invoice.partner_shipping_id, 'delivery') if invoice.partner_shipping_id else {},
            }]

        return super()._get_delivery_vals_list(invoice)

    def _get_partner_address_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_partner_address_vals(partner)
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-225]-A UBL invoice should not include the AccountingCustomerParty Party PostalAddress CountrySubentityCode
        vals.pop('country_subentity_code', None)
        return vals

    def _get_financial_institution_branch_vals(self, bank):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_financial_institution_branch_vals(bank)
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-664]-A UBL invoice should not include the FinancialInstitutionBranch FinancialInstitution
        # xpath test: not(//cac:FinancialInstitution)
        vals.pop('id_attrs', None)
        vals.pop('financial_institution_vals', None)
        return vals

    def _get_invoice_payment_means_vals_list(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_invoice_payment_means_vals_list(invoice)

        for vals in vals_list:
            vals.pop('payment_due_date', None)
            vals.pop('instruction_id', None)
            if vals.get('payment_id_vals'):
                vals['payment_id_vals'] = vals['payment_id_vals'][:1]

        return vals_list

    def _get_tax_category_list(self, customer, supplier, taxes):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_tax_category_list(customer, supplier, taxes)

        for vals in vals_list:
            vals.pop('name', None)

        return vals_list

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)

        for vals in vals_list:
            vals['currency_dp'] = 2
            for subtotal_vals in vals.get('tax_subtotal_vals', []):
                subtotal_vals.pop('percent', None)
                subtotal_vals['currency_dp'] = 2

        return vals_list

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        line_item_vals = super()._get_invoice_line_item_vals(line, taxes_vals)

        for val in line_item_vals['classified_tax_category_vals']:
            # [UBL-CR-600] A UBL invoice should not include the InvoiceLine Item ClassifiedTaxCategory TaxExemptionReasonCode
            val.pop('tax_exemption_reason_code', None)
            # [UBL-CR-601] TaxExemptionReason must not appear in InvoiceLine Item ClassifiedTaxCategory
            # [BR-E-10] TaxExemptionReason must only appear in TaxTotal TaxSubtotal TaxCategory
            val.pop('tax_exemption_reason', None)

        return line_item_vals

    def _get_invoice_line_allowance_vals_list(self, line, tax_values_list=None):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals_list = super()._get_invoice_line_allowance_vals_list(line, tax_values_list=tax_values_list)

        for vals in vals_list:
            vals['currency_dp'] = 2

        return vals_list

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._get_invoice_line_vals(line, line_id, taxes_vals)

        vals.pop('tax_total_vals', None)

        vals['currency_dp'] = 2
        vals['price_vals']['currency_dp'] = 2

        if line.currency_id.compare_amounts(vals['price_vals']['price_amount'], 0) == -1:
            # We can't have negative unit prices, so we invert the signs of
            # the unit price and quantity, resulting in the same amount in the end
            vals['price_vals']['price_amount'] *= -1
            vals['line_quantity'] *= -1

        return vals

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        # Old helper not used by default (see _export_invoice override)
        # If you change this method, please change the corresponding new helper (at the end of this file).
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            'customization_id': self._get_customization_ids()['ubl_bis3'],
            'profile_id': 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0',
            'currency_dp': 2,
            'ubl_version_id': None,
        })
        vals['vals']['monetary_total_vals']['currency_dp'] = 2

        # [NL-R-001] For suppliers in the Netherlands, if the document is a creditnote, the document MUST
        # contain an invoice reference (cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID)
        if vals['supplier'].country_id.code == 'NL' and 'refund' in invoice.move_type:
            vals['vals'].update({
                'billing_reference_vals': {
                    'id': invoice.ref,
                    'issue_date': None,
                }
            })

        # For B2G transactions in Germany: set the buyer_reference to the Leitweg-ID (code 0204)
        if invoice.commercial_partner_id.peppol_eas == '0204':
            vals['vals'].update({
                'buyer_reference': invoice.commercial_partner_id.peppol_endpoint,
            })

        return vals

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account.edi.xml.ubl_21
        constraints = super()._export_invoice_constraints(invoice, vals)

        constraints.update(
            self._invoice_constraints_peppol_en16931_ubl(invoice, vals)
        )
        constraints.update(
            self._invoice_constraints_cen_en16931_ubl(invoice, vals)
        )

        return constraints

    def _invoice_constraints_cen_en16931_ubl(self, invoice, vals):
        """
        corresponds to the errors raised by ' schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt' for invoices.
        This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/CEN-EN16931-UBL.sch.
        """
        eu_countries = self.env.ref('base.europe').country_ids
        intracom_delivery = (vals['customer'].country_id in eu_countries
                             and vals['supplier'].country_id in eu_countries
                             and vals['customer'].country_id != vals['supplier'].country_id)

        constraints = {
            # [BR-61]-If the Payment means type code (BT-81) means SEPA credit transfer, Local credit transfer or
            # Non-SEPA international credit transfer, the Payment account identifier (BT-84) shall be present.
            # note: Payment account identifier is <cac:PayeeFinancialAccount>
            # note: no need to check account_number, because it's a required field for a partner_bank
            'cen_en16931_payment_account_identifier': self._check_required_fields(
                invoice, 'partner_bank_id'
            ) if vals['vals']['payment_means_vals_list'][0]['payment_means_code'] in (30, 58) else None,
            # [BR-IC-12]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Deliver to country code (BT-80) shall not be blank.
            'cen_en16931_delivery_country_code': self._check_required_fields(
                vals['vals']['delivery_vals_list'][0], 'delivery_location_vals',
                _("For intracommunity supply, the delivery address should be included.")
            ) if intracom_delivery else None,

            # [BR-IC-11]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14)
            # shall not be blank.
            'cen_en16931_delivery_date_invoicing_period': self._check_required_fields(
                vals['vals']['delivery_vals_list'][0], 'actual_delivery_date',
                _("For intracommunity supply, the actual delivery date or the invoicing period should be included.")
            ) and self._check_required_fields(
                vals['vals']['invoice_period_vals_list'][0], ['start_date', 'end_date'],
                _("For intracommunity supply, the actual delivery date or the invoicing period should be included.")
            ) if intracom_delivery else None,
        }

        for line_vals in vals['vals']['line_vals']:
            if not line_vals['item_vals'].get('name'):
                # [BR-25]-Each Invoice line (BG-25) shall contain the Item name (BT-153).
                constraints.update({'cen_en16931_item_name': _("Each invoice line should have a product or a label.")})
                break

        for line in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section')):
            if len(line.tax_ids.flatten_taxes_hierarchy().filtered(lambda t: t.amount_type != 'fixed')) != 1:
                # [UBL-SR-48]-Invoice lines shall have one and only one classified tax category.
                # /!\ exception: possible to have any number of ecotaxes (fixed tax) with a regular percentage tax
                constraints.update({'cen_en16931_tax_line': _("Each invoice line shall have one and only one tax.")})

        for role in ('supplier', 'customer'):
            constraints[f'cen_en16931_{role}_country'] = self._check_required_fields(
                vals['vals'][f'accounting_{role}_party_vals']['party_vals']['postal_address_vals']['country_vals'],
                'identification_code',
                _("The country is required for the %s.", role)
            )
            scheme_vals = vals['vals'][f'accounting_{role}_party_vals']['party_vals']['party_tax_scheme_vals'][-1:]
            if (
                not (scheme_vals and scheme_vals[0]['company_id'] and scheme_vals[0]['company_id'][:2].isalpha())
                and (scheme_vals and scheme_vals[0]['tax_scheme_vals'].get('id') == 'VAT')
                and self._name in ('account.edi.xml.ubl_bis3', 'account.edi.xml.ubl_nl', 'account.edi.xml.ubl_de')
            ):
                # [BR-CO-09]-The Seller VAT identifier (BT-31), the Seller tax representative VAT identifier (BT-63)
                # and the Buyer VAT identifier (BT-48) shall have a prefix in accordance with ISO code ISO 3166-1
                # alpha-2 by which the country of issue may be identified. Nevertheless, Greece may use the prefix 'EL'.
                constraints.update({f'cen_en16931_{role}_vat_country_code': _(
                    "The VAT of the %s should be prefixed with its country code.", role)})

        if invoice.partner_shipping_id:
            # [BR-57]-Each Deliver to address (BG-15) shall contain a Deliver to country code (BT-80).
            constraints['cen_en16931_delivery_address'] = self._check_required_fields(invoice.partner_shipping_id, 'country_id')
        return constraints

    def _invoice_constraints_peppol_en16931_ubl(self, invoice, vals):
        """
        corresponds to the errors raised by 'schematron/openpeppol/3.13.0/xslt/PEPPOL-EN16931-UBL.xslt' for
        invoices in ecosio. This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/PEPPOL-EN16931-UBL.sch.

        The national rules (https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules) are included in this file.
        They always refer to the supplier's country.
        """
        constraints = {
            # PEPPOL-EN16931-R003: A buyer reference or purchase order reference MUST be provided.
            'peppol_en16931_ubl_buyer_ref_po_ref':
                "A buyer reference or purchase order reference must be provided." if self._check_required_fields(
                    vals['vals'], 'buyer_reference'
                ) and self._check_required_fields(vals['vals'], 'order_reference') else None,
        }

        if vals['supplier'].country_id.code == 'NL':
            constraints.update({
                # [NL-R-001] For suppliers in the Netherlands, if the document is a creditnote, the document MUST contain
                # an invoice reference (cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID)
                'nl_r_001': self._check_required_fields(invoice, 'ref') if 'refund' in invoice.move_type else '',

                # [NL-R-002] For suppliers in the Netherlands the supplier’s address (cac:AccountingSupplierParty/cac:Party
                # /cac:PostalAddress) MUST contain street name (cbc:StreetName), city (cbc:CityName) and post code (cbc:PostalZone)
                'nl_r_002_street': self._check_required_fields(vals['supplier'], 'street'),
                'nl_r_002_zip': self._check_required_fields(vals['supplier'], 'zip'),
                'nl_r_002_city': self._check_required_fields(vals['supplier'], 'city'),

                # [NL-R-003] For suppliers in the Netherlands, the legal entity identifier MUST be either a
                # KVK or OIN number (schemeID 0106 or 0190)
                'nl_r_003': _(
                    "%s should have a KVK or OIN number set in Company ID field or as Peppol e-address (EAS code 0106 or 0190).",
                    vals['supplier'].display_name
                ) if (
                    not vals['supplier'].peppol_eas in ('0106', '0190') and
                    (not vals['supplier'].company_registry or len(vals['supplier'].company_registry) not in (8, 9))
                ) else '',

                # [NL-R-007] For suppliers in the Netherlands, the supplier MUST provide a means of payment
                # (cac:PaymentMeans) if the payment is from customer to supplier
                'nl_r_007': self._check_required_fields(invoice, 'partner_bank_id')
            })

            if vals['customer'].country_id.code == 'NL':
                constraints.update({
                    # [NL-R-004] For suppliers in the Netherlands, if the customer is in the Netherlands, the customer
                    # address (cac:AccountingCustomerParty/cac:Party/cac:PostalAddress) MUST contain the street name
                    # (cbc:StreetName), the city (cbc:CityName) and post code (cbc:PostalZone)
                    'nl_r_004_street': self._check_required_fields(vals['customer'], 'street'),
                    'nl_r_004_city': self._check_required_fields(vals['customer'], 'city'),
                    'nl_r_004_zip': self._check_required_fields(vals['customer'], 'zip'),

                    # [NL-R-005] For suppliers in the Netherlands, if the customer is in the Netherlands,
                    # the customer’s legal entity identifier MUST be either a KVK or OIN number (schemeID 0106 or 0190)
                    'nl_r_005': _(
                        "%s should have a KVK or OIN number set in Company ID field or as Peppol e-address (EAS code 0106 or 0190).",
                        vals['customer'].display_name
                    ) if (
                        not vals['customer'].commercial_partner_id.peppol_eas in ('0106', '0190') and
                        (not vals['customer'].commercial_partner_id.company_registry or len(vals['customer'].commercial_partner_id.company_registry) not in (8, 9))
                    ) else '',
                })

        if vals['supplier'].country_id.code == 'NO':
            vat = vals['supplier'].vat
            constraints.update({
                # NO-R-001: For Norwegian suppliers, a VAT number MUST be the country code prefix NO followed by a
                # valid Norwegian organization number (nine numbers) followed by the letters MVA.
                # Note: mva.is_valid("179728982MVA") is True while it lacks the NO prefix
                'no_r_001': _(
                    "The VAT number of the supplier does not seem to be valid. It should be of the form: NO179728982MVA."
                ) if not mva.is_valid(vat) or len(vat) != 14 or vat[:2] != 'NO' or vat[-3:] != 'MVA' else "",
            })

        if vals['supplier'].country_id.code == 'BE' and vals['supplier'].company_registry:
            if not be_vat.is_valid(vals['supplier'].company_registry):
                constraints.update({
                    'PEPPOL-COMMON-R043_supplier': _('%s should have a valid KBO/BCE number in the Company ID field', vals['supplier'].display_name),
                })

        if vals['customer'].country_id.code == 'BE' and vals['customer'].company_registry:
            if not be_vat.is_valid(vals['customer'].company_registry):
                constraints.update({
                    'PEPPOL-COMMON-R043_customer': _('%s should have a valid KBO/BCE number in the Company ID field', vals['customer'].display_name),
                })
        return constraints

    def _import_retrieve_partner_vals(self, tree, role):
        # EXTENDS account.edi.xml.ubl_20
        partner_vals = super()._import_retrieve_partner_vals(tree, role)
        endpoint_node = tree.find(f'.//cac:{role}Party/cac:Party/cbc:EndpointID', UBL_NAMESPACES)
        if endpoint_node is not None:
            peppol_eas = endpoint_node.attrib.get('schemeID')
            peppol_endpoint = endpoint_node.text
            if peppol_eas and peppol_endpoint:
                # include the EAS and endpoint in the search domain when retrieving the partner
                partner_vals.update({
                    'peppol_eas': peppol_eas,
                    'peppol_endpoint': peppol_endpoint,
                })
        return partner_vals

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

    def _export_invoice(self, invoice, convert_fixed_taxes=True):
        # Use the new dict_to_xml helpers by default
        # unless the 'account_edi_ubl_cii.use_new_dict_to_xml_helpers' param is set to False.
        if str2bool(
            self.env['ir.config_parameter'].sudo().get_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True),
            default=True,
        ):
            return self._export_invoice_new(invoice)

        return super()._export_invoice(invoice, convert_fixed_taxes=convert_fixed_taxes)

    def _add_document_currency_vals(self, vals):
        super()._add_document_currency_vals(vals)
        vals['currency_dp'] = 2  # In BIS 3, always use 2 decimal places

    # -------------------------------------------------------------------------
    # EXPORT: BIS3 LAYER
    # -------------------------------------------------------------------------

    def _can_export_selfbilling(self):
        # Overridden in `account_peppol_selfbilling`
        return False

    def _add_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
        }
        self._ubl_add_accounting_supplier_party_node(sub_vals)

    def _add_invoice_accounting_customer_party_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
        }
        self._ubl_add_accounting_customer_party_node(sub_vals)

    def _add_invoice_delivery_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
        }
        self._ubl_add_invoice_delivery_nodes(sub_vals)

    def _add_invoice_allowance_charge_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_allowance_charge_nodes(sub_vals)

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        # OVERRIDE
        invoice = vals.get('invoice')
        if not invoice:
            return

        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_legal_monetary_total_node(sub_vals)

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_payment_means_nodes(sub_vals)

    def _add_invoice_payment_terms_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }

        self._ubl_add_payment_terms_nodes(sub_vals)

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_tax_totals_nodes(sub_vals)

    def _add_invoice_monetary_total_vals(self, vals):
        # OVERRIDE
        pass

    def _add_invoice_line_id_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_id_node(sub_vals)

    def _add_invoice_line_allowance_charge_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_allowance_charge_nodes(sub_vals)

    def _add_invoice_line_amount_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }

        if vals['document_type'] == 'credit_note':
            self._ubl_add_line_credited_quantity_node(sub_vals)
        else:
            self._ubl_add_line_invoiced_quantity_node(sub_vals)

        self._ubl_add_line_extension_amount_node(sub_vals)

    def _add_invoice_line_period_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_period_nodes(sub_vals)

    def _add_invoice_line_pricing_reference_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_pricing_reference_node(sub_vals)

    def _add_invoice_line_tax_total_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_tax_totals_nodes(sub_vals)

    def _add_invoice_line_tax_category_nodes(self, line_node, vals):
        # OVERRIDE
        pass

    def _add_invoice_line_item_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_item_node(sub_vals)

    def _add_invoice_line_price_nodes(self, line_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'line_node': line_node,
            'base_line': vals['line_vals']['base_line'],
        }
        self._ubl_add_line_price_node(sub_vals)

    def _ubl_add_invoice_line_node(self, vals):
        # OVERRIDE. For retro-compatibility, ensure '_get_invoice_line_node' is called.
        sub_vals = {
            **vals,
            'base_line': vals['line_vals']['base_line'],
        }
        vals['line_node'].update(self._get_invoice_line_node(sub_vals))

    def _ubl_add_credit_note_line_node(self, vals):
        # OVERRIDE. For retro-compatbility, ensure '_get_invoice_line_node' is called.
        sub_vals = {
            **vals,
            'base_line': vals['line_vals']['base_line'],
        }
        vals['line_node'].update(self._get_invoice_line_node(sub_vals))

    def _add_invoice_line_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        if vals['document_type'] == 'invoice':
            self._ubl_add_invoice_line_nodes(sub_vals)
        elif vals['document_type'] == 'credit_note':
            self._ubl_add_credit_note_line_nodes(sub_vals)

    def _add_invoice_header_nodes(self, document_node, vals):
        # OVERRIDE
        sub_vals = {
            **vals,
            'document_node': document_node,
            'currency': vals['currency_id'],
        }
        self._ubl_add_version_id_node(sub_vals)
        self._ubl_add_customization_id_node(sub_vals)
        self._ubl_add_profile_id_node(sub_vals)
        self._ubl_add_id_node(sub_vals)
        self._ubl_add_copy_indicator_node(sub_vals)
        self._ubl_add_issue_date_node(sub_vals)
        if vals['document_type'] == 'invoice':
            self._ubl_add_due_date_node(sub_vals)
            self._ubl_add_invoice_type_code_node(sub_vals)
        elif vals['document_type'] == 'credit_note':
            self._ubl_add_credit_note_type_code_node(sub_vals)
        self._ubl_add_notes_nodes(sub_vals)
        self._ubl_add_document_currency_code_node(sub_vals)
        self._ubl_add_tax_currency_code_node(sub_vals)
        self._ubl_add_buyer_reference_node(sub_vals)
        self._ubl_add_order_reference_node(sub_vals)
        self._ubl_add_billing_reference_nodes(sub_vals)

    def _add_invoice_config_vals(self, vals):
        super()._add_invoice_config_vals(vals)

        # There is no specifications for debit notes in BIS3, we'll concider them as invoices
        if vals['document_type'] == 'debit_note':
            vals['document_type'] = 'invoice'

        invoice = vals['invoice']
        vals.update(self._init_invoice_export_values(invoice))

    def _setup_base_lines(self, vals):
        # OVERRIDE
        pass

    def _add_invoice_base_lines_vals(self, vals):
        # OVERRIDE
        pass

    def _add_invoice_line_vals(self, vals):
        # OVERRIDE
        pass

    # -------------------------------------------------------------------------
    # EXPORT: Constraints for new helpers
    # -------------------------------------------------------------------------

    def _export_invoice_constraints_new(self, invoice, vals):
        constraints = self._export_document_node_constraints(vals)
        constraints.update(
            self._invoice_constraints_peppol_en16931_ubl_new(invoice, vals)
        )
        constraints.update(
            self._invoice_constraints_cen_en16931_ubl_new(invoice, vals)
        )
        return constraints

    def _invoice_constraints_cen_en16931_ubl_new(self, invoice, vals):
        return {}

    def _invoice_constraints_peppol_en16931_ubl_new(self, invoice, vals):
        """
        corresponds to the errors raised by 'schematron/openpeppol/3.13.0/xslt/PEPPOL-EN16931-UBL.xslt' for
        invoices in ecosio. This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/PEPPOL-EN16931-UBL.sch.

        The national rules (https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules) are included in this file.
        They always refer to the supplier's country.
        """
        constraints = {}

        if vals['supplier'].country_id.code == 'NO':
            vat = vals['supplier'].vat
            constraints.update({
                # NO-R-001: For Norwegian suppliers, a VAT number MUST be the country code prefix NO followed by a
                # valid Norwegian organization number (nine numbers) followed by the letters MVA.
                # Note: mva.is_valid("179728982MVA") is True while it lacks the NO prefix
                'no_r_001': _(
                    "The VAT number of the supplier does not seem to be valid. It should be of the form: NO179728982MVA."
                ) if not mva.is_valid(vat) or len(vat) != 14 or vat[:2] != 'NO' or vat[-3:] != 'MVA' else "",
            })

        if vals['supplier'].country_id.code == 'BE' and vals['supplier'].company_registry:
            if not be_vat.is_valid(vals['supplier'].company_registry):
                constraints.update({
                    'PEPPOL-COMMON-R043_supplier': _('%s should have a valid KBO/BCE number in the Company ID field', vals['supplier'].display_name),
                })

        if vals['customer'].country_id.code == 'BE' and vals['customer'].company_registry:
            if not be_vat.is_valid(vals['customer'].company_registry):
                constraints.update({
                    'PEPPOL-COMMON-R043_customer': _('%s should have a valid KBO/BCE number in the Company ID field', vals['customer'].display_name),
                })
        return constraints
