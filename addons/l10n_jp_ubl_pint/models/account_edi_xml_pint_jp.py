from odoo import models


class AccountEdiXmlUBLPINTJP(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.pint_jp'
    _description = "Japanese implementation of Peppol International (PINT) model for Billing"
    """
    Pint is a standard for International Billing from Peppol. It is based on Peppol BIS Billing 3.
    It serves as a base for per-country specialization, while keeping a standard core for data being used
    across countries. This is not meant to be used directly, but rather to be extended by country-specific modules.

    The JP PINT format is the Japanese implementation of PINT.

    * PINT Official documentation: https://docs.peppol.eu/poac/pint/pint/
    * PINT JP Official documentation: https://docs.peppol.eu/poac/jp/pint-jp
    """

    def _export_invoice_filename(self, invoice):
        # EXTENDS account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_jp.xml"

    def _get_partner_address_vals(self, partner):
        # EXTENDS account_edi_ubl_cii
        vals = super()._get_partner_address_vals(partner)
        vals.pop('country_subentity_code', None)
        return vals

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS account_edi_ubl_cii
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)
        for vals in vals_list:
            vals.pop('company_id')  # optional, if set: scheme_id should be taken from ISO/IEC 6523 list
        return vals_list

    def _get_invoice_period_vals_list(self, invoice):
        # EXTENDS
        vals_list = super()._get_invoice_period_vals_list(invoice)
        # [aligned-ibrp-052] An Invoice MUST have an invoice period (ibg-14) or an Invoice line period (ibg-26).
        vals_list.append({
            'start_date': invoice.invoice_date,
            'end_date': invoice.invoice_date,
        })
        return vals_list

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # [aligned-ibr-jp-06]-Tax category tax amount (ibt-117) with currency code JPY and tax category tax amount
        # in accounting currency (ibt-190) shall not have decimal.
        # see also: https://docs.peppol.eu/poac/jp/pint-jp/bis/#_rounding
        vals_list = super()._get_invoice_tax_totals_vals_list(invoice, taxes_vals)
        for vals in vals_list:
            vals['currency_dp'] = invoice.currency_id.decimal_places
            for subtotal_vals in vals.get('tax_subtotal_vals', []):
                subtotal_vals['currency_dp'] = invoice.currency_id.decimal_places

        company_currency = invoice.company_id.currency_id
        if invoice.currency_id != company_currency:
            # if company currency != invoice currency, need to add a TaxTotal section
            # see https://docs.peppol.eu/poac/jp/pint-jp/bis/#_tax_in_accounting_currency
            tax_totals_vals = {
                'currency': company_currency,
                'currency_dp': company_currency.decimal_places,
                'tax_amount': taxes_vals['tax_amount'],
                'tax_subtotal_vals': [],
            }
            for _grouping_key, vals in taxes_vals['tax_details'].items():
                tax_totals_vals['tax_subtotal_vals'].append({
                    'currency': company_currency,
                    'currency_dp': company_currency.decimal_places,
                    'taxable_amount': vals['base_amount'],
                    'tax_amount': vals['tax_amount'],
                    'percent': vals['_tax_category_vals_']['percent'],
                    'tax_category_vals': vals['_tax_category_vals_'],
                })
            vals_list.append(tax_totals_vals)
        return vals_list

    def _export_invoice_vals(self, invoice):
        # EXTENDS account_edi_ubl_cii
        vals = super()._export_invoice_vals(invoice)
        vals['vals'].update({
            # see https://docs.peppol.eu/poac/jp/pint-jp/bis/#profiles
            'customization_id': 'urn:peppol:pint:billing-1@jp-1',
            'profile_id': 'urn:peppol:bis:billing',
        })
        if invoice.currency_id != invoice.company_id.currency_id:
            # see https://docs.peppol.eu/poac/jp/pint-jp/bis/#_tax_in_accounting_currency
            vals['vals']['tax_currency_code'] = invoice.company_id.currency_id.name  # accounting currency
        return vals
