# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.tools import float_is_zero

ANZ_TAX_CATEGORIES = {'S', 'E', 'Z', 'G', 'O'}


class AccountEdiXmlPint_Anz(models.AbstractModel):
    _name = 'account.edi.xml.pint_anz'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "Australia & New Zealand implementation of Peppol International (PINT) model for Billing"
    """
    Pint is a standard for International Billing from Peppol. It is based on Peppol BIS Billing 3.
    It serves as a base for per-country specialization, while keeping a standard core for data being used
    across countries. This is not meant to be used directly, but rather to be extended by country-specific modules.

    The ANZ PINT format is the Australia & New Zealand implementation of PINT.

    * PINT Official documentation: https://docs.peppol.eu/poac/pint/pint/
    * PINT ANZ Official documentation: https://docs.peppol.eu/poac/aunz/pint-aunz/
    """

    def _export_invoice_filename(self, invoice):
        # EXTENDS account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_anz.xml"

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'urn:peppol:pint:billing-1@aunz-1'

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        # EXTENDS account.edi.xml.ubl_bis3
        grouping_key = super()._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)
        if not grouping_key:
            return

        # A business not registered for GST cannot issue tax invoices.
        # In this case, the tax category code should be O (Outside scope of tax).
        # See https://docs.peppol.eu/poac/aunz/pint-aunz/bis/#_tax_category_code
        supplier = vals['supplier']
        if not supplier.ref_company_ids[:1].l10n_au_is_gst_registered:
            grouping_key['tax_category_code'] = 'O'

        # As of PINT A-NZ v1.1.0: [aligned-ibrp-o-05-aunz] tax categories of type "Not Subject to tax" (i.e. tax_category_code == 'O') must NOT have
        # tax rate ('cbc:Percent').
        if (
            grouping_key['tax_category_code'] == 'O'
            and not grouping_key['percent']
        ):
            grouping_key['percent'] = None

        return grouping_key

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)

        # see https://docs.peppol.eu/poac/aunz/pint-aunz/bis/#_identifying_the_a_nz_billing_specialisation
        document_node['cbc:ProfileID'] = {'_text': 'urn:peppol:bis:billing'}

    def _ubl_add_party_legal_entity_nodes(self, vals):
        # EXTENDS
        super()._ubl_add_party_legal_entity_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if commercial_partner.country_code in ('AU', 'NZ'):
            if commercial_partner.vat and commercial_partner.vat != '/':
                vals['party_node']['cac:PartyLegalEntity'] = [{
                    'cbc:RegistrationName': {'_text': commercial_partner.name},
                    'cbc:CompanyID': {
                        '_text': commercial_partner.vat,
                        'schemeID': '0151' if commercial_partner.country_code == 'AU' else '0088',
                    },
                }]
            elif commercial_partner.peppol_eas and commercial_partner.peppol_endpoint:
                vals['party_node']['cac:PartyLegalEntity'] = [{
                    'cbc:RegistrationName': {'_text': commercial_partner.name},
                    'cbc:CompanyID': {
                        '_text': commercial_partner.peppol_endpoint,
                        'schemeID': commercial_partner.peppol_eas,
                    },
                }]

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account_edi_ubl_cii
        constraints = super()._export_invoice_constraints(invoice, vals)

        # Tax category must be filled on the line, with a value from SG categories.
        tax_total_node = vals['document_node']['cac:TaxTotal'][0]
        for tax_subtotal_node in tax_total_node['cac:TaxSubtotal']:
            if any(tax_category_node['cbc:ID']['_text'] not in ANZ_TAX_CATEGORIES for tax_category_node in tax_subtotal_node['cac:TaxCategory']):
                constraints['anz_vat_category_required'] = _("You must set a tax category on each taxes of the invoice.\nValid categories are: S, E, Z, G, O")

        # Tax category of type "Not subject to tax" must have tax amount 0
        count_outside_of_scope_breakdown = 0
        for tax_subtotal in tax_total_node['cac:TaxSubtotal']:
            if any(tax_category_node['cbc:ID']['_text'] != 'O' for tax_category_node in tax_subtotal['cac:TaxCategory']):
                continue
            count_outside_of_scope_breakdown += 1

            if float_is_zero(tax_subtotal['cbc:TaxAmount']['_text'], precision_digits=2):
                continue

            if vals['supplier'].ref_company_ids[:1].l10n_au_is_gst_registered:
                constraints['anz_tax_breakdown_amount'] = \
                    self.env._("A tax category of type 'Not subject to tax' must have tax"
                               " amount set to 0")
            else:
                # If a company is not GST registered, this module remaps all tax categories
                # to 'O' (Other/Out of Scope). This causes an issue when a line contained a
                # non-zero tax, as it would create a tax subtotal with (Code: 'O', Amount:
                # non-zero), which violates PINT rules.
                # Since the code silently remaps tax classification code, the original error
                # message might be misleading for users. This constraint contains better
                # explaination of error and intructions on how to prevent it.
                constraints['anz_non_gst_supplier_tax_scope'] = \
                    self.env._("Suppliers not registered for GST cannot use taxes that are"
                               " not zero-rated. Please ensure the tax category is set to"
                               " 'O' (Services outside scope of tax) with a tax amount of 0.")

        # There should be at most one tax breakdown of type "Not subject to tax".
        if count_outside_of_scope_breakdown > 1 and vals['supplier'].ref_company_ids[:1].l10n_au_is_gst_registered:
            constraints['anz_duplicate_tax_breakdown'] = \
                self.env._("A tax breakdown of type 'Not subject to tax' should appear at most"
                           " once in the tax breakdown")

        # ALIGNED-IBR-001-AUNZ and ALIGNED-IBR-002-AUNZ
        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]
            if partner.country_code == 'AU' and partner.peppol_eas != '0151':
                constraints[f'au_{partner_type}_eas_0151'] = _("The Peppol EAS must be set to ABN (0151) if the partner country is Australia.")
            elif partner.country_code == 'NZ' and partner.peppol_eas != '0088':
                constraints[f'nz_{partner_type}_eas_0088'] = _("The Peppol EAS must be set to EAN (0088) if the partner country is New Zealand.")

        return constraints
