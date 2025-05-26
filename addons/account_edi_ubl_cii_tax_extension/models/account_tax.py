from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    ubl_cii_tax_category_code = fields.Selection(
        help="The VAT category code used for electronic invoicing purposes.",
        string="Tax Category Code",
        selection=[
            ('AE', 'AE - Vat Reverse Charge'),
            ('E', 'E - Exempt from Tax'),
            ('S', 'S - Standard rate'),
            ('Z', 'Z - Zero rated goods'),
            ('G', 'G - Free export item, VAT not charged'),
            ('O', 'O - Services outside scope of tax'),
            ('K', 'K - VAT exempt for EEA intra-community supply of goods and services'),
            ('L', 'L - Canary Islands general indirect tax'),
            ('M', 'M - Tax for production, services and importation in Ceuta and Melilla'),
            ('B', 'B - Transferred (VAT), In Italy')
        ]
    )
    ubl_cii_tax_exemption_reason_code = fields.Selection(
        help="The reason why the amount is exempted from VAT or why no VAT is being charged, used for electronic invoicing purposes.",
        string="Tax Exemption Reason Code",
        selection=[
            ('VATEX-EU-79-C', 'VATEX-EU-79-C - Exempt based on article 79, point c of Council Directive 2006/112/EC'),
            ('VATEX-EU-132', 'VATEX-EU-132 - Exempt based on article 132 of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1A', 'VATEX-EU-132-1A - Exempt based on article 132, section 1 (a) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1B', 'VATEX-EU-132-1B - Exempt based on article 132, section 1 (b) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1C', 'VATEX-EU-132-1C - Exempt based on article 132, section 1 (c) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1D', 'VATEX-EU-132-1D - Exempt based on article 132, section 1 (d) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1E', 'VATEX-EU-132-1E - Exempt based on article 132, section 1 (e) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1F', 'VATEX-EU-132-1F - Exempt based on article 132, section 1 (f) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1G', 'VATEX-EU-132-1G - Exempt based on article 132, section 1 (g) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1H', 'VATEX-EU-132-1H - Exempt based on article 132, section 1 (h) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1I', 'VATEX-EU-132-1I - Exempt based on article 132, section 1 (i) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1J', 'VATEX-EU-132-1J - Exempt based on article 132, section 1 (j) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1K', 'VATEX-EU-132-1K - Exempt based on article 132, section 1 (k) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1L', 'VATEX-EU-132-1L - Exempt based on article 132, section 1 (l) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1M', 'VATEX-EU-132-1M - Exempt based on article 132, section 1 (m) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1N', 'VATEX-EU-132-1N - Exempt based on article 132, section 1 (n) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1O', 'VATEX-EU-132-1O - Exempt based on article 132, section 1 (o) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1P', 'VATEX-EU-132-1P - Exempt based on article 132, section 1 (p) of Council Directive 2006/112/EC'),
            ('VATEX-EU-132-1Q', 'VATEX-EU-132-1Q - Exempt based on article 132, section 1 (q) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143', 'VATEX-EU-143 - Exempt based on article 143 of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1A', 'VATEX-EU-143-1A - Exempt based on article 143, section 1 (a) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1B', 'VATEX-EU-143-1B - Exempt based on article 143, section 1 (b) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1C', 'VATEX-EU-143-1C - Exempt based on article 143, section 1 (c) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1D', 'VATEX-EU-143-1D - Exempt based on article 143, section 1 (d) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1E', 'VATEX-EU-143-1E - Exempt based on article 143, section 1 (e) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1F', 'VATEX-EU-143-1F - Exempt based on article 143, section 1 (f) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1FA', 'VATEX-EU-143-1FA - Exempt based on article 143, section 1 (fa) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1G', 'VATEX-EU-143-1G - Exempt based on article 143, section 1 (g) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1H', 'VATEX-EU-143-1H - Exempt based on article 143, section 1 (h) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1I', 'VATEX-EU-143-1I - Exempt based on article 143, section 1 (i) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1J', 'VATEX-EU-143-1J - Exempt based on article 143, section 1 (j) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1K', 'VATEX-EU-143-1K - Exempt based on article 143, section 1 (k) of Council Directive 2006/112/EC'),
            ('VATEX-EU-143-1L', 'VATEX-EU-143-1L - Exempt based on article 143, section 1 (l) of Council Directive 2006/112/EC'),
            ('VATEX-EU-148', 'VATEX-EU-148 - Exempt based on article 148 of Council Directive 2006/112/EC'),
            ('VATEX-EU-148-A', 'VATEX-EU-148-A - Exempt based on article 148, section (a) of Council Directive 2006/112/EC'),
            ('VATEX-EU-148-B', 'VATEX-EU-148-B - Exempt based on article 148, section (b) of Council Directive 2006/112/EC'),
            ('VATEX-EU-148-C', 'VATEX-EU-148-C - Exempt based on article 148, section (c) of Council Directive 2006/112/EC'),
            ('VATEX-EU-148-D', 'VATEX-EU-148-D - Exempt based on article 148, section (d) of Council Directive 2006/112/EC'),
            ('VATEX-EU-148-E', 'VATEX-EU-148-E - Exempt based on article 148, section (e) of Council Directive 2006/112/EC'),
            ('VATEX-EU-148-F', 'VATEX-EU-148-F - Exempt based on article 148, section (f) of Council Directive 2006/112/EC'),
            ('VATEX-EU-148-G', 'VATEX-EU-148-G - Exempt based on article 148, section (g) of Council Directive 2006/112/EC'),
            ('VATEX-EU-151', 'VATEX-EU-151 - Exempt based on article 151 of Council Directive 2006/112/EC'),
            ('VATEX-EU-151-1A', 'VATEX-EU-151-1A - Exempt based on article 151, section 1 (a) of Council Directive 2006/112/EC'),
            ('VATEX-EU-151-1AA', 'VATEX-EU-151-1AA - Exempt based on article 151, section 1 (aa) of Council Directive 2006/112/EC'),
            ('VATEX-EU-151-1B', 'VATEX-EU-151-1B - Exempt based on article 151, section 1 (b) of Council Directive 2006/112/EC'),
            ('VATEX-EU-151-1C', 'VATEX-EU-151-1C - Exempt based on article 151, section 1 (c) of Council Directive 2006/112/EC'),
            ('VATEX-EU-151-1D', 'VATEX-EU-151-1D - Exempt based on article 151, section 1 (d) of Council Directive 2006/112/EC'),
            ('VATEX-EU-151-1E', 'VATEX-EU-151-1E - Exempt based on article 151, section 1 (e) of Council Directive 2006/112/EC'),
            ('VATEX-EU-309', 'VATEX-EU-309 - Exempt based on article 309 of Council Directive 2006/112/EC'),
            ('VATEX-EU-AE', 'VATEX-EU-AE - Reverse charge'),
            ('VATEX-EU-D', 'VATEX-EU-D - Intra-Community acquisition from second hand means of transport'),
            ('VATEX-EU-F', 'VATEX-EU-F - Intra-Community acquisition of second hand goods'),
            ('VATEX-EU-G', 'VATEX-EU-G - Export outside the EU'),
            ('VATEX-EU-I', 'VATEX-EU-I - Intra-Community acquisition of works of art'),
            ('VATEX-EU-IC', 'VATEX-EU-IC - Intra-Community supply'),
            ('VATEX-EU-O', 'VATEX-EU-O - Not subject to VAT'),
            ('VATEX-EU-J', 'VATEX-EU-J - Intra-Community acquisition of collectors items and antiques'),
            ('VATEX-FR-FRANCHISE', 'VATEX-FR-FRANCHISE - France domestic VAT franchise in base'),
            ('VATEX-FR-CNWVAT', 'VATEX-FR-CNWVAT - France domestic Credit Notes without VAT, due to supplier forfeit of VAT for discount'),
        ]
    )
    ubl_cii_requires_exemption_reason = fields.Boolean(compute='_compute_ubl_cii_requires_exemption_reason')

    @api.depends('ubl_cii_tax_category_code')
    def _compute_ubl_cii_requires_exemption_reason(self):
        for tax in self:
            tax.ubl_cii_requires_exemption_reason = tax.ubl_cii_tax_category_code in ['AE', 'E', 'G', 'O', 'K']

    @api.onchange('ubl_cii_requires_exemption_reason')
    def _onchange_ubl_cii_tax_category_code(self):
        for tax in self:
            if not tax.ubl_cii_requires_exemption_reason:
                tax.ubl_cii_tax_exemption_reason_code = False
