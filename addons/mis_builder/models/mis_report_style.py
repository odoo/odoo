# Copyright 2016 Therp BV (<http://therp.nl>)
# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import sys

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .accounting_none import AccountingNone
from .data_error import DataError

if sys.version_info.major >= 3:
    unicode = str


class PropertyDict(dict):
    def __getattr__(self, name):
        return self.get(name)

    def copy(self):  # pylint: disable=copy-wo-api-one,method-required-super
        return PropertyDict(self)


PROPS = [
    "color",
    "background_color",
    "font_style",
    "font_weight",
    "font_size",
    "indent_level",
    "prefix",
    "suffix",
    "dp",
    "divider",
    "hide_empty",
    "hide_always",
]

TYPE_NUM = "num"
TYPE_PCT = "pct"
TYPE_STR = "str"

CMP_DIFF = "diff"
CMP_PCT = "pct"
CMP_NONE = "none"


class MisReportKpiStyle(models.Model):
    _name = "mis.report.style"
    _description = "MIS Report Style"

    @api.constrains("indent_level")
    def check_positive_val(self):
        for record in self:
            if record.indent_level < 0:
                raise ValidationError(
                    _("Indent level must be greater than " "or equal to 0")
                )

    _font_style_selection = [("normal", "Normal"), ("italic", "Italic")]

    _font_weight_selection = [("nornal", "Normal"), ("bold", "Bold")]

    _font_size_selection = [
        ("medium", "medium"),
        ("xx-small", "xx-small"),
        ("x-small", "x-small"),
        ("small", "small"),
        ("large", "large"),
        ("x-large", "x-large"),
        ("xx-large", "xx-large"),
    ]

    _font_size_to_xlsx_size = {
        "medium": 11,
        "xx-small": 5,
        "x-small": 7,
        "small": 9,
        "large": 13,
        "x-large": 15,
        "xx-large": 17,
    }

    # style name
    # TODO enforce uniqueness
    name = fields.Char(string="Style name", required=True)

    # color
    color_inherit = fields.Boolean(default=True)
    color = fields.Char(
        string="Text color",
        help="Text color in valid RGB code (from #000000 to #FFFFFF)",
        default="#000000",
    )
    background_color_inherit = fields.Boolean(default=True)
    background_color = fields.Char(
        help="Background color in valid RGB code (from #000000 to #FFFFFF)",
        default="#FFFFFF",
    )
    # font
    font_style_inherit = fields.Boolean(default=True)
    font_style = fields.Selection(selection=_font_style_selection)
    font_weight_inherit = fields.Boolean(default=True)
    font_weight = fields.Selection(selection=_font_weight_selection)
    font_size_inherit = fields.Boolean(default=True)
    font_size = fields.Selection(selection=_font_size_selection)
    # indent
    indent_level_inherit = fields.Boolean(default=True)
    indent_level = fields.Integer()
    # number format
    prefix_inherit = fields.Boolean(default=True)
    prefix = fields.Char()
    suffix_inherit = fields.Boolean(default=True)
    suffix = fields.Char()
    dp_inherit = fields.Boolean(default=True)
    dp = fields.Integer(string="Rounding", default=0)
    divider_inherit = fields.Boolean(default=True)
    divider = fields.Selection(
        [
            ("1e-6", _("µ")),
            ("1e-3", _("m")),
            ("1", _("1")),
            ("1e3", _("k")),
            ("1e6", _("M")),
        ],
        string="Factor",
        default="1",
    )
    hide_empty_inherit = fields.Boolean(default=True)
    hide_empty = fields.Boolean(default=False)
    hide_always_inherit = fields.Boolean(default=True)
    hide_always = fields.Boolean(default=False)

    @api.model
    def merge(self, styles):
        """Merge several styles, giving priority to the last.

        Returns a PropertyDict of style properties.
        """
        r = PropertyDict()
        for style in styles:
            if not style:
                continue
            if isinstance(style, dict):
                r.update(style)
            else:
                for prop in PROPS:
                    inherit = getattr(style, prop + "_inherit", None)
                    if not inherit:
                        value = getattr(style, prop)
                        r[prop] = value
        return r

    @api.model
    def render(self, lang, style_props, var_type, value, sign="-"):
        if var_type == TYPE_NUM:
            return self.render_num(
                lang,
                value,
                style_props.divider,
                style_props.dp,
                style_props.prefix,
                style_props.suffix,
                sign=sign,
            )
        elif var_type == TYPE_PCT:
            return self.render_pct(lang, value, style_props.dp, sign=sign)
        else:
            return self.render_str(lang, value)

    @api.model
    def render_num(
        self, lang, value, divider=1.0, dp=0, prefix=None, suffix=None, sign="-"
    ):
        # format number following user language
        if value is None or value is AccountingNone:
            return ""
        value = round(value / float(divider or 1), dp or 0) or 0
        r = lang.format("%%%s.%df" % (sign, dp or 0), value, grouping=True)
        r = r.replace("-", "\N{NON-BREAKING HYPHEN}")
        if prefix:
            r = prefix + "\N{NO-BREAK SPACE}" + r
        if suffix:
            r = r + "\N{NO-BREAK SPACE}" + suffix
        return r

    @api.model
    def render_pct(self, lang, value, dp=1, sign="-"):
        return self.render_num(lang, value, divider=0.01, dp=dp, suffix="%", sign=sign)

    @api.model
    def render_str(self, lang, value):
        if value is None or value is AccountingNone:
            return ""
        return unicode(value)

    @api.model
    def compare_and_render(
        self,
        lang,
        style_props,
        var_type,
        compare_method,
        value,
        base_value,
        average_value=1,
        average_base_value=1,
    ):
        """
        :param lang: res.lang record
        :param style_props: PropertyDict with style properties
        :param var_type: num, pct or str
        :param compare_method: diff, pct, none
        :param value: value to compare (value - base_value)
        :param base_value: value compared with (value - base_value)
        :param average_value: value = value / average_value
        :param average_base_value: base_value = base_value / average_base_value
        :return: tuple with 4 elements
            - delta = comparison result (Float or AccountingNone)
            - delta_r = delta rendered in formatted string (String)
            - delta_style = PropertyDict with style properties
            - delta_type = Type of the comparison result (num or pct)
        """
        delta = AccountingNone
        delta_r = ""
        delta_style = style_props.copy()
        delta_type = TYPE_NUM
        if isinstance(value, DataError) or isinstance(base_value, DataError):
            return AccountingNone, "", delta_style, delta_type
        if value is None:
            value = AccountingNone
        if base_value is None:
            base_value = AccountingNone
        if var_type == TYPE_PCT:
            delta = value - base_value
            if delta and round(delta, (style_props.dp or 0) + 2) != 0:
                delta_style.update(divider=0.01, prefix="", suffix=_("pp"))
            else:
                delta = AccountingNone
        elif var_type == TYPE_NUM:
            if value and average_value:
                # pylint: disable=redefined-variable-type
                value = value / float(average_value)
            if base_value and average_base_value:
                # pylint: disable=redefined-variable-type
                base_value = base_value / float(average_base_value)
            if compare_method == CMP_DIFF:
                delta = value - base_value
                if delta and round(delta, style_props.dp or 0) != 0:
                    pass
                else:
                    delta = AccountingNone
            elif compare_method == CMP_PCT:
                if base_value and round(base_value, style_props.dp or 0) != 0:
                    delta = (value - base_value) / abs(base_value)
                    if delta and round(delta, 3) != 0:
                        delta_style.update(dp=1)
                        delta_type = TYPE_PCT
                    else:
                        delta = AccountingNone
        if delta is not AccountingNone:
            delta_r = self.render(lang, delta_style, delta_type, delta, sign="+")
        return delta, delta_r, delta_style, delta_type

    @api.model
    def to_xlsx_style(self, var_type, props, no_indent=False):
        xlsx_attributes = [
            ("italic", props.font_style == "italic"),
            ("bold", props.font_weight == "bold"),
            ("size", self._font_size_to_xlsx_size.get(props.font_size, 11)),
            ("font_color", props.color),
            ("bg_color", props.background_color),
        ]
        if var_type == TYPE_NUM:
            num_format = "#,##0"
            if props.dp:
                num_format += "."
                num_format += "0" * props.dp
            if props.prefix:
                num_format = f'"{props.prefix} "{num_format}'
            if props.suffix:
                num_format = f'{num_format}" {props.suffix}"'
            xlsx_attributes.append(("num_format", num_format))
        elif var_type == TYPE_PCT:
            num_format = "0"
            if props.dp:
                num_format += "."
                num_format += "0" * props.dp
            num_format += "%"
            xlsx_attributes.append(("num_format", num_format))
        if props.indent_level is not None and not no_indent:
            xlsx_attributes.append(("indent", props.indent_level))
        return dict([a for a in xlsx_attributes if a[1] is not None])

    @api.model
    def to_css_style(self, props, no_indent=False):
        css_attributes = [
            ("font-style", props.font_style),
            ("font-weight", props.font_weight),
            ("font-size", props.font_size),
            ("color", props.color),
            ("background-color", props.background_color),
        ]
        if props.indent_level is not None and not no_indent:
            css_attributes.append(("text-indent", f"{props.indent_level}em"))
        return (
            "; ".join(["{}: {}".format(*a) for a in css_attributes if a[1] is not None])
            or None
        )
