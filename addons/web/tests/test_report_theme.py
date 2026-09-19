import base64

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "web_unit", "report_theme")
class TestReportTheme(TransactionCase):
    def test_css_vars_defaults_on_empty_recordset(self):
        css = self.env["report.theme"]._get_css_vars("#111", "#222", "Lato")
        self.assertIn("--rp-accent: #111;", css)
        self.assertIn("--rp-secondary: #222;", css)
        self.assertIn("--rp-font: Lato;", css)
        self.assertIn("--rp-density: 0.5rem;", css)
        self.assertIn("--rp-rule: 1px;", css)

    def test_font_fallback_chain(self):
        theme = self.env["report.theme"].create({"name": "T", "font_body": False})
        css = theme._get_css_vars("#111", "#222", "Georgia, serif")
        self.assertIn("--rp-font: Georgia, serif;", css)
        self.assertIn("--rp-font-display: Georgia, serif;", css)

        theme.font_display = "'Playfair Display', serif"
        css = theme._get_css_vars("#111", "#222", "Lato")
        self.assertIn("--rp-font: Lato;", css)
        self.assertIn("--rp-font-display: 'Playfair Display', serif;", css)

    def test_css_vars_strip_declaration_breakers(self):
        theme = self.env["report.theme"].create(
            {
                "name": "Hostile",
                "font_body": "Georgia; } body { color: red } \n",
                "row_padding": "1rem;}{",
            }
        )
        css = str(theme._get_css_vars("#111", "#222", "Lato"))
        self.assertNotIn("{", css.replace("&#39;", ""))
        self.assertNotIn("}", css)
        self.assertEqual(css.count(";"), 7)

    def test_company_stylesheet_carries_tokens(self):
        css = base64.b64decode(self.env["res.company"]._get_asset_style_b64()).decode()
        for token in ("--rp-accent", "--rp-font", "--rp-density", "--rp-rule"):
            self.assertIn(token, css)

    def test_default_theme_backfill_is_idempotent(self):
        modern = self.env.ref("web.report_theme_modern")
        ledger = self.env.ref("web.report_theme_ledger")
        company = self.env["res.company"].create({"name": "Backfill Co"})
        company.report_config_id.report_theme_id = False
        chosen = self.env["res.company"].create({"name": "Chosen Co"})
        chosen.report_config_id.report_theme_id = ledger
        self.env["report.config"]._update_report_theme_default()
        self.assertEqual(company.report_config_id.report_theme_id, modern)
        self.assertEqual(chosen.report_config_id.report_theme_id, ledger)

    def test_theme_change_regenerates_company_stylesheet(self):
        attachment = self.env.ref("web.asset_styles_company_report")
        before = attachment.datas
        self.env.company.report_config_id.report_theme_id = self.env.ref(
            "web.report_theme_editorial"
        )
        after = self.env.ref("web.asset_styles_company_report").datas
        self.assertNotEqual(before, after)
        self.assertIn("Georgia", base64.b64decode(after).decode())

    def test_editing_theme_token_regenerates_company_stylesheet(self):
        theme = self.env.ref("web.report_theme_modern")
        self.env.company.report_config_id.report_theme_id = theme
        before = self.env.ref("web.asset_styles_company_report").datas
        theme.row_padding = "2.5rem"
        after = self.env.ref("web.asset_styles_company_report").datas
        self.assertNotEqual(before, after)
        self.assertIn("2.5rem", base64.b64decode(after).decode())

    def test_editing_theme_non_token_field_skips_regeneration(self):
        theme = self.env.ref("web.report_theme_modern")
        self.env.company.report_config_id.report_theme_id = theme
        before = self.env.ref("web.asset_styles_company_report").datas
        theme.sequence += 5
        after = self.env.ref("web.asset_styles_company_report").datas
        self.assertEqual(before, after)

    def test_condensed_theme_shipped(self):
        theme = self.env.ref("web.report_theme_condensed")
        css = str(theme._get_css_vars("#111", "#222", "Lato"))
        self.assertIn("--rp-font-display: Oswald", css)
