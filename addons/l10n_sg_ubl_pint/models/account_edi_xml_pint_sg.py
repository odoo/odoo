# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


SG_TAX_CATEGORIES = {'SR', 'SRCA-S', 'SRCA-C', 'SROVR-RS', 'SROVR-LVG', 'SRLVG', 'ZR', 'ES33', 'ESN33', 'DS', 'OS', 'NG', 'NA'}


class AccountEdiXmlUBLPINTSG(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.pint_sg'
    _description = "Singapore implementation of Peppol International (PINT) model for Billing"
    """
    Pint is a standard for International Billing from Peppol. It is based on Peppol BIS Billing 3.
    It serves as a base for per-country specialization, while keeping a standard core for data being used
    across countries. This is not meant to be used directly, but rather to be extended by country-specific modules.

    The SG PINT format is the Singapore implementation of PINT.

    * PINT Official documentation: https://docs.peppol.eu/poac/pint/pint/
    * PINT SG Official documentation: https://docs.peppol.eu/poac/sg/2024-Q2/pint-sg/
    """

    def _export_invoice_filename(self, invoice):
        # OVERRIDE account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_sg.xml"

    def _get_partner_party_vals(self, partner, role):
        # EXTENDS account_edi_ubl_cii
        vals = super()._get_partner_party_vals(partner, role)

        for party_tax_scheme in vals['party_tax_scheme_vals']:
            party_tax_scheme['tax_scheme_vals'] = {'id': 'GST'}

        return vals

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # EXTENDS account_edi_ubl_cii
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)
        company_currency = invoice.company_id.currency_id
        if invoice.currency_id != company_currency:
            # if company currency != invoice currency, need to add a TaxTotal section
            # see https://docs.peppol.eu/poac/sg/2024-Q2/pint-sg/bis/#_invoice_totals_in_gst_accounting_currency
            tax_totals_vals = {
                'currency': company_currency,
                'currency_dp': company_currency.decimal_places,
                'tax_amount': taxes_vals['tax_amount'],
            }
            vals_list.append(tax_totals_vals)
        return vals_list

    def _get_tax_category_list(self, customer, supplier, taxes):
        # EXTENDS account_edi_ubl_cii
        vals_list = super()._get_tax_category_list(customer, supplier, taxes)
        for vals in vals_list:
            vals['tax_scheme_vals'] = {'id': 'GST'}
        return vals_list

    def _export_invoice_vals(self, invoice):
        # EXTENDS account_edi_ubl_cii
        vals = super()._export_invoice_vals(invoice)

        amounts_in_accounting_currency = (
            ('sgdtotal-excl-gst', invoice.amount_untaxed_signed),
            ('sgdtotal-incl-gst', invoice.amount_total_signed),
        )

        vals['vals'].update({
            # see https://docs.peppol.eu/poac/sg/2024-Q2/pint-sg/bis/#_bis_identifiers
            'customization_id': self._get_customization_ids()['pint_sg'],
            'profile_id': 'urn:peppol:bis:billing',
            'uuid': invoice._l10n_sg_get_uuid(),
        })

        if invoice.currency_id != invoice.company_id.currency_id:
            # see https://docs.peppol.eu/poac/sg/2024-Q2/pint-sg/bis/#_invoice_totals_in_gst_accounting_currency
            vals['vals']['tax_currency_code'] = invoice.company_id.currency_id.name  # accounting currency
            # [BR-53-GST-SG]-If the GST accounting currency code (BT-6-GST) is present, then the Invoice total GST amount (BT-111-GST),
            # Invoice total including GST amount and Invoice Total excluding GST amount in accounting currency shall be provided.
            vals['vals']['additional_document_reference_list'] = [{
                'id': invoice.company_id.currency_id.name,
                'document_description': amount,
                'document_type_code': code,
            } for code, amount in amounts_in_accounting_currency]
        return vals

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account_edi_ubl_cii
        constraints = super()._export_invoice_constraints(invoice, vals)

        # Tax category must be filled on the line, with a value from SG categories.
        for tax_total_val in vals['vals']['tax_total_vals']:
            for tax_subtotal_val in tax_total_val.get('tax_subtotal_vals', ()):
                if tax_subtotal_val['tax_category_vals']['tax_category_code'] not in SG_TAX_CATEGORIES:
                    constraints['sg_vat_category_required'] = _("You must set a Singaporean tax category on each taxes of the invoice.")

        return constraints
