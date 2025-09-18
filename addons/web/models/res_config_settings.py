from typing import Any

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    web_app_name = fields.Char("Web App Name", config_parameter="web.web_app_name")

    # --- Company ---
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    is_root_company = fields.Boolean(compute="_compute_is_root_company")
    company_name = fields.Char(related="company_id.display_name", string="Company Name")
    company_informations = fields.Text(compute="_compute_company_informations")
    company_country_code = fields.Char(
        related="company_id.country_id.code",
        string="Company Country Code",
        readonly=True,
    )
    company_country_group_codes = fields.Json(
        related="company_id.country_id.country_group_codes"
    )
    company_count = fields.Integer(
        "Number of Companies", compute="_compute_company_count"
    )
    report_footer = fields.Html(
        related="company_id.report_footer",
        string="Custom Report Footer",
        help="Footer text displayed at the bottom of all reports.",
        readonly=False,
    )
    external_report_layout_id = fields.Many2one(
        related="company_id.external_report_layout_id"
    )

    # --- Users & languages ---
    active_user_count = fields.Integer(
        "Number of Active Users", compute="_compute_active_user_count"
    )
    language_count = fields.Integer(
        "Number of Languages", compute="_compute_language_count"
    )

    # --- Module toggles ---
    module_base_import = fields.Boolean(
        "Allow users to import data from CSV/XLS/XLSX/ODS files"
    )
    module_google_calendar = fields.Boolean(
        string="Allow the users to synchronize their calendar with Google Calendar"
    )
    module_microsoft_calendar = fields.Boolean(
        string="Allow the users to synchronize their calendar with Outlook Calendar"
    )
    module_mail_plugin = fields.Boolean(
        string="Allow integration with the mail plugins"
    )
    module_auth_oauth = fields.Boolean("Use external authentication providers (OAuth)")
    module_auth_ldap = fields.Boolean("LDAP Authentication")
    module_account_inter_company_rules = fields.Boolean("Manage Inter Company")
    module_voip = fields.Boolean("Phone")
    module_web_unsplash = fields.Boolean("Unsplash Image Library")
    module_sms = fields.Boolean("SMS")
    module_partner_autocomplete = fields.Boolean("Partner Autocomplete")
    module_base_geolocalize = fields.Boolean("GeoLocalize")
    module_google_recaptcha = fields.Boolean("reCAPTCHA")
    module_website_cf_turnstile = fields.Boolean("Cloudflare Turnstile")
    module_google_address_autocomplete = fields.Boolean("Google Address Autocomplete")

    # --- Groups ---
    group_multi_currency = fields.Boolean(
        string="Multi-Currencies",
        implied_group="base.group_multi_currency",
        help="Allows to work in a multi currency environment",
    )

    # --- UI / misc ---
    show_effect = fields.Boolean(
        string="Show Effect", config_parameter="base.show_effect"
    )
    profiling_enabled_until = fields.Datetime(
        "Profiling enabled until",
        config_parameter="base.profiling_enabled_until",
    )

    def open_company(self) -> dict[str, Any]:
        """Open the current company form."""
        return {
            "type": "ir.actions.act_window",
            "name": "My Company",
            "view_mode": "form",
            "res_model": "res.company",
            "res_id": self.env.company.id,
            "target": "current",
        }

    def open_new_user_default_groups(self) -> dict[str, Any]:
        """Open (or create) the default access group for new users."""
        default_group = self.env.ref(
            "base.default_user_group", raise_if_not_found=False
        )
        if not default_group:
            default_group = self.env["res.groups"].create(
                {
                    "name": _("Default access for new users"),
                }
            )
            self.env["ir.model.data"].create(
                {
                    "name": "default_user_group",
                    "module": "base",
                    "res_id": default_group.id,
                    "model": "res.groups",
                    "noupdate": True,
                }
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Edit new user default group"),
            "view_mode": "form",
            "res_model": "res.groups",
            "res_id": default_group.id,
            "views": [(self.env.ref("base.view_default_groups_form").id, "form")],
            "target": "new",
        }

    @api.model
    def _prepare_report_view_action(self, template: str) -> dict[str, Any]:
        """Return an act_window action to edit the given QWeb report template."""
        template_id = self.env.ref(template)
        return {
            "type": "ir.actions.act_window",
            "res_model": "ir.ui.view",
            "view_mode": "form",
            "res_id": template_id.id,
        }

    def edit_external_header(self) -> dict[str, Any] | bool:
        """Open the external report layout template for editing."""
        if not self.external_report_layout_id:
            return False
        return self._prepare_report_view_action(self.external_report_layout_id.key)

    # NOTE: TransientModel computed fields must depend on a stored field
    # to avoid being evaluated without context. company_id is used as the trigger.
    @api.depends("company_id")
    def _compute_company_count(self) -> None:
        company_count = self.env["res.company"].sudo().search_count([])
        for record in self:
            record.company_count = company_count

    @api.depends("company_id")
    def _compute_active_user_count(self) -> None:
        active_user_count = (
            self.env["res.users"].sudo().search_count([("share", "=", False)])
        )
        for record in self:
            record.active_user_count = active_user_count

    @api.depends("company_id")
    def _compute_language_count(self) -> None:
        language_count = len(self.env["res.lang"].get_installed())
        for record in self:
            record.language_count = language_count

    @api.depends("company_id")
    def _compute_company_informations(self) -> None:
        for record in self:
            parts = []
            c = record.company_id
            if c.street:
                parts.append(f"{c.street}\n")
            if c.street2:
                parts.append(f"{c.street2}\n")
            if c.zip and c.city:
                parts.append(f"{c.zip} - {c.city}\n")
            elif c.zip:
                parts.append(f"{c.zip}\n")
            elif c.city:
                parts.append(f"{c.city}\n")
            if c.state_id:
                parts.append(f"{c.state_id.display_name}\n")
            if c.country_id:
                parts.append(c.country_id.display_name)
            if c.vat:
                vat_label = c.country_id.vat_label or _("VAT")
                parts.append(f"\n{vat_label}: {c.vat}")
            record.company_informations = "".join(parts)

    @api.depends("company_id")
    def _compute_is_root_company(self) -> None:
        for record in self:
            record.is_root_company = not record.company_id.parent_id
