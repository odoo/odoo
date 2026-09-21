from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = ("l10n_tr_tax_office_id",)

    l10n_tr_nilvera_einvoice_extended_config_id = fields.Many2one(
        comodel_name="l10n_tr_nilvera_einvoice_extended.config",
        compute="_compute_l10n_tr_nilvera_einvoice_extended_config_id",
        search="_search_l10n_tr_nilvera_einvoice_extended_config_id",
    )

    def _search_l10n_tr_nilvera_einvoice_extended_config_id(self, operator, value):
        return self._search_config_link(
            "l10n_tr_nilvera_einvoice_extended.config", operator, value
        )

    def _compute_l10n_tr_nilvera_einvoice_extended_config_id(self):
        configs = self.env["l10n_tr_nilvera_einvoice_extended.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_tr_nilvera_einvoice_extended_config_id = by_company.get(
                company.id, False
            )
