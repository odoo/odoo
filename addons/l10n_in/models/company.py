from odoo import Command, api, fields, models
from odoo.exceptions import RedirectWarning


class ResCompany(models.Model):
    _inherit = "res.company"
    _inherits_sudo_fields = (
        "l10n_in_pan_entity_id",
        "l10n_in_tan",
        "l10n_in_gst_state_warning",
    )

    # a projection of the company's own PAN entity, not a setting: its path
    # starts at a field the company itself declares
    l10n_in_pan_type = fields.Selection(
        related="l10n_in_pan_entity_id.type",
        string="PAN Type",
    )

    l10n_in_upi_id = fields.Char(
        related="l10n_in_config_id.l10n_in_upi_id",
        readonly=False,
    )

    l10n_in_config_id = fields.Many2one(
        comodel_name="l10n_in.config",
        compute="_compute_l10n_in_config_id",
        search="_search_l10n_in_config_id",
    )

    def _search_l10n_in_config_id(self, operator, value):
        return self._search_config_link("l10n_in.config", operator, value)

    def _compute_l10n_in_config_id(self):
        configs = self.env["l10n_in.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.l10n_in_config_id = by_company.get(company.id, False)

    def _activate_l10n_in_taxes(self, group_refs, company):
        for group_ref in group_refs:
            tax_group = (
                self.env["account.chart.template"]
                .with_company(company)
                .ref(group_ref, raise_if_not_found=False)
            )
            if not tax_group:
                continue
            taxes = (
                self.env["account.tax"]  # noqa: E8507 - chart setup: one query per tax group of the company
                .with_company(company)
                .with_context(active_test=False)
                .search(
                    [
                        ("tax_group_id", "=", tax_group.id),
                    ]
                )
            )
            taxes.write({"active": True})

    @api.onchange("vat")
    def onchange_vat(self):
        self.partner_id.onchange_vat()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        # Update Fiscal Positions for new branch
        res._update_l10n_in_fiscal_position()
        return res

    def write(self, vals):
        res = super().write(vals)
        if vals.get("vat"):
            # Enable GST(l10n_in_is_gst_registered) when a valid GSTIN(vat) is applied.
            self._update_l10n_in_is_gst_registered()
        if (
            vals.get("state_id") or vals.get("country_id")
        ) and not self.env.context.get("delay_account_group_sync"):
            # Update Fiscal Positions for companies setting up state for the first time
            self._update_l10n_in_fiscal_position()
        return res

    def _update_l10n_in_fiscal_position(self):
        companies_need_update_fp = self.filtered(
            lambda c: c.parent_ids[0].account_config_id.chart_template == "in"
        )
        for company in companies_need_update_fp:
            ChartTemplate = self.env["account.chart.template"].with_company(company)
            fiscal_position_data = ChartTemplate._get_in_account_fiscal_position()
            for values in fiscal_position_data.values():
                values["tax_ids"] = [
                    Command.set(
                        [
                            xml_id
                            for xml_id in values["tax_ids"][0][2]
                            if ChartTemplate.ref(xml_id, raise_if_not_found=False)
                        ]
                    )
                ]
            ChartTemplate._load_data({"account.fiscal.position": fiscal_position_data})

    def _update_l10n_in_is_gst_registered(self):
        for company in self:
            if company.country_code == "IN" and company.vat:
                company.l10n_in_config_id.l10n_in_is_gst_registered = (
                    company.partner_id.check_vat_in(company.vat)
                )

    def action_update_state_as_per_gstin(self):
        self.check_singleton()
        self.partner_id.action_update_state_as_per_gstin()

    def _check_tax_return_configuration(self):
        """
        Check if the company is properly configured for tax returns.
        :raises RedirectWarning: if something is wrong configured.
        """

        if self.country_code != "IN":
            return super()._check_tax_return_configuration()

        is_l10n_in_reports_installed = (
            "l10n_in_reports"
            in self.env["ir.module.module"]._get_installed_module_ids()
        )
        if not is_l10n_in_reports_installed:
            msg = self.env._(
                "First enable GST e-Filing feature from configuration for company %s.",
                (self.name),
            )
            action = self.env.ref("account.action_account_config")
            raise RedirectWarning(msg, action.id, self.env._("Go to configuration"))
        return None
