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
_fonts_cache = {'registered_fonts':[], 'total_system_fonts': 0}
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

__foundFonts = None

def linux_home_fonts():
    """
    This function appends local font directory in TTFSearchPath_Linux.
    """
    home = os.environ.get('HOME')
    if home is not None:
        # user fonts on OSX
        path = os.path.join(home, 'Library', 'Fonts')
        path = os.path.join(home, '.fonts')
        TTFSearchPath_Linux.append(path)

def all_sysfonts_list():
    """
        This function returns list of font directories of system.
    """
    searchpath = []
    filepath = []
    global __foundFonts
    __foundFonts = {}
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
                __foundFonts[filename]=os.path.join(dirname, filename)
    return filepath
    
def RegisterCustomFonts():
    """
    This function prepares a list for all system fonts to be registered
    in reportlab and returns the updated list with new fonts.
    """
    all_system_fonts = sorted(all_sysfonts_list())
    if len(all_system_fonts) > _fonts_cache['total_system_fonts']:
        all_mode = {}
        last_family = ""
        for i,dirname in enumerate(all_system_fonts):
            try:
                font_info = ttfonts.TTFontFile(dirname)
                if not last_family:
                    last_family = font_info.familyName
                if not all_mode:
                    all_mode = {
                        'regular':(font_info.familyName, font_info.name, dirname.split('/')[-1], 'regular'),
                        'italic':(),
                        'bold':(font_info.familyName, font_info.name, dirname.split('/')[-1], 'bold'),
                        'bolditalic':(),
                    }
                if (last_family != font_info.familyName) or ((i+1) == len(all_system_fonts)):
                    if not all_mode['italic']:
                        all_mode['italic'] = (all_mode['regular'][0],all_mode['regular'][1],all_mode['regular'][2],'italic')
                    if not all_mode['bolditalic']:
                        all_mode['bolditalic'] = (all_mode['bold'][0],all_mode['bold'][1],all_mode['bold'][2],'bolditalic')
                    CustomTTFonts.extend(all_mode.values())
                    all_mode = {
                        'regular':(font_info.familyName, font_info.name, dirname.split('/')[-1], 'regular'),
                        'italic':(),
                        'bold':(font_info.familyName, font_info.name, dirname.split('/')[-1], 'bold'),
                        'bolditalic':(),
                        }
                mode = font_info.styleName.lower().replace(" ", "") 
                if (mode== 'normal') or (mode == 'regular') or (mode == 'medium') or (mode == 'book'):
                    all_mode['regular'] = (font_info.familyName, font_info.name, dirname.split('/')[-1], 'regular')
                elif (mode == 'italic') or (mode == 'oblique'):
                    all_mode['italic'] = (font_info.familyName, font_info.name, dirname.split('/')[-1], 'italic')
                elif mode == 'bold':
                    all_mode['bold'] = (font_info.familyName, font_info.name, dirname.split('/')[-1], 'bold')
                elif (mode == 'bolditalic') or (mode == 'boldoblique'):
                    all_mode['bolditalic'] = (font_info.familyName, font_info.name, dirname.split('/')[-1], 'bolditalic')
                last_family = font_info.familyName
                _fonts_cache['registered_fonts'].append((font_info.name, font_info.name))
                _logger.debug("Found font %s at %s", font_info.name, dirname)
            except:
                _logger.warning("Could not register Font %s", dirname)
        _fonts_cache['total_system_fonts'] = len(all_system_fonts)
        _fonts_cache['registered_fonts'] = list(set(_fonts_cache['registered_fonts']))
    return _fonts_cache['registered_fonts']
    
def SetCustomFonts(rmldoc):
    """ Map some font names to the corresponding TTF fonts

        The ttf font may not even have the same name, as in
        Times -> Liberation Serif.
        This function is called once per report, so it should
        avoid system-wide processing (cache it, instead).
    """
    if not _fonts_cache['registered_fonts']:
        RegisterCustomFonts()
    for name, font, filename, mode in CustomTTFonts:
        if os.path.isabs(filename) and os.path.exists(filename):
            rmldoc.setTTFontMapping(name, font, filename, mode)
        elif filename in __foundFonts:
            rmldoc.setTTFontMapping(name, font, __foundFonts[filename], mode)     
    return True
# eof

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
