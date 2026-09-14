import base64
from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType


class ResCompany(models.Model):
    _inherit = "res.company"

    _REPORT_STYLE_FIELDS: frozenset[str] = frozenset(
        {
            "external_report_layout_id",
            "font",
            "primary_color",
            "secondary_color",
            "report_theme_id",
        }
    )

    external_report_layout_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Document Template",
    )
    font = fields.Selection(
        selection=[
            ("Lato", "Lato"),
            ("Roboto", "Roboto"),
            ("Open_Sans", "Open Sans"),
            ("Montserrat", "Montserrat"),
            ("Oswald", "Oswald"),
            ("Raleway", "Raleway"),
            ("Tajawal", "Tajawal"),
            ("Fira_Mono", "Fira Mono"),
        ],
        default="Lato",
    )
    primary_color = fields.Char()
    secondary_color = fields.Char()
    layout_background = fields.Selection(
        selection=[
            ("Blank", "Blank"),
            ("Demo logo", "Demo logo"),
            ("Custom", "Custom"),
        ],
        default="Blank",
        required=True,
    )
    layout_background_image = fields.Binary(string="Background Image")
    homemenu_default_config = fields.Json(
        string="Default Home Menu Layout",
        help="The home menu layout a user of this company sees until they "
        "customise their own: the same shape as the user's setting.",
    )
    report_theme_id = fields.Many2one(
        comodel_name="report.theme",
        default=lambda self: self.env.ref(
            "web.report_theme_modern", raise_if_not_found=False
        ),
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        companies = super().create(vals_list)
        if any(
            not self._REPORT_STYLE_FIELDS.isdisjoint(values) for values in vals_list
        ):
            self._update_asset_style()
        return companies

    def write(self, vals: dict[str, Any]) -> bool:
        res = super().write(vals)
        if not self._REPORT_STYLE_FIELDS.isdisjoint(vals):
            self.env.registry.clear_cache("assets")
            self._update_asset_style()
        return res

    def _get_asset_style_b64(self) -> bytes:
        company_ids = self.sudo().search([])
        company_styles = self.env["ir.qweb"]._render(
            "web.styles_company_report",
            {
                "company_ids": company_ids,
            },
            raise_if_not_found=False,
        )
        return base64.b64encode(company_styles.encode())

    @api.model
    def _update_report_theme_default(self) -> None:
        modern = self.env.ref("web.report_theme_modern", raise_if_not_found=False)
        if not modern:
            return
        self.sudo().search([("report_theme_id", "=", False)]).report_theme_id = modern

    def _update_asset_style(self) -> None:
        asset_attachment = self.env.ref(
            "web.asset_styles_company_report", raise_if_not_found=False
        )
        if not asset_attachment:
            return
        asset_attachment = asset_attachment.sudo()
        b64_val = self._get_asset_style_b64()
        if b64_val != asset_attachment.datas:
            asset_attachment.write({"datas": b64_val})
