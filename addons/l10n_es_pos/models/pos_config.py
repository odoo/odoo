from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    is_spanish = fields.Boolean(
        string="Company located in Spain",
        compute="_compute_is_spanish",
    )
    l10n_es_simplified_invoice_journal_id = fields.Many2one(
        comodel_name="account.journal",
        domain=[("type", "=", "sale")],
        check_company=True,
    )
    simplified_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Simplified invoice partner",
        compute="_compute_simplified_partner_id",
    )

    @api.depends("company_id")
    def _compute_is_spanish(self):
        for pos in self:
            pos.is_spanish = (
                pos.company_id.country_code == "ES"
                and pos.l10n_es_simplified_invoice_journal_id
            )

    def _compute_simplified_partner_id(self):
        for config in self:
            config.simplified_partner_id = self.env.ref("l10n_es.partner_simplified").id

    def get_limited_partners_loading(self, offset=0):
        # the simplified partner must be loaded whatever the ranking says -- but
        # only for a Spanish till, and only on its first page: appended to every
        # page it came back once per page, and appended for every till it put a
        # Spanish partner in the list of companies that have no Spanish journal
        res = super().get_limited_partners_loading(offset)
        if not self.is_spanish or offset:
            return res
        if (self.simplified_partner_id.id,) not in res:
            res.append((self.simplified_partner_id.id,))
        return res
