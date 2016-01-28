# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# Author : Nicolas Bessi (Camptocamp)

from openerp.osv import fields, osv

class HeaderHTML(osv.osv):
    """HTML Header allows you to define HTML CSS and Page format"""

    _name = "ir.header_webkit"
    _columns = {
        'company_id' : fields.many2one('res.company', 'Company'),
        'html' : fields.text('webkit header', help="Set Webkit Report Header"),
        'footer_html' : fields.text('webkit footer', help="Set Webkit Report Footer."),
        'css' : fields.text('Header CSS'),
        'name' : fields.char('Name', required=True),
        'margin_top' : fields.float('Top Margin (mm)'),
        'margin_bottom' : fields.float('Bottom Margin (mm)'),
        'margin_left' : fields.float('Left Margin (mm)'),
        'margin_right' : fields.float('Right Margin (mm)'),
        'orientation' : fields.selection(
                        [('Landscape','Landscape'),('Portrait', 'Portrait')],
                        'Orientation',
                        ),
        'format': fields.selection(
                [
                ('A0' ,'A0  5   841 x 1189 mm'),
                ('A1' ,'A1  6   594 x 841 mm'),
                ('A2' ,'A2  7   420 x 594 mm'),
                ('A3' ,'A3  8   297 x 420 mm'),
                ('A4' ,'A4  0   210 x 297 mm, 8.26 x 11.69 inches'),
                ('A5' ,'A5  9   148 x 210 mm'),
                ('A6' ,'A6  10  105 x 148 mm'),
                ('A7' ,'A7  11  74 x 105 mm'),
                ('A8' ,'A8  12  52 x 74 mm'),
                ('A9' ,'A9  13  37 x 52 mm'),
                ('B0' ,'B0  14  1000 x 1414 mm'),
                ('B1' ,'B1  15  707 x 1000 mm'),
                ('B2' ,'B2  17  500 x 707 mm'),
                ('B3' ,'B3  18  353 x 500 mm'),
                ('B4' ,'B4  19  250 x 353 mm'),
                ('B5' ,'B5  1   176 x 250 mm, 6.93 x 9.84 inches'),
                ('B6' ,'B6  20  125 x 176 mm'),
                ('B7' ,'B7  21  88 x 125 mm'),
                ('B8' ,'B8  22  62 x 88 mm'),
                ('B9' ,'B9  23  33 x 62 mm'),
                ('B10',':B10    16  31 x 44 mm'),
                ('C5E','C5E 24  163 x 229 mm'),
                ('Comm10E','Comm10E 25  105 x 241 mm, U.S. Common 10 Envelope'),
                ('DLE', 'DLE 26 110 x 220 mm'),
                ('Executive','Executive 4   7.5 x 10 inches, 190.5 x 254 mm'),
                ('Folio','Folio 27  210 x 330 mm'),
                ('Ledger', 'Ledger  28  431.8 x 279.4 mm'),
                ('Legal', 'Legal    3   8.5 x 14 inches, 215.9 x 355.6 mm'),
                ('Letter','Letter 2 8.5 x 11 inches, 215.9 x 279.4 mm'),
                ('Tabloid', 'Tabloid 29 279.4 x 431.8 mm'),
                ],
                'Paper size',
                required=True,
                help="Select Proper Paper size"
        )
    }

class HeaderImage(osv.osv):
    """Logo allows you to define multiple logo per company"""
    _name = "ir.header_img"
    _columns = {
        'company_id' : fields.many2one('res.company', 'Company'),
        'img' : fields.binary('Image', attachment=True),
        'name' : fields.char('Name', required =True, help="Name of Image"),
        'type' : fields.char('Type', required =True, help="Image type(png,gif,jpeg)")
    }
