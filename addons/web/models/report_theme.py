from markupsafe import Markup

from odoo import fields, models

_CSS_UNSAFE = str.maketrans("", "", "{};\n\r<>")


class ReportTheme(models.Model):
    _name = "report.theme"
    _description = "Report Theme"
    _order = "sequence, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=50)

    font_body = fields.Char(
        string="Body font",
        help="CSS font-family for running text. Empty uses the company font.",
    )
    font_display = fields.Char(
        string="Display font",
        help="CSS font-family for the document title and grand total. "
        "Empty uses the body font.",
    )

    row_padding = fields.Char(
        string="Table row padding",
        default="0.5rem",
        help="Vertical padding of table rows (CSS length), e.g. 0.3rem for a "
        "dense ledger or 0.7rem for a roomier document.",
    )
    border_radius = fields.Char(
        string="Corner radius",
        default="0",
        help="Corner radius for totals bands and boxed elements (CSS length).",
    )
    rule_weight = fields.Char(
        string="Rule weight",
        default="1px",
        help="Thickness of the accent rule under table headers (CSS length).",
    )

    _STYLE_FIELDS = frozenset(
        {"font_body", "font_display", "row_padding", "border_radius", "rule_weight"}
    )

    def write(self, vals):
        res = super().write(vals)
        if not self._STYLE_FIELDS.isdisjoint(vals):
            self.env["res.company"]._update_asset_style()
        return res

    def unlink(self):
        in_use = bool(
            self.env["report.config"]
            .sudo()
            .search_count([("report_theme_id", "in", self.ids)], limit=1)
        )
        res = super().unlink()
        if in_use:
            self.env["res.company"]._update_asset_style()
        return res

    def _get_css_vars(self, primary: str, secondary: str, base_font: str) -> Markup:
        theme = self[:1]

        def css(value: str) -> str:
            return str(value).translate(_CSS_UNSAFE).strip()

        body = css(theme.font_body or base_font)
        display = css(theme.font_display or body)
        return Markup(
            "--rp-accent: %s;\n"
            "--rp-secondary: %s;\n"
            "--rp-font: %s;\n"
            "--rp-font-display: %s;\n"
            "--rp-density: %s;\n"
            "--rp-radius: %s;\n"
            "--rp-rule: %s;"
        ) % (
            css(primary),
            css(secondary),
            Markup(body),
            Markup(display),
            Markup(css(theme.row_padding or "0.5rem")),
            Markup(css(theme.border_radius or "0")),
            Markup(css(theme.rule_weight or "1px")),
        )
