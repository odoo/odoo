from odoo import fields, models

EXEMPTION_REASON_CODES = [
    ('VATEX-SA-29', 'VATEX-SA-29 Financial services mentioned in Article 29 of the VAT Regulations.'),
    ('VATEX-SA-29-7', 'VATEX-SA-29-7 Life insurance services mentioned in Article 29 of the VAT Regulations.'),
    ('VATEX-SA-30', 'VATEX-SA-30 Real estate transactions mentioned in Article 30 of the VAT Regulations.'),
    ('VATEX-SA-32', 'VATEX-SA-32 Export of goods.'),
    ('VATEX-SA-33', 'VATEX-SA-33 Export of Services.'),
    ('VATEX-SA-34-1', 'VATEX-SA-34-1 The international transport of Goods.'),
    ('VATEX-SA-34-2', 'VATEX-SA-34-2 The international transport of Passengers.'),
    ('VATEX-SA-34-3', 'VATEX-SA-34-3 Services directly connected and incidental to a Supply of international passenger transport.'),
    ('VATEX-SA-34-4', 'VATEX-SA-34-4 Supply of a qualifying means of transport.'),
    ('VATEX-SA-34-5', 'VATEX-SA-34-5 Any services relating to Goods or passenger transportation, as defined in article twenty five of these Regulations.'),
    ('VATEX-SA-35', 'VATEX-SA-35 Medicines and medical equipment.'),
    ('VATEX-SA-36', 'VATEX-SA-36 Qualifying metals.'),
    ('VATEX-SA-EDU', 'VATEX-SA-EDU Private education to citizen.'),
    ('VATEX-SA-HEA', 'VATEX-SA-HEA Private healthcare to citizen.'),
    ('VATEX-SA-OOS', 'VATEX-SA-OOS Not subject to VAT.')
]

REQUIRED_EXEMPTION_CODES = {'AE', 'E', 'G', 'O', 'K', 'Z'}
NO_EXEMPTION_REASON_CODES = {'Z', 'E'}


class AccountTax(models.Model):
    _inherit = 'account.tax'

    ubl_cii_tax_exemption_reason_code = fields.Selection(selection_add=EXEMPTION_REASON_CODES)
    l10n_sa_show_exemption_reason = fields.Boolean(compute="_compute_l10n_sa_show_exemption_reason")

    def _compute_ubl_cii_requires_exemption_reason(self):
        super()._compute_ubl_cii_requires_exemption_reason()
        for record in self.filtered(lambda rec: rec.company_id.account_fiscal_country_id.code == 'SA'):
            record.ubl_cii_requires_exemption_reason = record.ubl_cii_tax_category_code in REQUIRED_EXEMPTION_CODES

    def _compute_l10n_sa_show_exemption_reason(self):
        for tax in self:
            tax.l10n_sa_show_exemption_reason = (
                tax.company_id.account_fiscal_country_id.code != 'SA'
                or tax.ubl_cii_tax_category_code not in NO_EXEMPTION_REASON_CODES
            )
