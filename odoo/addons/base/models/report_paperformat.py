# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

# see http://doc.qt.io/archives/qt-4.8/qprinter.html#PaperSize-enum
PAPER_SIZES = [
    {
        'description': 'A0  5   841 x 1189 mm',
        'key': 'A0',
        'height': 1189.0,
        'width': 841.0,
    }, {
        'key': 'A1',
        'description': 'A1  6   594 x 841 mm',
        'height': 841.0,
        'width': 594.0,
    }, {
        'key': 'A2',
        'description': 'A2  7   420 x 594 mm',
        'height': 594.0,
        'width': 420.0,
    }, {
        'key': 'A3',
        'description': 'A3  8   297 x 420 mm',
        'height': 420.0,
        'width': 297.0,
    }, {
        'key': 'A4',
        'description': 'A4  0   210 x 297 mm, 8.26 x 11.69 inches',
        'height': 297.0,
        'width': 210.0,
    }, {
        'key': 'A5',
        'description': 'A5  9   148 x 210 mm',
        'height': 210.0,
        'width': 148.0,
    }, {
        'key': 'A6',
        'description': 'A6  10  105 x 148 mm',
        'height': 148.0,
        'width': 105.0,
    }, {
        'key': 'A7',
        'description': 'A7  11  74 x 105 mm',
        'height': 105.0,
        'width': 74.0,
    }, {
        'key': 'A8',
        'description': 'A8  12  52 x 74 mm',
        'height': 74.0,
        'width': 52.0,
    }, {
        'key': 'A9',
        'description': 'A9  13  37 x 52 mm',
        'height': 52.0,
        'width': 37.0,
    }, {
        'key': 'B0',
        'description': 'B0  14  1000 x 1414 mm',
        'height': 1414.0,
        'width': 1000.0,
    }, {
        'key': 'B1',
        'description': 'B1  15  707 x 1000 mm',
        'height': 1000.0,
        'width': 707.0,
    }, {
        'key': 'B2',
        'description': 'B2  17  500 x 707 mm',
        'height': 707.0,
        'width': 500.0,
    }, {
        'key': 'B3',
        'description': 'B3  18  353 x 500 mm',
        'height': 500.0,
        'width': 353.0,
    }, {
        'key': 'B4',
        'description': 'B4  19  250 x 353 mm',
        'height': 353.0,
        'width': 250.0,
    }, {
        'key': 'B5',
        'description': 'B5  1   176 x 250 mm, 6.93 x 9.84 inches',
        'height': 250.0,
        'width': 176.0,
    }, {
        'key': 'B6',
        'description': 'B6  20  125 x 176 mm',
        'height': 176.0,
        'width': 125.0,
    }, {
        'key': 'B7',
        'description': 'B7  21  88 x 125 mm',
        'height': 125.0,
        'width': 88.0,
    }, {
        'key': 'B8',
        'description': 'B8  22  62 x 88 mm',
        'height': 88.0,
        'width': 62.0,
    }, {
        'key': 'B9',
        'description': 'B9  23  33 x 62 mm',
        'height': 62.0,
        'width': 33.0,
    }, {
        'key': 'B10',
        'description': 'B10    16  31 x 44 mm',
        'height': 44.0,
        'width': 31.0,
    }, {
        'key': 'C5E',
        'description': 'C5E 24  163 x 229 mm',
        'height': 229.0,
        'width': 163.0,
    }, {
        'key': 'Comm10E',
        'description': 'Comm10E 25  105 x 241 mm, U.S. Common 10 Envelope',
        'height': 241.0,
        'width': 105.0,
    }, {
        'key': 'DLE',
        'description': 'DLE 26 110 x 220 mm',
        'height': 220.0,
        'width': 110.0,
    }, {
        'key': 'Executive',
        'description': 'Executive 4   7.5 x 10 inches, 190.5 x 254 mm',
        'height': 254.0,
        'width': 190.5,
    }, {
        'key': 'Folio',
        'description': 'Folio 27  210 x 330 mm',
        'height': 330.0,
        'width': 210.0,
    }, {
        'key': 'Ledger',
        'description': 'Ledger  28  431.8 x 279.4 mm',
        'height': 279.4,
        'width': 431.8,
    }, {
        'key': 'Legal',
        'description': 'Legal    3   8.5 x 14 inches, 215.9 x 355.6 mm',
        'height': 355.6,
        'width': 215.9,
    }, {
        'key': 'Letter',
        'description': 'Letter 2 8.5 x 11 inches, 215.9 x 279.4 mm',
        'height': 279.4,
        'width': 215.9,
    }, {
        'key': 'Tabloid',
        'description': 'Tabloid 29 279.4 x 431.8 mm',
        'height': 431.8,
        'width': 279.4,
    }, {
        'key': 'custom',
        'description': 'Custom',
    },
]


class report_paperformat(models.Model):
    _name = "report.paperformat"
    _description = "Paper Format Config"

    name = fields.Char('Name', required=True)
    default = fields.Boolean('Default paper format?')
    format = fields.Selection([(ps['key'], ps['description']) for ps in PAPER_SIZES], 'Paper size', default='A4', help="Select Proper Paper size")
    margin_top = fields.Float('Top Margin (mm)', default=40)
    margin_bottom = fields.Float('Bottom Margin (mm)', default=20)
    margin_left = fields.Float('Left Margin (mm)', default=7)
    margin_right = fields.Float('Right Margin (mm)', default=7)
    page_height = fields.Integer('Page height (mm)', default=False)
    page_width = fields.Integer('Page width (mm)', default=False)
    orientation = fields.Selection([
        ('Landscape', 'Landscape'),
        ('Portrait', 'Portrait')
        ], 'Orientation', default='Landscape')
    header_line = fields.Boolean('Display a header line', default=False)
    header_spacing = fields.Integer('Header spacing', default=35)
    disable_shrinking = fields.Boolean('Disable smart shrinking')
    dpi = fields.Integer('Output DPI', required=True, default=90)
    report_ids = fields.One2many('ir.actions.report', 'paperformat_id', 'Associated reports', help="Explicitly associated reports")
    print_page_width = fields.Float('Print page width (mm)', compute='_compute_print_page_size')
    print_page_height = fields.Float('Print page height (mm)', compute='_compute_print_page_size')
    css_margins = fields.Boolean('Use css margins', default=False)

    @api.constrains('format')
    def _check_format_or_page(self):
        if self.filtered(lambda x: x.format != 'custom' and (x.page_width or x.page_height)):
            raise ValidationError(_('You can select either a format or a specific page width/height, but not both.'))

    def _compute_print_page_size(self):
        for record in self:
            width = height = 0.0
            if record.format:
                if record.format == 'custom':
                    width = record.page_width
                    height = record.page_height
                else:
                    paper_size = next(ps for ps in PAPER_SIZES if ps['key'] == record.format)
                    width = paper_size['width']
                    height = paper_size['height']

            if record.orientation == 'Landscape':
                # swap sizes
                width, height = height, width

            record.print_page_width = width
            record.print_page_height = height
