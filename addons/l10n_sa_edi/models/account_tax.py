from odoo import fields, models, api, _
from odoo.exceptions import UserError


EXEMPTION_REASON_CODES = [
    ('VATEX-SA-29', 'VATEX-SA-29 Financial services mentioned in Article 29 of the VAT Regulations.'),
    ('VATEX-SA-29-7', 'VATEX-SA-29-7 Life insurance services mentioned in Article 29 of the VAT.'),
    ('VATEX-SA-30', 'VATEX-SA-30 Real estate transactions mentioned in Article 30 of the VAT Regulations.'),
    ('VATEX-SA-32', 'VATEX-SA-32 Export of goods.'),
    ('VATEX-SA-33', 'VATEX-SA-33 Export of Services.'),
    ('VATEX-SA-34-1', 'VATEX-SA-34-1 The international transport of Goods.'),
    ('VATEX-SA-34-2', 'VATEX-SA-34-1 The international transport of Passengers.'),
    ('VATEX-SA-34-3', 'VATEX-SA-34-3 Services directly connected and incidental to a Supply of international passenger transport.'),
    ('VATEX-SA-34-4', 'VATEX-SA-34-4 Supply of a qualifying means of transport.'),
    ('VATEX-SA-34-5', 'VATEX-SA-34-5 Any services relating to Goods or passenger transportation, as defined in article twenty five of these Regulations.'),
    ('VATEX-SA-35', 'VATEX-SA-35 Medicines and medical equipment.'),
    ('VATEX-SA-36', 'VATEX-SA-36 Qualifying metals.'),
    ('VATEX-SA-EDU', 'VATEX-SA-EDU Private education to citizen.'),
    ('VATEX-SA-HEA', 'VATEX-SA-HEA Private healthcare to citizen.'),
    ('VATEX-SA-OOS', 'VATEX-SA-OOS Not subject to VAT.')
]


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_sa_is_retention = fields.Boolean("Is Retention", default=False,
                                          help="Determines whether or not a tax counts as a Withholding Tax")

    ubl_cii_tax_exemption_reason_code = fields.Selection(selection_add=EXEMPTION_REASON_CODES)

    @api.onchange('amount')
    def onchange_amount(self):
        super().onchange_amount()
        self.l10n_sa_is_retention = False

    @api.constrains("l10n_sa_is_retention", "amount", "type_tax_use")
    def _l10n_sa_constrain_is_retention(self):
        for tax in self:
            if tax.amount >= 0 and tax.l10n_sa_is_retention and tax.type_tax_use == 'sale':
                raise UserError(_("Cannot set a tax to Retention if the amount is greater than or equal 0"))

    @api.depends('ubl_cii_tax_category_code')
    def _compute_ubl_cii_requires_exemption_reason(self):
        for tax in self:
            tax.ubl_cii_requires_exemption_reason = (
                tax.ubl_cii_tax_category_code in ['AE', 'E', 'G', 'O', 'K', 'Z'] and
                tax.type_tax_use == 'sale' and
                tax.country_code == 'SA' and
                tax.amount != 0
            )
