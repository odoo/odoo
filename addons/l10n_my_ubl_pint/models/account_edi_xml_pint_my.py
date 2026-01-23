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

    def _get_customization_id(self, process_type='billing'):
        if process_type == 'billing':
            return 'urn:peppol:pint:billing-1@my-1'

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        # EXTENDS account.edi.xml.ubl_bis3

        # In malaysia, tax on good is paid at the manufacturer level. It is thus common to invoice without taxes,
        # unless invoicing for a service.
        if not tax_data:
            return

        grouping_key = super()._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)
        if not grouping_key:
            return

        # If a business is not registered for SST and/or TTx, the business is not allowed to charge sales tax,
        # service tax or tourism tax in the e-Invoice.
        # In this case, the tax category code should be 'O' (Outside scope of tax).
        # For now, we do not properly support Tourism tax (TTx) due to a lack of clarity on the subject.
        supplier = vals['supplier']
        if not supplier.sst_registration_number:
            grouping_key['tax_category_code'] = 'O'
        elif tax_data['tax'].amount != 0:
            grouping_key['tax_category_code'] = 'T'
        else:
            grouping_key['tax_category_code'] = 'E'

        return grouping_key

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_tax_total_nodes(document_node, vals)
        nodes = document_node['cac:TaxTotal']

        if not nodes:
            tax_total_node = self._ubl_get_tax_total_node(vals, {
                'currency': vals['currency_id'],
                'amount': 0.0,
                'subtotals': {},
            })
            nodes.append(tax_total_node)

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        super()._add_invoice_header_nodes(document_node, vals)
        document_node['cbc:ProfileID'] = {'_text': 'urn:peppol:bis:billing'}

    def _ubl_add_party_tax_scheme_nodes(self, vals):
        # EXTENDS account.edi.ubl_bis3
        super()._ubl_add_party_tax_scheme_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if commercial_partner.country_code == 'MY':
            vals['party_node']['cac:PartyTaxScheme'] = [{
                'cbc:CompanyID': {'_text': commercial_partner.sst_registration_number or 'NA'},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'NOT_EU_VAT'},
                },
            }]

    def _ubl_add_accounting_supplier_party_tax_scheme_nodes(self, vals):
        # EXTENDS account.edi.ubl_bis3
        super()._ubl_add_accounting_supplier_party_tax_scheme_nodes(vals)
        nodes = vals['party_node']['cac:PartyTaxScheme']
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if commercial_partner.country_code == 'MY':
            nodes.append({
                'cbc:CompanyID': {'_text': commercial_partner.vat or 'NA'},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'GST'},
                },
            })

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account_edi_ubl_cii
        constraints = super()._export_invoice_constraints(invoice, vals)

        # A tax category "Outside of tax cope" can only have an amount of 0.
        for tax_total_node in vals['document_node']['cac:TaxTotal']:
            for tax_subtotal_node in tax_total_node['cac:TaxSubtotal']:
                for tax_category_node in tax_subtotal_node['cac:TaxCategory']:
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
