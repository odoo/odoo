from odoo import api, fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    intermediary_bank_bic = fields.Char(
        "Intermediary SWIFT",
        help="An intermediary bank facilitates international wire transfers between your bank and the beneficiary's bank when they don't have a direct relationship.",
    )
    show_intermediary_bank_bic = fields.Boolean(compute="_compute_show_intermediary_bank_bic")

    @api.depends_context('company')
    def _compute_show_intermediary_bank_bic(self):
        for bank in self:
            bank.show_intermediary_bank_bic = bank.env.company.account_fiscal_country_id.code == 'US'
