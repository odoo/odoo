# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import odoo.tests.common as common

from ..models.accounting_none import AccountingNone
from ..models.data_error import DataError
from ..models.mis_report_style import CMP_DIFF, CMP_PCT, TYPE_NUM, TYPE_PCT, TYPE_STR


class TestRendering(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.style_obj = self.env["mis.report.style"]
        self.kpi_obj = self.env["mis.report.kpi"]
        self.style = self.style_obj.create(dict(name="teststyle"))
        self.lang = (
            self.env["res.lang"]
            .with_context(active_test=False)
            .search([("code", "=", "en_US")])[0]
        )

    def _render(self, value, var_type=TYPE_NUM):
        style_props = self.style_obj.merge([self.style])
        return self.style_obj.render(self.lang, style_props, var_type, value)

    def _compare_and_render(
        self, value, base_value, var_type=TYPE_NUM, compare_method=CMP_PCT
    ):
        style_props = self.style_obj.merge([self.style])
        r = self.style_obj.compare_and_render(
            self.lang, style_props, var_type, compare_method, value, base_value
        )[:2]
        if r[0]:
            return (round(r[0], 8), r[1])
        else:
            return r

    def test_render(self):
        self.assertEqual("1", self._render(1))
        self.assertEqual("1", self._render(1.1))
        self.assertEqual("2", self._render(1.6))
        self.style.dp_inherit = False
        self.style.dp = 2
        self.assertEqual("1.00", self._render(1))
        self.assertEqual("1.10", self._render(1.1))
        self.assertEqual("1.60", self._render(1.6))
        self.assertEqual("1.61", self._render(1.606))
        self.assertEqual("12,345.67", self._render(12345.67))

    def test_render_negative(self):
        # non breaking hyphen
        self.assertEqual("\u20111", self._render(-1))

    def test_render_zero(self):
        self.assertEqual("0", self._render(0))
        self.assertEqual("", self._render(None))
        self.assertEqual("", self._render(AccountingNone))

    def test_render_suffix(self):
        self.style.suffix_inherit = False
        self.style.suffix = "€"
        self.assertEqual("1\xa0€", self._render(1))
        self.style.suffix = "k€"
        self.style.divider_inherit = False
        self.style.divider = "1e3"
        self.assertEqual("1\xa0k€", self._render(1000))

    def test_render_prefix(self):
        self.style.prefix_inherit = False
        self.style.prefix = "$"
        self.assertEqual("$\xa01", self._render(1))
        self.style.prefix = "k$"
        self.style.divider_inherit = False
        self.style.divider = "1e3"
        self.assertEqual("k$\xa01", self._render(1000))

    def test_render_divider(self):
        self.style.divider_inherit = False
        self.style.divider = "1e3"
        self.style.dp_inherit = False
        self.style.dp = 0
        self.assertEqual("1", self._render(1000))
        self.style.divider = "1e6"
        self.style.dp = 3
        self.assertEqual("0.001", self._render(1000))
        self.style.divider = "1e-3"
        self.style.dp = 0
        self.assertEqual("1,000", self._render(1))
        self.style.divider = "1e-6"
        self.style.dp = 0
        self.assertEqual("1,000,000", self._render(1))

    def test_render_pct(self):
        self.assertEqual("100\xa0%", self._render(1, TYPE_PCT))
        self.assertEqual("50\xa0%", self._render(0.5, TYPE_PCT))
        self.style.dp_inherit = False
        self.style.dp = 2
        self.assertEqual("51.23\xa0%", self._render(0.5123, TYPE_PCT))

    def test_render_string(self):
        self.assertEqual("", self._render("", TYPE_STR))
        self.assertEqual("", self._render(None, TYPE_STR))
        self.assertEqual("abcdé", self._render("abcdé", TYPE_STR))

    def test_compare_num_pct(self):
        self.assertEqual((1.0, "+100.0\xa0%"), self._compare_and_render(100, 50))
        self.assertEqual((0.5, "+50.0\xa0%"), self._compare_and_render(75, 50))
        self.assertEqual((0.5, "+50.0\xa0%"), self._compare_and_render(-25, -50))
        self.assertEqual((1.0, "+100.0\xa0%"), self._compare_and_render(0, -50))
        self.assertEqual((2.0, "+200.0\xa0%"), self._compare_and_render(50, -50))
        self.assertEqual((-0.5, "\u201150.0\xa0%"), self._compare_and_render(25, 50))
        self.assertEqual((-1.0, "\u2011100.0\xa0%"), self._compare_and_render(0, 50))
        self.assertEqual((-2.0, "\u2011200.0\xa0%"), self._compare_and_render(-50, 50))
        self.assertEqual((-0.5, "\u201150.0\xa0%"), self._compare_and_render(-75, -50))
        self.assertEqual(
            (AccountingNone, ""), self._compare_and_render(50, AccountingNone)
        )
        self.assertEqual((AccountingNone, ""), self._compare_and_render(50, None))
        self.assertEqual((AccountingNone, ""), self._compare_and_render(50, 50))
        self.assertEqual((0.002, "+0.2\xa0%"), self._compare_and_render(50.1, 50))
        self.assertEqual((AccountingNone, ""), self._compare_and_render(50.01, 50))
        self.assertEqual(
            (-1.0, "\u2011100.0\xa0%"), self._compare_and_render(AccountingNone, 50)
        )
        self.assertEqual((-1.0, "\u2011100.0\xa0%"), self._compare_and_render(None, 50))
        self.assertEqual(
            (AccountingNone, ""), self._compare_and_render(DataError("#ERR", "."), 1)
        )
        self.assertEqual(
            (AccountingNone, ""), self._compare_and_render(1, DataError("#ERR", "."))
        )

    def test_compare_num_diff(self):
        self.assertEqual(
            (25, "+25"), self._compare_and_render(75, 50, TYPE_NUM, CMP_DIFF)
        )
        self.assertEqual(
            (-25, "\u201125"), self._compare_and_render(25, 50, TYPE_NUM, CMP_DIFF)
        )
        self.style.suffix_inherit = False
        self.style.suffix = "€"
        self.assertEqual(
            (-25, "\u201125\xa0€"),
            self._compare_and_render(25, 50, TYPE_NUM, CMP_DIFF),
        )
        self.style.suffix = ""
        self.assertEqual(
            (50.0, "+50"),
            self._compare_and_render(50, AccountingNone, TYPE_NUM, CMP_DIFF),
        )
        self.assertEqual(
            (50.0, "+50"), self._compare_and_render(50, None, TYPE_NUM, CMP_DIFF)
        )
        self.assertEqual(
            (-50.0, "\u201150"),
            self._compare_and_render(AccountingNone, 50, TYPE_NUM, CMP_DIFF),
        )
        self.assertEqual(
            (-50.0, "\u201150"), self._compare_and_render(None, 50, TYPE_NUM, CMP_DIFF)
        )
        self.style.dp_inherit = False
        self.style.dp = 2
        self.assertEqual(
            (0.1, "+0.10"), self._compare_and_render(1.1, 1.0, TYPE_NUM, CMP_DIFF)
        )
        self.assertEqual(
            (AccountingNone, ""),
            self._compare_and_render(1.001, 1.0, TYPE_NUM, CMP_DIFF),
        )

    def test_compare_pct(self):
        self.assertEqual(
            (0.25, "+25\xa0pp"), self._compare_and_render(0.75, 0.50, TYPE_PCT)
        )
        self.assertEqual(
            (AccountingNone, ""), self._compare_and_render(0.751, 0.750, TYPE_PCT)
        )

    def test_compare_pct_result_type(self):
        style_props = self.style_obj.merge([self.style])
        result = self.style_obj.compare_and_render(
            self.lang, style_props, TYPE_PCT, CMP_DIFF, 0.75, 0.50
        )
        self.assertEqual(result[3], TYPE_NUM)

    def test_merge(self):
        self.style.color = "#FF0000"
        self.style.color_inherit = False
        style_props = self.style_obj.merge([self.style])
        self.assertEqual(style_props, {"color": "#FF0000"})
        style_dict = {"color": "#00FF00", "dp": 0}
        style_props = self.style_obj.merge([self.style, style_dict])
        self.assertEqual(style_props, {"color": "#00FF00", "dp": 0})
        style2 = self.style_obj.create(
            dict(
                name="teststyle2",
                dp_inherit=False,
                dp=1,
                # color_inherit=True: will not be applied
                color="#0000FF",
            )
        )
        style_props = self.style_obj.merge([self.style, style_dict, style2])
        self.assertEqual(style_props, {"color": "#00FF00", "dp": 1})

    def test_css(self):
        self.style.color_inherit = False
        self.style.color = "#FF0000"
        self.style.background_color_inherit = False
        self.style.background_color = "#0000FF"
        self.style.suffix_inherit = False
        self.style.suffix = "s"
        self.style.prefix_inherit = False
        self.style.prefix = "p"
        self.style.font_style_inherit = False
        self.style.font_style = "italic"
        self.style.font_weight_inherit = False
        self.style.font_weight = "bold"
        self.style.font_size_inherit = False
        self.style.font_size = "small"
        self.style.indent_level_inherit = False
        self.style.indent_level = 2
        style_props = self.style_obj.merge([self.style])
        css = self.style_obj.to_css_style(style_props)
        self.assertEqual(
            css,
            "font-style: italic; "
            "font-weight: bold; "
            "font-size: small; "
            "color: #FF0000; "
            "background-color: #0000FF; "
            "text-indent: 2em",
        )
        css = self.style_obj.to_css_style(style_props, no_indent=True)
        self.assertEqual(
            css,
            "font-style: italic; "
            "font-weight: bold; "
            "font-size: small; "
            "color: #FF0000; "
            "background-color: #0000FF",
        )

    def test_xslx(self):
        self.style.color_inherit = False
        self.style.color = "#FF0000"
        self.style.background_color_inherit = False
        self.style.background_color = "#0000FF"
        self.style.suffix_inherit = False
        self.style.suffix = "s"
        self.style.prefix_inherit = False
        self.style.prefix = "p"
        self.style.dp_inherit = False
        self.style.dp = 2
        self.style.font_style_inherit = False
        self.style.font_style = "italic"
        self.style.font_weight_inherit = False
        self.style.font_weight = "bold"
        self.style.font_size_inherit = False
        self.style.font_size = "small"
        self.style.indent_level_inherit = False
        self.style.indent_level = 2
        style_props = self.style_obj.merge([self.style])
        xlsx = self.style_obj.to_xlsx_style(TYPE_NUM, style_props)
        self.assertEqual(
            xlsx,
            {
                "italic": True,
                "bold": True,
                "size": 9,
                "font_color": "#FF0000",
                "bg_color": "#0000FF",
                "num_format": '"p "#,##0.00" s"',
                "indent": 2,
            },
        )
        xlsx = self.style_obj.to_xlsx_style(TYPE_NUM, style_props, no_indent=True)
        self.assertEqual(
            xlsx,
            {
                "italic": True,
                "bold": True,
                "size": 9,
                "font_color": "#FF0000",
                "bg_color": "#0000FF",
                "num_format": '"p "#,##0.00" s"',
            },
        )
        # percent type ignore prefix and suffix
        xlsx = self.style_obj.to_xlsx_style(TYPE_PCT, style_props, no_indent=True)
        self.assertEqual(
            xlsx,
            {
                "italic": True,
                "bold": True,
                "size": 9,
                "font_color": "#FF0000",
                "bg_color": "#0000FF",
                "num_format": "0.00%",
            },
        )

        # str type have no num_format style
        xlsx = self.style_obj.to_xlsx_style(TYPE_STR, style_props, no_indent=True)
        self.assertEqual(
            xlsx,
            {
                "italic": True,
                "bold": True,
                "size": 9,
                "font_color": "#FF0000",
                "bg_color": "#0000FF",
            },
        )
