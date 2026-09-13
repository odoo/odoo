import logging
from math import ceil
from typing import Any

from markupsafe import Markup
from PIL.Image import Resampling

from odoo import api, fields, models
from odoo.libs.colors import get_lightness, get_saturation, rgb_to_hex
from odoo.libs.text import nl2br
from odoo.tools import html2plaintext, is_html_empty
from odoo.tools import image as tools

from odoo.addons.base.models.assetsbundle import ScssStylesheetAsset

_logger = logging.getLogger(__name__)

DEFAULT_PRIMARY = "#000000"
DEFAULT_SECONDARY = "#000000"


class BaseDocumentLayout(models.TransientModel):
    _name = "base.document.layout"
    _description = "Company Document Layout"

    @api.model
    def _default_report_footer(self) -> str:
        company = self.env.company
        footer_fields = [
            field
            for field in [
                company.phone_ids._primary().number,
                company.email,
                company.website,
                company.vat,
            ]
            if isinstance(field, str) and len(field) > 0
        ]
        return Markup(" ").join(footer_fields)

    @api.model
    def _default_company_details(self) -> str:
        company = self.env.company
        address_format, company_data = company.partner_id._prepare_display_address()
        address_format = self._clean_address_format(address_format, company_data)
        if "company_name" not in address_format:
            address_format = "%(company_name)s\n" + address_format
            company_data["company_name"] = company_data["company_name"] or company.name
        return nl2br(address_format) % company_data

    def _clean_address_format(
        self, address_format: str, company_data: dict[str, Any]
    ) -> str:
        missing_company_data = [k for k, v in company_data.items() if not v]
        for key in missing_company_data:
            if f"%({key})s" in address_format:
                address_format = address_format.replace(f"%({key})s\n", "")
                address_format = address_format.replace(f"%({key})s", "")
        return address_format

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    logo = fields.Binary(
        related="company_id.logo",
        readonly=False,
    )
    preview_logo = fields.Binary(
        related="logo",
        string="Preview logo",
    )
    report_header = fields.Html(
        related="company_id.report_header",
        readonly=False,
    )
    report_footer = fields.Html(
        related="company_id.report_footer",
        default=_default_report_footer,
        readonly=False,
    )
    company_details = fields.Html(
        related="company_id.company_details",
        default=_default_company_details,
        readonly=False,
    )
    is_company_details_empty = fields.Boolean(
        compute="_compute_is_company_details_empty"
    )
    paperformat_id = fields.Many2one(
        related="company_id.paperformat_id",
        readonly=False,
    )
    external_report_layout_id = fields.Many2one(
        related="company_id.external_report_layout_id",
        readonly=False,
    )
    font = fields.Selection(
        related="company_id.font",
        readonly=False,
    )
    primary_color = fields.Char(
        related="company_id.primary_color",
        readonly=False,
    )
    secondary_color = fields.Char(
        related="company_id.secondary_color",
        readonly=False,
    )
    custom_colors = fields.Boolean(
        compute="_compute_custom_colors",
        readonly=False,
    )
    logo_primary_color = fields.Char(compute="_compute_logo_colors")
    logo_secondary_color = fields.Char(compute="_compute_logo_colors")
    layout_background = fields.Selection(
        related="company_id.layout_background",
        readonly=False,
    )
    layout_background_image = fields.Binary(
        related="company_id.layout_background_image",
        readonly=False,
    )
    report_layout_id = fields.Many2one(comodel_name="report.layout")
    report_theme_id = fields.Many2one(
        related="company_id.report_theme_id",
        readonly=False,
    )
    preview = fields.Html(
        sanitize=False,
        compute="_compute_preview",
    )
    partner_id = fields.Many2one(
        related="company_id.partner_id",
        readonly=True,
    )
    phone_ids = fields.Many2many(
        related="company_id.phone_ids",
        readonly=True,
    )
    email = fields.Char(
        related="company_id.email",
        readonly=True,
    )
    website = fields.Char(
        related="company_id.website",
        readonly=True,
    )
    vat = fields.Char(
        related="company_id.vat",
        readonly=True,
    )
    name = fields.Char(
        related="company_id.name",
        readonly=True,
    )
    country_id = fields.Many2one(
        related="company_id.country_id",
        readonly=True,
    )

    @api.depends(
        "logo_primary_color",
        "logo_secondary_color",
        "primary_color",
        "secondary_color",
    )
    def _compute_custom_colors(self) -> None:
        for wizard in self:
            logo_primary = wizard.logo_primary_color or ""
            logo_secondary = wizard.logo_secondary_color or ""
            wizard.custom_colors = (
                wizard.logo
                and wizard.primary_color
                and wizard.secondary_color
                and not (
                    wizard.primary_color.lower() == logo_primary.lower()
                    and wizard.secondary_color.lower() == logo_secondary.lower()
                )
            )

    @api.depends("logo")
    def _compute_logo_colors(self) -> None:
        for wizard in self:
            if wizard.env.context.get("bin_size"):
                wizard_for_image = wizard.with_context(bin_size=False)
            else:
                wizard_for_image = wizard
            wizard.logo_primary_color, wizard.logo_secondary_color = (
                wizard.extract_image_primary_secondary_colors(wizard_for_image.logo)
            )

    @api.depends(
        "report_layout_id",
        "report_theme_id",
        "logo",
        "font",
        "primary_color",
        "secondary_color",
        "report_header",
        "report_footer",
        "layout_background",
        "layout_background_image",
        "company_details",
    )
    def _compute_preview(self) -> None:
        styles = self._get_asset_style()

        for wizard in self:
            if wizard.report_layout_id:
                if wizard.env.context.get("bin_size"):
                    wizard = wizard.with_context(bin_size=False)
                wizard.preview = wizard.env["ir.ui.view"]._render_template(
                    wizard._get_preview_template(),
                    wizard._get_render_information(styles),
                )
            else:
                wizard.preview = False

    def _get_preview_template(self) -> str:
        return "web.report_invoice_wizard_preview"

    def _get_render_information(self, styles: str) -> dict[str, Any]:
        self.check_singleton()
        preview_css = self._get_css_for_preview(styles)
        return {
            "company": self,
            "preview_css": preview_css,
            "is_html_empty": is_html_empty,
        }

    @api.onchange("company_id")
    def _onchange_company_id(self) -> None:
        for wizard in self:
            wizard.logo = wizard.company_id.logo
            wizard.report_header = wizard.company_id.report_header
            wizard.report_footer = (
                wizard.company_id.report_footer
                if isinstance(wizard.company_id.report_footer, str)
                else wizard.report_footer
            )
            wizard.company_details = (
                wizard.company_id.company_details
                if isinstance(wizard.company_id.company_details, str)
                else wizard.company_details
            )
            wizard.paperformat_id = wizard.company_id.paperformat_id
            wizard.external_report_layout_id = (
                wizard.company_id.external_report_layout_id
            )
            wizard.font = wizard.company_id.font
            wizard.primary_color = wizard.company_id.primary_color
            wizard.secondary_color = wizard.company_id.secondary_color
            wizard_layout = wizard.env["report.layout"].search(  # noqa: E8507 - a transient wizard: one record
                [
                    (
                        "view_id.key",
                        "=",
                        wizard.company_id.external_report_layout_id.key,
                    )
                ]
            )
            wizard.report_layout_id = wizard_layout or wizard_layout.search([], limit=1)

            if not wizard.primary_color:
                wizard.primary_color = wizard.logo_primary_color or DEFAULT_PRIMARY
            if not wizard.secondary_color:
                wizard.secondary_color = (
                    wizard.logo_secondary_color or DEFAULT_SECONDARY
                )

    @api.onchange("custom_colors")
    def _onchange_custom_colors(self) -> None:
        for wizard in self:
            if wizard.logo and not wizard.custom_colors:
                wizard.primary_color = wizard.logo_primary_color or DEFAULT_PRIMARY
                wizard.secondary_color = (
                    wizard.logo_secondary_color or DEFAULT_SECONDARY
                )

    @api.onchange("report_layout_id")
    def _onchange_report_layout_id(self) -> None:
        for wizard in self:
            wizard.external_report_layout_id = wizard.report_layout_id.view_id

    @api.onchange("logo")
    def _onchange_logo(self) -> None:
        for wizard in self:
            company = wizard.company_id
            if (
                wizard.logo == company.logo
                and company.primary_color
                and company.secondary_color
            ):
                continue

            if wizard.logo_primary_color:
                wizard.primary_color = wizard.logo_primary_color
            if wizard.logo_secondary_color:
                wizard.secondary_color = wizard.logo_secondary_color

    @api.model
    def extract_image_primary_secondary_colors(
        self, logo: Any, white_threshold: int = 225, mitigate: int = 175
    ) -> tuple[str | bool, str | bool]:
        if not logo:
            return False, False
        if not isinstance(logo, (str, bytes)):
            return False, False
        padding = -len(logo) % 4
        logo += b"=" * padding if isinstance(logo, bytes) else "=" * padding
        try:
            image = tools.image_fix_orientation(tools.base64_to_image(logo))
        except Exception:
            _logger.debug(
                "Could not parse logo image for color extraction", exc_info=True
            )
            return False, False

        base_w, base_h = image.size
        w = ceil(50 * base_w / base_h)
        h = 50

        image_converted = image.convert("RGBA")
        image_resized = image_converted.resize((w, h), resample=Resampling.NEAREST)

        colors = [
            color
            for color in (image_resized.getcolors(w * h) or [])
            if not (
                color[1][0] > white_threshold
                and color[1][1] > white_threshold
                and color[1][2] > white_threshold
            )
            and color[1][3] > 0
        ]

        if not colors:
            return False, False
        primary, remaining = tools.average_dominant_color(colors, mitigate=mitigate)
        secondary = (
            tools.average_dominant_color(remaining, mitigate=mitigate)[0]
            if remaining
            else primary
        )

        l_primary = get_lightness(primary)
        l_secondary = get_lightness(secondary)
        if (l_primary < 0.2 and l_secondary < 0.2) or (
            l_primary >= 0.2 and l_secondary >= 0.2
        ):
            s_primary = get_saturation(primary)
            s_secondary = get_saturation(secondary)
            if s_primary < s_secondary:
                primary, secondary = secondary, primary
        elif l_secondary > l_primary:
            primary, secondary = secondary, primary

        return rgb_to_hex(primary), rgb_to_hex(secondary)

    def action_save_layout(self) -> dict[str, Any]:
        return self.env.context.get("report_action") or {
            "type": "ir.actions.act_window_close"
        }

    def _get_asset_style(self) -> str:
        return self.env["ir.qweb"]._render(
            "web.styles_company_report",
            {
                "company_ids": self,
            },
            raise_if_not_found=False,
        )

    @api.model
    def _get_css_for_preview(self, scss: str) -> str:
        if not scss.strip():
            return ""
        asset = ScssStylesheetAsset.for_inline_compile("// css_for_preview")
        css_code = asset.compile(scss)
        return Markup(css_code) if isinstance(scss, Markup) else css_code

    @api.depends("company_details")
    def _compute_is_company_details_empty(self) -> None:
        for record in self:
            record.is_company_details_empty = not html2plaintext(
                record.company_details or ""
            )
