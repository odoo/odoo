# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountEdiXmlPint_My(models.AbstractModel):
    _name = 'account.edi.xml.pint_my'
    _inherit = ["account.edi.xml.ubl_bis3"]
    _description = "Malaysian implementation of Peppol International (PINT) model for Billing"
    """
    * PINT Official documentation: https://docs.peppol.eu/poac/pint/pint/
    * PINT MY Official documentation: https://docs.peppol.eu/poac/my/pint-my
    """

    def _export_invoice_filename(self, invoice):
        # EXTENDS account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_my.xml"

    # -------------------------------------------------------------------------
    # EXPORT: Old helpers
    # -------------------------------------------------------------------------

    def _export_invoice_vals(self, invoice):
        # EXTENDS account_edi_ubl_cii
        vals = super()._export_invoice_vals(invoice)
        vals['vals'].update({
            # see https://docs.peppol.eu/poac/my/pint-my/bis/#profiles
            'customization_id': self._get_customization_ids()['pint_my'],
            'profile_id': 'urn:peppol:bis:billing',
        })
        if invoice.currency_id != invoice.company_id.currency_id:
            # see https://docs.peppol.eu/poac/my/pint-my/bis/#_tax_in_accounting_currency
            vals['vals']['tax_currency_code'] = invoice.company_id.currency_id.name  # accounting currency
        return vals

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # EXTENDS account_edi_ubl_cii
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)
        company_currency = invoice.company_id.currency_id
        if invoice.currency_id != company_currency:
            # see https://docs.peppol.eu/poac/my/pint-my/bis/#_tax_in_accounting_currency
            vals_list.append({
                'currency': company_currency,
                'currency_dp': company_currency.decimal_places,
                'tax_amount': taxes_vals['tax_amount'],
                'tax_subtotal_vals': [],
            })
        return vals_list

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        """ [aligned-ibrp-cl-01-my]-Malaysian invoice tax categories MUST be coded using Malaysian codes. """
        # EXTENDS account_edi_ubl_cii
        tax_scheme_vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)
        # See https://docs.peppol.eu/poac/my/pint-my/bis/#_seller_tax_identifier
        tax_scheme_vals_list[0]['company_id'] = partner.sst_registration_number or 'NA'
        if role == 'supplier':
            # TIN
            gst_tax_scheme = tax_scheme_vals_list[0].copy()
            gst_tax_scheme.update({
                'company_id': partner.vat or 'NA',
                'tax_scheme_vals': {'id': 'GST'},
            })
            tax_scheme_vals_list.append(gst_tax_scheme)

        return tax_scheme_vals_list

    def _get_tax_unece_codes(self, customer, supplier, tax):
        """
        In malaysia, only the following codes can be used: T, E, O
        https://docs.peppol.eu/poac/my/pint-my/bis/#_tax_category_code
        """
        # OVERRIDE account_edi_ubl_cii
        codes = {
            'tax_category_code': False,
            'tax_exemption_reason_code': False,
            'tax_exemption_reason': False,
        }
        # If a business is not registered for SST and/or TTx, the business is not allowed to charge sales tax,
        # service tax or tourism tax in the e-Invoice.
        # In this case, the tax category code should be 'O' (Outside scope of tax).
        # For now, we do not properly support Tourism tax (TTx) due to a lack of clarity on the subject.
        if not supplier.sst_registration_number:
            codes['tax_category_code'] = 'O'
        elif tax.amount != 0:
            codes['tax_category_code'] = 'T'
        else:
            codes['tax_category_code'] = 'E'
        return codes

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account_edi_ubl_cii
        constraints = super()._export_invoice_constraints(invoice, vals)

        # A tax category "Outside of tax cope" can only have an amount of 0.
        for tax_total_val in vals['vals']['tax_total_vals']:
            for tax_subtotal_val in tax_total_val['tax_subtotal_vals']:
                tax_category_vals = tax_subtotal_val['tax_category_vals']
                if tax_category_vals['tax_category_code'] == 'O' and tax_category_vals['percent'] != 0:
                    constraints['peppol_my_sst_registration'] = _(
                        "If your business is registered for SST, please provide your registration number in your company details.\n"
                        "Otherwise, you are not allowed to charge sales or services taxes in the e-Invoice."
                    )
                    break

        # In malaysia, tax on good is paid at the manufacturer level. It is thus common to invoice without taxes,
        # unless invoicing for a service.
        constraints.pop('tax_on_line', '')
        constraints.pop('cen_en16931_tax_line', '')

        return constraints

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

    def _get_tax_category_code(self, customer, supplier, tax):
        """
        In malaysia, only the following codes can be used: T, E, O
        https://docs.peppol.eu/poac/my/pint-my/bis/#_tax_category_code
        """
        # OVERRIDE account_edi_ubl_cii
        # If a business is not registered for SST and/or TTx, the business is not allowed to charge sales tax,
        # service tax or tourism tax in the e-Invoice.
        # In this case, the tax category code should be 'O' (Outside scope of tax).
        # For now, we do not properly support Tourism tax (TTx) due to a lack of clarity on the subject.
        if not supplier.sst_registration_number:
            return 'O'
        elif tax.amount != 0:
            return 'T'
        else:
            return 'E'

    def _add_document_tax_grouping_function_vals(self, vals):
        # OVERRIDE account_edi_ubl_cii
        # In malaysia, tax on good is paid at the manufacturer level. It is thus common to invoice without taxes,
        # unless invoicing for a service.
        super()._add_document_tax_grouping_function_vals(vals)

        tax_grouping_function = vals['tax_grouping_function']

        def modified_tax_grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']
            if not tax:
                return None
            return tax_grouping_function(base_line, tax_data)

        vals['tax_grouping_function'] = modified_tax_grouping_function

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        document_node['cbc:CustomizationID'] = {'_text': self._get_customization_ids()['pint_my']}
        document_node['cbc:ProfileID'] = {'_text': 'urn:peppol:bis:billing'}

        invoice = vals['invoice']
        if invoice.currency_id != invoice.company_id.currency_id:
            # see https://docs.peppol.eu/poac/my/pint-my/bis/#_tax_in_accounting_currency
            document_node['cbc:TaxCurrencyCode'] = {'_text': invoice.company_id.currency_id.name}

    def _get_party_node(self, vals):
        party_node = super()._get_party_node(vals)
        commercial_partner = vals['partner'].commercial_partner_id

        # See https://docs.peppol.eu/poac/my/pint-my/bis/#_seller_tax_identifier
        party_node['cac:PartyTaxScheme'][0]['cbc:CompanyID']['_text'] = commercial_partner.sst_registration_number or 'NA'

        if vals['role'] == 'supplier':
            party_node['cac:PartyTaxScheme'].append(
                {
                    **party_node['cac:PartyTaxScheme'][0],
                    'cbc:CompanyID': {'_text': commercial_partner.vat or 'NA'},
                    'cac:TaxScheme': {
                        'cbc:ID': {'_text': 'GST'}
                    }
                }
            )

        return party_node

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_tax_total_nodes(document_node, vals)

        document_node['cac:TaxTotal'] = [document_node['cac:TaxTotal']]

        # see https://docs.peppol.eu/poac/my/pint-my/bis/#_tax_in_accounting_currency
        company_currency = vals['invoice'].company_id.currency_id
        if vals['invoice'].currency_id != company_currency:
            self._add_tax_total_node_in_company_currency(document_node, vals)

        # Remove the tax subtotals from the TaxTotal in company currency
        document_node['cac:TaxTotal'][-1]['cac:TaxSubtotal'] = []

    def _export_invoice_constraints_new(self, invoice, vals):
        # EXTENDS account_edi_ubl_cii
        constraints = super()._export_invoice_constraints_new(invoice, vals)

        # A tax category "Outside of tax cope" can only have an amount of 0.
        tax_total_node = vals['document_node']['cac:TaxTotal'][0]
        for tax_subtotal_node in tax_total_node['cac:TaxSubtotal']:
            tax_category_node = tax_subtotal_node['cac:TaxCategory']
            if tax_category_node['cbc:ID'] == 'O' and tax_subtotal_node['cbc:Percent'] != 0:
                constraints['peppol_my_sst_registration'] = _(
                    "If your business is registered for SST, please provide your registration number in your company details.\n"
                    "Otherwise, you are not allowed to charge sales or services taxes in the e-Invoice."
                )
                break

        # In malaysia, tax on good is paid at the manufacturer level. It is thus common to invoice without taxes,
        # unless invoicing for a service.
        constraints.pop('tax_on_line', '')
        constraints.pop('cen_en16931_tax_line', '')

        return constraints
