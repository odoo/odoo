# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class AccountEdiXmlUBLPINTMY(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_bis3"
    _name = 'account.edi.xml.pint_my'
    _description = "Malaysian implementation of Peppol International (PINT) model for Billing"
    """
    * PINT Official documentation: https://docs.peppol.eu/poac/pint/pint/
    * PINT MY Official documentation: https://docs.peppol.eu/poac/my/pint-my
    """

    def _export_invoice_filename(self, invoice):
        # EXTENDS account_edi_ubl_cii
        return f"{invoice.name.replace('/', '_')}_pint_my.xml"

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
                'company_id': partner.vat,
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
