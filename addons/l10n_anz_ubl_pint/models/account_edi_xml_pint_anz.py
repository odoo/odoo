# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.tools import float_is_zero

ANZ_TAX_CATEGORIES = {'S', 'E', 'Z', 'G', 'O'}


class AccountEdiXmlUBLPINTANZ(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = "account.edi.xml.pint_anz"
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

    def _get_partner_party_vals(self, partner, role):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._get_partner_party_vals(partner, role)

        for party_tax_scheme in vals['party_tax_scheme_vals']:
            party_tax_scheme['tax_scheme_vals'] = {'id': 'GST'}

        return vals

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)
        company_currency = invoice.company_id.currency_id
        if invoice.currency_id != company_currency:
            # if company currency != invoice currency, need to add a TaxTotal section
            # see https://docs.peppol.eu/poac/aunz/pint-aunz/bis/#_tax_in_accounting_currency
            tax_totals_vals = {
                'currency': company_currency,
                'currency_dp': company_currency.decimal_places,
                'tax_amount': taxes_vals['tax_amount'],
            }
            vals_list.append(tax_totals_vals)
        return vals_list

    def _get_tax_unece_codes(self, customer, supplier, tax):
        """ The GST category must be provided in the file.
        See https://docs.peppol.eu/poac/aunz/pint-aunz/bis/#_tax_category_code
        """
        # OVERRIDE account_edi_ubl_cii
        if not supplier.vat:
            return {
                'tax_category_code': 'O',
                'tax_exemption_reason_code': False,
                'tax_exemption_reason': False,
            }  # a business is not registered for GST, the business cannot issue tax invoices. In this case, the GST category code should be O (Outside scope of tax).
        return super()._get_tax_unece_codes(customer, supplier, tax)

    def _get_tax_category_list(self, customer, supplier, taxes):
        # EXTENDS account_edi_ubl_cii
        vals_list = super()._get_tax_category_list(customer, supplier, taxes)
        for vals in vals_list:
            vals['tax_scheme_vals'] = {'id': 'GST'}
        return vals_list

    def _get_customization_ids(self):
        vals = super()._get_customization_ids()
        vals['pint_anz'] = 'urn:peppol:pint:billing-1@aunz-1'
        return vals

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_bis3
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)

        for vals in vals_list:
            # In both case the scheme must be set to a value that comes from the eas.
            if partner.country_code in ('AU', 'NZ'):
                vals['company_id_attrs'] = {'schemeID': partner.peppol_eas}
        return vals_list

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        # EXTENDS account.edi.xml.ubl_bis3
        line_item_vals = super()._get_invoice_line_item_vals(line, taxes_vals)

        for val in line_item_vals['classified_tax_category_vals']:
            # As of PINT A-NZ v1.1.0: [aligned-ibrp-o-05-aunz] tax categories of type "Not Subject to tax" (i.e. tax_category_code == 'O') must NOT have
            # tax rate ('cbc:Percent').
            if val.get('id') == 'O' and float_is_zero(val.get('percent'), precision_digits=2):
                del val['percent']

        return line_item_vals

    def _export_invoice_vals(self, invoice):
        # EXTENDS account_edi_ubl_cii
        vals = super()._export_invoice_vals(invoice)

        vals['vals'].update({
            # see https://docs.peppol.eu/poac/aunz/pint-aunz/bis/#_identifying_the_a_nz_billing_specialisation
            'customization_id': self._get_customization_ids()['pint_anz'],
            'profile_id': 'urn:peppol:bis:billing',
        })

        if invoice.currency_id != invoice.company_id.currency_id:
            # see https://docs.peppol.eu/poac/aunz/pint-aunz/bis/#_tax_in_accounting_currency
            vals['vals']['tax_currency_code'] = invoice.company_id.currency_id.name  # accounting currency
        return vals

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account_edi_ubl_cii
        constraints = super()._export_invoice_constraints(invoice, vals)

        # Tax category must be filled on the line, with a value from SG categories.
        for tax_total_val in vals['vals']['tax_total_vals']:
            for tax_subtotal_val in tax_total_val.get('tax_subtotal_vals', ()):
                if tax_subtotal_val['tax_category_vals']['tax_category_code'] not in ANZ_TAX_CATEGORIES:
                    constraints['sg_vat_category_required'] = _("You must set a tax category on each taxes of the invoice.\nValid categories are: S, E, Z, G, O")

        # Tax category of type "Not subject to tax" must have tax amount 0
        count_outside_of_scope_breakdown = 0
        for tax_category, tax_category_vals in vals['taxes_vals']['tax_details'].items():
            if tax_category['tax_category_id'] != 'O':
                continue
            count_outside_of_scope_breakdown += 1

            if float_is_zero(tax_category_vals['tax_amount'], precision_digits=2):
                continue

            if vals['supplier'].vat:
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
        if count_outside_of_scope_breakdown > 1 and vals['supplier'].vat:
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
