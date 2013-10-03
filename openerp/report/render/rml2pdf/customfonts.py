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
_fonts_cache = {'registered_fonts': [], 'total_system_fonts': 0}
_logger = logging.getLogger(__name__)

CustomTTFonts = []

TTFSearchPath = [
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

def all_sysfonts_list():
    """
        This function returns list of font directories of system.
    """
    searchpath = []
    filepath = []

    # Append the original search path of reportlab
    searchpath = list(set(TTFSearchPath + rl_config.TTFSearchPath))
    for dirname in searchpath:
        dirname = os.path.expanduser(dirname)
        if os.path.exists(dirname):
            for filename in [x for x in os.listdir(dirname) if x.lower().endswith('.ttf')]:
                filepath.append(os.path.join(dirname, filename))
    return sorted(filepath)

def init_new_font(familyName, name, font_dir):
    return {
        'regular':(familyName, name, font_dir, 'regular'),
        'italic':(),
        'bold':(familyName, name, font_dir, 'bold'),
        'bolditalic':(),
    }
    
def RegisterCustomFonts():
    """
    This function prepares a list for all system fonts to be registered
    in reportlab and returns the updated list with new fonts.
    """
    all_system_fonts = all_sysfonts_list()
    if len(all_system_fonts) > _fonts_cache['total_system_fonts']:
        global TTFSearchPath
        font_modes, last_family, registered_font_list, _fonts_cache['registered_fonts'], TTFSearchPath = {}, "", [], [], []

        #Prepares a list of registered fonts. Remove such fonts those don't have cmap for Unicode.
        for dirname in all_system_fonts:
            try:
                font_info = ttfonts.TTFontFile(dirname)
                if font_info.styleName in ('Regular','Normal','Book','Medium'):
                    _fonts_cache['registered_fonts'].append((font_info.name, font_info.name))
                registered_font_list.append((font_info.familyName, font_info.name, dirname, font_info.styleName.lower().replace(" ", "")))
                _logger.debug("Found font %s at %s", font_info.name, dirname)
            except:
                _logger.warning("Could not register Font %s", dirname)
        
        #Prepare font list for mapping.Each font family requires four type of modes(regular,bold,italic,bolditalic).
        #If all modes are not found, dummy entries are made for remaining modes.
        for familyName, name, font_dir, mode in sorted(registered_font_list):
            if not last_family or not font_modes:
                last_family = familyName
                font_modes = init_new_font(familyName, name, font_dir)

            if last_family != familyName:
                # new font familly, adding previous to the list of fonts
                if not font_modes['italic']:
                    font_modes['italic'] = font_modes['regular'][:3]+('italic',)
                if not font_modes['bolditalic']:
                    font_modes['bolditalic'] = font_modes['bold'][:3]+('bolditalic',)
                CustomTTFonts.extend(font_modes.values())
                font_modes = init_new_font(familyName, name, font_dir)

            if (mode== 'normal') or (mode == 'regular') or (mode == 'medium') or (mode == 'book'):
                font_modes['regular'] = (familyName, name, font_dir, 'regular')
            elif (mode == 'italic') or (mode == 'oblique'):
                font_modes['italic'] = (familyName, name, font_dir, 'italic')
            elif mode == 'bold':
                font_modes['bold'] = (familyName, name, font_dir, 'bold')
            elif (mode == 'bolditalic') or (mode == 'boldoblique'):
                font_modes['bolditalic'] = (familyName, name, font_dir, 'bolditalic')
            last_family = familyName

        # add the last one
        if font_modes:
            if not font_modes['italic']:
                font_modes['italic'] = font_modes['regular'][:3]+('italic',)
            if not font_modes['bolditalic']:
                font_modes['bolditalic'] = font_modes['bold'][:3]+('bolditalic',)
            CustomTTFonts.extend(font_modes.values())

        _fonts_cache['total_system_fonts'] = len(all_system_fonts)
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
    return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
