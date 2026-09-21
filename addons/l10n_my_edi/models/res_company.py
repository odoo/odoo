from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = (
        "l10n_my_identification_type",
        "l10n_my_identification_number",
        "l10n_my_edi_industrial_classification",
    )

    l10n_my_edi_config_id = fields.Many2one(
        comodel_name="l10n_my_edi.config",
        compute="_compute_l10n_my_edi_config_id",
        search="_search_l10n_my_edi_config_id",
    )

    l10n_my_identification_number_placeholder = fields.Char(
        related="l10n_my_edi_config_id.l10n_my_identification_number_placeholder",
    )

    def _search_l10n_my_edi_config_id(self, operator, value):
        return self._search_config_link("l10n_my_edi.config", operator, value)

    def _compute_l10n_my_edi_config_id(self):
        configs = self.env["l10n_my_edi.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_my_edi_config_id = by_company.get(company.id, False)

    def _l10n_my_edi_create_proxy_user(self):
        """This method will create a new proxy user for the current company based on the selected mode, if no users already exists."""
        self.check_singleton()
        if not self.l10n_my_edi_config_id.l10n_my_edi_proxy_user_id:
            self.env["account_edi_proxy_client.user"]._register_proxy_user(
                self, "l10n_my_edi", self.l10n_my_edi_config_id.l10n_my_edi_mode
            )

    def _l10n_my_edi_enabled(self):
        self.check_singleton()
        return bool(self.sudo().l10n_my_edi_config_id.l10n_my_edi_proxy_user_id)
