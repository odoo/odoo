from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    is_spanish = fields.Boolean(string="Company located in Spain", compute="_is_company_spanish")

    def _is_company_spanish(self):
        for pos in self:
            pos.is_spanish = pos.company_id.country_id.code == "ES"

    l10n_es_simplified_invoice_limit = fields.Float(
        string="Simplified Invoice limit amount",
        help="Over this amount is not legally possible to create a simplified invoice",
        default=400,
    )
    l10n_es_simplified_invoice_journal_id = fields.Many2one('account.journal')
    simplified_partner_id = fields.Many2one(
        "res.partner", string="Simplified invoice partner", compute="_get_simplified_partner"
    )

    @api.depends("company_id")
    def _get_simplified_partner(self):
        for config in self:
            config.simplified_partner_id = self.env.ref("l10n_es.partner_simplified").id

    def get_limited_partners_loading(self):
        # this function normally returns 100 partners, but we have to make sure that
        # the simplified partner is also loaded
        res = super().get_limited_partners_loading()
        if (self.simplified_partner_id.id,) not in res:
            res.append((self.simplified_partner_id.id,))
        return res
