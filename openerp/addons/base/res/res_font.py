# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from reportlab import rl_config
from reportlab.pdfbase import pdfmetrics, ttfonts
from openerp.osv import fields, osv

import logging
import os,platform

"""This module allows the mapping of some system-available TTF fonts to
the reportlab engine.

This file could be customized per distro (although most Linux/Unix ones)
should have the same filenames, only need the code below).

Due to an awful configuration that ships with reportlab at many Linux
and Ubuntu distros, we have to override the search path, too.
"""
_fonts_cache = {'registered_fonts': [], 'total_system_fonts': 0}
_logger = logging.getLogger(__name__)

# Basic fonts family included in PDF standart, will always be in the font list
BasePDFFonts = [
    'Helvetica',
    'Times',
    'Courier'
]

# List of fonts found on the disk
CustomTTFonts = BaseCustomTTFonts = [ ('Helvetica', "DejaVu Sans", "DejaVuSans.ttf", 'normal'),
        ('Helvetica', "DejaVu Sans Bold", "DejaVuSans-Bold.ttf", 'bold'),
        ('Helvetica', "DejaVu Sans Oblique", "DejaVuSans-Oblique.ttf", 'italic'),
        ('Helvetica', "DejaVu Sans BoldOblique", "DejaVuSans-BoldOblique.ttf", 'bolditalic'),
        ('Times', "Liberation Serif", "LiberationSerif-Regular.ttf", 'normal'),
        ('Times', "Liberation Serif Bold", "LiberationSerif-Bold.ttf", 'bold'),
        ('Times', "Liberation Serif Italic", "LiberationSerif-Italic.ttf", 'italic'),
        ('Times', "Liberation Serif BoldItalic", "LiberationSerif-BoldItalic.ttf", 'bolditalic'),
        ('Courier', "FreeMono", "FreeMono.ttf", 'normal'),
        ('Courier', "FreeMono Bold", "FreeMonoBold.ttf", 'bold'),
        ('Courier', "FreeMono Oblique", "FreeMonoOblique.ttf", 'italic'),
        ('Courier', "FreeMono BoldOblique", "FreeMonoBoldOblique.ttf", 'bolditalic'),
]


# Search path for TTF files, in addition of rl_config.TTFSearchPath
TTFSearchPath = [
            '~/test',
            '/usr/share/fonts/truetype', # SuSE
            '/usr/share/fonts/dejavu', '/usr/share/fonts/liberation', # Fedora, RHEL
            '/usr/share/fonts/truetype/*','/usr/local/share/fonts' # Ubuntu,
            '/usr/share/fonts/TTF/*', # at Mandriva/Mageia
            '/usr/share/fonts/TTF', # Arch Linux
            '/usr/lib/openoffice/share/fonts/truetype/',
            '~/.fonts',
            '~/.local/share/fonts',

            # mac os X - from
            # http://developer.apple.com/technotes/tn/tn2024.html
            '~/Library/Fonts',
            '/Library/Fonts',
            '/Network/Library/Fonts',
            '/System/Library/Fonts',

            # windows
            'c:/winnt/fonts',
            'c:/windows/fonts'
]

def list_all_sysfonts():
    """
        This function returns list of font directories of system.
    """
    filepath = []

    # Perform the search for font files ourselves, as reportlab's
    # TTFOpenFile is not very good at it.
    searchpath = list(set(TTFSearchPath + rl_config.TTFSearchPath))
    for dirname in searchpath:
        dirname = os.path.expanduser(dirname)
        if os.path.exists(dirname):
            for filename in [x for x in os.listdir(dirname) if x.lower().endswith('.ttf')]:
                filepath.append(os.path.join(dirname, filename))
    return filepath


class res_font(osv.Model):
    _name = "res.font"
    _description = 'Fonts available'
    _order = 'name'

    _columns = {
        'name': fields.char("Name", required=True),
    }

    _sql_constraints = [
        ('name_font_uniq', 'unique(name)', 'You can not register to fonts with the same name'),
    ]

    def act_discover_fonts(self, cr, uid, ids, context=None):
        CustomTTFonts = BaseCustomTTFonts

        found_fonts = {}
        for font_path in list_all_sysfonts():
            try:
                font = ttfonts.TTFontFile(font_path)
                _logger.debug("Found font %s at %s", font.name, font_path)
                if not found_fonts.get(font.familyName):
                    found_fonts[font.familyName] = {'name': font.familyName}

                mode = font.styleName.lower().replace(" ", "")

                CustomTTFonts.append((font.familyName, font.name, font_path, mode))
            except ttfonts.TTFError:
                _logger.warning("Could not register Font %s", font_path)

        # add default PDF fonts
        for family in BasePDFFonts:
            if not found_fonts.get(family):
                found_fonts[family] = {'name': family}


        # to make sure we always have updated list, delete all and recreate
        self.unlink(cr, uid, self.search(cr, uid, [], context=context), context=context)
        for family, vals in found_fonts.items():
            self.create(cr, uid, vals, context=context)

