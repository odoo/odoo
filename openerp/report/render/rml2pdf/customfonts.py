# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 P. Christeas, Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2013 OpenERP SA. (http://www.openerp.com)
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
import logging
import os,platform

# .apidoc title: TTF Font Table

"""This module allows the mapping of some system-available TTF fonts to
the reportlab engine.

This file could be customized per distro (although most Linux/Unix ones)
should have the same filenames, only need the code below).

Due to an awful configuration that ships with reportlab at many Linux
and Ubuntu distros, we have to override the search path, too.
"""
_fonts_info = {'supported_fonts':[], 'font_len': 0}
_logger = logging.getLogger(__name__)

CustomTTFonts = [ ('Helvetica', "DejaVu Sans", "DejaVuSans.ttf", 'normal'),
        ('Helvetica', "DejaVu Sans Bold", "DejaVuSans-Bold.ttf", 'bold'),
        ('Helvetica', "DejaVu Sans Oblique", "DejaVuSans-Oblique.ttf", 'italic'),
        ('Helvetica', "DejaVu Sans BoldOblique", "DejaVuSans-BoldOblique.ttf", 'bolditalic'),
        ('Times', "Liberation Serif", "LiberationSerif-Regular.ttf", 'normal'),
        ('Times', "Liberation Serif Bold", "LiberationSerif-Bold.ttf", 'bold'),
        ('Times', "Liberation Serif Italic", "LiberationSerif-Italic.ttf", 'italic'),
        ('Times', "Liberation Serif BoldItalic", "LiberationSerif-BoldItalic.ttf", 'bolditalic'),
        ('Times-Roman', "Liberation Serif", "LiberationSerif-Regular.ttf", 'normal'),
        ('Times-Roman', "Liberation Serif Bold", "LiberationSerif-Bold.ttf", 'bold'),
        ('Times-Roman', "Liberation Serif Italic", "LiberationSerif-Italic.ttf", 'italic'),
        ('Times-Roman', "Liberation Serif BoldItalic", "LiberationSerif-BoldItalic.ttf", 'bolditalic'),
        ('Courier', "FreeMono", "FreeMono.ttf", 'normal'),
        ('Courier', "FreeMono Bold", "FreeMonoBold.ttf", 'bold'),
        ('Courier', "FreeMono Oblique", "FreeMonoOblique.ttf", 'italic'),
        ('Courier', "FreeMono BoldOblique", "FreeMonoBoldOblique.ttf", 'bolditalic'),

        # Sun-ExtA can be downloaded from http://okuc.net/SunWb/
        ('Sun-ExtA', "Sun-ExtA", "Sun-ExtA.ttf", 'normal'),
]

TTFSearchPath_Linux = [
            '/usr/share/fonts/truetype', # SuSE
            '/usr/share/fonts/dejavu', '/usr/share/fonts/liberation', # Fedora, RHEL
            '/usr/share/fonts/truetype/*','/usr/local/share/fonts' # Ubuntu,
            '/usr/share/fonts/TTF/*', # at Mandriva/Mageia
            '/usr/share/fonts/TTF', # Arch Linux
            '/usr/lib/openoffice/share/fonts/truetype/',
            ]

TTFSearchPath_Windows = [
            'c:/winnt/fonts',
            'c:/windows/fonts'
            ]

TTFSearchPath_Darwin = [
            #mac os X - from
            #http://developer.apple.com/technotes/tn/tn2024.html
            '~/Library/Fonts',
            '/Library/Fonts',
            '/Network/Library/Fonts',
            '/System/Library/Fonts',
            ]

TTFSearchPathMap = {
    'Darwin': TTFSearchPath_Darwin,
    'Windows': TTFSearchPath_Windows,
    'Linux': TTFSearchPath_Linux,
}

def linux_home_fonts():
    home = os.environ.get('HOME')
    if home is not None:
        # user fonts on OSX
        path = os.path.join(home, 'Library', 'Fonts')
        path = os.path.join(home, '.fonts')
        TTFSearchPath_Linux.append(path)

def all_sysfonts_list():
    searchpath = []
    filepath = []
    local_platform = platform.system()
    if local_platform in TTFSearchPathMap:
        if local_platform == 'Linux':
            linux_home_fonts()
        searchpath += TTFSearchPathMap[local_platform]
    # Append the original search path of reportlab (at the end)
    searchpath += rl_config.TTFSearchPath 
    searchpath = list(set(searchpath))
    for dirname in searchpath:
        if os.path.exists(dirname):
            for filename in [x for x in os.listdir(dirname) if x.lower().endswith('.ttf')]:
                filepath.append(os.path.join(dirname, filename))
    return filepath
    
def RegisterCustomFonts():
    global _fonts_info
    all_system_fonts = all_sysfonts_list()
    if len(all_system_fonts) > _fonts_info['font_len']:
        for dirname in all_system_fonts:
            try:
                face = ttfonts.TTFontFace(dirname)
                if (face.name, face.name) not in _fonts_info['supported_fonts']:
                    font_info = ttfonts.TTFontFile(dirname)
                    pdfmetrics.registerFont(ttfonts.TTFont(face.name, dirname, asciiReadable=0))
                    _fonts_info['supported_fonts'].append((face.name, face.name))
                    CustomTTFonts.append((font_info.familyName, font_info.name, dirname.split('/')[-1], font_info.styleName.lower().replace(" ", "")))
                _logger.debug("Found font %s at %s", face.name, dirname)
            except:
                _logger.warning("Could not register Font %s", dirname)
        _fonts_info['font_len'] = len(all_system_fonts)
    return _fonts_info['supported_fonts']
    
def SetCustomFonts(rmldoc):
    """ Map some font names to the corresponding TTF fonts

        The ttf font may not even have the same name, as in
        Times -> Liberation Serif.
        This function is called once per report, so it should
        avoid system-wide processing (cache it, instead).
    """
    global _fonts_info
    if not _fonts_info['supported_fonts']:
        RegisterCustomFonts()
    for name, font, filename, mode in CustomTTFonts:
        if os.path.isabs(filename) and os.path.exists(filename):
            rmldoc.setTTFontMapping(name, font, filename, mode)
    return True
# eof

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
