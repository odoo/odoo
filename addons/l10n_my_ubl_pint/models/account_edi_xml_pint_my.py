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

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'urn:peppol:pint:billing-1@my-1'

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
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

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account_edi_ubl_cii
        constraints = super()._export_invoice_constraints(invoice, vals)

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
