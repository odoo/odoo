from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

PAPER_SIZES = [
    {
        "description": "A0  5   841 x 1189 mm",
        "key": "A0",
        "height": 1189.0,
        "width": 841.0,
    },
    {
        "key": "A1",
        "description": "A1  6   594 x 841 mm",
        "height": 841.0,
        "width": 594.0,
    },
    {
        "key": "A2",
        "description": "A2  7   420 x 594 mm",
        "height": 594.0,
        "width": 420.0,
    },
    {
        "key": "A3",
        "description": "A3  8   297 x 420 mm",
        "height": 420.0,
        "width": 297.0,
    },
    {
        "key": "A4",
        "description": "A4  0   210 x 297 mm, 8.26 x 11.69 inches",
        "height": 297.0,
        "width": 210.0,
    },
    {
        "key": "A5",
        "description": "A5  9   148 x 210 mm",
        "height": 210.0,
        "width": 148.0,
    },
    {
        "key": "A6",
        "description": "A6  10  105 x 148 mm",
        "height": 148.0,
        "width": 105.0,
    },
    {
        "key": "A7",
        "description": "A7  11  74 x 105 mm",
        "height": 105.0,
        "width": 74.0,
    },
    {
        "key": "A8",
        "description": "A8  12  52 x 74 mm",
        "height": 74.0,
        "width": 52.0,
    },
    {
        "key": "A9",
        "description": "A9  13  37 x 52 mm",
        "height": 52.0,
        "width": 37.0,
    },
    {
        "key": "B0",
        "description": "B0  14  1000 x 1414 mm",
        "height": 1414.0,
        "width": 1000.0,
    },
    {
        "key": "B1",
        "description": "B1  15  707 x 1000 mm",
        "height": 1000.0,
        "width": 707.0,
    },
    {
        "key": "B2",
        "description": "B2  17  500 x 707 mm",
        "height": 707.0,
        "width": 500.0,
    },
    {
        "key": "B3",
        "description": "B3  18  353 x 500 mm",
        "height": 500.0,
        "width": 353.0,
    },
    {
        "key": "B4",
        "description": "B4  19  250 x 353 mm",
        "height": 353.0,
        "width": 250.0,
    },
    {
        "key": "B5",
        "description": "B5  1   176 x 250 mm, 6.93 x 9.84 inches",
        "height": 250.0,
        "width": 176.0,
    },
    {
        "key": "B6",
        "description": "B6  20  125 x 176 mm",
        "height": 176.0,
        "width": 125.0,
    },
    {
        "key": "B7",
        "description": "B7  21  88 x 125 mm",
        "height": 125.0,
        "width": 88.0,
    },
    {
        "key": "B8",
        "description": "B8  22  62 x 88 mm",
        "height": 88.0,
        "width": 62.0,
    },
    {
        "key": "B9",
        "description": "B9  23  44 x 62 mm",
        "height": 62.0,
        "width": 44.0,
    },
    {
        "key": "B10",
        "description": "B10    16  31 x 44 mm",
        "height": 44.0,
        "width": 31.0,
    },
    {
        "key": "C5E",
        "description": "C5E 24  163 x 229 mm",
        "height": 229.0,
        "width": 163.0,
    },
    {
        "key": "Comm10E",
        "description": "Comm10E 25  105 x 241 mm, U.S. Common 10 Envelope",
        "height": 241.0,
        "width": 105.0,
    },
    {
        "key": "DLE",
        "description": "DLE 26 110 x 220 mm",
        "height": 220.0,
        "width": 110.0,
    },
    {
        "key": "Executive",
        "description": "Executive 4   7.5 x 10 inches, 190.5 x 254 mm",
        "height": 254.0,
        "width": 190.5,
    },
    {
        "key": "Folio",
        "description": "Folio 27  210 x 330 mm",
        "height": 330.0,
        "width": 210.0,
    },
    {
        "key": "Ledger",
        "description": "Ledger  28  431.8 x 279.4 mm",
        "height": 279.4,
        "width": 431.8,
    },
    {
        "key": "Legal",
        "description": "Legal    3   8.5 x 14 inches, 215.9 x 355.6 mm",
        "height": 355.6,
        "width": 215.9,
    },
    {
        "key": "Letter",
        "description": "Letter 2 8.5 x 11 inches, 215.9 x 279.4 mm",
        "height": 279.4,
        "width": 215.9,
    },
    {
        "key": "Tabloid",
        "description": "Tabloid 29 279.4 x 431.8 mm",
        "height": 431.8,
        "width": 279.4,
    },
    {
        "key": "custom",
        "description": "Custom",
    },
]

PAPER_SIZE_BY_KEY = {ps["key"]: ps for ps in PAPER_SIZES}


class ReportPaperformat(models.Model):
    _name = "report.paperformat"
    _description = "Paper Format Config"

    name = fields.Char(required=True)
    format = fields.Selection(
        selection=[(ps["key"], ps["description"]) for ps in PAPER_SIZES],
        string="Paper size",
        default="A4",
        help="Select Proper Paper size",
    )
    margin_top = fields.Float(
        string="Top Margin (mm)",
        default=40,
    )
    margin_bottom = fields.Float(
        string="Bottom Margin (mm)",
        default=20,
    )
    margin_left = fields.Float(
        string="Left Margin (mm)",
        default=7,
    )
    margin_right = fields.Float(
        string="Right Margin (mm)",
        default=7,
    )
    page_height = fields.Integer(
        string="Page height (mm)",
        default=False,
    )
    page_width = fields.Integer(
        string="Page width (mm)",
        default=False,
    )
    orientation = fields.Selection(
        selection=[("Landscape", "Landscape"), ("Portrait", "Portrait")],
        default="Landscape",
    )
    header_line = fields.Boolean(
        string="Display a header line",
        default=False,
    )
    header_spacing = fields.Integer(
        string="Header spacing (mm)",
        default=35,
        help="Height in mm of the header area. Used by report templates (e.g. DIN 5008) "
        "as a layout variable. Has no effect on standard Odoo reports.",
    )
    disable_shrinking = fields.Boolean(
        string="Disable auto-shrinking",
        help="When enabled, the Web Studio report preview skips viewport-shrink "
        "correction. Has no effect on WeasyPrint PDF generation.",
    )
    dpi = fields.Integer(
        string="Preview DPI",
        default=90,
        required=True,
        help="DPI used to scale the HTML preview in Web Studio (96 / dpi = zoom factor). "
        "Does not affect WeasyPrint PDF output, which is resolution-independent.",
    )
    report_ids = fields.One2many(
        comodel_name="ir.actions.report",
        inverse_name="paperformat_id",
        string="Associated reports",
        help="Explicitly associated reports",
    )
    print_page_width = fields.Float(
        string="Print page width (mm)",
        compute="_compute_print_page_size",
    )
    print_page_height = fields.Float(
        string="Print page height (mm)",
        compute="_compute_print_page_size",
    )
    css_margins = fields.Boolean(
        string="Use body padding margins",
        default=False,
        help="When enabled, horizontal spacing is applied as CSS body padding (8 mm) "
        "rather than @page margin rules. Header/footer running elements add matching "
        "padding to stay aligned with the body content. Typically used together with "
        "margin_left=0 and margin_right=0.",
    )

    @api.constrains("format", "page_width", "page_height")
    def _check_format_or_page(self) -> None:
        _debug.perf.count("format_or_page_checked", paperformats=len(self))
        if conflicting := self.filtered(
            lambda x: x.format != "custom" and (x.page_width or x.page_height)
        ):
            _debug.logic(
                "format_rejected",
                paperformats=conflicting.ids,
                reason="format_and_page",
            )
            raise ValidationError(
                self.env._(
                    "You can select either a format or a specific page width/height, but not both."
                )
            )

    @api.depends("format", "orientation", "page_width", "page_height")
    def _compute_print_page_size(self) -> None:
        _debug.perf.count("print_page_size_computed", paperformats=len(self))
        for record in self:
            width = height = 0.0
            if _debug.logic.enabled and not record.format:
                _debug.logic("page_size_missing_format", paperformat=record.id)
            if record.format:
                if record.format == "custom":
                    width = record.page_width
                    height = record.page_height
                    _debug.logic(
                        "page_size_custom",
                        paperformat=record.id,
                        width=width,
                        height=height,
                    )
                else:
                    paper_size = PAPER_SIZE_BY_KEY.get(record.format)
                    if paper_size is None:
                        _debug.logic(
                            "page_size_unknown",
                            paperformat=record.id,
                            format=record.format,
                        )
                        record.print_page_width = 0.0
                        record.print_page_height = 0.0
                        continue
                    width = paper_size["width"]
                    height = paper_size["height"]

            if record.orientation == "Landscape":
                width, height = height, width

            _debug.logic(
                "page_size_resolved",
                paperformat=record.id,
                format=record.format,
                orientation=record.orientation,
                width=width,
                height=height,
            )
            record.print_page_width = width
            record.print_page_height = height
