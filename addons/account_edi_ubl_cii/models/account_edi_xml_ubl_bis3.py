# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.tools.misc import str2bool
from odoo.addons.account.tools import dict_to_xml
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES

from stdnum.no import mva


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _name = "account.edi.xml.ubl_bis3"
    _inherit = 'account.edi.xml.ubl_21'
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
        vals = super()._get_country_vals(country)

        vals.pop('name', None)

        return vals

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        if not partner.vat:
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

        return vals_list

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_21
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
        vals = super()._get_partner_contact_vals(partner)

        vals.pop('id', None)

        return vals

    def _get_partner_party_vals(self, partner, role):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_party_vals(partner, role)

        partner = partner.commercial_partner_id
        vals.update({
            'endpoint_id': partner.peppol_endpoint,
            'endpoint_id_attrs': {'schemeID': partner.peppol_eas},
        })

        return vals

    def _get_partner_party_identification_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_party_identification_vals_list(partner)

        if partner.country_code == 'NL':
            vals.append({
                'id': partner.peppol_endpoint,
            })
        return vals

    def _get_delivery_vals_list(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.partner_id

        economic_area = self.env.ref('base.europe').country_ids.mapped('code') + ['NO']
        intracom_delivery = (customer.country_id.code in economic_area
                             and supplier.country_id.code in economic_area
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
            }]

        return super()._get_delivery_vals_list(invoice)

    def _get_partner_address_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_address_vals(partner)
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-225]-A UBL invoice should not include the AccountingCustomerParty Party PostalAddress CountrySubentityCode
        vals.pop('country_subentity_code', None)
        return vals

    def _get_financial_institution_branch_vals(self, bank):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_financial_institution_branch_vals(bank)
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-664]-A UBL invoice should not include the FinancialInstitutionBranch FinancialInstitution
        # xpath test: not(//cac:FinancialInstitution)
        vals.pop('id_attrs', None)
        vals.pop('financial_institution_vals', None)
        return vals

    def _get_invoice_payment_means_vals_list(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_invoice_payment_means_vals_list(invoice)

        for vals in vals_list:
            vals.pop('payment_due_date', None)
            vals.pop('instruction_id', None)
            if vals.get('payment_id_vals'):
                vals['payment_id_vals'] = vals['payment_id_vals'][:1]

        return vals_list

    def _get_tax_category_list(self, customer, supplier, taxes):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_tax_category_list(customer, supplier, taxes)

        for vals in vals_list:
            vals.pop('name', None)

        return vals_list

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)

        for vals in vals_list:
            vals['currency_dp'] = 2
            for subtotal_vals in vals.get('tax_subtotal_vals', []):
                subtotal_vals.pop('percent', None)
                subtotal_vals['currency_dp'] = 2

        return vals_list

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
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
        vals_list = super()._get_invoice_line_allowance_vals_list(line, tax_values_list=tax_values_list)

        for vals in vals_list:
            vals['currency_dp'] = 2

        return vals_list

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        # EXTENDS account.edi.xml.ubl_21
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
                # alpha-2 by which the country of issue may be identified. Nevertheless, Greece may use the prefix ‘EL’.
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
        # Only for BIS3 invoices: if the 'account_edi_ubl_cii.use_new_dict_to_xml_helpers' param is set,
        # use the new dict_to_xml helpers.
        if (
            self._name == 'account.edi.xml.ubl_bis3'
            and str2bool(
                self.env['ir.config_parameter'].sudo().get_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True),
                default=True,
            )
        ):
            return self._export_invoice_new(invoice)

        return super()._export_invoice(invoice, convert_fixed_taxes=convert_fixed_taxes)

    def _add_document_currency_vals(self, vals):
        super()._add_document_currency_vals(vals)
        vals['currency_dp'] = 2  # In BIS 3, always use 2 decimal places

    # -------------------------------------------------------------------------
    # EXPORT: Templates for invoice header nodes
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        # Call the parent method from UBL 2.1
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']

        # Override specific BIS3 values
        document_node.update({
            'cbc:UBLVersionID': None,
            'cbc:CustomizationID': {'_text': self._get_customization_ids()['ubl_bis3']},
            'cbc:ProfileID': {'_text': 'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0'},
        })

        # [NL-R-001] For suppliers in the Netherlands, if the document is a creditnote, the document MUST
        # contain an invoice reference (cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID)
        if vals['supplier'].country_id.code == 'NL' and 'refund' in invoice.move_type:
            document_node['cac:BillingReference'] = {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': invoice.ref},
                }
            }

    def _add_invoice_delivery_nodes(self, document_node, vals):
        """ [BR-IC-12]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
        "Intra-community supply" the Deliver to country code (BT-80) shall not be blank.

        [BR-IC-11]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
        "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14)
        shall not be blank.
        """
        super()._add_invoice_delivery_nodes(document_node, vals)

        invoice = vals['invoice']
        customer = vals['customer']
        supplier = vals['supplier']
        intracom_delivery = (
            customer.country_id.code in (economic_area := self.env.ref('base.europe').country_ids.mapped('code') + ['NO'])
            and supplier.country_id.code in economic_area
            and supplier.country_id != customer.country_id
        )
        if intracom_delivery:
            document_node['cac:Delivery'] = {
                'cbc:ActualDeliveryDate': {'_text': invoice.invoice_date},
                'cac:DeliveryLocation': {
                    'cac:Address': self._get_address_node({'partner': vals['partner_shipping']})
                },
            }

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        super()._add_invoice_payment_means_nodes(document_node, vals)
        document_node['cac:PaymentMeans']['cbc:PaymentDueDate'] = None
        document_node['cac:PaymentMeans']['cbc:InstructionID'] = None

    def _get_address_node(self, vals):
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-225]-A UBL invoice should not include the AccountingCustomerParty Party PostalAddress CountrySubentityCode
        address_node = super()._get_address_node(vals)
        address_node['cbc:CountrySubentityCode'] = None
        address_node['cac:Country']['cbc:Name'] = None
        return address_node

    def _get_party_node(self, vals):
        party_node = super()._get_party_node(vals)

        partner = vals['partner']
        role = vals['role']
        commercial_partner = partner.commercial_partner_id

        if commercial_partner.peppol_endpoint:
            party_node['cbc:EndpointID'] = {
                '_text': commercial_partner.peppol_endpoint,
                'schemeID': commercial_partner.peppol_eas
            }

        if commercial_partner.country_code == 'NL':
            party_node['cac:PartyIdentification'] = [
                party_node['cac:PartyIdentification'],
                {
                    'cbc:ID': {'_text': commercial_partner.peppol_endpoint}
                }
            ]

        party_node['cac:PartyTaxScheme'] = party_tax_scheme = [
            {
                'cbc:CompanyID': {'_text': commercial_partner.vat or commercial_partner.peppol_endpoint},
                'cac:TaxScheme': {
                    # [BR-CO-09] if the PartyTaxScheme/TaxScheme/ID == 'VAT', CompanyID must start with a country code prefix.
                    # In some countries however, the CompanyID can be with or without country code prefix and still be perfectly
                    # valid (RO, HU, non-EU countries).
                    # We have to handle their cases by changing the TaxScheme/ID to 'something other than VAT',
                    # preventing the trigger of the rule.
                    'cbc:ID': {'_text': (
                        'NOT_EU_VAT' if commercial_partner.country_id and commercial_partner.vat and not commercial_partner.vat[:2].isalpha()
                        else 'VAT' if commercial_partner.vat
                        else commercial_partner.peppol_eas
                    )},
                },
            }
        ]
        if partner.country_id.code == "NO" and role == 'supplier':
            party_tax_scheme.append({
                'cbc:CompanyID': {'_text': "Foretaksregisteret"},
                'cac:TaxScheme': {'cbc:ID': {'_text': 'TAX'}},
            })

        if commercial_partner.country_code == 'NL':
            # For NL, VAT can be used as a Peppol endpoint, but KVK/OIN has to be used as PartyLegalEntity/CompanyID
            # To implement a workaround on stable, company_registry field is used without recording whether
            # the number is a KVK or OIN, and the length of the number (8 = KVK, 9 = OIN) is used to determine the type
            nl_id = commercial_partner.company_registry if commercial_partner.peppol_eas not in ('0106', '0190') else commercial_partner.peppol_endpoint
            party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {
                '_text': nl_id,
                'schemeID': '0190' if nl_id and len(nl_id) == 9 else '0106'
            }
        elif commercial_partner.country_id.code == 'LU' and commercial_partner.company_registry:
            party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {
                '_text': commercial_partner.company_registry
            }
        elif commercial_partner.country_code == 'SE' and commercial_partner.company_registry:
            party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {
                '_text': ''.join(char for char in commercial_partner.company_registry if char.isdigit
                ())
            }
        else:
            party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {
                '_text': commercial_partner.vat or commercial_partner.peppol_endpoint,
                # DK-R-014: For Danish Suppliers it is mandatory to specify schemeID as "0184" (DK CVR-number) when
                # PartyLegalEntity/CompanyID is used for AccountingSupplierParty
                'schemeID': '0184' if commercial_partner.country_id.code == 'DK' else None
            }

        party_node['cac:PartyLegalEntity']['cac:RegistrationAddress'] = None

        party_node['cac:Contact']['cbc:ID'] = None
        return party_node

    def _get_financial_account_node(self, vals):
        # schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt
        # [UBL-CR-664]-A UBL invoice should not include the FinancialInstitutionBranch FinancialInstitution
        # xpath test: not(//cac:FinancialInstitution)
        financial_account_node = super()._get_financial_account_node(vals)

        if financial_account_node['cac:FinancialInstitutionBranch']:
            financial_account_node['cac:FinancialInstitutionBranch']['cac:FinancialInstitution'] = None

            if financial_account_node['cac:FinancialInstitutionBranch']['cbc:ID']:
                financial_account_node['cac:FinancialInstitutionBranch']['cbc:ID']['schemeID'] = None

        return financial_account_node

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document amount nodes
    # -------------------------------------------------------------------------

    def _get_tax_subtotal_node(self, vals):
        # Compute total tax amount
        tax_subtotal_node = super()._get_tax_subtotal_node(vals)
        tax_subtotal_node['cbc:Percent'] = None
        return tax_subtotal_node

    def _get_tax_category_node(self, vals):
        grouping_key = vals['grouping_key']
        return {
            'cbc:ID': {'_text': grouping_key['tax_category_code']},
            'cbc:Percent': {'_text': grouping_key['amount']},
            'cbc:TaxExemptionReasonCode': {'_text': grouping_key.get('tax_exemption_reason_code')},
            'cbc:TaxExemptionReason': {'_text': grouping_key.get('tax_exemption_reason')},
            'cac:TaxScheme': {
                'cbc:ID': {'_text': 'VAT'}
            }
        }

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document level allowance/charge nodes
    # -------------------------------------------------------------------------

    def _get_document_allowance_charge_node(self, vals):
        allowance_charge_node = super()._get_document_allowance_charge_node(vals)
        allowance_charge_node['cbc:MultiplierFactorNumeric'] = None
        return allowance_charge_node

    # -------------------------------------------------------------------------
    # EXPORT: Templates for line nodes
    # -------------------------------------------------------------------------

    def _add_document_line_amount_nodes(self, line_node, vals):
        super()._add_document_line_amount_nodes(line_node, vals)
        # We can't have negative unit prices, so we invert the signs of
        # the unit price and quantity, resulting in the same amount in the end
        quantity_tag = self._get_tags_for_document_type(vals)['line_quantity']
        if vals['base_line']['price_unit'] < 0.0:
            line_node[quantity_tag]['_text'] = -vals['base_line']['quantity']

    def _add_document_line_tax_total_nodes(self, line_node, vals):
        # TaxTotal should not be used in BIS 3.0
        pass

    def _add_document_line_tax_category_nodes(self, line_node, vals):
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])

        line_node['cac:Item']['cac:ClassifiedTaxCategory'] = [
            # [UBL-CR-600] A UBL invoice should not include the InvoiceLine Item ClassifiedTaxCategory TaxExemptionReasonCode
            # [UBL-CR-601] TaxExemptionReason must not appear in InvoiceLine Item ClassifiedTaxCategory
            # [BR-E-10] TaxExemptionReason must only appear in TaxTotal TaxSubtotal TaxCategory
            self._get_tax_category_node({
                **vals,
                'grouping_key': {
                    **grouping_key,
                    'tax_exemption_reason_code': None,
                    'tax_exemption_reason': None,
                }
            })
            for grouping_key in aggregated_tax_details
            if grouping_key
        ]

    def _add_document_line_price_nodes(self, line_node, vals):
        super()._add_document_line_price_nodes(line_node, vals)
        if vals['base_line']['price_unit'] < 0.0:
            line_node['cac:Price']['cbc:PriceAmount']['_text'] = -line_node['cac:Price']['cbc:PriceAmount']['_text']

    # -------------------------------------------------------------------------
    # EXPORT: Constraints for new helpers
    # -------------------------------------------------------------------------

    def _export_invoice_constraints_new(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals)
        constraints.update(
            self._invoice_constraints_peppol_en16931_ubl_new(invoice, vals)
        )
        constraints.update(
            self._invoice_constraints_cen_en16931_ubl_new(invoice, vals)
        )
        return constraints

    def _invoice_constraints_cen_en16931_ubl_new(self, invoice, vals):
        """
        corresponds to the errors raised by ' schematron/openpeppol/3.13.0/xslt/CEN-EN16931-UBL.xslt' for invoices.
        This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/CEN-EN16931-UBL.sch.
        """
        eu_countries = self.env.ref('base.europe').country_ids
        intracom_delivery = (vals['customer'].country_id in eu_countries
                             and vals['supplier'].country_id in eu_countries
                             and vals['customer'].country_id != vals['supplier'].country_id)

        nsmap = self._get_document_nsmap(vals)

        constraints = {
            # [BR-61]-If the Payment means type code (BT-81) means SEPA credit transfer, Local credit transfer or
            # Non-SEPA international credit transfer, the Payment account identifier (BT-84) shall be present.
            # note: Payment account identifier is <cac:PayeeFinancialAccount>
            # note: no need to check account_number, because it's a required field for a partner_bank
            'cen_en16931_payment_account_identifier': self._check_required_fields(
                invoice, 'partner_bank_id'
            ) if vals['document_node']['cac:PaymentMeans']['cbc:PaymentMeansCode']['_text'] in (30, 58) else None,
            # [BR-IC-12]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Deliver to country code (BT-80) shall not be blank.
            'cen_en16931_delivery_country_code': (
                _("For intracommunity supply, the delivery address should be included.")
            ) if intracom_delivery and dict_to_xml(vals['document_node']['cac:Delivery']['cac:DeliveryLocation'], nsmap=nsmap, tag='cac:DeliveryLocation') is None else None,

            # [BR-IC-11]-In an Invoice with a VAT breakdown (BG-23) where the VAT category code (BT-118) is
            # "Intra-community supply" the Actual delivery date (BT-72) or the Invoicing period (BG-14)
            # shall not be blank.
            'cen_en16931_delivery_date_invoicing_period': (
                _("For intracommunity supply, the actual delivery date or the invoicing period should be included.")
                if (
                    intracom_delivery
                    and dict_to_xml(vals['document_node']['cac:Delivery']['cbc:ActualDeliveryDate'], nsmap=nsmap, tag='cbc:ActualDeliveryDate') is None
                    and dict_to_xml(vals['document_node']['cac:InvoicePeriod'], nsmap=nsmap, tag='cac:InvoicePeriod') is None
                )
                else None
            )
        }

        line_tag = self._get_tags_for_document_type(vals)['document_line']
        line_nodes = vals['document_node'][line_tag]

        for line_node in line_nodes:
            if not line_node['cac:Item']['cbc:Name']['_text']:
                # [BR-25]-Each Invoice line (BG-25) shall contain the Item name (BT-153).
                constraints.update({'cen_en16931_item_name': _("Each invoice line should have a product or a label.")})
                break

        for line in invoice.invoice_line_ids.filtered(lambda x: x.display_type not in ('line_note', 'line_section')):
            if len(line.tax_ids.flatten_taxes_hierarchy().filtered(lambda t: t.amount_type != 'fixed')) != 1:
                # [UBL-SR-48]-Invoice lines shall have one and only one classified tax category.
                # /!\ exception: possible to have any number of ecotaxes (fixed tax) with a regular percentage tax
                constraints.update({'cen_en16931_tax_line': _("Each invoice line shall have one and only one tax.")})

        for role in ('supplier', 'customer'):
            party_node = vals['document_node']['cac:AccountingCustomerParty'] if role == 'customer' else vals['document_node']['cac:AccountingSupplierParty']
            constraints[f'cen_en16931_{role}_country'] = (
                _("The country is required for the %s.", role)
                if not party_node['cac:Party']['cac:PostalAddress']['cac:Country']['cbc:IdentificationCode']['_text']
                else None
            )
            tax_scheme_node = party_node['cac:Party']['cac:PartyTaxScheme']
            if tax_scheme_node and (
                self._name in ('account.edi.xml.ubl_bis3', 'account.edi.xml.ubl_nl', 'account.edi.xml.ubl_de')
                and (tax_scheme_node[0]['cac:TaxScheme']['cbc:ID']['_text'] == 'VAT')
                and not (tax_scheme_node[0]['cbc:CompanyID']['_text'][:2].isalpha())
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

    def _invoice_constraints_peppol_en16931_ubl_new(self, invoice, vals):
        """
        corresponds to the errors raised by 'schematron/openpeppol/3.13.0/xslt/PEPPOL-EN16931-UBL.xslt' for
        invoices in ecosio. This xslt was obtained by transforming the corresponding sch
        https://docs.peppol.eu/poacc/billing/3.0/files/PEPPOL-EN16931-UBL.sch.

        The national rules (https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules) are included in this file.
        They always refer to the supplier's country.
        """
        nsmap = self._get_document_nsmap(vals)
        constraints = {
            # PEPPOL-EN16931-R003: A buyer reference or purchase order reference MUST be provided.
            'peppol_en16931_ubl_buyer_ref_po_ref':
                "A buyer reference or purchase order reference must be provided." if (
                    dict_to_xml(vals['document_node']['cbc:BuyerReference'], nsmap=nsmap, tag='cbc:BuyerReference') is None
                    and dict_to_xml(vals['document_node']['cac:OrderReference'], nsmap=nsmap, tag='cac:OrderReference') is None
                ) else None,
        }

        if vals['supplier'].country_id.code == 'NL':
            constraints.update({
                # [NL-R-001] For suppliers in the Netherlands, if the document is a creditnote, the document MUST contain
                # an invoice reference (cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID)
                'nl_r_001': self._check_required_fields(invoice, 'ref') if 'refund' in invoice.move_type else '',

                # [NL-R-002] For suppliers in the Netherlands the supplier's address (cac:AccountingSupplierParty/cac:Party
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
                    # the customer's legal entity identifier MUST be either a KVK or OIN number (schemeID 0106 or 0190)
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
        return constraints
