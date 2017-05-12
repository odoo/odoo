# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class report_paperformat(models.Model):
    _name = "report.paperformat"
    _description = "Allows customization of a report."

    name = fields.Char('Name', required=True)
    default = fields.Boolean('Default paper format ?')
    format = fields.Selection([
        ('A0', 'A0  5   841 x 1189 mm'),
        ('A1', 'A1  6   594 x 841 mm'),
        ('A2', 'A2  7   420 x 594 mm'),
        ('A3', 'A3  8   297 x 420 mm'),
        ('A4', 'A4  0   210 x 297 mm, 8.26 x 11.69 inches'),
        ('A5', 'A5  9   148 x 210 mm'),
        ('A6', 'A6  10  105 x 148 mm'),
        ('A7', 'A7  11  74 x 105 mm'),
        ('A8', 'A8  12  52 x 74 mm'),
        ('A9', 'A9  13  37 x 52 mm'),
        ('B0', 'B0  14  1000 x 1414 mm'),
        ('B1', 'B1  15  707 x 1000 mm'),
        ('B2', 'B2  17  500 x 707 mm'),
        ('B3', 'B3  18  353 x 500 mm'),
        ('B4', 'B4  19  250 x 353 mm'),
        ('B5', 'B5  1   176 x 250 mm, 6.93 x 9.84 inches'),
        ('B6', 'B6  20  125 x 176 mm'),
        ('B7', 'B7  21  88 x 125 mm'),
        ('B8', 'B8  22  62 x 88 mm'),
        ('B9', 'B9  23  33 x 62 mm'),
        ('B10', ':B10    16  31 x 44 mm'),
        ('C5E', 'C5E 24  163 x 229 mm'),
        ('Comm10E', 'Comm10E 25  105 x 241 mm, U.S. '
         'Common 10 Envelope'),
        ('DLE', 'DLE 26 110 x 220 mm'),
        ('Executive', 'Executive 4   7.5 x 10 inches, '
         '190.5 x 254 mm'),
        ('Folio', 'Folio 27  210 x 330 mm'),
        ('Ledger', 'Ledger  28  431.8 x 279.4 mm'),
        ('Legal', 'Legal    3   8.5 x 14 inches, '
         '215.9 x 355.6 mm'),
        ('Letter', 'Letter 2 8.5 x 11 inches, '
         '215.9 x 279.4 mm'),
        ('Tabloid', 'Tabloid 29 279.4 x 431.8 mm'),
        ('custom', 'Custom')
        ], 'Paper size', default='A4', help="Select Proper Paper size")
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
    dpi = fields.Integer('Output DPI', required=True, default=90)
    report_ids = fields.One2many('ir.actions.report.xml', 'paperformat_id', 'Associated reports', help="Explicitly associated reports")

    @api.constrains('format')
    def _check_format_or_page(self):
        if self.filtered(lambda x: x.format != 'custom' and (x.page_width or x.page_height)):
            raise ValidationError(_('Error ! You cannot select a format AND specific page width/height.'))
