from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_tw_edi_ecpay_config_id = fields.Many2one(
        comodel_name="l10n_tw_edi_ecpay.config",
        compute="_compute_l10n_tw_edi_ecpay_config_id",
        search="_search_l10n_tw_edi_ecpay_config_id",
    )

    def _search_l10n_tw_edi_ecpay_config_id(self, operator, value):
        return self._search_config_link("l10n_tw_edi_ecpay.config", operator, value)

    def _compute_l10n_tw_edi_ecpay_config_id(self):
        configs = self.env["l10n_tw_edi_ecpay.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_tw_edi_ecpay_config_id = by_company.get(company.id, False)

    def _is_ecpay_enabled(self):
        return bool(
            self.sudo().l10n_tw_edi_ecpay_merchant_id
            and self.sudo().l10n_tw_edi_ecpay_hashkey
            and self.sudo().l10n_tw_edi_ecpay_hashIV
        )
