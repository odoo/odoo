from odoo import models

TAX_EXEMPTION_MAPPING = {
    'VATEX-EU-79-C': 'Exempt based on article 79, point c of Council Directive 2006/112/EC',
    'VATEX-EU-132': 'Exempt based on article 132 of Council Directive 2006/112/EC',
    'VATEX-EU-132-1A': 'Exempt based on article 132, section 1 (a) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1B': 'Exempt based on article 132, section 1 (b) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1C': 'Exempt based on article 132, section 1 (c) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1D': 'Exempt based on article 132, section 1 (d) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1E': 'Exempt based on article 132, section 1 (e) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1F': 'Exempt based on article 132, section 1 (f) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1G': 'Exempt based on article 132, section 1 (g) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1H': 'Exempt based on article 132, section 1 (h) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1I': 'Exempt based on article 132, section 1 (i) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1J': 'Exempt based on article 132, section 1 (j) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1K': 'Exempt based on article 132, section 1 (k) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1L': 'Exempt based on article 132, section 1 (l) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1M': 'Exempt based on article 132, section 1 (m) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1N': 'Exempt based on article 132, section 1 (n) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1O': 'Exempt based on article 132, section 1 (o) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1P': 'Exempt based on article 132, section 1 (p) of Council Directive 2006/112/EC',
    'VATEX-EU-132-1Q': 'Exempt based on article 132, section 1 (q) of Council Directive 2006/112/EC',
    'VATEX-EU-143': 'Exempt based on article 143 of Council Directive 2006/112/EC',
    'VATEX-EU-143-1A': 'Exempt based on article 143, section 1 (a) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1B': 'Exempt based on article 143, section 1 (b) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1C': 'Exempt based on article 143, section 1 (c) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1D': 'Exempt based on article 143, section 1 (d) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1E': 'Exempt based on article 143, section 1 (e) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1F': 'Exempt based on article 143, section 1 (f) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1FA': 'Exempt based on article 143, section 1 (fa) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1G': 'Exempt based on article 143, section 1 (g) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1H': 'Exempt based on article 143, section 1 (h) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1I': 'Exempt based on article 143, section 1 (i) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1J': 'Exempt based on article 143, section 1 (j) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1K': 'Exempt based on article 143, section 1 (k) of Council Directive 2006/112/EC',
    'VATEX-EU-143-1L': 'Exempt based on article 143, section 1 (l) of Council Directive 2006/112/EC',
    'VATEX-EU-148': 'Exempt based on article 148 of Council Directive 2006/112/EC',
    'VATEX-EU-148-A': 'Exempt based on article 148, section (a) of Council Directive 2006/112/EC',
    'VATEX-EU-148-B': 'Exempt based on article 148, section (b) of Council Directive 2006/112/EC',
    'VATEX-EU-148-C': 'Exempt based on article 148, section (c) of Council Directive 2006/112/EC',
    'VATEX-EU-148-D': 'Exempt based on article 148, section (d) of Council Directive 2006/112/EC',
    'VATEX-EU-148-E': 'Exempt based on article 148, section (e) of Council Directive 2006/112/EC',
    'VATEX-EU-148-F': 'Exempt based on article 148, section (f) of Council Directive 2006/112/EC',
    'VATEX-EU-148-G': 'Exempt based on article 148, section (g) of Council Directive 2006/112/EC',
    'VATEX-EU-151': 'Exempt based on article 151 of Council Directive 2006/112/EC',
    'VATEX-EU-151-1A': 'Exempt based on article 151, section 1 (a) of Council Directive 2006/112/EC',
    'VATEX-EU-151-1AA': 'Exempt based on article 151, section 1 (aa) of Council Directive 2006/112/EC',
    'VATEX-EU-151-1B': 'Exempt based on article 151, section 1 (b) of Council Directive 2006/112/EC',
    'VATEX-EU-151-1C': 'Exempt based on article 151, section 1 (c) of Council Directive 2006/112/EC',
    'VATEX-EU-151-1D': 'Exempt based on article 151, section 1 (d) of Council Directive 2006/112/EC',
    'VATEX-EU-151-1E': 'Exempt based on article 151, section 1 (e) of Council Directive 2006/112/EC',
    'VATEX-EU-309': 'Exempt based on article 309 of Council Directive 2006/112/EC',
    'VATEX-EU-AE': 'Reverse charge',
    'VATEX-EU-D': 'Intra-Community acquisition from second hand means of transport',
    'VATEX-EU-F': 'Intra-Community acquisition of second hand goods',
    'VATEX-EU-G': 'Export outside the EU',
    'VATEX-EU-I': 'Intra-Community acquisition of works of art',
    'VATEX-EU-IC': 'Intra-Community supply',
    'VATEX-EU-O': 'Not subject to VAT',
    'VATEX-EU-J': 'Intra-Community acquisition of collectors items and antiques',
    'VATEX-FR-FRANCHISE': 'France domestic VAT franchise in base',
    'VATEX-FR-CNWVAT': 'France domestic Credit Notes without VAT, due to supplier forfeit of VAT for discount',
}


class AccountEdiCommon(models.AbstractModel):
    _inherit = "account.edi.common"

    def _get_tax_unece_codes(self, customer, supplier, tax):
        if tax.ubl_cii_tax_category_code:
            tax_exemption_reason = TAX_EXEMPTION_MAPPING.get(tax.ubl_cii_tax_exemption_reason_code)
            return {
                'tax_category_code': tax.ubl_cii_tax_category_code,
                'tax_exemption_reason_code': tax.ubl_cii_tax_exemption_reason_code,
                'tax_exemption_reason': tax_exemption_reason,
            }
        return super()._get_tax_unece_codes(customer, supplier, tax)
