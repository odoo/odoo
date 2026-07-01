from stdnum import luhn
from odoo import models, _


class AccountEdiXmlUBLBIS3(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS account.edi.xml.ubl_21
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)

        # sources:
        #  https://sfti.se/download/18.427140af179361c4e462cc34/1620641679827/Beskrivning%20av%20svenska%20valideringsregler%202018-11-12.pdf
        #  https://docs.peppol.eu/poacc/billing/3.0/bis/#national_rules (SE-R-005 (fatal))
        if partner.country_id.code == "SE" and role == 'supplier':
            vals_list.append({
                'company_id': "GODKÄND FÖR F-SKATT",
                'tax_scheme_vals': {'id': 'TAX'},
            })
        return vals_list

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._export_invoice_vals(invoice)

        # Add RequisitionDocumentReference from invoice.ref if available
        if invoice.ref:
            vals['vals']['requisition_document_reference'] = invoice.ref
        # Add order reference if invoice_origin is set
        if invoice.invoice_origin:
            vals['vals']['order_reference_vals'] = {'id': invoice.invoice_origin}

        return vals

    def _invoice_constraints_peppol_en16931_ubl(self, invoice, vals):
        constraints = super()._invoice_constraints_peppol_en16931_ubl(invoice, vals)

        if vals['supplier'].country_id.code == 'SE':
            vat = vals['supplier'].vat.strip() if vals['supplier'].vat else ""
            company_registration = vals['supplier'].company_registry.replace('-', '').strip() if vals['supplier'].company_registry else ""
            tax_scheme = vals['supplier'].tax_scheme.strip().upper() if vals['supplier'].tax_scheme else ""
            payment_means_code = vals['supplier'].payment_means_code.strip() if vals['supplier'].payment_means_code else ""
            financial_branch_id = vals['supplier'].financial_branch_id.strip() if vals['supplier'].financial_branch_id else ""
            account_id = vals['supplier'].account_id.strip() if vals['supplier'].account_id else ""

            constraints.update({
                # SE-R-001: VAT number must be 14 characters long and start with 'SE'
                'se_r_001': _("The VAT number must be 14 characters long and start with 'SE'.")
                if not (vat.startswith("SE") and len(vat) == 14) else "",

                # SE-R-002: Last 12 characters of VAT must be numeric
                'se_r_002': _("The last 12 characters of the VAT number must be numeric.")
                if not (vat[2:].isdigit() if len(vat) == 14 else False) else "",

                # SE-R-003: Organization number must be numeric
                'se_r_003': _("The Swedish organization number must be numeric.")
                if not company_registration.isdigit() else "",

                # SE-R-004: Organization number must be 10 characters
                'se_r_004': _("The Swedish organization number must be 10 characters long.")
                if len(company_registration) != 10 else "",

                # SE-R-005: "Godkänd för F-skatt" must be stated if Seller Tax Registration ID is used
                'se_r_005': _("The supplier must indicate 'Godkänd för F-skatt' when using Seller Tax Registration ID.")
                if tax_scheme and tax_scheme != "VAT" and tax_scheme != "GODKÄND FÖR F-SKATT" else "",

                # SE-R-006: Only VAT rates of 6, 12, or 25 are allowed
                'se_r_006': _("Only VAT rates of 6, 12, or 25 percent are allowed for Swedish suppliers.")
                if vals['vat_rate'] not in {6, 12, 25} else "",

                # SE-R-007: Plusgiro account ID must be numeric
                'se_r_007': _("The Plusgiro account ID must be numeric.")
                if financial_branch_id == "SE:PLUSGIRO" and not account_id.isdigit() else "",

                # SE-R-008: Bankgiro account ID must be numeric
                'se_r_008': _("The Bankgiro account ID must be numeric.")
                if financial_branch_id == "SE:BANKGIRO" and not account_id.isdigit() else "",

                # SE-R-009: Bankgiro account ID must be 7-8 characters
                'se_r_009': _("The Bankgiro account ID must have 7 or 8 characters.")
                if financial_branch_id == "SE:BANKGIRO" and len(account_id) not in {7, 8} else "",

                # SE-R-010: Plusgiro account ID must have 2-8 characters
                'se_r_010': _("The Plusgiro account ID must have between 2 and 8 characters.")
                if financial_branch_id == "SE:PLUSGIRO" and not (2 <= len(account_id) <= 8) else "",

                # SE-R-011: Must use PaymentMeans Code 30 for Bankgiro/Plusgiro
                'se_r_011': _("For Bankgiro or Plusgiro, use PaymentMeans Code '30'.")
                if payment_means_code in {"50", "56"} else "",

                # SE-R-012: Domestic transactions between Swedish partners must use PaymentMeans Code 30
                'se_r_012': _("For domestic transactions between Swedish companies, use PaymentMeans Code '30'.")
                if vals['customer'].country_id.code == 'SE' and payment_means_code == "31" else "",

                # SE-R-013: Organization number must pass the Luhn algorithm
                'se_r_013': _("The last digit of the Swedish organization number must be valid according to the Luhn algorithm.")
                if not luhn.is_valid(company_registration) else "",
            })
        return constraints
