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

import logging
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase import ttfonts
import platform
from reportlab import rl_config
supported_fonts = []

#.apidoc title: TTF Font Table

"""This module allows the mapping of some system-available TTF fonts to
the reportlab engine.

This file could be customized per distro (although most Linux/Unix ones)
should have the same filenames, only need the code below).

Due to an awful configuration that ships with reportlab at many Linux
and Ubuntu distros, we have to override the search path, too.
"""

_logger = logging.getLogger(__name__)

TTFSearchPath_Linux = [
            '/usr/share/fonts/truetype', # SuSE
            '/usr/share/fonts/dejavu', '/usr/share/fonts/liberation', # Fedora, RHEL
            '/usr/share/fonts/truetype/*', # Ubuntu,
            '/usr/share/fonts/TTF/*', # at Mandriva/Mageia
            '/usr/share/fonts/TTF', # Arch Linux
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

def RegisterCustomFonts():
    searchpath = []
    global supported_fonts
    local_platform = platform.system()
    if local_platform in TTFSearchPathMap:
        searchpath += TTFSearchPathMap[local_platform]
    # Append the original search path of reportlab (at the end)
    searchpath += rl_config.TTFSearchPath 
    for dirname in searchpath:
        if os.path.exists(dirname):
            for filename in os.listdir(dirname):
                if filename.lower().endswith('.ttf'):
                    filename = os.path.join(dirname, filename)
                    try:
                        face = ttfonts.TTFontFace(filename)
                        pdfmetrics.registerFont(ttfonts.TTFont(face.name, filename, asciiReadable=0))
                        supported_fonts.append((face.name,face.name))
                        _logger.debug("Found font %s at %s", face.name, filename)
                    except:
                        _logger.warning("Could not register Font %s",face.name)
    return True

#eof

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
